import requests
import json
import random
import time
import uuid
from MyMQTT import *

class TemperatureSensorMQTT:
    def __init__(self, settings, greenhouseID):
        self.settings = settings
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]

        self.greenhouseID = greenhouseID
        self.temperatureTopic = self.settings["temperatureTopic"].format(greenhouseID=self.greenhouseID)
        self.heatingcoolingTopic = self.settings["heatingcoolingTopic"].format(greenhouseID=self.greenhouseID)

        self.deviceInfo = self.settings["deviceInfo"]

        self.deviceID = f"TemperatureSensor{self.greenhouseID}" # example: TemperatureSensor1

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=None)

        self.current_temperature = None  
        self.previous_temperature = 35.0  # initial temperature
        self.max_temperature = 45.0 # maximum temperature
        self.min_temperature = 10.0 # minimum temperature
        self.heating = False
        self.cooling = False

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
    
    def start(self):
        """
        Start the MQTT client and subscribe to the temperature topic
        """
        self.mqttClient.start()
        self.mqttClient.mySubscribe(self.heatingcoolingTopic)
        self.mqttClient.mySubscribe(self.temperatureTopic)  

    def stop(self):
        """
        Stop the MQTT client
        """
        self.mqttClient.stop()

    def notify(self, topic, payload):
        """
        Retreive command from the actuator and set the heating/cooling state accordingly.
        """
        if topic == self.heatingcoolingTopic:
            try:
                message = json.loads(payload)
                command = message.get("command")

                if command == "heating_on":
                    self.heating = True
                    self.cooling = False
                elif command == "cooling_on":
                    self.heating = False
                    self.cooling = True
                elif command == "off":
                    self.heating = False
                    self.cooling = False
                else:
                    print(f"[{self.deviceID}] Unknown command: {command}")
            except json.JSONDecodeError:
                print(f"[{self.deviceID}] Error in the format of the MQTT message.")
            except Exception as e:
                print(f"[{self.deviceID}] Error in the message: {e}")

    def simulate_temperature(self):
        """
        Simulate the reading of the temperature value.
        In a real scenario, this would be replaced with actual sensor reading logic.
        """
        if self.heating:
            self.current_temperature = min(self.previous_temperature + random.uniform(0.3, 0.8), self.max_temperature)
        elif self.cooling:
            self.current_temperature = max(self.previous_temperature - random.uniform(0.3, 0.8), self.min_temperature)
        else:
            self.current_temperature = max(self.min_temperature, min(self.max_temperature, self.previous_temperature + random.uniform(-0.2, 0.2)))

        self.previous_temperature = self.current_temperature # update the previous temperature
        return round(self.current_temperature, 1) 

    def publish(self):
        """
        PUblish the temperature value to the topic MQTT.
        """
        temperature = self.simulate_temperature()

        self.mqttClient.myPublish(self.temperatureTopic, str(temperature)) # publish the temperature
        print(f"[{self.deviceID}] Published Temperature: {temperature} °C") # print the complete message

if __name__ == '__main__':
    settings = json.load(open("settings.json")) # setting file

    try:
        response = requests.get(f"{settings['catalogURL']}/greenhouses") # get the list of greenhouses
        greenhouses = response.json().get('greenhousesList', [])
    except Exception as e:
        print(f"Error fetching greenhouses: {e}")
        greenhouses = []

    sensors = [] 
    for greenhouse in greenhouses:
        greenhouseID = greenhouse["greenhouseID"]
        sensor = TemperatureSensorMQTT(settings, greenhouseID) # create a sensor for each greenhouse
        sensors.append(sensor)

    print("Temperature sensors started.")
    
    try:
        while True:
            for sensor in sensors:
                time.sleep(5)
                sensor.publish() # publish the temperature value
                sensor.updateDevice() # update the device in the catalog

            time.sleep(10) 
    except KeyboardInterrupt:
        print("Stopping sensors...")
        for sensor in sensors:
            sensor.stop()
