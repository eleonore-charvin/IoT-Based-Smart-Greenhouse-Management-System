import json
import requests
import uuid
import time
from MyMQTT import *

################à finireeeee
class ActuatorControl:
    def __init__(self, settings, greenhouseID):
        self.settings = settings
        self.broker_ip = self.settings["brokerIP"]
        self.broker_port = self.settings["brokerPort"] 

        self.greenhouseID = greenhouseID
        self.heatingcoolingTopic = self.settings["heatingcoolingTopic"].format(greenhouseID=self.greenhouseID)
        self.status = self.settings["deviceInfo"]["status"]
        
        self.deviceInfo = self.settings["deviceInfo"]

        self.deviceID = f"TemperatureActuator{self.greenhouseID}"  # example: TemperatureActuator1

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=None)

        #????????self.actuator_topic = f"{self.heatingcoolingTopic}Greenhouse{self.greenhouseID}/actuator"

        self.start()
        self.registerDevice() # register the device in the catalog
        
    def registerDevice(self):
        """
        Register the service in the catalog
        """     
        actualTime = time.time()
        self.deviceInfo["lastUpdate"] = actualTime
        self.deviceInfo["deviceID"] = self.deviceID
        self.deviceInfo["greenhouseID"] = self.greenhouseID
        requests.post(f"{self.settings['catalogURL']}/devices", data=json.dumps(self.deviceInfo))

    def updateDevice(self):
        """
        Update the service registration in the catalog
        """
        actualTime = time.time()
        self.deviceInfo["lastUpdate"] = actualTime
        requests.put(f"{self.settings['catalogURL']}/devices", data=json.dumps(self.deviceInfo))
        

    def notify(self, topic, payload):
        """Riceve i comandi dal topic MQTT e stampa lo stato dell'attuatore."""
        try:
            data = json.loads(payload)
            command = data.get("command", {})

            heating = command.get("heating", "off")
            cooling = command.get("cooling", "off")

            if heating == "on" and cooling == "off":
                print(f"[{self.deviceID}] Heating system is ON. The greenhouse is warming up.")
            elif cooling == "on" and heating == "off":
                print(f"[{self.deviceID}] Cooling system is ON. The greenhouse is cooling down.")
            elif heating == "off" and cooling == "off":
                print(f"[{self.deviceID}] All systems are OFF. Temperature is within the desired range.")
            else:
                print(f"[{self.deviceID}] Invalid command received.")

        except Exception as e:
            print(f"[{self.deviceID}] Error processing MQTT message: {e}")

    def start(self):
        """Avvia il client MQTT e si sottoscrive al topic dell'attuatore."""
        self.mqttClient.start()
        self.mqttClient.mySubscribe(self.actuator_topic)
        print(f"[{self.deviceID}] Actuator control system started, listening on {self.actuator_topic}")

    def stop(self):
        """Ferma il client MQTT."""
        self.client.stop()
        print(f"[{self.deviceID}] Actuator control system stopped.")

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

    print("Actuator control systems started.")

    try:
        while True:
            for actuator in actuators:
                actuator.updateDevice()

            time.sleep(10)
    except KeyboardInterrupt:
        print("Stopping actuators...")
        for actuator in actuators:
            actuator.stop()