#!/usr/bin/env python3
"""Login and get a fresh access token for the bot"""
import asyncio
from nio import AsyncClient, LoginResponse

async def login():
    client = AsyncClient('http://local.synapse.server:8008', '@spaces-bot2:local.synapse.server')
    
    response = await client.login('botpass123')
    
    if isinstance(response, LoginResponse):
        print("\n" + "=" * 60)
        print("✅ LOGIN SUCCESSFUL!")
        print("=" * 60)
        print(f"\nUser ID: {response.user_id}")
        print(f"Access Token: {response.access_token}")
        print(f"Device ID: {response.device_id}")
        print("\nUpdate config.ini with these values:")
        print(f"access_token = {response.access_token}")
        print(f"device_id = {response.device_id}")
    else:
        print(f"\n❌ LOGIN FAILED: {response}")
    
    await client.close()

asyncio.run(login())
