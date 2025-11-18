#!/usr/bin/env python3
"""
Invite admin to all existing spaces and rooms
"""

import asyncio
import sqlite3
from nio import AsyncClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def invite_admin_to_all():
    """Invite admin user to all spaces and rooms in database"""
    
    # Bot credentials
    homeserver = "http://local.synapse.server:8008"
    bot_user = "@spaces-bot:local.synapse.server"
    bot_token = "syt_c3BhY2VzLWJvdA_vWEpGsAKjZYSYUBWvcQS_3keCxk"
    admin_user = "@admin:local.synapse.server"
    
    # Initialize client
    client = AsyncClient(homeserver, bot_user)
    client.access_token = bot_token
    client.user_id = bot_user
    
    # Connect to database
    conn = sqlite3.connect('/bot/data/spaces.db')
    cursor = conn.cursor()
    
    # Get all spaces
    cursor.execute('SELECT space_id, space_name FROM spaces')
    spaces = cursor.fetchall()
    
    # Get all rooms
    cursor.execute('SELECT room_id, room_name FROM subject_rooms')
    rooms = cursor.fetchall()
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"Inviting {admin_user} to all spaces and rooms...")
    print(f"{'='*80}\n")
    
    invited_count = 0
    failed_count = 0
    
    # Invite to all spaces
    print(f"📍 Inviting to {len(spaces)} spaces...")
    for space_id, space_name in spaces:
        try:
            await client.room_invite(space_id, admin_user)
            logger.info(f"✅ Invited admin to space: {space_name} ({space_id})")
            invited_count += 1
            await asyncio.sleep(0.5)  # Rate limit protection
        except Exception as e:
            logger.warning(f"❌ Failed to invite admin to space {space_name}: {e}")
            failed_count += 1
    
    # Invite to all rooms
    print(f"\n📖 Inviting to {len(rooms)} rooms...")
    for room_id, room_name in rooms:
        try:
            await client.room_invite(room_id, admin_user)
            logger.info(f"✅ Invited admin to room: {room_name} ({room_id})")
            invited_count += 1
            await asyncio.sleep(0.5)  # Rate limit protection
        except Exception as e:
            logger.warning(f"❌ Failed to invite admin to room {room_name}: {e}")
            failed_count += 1
    
    await client.close()
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Successfully invited: {invited_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📧 Total invites sent: {invited_count + failed_count}")
    print(f"\nCheck your Matrix client for pending invites!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(invite_admin_to_all())
