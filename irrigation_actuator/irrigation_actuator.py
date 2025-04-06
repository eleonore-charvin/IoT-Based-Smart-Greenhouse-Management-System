import json

import time
import MyMQTT

class IrrigationActuator:
    def __init__(self, clientID, broker, port, irrigation_topic, serviceinfo, zoneID):
        self.client = MyMQTT.MyMQTT(clientID, broker, port, self)
        self.irrigation_topic = irrigation_topic
        self.serviceinfo = serviceinfo
        self.irrigation_status = "OFF"
        self.zone_id = zoneID
        self.client.start()
        self.client.mySubscribe(self.irrigation_topic)

    def registerService(self):
        """
        Register the service in the catalog
        """
        try:
            actualTime = time.time()
            self.serviceInfo["lastUpdate"] = actualTime
            requests.post(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
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
            requests.put(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
        except cherrypy.HTTPError as e: # Catching HTTPError
            print(f"Error raised by catalog while updating service: {e.status} - {e.args[0]}")
        except Exception as e:
            print(f"Error updating service in the catalog: {e}")
            
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
    try:
        greenhouses = requests.get(f"{config['catalog_url']}/greenhouses").json().get('greenhousesList', [])
        for greenhouse in greenhouses:
            for zone in greenhouse.get("Zones", []):
                zone_id = zone["ZoneID"]
                irrigation_topic = zone.get("IrrigationTopic", config["irrigation_topic"])
                actuator = IrrigationActuator(
                    clientID=f"IrrigationActuator_{zone_id}",
                    broker=config["broker"],
                    port=config["port"],
                    irrigation_topic=irrigation_topic,
                    zoneID=zone_id,
                    catalog_url=config["catalog_url"]
                )
                actuator.registerService()
                actuator.start()
    try:
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            #Every 40s
            if counter == 20:
                # Update the service registration
                actuator.updateService()
                counter = 0

    except KeyboardInterrupt:
        print("Chiusura Irrigation Actuator...")
        actuator.stop()
