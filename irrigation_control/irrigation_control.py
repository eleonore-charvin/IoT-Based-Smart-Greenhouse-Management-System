import json
import requests
import MyMQTT
import cherrypy
import time
import uuid

class IrrigationControl:
    def __init__(self, settings):
        self.client_id = str(uuid.uuid1())
        self.settings = settings
        self.broker = settings["broker"]
        self.port = settings["port"]
        self.serviceInfo = settings["serviceInfo"]
        self.client = MyMQTT.MyMQTT(self.client_id, self.broker, self.port, self)
        self.irrigation_topic = settings["irrigationTopic"]
        self.moisture_topic = settings["moistureTopic"]
        self.catalog_url = settings["catalogURL"]
        self.fields = {}

    def get_all_fields(self):
        try:
            greenhouses = requests.get(f"{self.catalog_url}/greenhouses").json().get('greenhousesList', [])
            fields = {}
            for greenhouse in greenhouses:
                for zone in greenhouse.get("zones", []):
                    fields[zone["zoneID"]] = zone["Mois_threshold"]["low"]
            return fields
        except Exception as e:
            print(f"Error fetching catalog: {e}")
        return {}
    
    def registerService(self):
        """
        Register the service in the catalog
        """
        try:
            actualTime = time.time()
            self.serviceInfo["lastUpdate"] = actualTime
            requests.post(f"{self.catalog_url}/services", data=json.dumps(self.serviceInfo))
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
            requests.put(f"{self.catalog_url}/services", data=json.dumps(self.serviceInfo))
        except cherrypy.HTTPError as e: # Catching HTTPError
            print(f"Error raised by catalog while updating service: {e.status} - {e.args[0]}")
        except Exception as e:
            print(f"Error updating service in the catalog: {e}")

    
    def notify(self, topic, payload):
        try:
            data = json.loads(payload)
            greenhouse_id = topic.split("/")[-3]
            zone_id = topic.split("/")[-2]
            moisture_level = data["e"][0]["v"]
            ###### replace this by call to catalog function
            self.fields = self.get_all_fields() #takes the fields every times
            
            #check if the moisture level is greater or lower than the treshold and put ON/OFF the irrigation command
            if zone_id in self.fields:
                threshold = self.fields[zone_id]
                if moisture_level < threshold:
                    print(f"Greenhouse {greenhouse_id} zone {zone_id}, Moisture level: {moisture_level}, needs water!")
                    irrigation_command = {"command": "ON"}
                    self.client.myPublish(self.irrigation_topic.format(greenhouseID=greenhouse_id, zoneID=zone_id), json.dumps(irrigation_command))
                else:
                    print(f"Greenhouse {greenhouse_id} zone {zone_id}, Moisture level {moisture_level}%, does not need water.")
                    irrigation_command = {"command": "OFF"}
                    self.client.myPublish(self.irrigation_topic.format(greenhouseID=greenhouse_id, zoneID=zone_id), json.dumps(irrigation_command))
                
            else:
                print(f"Error: Zone {zone_id} not found in the catalog")
        except Exception as e:
            print(f"Error processing message: {e}")

    def start(self):
        self.client.start() #takes the fields at the beginning of simulation
        self.client.mySubscribe(self.moisture_topic)
        print("Irrigation control ON")

    def stop(self):
        self.client.stop()
        print("Irrigation control OFF")

if __name__ == "__main__":
    with open("settings.json", "r") as f:
        config = json.load(f)

    irrigation_control = IrrigationControl(config)
    irrigation_control.registerService()

    irrigation_control.start()

    try:
        while True:
            time.sleep(10)
            irrigation_control.updateService()
    except KeyboardInterrupt:
        irrigation_control.stop()
        print("\nExit...")
