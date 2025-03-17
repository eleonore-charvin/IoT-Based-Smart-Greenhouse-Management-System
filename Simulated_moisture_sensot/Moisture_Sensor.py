import json
import time
import random
import requests
import cherrypy
import uuid
from MyMQTT import MyMQTT

class SimulatedMoistureSensor:
    exposed = True 

    def __init__(self, settings):
        self.settings = settings
        self.catalog_url = settings['catalog_url']
        self.device_info = settings['device_info']
        
        self.device_id = str(uuid.uuid4()) 
        self.device_info['ID'] = self.device_id
        self.device_info['port'] = random.randint(9000, 9999)
        self.greenhouse_id = self.get_greenhouse_id()

        self.mqtt_broker = settings['broker']
        self.mqtt_port = settings['port']
        self.moisture_topic = settings['moisture_topic']
        self.irrigation_topic = settings['irrigation_topic']
        self.client_id = str(uuid.uuid1())
        self.client = MyMQTT(self.client_id, self.mqtt_broker, self.mqtt_port, self)
        
        self.zone_id = settings['zone_id']
        self.moisture_level = random.randint(30, 60)
        self.irrigation_on = False
        
        requests.post(f'{self.catalog_url}/devices', data=json.dumps(self.device_info))
        self.startSim()
    
    def get_greenhouse_id(self):
        try:
            response = requests.get(f'{self.catalog_url}')
            catalog = response.json()
            for greenhouse in catalog['greenhouseList']:
                for device in greenhouse['devices']:
                    if device['deviceID'] == self.device_info['ID']:
                        return greenhouse['greenhouseID']
            return "unknown"
        except Exception as e:
            print(f"Errore nel recupero dell'ID della serra: {e}")
            return "unknown"
    
    def notify(self, topic, payload):
        try:
            message = json.loads(payload)
            if message.get("zone_id") == self.zone_id:
                self.irrigation_on = (message.get("command") == "ON")
        except Exception as e:
            print(f"Errore nell'elaborazione del messaggio: {e}")
    
    def update_moisture(self):
        if self.irrigation_on:
            self.moisture_level = min(100, self.moisture_level + 10)
        else:
            self.moisture_level = max(0, self.moisture_level - random.randint(1, 3))
        return round(self.moisture_level, 2)
    
    def startSim(self):
        self.client.start()
        self.client.mySubscribe(self.irrigation_topic)
    
    def stopSim(self):
        self.client.stop()
    
    def publish(self):
        message = {"zone_id": self.zone_id, "moisture": self.update_moisture()}
        self.client.myPublish(self.moisture_topic, message)
        print(f"Zone {self.zone_id}: Moisture {self.moisture_level}% (Irrigation: {self.irrigation_on})")
    
    def GET(self, *uri, **params):
        if len(uri) != 0 and uri[0] == 'moisture':
            return json.dumps({"zone_id": self.zone_id, "moisture": self.update_moisture()})
        else:
            return json.dumps(self.device_info)
    
    def pingCatalog(self):
        requests.put(f'{self.catalog_url}/devices', data=json.dumps(self.device_info))
    
if __name__ == '__main__':
    with open('settings.json') as f:
        settings = json.load(f)
    
    conf = {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),'tools.sessions.on': True}}
    
    sensor = SimulatedMoistureSensor(settings)
    
    cherrypy.config.update({
        'server.socket_host': settings['device_info']['IP'],  
        'server.socket_port': sensor.device_info['port']
    })
    
    cherrypy.tree.mount(sensor, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()
