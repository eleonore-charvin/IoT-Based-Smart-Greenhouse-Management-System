import requests
import json
import random
import time
import uuid
from MyMQTT import *

class TemperatureSensorMQTT:
    def __init__(self, settings, greenhouseID):
        """
        Initialize TemperatureSensor.
        
        Parameters:
            settings (dict): Settings of TemperatureSensor.
            greenhouseID (int): ID of the greenhouse in which the sensor is.
        """

        self.settings = settings
        self.catalogURL = self.settings["catalogURL"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]

        self.greenhouseID = greenhouseID
        self.temperatureTopic = self.settings["temperatureTopic"].format(greenhouseID=self.greenhouseID)
        self.heatingcoolingTopic = self.settings["heatingcoolingTopic"].format(greenhouseID=self.greenhouseID)

        self.deviceInfo = self.settings["deviceInfo"]

        self.deviceID = f"TemperatureSensor{self.greenhouseID}" # example: TemperatureSensor1

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)

        self.current_temperature = None  
        self.max_temperature = 45 # maximum temperature
        self.min_temperature = 10 # minimum temperature
        self.previous_temperature = random.randint(self.min_temperature, self.max_temperature) # initial temperature
        self.heating = False
        self.cooling = False

        self._message = {
            "v":"",
            "u":"°C",
            "t":"",
            "n":"temperature"
        }

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
            params = {"greenhouseID": greenhouseID}
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
    
    def start(self):
        """
        Start the MQTT client and subscribe to the temperature topic
        """
        self.mqttClient.start()
        self.mqttClient.mySubscribe(self.heatingcoolingTopic) # subscribe to the heating/cooling topic 
    
    def stop(self):
        """
        Stop the MQTT client
        """
        self.mqttClient.stop()

    def notify(self, topic, payload):
        """
        Method called when a message is received.
        Retreive the command and set the heating and cooling states accordingly.
        
        Parameters:
            topic (str): topic of the message.
            payload (json): payload of the message.
        """
        try:
            message = json.loads(payload)
            command = message.get("command")

            if command == "heating":
                self.heating = True
                self.cooling = False
            elif command == "cooling":
                self.heating = False
                self.cooling = True
            elif command == "off":
                self.heating = False
                self.cooling = False
            else:
                print(f"[Greenhouse {self.greenhouseID}] Unknown command: {command}")
        except json.JSONDecodeError:
            print(f"[Greenhouse {self.greenhouseID}] Error in the format of the MQTT message.")
        except Exception as e:
            print(f"[Greenhouse {self.greenhouseID}] Error in the message: {e}")

    def simulate_temperature(self):
        """
        Simulate the temperature value.
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
        Simulate and publish the temperature value.
        """
        temperature = self.simulate_temperature()
        message = self._message.copy()
        message["v"] = temperature
        message["t"] = time.time()
        self.mqttClient.myPublish(self.temperatureTopic, message) # publish the temperature
        print(f"[Greenhouse {self.greenhouseID}] Published Temperature {temperature} °C") # print the complete message

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

    print("Temperature sensors started...")
    
    try:
        while True:
            for sensor in sensors:
                time.sleep(15)
                sensor.publish() # publish the temperature value
                sensor.updateDevice() # update the device in the catalog

            time.sleep(10) 
    except KeyboardInterrupt:
        print("Stopping sensors...")
        for sensor in sensors:
            sensor.stop()