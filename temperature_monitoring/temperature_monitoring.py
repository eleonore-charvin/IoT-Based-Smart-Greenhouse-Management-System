import requests
import json
import time
import datetime
import uuid
from MyMQTT import *

class TemperatureMonitoring:
    exposed = True

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
        self.baseTopic = self.settings["mqttTopic"]
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.moistureIncrement = self.settings["moistureIncrement"]

        # Create an MQTT client
        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=None)
        self.__message_adjustment = {"greenhouseID": "", "moistureThresholdUpdate": ""}
        # Start it
        self.mqttClient.start()
        
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
        # If the greenhouse has a channel, get its ID and read API key
        if "thingspeakChannel" in greenhouse.keys():
            thingspeakInfo = greenhouse["thingspeakChannel"]
            channel_id = thingspeakInfo["channelID"]
            channel_read_api_key = thingspeakInfo["channelReadAPIkey"]
            
            # Build the URL with time filtering
            field_number = 1 # temperature
            url = f"{self.baseURL}channels/{channel_id}/fields/{field_number}.json?api_key={channel_read_api_key}&start={start_date_str}&end={end_date_str}"

            # Fetch data from ThingSpeak
            response = requests.get(url)
            data = response.json()
            feeds = data.get("feeds", [])

            # Extract timestamp and temperature values
            daily_temperatures = {}
            for entry in feeds:
                timestamp = entry["created_at"][:10]  # Extract only the date (YYYY-MM-DD)
                temp_value = entry.get(f"field{field_number}")

                if temp_value is not None:
                    temp_value = float(temp_value)
                    if timestamp not in daily_temperatures:
                        daily_temperatures[timestamp] = []
                    daily_temperatures[timestamp].append(temp_value)

            # Compute daily averages
            daily_avg_temperature = {date: sum(temps) / len(temps) for date, temps in daily_temperatures.items()}
            return daily_avg_temperature
            
        else:
            print("Cannot retrieve channel for Greenhouse {greenhouseID}")
    
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
        variations = 0

        # Compare each day with the previous day
        for i in range(1, len(sorted_dates)):
            previous_temperature = daily_avg_temperature[sorted_dates[i - 1]]
            current_temperature = daily_avg_temperature[sorted_dates[i]]

            # If the temperature increases, add +1 to the variations
            if current_temperature > previous_temperature:
                variations += 1

            # If the temperature decreases, add -1 to the variations
            elif current_temperature < previous_temperature:
                variations += -1

        # If the temperature has increased every day, increment the moisture threshold
        if variations == len(sorted_dates) - 1:
            return self.moistureIncrement
        
        # If the temperature has decreased every day, decrement the moisture threshold
        elif variations == -(len(sorted_dates) - 1):
            return - self.moistureIncrement
        
        # Else, don't change the moisture threshold
        else:
            return 0

    def publish(self):
        """
        Publish the update of the moisture threshold for each greenhouse in the catalog.
        """
        # Compute the date range (last 5 days)
        end_date = datetime.datetime.now() # Current time
        start_date = end_date - datetime.timedelta(days=5) # 5 days ago

        # Format dates for ThingSpeak API (ISO 8601 format)
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Get the list of greenhouses from the catalog
        response = requests.get(f"{self.catalogURL}/getGreenhouses")
        greenhouses = response.json()

        # For each greenhouse
        for greenhouse in greenhouses:
            # Compute the daily average temperature for the last 5 days
            daily_avg_temperature = self.get_temperature_averages(greenhouse, start_date_str, end_date_str)
            
            # Compute the adjustement of the moisture threshold
            moisture_adjustment = self.compute_moisture_adjustment(daily_avg_temperature)

            # If we have to adjust the moisture threshold, publish the adjustment
            if moisture_adjustment != 0:
                message_adjustment = self.__message_adjustment
                message_adjustment["greenhouseID"] = greenhouse["greenhouseID"]
                message_adjustment["moistureThresholdUpdate"] = moisture_adjustment
                self.mqttClient.myPublish(self.baseTopic, message_adjustment)
                print(f"Published moisture threshold adjustment for greenhouse {greenhouse["greenhouseID"]}: {moisture_adjustment}")

if __name__ == "__main__":
    # Create an instance of TemperatureMonitoring
    settings = json.load(open("settings.json"))
    temperature_monitoring = TemperatureMonitoring(settings)
    print("Starting Temperature Monitoring...")

    # Register it in the catalog
    temperature_monitoring.registerService()

    # Track the last published date and the number of days (to wait for 5 days before starting the update)
    last_published_date = None
    number_days = 0

    try:
        while True:
            # Every 40s, update the service registration
            time.sleep(40)
            temperature_monitoring.updateService()

            # Get the current day
            current_date = datetime.datetime.now().date()

            # Once per day, compute and publish the update of the moisture threshold
            if last_published_date != current_date:
                # If less than 5 days passed, wait for another day
                if number_days < 5:
                    number_days += 1
                
                # Else, compute and publish the update of the moisture threshold
                else:
                    temperature_monitoring.publish()
                    # Update last published date
                    last_published_date = current_date 

    except KeyboardInterrupt:
        # Graceful shutdown
        temperature_monitoring.stop()
        print("Temperature Monitoring Stopped")