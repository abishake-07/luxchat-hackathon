# Luxembourg Spaces Manager - Quick Start

## Setup Steps

### 1. Run Setup Script
```powershell
cd C:\Users\abish\OneDrive\Documents\Projects\luxchat-hackaton
python luxchat-spaces-manager\setup_bot.py
```

This will:
- Create `@spaces-bot:local.synapse.server` user
- Generate access token and device ID
- Display configuration values

### 2. Configure the Bot

Copy the output from setup script to `luxchat-spaces-manager/config.ini`:

```ini
[homeserver]
homeserver = http://local.synapse.server:8008
bot_uid = @spaces-bot:local.synapse.server
access_token = YOUR_TOKEN_HERE
device_id = YOUR_DEVICE_ID_HERE

[config]
management_room = !ROOM_ID_HERE
```

### 3. Create Management Room

In your Matrix client (Luxchat Web):
1. Create a new room called "Spaces Bot Management"
2. Invite `@spaces-bot:local.synapse.server`
3. Copy the room ID from room settings
4. Add room ID to `config.ini` under `management_room`

### 4. Build and Run

```powershell
cd C:\Users\abish\OneDrive\Documents\Projects\luxchat-hackaton
docker compose build spaces-bot
docker compose up -d spaces-bot
```

### 5. Test the Bot

In the management room, send:
```
!help
```

To create a complete school:
```
!setup_fundamental_school "École Fondamentale Belair"
```

This will create:
- 🏫 Root school space
- 🎓 4 Cycles (ages 3-12)
- 📚 9 Years total
- 📖 ~170 subject rooms
- 👥 Administration space
- 👨‍👩‍👧‍👦 Parents space

## Commands

- `!help` - Show help
- `!setup_fundamental_school "Name"` - Create complete fundamental school

## Viewing the Hierarchy

The space hierarchy will appear in:
- **Luxchat Web**: Left sidebar → Spaces section
- **Element**: Home tab → Spaces section
- You can expand each space to see sub-spaces and rooms

## Troubleshooting

### Bot doesn't respond
```powershell
docker logs spaces-bot
```

### Database issues
Delete and recreate:
```powershell
rm luxchat-spaces-manager\data\spaces.db
docker compose restart spaces-bot
```

### Rebuild after code changes
```powershell
docker compose down spaces-bot
docker compose build spaces-bot
docker compose up -d spaces-bot
```

## Next Steps

1. Test with a small school structure first
2. Verify hierarchy appears in Matrix client
3. Add students/teachers to rooms via attendance bot
4. Link class rooms to spaces for integrated management
