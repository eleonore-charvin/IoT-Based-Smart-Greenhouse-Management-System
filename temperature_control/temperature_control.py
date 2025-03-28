import json
import requests
import time
from MyMQTT import *

class TemperatureControl:
    def __init__(self, settings):
        self.settings = settings
        self.catalog_url = self.settings["catalogURL"]
        self.broker_ip = self.settings["brokerIP"]
        self.broker_port = self.settings["brokerPort"]
        self.mqtt_topic_base = self.settings["mqttTopic"]

        self.client = MyMQTT("TemperatureControl", self.broker_ip, self.broker_port, self)

        self.greenhouse_id = 1  
        self.temp_min = None
        self.temp_max = None
        self.current_temperature = None
        self.last_command = None  # Ultimo comando inviato

    def get_temperature_range(self):
        """Recupera il range di temperatura accettabile dal catalogo."""
        try:
            response = requests.get(self.catalog_url)
            if response.status_code == 200:
                catalog = response.json()
                for greenhouse in catalog["greenhousesList"]:
                    if greenhouse["greenhouseID"] == self.greenhouse_id:
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

    def notify_actuator(self, heating, cooling):
        """Pubblica lo stato attuale sul topic /actuator."""
        topic = f"{self.mqtt_topic_base}Greenhouse{self.greenhouse_id}/actuator"
        message = {
            "command": {
                "heating": "on" if heating else "off",
                "cooling": "on" if cooling else "off"
            }
        }

        # Convertiamo il messaggio in stringa per confrontarlo con il precedente
        message_str = json.dumps(message)
        
        if message_str != self.last_command:
            self.client.myPublish(topic, message_str)
            print(f"Pubblicato comando: {message}")
            self.last_command = message_str  # Aggiorniamo l'ultimo comando inviato

    def temperature_callback(self, topic, payload):
        """Gestisce i messaggi ricevuti dal sensore di temperatura."""
        try:
            data = json.loads(payload)
            self.current_temperature = data["e"][0]["v"]
            print(f"Temperatura ricevuta: {self.current_temperature}")
            self.control_temperature()
        except Exception as e:
            print(f"Errore nella gestione del messaggio MQTT: {e}")

    def control_temperature(self):
        """Decide se attivare riscaldamento o raffreddamento e pubblica sempre lo stato attuale."""
        if self.current_temperature is None or self.temp_min is None or self.temp_max is None:
            return

        if self.current_temperature < self.temp_min:
            self.notify_actuator(heating=True, cooling=False)
        elif self.current_temperature > self.temp_max:
            self.notify_actuator(heating=False, cooling=True)
        else:
            self.notify_actuator(heating=False, cooling=False)

    def start(self):
        """Avvia il controllo della temperatura."""
        self.get_temperature_range()
        temp_topic = f"{self.mqtt_topic_base}Greenhouse{self.greenhouse_id}/temperature"
        self.client.mySubscribe(temp_topic)
        self.client.start()
        print("Controllo della temperatura avviato.")

    def stop(self):
        """Ferma il client MQTT."""
        self.client.stop()
        print("Controllo della temperatura arrestato.")

if __name__ == "__main__":
    # Apertura del file settings.json
    with open("settings.json", "r") as file:
        settings = json.load(file)

    controller = TemperatureControl(settings)
    controller.start()
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        controller.stop()
