import requests
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
        self.topic = self.settings["mqttTopic"] + "#"

        self.heatingToInt = {"heating": 1, "cooling": -1, "off": 0}
        self.irrigationToInt = {"ON": 1, "OFF": 0}
        self.__params = {
            "field1": "Temperature",
            "field2": "Heating and cooling",
            "field3": "Total irrigation"
        }
        self.maxZoneFields = 5

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
            actualTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.serviceInfo["lastUpdate"] = actualTime
            response = requests.post(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
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
            response = requests.put(f"{self.catalogURL}/services", data=json.dumps(self.serviceInfo))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while updating service: {e.response.status_code} - {e.args[0]}")
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
            message_value = message_decoded["v"] if "v" in message_decoded.keys() else message_decoded["command"]
            decide_measurement = topic.split("/")[-1]
            greenhouseID = int(topic.split("/")[2])
            zoneID = int(topic.split("/")[3]) if len(topic.split("/")) > 4 else -1
        except json.JSONDecodeError:
            print(f"Error decoding JSON message")
            return
        except ValueError:
            print((f"Invalid greenhouseID or zoneID: {topic.split("/")[2]}, {topic.split("/")[3]}"))
            return

        # Get the write API key of the channel corresponding to the greenhouse
        channel_write_api_key, channelID, numberZoneFields = self.getGreenhouseWriteAPIKey(greenhouseID)

        # Check if we need to create new fields for the zones
        # i.e. if there are more zones than numberZoneFields
        try:
            # Get the zone ids of the greenhouse from the catalog
            params = {"greenhouseID": greenhouseID}
            response = requests.get(f"{self.catalogURL}/zonesID", params=params)
            response.raise_for_status()
            zones = response.json().get("zones", [])

        except json.JSONDecodeError:
            print(f"Error decoding JSON response for greenhouse {greenhouseID}")
            return
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while fetching zones id of greenhouse {greenhouseID}: {e.response.status_code} - {e.args[0]}")
            return
        except Exception as e:
            print(f"Error fetching zones id of greenhouse {greenhouseID} from the catalog: {e}")
            return
        
        # If it is possible to create new fields for the zones, add them
        if ((len(zones) > numberZoneFields) and (numberZoneFields < self.maxZoneFields)):
            print(f"New zones have been added to greenhouse {greenhouseID}, creating new fields for them in the channel")
            self.addZoneFields(channelID, greenhouseID)
            
        error = False

        # Match the measurement with the field
        # In Thingspeak website, we decided that:
        # - field 1 = temperature
        if decide_measurement == "temperature":
            print(f"\n \n[Greenhouse {greenhouseID}] Temperature Message")
            field_number = 1

        # - field 2 = heating and cooling status
        elif decide_measurement == "heatingcooling":
            print(f"\n \n[Greenhouse {greenhouseID}] Heating and cooling Message")
            field_number = 2
            message_value = self.heatingToInt[message_value] # convert the value to the corresponding integer

        # - field 3 = sum of irrigation status
        elif decide_measurement == "irrigation":
            print(f"\n \n[Greenhouse {greenhouseID} zone {zoneID}] Irrigation Message")
            field_number = 3
            message_value = self.irrigationToInt[message_value] # convert the value to the corresponding integer

        # - fields 4-8 = moisture of one zone
        # the matching between the field number and the zone id is made in the catalog
        elif decide_measurement == "moisture":
            print(f"\n \n[Greenhouse {greenhouseID} zone {zoneID}] Moisture Message")

            # Get the field id of the zone from the catalog
            try:
                params = {"zoneID": zoneID}
                response = requests.get(f"{self.catalogURL}/zones", params=params)
                response.raise_for_status()
                zone = response.json().get("zonesList", [])[0]
                field_number = zone.get("thingspeakFieldID", -1)
                print(f"Uploading zone {zoneID} on field {field_number}")
            except json.JSONDecodeError:
                    print(f"Error decoding JSON response for zone {zoneID}")
                    return
            except requests.exceptions.HTTPError as e:
                print(f"Error raised by catalog while fetching zone {zoneID}: {e.response.status_code} - {e.args[0]}")
                return
            except Exception as e:
                print(f"Error fetching fetching zone {zoneID} from the catalog: {e}")
                return

            if field_number == -1:
                print(f"No field for zone {zoneID}")
                error = True

        else: 
            error = True

        if error:
            print(f"Unrecognised measurement type: {decide_measurement} zone {zoneID}")
        else:
            print(message_decoded)

            # Upload the value on Thingspeak
            self.uploadThingspeak(channel_write_api_key=channel_write_api_key, field_number=field_number, field_value=message_value)
    
    def getGreenhouseWriteAPIKey(self, greenhouseID):
        """
        Get the write API key of the channel corresponding to the greenhouse.
        If there is no channel associated with this greenhouse, a new one is created.

        Parameters:
            greenhouseID (int): ID of the greenhouse.

        Returns:
            channel_write_api_key (str): write API key of the channel.
            channelID (str): ID of the channel.
            numberZoneFields (int): number of fields of the channel created for the zones of the greenhouse.
        """

        # Get the greenhouse from the catalog
        try:
            params = {"greenhouseID": greenhouseID}
            response = requests.get(f"{self.catalogURL}/greenhouses", params=params)
            response.raise_for_status()
            greenhouse = response.json().get("greenhousesList", [])[0]
        except json.JSONDecodeError:
            print(f"Error decoding JSON response for greenhouse {greenhouseID}")
            return "", 0, 0
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while fetching greenhouse {greenhouseID}: {e.response.status_code} - {e.args[0]}")
            return "", 0, 0
        except Exception as e:
            print(f"Error fetching greenhouse {greenhouseID} from the catalog: {e}")
            return "", 0, 0
        
        # If the greenhouse has a channel, get its write API key
        if "thingspeakChannel" in greenhouse.keys():
            thingspeakInfo = greenhouse.get("thingspeakChannel", {})
            channel_write_api_key = thingspeakInfo.get("channelWriteAPIkey", "")
            channelID = thingspeakInfo.get("channelID", 0)
            numberZoneFields = thingspeakInfo.get("numberZoneFields", 0)
        
        # Else, create a new channel and get its write API key
        else:
            print(f"No existing channel for greenhouse {greenhouse.get("greenhouseID", "")}, creating one")
            channel_write_api_key, channelID, numberZoneFields = self.createGreenhouseChannel(greenhouse)
        return channel_write_api_key, channelID, numberZoneFields
        
    def createGreenhouseChannel(self, greenhouse):
        """
        Create a new channel for the greenhouse and return its write API key.

        Parameters:
            greenhouse (dict): dictionnary containing the information on the greenhouse.

        Returns:
            channel_write_api_key (str): write API key of the channel.
            channelID (str): ID of the channel.
            numberZoneFields (int): number of fields of the channel created for the zones of the greenhouse.
        """
        # Define the URL
        urlToSend = f"{self.baseURL}channels.json"
        greenhouseID = greenhouse.get("greenhouseID", "")

        # Map each zone of the greenhouse to a field
        fieldToZone = {}
        fields_number = 0
        for zone in greenhouse["zones"]:
            if fields_number < self.maxZoneFields:
                fieldToZone[fields_number] = zone["zoneID"]
                fields_number += 1
            else:
                print(f"Only fields for the 5 first zones have been created\n{len(greenhouse["zones"]) - self.maxZoneFields} zones will not be updated on Thingspeak")
                break

        name = f"Greenhouse {greenhouseID}"
        params = self.__params.copy()
        params["name"] = name
        
        numberZoneFields = min(len(fieldToZone), self.maxZoneFields)
        for i in range(numberZoneFields):
            params[f"field{4 + i}"] = f"Moisture Zone {fieldToZone[i]}"
        headers = {
            "Content-Type": "application/json",
            "X-THINGSPEAKAPIKEY": self.userAPIKey
        }

        # Create the channel
        response = requests.post(urlToSend, headers=headers, data=json.dumps(params))

        if response.status_code == 200:

            try:
                channel_info = response.json()
            except json.JSONDecodeError:
                print("Error decoding JSON response from Thingspeak")
                return "", 0, 0

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
            thingspeakChannel = {
                "channelID": channel_id,
                "channelWriteAPIkey": channel_write_api_key,
                "channelReadAPIkey": channel_read_api_key,
                "numberZoneFields": numberZoneFields
            }
            greenhouse["thingspeakChannel"] = thingspeakChannel
            try:
                requests.put(f"{self.catalogURL}/greenhouses", data=json.dumps(greenhouse))
            except requests.exceptions.HTTPError as e:
                print(f"Error raised by catalog while updating greenhouse {greenhouseID}: {e.response.status_code} - {e.args[0]}")
                return "", 0, 0
            except Exception as e:
                print(f"Error while updating greenhouse {greenhouseID} in the catalog: {e}")
                return "", 0, 0
            
            # Update each zone with its corresponding field id in the catalog
            for field in fieldToZone.keys():
                zoneID = fieldToZone[field]
                self.updateZoneWithFieldID(zoneID, 4 + field, greenhouseID)
                
            print(f"New channel created: {name}")
            return channel_write_api_key, channel_id, numberZoneFields

        else:
            print(f"Failed to create channel {name}: {response.text}")
    
    def updateZoneWithFieldID(self, zoneID, fieldID, greenhouseID):
        """
        Update the zone in the catalog with the id of its field on Thingspeak.

        Parameters:
            zoneID (int): ID of the zone.
            fieldID (int): ID of the field.
            greenhouseID (int): ID of the greenhouse in which the zone is.
        """
        # Get the zone from the catalog
        try:
            params = {"zoneID": zoneID}
            response = requests.get(f"{self.catalogURL}/zones", params=params)
            response.raise_for_status()
            zones = response.json().get("zonesList", [])
        except json.JSONDecodeError:
            print(f"Error decoding JSON response for zone {zoneID}")
            return
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while fetching zone {zoneID}: {e.response.status_code} - {e.args[0]}")
            return
        except Exception as e:
            print(f"Error while fetching zone {zoneID} from the catalog: {e}")
            return
        
        if zones:
            zone = zones[0]

            # Add the field id
            zone["thingspeakFieldID"] = fieldID

            # Update the zone in the catalog
            try:
                params = {"greenhouseID": greenhouseID}
                response = requests.put(f"{self.catalogURL}/zones", params=params, data=json.dumps(zone))
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print(f"Error raised by catalog while updating zone {zoneID}: {e.response.status_code} - {e.args[0]}")
            
            except Exception as e:
                print(f"Error while updating zone {zoneID} in the catalog: {e}")
        
    def addZoneFields(self, channelID, greenhouseID):
        """
        Add new fields in the channel of the greenhouse for each new zone and update the zones in the catalog with the id of their field.

        Parameters:
            channelID (int): ID of the channel f the greenhouse on Thingspeak.
            greenhouseID (int): ID of the greenhouse.
        """
        # Get the zones of the greenhouse from the catalog
        try:
            params = {"greenhouseID": greenhouseID}
            response = requests.get(f"{self.catalogURL}/zones", params=params)
            response.raise_for_status()
            zones = response.json().get("zonesList", [])
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while fetching zones of greenhouse {greenhouseID}: {e.response.status_code} - {e.args[0]}")
            return
        
        except Exception as e:
            print(f"Error while fetching zones of greenhouse {greenhouseID} in the catalog: {e}")
            return

        # Get the mapping of the existing zones of the greenhouse and store the new zones
        fieldToZone = {}
        new_zones = []
        for zone in zones:
            # If the zone already exists, store its fieldID
            if "thingspeakFieldID" in zone.keys():
                thingspeakFieldID = zone["thingspeakFieldID"]
                fieldToZone[thingspeakFieldID] = zone["zoneID"]
            # Else, store its zoneID
            else:
                new_zones.append(zone["zoneID"])
        
        # For every new zone, if there are free fields, create a new fieldID
        max_zones_add = min(len(new_zones), 4 + self.maxZoneFields - max(fieldToZone.keys()))
        new_zones_to_add = new_zones[:max_zones_add]
        fields_number  = max(fieldToZone.keys()) + 1
        for zone in new_zones_to_add:
            fieldToZone[fields_number] = zone
            fields_number += 1
        
        name = f"Greenhouse {greenhouseID}"
        params = self.__params.copy()
        params["name"] = name
        
        numberZoneFields = min(len(fieldToZone), self.maxZoneFields)
        number_fields = 0
        for i in fieldToZone.keys():
            if number_fields < numberZoneFields:
                params[f"field{i}"] = f"Moisture Zone {fieldToZone[i]}"
                number_fields += 1
        headers = {
            "Content-Type": "application/json",
            "X-THINGSPEAKAPIKEY": self.userAPIKey
        }

        # Update the channel on Thingspeak
        print(f"Updating ThingSpeak channel {channelID}")
        response = requests.put(f"{self.baseURL}channels/{channelID}.json", headers=headers, data=json.dumps(params))

        if response.status_code == 200:
                
            # Update each new zone with its corresponding field id in the catalog
            for field in fieldToZone.keys():
                zoneID = fieldToZone[field]
                if zoneID in new_zones_to_add:
                    self.updateZoneWithFieldID(zoneID, field, greenhouseID)

            # Update the number of zones fields in the greenhouse
            added_zones = len(new_zones_to_add)
            self.updateNumberFields(greenhouseID, added_zones)

            print(f"{added_zones} new fields added to channel {name}")

        else:
            print(f"Failed to add {added_zones} new fields to channel {name}: {response.text}")

        if len(new_zones) > max_zones_add:
            print(f"Only fields for the 5 first zones have been created\n{len(zones) - self.maxZoneFields} zones will not be updated on Thingspeak")

    def updateNumberFields(self, greenhouseID, added_zones):
        """
        Update the number of zones fields in the grennhouse in the catalog.

        Parameters:
            greenhouseID (int): ID of the greenhouse.
            added_zones (int): number of zones that have been added.
        """

        # Get the greenhouse from the catalog
        try:
            params = {"greenhouseID": greenhouseID}
            response = requests.get(f"{self.catalogURL}/greenhouses", params=params)
            response.raise_for_status()
            greenhouse = response.json().get("greenhousesList", [])[0]
            old_number = greenhouse["thingspeakChannel"]["numberZoneFields"]
        except json.JSONDecodeError:
            print(f"Error decoding JSON response for greenhouse {greenhouseID}")
            return
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while fetching greenhouse {greenhouseID}: {e.response.status_code} - {e.args[0]}")
            return
        except Exception as e:
            print(f"Error fetching fetching greenhouse {greenhouseID} from the catalog: {e}")
            return
        
        # Update the greenhouse in the catalog with the new number of zones fields
        try:
            new_number = old_number + added_zones
            greenhouse["thingspeakChannel"]["numberZoneFields"] = new_number
            response = requests.put(f"{self.catalogURL}/greenhouses", params=params, data=json.dumps(greenhouse))
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while updating greenhouse {greenhouseID}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            print(f"Error fetching updating greenhouse {greenhouseID} from the catalog: {e}")

    def uploadThingspeak(self, channel_write_api_key, field_number, field_value):
        """
        Upload a value in a field on Thingspeak.
        
        Parameters:
            channel_write_api_key (str): write API key of the channel.
            field_number (int): number of the field.
            field_value (float): value to upload.
        """
        
        # Wait 15 s because ThingSpeak has a 15 s upload rate limit
        time.sleep(15)

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