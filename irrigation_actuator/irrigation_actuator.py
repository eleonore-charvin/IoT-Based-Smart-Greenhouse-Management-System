import json
import requests
import time
import MyMQTT
import uuid

class IrrigationActuator:
    def __init__(self, settings, greenhouseID, zoneID):
        self.settings = settings
        self.clientID = str(uuid.uuid4())
        self.broker = settings["brokerIP"]
        self.port = settings["brokerPort"]
        self.catalog_url = settings["catalogURL"]
        self.client = MyMQTT.MyMQTT(self.clientID, self.broker, self.port, self)
        self.irrigation_topic = settings["irrigationTopic"].format(greenhouseID=greenhouseID, zoneID=zoneID)
        self.device_info = settings['deviceInfo'].copy()
        self.deviceID = f"IrrigationActuator{zoneID}" 
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
            actualTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.device_info["lastUpdate"] = actualTime
            params = {"zoneID": self.zone_id}
            response = requests.post(f"{self.catalog_url}/devices", params=params, data=json.dumps(self.device_info))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"[Greenhouse {self.greenhouse_id} zone {self.zone_id}] Error raised by catalog while registering device: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            print(f"[Greenhouse {self.greenhouse_id} zone {self.zone_id}] Error registering device in the catalog: {e}")

    def updateDevice(self):
        """
        Update the device registration in the catalog
        """
        try:
            actualTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.device_info["lastUpdate"] = actualTime
            response = requests.put(f"{self.catalog_url}/devices", data=json.dumps(self.device_info))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"[Greenhouse {self.greenhouse_id} zone {self.zone_id}] Error raised by catalog while registering device: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            print(f"[Greenhouse {self.greenhouse_id} zone {self.zone_id}] Error registering device in the catalog: {e}")
    
    def notify(self, topic, payload):
        try:
            message = json.loads(payload)
            zone_id = topic.split("/")[-2]
            greenhouse_id = topic.split("/")[-2]
            command = message.get("command")
            
            if command == "ON":
                print(f"[Greenhouse {greenhouse_id} zone {zone_id}] Irrigation started")
                self.irrigation_status = "ON"
            elif command == "OFF":
                print(f"[Greenhouse {greenhouse_id} zone {zone_id}] Irrigation stopped")
                self.irrigation_status = "OFF"
            else:
                print(f"[Greenhouse {greenhouse_id} zone {zone_id}] Invalid command received: {command}")
        except (ValueError, KeyError) as e:
            print(f"[Greenhouse {greenhouse_id} zone {zone_id}] Error processing message: {e}")

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
