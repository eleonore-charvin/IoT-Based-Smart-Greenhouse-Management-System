import json
import time
import MyMQTT

class IrrigationActuator:
<<<<<<< HEAD
    def __init__(self, clientID, broker, port, sub_topic):
        self.client = MyMQTT(clientID, broker, port, self)
        self.client.start()
        self.client.mySubscribe(sub_topic)
        self.irrigation_status = "OFF"

    def notify(self, topic, payload):
        try:
            #receives the message with the action to do
            message = json.loads(payload.decode())
            action = message.get("action")
            
            #actuation of the action in the message
            if action == "start_irrigation":
                print("Irrigation started")
                self.irrigation_status = "ON"
            elif action == "stop_irrigation":
                print("Irrigation stopped")
                self.irrigation_status = "OFF"
            else:
                print("Invalid action received")
        except (ValueError, KeyError) as e:
            print(f"Error processing message: {e}")

=======
    def __init__(self, clientID, broker, port, irrigation_topic, potID):
        self.client = MyMQTT.MyMQTT(clientID, broker, port, self)
        self.irrigation_topic = irrigation_topic
        self.irrigation_status = "OFF"
        self.pot_id = potID
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

>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
if __name__ == "__main__":
    with open("settings.json", "r") as f:
        config = json.load(f)

    actuator = IrrigationActuator(
<<<<<<< HEAD
        broker=config["broker"],
        port=config["port"], 
        irrigation_topic= config["irrigation_topic"],
    )
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("Chiusura Irrigation Actuator...")
        actuator.client.stop()
=======
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
>>>>>>> d0cf3d68c964947a43f269bbe0ad6b9207443f7a
