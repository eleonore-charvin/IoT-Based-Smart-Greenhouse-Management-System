import requests
import json
import time
import uuid
from MyMQTT import *

class TemperatureControl:
    def __init__(self, settings):
        """
        Initialize TemperatureControl.
        
        Parameters:
            settings (dict): Settings of TemperatureControl.
        """
        
        self.settings = settings
        self.catalogURL = self.settings["catalogURL"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.serviceInfo = self.settings["serviceInfo"]
        self.temperatureTopic = self.settings["temperatureTopic"]
        self.heatingcoolingTopic = self.settings["heatingcoolingTopic"]

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)

        self.temp_min = None
        self.temp_max = None
        self.current_temperature = None

        self.start() 
        self.registerService()

    def registerService(self):
        """
        Register the service in the catalog
        """
        try:
            actualTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.serviceInfo["lastUpdate"] = actualTime
            response = requests.post(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while registering service: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            print(f"Error registering service in the catalog: {e}")
        
    def updateService(self):
        """
        Update the service registration in the catalog
        """
        try:
            actualTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.serviceInfo["lastUpdate"] = actualTime
            response = requests.put(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while updating service: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            print(f"Error updating service in the catalog: {e}")

    def get_temperature_range(self, greenhouseID):
        """
        Get the temperature range of the greenhouse.

        Params:
            greenhouseID (int): ID of the greenhouse whose temperature range to get.
        """
        try:
            # Get the zones in the greenhouse from the catalog
            params = {"greenhouseID": greenhouseID}
            response = requests.get(f"{self.catalogURL}/zones", params=params)
            if response.status_code == 200:
                zones = response.json().get("zonesList", [])
                min_temp_values = []
                max_temp_values = []

                # Get the temperature ranges of all zones in the greenhouse
                for zone in zones:
                    temperature_range = zone["temperatureRange"]
                    min_temp_values.append(temperature_range["min"])
                    max_temp_values.append(temperature_range["max"])

                # Compute the greenhouse range as the maximum of the lower bounds and minimum of the upper bounds
                temp_min = max(min_temp_values)
                temp_max = min(max_temp_values)
                print(f"[Greenhouse {greenhouseID}] Temperature range {temp_min} °C - {temp_max} °C")
                return temp_min, temp_max
            print(f"[Greenhouse {greenhouseID}] Error fetching the greenhouse data from the catalog.")
        except Exception as e:
            print(f"[Greenhouse {greenhouseID}] Error in the request for the catalog : {e}")

    def notify(self, topic, payload):
        """
        Method called when a message is received.
        Retreive the received temperature and compare it with the temperature range of the greenhouse to decide whether to activate the heating actuator, the cooling one or to deactivate both.
        
        Parameters:
            topic (str): topic of the message.
            payload (json): payload of the message.
        """
        greenhouseID = topic.split("/")[-2] # prendo l'ID della serra
        try:
            data = json.loads(payload)
            current_temperature = data["v"] # temperatura attuale
            self.control_temperature(current_temperature,greenhouseID)
        except Exception as e:
            print(f"[Greenhouse {greenhouseID}] Error processing message: {e}")

    def control_temperature(self, current_temperature, greenhouseID):
        """
        Decide the actuation command (heating, cooling or off) based on the currente temperature and publish the decided value.
        
        Params:
            current_temperature (float): temperature of the greenhouse.
            greenhouseID (int): ID of the greenhouse.
        """

        # Get the temperature range of the greenhouse
        temp_min, temp_max = self.get_temperature_range(greenhouseID)
        if current_temperature is None or temp_min is None or temp_max is None:
            return

        # If the temperature is below the minimum, publish the heating command
        if current_temperature < temp_min:
            self.publish("heating", greenhouseID)
            print(f"[Greenhouse {greenhouseID}] Temperature {current_temperature} °C, heating needed!")
        
        # If the temperature is above the maximum, publish the cooling command
        elif current_temperature > temp_max:
            self.publish("cooling", greenhouseID)
            print(f"[Greenhouse {greenhouseID}] Temperature {current_temperature} °C, cooling needed!")
        
        # Otherwise, publish the off command
        else:
            self.publish("off", greenhouseID)
            print(f"[Greenhouse {greenhouseID}] Temperature {current_temperature} °C, acceptable")

    def publish(self, command, greenhouseID):
        """
        Pubblish the actuation command for the greenhouse.

        Params:
            command (str): value of the actuation command.
            greenhouseID (int): ID of the greenhouse that the actuation command concerns.
        """
        message = {
            "command": command
        }
        self.mqttClient.myPublish(self.heatingcoolingTopic.format(greenhouseID=greenhouseID), message)

    def start(self):
        """
        Start the MQTT client and subscribe to the topic.
        """
        self.mqttClient.start()
        self.mqttClient.mySubscribe(self.temperatureTopic)

    def stop(self):
        """
        Stop the MQTT client.
        """
        self.mqttClient.stop()

if __name__ == "__main__":
    settings = json.load(open("settings.json"))

    controller = TemperatureControl(settings)
    print("Starting Temperature Controller...")
    
    try:
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            # Every 40s
            if counter == 20:
                controller.updateService()
                counter = 0

    except KeyboardInterrupt:
        controller.stop()
        print("Temperature Controller Stopped.")