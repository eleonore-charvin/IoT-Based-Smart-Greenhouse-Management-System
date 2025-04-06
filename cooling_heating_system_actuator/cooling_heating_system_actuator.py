import json
import requests
import uuid
import cherrypy
import time
from MyMQTT import *

class ActuatorControl:
    def __init__(self, settings, greenhouseID):
        self.settings = settings
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"] 
        self.catalogURL = self.settings["catalogURL"]

        self.greenhouseID = greenhouseID
        self.heatingcoolingTopic = self.settings["heatingcoolingTopic"].format(greenhouseID=self.greenhouseID)
        self.status = self.settings["deviceInfo"]["status"]
        
        self.deviceInfo = self.settings["deviceInfo"]

        self.deviceID = f"TemperatureActuator{self.greenhouseID}"  # example: TemperatureActuator1

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=None)

        self.start()
        self.registerDevice() # register the device in the catalog

    def registerDevice(self):
        """
        Register the device in the catalog
        """  
        try:   
            actualTime = time.time()
            self.deviceInfo["lastUpdate"] = actualTime
            self.deviceInfo["deviceID"] = self.deviceID
            self.deviceInfo["greenhouseID"] = self.greenhouseID
            response = requests.post(f"{self.catalogURL}/devices", data=json.dumps(self.deviceInfo))
            response.raise_for_status()
        except cherrypy.HTTPError as e: # Catching HTTPError
            print(f"Error raised by catalog while registering device: {e.status} - {e.args[0]}")
        except Exception as e:
            print(f"Error registering device in the catalog: {e}")

    def updateDevice(self):
        """
        Update the device registration in the catalog
        """
        try:
            actualTime = time.time()
            self.deviceInfo["lastUpdate"] = actualTime
            response = requests.post(f"{self.catalogURL}/devices", data=json.dumps(self.deviceInfo))
            response.raise_for_status()
        except cherrypy.HTTPError as e: # Catching HTTPError
            print(f"Error raised by catalog while registering device: {e.status} - {e.args[0]}")
        except Exception as e:
            print(f"Error registering device in the catalog: {e}")
    
    def notify(self, topic, payload):
        """Riceve i comandi dal topic MQTT e stampa lo stato dell'attuatore."""
        try:
            data = json.loads(payload)
            command = data.get("command", {})

            if command == "heating":
                self.status = "heating"
                print(f"[{self.deviceID}] Heating is ON.")
            elif command == "cooling":
                self.status = "cooling"
                print(f"[{self.deviceID}] Cooling is ON.")
            elif command == "off":
                self.status = "off"
                print(f"[{self.deviceID}] Actuators are OFF.")
            else:
                print(f"[{self.deviceID}] Unknown command received: {command}")
        except json.JSONDecodeError:
            print(f"[{self.deviceID}] Error in the format of the MQTT message.")
        except Exception as e:
            print(f"[{self.deviceID}] Error in the message: {e}")

    def start(self):
        """Avvia il client MQTT e si sottoscrive al topic dell'attuatore."""
        self.mqttClient.start()
        self.mqttClient.mySubscribe(self.heatingcoolingTopic)
        
    def stop(self):
        """Ferma il client MQTT."""
        self.mqttClient.stop()

if __name__ == "__main__":
    settings = json.load(open("settings.json"))

    try:
        response = requests.get(f"{settings['catalogURL']}/greenhouses")
        greenhouses = response.json().get('greenhousesList', [])
    except Exception as e:
        print(f"Error fetching greenhouses: {e}")
        greenhouses = []

    actuators = [] 
    for greenhouse in greenhouses:
        greenhouseID = greenhouse["greenhouseID"]
        actuator = ActuatorControl(settings, greenhouseID)
        actuators.append(actuator)

    print("Actuator control systems started...") 

    try:
        while True:
            for actuator in actuators:
                time.sleep(5)
                actuator.updateDevice()

            time.sleep(10)
    except KeyboardInterrupt:
        print("Stopping actuators...")
        for actuator in actuators:
            actuator.stop()