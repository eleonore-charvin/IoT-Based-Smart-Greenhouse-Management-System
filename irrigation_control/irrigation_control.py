import json
import requests
import MyMQTT
import cherrypy
import time

class IrrigationControl:
    def __init__(self, broker, port, moisture_topic, irrigation_topic, catalog_url, greenhouse_id):
        self.client = MyMQTT.MyMQTT("IrrigationControl", broker, port, self)
        self.irrigation_topic = irrigation_topic
        self.moisture_topic = moisture_topic
        self.catalog_url = catalog_url
        self.greenhouse_id = greenhouse_id
        self.fields = {}

    def get_all_fields(self):
        try:
            catalog = requests.get(self.catalog_url).json()
            fields = {}
            for greenhouse in catalog["greenhouseList"]:
                if greenhouse["greenhouseID"] == self.greenhouse_id:
                    for zone in greenhouse["Zones"]:
                        fields[zone["ZoneID"]] = zone["Mois_threshold"]["low"]
            return fields
        except Exception as e:
            print(f"Error fetching catalog: {e}")
        return {}

    def notify(self, topic, payload):
        try:
            data = json.loads(payload.decode())
            zone_id = data["zone_id"]
            moisture_level = data["moisture"]
            
            if zone_id in self.fields:
                threshold = self.fields[zone_id]
                if moisture_level < threshold:
                    print(f"Zone {zone_id}, Moisture level: {moisture_level}, needs water!")
                    irrigation_command = {"zone_id": zone_id, "command": "ON"}
                    self.client.myPublish(self.irrigation_topic, irrigation_command)
                else:
                    print(f"Zone {zone_id}, Moisture level {moisture_level}%, does not need water.")
            else:
                print(f"Error: Zone {zone_id} not found in the catalog")
        except Exception as e:
            print(f"Error processing message: {e}")

    def start(self):
        self.fields = self.get_all_fields()
        self.client.start()
        self.client.mySubscribe(self.moisture_topic)
        print("Irrigation control ON")
        
    def stop(self):
        self.client.stop()
        print("Irrigation control OFF")
        
if __name__ == "__main__":
    with open("settings.json", "r") as f:
        config = json.load(f)

    irrigation_control = IrrigationControl(
        broker=config["broker"],
        port=config["port"], 
        moisture_topic=config["moisture_topic"],
        irrigation_topic=config["irrigation_topic"],
        catalog_url=config["catalog_url"],
        greenhouse_id=config["greenhouse_id"]
    )
    
    irrigation_control.start()
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        irrigation_control.stop()
        print("\nExit...")
