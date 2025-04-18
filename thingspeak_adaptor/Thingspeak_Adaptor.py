import requests
import cherrypy
import json
from MyMQTT import *
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

        # Decode the message
        try:
            message_decoded = json.loads(payload)
            message_value = message_decoded["e"][0]["v"]
            decide_measurement = message_decoded["e"][0]["n"]
            greenhouseID = int(topic.split("/")[-2])
            zoneID = int(topic.split("/")[-1])
        except json.JSONDecodeError:
            print(f"Error decoding JSON message")
            return
        except ValueError:
            print((f"Invalid greenhouseID or zoneID: {topic.split("/")[-2]}, {topic.split("/")[-1]}"))

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

        # - fields 4-8 = moisture of one zone
        # the matching between the field number and the zone id is made in the catalog
        elif decide_measurement == "moisture":
            print("\n \n Moisture Message")

            # Get the field id of the zone from the catalog
            try:
                params = {"zoneID": zoneID}
                response = requests.get(f"{self.catalogURL}/zones", params=params)
                zone = response.json().get("zonesList", [])[0]
                field_number = zone.get("thingspeakFieldID", -1)
            except json.JSONDecodeError:
                    print(f"Error decoding JSON response for zone {zoneID}")
            except cherrypy.HTTPError as e: # Catching HTTPError
                print(f"Error raised by catalog while fetching zone {zoneID}: {e.status} - {e.args[0]}")
            except Exception as e:
                print(f"Error fetching fetching zone {zoneID} from the catalog: {e}")

            if field_number == -1:
                print(f"No field for zone {zoneID}")
                error = True

        else: 
            error = True

        if error:
            print(f"Unrecognised measurement type: {decide_measurement} zone {zoneID}")
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
        try:
            params = {"greenhouseID": greenhouseID}
            response = requests.get(f"{self.catalogURL}/greenhouses", params=params)
            greenhouse = response.json().get("greenhousesList", [])[0]
        except json.JSONDecodeError:
            print(f"Error decoding JSON response for greenhouse {greenhouseID}")
            return ""
        except cherrypy.HTTPError as e: # Catching HTTPError
            print(f"Error raised by catalog while fetching greenhouse {greenhouseID}: {e.status} - {e.args[0]}")
            return ""
        except Exception as e:
            print(f"Error fetching greenhouse {greenhouseID} from the catalog: {e}")
            return ""
        
        # If the greenhouse has a channel, get its write API key
        if "thingspeakChannel" in greenhouse.keys():
            thingspeakInfo = greenhouse.get("thingspeakChannel", "")
            channel_write_api_key = thingspeakInfo.get("channelWriteAPIkey", "")
        
        # Else, create a new channel and get its write API key
        else:
            print(f"No existing channel for greenhouse {greenhouse.get("greenhouseID", "")}, creating one")
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
        greenhouseID = greenhouse.get("greenhouseID", "")

        # Map each zone of the greenhouse to a field
        fieldToZone = {}
        fields_number  = 0
        for zone in greenhouse["zones"]:
            if fields_number < 5:
                fieldToZone[fields_number] = zone["zoneID"]
                fields_number += 1
            else:
                print(f"Only fields for the 5 1st zones were created\n{len(greenhouse["zones"]) - 5} zones won't be updated on Thingspeak")
                break

        name = f"Greenhouse {greenhouseID}"
        params = {
            "api_key": self.userAPIKey,
            "name": name,
            "field1": "Temperature",
            "field2": "Heating and cooling",
            "field3": "Total irrigation",
            "field4": f"Moisture Zone {fields_number[0]}",
            "field5": f"Moisture Zone {fields_number[1]}",
            "field6": f"Moisture Zone {fields_number[2]}",
            "field7": f"Moisture Zone {fields_number[3]}",
            "field8": f"Moisture Zone {fields_number[4]}"
        }

        # Create the channel
        response = requests.post(urlToSend, data=json.dumps(params))

        if response.status_code == 200:

            try:
                channel_info = response.json()
            except json.JSONDecodeError:
                print("Error decoding JSON response from Thingspeak")
                return ""

            # Get the channel information from the response
            channel_id = channel_info.get("id", "")
            channel_read_api_key = ""
            channel_write_api_key = ""
            for api_key in channel_info.get("api_keys", []):
                if api_key.get("write_flag", False) == True:
                    channel_write_api_key = api_key.get("api_key", "")
                else:
                    channel_read_api_key = api_key.get("api_key", "")

            # Update the greenhouse in the catalog with the channel information
            thingspeakInfo = {
                "channelID": channel_id,
                "channelWriteAPIkey": channel_write_api_key,
                "channelReadAPIkey": channel_read_api_key
            }
            greenhouse["thingspeakInfo"] = thingspeakInfo
            try:
                requests.put(f"{self.catalogURL}/greenhouses", data=json.dumps(greenhouse))
            except cherrypy.HTTPError as e: # Catching HTTPError
                print(f"Error raised by catalog while updating greenhouse {greenhouseID}: {e.status} - {e.args[0]}")
                return ""
            except Exception as e:
                print(f"Error fetching updating greenhouse {greenhouseID} from the catalog: {e}")
                return ""
            
            # Update each zone with its corresponding field id in the catalog
            for field in fieldToZone.keys():
                zoneID = fieldToZone[field]

                # Get the zone from the catalog
                try:
                    params = {"zoneID": zoneID}
                    response = requests.get(f"{self.catalogURL}/zones", params=params)
                    zone = response.json().get("zonesList", [])[0]
                except json.JSONDecodeError:
                    print(f"Error decoding JSON response for zone {zoneID}")
                except cherrypy.HTTPError as e: # Catching HTTPError
                    print(f"Error raised by catalog while fetching zone {zoneID}: {e.status} - {e.args[0]}")
                except Exception as e:
                    print(f"Error fetching fetching zone {zoneID} from the catalog: {e}")
                    
                # Add the field id
                zone["thingspeakFieldID"] = field

                # Update the zone in the catalog
                try:
                    params = {"greenhouseID": greenhouseID}
                    response = requests.put(f"{self.catalogURL}/zones", params=params, data=json.dumps(zone))
                except cherrypy.HTTPError as e: # Catching HTTPError
                    print(f"Error raised by catalog while updating zone {zoneID}: {e.status} - {e.args[0]}")
                
                except Exception as e:
                    print(f"Error fetching updating zone {zoneID} from the catalog: {e}")
                
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