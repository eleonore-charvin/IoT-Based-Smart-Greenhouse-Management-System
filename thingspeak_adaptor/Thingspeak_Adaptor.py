import requests
import json
from MyMQTT import *
import random
import time
import uuid

class Thingspeak_Adaptor:

    def __init__(self, settings):
        """
        Initialize Thingspeak_Adaptor.
        
        Parameters:
            settings (dict): Settings of Thingspeak_Adaptor.
        """
        # Load the settings
        self.settings = settings
        self.catalogURL = settings["catalogURL"]
        self.serviceInfo = settings['serviceInfo']
        self.baseURL = self.settings["thingspeakURL"]
        self.userAPIKey = self.settings["userAPIKey"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.topic = self.settings["mqttTopic"] + "/#"

        self.heatingToInt = {"heating_on": 1, "cooling_on": -1, "off": 0}
        self.irrigationToInt = {"ON": 1, "OFF": 0}

        # Create an MQTT client
        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self) # uuid is to generate a random string for the client id
        # Start it
        self.mqttClient.start()
        # Subscribe to the topic
        self.mqttClient.mySubscribe(self.topic)
    
    def registerService(self):
        """
        Register the service in the catalog
        """
        actualTime = time.time()
        self.serviceInfo["lastUpdate"] = actualTime
        requests.post(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
    
    def updateService(self):
        """
        Update the service registration in the catalog
        """
        actualTime = time.time()
        self.serviceInfo["lastUpdate"] = actualTime
        requests.put(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))

    def stop(self):
        """
        Stop the MQTT client
        """
        self.mqttClient.stop()
    
    def notify(self, topic, payload):
        """
        Method called when a message is received.
        
        Parameters:
            topic (str): topic of the message.
            payload (json): payload of the message.
        """
        # Structure of the message:
        # {'bn':f'group06/SmartGreenhouse/{greenhouseID}/{zoneID}','e':[{'n':'humidity','v':'', 't':'','u':'%'}]}

        # Decode the message
        message_decoded = json.loads(payload)
        message_value = message_decoded["e"][0]["v"]
        decide_measurement = message_decoded["e"][0]["n"]
        greenhouseID = int(message_decoded["bn"].split("/")[-2])
        zoneID = int(message_decoded["bn"].split("/")[-1])
        error = False

        # Match the measurement with the field
        # In Thingspeak website, we decided that:
        # - field 1 = temperature
        if decide_measurement == "temperature":
            print("\n \n Temperature Message")
            field_number = 1

        # - field 2 = heating and cooling status
        elif decide_measurement == "heating_cooling":
            print("\n \n Heating and cooling Message")
            field_number = 2
            message_value = self.heatingToInt[message_value] # convert the value to the corresponding integer

        # - field 3 = sum of irrigation status
        elif decide_measurement == "irrigation":
            print("\n \n Irrigation Message")
            field_number = 3
            message_value = self.irrigationToInt[message_value] # convert the value to the corresponding integer

        # - field 4 = moisture of zone 1
        # - field 5 = moisture of zone 2
        # ...
        # - field 8 = moisture of zone 5 (if it exists)
        elif decide_measurement == "moisture":
            print("\n \n Moisture Message")
            if not ((zoneID > 0) and (zoneID < 6)):
                raise ValueError(f"Invalid zoneID: {zoneID}")
            else:
                field_number = zoneID + 3

        else: 
            error = True

        if error:
            print("Error")
        else:
            print(message_decoded)

            # Get the write API key of the channel corresponding to the greenhouse
            channel_write_api_key = self.getGreenhouseWriteAPIKey(greenhouseID)

            # Upload the value on Thingspeak
            self.uploadThingspeak(channel_write_api_key=channel_write_api_key, field_number=field_number, field_value=message_value)
    
    def getGreenhouseWriteAPIKey(self, greenhouseID):
        """
        Get the write API key of the channel corresponding to the greenhouse.
        If there is no channel associated with this greenhouse, a new one is created.

        Parameters:
            greenhouseID (int): ID of the greenhouse.

        Returns:
            str: write API key of the channel.
        """
        # Get the greenhouse from the catalog
        response = requests.get(f"{self.catalogURL}/getGeenhouse?greenhouseID={greenhouseID}")
        greenhouse = response.json()
        
        # If the greenhouse has a channel, get its write API key
        if "thingspeakChannel" in greenhouse.keys():
            thingspeakInfo = greenhouse["thingspeakChannel"]
            channel_write_api_key = thingspeakInfo["channelWriteAPIkey"]
        
        # Else, creayte a new channel and get its write API key
        else:
            channel_write_api_key = self.createGreenhouseChannel(greenhouse)
        return channel_write_api_key
        
    def createGreenhouseChannel(self, greenhouse):
        """
        Create a new channel for the greenhouse and return its write API key.

        Parameters:
            greenhouse (dict): dictionnary containing the information on the greenhouse.

        Returns:
            str: the write API key of the created channel.
        """
        # Define the URL
        urlToSend = f"{self.baseURL}channels.json"
        name = f"Greenhouse {greenhouse["greenhouseID"]}"
        params = {
            "api_key": self.userAPIKey,
            "name": name,
            "field1": "Temperature",
            "field2": "Heating and cooling",
            "field3": "Total irrigation",
            "field4": "Moisture Zone 1",
            "field5": "Moisture Zone 2",
            "field6": "Moisture Zone 3",
            "field7": "Moisture Zone 4",
            "field8": "Moisture Zone 5"
        }

        # Create the channel
        response = requests.post(urlToSend, data=json.dumps(params))

        if response.status_code == 200:
            channel_info = response.json()

            # Get the channel information from the response
            channel_id = channel_info["id"]
            channel_read_api_key = ""
            channel_write_api_key = ""
            for api_key in channel_info["api_keys"]:
                if api_key["write_flag"] == True:
                    channel_write_api_key = api_key["api_key"]
                else:
                    channel_read_api_key = api_key["api_key"]

            # Update the device in the catalog with the channel information
            thingspeakInfo = {
                "channelID": channel_id,
                "channelWriteAPIkey": channel_write_api_key,
                "channelReadAPIkey": channel_read_api_key
            }
            greenhouse["thingspeakInfo"] = thingspeakInfo
            requests.put(f"{self.catalogURL}/updateGreenhouse", data=json.dumps(greenhouse))
            
            print(f"New channel created: {name}")
            return channel_write_api_key

        else:
            print(f"Failed to create channel {name}: {response.text}")
        

    def uploadThingspeak(self, channel_write_api_key, field_number, field_value):
        """
        Upload a value in a field on Thingspeak.
        
        Parameters:
            channel_write_api_key (str): write API key of the channel.
            field_number (int): number of the field.
            field_value (float): value to upload.
        """
        # Define the URL
        urlToSend = f"{self.baseURL}update?api_key={channel_write_api_key}&field{field_number}={field_value}"
        
        # Ensure the update goes through
        status = 0
        while status == 0:
            response = requests.get(urlToSend)
            status = response.text
            print(f"Upload failed, retrying")
        print(f"Upload success: {status}")

if __name__ == "__main__":
    # Create an instance of Thingspeak_Adaptor
    settings = json.load(open("settings.json"))
    ts_adaptor = Thingspeak_Adaptor(settings)
    print("Starting Thingspeak Adaptor...")

    # Register it in the catalog
    ts_adaptor.registerService()

    try:
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            
            # Every 40s
            if counter == 20:
                # Update the service registration
                ts_adaptor.updateService()
                counter = 0

    except KeyboardInterrupt:
        # Graceful shutdown
        ts_adaptor.stop()
        print("Thingspeak Adaptor Stopped")