<<<<<<< HEAD
<<<<<<< HEAD
=======
import cherrypy
>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
=======
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
import requests
import json
import random
import time
import uuid
from MyMQTT import *

<<<<<<< HEAD
<<<<<<< HEAD
class TemperatureSensorMQTT:
    def __init__(self, settings, greenhouseID):

        self.settings = settings 
        self.catalogURL = self.settings['catalogURL']

        self.greenhouseID = greenhouseID
        self.deviceID = f"temp_sens{self.greenhouseID}"  # ID univoco per il sensore

        self.mqttBroker = self.settings['mqttBroker']
        self.mqttPort = self.settings['mqttPort']
        self.topic_publish = f"group06/SmartGreenhouse/{self.greenhouseID}/temperature"
        self.topic_subscribe = f"group06/SmartGreenhouse/{self.greenhouseID}/actuator"
        self.clientID = str(uuid.uuid1())  
        self.client = MyMQTT(self.clientID, self.mqttBroker, self.mqttPort, self)

        self.current_temperature = random.uniform(17.0, 40.0)
        self.heating = False  
        self.cooling = False  

        # Registra il dispositivo nel catalogo
        deviceInfo = {
            "ID": self.deviceID,
            "type": "temperature_sensor",
            "greenhouseID": self.greenhouseID
        }
        requests.post(f'{self.catalogURL}/devices', json=deviceInfo)

        self.startMQTT()

    def notify(self, topic, payload):
        """Riceve i comandi dall'attuatore"""
=======
class TemperatureSensorREST_MQTT:
    exposed = True 

    def __init__(self, pi, settings):
        
=======
class TemperatureSensorMQTT:
    def __init__(self, settings, greenhouseID):
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
        self.settings = settings
        self.catalogURL = self.settings['catalogURL']

        self.greenhouseID = greenhouseID
        self.deviceID = f"temp_sens{self.greenhouseID}"  # ID univoco per il sensore

        self.mqttBroker = self.settings['mqttBroker']
        self.mqttPort = self.settings['mqttPort']
        self.topic_publish = f"group06/SmartGreenhouse/{self.greenhouseID}/temperature"
        self.topic_subscribe = f"group06/SmartGreenhouse/{self.greenhouseID}/actuator"
        self.clientID = str(uuid.uuid1())  
        self.client = MyMQTT(self.clientID, self.mqttBroker, self.mqttPort, self)

        self.current_temperature = random.uniform(17.0, 40.0)
        self.heating = False  
        self.cooling = False  

        # Registra il dispositivo nel catalogo
        deviceInfo = {
            "ID": self.deviceID,
            "type": "temperature_sensor",
            "greenhouseID": self.greenhouseID
        }
        requests.post(f'{self.catalogURL}/devices', json=deviceInfo)

        self.startMQTT()

    def notify(self, topic, payload):
<<<<<<< HEAD
        
>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
=======
        """Riceve i comandi dall'attuatore"""
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
        try:
            message = json.loads(payload)
            command = message.get("command")

            if command == "heating_on":
                self.heating = True
                self.cooling = False
<<<<<<< HEAD
<<<<<<< HEAD
                print(f"[{self.deviceID}] Heating ON")
            elif command == "cooling_on":
                self.cooling = True
                self.heating = False
                print(f"[{self.deviceID}] Cooling ON")
            elif command == "off":
                self.heating = False
                self.cooling = False
                print(f"[{self.deviceID}] All OFF")
        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    def read_temperature_value(self):
        """Simula la lettura della temperatura"""
=======
=======
                print(f"[{self.deviceID}] Heating ON")
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
            elif command == "cooling_on":
                self.cooling = True
                self.heating = False
                print(f"[{self.deviceID}] Cooling ON")
            elif command == "off":
                self.heating = False
                self.cooling = False
                print(f"[{self.deviceID}] All OFF")
        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    def read_temperature_value(self):
<<<<<<< HEAD
    
>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
=======
        """Simula la lettura della temperatura"""
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
        if self.heating:
            self.current_temperature = min(self.current_temperature + random.uniform(0.3, 0.8), 35.0)
        elif self.cooling:
            self.current_temperature = max(self.current_temperature - random.uniform(0.3, 0.8), 18.0)
        else:
            self.current_temperature = max(18.0, min(35.0, self.current_temperature + random.uniform(-0.2, 0.2)))
<<<<<<< HEAD
<<<<<<< HEAD

        return round(self.current_temperature, 2)

    def startMQTT(self):
        """Avvia il client MQTT"""
        self.client.start()
        self.client.mySubscribe(self.topic_subscribe)

    def stopMQTT(self):
        """Ferma il client MQTT"""
        self.client.stop()

    def publish_temperature(self):
        """Pubblica la temperatura attuale"""
        message = {
            'bn': f'TemperatureSensor_{self.deviceID}',
            'e': [{'n': 'temperature', 'v': self.read_temperature_value(), 't': time.time(), 'u': 'cel'}]
        }
        self.client.myPublish(self.topic_publish, json.dumps(message))
        print(f"[{self.deviceID}] Published: {message}")

if __name__ == '__main__':
    with open('settings.json') as settings_file:
        settings = json.load(settings_file)

    # Recupera la lista delle serre dal catalogo
    try:
        response = requests.get(f"{settings['catalogURL']}/greenhouses")
        greenhouses = response.json().get('greenhousesList', [])
    except Exception as e:
        print(f"Error fetching greenhouses: {e}")
        greenhouses = []

    sensors = []  # Lista per mantenere le istanze dei sensori

    for greenhouse in greenhouses:
        greenhouseID = greenhouse["greenhouseID"]
        sensor = TemperatureSensorMQTT(settings, greenhouseID)
        sensors.append(sensor)

    print("Temperature sensors started.")

    try:
        while True:
            for sensor in sensors:
                sensor.publish_temperature()
            time.sleep(10)
    except KeyboardInterrupt:
        print("Stopping sensors...")
        for sensor in sensors:
            sensor.stopMQTT()
=======
    
=======

>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
        return round(self.current_temperature, 2)

    def startMQTT(self):
        """Avvia il client MQTT"""
        self.client.start()
        self.client.mySubscribe(self.topic_subscribe)

    def stopMQTT(self):
        """Ferma il client MQTT"""
        self.client.stop()

    def publish_temperature(self):
        """Pubblica la temperatura attuale"""
        message = {
            'bn': f'TemperatureSensor_{self.deviceID}',
            'e': [{'n': 'temperature', 'v': self.read_temperature_value(), 't': time.time(), 'u': 'cel'}]
        }
        self.client.myPublish(self.topic_publish, json.dumps(message))
        print(f"[{self.deviceID}] Published: {message}")

if __name__ == '__main__':
    with open('settings.json') as settings_file:
        settings = json.load(settings_file)
<<<<<<< HEAD
    
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
>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
=======

    # Recupera la lista delle serre dal catalogo
    try:
        response = requests.get(f"{settings['catalogURL']}/greenhouses")
        greenhouses = response.json().get('greenhousesList', [])
    except Exception as e:
        print(f"Error fetching greenhouses: {e}")
        greenhouses = []

    sensors = []  # Lista per mantenere le istanze dei sensori

    for greenhouse in greenhouses:
        greenhouseID = greenhouse["greenhouseID"]
        sensor = TemperatureSensorMQTT(settings, greenhouseID)
        sensors.append(sensor)

    print("Temperature sensors started.")

    try:
        while True:
            for sensor in sensors:
                sensor.publish_temperature()
            time.sleep(10)
    except KeyboardInterrupt:
        print("Stopping sensors...")
        for sensor in sensors:
            sensor.stopMQTT()
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
