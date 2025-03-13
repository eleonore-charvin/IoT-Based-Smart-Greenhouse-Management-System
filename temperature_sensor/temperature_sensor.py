import cherrypy
import requests
import json
import random
import time
import uuid
from MyMQTT import *

class TemperatureSensorREST_MQTT:
    exposed = True 

    def __init__(self, pi, settings):
        
        self.settings = settings
        self.catalogURL = self.settings['catalogURL']  # URL del catalogo
        self.deviceInfo = self.settings['deviceInfo']  # Info del dispositivo
        
        self.deviceID = str(uuid.uuid4()) # Genera un ID univoco per il dispositivo per il catalogo
        self.deviceInfo['ID'] = self.deviceID
        self.deviceInfo['port'] = random.randint(9000, 9999) # Assegna dinamicamente una porta casuale per REST

        self.pingInterval = pi # Tempo di aggiornamento del catalogo

        self.greenhouseID = self.get_greenhouse_id()

        self.mqttBroker = self.settings['mqttBroker']
        self.mqttPort = self.settings['mqttPort']
        self.topic_publish = f"group06/SmartGreenhouse/{self.greenhouseID}/temperature"  # Topic per pubblicare temperatura
        self.topic_subscribe = f"group06/SmartGreenhouse/{self.greenhouseID}/actuator"  # Topic per ricevere comandi
        self.clientID = str(uuid.uuid1()) # Client MQTT
        self.client = MyMQTT(self.clientID, self.mqttBroker, self.mqttPort, self) # Chiamo MyMQTT

        self.__message_temperature = {
            'bn': f'TemperatureSensorREST_MQTT_{self.deviceID}',
            'e': [{'n': 'temperature', 'v': '', 't': '', 'u': 'cel'}]
        }
        
        self.current_temperature = random.uniform(17.0, 40.0)  
        self.heating = False  
        self.cooling = False  

        requests.post(f'{self.catalogURL}/devices', data=json.dumps(self.deviceInfo)) # Registro il dispostivo nel catalogo
        
        self.startSim() # Avvio la simulazione del sensore

    '''funzioni'''

    def get_greenhouse_id(self):
        try:
            response = requests.get(f'{self.catalogURL}')
            catalog = response.json()
            
            for greenhouse in catalog['greenhousesList']:
                for device in greenhouse['devices']:
                    if device['deviceID'] == self.deviceInfo['ID']:
                        return greenhouse['greenhouseID']
            
            return "unknown"
        except Exception as e:
            print(f"Errore nel recupero dell'ID della serra: {e}")
            return "unknown"
    
    def notify(self, topic, payload):
        
        try:
            message = json.loads(payload)
            command = message.get("command")

            if command == "heating_on":
                self.heating = True
                self.cooling = False
            elif command == "cooling_on":
                self.cooling = True
                self.heating = False
            elif command == "off":
                self.heating = False
                self.cooling = False
        except Exception as e:
            print(f"Errore nell'elaborazione del messaggio: {e}")
    
    def read_temperature_value(self):
    
        if self.heating:
            self.current_temperature = min(self.current_temperature + random.uniform(0.3, 0.8), 35.0)
        elif self.cooling:
            self.current_temperature = max(self.current_temperature - random.uniform(0.3, 0.8), 18.0)
        else:
            self.current_temperature = max(18.0, min(35.0, self.current_temperature + random.uniform(-0.2, 0.2)))
    
        return round(self.current_temperature, 2)

    def startSim(self):
        self.client.start()
        self.client.mySubscribe(self.topic_subscribe)
    
    def stopSim(self):
        self.client.stop()
    
    def publish(self):
        message_temperature = self.__message_temperature
        message_temperature['e'][0]['v'] = self.read_temperature_value()
        message_temperature['e'][0]['t'] = time.time()
        self.client.myPublish(self.topic_publish, message_temperature)
        print(f"Messaggio pubblicato: \n {message_temperature}")

    def GET(self, *uri, **params):
        if len(uri) != 0 and uri[0] == 'temp':
            message = self.__message_temperature
            message['e'][0]['v'] = self.read_temperature_value()
            message['e'][0]['t'] = time.time()
            return json.dumps(message)
        else:
            return json.dumps(self.deviceInfo)

    def pingCatalog(self):
        requests.put(f'{self.catalogURL}/devices', data=json.dumps(self.deviceInfo))

if __name__ == '__main__':
    
    with open('settings.json') as settings_file:
        settings = json.load(settings_file)
    
    conf = {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),'tools.sessions.on': True}}
    
    s = TemperatureSensorREST_MQTT(30, settings)
    
    cherrypy.config.update({
        'server.socket_host': settings['deviceInfo']['IP'],  
        'server.socket_port': s.deviceInfo['port']
        })
    
    cherrypy.tree.mount(s, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()