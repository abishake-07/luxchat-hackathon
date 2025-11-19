#!/usr/bin/env python3
"""Check what rooms the bot is currently in"""
import asyncio
from nio import AsyncClient

async def check_rooms():
    client = AsyncClient('http://local.synapse.server:8008', '@spaces-bot:local.synapse.server')
    client.access_token = 'syt_c3BhY2VzLWJvdA_JgjHYtVSoKjHmztOZjOj_4OVcXZ'
    
    # Sync to get current rooms
    sync_response = await client.sync(timeout=3000)
    
    print("=" * 60)
    print("ROOMS THE BOT IS CURRENTLY IN:")
    print("=" * 60)
    
    if hasattr(sync_response, 'rooms'):
        joined_rooms = sync_response.rooms.join
        print(f"\nTotal joined rooms: {len(joined_rooms)}\n")
        
        for room_id, room_info in joined_rooms.items():
            print(f"Room ID: {room_id}")
            if hasattr(room_info, 'timeline') and room_info.timeline.events:
                print(f"  Events in timeline: {len(room_info.timeline.events)}")
            print()
    else:
        print("No rooms found or sync failed")
        print(f"Sync response type: {type(sync_response)}")
        print(f"Sync response: {sync_response}")
    
    await client.close()

asyncio.run(check_rooms())
