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
        :param settings: Settings of hingspeak_Adaptor 
        """
        # Load the settings
        self.settings = settings
        self.catalogURL = settings["catalogURL"]
        self.serviceInfo = settings['serviceInfo']
        self.baseURL = self.settings["ThingspeakURL"]
        self.channelWriteAPIkey = self.settings["ChannelWriteAPIkey"]
        self.channelReadAPIkey = self.settings["ChannelReadAPIKey"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.topic = self.settings["mqttTopic"] + "/#"

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
        :param topic: topic of the message
        :param payload: payload of he message
        """
        # Structure of the message:
        # {'bn':f'SensorREST_MQTT_{self.deviceID}','e':[{'n':'humidity','v':'', 't':'','u':'%'}]}

        # Decode the message
        message_decoded = json.loads(payload)
        message_value = message_decoded["e"][0]["v"]
        decide_measurement = message_decoded["e"][0]["n"]
        error = False

        # Match the measurement with the field
        # In Thingspeak website, we decided that:
        # - field 1 = temperature
        # - field 2 = moisture
        if decide_measurement == "temperature":
            print("\n \n Temperature Message")
            field_number = 1
        elif decide_measurement == "moisture":
            print("\n \n Humidity Message")
            field_number = 2
        else: 
            error = True

        if error:
            print("Error")
        else:
            print(message_decoded)
            # Upload the value on Thingspeak
            self.uploadThingspeak(field_number=field_number, field_value=message_value)
    
    def uploadThingspeak(self, field_number, field_value):
        """
        Upload a value in a field on Thingspeak.
        :param field_number: number of the field
        :param field_value: value to upload
        """
        # Define the URL
        urlToSend = f"{self.baseURL}{self.channelWriteAPIkey}&field{field_number}={field_value}"
        
        # While loop to make sure that it has been updated
        status = 0
        while status == 0:
            r = requests.get(urlToSend)
            status = r.text
            print(status) # prints if it has been updated or not -> you need to make sure it has been updated 

if __name__ == "__main__":
    # Create an instance of Thingspeak_Adaptor
    settings = json.load(open("settings.json"))
    ts_adaptor = Thingspeak_Adaptor(settings)
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