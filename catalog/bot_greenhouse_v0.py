
import json            
import time          
import requests    
import telepot         
from telepot.loop import MessageLoop  
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton  
from MyMQTT import MyMQTT  

token = '8093558201:AAH7ET2nUT8uSkwlcn6zs6ykBvqcLjORauo'


with open("C:/Users/parni/Desktop/MSc_PoliTo/Programming_For_IoT/FinalProject/config.json") as f:
    cfg = json.load(f)  
API_BASE    = cfg.get('api_base', 'http://localhost:8080')  
MQTT_BROKER = cfg['MQTT_BROKER']  
MQTT_PORT   = cfg['MQTT_PORT']     
TOPIC       = cfg['TOPIC_PUBLISH'] 

mqtt_client = MyMQTT(
    clientID="telegramBotClient", 
    broker=MQTT_BROKER,
    port=MQTT_PORT,
    notifier=None                 
)
mqtt_client.start() 


class GreenhouseBot:
    def __init__(self, token):
        self.bot = telepot.Bot(token)
        MessageLoop(self.bot, {'chat': self.on_message}).run_as_thread()
        print("GreenhouseBot listening...") 

    def on_message(self, msg):
        flavor, chat_type, chat_id = telepot.glance(msg)
        text = msg.get('text', '').strip()  
        if not text.startswith('/'):
            return  
        parts = text.split()  
        cmd = parts[0].lower()  
        args = parts[1:]       

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
            elif cmd == '/list':
                self.cmd_list(chat_id, args)
            else:
                self.bot.sendMessage(chat_id, "Unknown command. Use /help.")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Error: {e}")


    def cmd_create_user(self, chat_id, args):
        username = ' '.join(args) if args else None
        payload = {
            "UserID": chat_id,
            "UserName": username or f"User_{chat_id}",  
            "ChatID": chat_id,
            "Houses": []  
        }
        
        r = requests.post(f"{API_BASE}/users", json=payload)
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Registered user {payload['UserName']} (ID={chat_id})")
        else:
            self.bot.sendMessage(chat_id, f"Failed to register: {r.text}")

    def cmd_delete_user(self, chat_id):
        
        r = requests.delete(f"{API_BASE}/users/{chat_id}")
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"User ID={chat_id} deleted")
        else:
            self.bot.sendMessage(chat_id, f"Failed to delete: {r.text}")

    
    def cmd_create_greenhouse(self, chat_id, args):
        # expect a greenhouse name argument
        if not args:
            return self.bot.sendMessage(chat_id, "Usage: /create_greenhouse <name>")
        name = ' '.join(args)
        # fetch existing greenhouses to determine next ID
        gh_list = requests.get(f"{API_BASE}/greenhouses").json().get('GreenHouses', [])
        new_id = max((gh['ID'] for gh in gh_list), default=0) + 1
        payload = {"ID": new_id, "Name": name, "Location": "", "Zones": []}
        r = requests.post(f"{API_BASE}/greenhouses", json=payload)
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Created greenhouse '{name}' (ID={new_id})")
        else:
            self.bot.sendMessage(chat_id, f"Failed to create greenhouse: {r.text}")

    def cmd_delete_greenhouse(self, chat_id, args):
        # Delete greenhouse by ID argument
        try:
            gh_id = int(args[0])
        except:
            return self.bot.sendMessage(chat_id, "Usage: /delete_greenhouse <id>")
        r = requests.delete(f"{API_BASE}/greenhouses/{gh_id}")
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Deleted greenhouse ID={gh_id}")
        else:
            self.bot.sendMessage(chat_id, f"Failed to delete: {r.text}")

    def cmd_create_zone(self, chat_id, args):
        # Expect greenhouse ID and zone name
        if len(args) < 2:
            return self.bot.sendMessage(chat_id, "Usage: /create_zone <gh_id> <zone_name>")
        gh_id = int(args[0])
        name = ' '.join(args[1:])
        
        zones = requests.get(f"{API_BASE}/zones").json().get('ZonesList', [])
        new_id = max((z['ZoneID'] for z in zones), default=0) + 1
        payload = {
            "ZoneID": new_id,
            "GreenHouseID": gh_id,
            "zone_name": name,
            "TemperatureRange": {"min": 20, "max": 30},
            "DeviceList": [],
            "moisture_threshold": 30
        }
        r = requests.post(f"{API_BASE}/zones", json=payload)
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Zone '{name}' created ID={new_id} in GH {gh_id}")
        else:
            self.bot.sendMessage(chat_id, f"Failed to create zone: {r.text}")

    def cmd_delete_zone(self, chat_id, args):
        # Delete zone by ZoneID
        try:
            zone_id = int(args[0])
        except:
            return self.bot.sendMessage(chat_id, "Usage: /delete_zone <id>")
        r = requests.delete(f"{API_BASE}/zones/{zone_id}")
        if r.status_code == 200:
            self.bot.sendMessage(chat_id, f"Deleted zone ID={zone_id}")
        else:
            self.bot.sendMessage(chat_id, f"Failed to delete zone: {r.text}")

    
    def cmd_update_moisture(self, chat_id, args):
        # Expect ZoneID and delta value
        try:
            zone_id = int(args[0]); delta = float(args[1])
        except:
            return self.bot.sendMessage(chat_id, "Usage: /update_moisture <zone_id> <+/-value>")
        # Fetch current zone data
        r1 = requests.get(f"{API_BASE}/zones", params={"zoneID": zone_id})
        if r1.status_code != 200:
            return self.bot.sendMessage(chat_id, f"Error fetching zone: {r1.text}")
        zone = r1.json()
        old = zone.get('moisture_threshold', 0)
        new = old + delta
        if new < 0 or new > 100:
            return self.bot.sendMessage(chat_id, f"Threshold out of range: {new}")
        # Update via PUT
        zone['moisture_threshold'] = new
        r2 = requests.put(f"{API_BASE}/zones", json=zone)
        if r2.status_code == 200:
            # Publish MQTT update on success
            mqtt_client.publish(
                cfg['topics']['update_moisture'].format(zone_id=zone_id),
                {'zone_id': zone_id, 'threshold': new, 'timestamp': int(time.time())}
            )
            self.bot.sendMessage(chat_id, f"Moisture updated: {old}% → {new}%")
        else:
            self.bot.sendMessage(chat_id, f"Update failed: {r2.text}")

    def cmd_list(self, chat_id, args):
        # Expect a UserID argument
        try:
            user_id = int(args[0])
        except:
            return self.bot.sendMessage(chat_id, "Usage: /list <user_id>")
        data = requests.get(f"{API_BASE}/all").json()
        user = next((u for u in data.get('UsersList', []) if u['UserID'] == user_id), None)
        if not user:
            return self.bot.sendMessage(chat_id, f"User {user_id} not found")
        gh_ids = [h['HouseID'] for h in user.get('Houses', [])]
        lines = []
        # Iterate each greenhouse belonging to user
        for gh in data.get('GreenHouses', []):
            if gh['ID'] in gh_ids:
                lines.append(f"GH {gh['ID']}: {gh.get('Name','')}")
                zids = gh.get('Zones', [])
                # List zones under this greenhouse
                for z in data.get('ZonesList', []):
                    if z['ZoneID'] in zids:
                        lines.append(f"  - Zone {z['ZoneID']}: {z.get('zone_name','')}")
        if not lines:
            lines = ["No greenhouses/zones found."]
        self.bot.sendMessage(chat_id, "\n".join(lines))


if __name__ == '__main__':
    bot = GreenhouseBot(token)
    # Keep script running
    while True:
        time.sleep(1)
