import json
<<<<<<< HEAD
<<<<<<< HEAD
import requests
from MyMQTT import *

class ActuatorControl:
    def __init__(self, settings, greenhouseID):
        self.settings = settings
        self.broker_ip = self.settings["brokerIP"]
        self.broker_port = self.settings["brokerPort"] 
        self.mqtt_topic_base = self.settings["mqttTopic"]

        self.greenhouseID = greenhouseID
        self.deviceID = f"temp_act{self.greenhouseID}"  # ID univoco per l'attuatore

        self.client = MyMQTT(self.deviceID, self.broker_ip, self.broker_port, self)

        self.actuator_topic = f"{self.mqtt_topic_base}Greenhouse{self.greenhouseID}/actuator"

        self.startMQTT()

    def notify(self, topic, payload):
        """Riceve i comandi dal topic MQTT e stampa lo stato dell'attuatore."""
=======
=======
import requests
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
from MyMQTT import *

class ActuatorControl:
    def __init__(self, settings, greenhouseID):
        self.settings = settings
        self.broker_ip = self.settings["brokerIP"]
        self.broker_port = self.settings["brokerPort"] 
        self.mqtt_topic_base = self.settings["mqttTopic"]

        self.greenhouseID = greenhouseID
        self.deviceID = f"temp_act{self.greenhouseID}"  # ID univoco per l'attuatore

        self.client = MyMQTT(self.deviceID, self.broker_ip, self.broker_port, self)

        self.actuator_topic = f"{self.mqtt_topic_base}Greenhouse{self.greenhouseID}/actuator"

        self.startMQTT()

    def notify(self, topic, payload):
<<<<<<< HEAD
        """Riceve i comandi dal topic /actuator e stampa lo stato degli attuatori."""
>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
=======
        """Riceve i comandi dal topic MQTT e stampa lo stato dell'attuatore."""
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
        try:
            data = json.loads(payload)
            command = data.get("command", {})

            heating = command.get("heating", "off")
            cooling = command.get("cooling", "off")

            if heating == "on" and cooling == "off":
<<<<<<< HEAD
<<<<<<< HEAD
                print(f"[{self.deviceID}] Heating system is ON. The greenhouse is warming up.")
            elif cooling == "on" and heating == "off":
                print(f"[{self.deviceID}] Cooling system is ON. The greenhouse is cooling down.")
            elif heating == "off" and cooling == "off":
                print(f"[{self.deviceID}] All systems are OFF. Temperature is within the desired range.")
            else:
                print(f"[{self.deviceID}] Invalid command received.")

        except Exception as e:
            print(f"[{self.deviceID}] Error processing MQTT message: {e}")

    def startMQTT(self):
        """Avvia il client MQTT e si sottoscrive al topic dell'attuatore."""
        self.client.start()
        self.client.mySubscribe(self.actuator_topic)
        print(f"[{self.deviceID}] Actuator control system started, listening on {self.actuator_topic}")

    def stopMQTT(self):
        """Ferma il client MQTT."""
        self.client.stop()
        print(f"[{self.deviceID}] Actuator control system stopped.")
=======
                print("Heating system is ON. The greenhouse is warming up.")
=======
                print(f"[{self.deviceID}] Heating system is ON. The greenhouse is warming up.")
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
            elif cooling == "on" and heating == "off":
                print(f"[{self.deviceID}] Cooling system is ON. The greenhouse is cooling down.")
            elif heating == "off" and cooling == "off":
                print(f"[{self.deviceID}] All systems are OFF. Temperature is within the desired range.")
            else:
                print(f"[{self.deviceID}] Invalid command received.")

        except Exception as e:
            print(f"[{self.deviceID}] Error processing MQTT message: {e}")

    def startMQTT(self):
        """Avvia il client MQTT e si sottoscrive al topic dell'attuatore."""
        self.client.start()
        self.client.mySubscribe(self.actuator_topic)
        print(f"[{self.deviceID}] Actuator control system started, listening on {self.actuator_topic}")

    def stopMQTT(self):
        """Ferma il client MQTT."""
        self.client.stop()
<<<<<<< HEAD
        print("Actuator control system stopped.")
>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
=======
        print(f"[{self.deviceID}] Actuator control system stopped.")
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9

if __name__ == "__main__":
    with open("settings.json", "r") as file:
        settings = json.load(file)

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
    # Recupera la lista delle serre dal catalogo
    try:
        response = requests.get(f"{settings['catalogURL']}/greenhouses")
        greenhouses = response.json().get('greenhousesList', [])
    except Exception as e:
        print(f"Error fetching greenhouses: {e}")
        greenhouses = []

    actuators = []  # Lista per mantenere le istanze degli attuatori

    for greenhouse in greenhouses:
        greenhouseID = greenhouse["greenhouseID"]
        actuator = ActuatorControl(settings, greenhouseID)
        actuators.append(actuator)

    print("Actuator control systems started.")
<<<<<<< HEAD
=======
    actuator = ActuatorControl(settings)
    actuator.start()
>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
=======
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9

    try:
        while True:
            pass  # Mantiene il programma in esecuzione
    except KeyboardInterrupt:
<<<<<<< HEAD
<<<<<<< HEAD
        print("Stopping actuators...")
        for actuator in actuators:
            actuator.stopMQTT()
=======
        actuator.stop()
>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
=======
        print("Stopping actuators...")
        for actuator in actuators:
            actuator.stopMQTT()
>>>>>>> 52ec6cfc718fb7e9e41d468a5b25e7735d7f4ef9
