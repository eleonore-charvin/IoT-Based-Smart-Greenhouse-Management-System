#!/usr/bin/env python3
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Base URL of your REST API
API_BASE = 'http://localhost:8080'

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hello! I'm your SmartGreenhouse bot. Use /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available commands when the /help command is issued."""
    commands = (
        "/create_user <username> - Register yourself as a user",
        "/delete_user - Remove yourself",
        "/create_greenhouse <greenhouse_name> - Create a new greenhouse",
        "/delete_greenhouse <gh_id> - Delete a greenhouse",
        "/create_zone <gh_id> <zone_name> - Create a zone in a greenhouse",
        "/delete_zone <zone_id> - Delete a zone",
        "/update_moisture <zone_id> <+/-value> - Update moisture threshold",
        "/list <user_id> - List greenhouses and zones for a user",
    )
    await update.message.reply_text("\n".join(commands))

async def create_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register the sending user in the catalog."""
    chat_id = update.effective_chat.id
    # Username from args or their Telegram name
    username = ' '.join(context.args) if context.args else update.effective_user.full_name
    payload = {
        "UserID": chat_id,
        "UserName": username,
        "ChatID": chat_id,
        "Houses": []
    }
    r = requests.post(f"{API_BASE}/users", json=payload)
    if r.status_code == 200:
        await update.message.reply_text(f"User {username} registered with ID {chat_id}.")
    else:
        await update.message.reply_text(f"Failed to register user: {r.text}")

async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete the sending user from the catalog."""
    chat_id = update.effective_chat.id
    r = requests.delete(f"{API_BASE}/users/{chat_id}")
    if r.status_code == 200:
        await update.message.reply_text(f"User with ID {chat_id} deleted.")
    else:
        await update.message.reply_text(f"Failed to delete user: {r.text}")

async def create_greenhouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new greenhouse."""
    try:
        name = ' '.join(context.args)
        if not name:
            raise ValueError
    except ValueError:
        return await update.message.reply_text("Usage: /create_greenhouse <greenhouse_name>")
    # Determine next ID
    gh_list = requests.get(f"{API_BASE}/greenhouses").json().get("GreenHouses", [])
    new_id = max((gh["ID"] for gh in gh_list), default=0) + 1
    payload = {"ID": new_id, "Name": name, "Location": "", "Zones": []}
    r = requests.post(f"{API_BASE}/greenhouses", json=payload)
    if r.status_code == 200:
        await update.message.reply_text(f"Greenhouse '{name}' created with ID {new_id}.")
    else:
        await update.message.reply_text(f"Failed to create greenhouse: {r.text}")

async def delete_greenhouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a greenhouse by ID."""
    try:
        gh_id = int(context.args[0])
    except (IndexError, ValueError):
        return await update.message.reply_text("Usage: /delete_greenhouse <gh_id>")
    r = requests.delete(f"{API_BASE}/greenhouses/{gh_id}")
    if r.status_code == 200:
        await update.message.reply_text(f"Greenhouse {gh_id} deleted.")
    else:
        await update.message.reply_text(f"Failed to delete greenhouse: {r.text}")

async def create_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a zone in a greenhouse."""
    try:
        gh_id = int(context.args[0])
        zone_name = ' '.join(context.args[1:])
        if not zone_name:
            raise ValueError
    except (IndexError, ValueError):
        return await update.message.reply_text("Usage: /create_zone <gh_id> <zone_name>")
    # Determine next zone ID
    zones = requests.get(f"{API_BASE}/zones").json().get("ZonesList", [])
    new_zone_id = max((z["ZoneID"] for z in zones), default=0) + 1
    payload = {
        "ZoneID": new_zone_id,
        "GreenHouseID": gh_id,
        "zone_name": zone_name,
        "TemperatureRange": {"min": 20, "max": 30},
        "DeviceList": [],
        "moisture_threshold": 30
    }
    r = requests.post(f"{API_BASE}/zones", json=payload)
    if r.status_code == 200:
        await update.message.reply_text(f"Zone '{zone_name}' created with ID {new_zone_id} in greenhouse {gh_id}.")
    else:
        await update.message.reply_text(f"Failed to create zone: {r.text}")

async def delete_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a zone by ID."""
    try:
        zone_id = int(context.args[0])
    except (IndexError, ValueError):
        return await update.message.reply_text("Usage: /delete_zone <zone_id>")
    r = requests.delete(f"{API_BASE}/zones/{zone_id}")
    if r.status_code == 200:
        await update.message.reply_text(f"Zone {zone_id} deleted.")
    else:
        await update.message.reply_text(f"Failed to delete zone: {r.text}")

async def update_moisture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update the moisture threshold of a zone."""
    try:
        zone_id = int(context.args[0])
        delta = float(context.args[1])
    except (IndexError, ValueError):
        return await update.message.reply_text("Usage: /update_moisture <zone_id> <+/-value>")
    # Fetch current zone
    resp = requests.get(f"{API_BASE}/zones", params={"zoneID": zone_id})
    if resp.status_code != 200:
        return await update.message.reply_text(f"Error: {resp.text}")
    zone = resp.json()
    old_mt = zone.get("moisture_threshold", 0)
    new_mt = old_mt + delta
    if new_mt < 0 or new_mt > 100:
        return await update.message.reply_text(f"Threshold {new_mt}% out of bounds (0-100)")
    zone["moisture_threshold"] = new_mt
    r2 = requests.put(f"{API_BASE}/zones", json=zone)
    if r2.status_code == 200:
        await update.message.reply_text(f"Moisture for zone {zone_id}: {old_mt}% → {new_mt}%")
    else:
        await update.message.reply_text(f"Update failed: {r2.text}")

async def list_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List greenhouses and zones for a user ID."""
    try:
        user_id = int(context.args[0])
    except (IndexError, ValueError):
        return await update.message.reply_text("Usage: /list <user_id>")
    data = requests.get(f"{API_BASE}/all").json()
    user = next((u for u in data.get("UsersList", []) if u["UserID"] == user_id), None)
    if not user:
        return await update.message.reply_text(f"User {user_id} not found")
    gh_ids = [h["HouseID"] for h in user.get("Houses", [])]
    gh_names = []
    for gh in data.get("GreenHouses", []):
        if gh["ID"] in gh_ids:
            gh_names.append(f"{gh['ID']}: {gh.get('Name','')}" )
    msg = f"User {user_id} Greenhouses:\n" + "\n".join(gh_names)
    await update.message.reply_text(msg)


def main():
    app = ApplicationBuilder().token('8093558201:AAH7ET2nUT8uSkwlcn6zs6ykBvqcLjORauo').build()

    # Register handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('create_user', create_user))
    app.add_handler(CommandHandler('delete_user', delete_user))
    app.add_handler(CommandHandler('create_greenhouse', create_greenhouse))
    app.add_handler(CommandHandler('delete_greenhouse', delete_greenhouse))
    app.add_handler(CommandHandler('create_zone', create_zone))
    app.add_handler(CommandHandler('delete_zone', delete_zone))
    app.add_handler(CommandHandler('update_moisture', update_moisture))
    app.add_handler(CommandHandler('list', list_items))

    app.run_polling()


if __name__ == '__main__':
    main()
