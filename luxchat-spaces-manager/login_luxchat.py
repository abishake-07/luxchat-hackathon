#!/usr/bin/env python3
"""
Login to luxchat4pro.lu and get access token
"""

import asyncio
import aiohttp
from nio import AsyncClient, LoginResponse

# Configuration
HOMESERVER = "https://poc.luxchat4pro.lu"
USERNAME = "koblenz"  # Without @ and :server
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJLb2JsZW56In0.5Trv6JerbNHRb8bBCbgCQuMTRbigWdwEBcu8lGZ2EDM"


async def login_with_jwt():
    """Login using JWT token"""
    print("=" * 80)
    print("LOGGING IN TO LUXCHAT4PRO.LU")
    print("=" * 80)
    
    client = AsyncClient(HOMESERVER, f"@{USERNAME}:poc.luxchat4pro.lu")
    
    # Try JWT login
    print(f"\n1. Attempting JWT login...")
    print(f"   Username: {USERNAME}")
    print(f"   Server: {HOMESERVER}")
    
    try:
        # Try org.matrix.login.jwt
        response = await client.login(
            token=JWT_TOKEN,
            device_name="SpacesBot"
        )
        
        if isinstance(response, LoginResponse):
            print(f"\n✅ Login successful!")
            print(f"   User ID: {response.user_id}")
            print(f"   Device ID: {response.device_id}")
            print(f"   Access Token: {response.access_token[:50]}...")
            
            print(f"\n📝 Update config.ini with:")
            print(f"   bot_uid = {response.user_id}")
            print(f"   access_token = {response.access_token}")
            print(f"   device_id = {response.device_id}")
            
            await client.close()
            return response.access_token, response.device_id, response.user_id
        else:
            print(f"\n❌ Login failed: {response}")
            
    except Exception as e:
        print(f"\n❌ Login error: {e}")
    
    await client.close()
    return None, None, None


async def login_with_password():
    """Fallback: try password login"""
    print("\n" + "=" * 80)
    print("ALTERNATIVE: PASSWORD LOGIN")
    print("=" * 80)
    print("\nIf JWT login doesn't work, you can try password login:")
    print("\n1. Get your password from luxchat4pro.lu")
    print("2. Run this command:")
    print(f"   docker exec -it spaces-bot python3 -c \"")
    print(f"   from nio import AsyncClient; import asyncio")
    print(f"   async def login():")
    print(f"       client = AsyncClient('https://poc.luxchat4pro.lu', '@koblenz:poc.luxchat4pro.lu')")
    print(f"       resp = await client.login('YOUR_PASSWORD', device_name='SpacesBot')")
    print(f"       print(f'Access Token: {{resp.access_token}}')")
    print(f"       print(f'Device ID: {{resp.device_id}}')")
    print(f"       await client.close()")
    print(f"   asyncio.run(login())\"")


async def create_management_room(access_token):
    """Create management room"""
    print("\n" + "=" * 80)
    print("CREATING MANAGEMENT ROOM")
    print("=" * 80)
    
    async with aiohttp.ClientSession() as session:
        url = f"{HOMESERVER}/_matrix/client/v3/createRoom"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "name": "Luxchat Spaces Management",
            "topic": "Management room for Spaces Manager Bot",
            "preset": "trusted_private_chat",
            "visibility": "private"
        }
        
        try:
            async with session.post(url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    room_id = result.get('room_id')
                    print(f"\n✅ Management room created!")
                    print(f"   Room ID: {room_id}")
                    return room_id
                else:
                    error = await resp.text()
                    print(f"\n❌ Failed: {resp.status} - {error}")
                    return None
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return None


async def main():
    print("\n🚀 Luxchat4pro Login & Setup\n")
    
    # Try to login
    access_token, device_id, user_id = await login_with_jwt()
    
    if not access_token:
        await login_with_password()
        return
    
    # Create management room
    room_id = await create_management_room(access_token)
    
    print("\n" + "=" * 80)
    print("✅ SETUP COMPLETE!")
    print("=" * 80)
    
    if room_id:
        # Create updated config content
        config_content = f"""[homeserver]
homeserver = https://poc.luxchat4pro.lu
bot_uid = {user_id}
access_token = {access_token}
device_id = {device_id}

[config]
management_room = {room_id}
"""
        
        print("\n📝 Complete config.ini content:")
        print("-" * 80)
        print(config_content)
        print("-" * 80)
        
        # Save to file
        with open('/bot/config.ini', 'w') as f:
            f.write(config_content)
        
        print("\n✅ Config saved to /bot/config.ini")
        print("\nNext steps:")
        print("  1. Restart bot: docker restart spaces-bot")
        print("  2. Check logs: docker logs spaces-bot --tail 20")
        print("  3. Join the management room in Element")
        print("  4. Send !help to test the bot")
    
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
