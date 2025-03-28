import json

import time
import MyMQTT

class IrrigationActuator:
    def __init__(self, clientID, broker, port, irrigation_topic, zoneID):
        self.client = MyMQTT.MyMQTT(clientID, broker, port, self)
        self.irrigation_topic = irrigation_topic
        self.irrigation_status = "OFF"
        self.zone_id = zoneID
        self.client.start()
        self.client.mySubscribe(self.irrigation_topic)
        
    def notify(self, topic, payload):
        try:
            message = json.loads(payload)
            zone_id = message.get("zone_id")
            command = message.get("command")
            
            if command == "ON":
                print(f"Irrigation started for zone {zone_id}")
                self.irrigation_status = "ON"
            elif command == "OFF":
                print(f"Irrigation stopped for zone {zone_id}")
                self.irrigation_status = "OFF"
            else:
                print(f"Invalid command received: {command}")
        except (ValueError, KeyError) as e:
            print(f"Error processing message: {e}")

    def start(self):
        self.client.start()
        self.client.mySubscribe(self.irrigation_topic)
        print("Irrigation Actuator started.")

    def stop(self):
        self.client.stop()
        print("Irrigation Actuator stopped.")

if __name__ == "__main__":
    with open("settings.json", "r") as f:
        config = json.load(f)

    actuator = IrrigationActuator(
        clientID="IrrigationActuator",
        broker=config["broker"],
        port=config["port"], 
        irrigation_topic=config["irrigation_topic"],
        potID=config["potID"]
    )
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Chiusura Irrigation Actuator...")
        actuator.stop()
