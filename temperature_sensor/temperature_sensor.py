import requests
import json
import random
import time
import uuid
from MyMQTT import *

class TemperatureSensorMQTT:
    def __init__(self, settings, greenhouseID):
        self.settings = settings
        self.catalogURL = self.settings["catalogURL"]
        self.deviceInfo = self.settings["deviceInfo"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.greenhouseID = greenhouseID
        self.temperatureTopic = self.settings["temperatureTopic"].format(greenhouseID=self.greenhouseID)
        self.heatingcoolingTopic = self.settings["heatingcoolingTopic"].format(greenhouseID=self.greenhouseID)

        self.deviceID = f"TemperatureSensor{self.greenhouseID}"

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=None)

        self.current_temperature = None  
        self.previous_temperature = 20.0  # initial temperature
        self.heating = False
        self.cooling = False

        self.startMQTT()

    def startMQTT(self):
        """
        Start the MQTT client and subscribe to the temperature topic
        """
        self.mqttClient.start()
        self.mqttClient.mySubscribe(self.heatingcoolingTopic)
        self.mqttClient.mySubscribe(self.temperatureTopic)  

    def stopMQTT(self):
        """
        Stop the MQTT client
        """
        self.mqttClient.stop()

    def notify(self, topic, payload):
        """
        Retreive command from the  actuator and set the heating/cooling state accordingly.
        """
        if topic == self.heatingcoolingTopic:
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
                else:
                    print(f"[{self.deviceID}] Unknown command: {command}")
            except json.JSONDecodeError:
                print(f"[{self.deviceID}] Error in the format of the MQTT message.")
            except Exception as e:
                print(f"[{self.deviceID}] Error in the message: {e}")

    def read_temperature_value(self):
        """
        Simulate the reading of the temperature value.
        In a real scenario, this would be replaced with actual sensor reading logic.
        """
        if self.heating:
            self.current_temperature = min(self.previous_temperature + random.uniform(0.3, 0.8), 35.0)
        elif self.cooling:
            self.current_temperature = max(self.previous_temperature - random.uniform(0.3, 0.8), 18.0)
        else:
            self.current_temperature = max(18.0, min(35.0, self.previous_temperature + random.uniform(-0.2, 0.2)))

        self.previous_temperature = self.current_temperature
        return round(self.current_temperature, 1) 

    def publish(self):
        """
        PUblish the temperature value to the topic MQTT.
        """
        temperature = self.read_temperature_value()

        self.mqttClient.myPublish(self.temperatureTopic, str(temperature)) # publish the temperature
        print(f"[{self.deviceID}] Published Temperature: {temperature} °C") # print the complete message

if __name__ == '__main__':
    settings = json.load(open("settings.json"))

    try:
        response = requests.get(f"{settings['catalogURL']}/greenhouses")
        greenhouses = response.json().get('greenhousesList', [])
    except Exception as e:
        print(f"Error fetching greenhouses: {e}")
        greenhouses = []

    sensors = [] 
    for greenhouse in greenhouses:
        greenhouseID = greenhouse["greenhouseID"]
        sensor = TemperatureSensorMQTT(settings, greenhouseID)
        sensors.append(sensor)

    print("Temperature sensors started.")
    
    try:
        while True:
            for sensor in sensors:
                sensor.publish()
            time.sleep(10) 
    except KeyboardInterrupt:
        print("Stopping sensors...")
        for sensor in sensors:
            sensor.stopMQTT()
