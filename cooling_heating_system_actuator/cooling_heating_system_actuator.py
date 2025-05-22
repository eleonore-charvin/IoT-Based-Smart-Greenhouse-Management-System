import json
import requests
import uuid
import time
from MyMQTT import *

class CoolingHeatingActuator:

    def __init__(self, settings, greenhouseID):
        """
        Initialize CoolingHeatingActuator.
        
        Parameters:
            settings (dict): Settings of CoolingHeatingActuator.
            greenhouseID (int): ID of the greenhouse in which the actuator is.
        """

        self.settings = settings
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"] 
        self.catalogURL = self.settings["catalogURL"]

        self.greenhouseID = greenhouseID
        self.heatingcoolingTopic = self.settings["heatingcoolingTopic"].format(greenhouseID=self.greenhouseID)
        self.status = self.settings["deviceInfo"]["status"]
        
        self.deviceInfo = self.settings["deviceInfo"]

        self.deviceID = f"TemperatureActuator{self.greenhouseID}"  # example: TemperatureActuator1

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)

        self.start()
        self.registerDevice() # register the device in the catalog

    def registerDevice(self):
        """
        Register the device in the catalog.
        """  
        try:   
            actualTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.deviceInfo["lastUpdate"] = actualTime
            self.deviceInfo["deviceID"] = self.deviceID
            params = {"greenhouseID": self.greenhouseID}
            response = requests.post(f"{self.catalogURL}/devices", params=params, data=json.dumps(self.deviceInfo))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"[Greenhouse {self.greenhouseID}] Error raised by catalog while registering device: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            print(f"[Greenhouse {self.greenhouseID}] Error registering device in the catalog: {e}")

    def updateDevice(self):
        """
        Update the device registration in the catalog.
        """
        try:
            actualTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.deviceInfo["lastUpdate"] = actualTime
            response = requests.put(f"{self.catalogURL}/devices", data=json.dumps(self.deviceInfo))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"[Greenhouse {self.greenhouseID}] Error raised by catalog while registering device: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            print(f"[Greenhouse {self.greenhouseID}] Error registering device in the catalog: {e}")
    
    def notify(self, topic, payload):
        """
        Method called when a message is received.
        Retreive the command and set the status (heating/cooling/off) accordingly.
        
        Parameters:
            topic (str): topic of the message.
            payload (json): payload of the message.
        """
        try:
            data = json.loads(payload)
            command = data.get("command")

            if command == "heating":
                self.status = "heating"
                print(f"[Greenhouse {self.greenhouseID}] Heating is ON.")
            elif command == "cooling":
                self.status = "cooling"
                print(f"[Greenhouse {self.greenhouseID}] Cooling is ON.")
            elif command == "off":
                self.status = "off"
                print(f"[Greenhouse {self.greenhouseID}] Actuators are OFF.")
            else:
                print(f"[Greenhouse {self.greenhouseID}] Unknown command received: {command}")
        except json.JSONDecodeError:
            print(f"[Greenhouse {self.greenhouseID}] Error in the format of the MQTT message.")
        except Exception as e:
            print(f"[Greenhouse {self.greenhouseID}] Error in the message: {e}")

    def start(self):
        """
        Start the MQTT client and subscribe to the topic.
        """
        self.mqttClient.start()
        self.mqttClient.mySubscribe(self.heatingcoolingTopic)
        
    def stop(self):
        """
        Stop the MQTT client.
        """
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
        actuator = CoolingHeatingActuator(settings, greenhouseID)
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