import json
import requests
import MyMQTT
import cherrypy
import time

class IrrigationControl:
    def __init__(self, broker, port, moisture_topic, irrigation_topic, catalog_url):
        self.client = MyMQTT("IrrigationControl", broker, port, self)
        self.client.start()
        self.client.mySubscribe(moisture_topic)
        self.irrigation_topic = irrigation_topic
        self.catalog_url = catalog_url
        self.fields = self.get_all_fields()

    def get_all_fields(self):
        try:
            #get request for the catalog, in order to get the list of fields
            catalog = requests.get(self.catalog_url).json()
            fields = {}
            '''the dictionary will be in the form
                1:30        field 1 treshold 30
                2:40        ...
                ...
            '''
            for zone in catalog["GreenHouse"]["Zones"]:
                fields[zone["ZoneID"]] = zone["Mois_threshold"]["low"]
            return fields
        except Exception as e:
            print(f"Error:{e}")
        return fields

    def notify(self, topic, payload):
        try:
            #load the message to get the zone to control and its moisture level
            data = json.loads(payload.decode())
            zone_id = data["zone_id"]
            moisture_level = data["moisture"]
            
            #start the control logic
            if zone_id in self.fields:
                threshold = self.fields[zone_id]
                #check if the level is lower than the treshold
                if moisture_level < threshold:
                    print(f"Zone {zone_id}, Moisture level: {moisture_level}, needs water!")
                    irrigation_command = {"zone_id": zone_id, "command": "ON"}
                    self.client.myPublish(self.irrigation_topic, irrigation_command)
                else:
                    print(f"Zone {zone_id}, Moisture level {moisture_level}%, does not need water.")
            else:
                print(f"Error: zona {zone_id} not found in the catalog")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    with open("settings.json", "r") as f:
        config = json.load(f)

    irrigation_control = IrrigationControl(
        broker=config["broker"],
        port=config["port"], 
        moisture_topic= config["moisture_topic"],
        irrigation_topic= config["irrigation_topic"],
        catalog_url = config["catalog_url"]
    )
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        irrigation_control.stop()
        cherrypy.engine.block()
        print("\n Exit...")
