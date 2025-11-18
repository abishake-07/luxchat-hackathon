#!/usr/bin/env python3
"""
Join fake users to their respective rooms based on their roles
"""

import asyncio
import aiohttp
import sqlite3
import sys

# Configuration
SYNAPSE_URL = "http://local.synapse.server:8008"
ADMIN_TOKEN = "syt_YWRtaW4_DbZLNrxCeFIbyAXAPtln_0AuBvM"
BOT_TOKEN = "syt_c3BhY2VzLWJvdA_vWEpGsAKjZYSYUBWvcQS_3keCxk"
DB_PATH = "/bot/data/spaces.db"

async def get_user_token(session, user_id, password):
    """Login as user to get access token"""
    url = f"{SYNAPSE_URL}/_matrix/client/v3/login"
    data = {
        "type": "m.login.password",
        "identifier": {
            "type": "m.id.user",
            "user": user_id
        },
        "password": password
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("access_token")
            elif resp.status == 429:
                # Rate limited - wait and retry
                retry_data = await resp.json()
                retry_after = retry_data.get("retry_after_ms", 5000) / 1000
                print(f"  ⏳ Rate limited, waiting {retry_after:.1f}s...")
                await asyncio.sleep(retry_after + 1)
            else:
                error = await resp.text()
                print(f"❌ Failed to login {user_id}: {error}")
                return None
    
    print(f"❌ Failed to login after {max_retries} attempts")
    return None

async def join_room(session, room_id, access_token):
    """Join a room using user's access token"""
    url = f"{SYNAPSE_URL}/_matrix/client/v3/join/{room_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with session.post(url, headers=headers) as resp:
        if resp.status == 200:
            return True
        else:
            error = await resp.text()
            print(f"  ⚠️ Failed to join room: {error}")
            return False

async def set_power_level(session, room_id, user_id, power_level):
    """Set power level for a user in a room (using bot token)"""
    # First get current power levels
    url = f"{SYNAPSE_URL}/_matrix/client/v3/rooms/{room_id}/state/m.room.power_levels"
    headers = {"Authorization": f"Bearer {BOT_TOKEN}"}
    
    async with session.get(url, headers=headers) as resp:
        if resp.status == 200:
            power_levels = await resp.json()
        else:
            print(f"  ⚠️ Failed to get power levels for room")
            return False
    
    # Update power level for user
    if "users" not in power_levels:
        power_levels["users"] = {}
    power_levels["users"][user_id] = power_level
    
    # Send updated power levels
    async with session.put(url, headers=headers, json=power_levels) as resp:
        if resp.status == 200:
            return True
        else:
            error = await resp.text()
            print(f"  ⚠️ Failed to set power level: {error}")
            return False

def get_school_structure(school_name):
    """Get all rooms for a school organized by type"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get school info
    cursor.execute("SELECT school_id, root_space_id FROM schools WHERE school_name = ?", (school_name,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return None
    
    school_id, root_space_id = result
    
    # Get all spaces and rooms
    structure = {
        "school_id": school_id,
        "root_space_id": root_space_id,
        "levels": {},  # P1-P5 space IDs
        "subject_rooms": {},  # level -> list of room_ids
        "admin_space": None,
        "parent_space": None,
        "teacher_space": None
    }
    
    # Get all spaces under this school's root space
    cursor.execute("""
        SELECT space_id, space_name, space_type 
        FROM spaces 
        WHERE space_id = ? OR parent_space_id = ?
    """, (root_space_id, root_space_id))
    
    for space_id, space_name, space_type in cursor.fetchall():
        if space_type in ['level', 'primary_level', 'fundamental_level']:
            # Space name IS the level (P1, P2, etc. or C1Y1, C1Y2, etc.)
            structure["levels"][space_name] = space_id
        elif space_type in ['admin', 'parent', 'teacher']:
            structure[f"{space_type}_space"] = space_id
    
    # Get subject rooms organized by level
    for level, level_space_id in structure["levels"].items():
        cursor.execute("""
            SELECT room_id
            FROM subject_rooms
            WHERE space_id = ?
        """, (level_space_id,))
        structure["subject_rooms"][level] = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return structure

def get_users_with_credentials(school_name):
    """Get all users for a school with their credentials"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get school_id
    cursor.execute("SELECT school_id FROM schools WHERE school_name = ?", (school_name,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return []
    
    school_id = result[0]
    
    # Get all users with their passwords from the CSV
    # Passwords are NOT stored in database for security
    import csv
    users = []
    csv_path = f"/bot/data/fake_users_{school_name.replace(' ', '_')}.csv"
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Build full Matrix user ID from username
                user_id = f"@{row['username']}:local.synapse.server"
                users.append({
                    "user_id": user_id,
                    "username": row["username"],
                    "password": row["password"],
                    "role": row["role"],
                    "display_name": row["display_name"],
                    "level": row.get("level", "")
                })
    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_path}")
        conn.close()
        return []
    
    # Level is already in the CSV, no need to query database
    
    conn.close()
    return users

async def join_user_to_rooms(session, user, structure):
    """Join a user to appropriate rooms based on their role"""
    # Get user token
    print(f"\n👤 Processing {user['display_name']} ({user['role']})")
    token = await get_user_token(session, user["user_id"], user["password"])
    if not token:
        return False
    
    rooms_joined = 0
    
    if user["role"] == "student":
        level = user.get("level")
        if not level:
            print(f"  ⚠️ No level enrollment found")
            return False
        
        # Join level space
        if level in structure["levels"]:
            print(f"  📚 Joining {level} space...")
            if await join_room(session, structure["levels"][level], token):
                rooms_joined += 1
                # Set student power level (0)
                await set_power_level(session, structure["levels"][level], user["user_id"], 0)
        
        # Join all subject rooms for this level
        if level in structure["subject_rooms"]:
            print(f"  📖 Joining {len(structure['subject_rooms'][level])} subject rooms...")
            for room_id in structure["subject_rooms"][level]:
                if await join_room(session, room_id, token):
                    rooms_joined += 1
                    await set_power_level(session, room_id, user["user_id"], 0)
        
        # Join parent space (read-only access for students)
        if structure["parent_space"]:
            print(f"  👨‍👩‍👧 Joining parent space...")
            if await join_room(session, structure["parent_space"], token):
                rooms_joined += 1
                await set_power_level(session, structure["parent_space"], user["user_id"], 0)
    
    elif user["role"] == "teacher":
        # Join all P-level spaces
        print(f"  📚 Joining all level spaces...")
        for level, space_id in structure["levels"].items():
            if await join_room(session, space_id, token):
                rooms_joined += 1
                await set_power_level(session, space_id, user["user_id"], 50)
        
        # Join all subject rooms
        print(f"  📖 Joining all subject rooms...")
        for level, room_ids in structure["subject_rooms"].items():
            for room_id in room_ids:
                if await join_room(session, room_id, token):
                    rooms_joined += 1
                    await set_power_level(session, room_id, user["user_id"], 50)
        
        # Join teacher space
        if structure["teacher_space"]:
            print(f"  👨‍🏫 Joining teacher space...")
            if await join_room(session, structure["teacher_space"], token):
                rooms_joined += 1
                await set_power_level(session, structure["teacher_space"], user["user_id"], 50)
        
        # Join admin space (read-only for teachers)
        if structure["admin_space"]:
            print(f"  🏫 Joining admin space...")
            if await join_room(session, structure["admin_space"], token):
                rooms_joined += 1
                await set_power_level(session, structure["admin_space"], user["user_id"], 50)
    
    elif user["role"] == "parent":
        # Join parent space
        if structure["parent_space"]:
            print(f"  👨‍👩‍👧 Joining parent space...")
            if await join_room(session, structure["parent_space"], token):
                rooms_joined += 1
                await set_power_level(session, structure["parent_space"], user["user_id"], 15)
        
        # Join all level spaces (read-only)
        print(f"  📚 Joining level spaces (read-only)...")
        for level, space_id in structure["levels"].items():
            if await join_room(session, space_id, token):
                rooms_joined += 1
                await set_power_level(session, space_id, user["user_id"], 15)
    
    print(f"  ✅ Joined {rooms_joined} rooms")
    return True

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 join_users_to_rooms.py <school_name>")
        sys.exit(1)
    
    school_name = sys.argv[1]
    
    print("=" * 80)
    print(f"JOINING USERS TO ROOMS FOR: {school_name}")
    print("=" * 80)
    
    # Get school structure
    print("\n📋 Loading school structure...")
    structure = get_school_structure(school_name)
    if not structure:
        print(f"❌ School '{school_name}' not found in database")
        sys.exit(1)
    
    print(f"  ✅ Found {len(structure['levels'])} levels")
    print(f"  ✅ Found {sum(len(rooms) for rooms in structure['subject_rooms'].values())} subject rooms")
    
    # Get users
    print("\n👥 Loading users...")
    users = get_users_with_credentials(school_name)
    if not users:
        print(f"❌ No users found for '{school_name}'")
        sys.exit(1)
    
    print(f"  ✅ Found {len(users)} users")
    students = [u for u in users if u["role"] == "student"]
    teachers = [u for u in users if u["role"] == "teacher"]
    parents = [u for u in users if u["role"] == "parent"]
    print(f"     - {len(students)} students")
    print(f"     - {len(teachers)} teachers")
    print(f"     - {len(parents)} parents")
    
    # Join users to rooms
    async with aiohttp.ClientSession() as session:
        for i, user in enumerate(users, 1):
            print(f"\n[{i}/{len(users)}]", end=" ")
            await join_user_to_rooms(session, user, structure)
            await asyncio.sleep(2)  # Delay to avoid rate limiting
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE! All users have been joined to their rooms")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
