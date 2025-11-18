# Luxchat Spaces Manager

A Matrix bot for creating and managing hierarchical spaces for schools, associations, and organizations.

## Features

- 🏫 **Luxembourg Education Templates** - Pre-built hierarchies for Fundamental and Secondary education
- 🏗️ **Space Management** - Create spaces, sub-spaces, and rooms programmatically
- 📊 **Hierarchy Builder** - Automated setup for complex organizational structures
- 🔄 **Reusable** - Templates for schools, associations, businesses, and government

## Quick Start

### For Luxembourg Fundamental School

```bash
# In Matrix client, send command to the spaces-bot:
!setup_fundamental_school "École Fondamentale Luxembourg"

# The bot will create:
# - Root school space
# - 4 cycle sub-spaces (Cycle 1-4)
# - Year sub-spaces within each cycle
# - Subject rooms for each year
# - Administration space
# - Parents space
```

## Luxembourg Fundamental Education Structure

The bot creates the following hierarchy based on Luxembourg's education system:

```
🏫 École Fondamentale (Root Space)
├── 🎓 Cycle 1 (Ages 3-5) - 2 years
│   ├── 📚 Cycle 1.1
│   │   ├── 📖 Luxembourgish
│   │   ├── 📖 German
│   │   ├── 📖 French
│   │   ├── 🎨 Éveil aux Sciences
│   │   └── 🎵 Psychomotricité
│   └── 📚 Cycle 1.2 (same subjects)
├── 🎓 Cycle 2 (Ages 5-7) - 2 years
│   ├── 📚 Cycle 2.1
│   │   ├── 📖 Luxembourgish
│   │   ├── 📖 German
│   │   ├── 📖 French
│   │   ├── 🔢 Mathematics
│   │   └── 🔬 Sciences
│   └── 📚 Cycle 2.2 (same subjects)
├── 🎓 Cycle 3 (Ages 7-9) - 2 years
│   ├── 📚 Cycle 3.1
│   │   ├── 📖 Luxembourgish
│   │   ├── 📖 German
│   │   ├── 📖 French
│   │   ├── 🔢 Mathematics
│   │   ├── 🔬 Sciences
│   │   ├── 🌍 Histoire/Géographie
│   │   └── 💻 ICT
│   └── 📚 Cycle 3.2 (same subjects)
├── 🎓 Cycle 4 (Ages 9-12) - 3 years
│   ├── 📚 Cycle 4.1
│   │   ├── 📖 Luxembourgish
│   │   ├── 📖 German
│   │   ├── 📖 French
│   │   ├── 🔢 Mathematics
│   │   ├── 🔬 Natural Sciences
│   │   ├── 🌍 Human & Social Sciences
│   │   └── 💻 ICT
│   ├── 📚 Cycle 4.2 (same subjects)
│   └── 📚 Cycle 4.3 (same subjects)
├── 👥 Administration
│   ├── 📋 Teachers' Room
│   ├── 📢 School Announcements
│   └── 🤖 Bot Management
└── 👨‍👩‍👧‍👦 Parents
    ├── 📬 Parent-Teacher Communication
    └── 📅 Events & Meetings
```

## Commands

### Quick Setup
- `!setup_fundamental_school "School Name"` - Create complete fundamental school structure
- `!setup_secondary_school "School Name"` - Create secondary school structure (coming soon)

### Manual Space Management
- `!create_space "Name" [type]` - Create a new space
- `!create_subspace "Name" parent:<space_id>` - Create a sub-space
- `!create_room "Name" parent:<space_id>` - Create a room in a space
- `!show_hierarchy [space_id]` - Display space hierarchy

### Subject Management
- `!create_subject_room "Subject" cycle:<n> year:<n>` - Add subject room to specific year
- `!list_subjects cycle:<n>` - Show subjects for a cycle

## Configuration

Edit `config.ini`:

```ini
[homeserver]
homeserver = http://local.synapse.server:8008
bot_uid = @spaces-bot:local.synapse.server
access_token = your_token_here
device_id = DEVICE_ID

[config]
management_room = !room_id:local.synapse.server
```

## Use Cases

- **Schools**: Complete education hierarchies (fundamental, secondary)
- **Associations**: Sports clubs, cultural organizations
- **Businesses**: Department structures, project spaces
- **Government**: Ministry departments, public services
