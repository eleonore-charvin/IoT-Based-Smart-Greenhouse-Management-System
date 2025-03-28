import requests
import json
import time
import uuid
from MyMQTT import *

class TemperatureControl:
    def __init__(self, settings, greenhouseID):
        self.settings = settings
        self.catalogURL = self.settings["catalogURL"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.greenhouseID = greenhouseID
        self.temperatureTopic = self.settings["temperatureTopic"].format(greenhouseID=self.greenhouseID)
        self.heatingcoolingTopic = self.settings["heatingcoolingTopic"].format(greenhouseID=self.greenhouseID)

        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)

        self.temp_min = None
        self.temp_max = None
        self.current_temperature = None

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
            self.publish_command("heating_on")
        elif self.current_temperature > self.temp_max:
            self.publish_command("cooling_on")
        else:
            self.publish_command("off")

    def publish_command(self, command):
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

    try:
        response = requests.get(f"{settings['catalogURL']}/greenhouses")
        greenhouses = response.json().get('greenhousesList', [])
    except Exception as e:
        print(f"Error fetching greenhouses: {e}")
        greenhouses = []

    controllers = []  # Lista per gestire più serre

    for greenhouse in greenhouses:
        greenhouseID = greenhouse["greenhouseID"]
        controller = TemperatureControl(settings, greenhouseID)
        controllers.append(controller)
        controller.start() 

    print("Temperature controllers started.")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("Stopping controllers...")
        for controller in controllers:
            controller.stop()
