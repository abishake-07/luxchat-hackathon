#!/usr/bin/env python3
import asyncio
from nio import AsyncClient

async def test():
    client = AsyncClient('http://local.synapse.server:8008', '@spaces-bot:local.synapse.server')
    client.access_token = 'syt_c3BhY2VzLWJvdA_JgjHYtVSoKjHmztOZjOj_4OVcXZ'
    
    result = await client.room_send(
        '!NZvjpkpcInIitdDHUB:local.synapse.server',
        'm.room.message',
        {'msgtype': 'm.text', 'body': '🧪 **Test Message**\n\nIf you see this, the bot is working. Try: !help'}
    )
    
    print(f"Message sent: {result}")
    await client.close()

asyncio.run(test())
