
import json            
import time          
import uuid
import requests    
import telepot         
from telepot.loop import MessageLoop  
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton  
from MyMQTT import MyMQTT

class TelegramBot:

    def __init__(self, settings):
        """
        Initialize Telegram Bot.
        
        Parameters:
            settings (dict): Settings of Telegram Bot.
        """

        # Load the settings
        self.settings = settings
        self.catalogURL = settings["catalogURL"]
        self.serviceInfo = settings['serviceInfo']
        self.broker = self.settings["brokerIP"]
        self.port = self.settings["brokerPort"]
        self.token = self.settings["telegramToken"]

        # Data structures
        self.__user = {
            "userID": 0,
            "userName": "",
            "chatID": 0,
            "greenhouses": []
        }
        self.__greenhouse = {
            "greenhouseID": 0,
            "greenhouseName": "",
            "zones": [],
            "devices": []
        }
        self.__zone = {
            "zoneID": 0,
            "zoneName": "",
            "plantType": "",
            "temperatureRange": {
                "min": 0,
                "max": 0
            },
            "moistureThreshold": 0,
            "devices": []
        }
        self.__threshold_update = {
            "zoneID": 0, 
            "thresholdDelta": 0
        }

        # Create an instance of the bot
        self.bot = telepot.Bot(self.token)
        # Start the bot with a message loop
        MessageLoop(self.bot, {'chat': self.on_chat_message, 'callback_query': self.on_callback_query}).run_as_thread()
        
        # Create an MQTT client
        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=None) # uuid is to generate a random string for the client id
        # Start it
        self.mqttClient.start()
    
    def stop(self):
        """
        Stop the MQTT client
        """
        self.mqttClient.stop()
    
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

    def check_user_registration(self, chat_id):
        """
        Checks if the user is registered in the catalog.

        Parameters:
            chat_id (int): chat ID of the user.

        Returns:
            bool: whether the user is registered in the catalog.
        """

        # Get the user from the catalog
        user_found = False
        params = {"userID": chat_id}
        response = requests.get(f"{self.catalogURL}/users", params=params)
        
        # Check the response status
        if response.status_code == 200:
            user_found = True
        return user_found

    def on_chat_message(self, msg):
        """
        On-chat_message callback. Matches the command with the corresponding method.

        Parameters:
            msg: message.
        """

        content_type, chat_type, chat_id = telepot.glance(msg)
        text = msg.get('text', '').strip()

        if not text.startswith('/'):
            self.bot.sendMessage(chat_id, "Invalid command. The command should start with '/'.")
            print("Invalid command. The command should start with '/'")
            return
        
        msg_parts = text.split()  
        cmd = msg_parts[0].lower()  
        args = msg_parts[1:]       

        try:
            # Match the command with the corresponding method
            if cmd == '/create_user':
                print(f"Command: {cmd}")
                self.cmd_create_user(chat_id, args)
            
            elif cmd == '/help':
                print(f"Command: {cmd}")
                self.cmd_list(chat_id)

            else:
                # Check if the user is registered in the catalog
                user_found = self.check_user_registration(chat_id)
                if not user_found:
                    self.bot.sendMessage(chat_id, "No user found for this chat. Please register using '/create_user'")
                    print(f"User with chat ID {chat_id} not found")
                    return

                elif cmd == '/delete_user':
                    print(f"Command: {cmd}")
                    self.cmd_delete_user(chat_id)

                elif cmd == '/create_greenhouse':
                    print(f"Command: {cmd}")
                    self.cmd_create_greenhouse(chat_id, args)

                elif cmd == '/delete_greenhouse':
                    print(f"Command: {cmd}")
                    self.cmd_delete_greenhouse(chat_id, args)

                elif cmd == '/create_zone':
                    print(f"Command: {cmd}")
                    self.cmd_create_zone(chat_id, args)

                elif cmd == '/delete_zone':
                    print(f"Command: {cmd}")
                    self.cmd_delete_zone(chat_id, args)

                elif cmd == '/update_moisture':
                    print(f"Command: {cmd}")
                    self.cmd_update_moisture(chat_id, args)

                elif cmd == '/get_greenhouses':
                    print(f"Command: {cmd}")
                    self.cmd_get_greenhouses(chat_id)
                
                elif cmd == '/get_zones':
                    print(f"Command: {cmd}")
                    self.cmd_get_zones(chat_id, args)
                
                elif cmd == '/get_zone_info':
                    print(f"Command: {cmd}")
                    self.cmd_get_zone_info(chat_id, args)

                else:
                    self.bot.sendMessage(chat_id, "Invalid command. Please use '/help'.")
                    print(f"Invalid command: {cmd}")

        except Exception as e:
            self.bot.sendMessage(chat_id, "An error occured")
            print(f"An error occured for user with chatID {chat_id}: {e}")

    def on_callback_query(self, msg):
        """
        On callback-query handler. Matches the callback with the corresponding method

        Parameters:
            msg: message.
        """

        query_id , chat_id , query_data = telepot.glance(msg, flavor='callback_query')
        
        # Match the callback with the corresponding method
        if query_data.startswith("get_zones:"):
            # Get the greenhouse ID from the query data
            greenhouse_id = query_data.split(":")[1]

            # Call the function to get zones of the greenhouse
            print(f"Fetching zones for greenhouse {greenhouse_id}")
            self.cmd_get_zones(chat_id, greenhouse_id)

        elif query_data.startswith("get_zone_info:"):
            # Get the zone ID from the query data
            zone_id = query_data.split(":")[1]

            # Call the function to get the infromation of the zone
            print(f"Fetching information of zone {zone_id}")
            self.cmd_get_zone_info(chat_id, zone_id)

    def cmd_create_user(self, chat_id, args):
        """
        Method called on the command '/create_user'. Creates a user.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the user name.
        """

        # Create the user payload
        username = args[0] if args else f"user_{chat_id}"
        user = self.__user.copy()
        user["userID"] = chat_id
        user["userName"] = username
        user["chatID"] = chat_id
        
        # Create the user in the catalog
        try:
            response = requests.post(f"{self.catalogURL}/users", data=json.dumps(user))
            response.raise_for_status()
            if response.status_code == 200:
                self.bot.sendMessage(chat_id, f"Successfully registered user '{username}'")
                print(f"Registered user '{username}'")
        
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, f"Failed to register user '{username}'")
            print(f"Error raised by catalog while registering user '{username}': {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Failed to register user '{username}'")
            print(f"Error while registering user '{username}': {e}")
    
    def cmd_delete_user(self, chat_id):
        """
        Method called on the command '/delete_user'. Deletes a user.

        Parameters:
            chat_id (int): chat ID of the user.
        """
        
        # Delete the user from the catalog
        try:
            response = requests.delete(f"{self.catalogURL}/users/{chat_id}")
            response.raise_for_status()
            if response.status_code == 200:
                self.bot.sendMessage(chat_id, f"User deleted successfully")
                print(f"User with ID {chat_id} deleted")
        
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, f"Failed to delete user")
            print(f"Error raised by catalog while deleting user with ID {chat_id}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Failed to delete user")
            print(f"Error while deleting user with ID {chat_id}: {e}")

    def cmd_create_greenhouse(self, chat_id, args):
        """
        Method called on the command '/create_greenhouse'. Creates a greenhouse.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the greenhouse name.
        """

        if not args:
            self.bot.sendMessage(chat_id, "Please provide a name. Command usage: /create_greenhouse <name>")
            print("No name provided for 'create_greenhouse'.")
            return
        
        name = args[0]

        # Get the list of greenhouses from the catalog
        try:
            response = requests.get(f"{self.catalogURL}/greenhouses")
            response.raise_for_status()
            gh_list = response.json().get('greenhousesList', [])
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, f"Failed to create greenhouse '{name}'")
            print(f"Error raised by catalog while fetching greenhouses: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Failed to create greenhouse '{name}'")
            print(f"Error while fetching greenhouses: {e}")
        
        # Get the next available ID
        new_id = max((gh['greenhouseID'] for gh in gh_list), default=0) + 1

        # Create the grenhouse payload
        greenhouse = self.__greenhouse.copy()
        greenhouse["greenhouseID"] = new_id
        greenhouse["greenhouseName"] = name

        # Create the greenhouse in the catalog
        try:
            params = {"userID": chat_id}
            response = requests.post(f"{self.catalogURL}/greenhouses", data=json.dumps(greenhouse), params=params)
            response.raise_for_status()
            if response.status_code == 200:
                self.bot.sendMessage(chat_id, f"Greenhouse '{name}' successfully created")
                print(f"Greenhouse with ID {new_id} created")
        
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, f"Not able to create greenhouse '{name}'")
            print(f"Error raised by catalog while creating greenhouse with ID {new_id}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Not able to create greenhouse '{name}'")
            print(f"Error while creating greenhouse with ID {new_id}: {e}")

    def cmd_delete_greenhouse(self, chat_id, args):
        """
        Method called on the command '/delete_greenhouse. Deletes a greenhouse.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the greenhouse ID.
        """

        # Get the greenhouse ID from the argument
        if len(args) != 0:
            gh_id = int(args[0])
        else:
            self.bot.sendMessage(chat_id, "Please provide the ID of the greenhouse to delete. Command usage: /delete_greenhouse <gh_id>")
            print("No ID provided for 'delete_greenhouse'")
            return
        
        # Delete the greenhouse from the catalog
        try:
            response = requests.delete(f"{self.catalogURL}/greenhouses/{gh_id}", timeout=5)
            response.raise_for_status()
            if response.status_code == 200:
                self.bot.sendMessage(chat_id, f"Greenhouse successfully deleted")
                print(f"Deleted greenhouse with ID {gh_id}")
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, f"Failed to delete greenhouse")
            print(f"Error raised by catalog while deleting greenhouse with ID {gh_id}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Failed to delete greenhouse")
            print(f"Error while deleting greenhouse with ID {gh_id}: {e}")

    def cmd_create_zone(self, chat_id, args):
        """
        Method called on the command '/create_zone'. Creates a zone in a greenhouse.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the greenhouse ID and zone information.
        """

        # Get greenhouse ID and zone name from the arguments
        if len(args) < 6:
            self.bot.sendMessage(chat_id, "Please provide all required information. Command usage: /create_zone <gh_id> <zone_name> <plant_type> <min_temp> <max_temp> <moisture_threshold>")
            print("Missing information for 'create_zone'")
            return
        
        try:
            gh_id = int(args[0])
            name = args[1]
            plant_type = args[2]
            min_temp = float(args[3])
            max_temp = float(args[4])
            moisture_threshold = float(args[5])
        except ValueError:
            self.bot.sendMessage(chat_id, f"Please provide an integer for greenhouse ID and float numbers for min/max temperature and moisture threshold.")
            print((f"Invalid greenhouse ID, min/max temperature or moisture threshold: {args[0]}, {args[3]}, {args[4]}, {args[5]}"))

        # Get the zones from the catalog
        try:
            response = requests.get(f"{self.catalogURL}/zones")
            response.raise_for_status()
            zones = response.json().get('zonesList', [])
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, f"Failed to create zone '{name}'")
            print(f"Error raised by catalog while fetching zones: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Failed to create zone '{name}'")
            print(f"Error while fetching zones: {e}")
        
        # Get the next available ID
        new_id = max((z['zoneID'] for z in zones), default=0) + 1
        
        # Create the zone payload
        zone = self.__zone.copy()
        zone["zoneID"] = new_id
        zone["zoneName"] = name
        zone["plantType"] = plant_type
        zone["temperatureRange"]["min"] = min_temp
        zone["temperatureRange"]["max"] = max_temp
        zone["moistureThreshold"] = moisture_threshold

        # Create the zone in the catalog
        try:
            params = {"greenhouseID": gh_id}
            response = requests.post(f"{self.catalogURL}/zones", data=json.dumps(zone), params=params)
            response.raise_for_status()
            if response.status_code == 200:
                self.bot.sendMessage(chat_id, f"Zone '{name}' successfully created")
                print(f"Zone '{name}' created with ID {new_id} in greenhouse {gh_id}")
        
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, f"Failed to create zone '{name}'")
            print(f"Error raised by catalog while creating zone '{name}' in greenhouse {gh_id}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Failed to create zone '{name}'")
            print(f"Error while creating zone '{name}' in greenhouse {gh_id}: {e}")
        
    def cmd_delete_zone(self, chat_id, args):
        """
        Method called on the command '/delete_zone'. Deletes a zone.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the zone ID.
        """

        # Get the zone ID from the arguments
        if len(args) != 0:
            try:
                zone_id = int(args[0])
            except ValueError:
                self.bot.sendMessage(chat_id, f"Please provide an integer for zone ID.")
                print((f"Invalid zone ID: {args[0]}"))
                return
        else:
            self.bot.sendMessage(chat_id, "Please provide the ID of the zone to delete. Command usage: /delete_zone <zone_id>")
            print("No ID provided for 'delete_zone'")
            return
        
        # Delete the zone from the catalog
        try:
            response = requests.delete(f"{self.catalogURL}/zones/{zone_id}", timeout=5)
            response.raise_for_status()
            if response.status_code == 200:
                self.bot.sendMessage(chat_id, f"Deleted zone ID={zone_id}")
        
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, f"Failed to delete zone")
            print(f"Error raised by catalog while deleting zone {zone_id}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Failed to delete zone while deleting zone")
            print(f"Error while deleting zone {zone_id}: {e}")

    def cmd_update_moisture(self, chat_id, args):
        """
        Method called on the command '/update_moisture'. Updates the moisture threshold of a zone by adding a given value.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the zone ID and the value to add to the threshold.
        """

        # Get zoneID and value to add from the arguments
        if len(args) >= 2:
            try:
                zone_id = int(args[0])
                delta = float(args[1])
            except ValueError:
                self.bot.sendMessage(chat_id, f"Please provide an integer for zone ID and a float number for value to add.")
                print((f"Invalid zone ID, or value to add: {args[0]}, {args[1]}"))
                return
        else:
            self.bot.sendMessage(chat_id, "Please provide a zone ID and a value to add. Command usage: /update_moisture <zone_id> <+/-value>")
            print("No zone ID or delta value provided for 'update_moisture'")
            return
        
        # Create the threshold update payload
        threshold_update = self.__threshold_update.copy()
        threshold_update["zoneID"] = zone_id
        threshold_update["thresholdDelta"] = delta

        # Update the threshold in the catalog
        try:
            response = requests.put(f"{self.catalogURL}/threshold", data=json.dumps(threshold_update))
            response.raise_for_status()
            if response.status_code == 200:
                self.bot.sendMessage(chat_id, f"Moisture threshold has been updated with {delta}")
                print(f"Moisture threshold of zone with ID {zone_id} update with {delta}")
        
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, "Moisture threshold update failed")
            print(f"Error raised by catalog while updating the moisture threshold of zone {zone_id} by {delta}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, "Moisture threshold update failed")
            print(f"Error while updating the moisture threshold of zone {zone_id} by {delta}: {e}")

    def cmd_get_greenhouses(self, chat_id):
        """
        Method called on the command '/get_greenhouses'. Get the list of greenhouses of a user.
        Sends the greenhouses list in a keyboard.
        By clicking on a key, the command to fetch the zones of this greenhouse is executed.

        Parameters:
            chat_id (int): chat ID of the user.
        """

        # Get the user's greenhouses from the catalog
        try:
            params = {"userID": chat_id}
            response = requests.get(f"{self.catalogURL}/greenhouses", params=params)
            response.raise_for_status()
            if response.status_code == 200:
                greenhouses = response.json().get("greenhousesList", [])
                
                if not greenhouses:
                    self.bot.sendMessage(chat_id, "No greenhouses found.")
                    print(f"No greenhouses to display for user {chat_id}.")
                    return

                # Format the response as a keyboard
                buttons = [[InlineKeyboardButton(text=f"{gh["greenhouseID"]} - {gh["greenhouseName"]}", callback_data=f"get_zones:{gh['greenhouseID']}")] for gh in greenhouses]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                self.bot.sendMessage(chat_id, text="Click on a greenhouse to list its zones:", reply_markup=keyboard)
                print(f"Successfully fetched greenhouses of user {chat_id}")
        
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, "Impossible to retrieve greenhouses for this user")
            print(f"Error raised by catalog while fetching greenhouses of user {chat_id}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, "Impossible to retrieve greenhouses for this user")
            print(f"Error while fetching greenhouses of user {chat_id}: {e}")

    def cmd_get_zones(self, chat_id, args):
        """
        Method called on the command '/get_zones'. Get the list of zones of a greenhouse.
        Sends the zones list in a keyboard.
        By clicking on a key, the command to fetch the information of the zone is executed.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the greenhouse ID.
        """

        # Get the greenhouse ID from the arguments
        if len(args) != 0:
            try:
                greenhouse_id = int(args[0])
            except ValueError:
                self.bot.sendMessage(chat_id, f"Please provide an integer for greenhouse ID.")
                print((f"Invalid greenhouse ID: {args[0]}"))
                return
        else:
            self.bot.sendMessage(chat_id, "Please provide the ID of the greenhouse. Command usage: /get_zones <gh_id>")
            print("No ID provided for 'get_zones'")
            return

        # Get the greenhouse's zones from the catalog
        try:
            params = {"greenhouseID": greenhouse_id}
            response = requests.get(f"{self.catalogURL}/zones", params=params)
            response.raise_for_status()
            if response.status_code == 200:
                zones = response.json().get("zonesList", [])
                
                if not zones:
                    self.bot.sendMessage(chat_id, "No zones found.")
                    print(f"No zones to display for greenhouse {greenhouse_id}.")
                    return

                # Format the response as a keyboard
                buttons = [[InlineKeyboardButton(text=f"{z["zoneID"]} - {z["zoneName"]}", callback_data=f"get_zone_info:{z['zoneID']}")] for z in zones]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                self.bot.sendMessage(chat_id, text="Click on a zone to get its information:", reply_markup=keyboard)
                print(f"Successfully fetched zones of greenhouse {greenhouse_id}")
        
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, "Impossible to retrieve zones for this greenhouse.")
            print(f"Error raised by catalog while fetching zones of greenhouse {greenhouse_id}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, "Impossible to retrieve zones for this greenhouse.")
            print(f"Error while fetching zones of greenhouse {greenhouse_id}: {e}")

    def cmd_get_zone_info(self, chat_id, args):
        """
        Method called on the command '/get_zone_info'. Get the information of the zone.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the zone ID.
        """

        # Get the zone ID from the arguments
        if len(args) != 0:
            try:
                zone_id = int(args[0])
            except ValueError:
                self.bot.sendMessage(chat_id, f"Please provide an integer for zone ID.")
                print((f"Invalid zone ID: {args[0]}"))    
        else:
            self.bot.sendMessage(chat_id, "Please provide the ID of the zone. Command usage: /get_zone_info <zone_id>")
            print("No ID provided for 'get_zone_info'")
            return

        # Get the greenhouse's zones from the catalog
        try:
            params = {"zoneID": zone_id}
            response = requests.get(f"{self.catalogURL}/zones", params=params)
            response.raise_for_status()
            if response.status_code == 200:
                zones = response.json().get("zonesList", [])
                
                if not zones:
                    self.bot.sendMessage(chat_id, "Zone not found.")
                    print(f"Zone {zone_id} not found.")
                    return

                # Format the response
                zone = zones[0]
                msg = "Zone Information:\n"
                msg += f"ID: {zone['zoneID']}\n"
                msg += f"Name: {zone['zoneName']}\n"
                msg += f"Plant Type: {zone["plantType"]}\n"
                msg += f"Temperature Range: {zone["temperatureRange"]["min"]} °C - {zone["temperatureRange"]["max"]} °C\n"
                msg += f"Moisture Threshold: {zone["moistureThreshold"]} %\n"

                self.bot.sendMessage(chat_id, msg)
                print(f"Successfully fetched information of zone {zone_id}")
        
        except requests.exceptions.HTTPError as e:
            self.bot.sendMessage(chat_id, "Impossible to retrieve zone.")
            print(f"Error raised by catalog while fetching zone {zone_id}: {e.response.status_code} - {e.args[0]}")
        except Exception as e:
            self.bot.sendMessage(chat_id, "Impossible to retrieve zone.")
            print(f"Error while fetching zone {zone_id}: {e}")

    def cmd_list(self, chat_id):
        """
        Method called on the command '/help'. Lists the available commands.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the user ID.
        """

        commands = [
            "/create_user <username> - Register a new user.",
            "/delete_user - Delete the current user.",
            "/create_greenhouse <name> - Create a new greenhouse.",
            "/delete_greenhouse <id> - Delete a greenhouse by ID.",
            "/create_zone <gh_id> <zone_name> <plant_type> <min_temp> <max_temp> <moisture_threshold> - Create a zone in a greenhouse.",
            "/delete_zone <zone_id> - Delete a zone by ID.",
            "/update_moisture <zone_id> <+/-value> - Update moisture threshold.",
            "/get_greenhouses - Get the greenhouse of the current user.",
            "/get_zones <gh_id> - Get the zones in a greenhouse.",
            "/get_zone_info <zone_id> - Get the information of the zone.",
            "/help - List available commands and usage.",
        ]
        self.bot.sendMessage(chat_id, "\n".join(commands))

if __name__ == '__main__':
    # Create an instance of Telegram Bot
    settings = json.load(open("settings.json"))
    telegram_bot = TelegramBot(settings)
    print("Telegram Bot started...")

    # Register it in the catalog
    telegram_bot.registerService()

    try:
        # Keep script running
        while True:
            time.sleep(40)

            # Update the service registration
            telegram_bot.updateService()
    
    except KeyboardInterrupt:
        # Graceful shutdown
        telegram_bot.stop()
        print("Telegram Bot stopped")