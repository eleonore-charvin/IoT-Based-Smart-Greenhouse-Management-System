import requests
import json
import time
import uuid
from MyMQTT import *

class TemperatureControl:
    def __init__(self, settings):
        self.settings = settings
        self.catalogURL = self.settings["catalogURL"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.serviceInfo = self.settings["serviceInfo"]
        # self.temperatureTopic = self.settings["temperatureTopic"].format(greenhouseID=self.greenhouseID)
        # self.heatingcoolingTopic = self.settings["heatingcoolingTopic"].format(greenhouseID=self.greenhouseID)

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)

        self.temp_min = None
        self.temp_max = None
        self.current_temperature = None

        self.mqttClient.start() 

    def getCatalog(self):
        try:
            response = requests.get(f"{settings['catalogURL']}/greenhouses") # get the list of greenhouses
            self.greenhouses = response.json().get('greenhousesList', [])
        except Exception as e:
            print(f"Error fetching greenhouses: {e}")
            self.greenhouses = []

    ################## aggiungere parte per chiamare la funzione più volte per ogni serra
    def registerService(self):
        """
        Register the service in the catalog
        """
        actualTime = time.time()
        self.serviceInfo["lastUpdate"] = actualTime
        requests.post(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
    
    def updateService(self):
        """
        Update the service registration in the catalog
        """
        actualTime = time.time()
        self.serviceInfo["lastUpdate"] = actualTime
        requests.put(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))

    def get_temperature_range(self):
        """Recupera il range di temperatura accettabile dal catalogo."""
        try:
            response = requests.get(f"{self.catalogURL}/greenhouses")
            if response.status_code == 200:
                catalog = response.json()
                for greenhouse in catalog["greenhousesList"]:
                    if greenhouse["greenhouseID"] == self.greenhouseID:
                        min_temp_values = []
                        max_temp_values = []
                        for zone in greenhouse["zones"]:
                            for zone_info in catalog["zonesList"]:
                                if zone_info["zoneID"] == zone["zoneID"]:
                                    min_temp_values.append(zone_info["temperatureRange"]["min"])
                                    max_temp_values.append(zone_info["temperatureRange"]["max"])

                        self.temp_min = max(min_temp_values)
                        self.temp_max = min(max_temp_values)
                        print(f"Temperature range aggiornato: {self.temp_min} - {self.temp_max}")
                        return
            print("Errore nel recupero del catalogo")
        except Exception as e:
            print(f"Errore nella richiesta al catalogo: {e}")

    def temperature_callback(self, topic, payload):
        """Gestisce i messaggi ricevuti dal sensore di temperatura."""
        try:
            data = json.loads(payload)
            self.current_temperature = data["e"][0]["v"]
            print(f"[{self.greenhouseID}] Temperatura ricevuta: {self.current_temperature}")
            self.control_temperature()
        except Exception as e:
            print(f"[{self.greenhouseID}] Errore nella gestione del messaggio MQTT: {e}")

    def control_temperature(self):
        """Decide se attivare riscaldamento o raffreddamento e pubblica sempre lo stato attuale."""
        if self.current_temperature is None or self.temp_min is None or self.temp_max is None:
            return

        if self.current_temperature < self.temp_min:
            self.publish("heating_on")
        elif self.current_temperature > self.temp_max:
            self.publish("cooling_on")
        else:
            self.publish("off")

    def publish(self, command):
        """Pubblica il comando sul topic /heatingcoolingTopic."""
        message = {
            "command": command
        }
        self.mqttClient.myPublish(self.heatingcoolingTopic, json.dumps(message))
        print(f"[{self.greenhouseID}] Pubblicato comando: {command}")

    def start(self):
        """Avvia il controllo della temperatura."""
        self.get_temperature_range()
        self.mqttClient.mySubscribe(self.temperatureTopic)
        self.mqttClient.mySubscribe(self.heatingcoolingTopic)
        self.mqttClient.start()
        print(f"[{self.greenhouseID}] Controllo della temperatura avviato.")

    def stop(self):
        """Ferma il client MQTT."""
        self.mqttClient.stop()
        print(f"[{self.greenhouseID}] Controllo della temperatura arrestato.")

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
        print("Temperature Controller Stopped")