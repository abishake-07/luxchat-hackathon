#!/usr/bin/env python3
"""
Test connection to luxchat4pro.lu and create management room
"""

import asyncio
import aiohttp
from nio import AsyncClient, LoginResponse

# Configuration
HOMESERVER = "https://poc.luxchat4pro.lu"
USER_ID = "@koblenz:poc.luxchat4pro.lu"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJLb2JsZW56In0.5Trv6JerbNHRb8bBCbgCQuMTRbigWdwEBcu8lGZ2EDM"
DEVICE_ID = "SPACESBOT"


async def test_connection():
    """Test connection to luxchat4pro.lu"""
    print("=" * 80)
    print("TESTING CONNECTION TO LUXCHAT4PRO.LU")
    print("=" * 80)
    
    # Test 1: Check server is accessible
    print("\n1. Testing server endpoint...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{HOMESERVER}/_matrix/client/versions") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Server accessible: {HOMESERVER}")
                    print(f"   ✅ Supported versions: {data.get('versions', [])[:3]}...")
                else:
                    print(f"   ❌ Server returned status {resp.status}")
                    return False
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    
    # Test 2: Create client and test JWT authentication
    print("\n2. Testing JWT authentication...")
    client = AsyncClient(HOMESERVER, USER_ID, device_id=DEVICE_ID)
    client.access_token = JWT_TOKEN
    
    try:
        # Try to sync to verify authentication works
        sync_response = await client.sync(timeout=3000, full_state=False)
        
        if sync_response and hasattr(sync_response, 'rooms'):
            print(f"   ✅ Authentication successful!")
            print(f"   ✅ User ID: {USER_ID}")
            print(f"   ✅ Joined rooms: {len(sync_response.rooms.join)}")
            
            # List joined rooms
            if sync_response.rooms.join:
                print("\n   📋 Currently joined rooms:")
                for room_id, room_info in list(sync_response.rooms.join.items())[:5]:
                    print(f"      • {room_id}")
            else:
                print("   ⚠️  Not in any rooms yet")
            
            return True, sync_response
        else:
            print(f"   ❌ Sync failed: {sync_response}")
            return False, None
            
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        return False, None
    finally:
        await client.close()


async def create_management_room():
    """Create a management room for the bot"""
    print("\n" + "=" * 80)
    print("CREATING MANAGEMENT ROOM")
    print("=" * 80)
    
    async with aiohttp.ClientSession() as session:
        url = f"{HOMESERVER}/_matrix/client/v3/createRoom"
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "name": "Luxchat Spaces Management",
            "topic": "Management room for Spaces Manager Bot",
            "preset": "trusted_private_chat",
            "visibility": "private",
            "initial_state": [
                {
                    "type": "m.room.guest_access",
                    "state_key": "",
                    "content": {"guest_access": "can_join"}
                }
            ]
        }
        
        try:
            async with session.post(url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    room_id = result.get('room_id')
                    print(f"\n✅ Management room created!")
                    print(f"   Room ID: {room_id}")
                    print(f"   Name: Luxchat Spaces Management")
                    print(f"\n📝 Update config.ini with:")
                    print(f"   management_room = {room_id}")
                    return room_id
                else:
                    error = await resp.text()
                    print(f"\n❌ Failed to create room: {resp.status}")
                    print(f"   Error: {error}")
                    return None
        except Exception as e:
            print(f"\n❌ Error creating room: {e}")
            return None


async def main():
    print("\n🚀 Luxchat4pro Connection Test\n")
    
    # Test connection
    success, sync_response = await test_connection()
    
    if not success:
        print("\n❌ Connection test failed!")
        print("\nPossible issues:")
        print("  1. Wrong homeserver URL (try: https://matrix.poc.luxchat4pro.lu)")
        print("  2. JWT token expired or invalid")
        print("  3. Network/firewall blocking connection")
        return
    
    # Check if already in a management room
    has_management_room = False
    if sync_response and sync_response.rooms.join:
        for room_id, room_info in sync_response.rooms.join.items():
            # Check if this looks like a management room
            if "management" in room_id.lower() or len(sync_response.rooms.join) == 1:
                print(f"\n✅ Found potential management room: {room_id}")
                print(f"\n📝 Update config.ini with:")
                print(f"   management_room = {room_id}")
                has_management_room = True
                break
    
    # Create management room if needed
    if not has_management_room:
        print("\n🔧 Creating new management room...")
        room_id = await create_management_room()
        
        if not room_id:
            print("\n⚠️  Could not create management room.")
            print("   You can create one manually and update config.ini")
    
    print("\n" + "=" * 80)
    print("✅ SETUP COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Update config.ini with the management_room ID (shown above)")
    print("  2. Copy config.ini to Docker: docker cp config.ini spaces-bot:/bot/")
    print("  3. Restart bot: docker restart spaces-bot")
    print("  4. Check logs: docker logs spaces-bot --tail 20")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
