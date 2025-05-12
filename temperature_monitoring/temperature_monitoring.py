import requests
import json
import time
import datetime
import uuid
from MyMQTT import *

class TemperatureMonitoring:

    def __init__(self, settings):
        """
        Initialize TemperatureMonitoring.
        
        Parameters:
            settings (dict): Settings of TemperatureMonitoring.
        """

        # Load the settings
        self.settings = settings
        self.catalogURL = self.settings["catalogURL"]
        self.baseURL = self.settings["thingspeakURL"]
        self.serviceInfo = self.settings["serviceInfo"]
        self.updateTopic = self.settings["mqttTopic"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.moistureIncrement = self.settings["moistureIncrement"]
        self.__threshold_update = {
            "zoneID": 0, 
            "thresholdDelta": 0
        }

        # Create an MQTT client
        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=None)
        
        # Start it
        self.mqttClient.start()
        
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
    
    def get_temperature_averages(self, greenhouse, start_date_str, end_date_str):
        """
        Get the daily average temperature for the last 5 days.

        Parameters:
            greenhouse (dict): dictionnary containing the information on the greenhouse.
            start_date_str (str): string representing the start date (5 days ago).
            end_date_str (str): string representing the end date (current time).

        Returns:
            dict: dictionnary of (date of the day, average temperature on this day) pairs.
        """

        # Check if the greenhouse has a channel
        if "thingspeakChannel" not in greenhouse.keys():
            print(f"Cannot retrieve channel for Greenhouse {greenhouse.get("greenhouseID", "Unknown")}")
            return {}
        
        # If the greenhouse has a channel, get its ID and read API key
        else:
            thingspeakInfo = greenhouse.get("thingspeakChannel", {})
            channel_id = thingspeakInfo.get("channelID", "")
            channel_read_api_key = thingspeakInfo.get("channelReadAPIkey", "")
            
            # Build the URL with time filtering
            field_number = 1 # temperature
            url = f"{self.baseURL}channels/{channel_id}/fields/{field_number}.json?api_key={channel_read_api_key}&start={start_date_str}&end={end_date_str}"

            # Fetch data from ThingSpeak
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
            except json.JSONDecodeError:
                print("Error decoding JSON response from Thingspeak")
                return {}
            except Exception as e:
                print(f"Error fetching data from Thingspeak: {e}")
                return {}

            feeds = data.get("feeds", [])

            # Extract timestamp and temperature values
            daily_temperatures = {}
            for entry in feeds:
                timestamp = entry["created_at"][:10]  # Extract only the date (YYYY-MM-DD)
                temp_value = entry.get(f"field{field_number}", None)

                if temp_value is not None:
                    try:
                        temp_value = float(temp_value)
                    except ValueError:
                        print(f"Invalid temperature value: {temp_value}")
                    
                    if timestamp not in daily_temperatures:
                        daily_temperatures[timestamp] = []
                    daily_temperatures[timestamp].append(temp_value)

            # Compute daily averages
            daily_avg_temperature = {date: sum(temps) / len(temps) for date, temps in daily_temperatures.items()}
            return daily_avg_temperature
    
    def compute_moisture_adjustment(self, daily_avg_temperature):
        """
        Compute the amount to add or substract from the moisture threshold based on the daily average temperature for the last 5 days:
        - if the daily average temperature has increased constinuously over the 5 days, increase the moisture threshold (positive amount),
        - if it has decreased constinuously, decrease the moisture threshold (negative amount),
        - else, keep the moisture threshold as it is (0).

        Parameters:
            daily_avg_temperature (dict): dictionnary of (date of the day, average temperature on this day) pairs.

        Returns:
            int: amount to add or substract from the moisture threshold.
        """

        # Sort the dates chronologically
        sorted_dates = sorted(daily_avg_temperature.keys())
        number_dates = len(sorted_dates)
        variations = 0

        # Compare each day with the previous day
        for i in range(1, number_dates):
            previous_temperature = daily_avg_temperature[sorted_dates[i - 1]]
            current_temperature = daily_avg_temperature[sorted_dates[i]]

            # If the temperature increases, add +1 to the variations
            if current_temperature > previous_temperature:
                variations += 1

            # If the temperature decreases, add -1 to the variations
            elif current_temperature < previous_temperature:
                variations += -1

        # If the temperature has increased every day, increment the moisture threshold
        if variations == number_dates - 1:
            return self.moistureIncrement
        
        # If the temperature has decreased every day, decrement the moisture threshold
        elif variations == -(number_dates - 1):
            return - self.moistureIncrement
        
        # Else, don't change the moisture threshold
        else:
            return 0

    def update_moisture_threshold(self):
        """
        Update of the moisture threshold for each zone of each greenhouse in the catalog.
        """
        
        # Compute the date range (last 5 days)
        end_date = datetime.datetime.now() # Current time
        start_date = end_date - datetime.timedelta(days=5) # 5 days ago

        # Format dates for ThingSpeak API (ISO 8601 format)
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"Updating the moisture thresholds based on data from {start_date_str} to {end_date_str}")

        # Get the list of greenhouses from the catalog
        try:
            response = requests.get(f"{self.catalogURL}/greenhouses")
            response.raise_for_status()
            greenhouses = response.json().get("greenhousesList", [])
        except json.JSONDecodeError:
            print("Error decoding JSON response for greenhouses list")
            return
        except requests.exceptions.HTTPError as e:
            print(f"Error raised by catalog while fetching greenhouses list: {e.response.status_code} - {e.args[0]}")
            return
        except Exception as e:
            print(f"Error fetching greenhouses list from the catalog: {e}")
            return

        # For each greenhouse
        for greenhouse in greenhouses:
            # Compute the daily average temperature for the last 5 days
            daily_avg_temperature = self.get_temperature_averages(greenhouse, start_date_str, end_date_str)
            
            # Compute the adjustement of the moisture threshold
            moisture_adjustment = self.compute_moisture_adjustment(daily_avg_temperature)
            greenhouseID = greenhouse["greenhouseID"]
            print(f"[Greenhouse {greenhouseID}] moisture adjustment: {moisture_adjustment}")

            # If we have to adjust the moisture threshold, update it on the catalog for each zone in the greenhouse
            if moisture_adjustment != 0:
                for zone in greenhouse["zones"]:
                    zoneID = zone["zoneID"]
                    print(f"[Greenhouse {greenhouseID} zone {zoneID}] updating moisture threshold")
                    threshold_update = self.__threshold_update.copy()
                    threshold_update["zoneID"] = zoneID
                    threshold_update["thresholdDelta"] = moisture_adjustment
                    try:
                        response = requests.put(f"{self.catalogURL}/threshold", data=json.dumps(threshold_update))
                        response.raise_for_status()
                    except requests.exceptions.HTTPError as e:
                        print(f"Error raised by catalog while updating moisture threshold of zone {zoneID}: {e.response.status_code} - {e.args[0]}")
                    except Exception as e:
                        print(f"Error while updating moisture threshold of zone {zoneID} in the catalog: {e}")

if __name__ == "__main__":
    # Create an instance of TemperatureMonitoring
    settings = json.load(open("settings.json"))
    temperature_monitoring = TemperatureMonitoring(settings)
    print("Starting Temperature Monitoring...")

    # Register it in the catalog
    temperature_monitoring.registerService()

    # Track the last updated date and the number of days (to wait for 5 days before starting the update)
    last_updated_date = None
    number_days = 0

    try:
        while True:
            # Every 40s, update the service registration
            time.sleep(40)
            temperature_monitoring.updateService()

            # Get the current day
            current_date = datetime.datetime.now().date()

            # Once per day, compute the update of the moisture threshold
            if last_updated_date != current_date:
                # If less than 5 days have passed, wait for another day
                if number_days < 5:
                    number_days += 1
                
                # Else, compute the update of the moisture threshold
                else:
                    temperature_monitoring.update_moisture_threshold()
                    # Update last updated date
                    last_updated_date = current_date 

    except KeyboardInterrupt:
        # Graceful shutdown
        temperature_monitoring.stop()
        print("Temperature Monitoring Stopped")