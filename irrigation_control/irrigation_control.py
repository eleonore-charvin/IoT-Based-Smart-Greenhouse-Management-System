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
        self.broker = settings["brokerIP"]
        self.port = settings["brokerPort"]
        self.serviceInfo = settings["serviceInfo"]
        self.client = MyMQTT.MyMQTT(self.client_id, self.broker, self.port, self)
        self.irrigation_topic = settings["irrigationTopic"]
        self.moisture_topic = settings["moistureTopic"]
        self.catalog_url = settings["catalogURL"]
        self.start()
        self.registerService()

    def get_zone_threshold(self, greenhouseID, zoneID):
        try:
            params = {"zoneID": zoneID}
            response = requests.get(f"{self.catalog_url}/zones", params=params).json()
            zone = response.get('zonesList', [])[0]
            threshold = zone.get('moistureThreshold', 0)
            print(f"[Greenhouse {greenhouseID} zone {zoneID}] Moisture threshold {threshold} %")
            return threshold
        except Exception as e:
            print(f"[Greenhouse {greenhouseID} zone {zoneID}] Error fetching catalog: {e}")
        return 0
    
    def registerService(self):
        """
        Register the service in the catalog
        """
        try:
            actualTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.serviceInfo["lastUpdate"] = actualTime
            response = requests.post(f"{self.catalog_url}/services", data=json.dumps(self.serviceInfo))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while registering service: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            print(f"Error registering service in the catalog: {e}")
    
    def updateService(self):
        """
        Update the service registration in the catalog
        """
        try:
            actualTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.serviceInfo["lastUpdate"] = actualTime
            response = requests.put(f"{self.catalog_url}/services", data=json.dumps(self.serviceInfo))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while updating service: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            print(f"Error updating service in the catalog: {e}")

    def notify(self, topic, payload):
        try:
            data = json.loads(payload)
            greenhouse_id = topic.split("/")[-3]
            zone_id = topic.split("/")[-2]
            moisture_level = data["v"]
            
            # check if the moisture level is greater or lower than the treshold and put ON/OFF the irrigation command
            threshold = self.get_zone_threshold(greenhouse_id, zone_id)
            if moisture_level < threshold:
                print(f"[Greenhouse {greenhouse_id} zone {zone_id}] Moisture level {moisture_level} %, needs water!")
                irrigation_command = {"command": "ON"}
                self.client.myPublish(self.irrigation_topic.format(greenhouseID=greenhouse_id, zoneID=zone_id), irrigation_command)
            else:
                print(f"[Greenhouse {greenhouse_id} zone {zone_id}] Moisture level {moisture_level} %, does not need water.")
                irrigation_command = {"command": "OFF"}
                self.client.myPublish(self.irrigation_topic.format(greenhouseID=greenhouse_id, zoneID=zone_id), irrigation_command)
        
        except Exception as e:
            print(f"[Greenhouse {greenhouse_id} zone {zone_id}] Error processing message: {e}")

    def start(self):
        self.client.start()
        self.client.mySubscribe(self.moisture_topic)
        print("Irrigation control ON")

    def stop(self):
        self.client.stop()
        print("Irrigation control OFF")

if __name__ == "__main__":
    with open("settings.json", "r") as f:
        config = json.load(f)

    irrigation_control = IrrigationControl(config)

    try:
        while True:
            time.sleep(10)
            irrigation_control.updateService()
    except KeyboardInterrupt:
        irrigation_control.stop()
        print("\nExit...")
