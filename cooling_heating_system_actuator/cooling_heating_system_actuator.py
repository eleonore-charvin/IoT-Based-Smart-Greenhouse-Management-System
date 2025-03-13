import json
from MyMQTT import *

class ActuatorControl:
    def __init__(self, settings):
        self.settings = settings
        self.broker_ip = self.settings["brokerIP"]
        self.broker_port = self.settings["brokerPort"]
        self.mqtt_topic_base = self.settings["mqttTopic"]

        self.client = MyMQTT("ActuatorControl", self.broker_ip, self.broker_port, self)

        self.greenhouse_id = 1  # ID della serra da monitorare

    def notify(self, topic, payload):
        """Riceve i comandi dal topic /actuator e stampa lo stato degli attuatori."""
        try:
            data = json.loads(payload)
            command = data.get("command", {})

            heating = command.get("heating", "off")
            cooling = command.get("cooling", "off")

            if heating == "on" and cooling == "off":
                print("Heating system is ON. The greenhouse is warming up.")
            elif cooling == "on" and heating == "off":
                print("Cooling system is ON. The greenhouse is cooling down.")
            elif heating == "off" and cooling == "off":
                print("All systems are OFF. Temperature is within the desired range.")
            else:
                print("Invalid command received.")

        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    def start(self):
        """Avvia l'ascolto sul topic /actuator."""
        actuator_topic = f"{self.mqtt_topic_base}Greenhouse{self.greenhouse_id}/actuator"
        self.client.mySubscribe(actuator_topic)
        self.client.start()
        print("Actuator control system started.")

    def stop(self):
        """Ferma il client MQTT."""
        self.client.stop()
        print("Actuator control system stopped.")

if __name__ == "__main__":
    with open("settings.json", "r") as file:
        settings = json.load(file)

    actuator = ActuatorControl(settings)
    actuator.start()

    try:
        while True:
            pass  # Mantiene il programma in esecuzione
    except KeyboardInterrupt:
        actuator.stop()