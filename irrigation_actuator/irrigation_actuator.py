import json
import requests
import cherrypy
import time
import MyMQTT
import uuid

class IrrigationActuator:
    def __init__(self, settings, zoneID, greenhouseID):
        self.settings = settings
        self.clientID = str(uuid.uuid4())
        self.broker = settings["broker"]
        self.port = settings["port"]
        self.catalog_url = settings["catalogURL"]
        self.client = MyMQTT.MyMQTT(self.clientID, self.broker, self.port, self)
        self.irrigation_topic = settings["irrigationTopic"]
        self.device_info = settings['deviceInfo'].copy()
        self.deviceID = str(uuid.uuid4())
        self.device_info['deviceID'] = self.deviceID
        self.irrigation_status = "OFF"
        self.zone_id = zoneID
        self.greenhouse_id = greenhouseID
        self.start()
        self.registerDevice()

    def registerDevice(self):
        """
        Register the device in the catalog
        """  
        try:   
            actualTime = time.time()
            self.device_info["lastUpdate"] = actualTime
            params = {"zoneID": self.zone_id}
            response = requests.post(f"{self.catalog_url}/devices", params=params, data=json.dumps(self.device_info))
            response.raise_for_status()
        except cherrypy.HTTPError as e: # Catching HTTPError
            print(f"Error raised by catalog while registering device: {e.status} - {e.args[0]}")
        except Exception as e:
            print(f"Error registering device in the catalog: {e}")

    def updateDevice(self):
        """
        Update the device registration in the catalog
        """
        try:
            actualTime = time.time()
            self.device_info["lastUpdate"] = actualTime
            response = requests.put(f"{self.catalog_url}/devices", data=json.dumps(self.device_info))
            response.raise_for_status()
        except cherrypy.HTTPError as e: # Catching HTTPError
            print(f"Error raised by catalog while registering device: {e.status} - {e.args[0]}")
        except Exception as e:
            print(f"Error registering device in the catalog: {e}")
    
    def notify(self, topic, payload):
        try:
            message = json.loads(payload)
            zone_id = topic.split("/")[-2]
            greenhouse_id = topic.split("/")[-2]
            command = message.get("command")
            
            if command == "ON":
                print(f"Irrigation started for greenhouse {greenhouse_id} zone {zone_id}")
                self.irrigation_status = "ON"
            elif command == "OFF":
                print(f"Irrigation stopped for greenhouse {greenhouse_id} zone {zone_id}")
                self.irrigation_status = "OFF"
            else:
                print(f"Invalid command received: {command}")
        except (ValueError, KeyError) as e:
            print(f"Error processing message: {e}")

    def start(self):
        self.client.start()
        self.client.mySubscribe(self.irrigation_topic)

    def stop(self):
        self.client.stop()

if __name__ == "__main__":
    with open("settings.json", "r") as f:
        config = json.load(f)
    try:
        greenhouses = requests.get(f"{config['catalogURL']}/greenhouses").json().get('greenhousesList', [])
    except Exception as e:
        print(f"Error in retreiving greenhouses: {e}")
        greenhouses = []

    actuators = []
    for greenhouse in greenhouses:
        greenhouse_id = greenhouse["greenhouseID"]
        for zone in greenhouse.get("zones", []):
            zone_id = zone["zoneID"]
            actuator = IrrigationActuator(config, greenhouse_id, zone_id)
            actuators.append(actuator)
    
    print("Irrigation actuators on.")

    try:
        while True:
            time.sleep(10)
            for actuator in actuators:
                actuator.updateDevice()

    except KeyboardInterrupt:
        print("Stopping Irrigation Actuators...")
        for actuator in actuators:
            actuator.stop()
