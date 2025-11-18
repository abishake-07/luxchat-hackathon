#!/usr/bin/env python3
"""
Setup script for Luxembourg Spaces Manager Bot
Creates the bot user and generates configuration
"""

import requests
import sys

ADMIN_TOKEN = "syt_YWRtaW4_gsRJxUjzwAikbFgQKkeo_0MCXKm"
HOMESERVER = "http://localhost:8008"
BOT_USERNAME = "spaces-bot"
BOT_DISPLAYNAME = "Luxembourg Spaces Manager"
BOT_PASSWORD = "spaces_bot_secure_password_123"

def create_bot_user():
    """Create the spaces bot user via Synapse Admin API"""
    url = f"{HOMESERVER}/_synapse/admin/v2/users/@{BOT_USERNAME}:local.synapse.server"
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "password": BOT_PASSWORD,
        "displayname": BOT_DISPLAYNAME,
        "admin": False,
        "deactivated": False
    }
    
    print(f"Creating bot user: @{BOT_USERNAME}:local.synapse.server")
    response = requests.put(url, headers=headers, json=data)
    
    if response.status_code in [200, 201]:
        print("✅ Bot user created successfully!")
        return True
    else:
        print(f"❌ Failed to create bot user: {response.status_code}")
        print(response.text)
        return False

def login_bot():
    """Login and get access token"""
    url = f"{HOMESERVER}/_matrix/client/v3/login"
    
    data = {
        "type": "m.login.password",
        "identifier": {
            "type": "m.id.user",
            "user": BOT_USERNAME
        },
        "password": BOT_PASSWORD,
        "initial_device_display_name": "Spaces Manager Bot"
    }
    
    print("\nLogging in to get access token...")
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Login successful!")
        print(f"\nAccess Token: {result['access_token']}")
        print(f"Device ID: {result['device_id']}")
        print(f"User ID: {result['user_id']}")
        return result
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def main():
    print("=" * 60)
    print("Luxembourg Spaces Manager Bot Setup")
    print("=" * 60)
    
    # Create user
    if not create_bot_user():
        print("\n⚠️  Bot user may already exist, trying to login...")
    
    # Login
    login_result = login_bot()
    
    if login_result:
        print("\n" + "=" * 60)
        print("CONFIGURATION")
        print("=" * 60)
        print("\nAdd these values to luxchat-spaces-manager/config.ini:")
        print(f"""
[homeserver]
homeserver = http://local.synapse.server:8008
bot_uid = {login_result['user_id']}
access_token = {login_result['access_token']}
device_id = {login_result['device_id']}

[config]
management_room = !ROOM_ID_HERE
        """)
        print("\n⚠️  Don't forget to:")
        print("1. Create a management room in your Matrix client")
        print("2. Invite @spaces-bot:local.synapse.server to that room")
        print("3. Copy the room ID to config.ini (management_room)")
        print("4. Build and run: docker compose build spaces-bot && docker compose up -d spaces-bot")
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
