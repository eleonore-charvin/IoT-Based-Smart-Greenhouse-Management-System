import json
import time
import random
import requests
import uuid
from MyMQTT import MyMQTT

class MoistureSensor:

    def __init__(self, settings, greenhouse_id, zone_id):
        """
        Initialize MoistureSensor.
        
        Parameters:
            settings (dict): Settings of MoistureSensor.
            greenhouse_id (int): ID of the greenhouse in which the sensor is.
            zone°id (int): ID of the zone in which the sensor is.
        """

        self.settings = settings
        self.catalog_url = settings['catalogURL']
        self.device_info = settings['deviceInfo'].copy()

        self.device_id = f"MoistureSensor{zone_id}"
        self.device_info['deviceID'] = self.device_id
        self.moisture_level = random.randint(30, 60)
        self.irrigation_on = False

        self.mqtt_broker = settings['brokerIP']
        self.mqtt_port = settings['brokerPort']
        self.moisture_topic = settings['moistureTopic'].format(greenhouseID=greenhouse_id, zoneID=zone_id)
        self.irrigation_topic = settings['irrigationTopic'].format(greenhouseID=greenhouse_id, zoneID=zone_id)
        self.client_id = str(uuid.uuid1())
        self.client = MyMQTT(self.client_id, self.mqtt_broker, self.mqtt_port, self)

        self.zone_id = zone_id
        self.greenhouse_id = greenhouse_id

        self._message = {
            "v":"",
            "u":"%",
            "t":"",
            "n":"moisture"
        }

        #register the device to the catalog
        self.registerDevice()
        self.startSim()
    
    def registerDevice(self):
        """
        Register the device in the catalog.
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
        Update the device registration in the catalog.
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
        """
        Method called when a message is received.
        Retreive the command and set the irrigation status accordingly.
        
        Parameters:
            topic (str): topic of the message.
            payload (json): payload of the message.
        """
        try:
            message = json.loads(payload)
            self.irrigation_on = (message.get("command") == "ON")
        except Exception as e:
            print(f"[Greenhouse {self.greenhouse_id} zone {self.zone_id}] Error in message processing: {e}")
            
    def update_moisture(self):
        """
        Update the moisture level of the zone with respect to the irrigation status.
        """
        if self.irrigation_on:
            self.moisture_level = min(100, self.moisture_level + 10)
        else:
            self.moisture_level = max(0, self.moisture_level - random.randint(1, 3))
        return round(self.moisture_level, 2)

    def startSim(self):
        """
        Start the MQTT client and subscribe to the topic.
        """
        self.client.start()
        self.client.mySubscribe(self.irrigation_topic)

    def stopSim(self):
        """
        Stop the MQTT client.
        """
        self.client.stop()

    def publish(self):
        """
        Update the moisture level of the zone and publish it. 
        """
        moisture = self.update_moisture()
        message = self._message.copy()
        message["v"] = moisture
        message["t"] = time.time()
        self.client.myPublish(self.moisture_topic, message) # publish the moisture
        print(f"[Greenhouse {self.greenhouse_id} zone {self.zone_id}] Published moisture {moisture} %") # print the complete message

if __name__ == '__main__':
    with open('settings.json') as f:
        settings = json.load(f)

    try:
        #make a list of greenhouses from the catalog
        greenhouses = requests.get(f"{settings['catalogURL']}/greenhouses").json().get('greenhousesList', [])
    except Exception as e:
        print(f"Error in retreiving greenhouses: {e}")
        greenhouses = []

    sensors = []
    #for each greenhouse, take the relative zones and for each zone create a moisture sensor
    for greenhouse in greenhouses:
        greenhouse_id = greenhouse["greenhouseID"]
        for zone in greenhouse.get('zones', []):
            zone_id = zone['zoneID']
            sensor = MoistureSensor(settings, greenhouse_id, zone_id)
            sensors.append(sensor)

    print("Moisture sensors on.")

    try:
        while True:
            for sensor in sensors:
                time.sleep(15)
                sensor.publish()
                sensor.updateDevice()
            time.sleep(10)
    except KeyboardInterrupt:
        print("Sensors stopping...")
        for sensor in sensors:
            sensor.stopSim()
