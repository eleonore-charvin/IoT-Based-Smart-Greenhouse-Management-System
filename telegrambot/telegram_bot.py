
import json            
import time          
import uuid
import requests    
import telepot         
from telepot.loop import MessageLoop  
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton  
from MyMQTT import MyMQTT

class TelegramBot:

    def __init__(self, token):
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

        # Create an instance of the bot
        self.bot = telepot.Bot(token)
        # Start the bot with a message loop
        MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()
        
        # Create an MQTT client
        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=None) # uuid is to generate a random string for the client id
        # Start it
        self.mqttClient.start()

    def on_chat_message(self, msg):
        """
        On-chat_message callback.

        Parameters:
            msg: message.
        """

        content_type, chat_type, chat_id = telepot.glance(msg)
        text = msg.get('text', '').strip()
        if text.startswith('/') == False :
            return "Please enter a valid command starting with '/'"
        msg_parts = text.split()  
        cmd = msg_parts[0].lower()  
        args = msg_parts[1:]       

        try:
            
            if cmd == '/create_user':
                self.cmd_create_user(chat_id, args)
            elif cmd == '/delete_user':
                self.cmd_delete_user(chat_id)
            elif cmd == '/create_greenhouse':
                self.cmd_create_greenhouse(chat_id, args)
            elif cmd == '/delete_greenhouse':
                self.cmd_delete_greenhouse(chat_id, args)
            elif cmd == '/create_zone':
                self.cmd_create_zone(chat_id, args)
            elif cmd == '/delete_zone':
                self.cmd_delete_zone(chat_id, args)
            elif cmd == '/update_moisture':
                self.cmd_update_moisture(chat_id, args)
            elif cmd == '/help':
                self.cmd_list(chat_id, args)
            else:
                self.bot.sendMessage(chat_id, "Invalid command. Please use /help.")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Error: {e}")

    def cmd_create_user(self, chat_id, args):
        """
        Method called on the command '/create_user'. Creates a user.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the user name.
        """

        username = ' '.join(args) if args else None
        payload = {
            "UserID": chat_id,
            "UserName": username or f"User_{chat_id}",  
            "ChatID": chat_id,
            "Houses": []  
        }
        
        r = requests.post(f"{self.catalogURL}/users", json=payload, timeout=5)
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Registered user {payload['UserName']} (ID={chat_id})")
        else:
            self.bot.sendMessage(chat_id, f"Failed to register: {r.text}")

    def cmd_delete_user(self, chat_id):
        """
        Method called on the command '/delete_user'. Deletes a user.

        Parameters:
            chat_id (int): chat ID of the user.
        """
        
        r = requests.delete(f"{self.catalogURL}/users/{chat_id}", timeout=5)
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"User ID={chat_id} deleted")
        else:
            self.bot.sendMessage(chat_id, f"Failed to delete: {r.text}")

    def cmd_create_greenhouse(self, chat_id, args):
        """
        Method called on the command '/create_greenhouse'. Creates a greenhouse.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the greenhouse name.
        """

        if not args:
            return self.bot.sendMessage(chat_id, "Usage: /create_greenhouse <name>")
        name = ' '.join(args)
        gh_list = requests.get(f"{self.catalogURL}/greenhouses", timeout=5).json().get('GreenHouses', [])
        new_id = max((gh['ID'] for gh in gh_list), default=0) + 1
        payload = {"ID": new_id, "Name": name, "Location": "", "Zones": []}
        r = requests.post(f"{self.catalogURL}/greenhouses", json=payload, timeout=5)
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Greenhouse created !' (ID={new_id})")
        else:
            self.bot.sendMessage(chat_id, f"Not able to create greenhouse: {r.text}")

    def cmd_delete_greenhouse(self, chat_id, args):
        """
        Method called on the command '/delete_greenhouse. Deletes a greenhouse.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the greenhouse ID.
        """

        # Delete greenhouse by ID argument
        if len(args) != 0 :
            gh_id = int(args[0])
        else :
            return self.bot.sendMessage(chat_id, "Usage: /delete_greenhouse <id>")
        r = requests.delete(f"{self.catalogURL}/greenhouses/{gh_id}", timeout=5)
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Deleted greenhouse ID={gh_id}")
        else:
            self.bot.sendMessage(chat_id, f"Failed to delete: {r.text}")

    def cmd_create_zone(self, chat_id, args):
        """
        Method called on the command '/create_zone'. Creates a zone in a greenhouse.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the greenhouse ID and zone name.
        """

        # Expect greenhouse ID and zone name
        if len(args) < 2:
            return self.bot.sendMessage(chat_id, "Usage: /create_zone <gh_id> <zone_name>")
        gh_id = int(args[0])
        name = ' '.join(args[1:])
        zones = requests.get(f"{self.catalogURL}/zones", timeout=5).json().get('ZonesList', [])
        new_id = max((z['ZoneID'] for z in zones), default=0) + 1
        payload = {
            "ZoneID": new_id,
            "GreenHouseID": gh_id,
            "zone_name": name,
            "TemperatureRange": {"min": 20, "max": 30},
            "DeviceList": [],
            "moisture_threshold": 30
        }
        r = requests.post(f"{self.catalogURL}/zones", json=payload , timeout=5) 
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Zone '{name}' created ID={new_id} in GH {gh_id}")
        else:
            self.bot.sendMessage(chat_id, f"Failed to create zone: {r.text}")

    def cmd_delete_zone(self, chat_id, args):
        """
        Method called on the command '/delete_zone'. Deletes a zone.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the zone ID.
        """

        # Delete zone by ZoneID
        if len(args) != 0 :
            zone_id = int(args[0])
        else:
            return self.bot.sendMessage(chat_id, "Usage: /delete_zone <id>")
        r = requests.delete(f"{self.catalogURL}/zones/{zone_id}", timeout=5)
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Deleted zone ID={zone_id}")
        else:
            self.bot.sendMessage(chat_id, f"Failed to delete zone: {r.text}")

    def cmd_update_moisture(self, chat_id, args):
        """
        Method called on the command '/update_moisture'. Updates the moisture threshold of a zone by adding a given value.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the zone ID and the value to add to the threshold.
        """

        # expect ZoneID and the delta value
        try:
            zone_id = int(args[0])
            delta = float(args[1])
        except:
            return self.bot.sendMessage(chat_id, "Usage: /update_moisture <zone_id> <+/-value>")
        
        # fetch current zone data
        r1 = requests.get(f"{self.catalogURL}/zones", params={"zoneID": zone_id}, timeout=5)
        if r1.status_code != 200:
            return self.bot.sendMessage(chat_id, f"Error fetching zone: {r1.text}")
        zone = r1.json()
        old = zone.get('moisture_threshold', 0)
        new = old + delta
        if new < 0 or new > 100: # to check whether threshold is valid or not
            return self.bot.sendMessage(chat_id, f"Threshold out of range: {new}")
        
        # update via PUT
        zone['moisture_threshold'] = new
        r2 = requests.put(f"{self.catalogURL}/zones", json=zone, timeout=5)
        if r2.status_code == 200:
            # publish MQTT update on success
            self.mqtt_client.publish(
                cfg['topics']['update_moisture'].format(zone_id=zone_id),
                {'zone_id': zone_id, 'threshold': new, 'timestamp': int(time.time())}
            )
            self.bot.sendMessage(chat_id, f"Moisture threshold is updated: {old}% → {new}%")
        else:
            self.bot.sendMessage(chat_id, f"Update failed: {r2.text}")

    def cmd_list(self, chat_id, args):
        """
        Method called on the command '/help'. Lists the available commands.

        Parameters:
            chat_id (int): chat ID of the user.
            args (str): text that contains the user ID.
        """

        # expect a UserID argument
        if len(args) != 0 :
            user_id = int(args[0])
        else:
            return self.bot.sendMessage(chat_id, "Usage: /list <user_id>")
        data = requests.get(f"{self.catalogURL}/all", timeout=5).json()
        user = next((u for u in data.get('UsersList', []) if u['UserID'] == user_id), None)
        if not user:
            return self.bot.sendMessage(chat_id, f"User {user_id} not found")
        gh_ids = [h['HouseID'] for h in user.get('Houses', [])]
        lines = []
        for gh in data.get('GreenHouses', []):
            if gh['ID'] in gh_ids:
                lines.append(f"GH {gh['ID']}: {gh.get('Name','')}")
                zids = gh.get('Zones', [])
                for z in data.get('ZonesList', []):
                    if z['ZoneID'] in zids:
                        lines.append(f"  - Zone {z['ZoneID']}: {z.get('zone_name','')}")
        if not lines:
            lines = ["No greenhouses/zones found."]
        self.bot.sendMessage(chat_id, "\n".join(lines))


if __name__ == '__main__':
    settings = json.load(open("settings.json"))
    telegram_bot = TelegramBot(settings)
    print("GreenhouseBot is listening...")

    try:
        # Keep script running
        while True:
            time.sleep(40)
    
    except KeyboardInterrupt:
        # Graceful shutdown
        telegram_bot.stop()
        print("Thingspeak Adaptor Stopped")
