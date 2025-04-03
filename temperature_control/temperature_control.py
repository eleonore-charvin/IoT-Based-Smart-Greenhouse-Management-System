import requests
import json
import time
import uuid
import cherrypy
from MyMQTT import *

class TemperatureControl:
    def __init__(self, settings):
        self.settings = settings
        self.catalogURL = self.settings["catalogURL"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.serviceInfo = self.settings["serviceInfo"]
        self.temperatureTopic = self.settings["temperatureTopic"].format(greenhouseID='+')
        self.heatingcoolingTopic = self.settings["heatingcoolingTopic"]

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)

        self.temp_min = None
        self.temp_max = None
        self.current_temperature = None

        self.mqttClient.start() 

    def registerService(self):
        """
        Register the service in the catalog
        """
        try:
            actualTime = time.time()
            self.serviceInfo["lastUpdate"] = actualTime
            response = requests.post(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
            response.raise_for_status()
        except cherrypy.HTTPError as e: # Catching HTTPError
            print(f"Error raised by catalog while registering service: {e.status} - {e.args[0]}")
        except Exception as e:
            print(f"Error registering service in the catalog: {e}")
        
    def updateService(self):
        """
        Update the service registration in the catalog
        """
        try:
            actualTime = time.time()
            self.serviceInfo["lastUpdate"] = actualTime
            response = requests.put(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
            response.raise_for_status()
        except cherrypy.HTTPError as e: # Catching HTTPError
            print(f"Error raised by catalog while updating service: {e.status} - {e.args[0]}")
        except Exception as e:
            print(f"Error updating service in the catalog: {e}")

    def get_temperature_range(self,greenhouseID):
        """
        Recupera il range di temperatura accettabile dal catalogo.
        """
        try:
            response = requests.get(f"{self.catalogURL}/greenhouses")
            if response.status_code == 200:
                catalog = response.json()
                for greenhouse in catalog["greenhousesList"]: #maybe modify this 
                    if greenhouse["greenhouseID"] == greenhouseID:
                        min_temp_values = []
                        max_temp_values = []
                        for zone in greenhouse["zones"]:
                            for zone_info in catalog["zonesList"]:
                                if zone_info["zoneID"] == zone["zoneID"]:
                                    min_temp_values.append(zone_info["temperatureRange"]["min"])
                                    max_temp_values.append(zone_info["temperatureRange"]["max"])

                        temp_min = max(min_temp_values)
                        temp_max = min(max_temp_values)
                        print(f"Temperature range of greenhouse{greenhouseID}: {temp_min} - {temp_max}")
                        return temp_min, temp_max
            print("Error fetching the greenhouse data from the catalog.")
        except Exception as e:
            print(f"Error in the request for the catalog : {e}")

    def notify(self, topic, payload):
        """
        Gestisce i messaggi ricevuti dal sensore di temperatura.
        """
        greenhouseID = topic.split("/")[-2] # prendo l'ID della serra
        try:
            data = json.loads(payload)
            current_temperature = data["e"][0]["v"] # temperatura attuale
            print(f"[{greenhouseID}] Temperatura ricevuta: {current_temperature}")
            self.control_temperature(current_temperature,greenhouseID)
        except Exception as e:
            print(f"[{greenhouseID}] Errore nella gestione del messaggio MQTT: {e}")

    def control_temperature(self,current_temperature,greenhouseID):
        """
        Decide se attivare riscaldamento o raffreddamento e pubblica sempre lo stato attuale.
        """
        temp_min, temp_max = self.get_temperature_range(greenhouseID)
        if current_temperature is None or temp_min is None or temp_max is None:
            return

        if current_temperature < temp_min:
            self.publish("heating",greenhouseID)
        elif current_temperature > temp_max:
            self.publish("cooling",greenhouseID)
        else:
            self.publish("off",greenhouseID)

    def publish(self, command, greenhouseID):
        """
        Pubblica il comando sul topic /heatingcoolingTopic.
        """
        message = {
            "command": command
        }
        self.mqttClient.myPublish(self.heatingcoolingTopic.format(greenhouseID=greenhouseID), json.dumps(message))
        print(f"[{greenhouseID}] Pubblicato comando: {command}")

    def start(self):
        self.mqttClient.mySubscribe(self.temperatureTopic)
        self.mqttClient.start()

    def stop(self):
        self.mqttClient.stop()

if __name__ == "__main__":
    settings = json.load(open("settings.json"))

    controller = TemperatureControl(settings)
    print("Starting Temperature Controller...")

    controller.registerService()
    
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