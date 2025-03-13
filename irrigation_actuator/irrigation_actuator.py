import json
import time
import MyMQTT

class IrrigationActuator:
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

if __name__ == "__main__":
    with open("settings.json", "r") as f:
        config = json.load(f)

    actuator = IrrigationActuator(
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
