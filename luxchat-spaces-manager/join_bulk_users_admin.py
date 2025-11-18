#!/usr/bin/env python3
"""
Join bulk created users to rooms using Admin API (no login required!)
"""

import asyncio
import aiohttp
import sqlite3
import csv

SYNAPSE_URL = "http://local.synapse.server:8008"
ADMIN_TOKEN = "syt_YWRtaW4_DbZLNrxCeFIbyAXAPtln_0AuBvM"  # Admin token
DB_PATH = "/bot/data/spaces.db"
CSV_PATH = "/bot/data/bulk_created_users.csv"

async def join_user_to_room_admin(session, user_id, room_id):
    """Join a user to a room using admin API"""
    url = f"{SYNAPSE_URL}/_synapse/admin/v1/join/{room_id}"
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    data = {"user_id": user_id}
    
    try:
        async with session.post(url, headers=headers, json=data) as resp:
            if resp.status == 200:
                return True
            else:
                error = await resp.text()
                # Ignore "already in room" errors
                if "already in the room" not in error.lower():
                    print(f"      Failed: {error[:100]}")
                return False
    except Exception as e:
        print(f"      Error: {e}")
        return False

def get_school_rooms(school_name):
    """Get all rooms for Test School"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get school
    cursor.execute("SELECT school_id, root_space_id FROM schools WHERE school_name = ?", (school_name,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return None
    
    school_id, root_space_id = result
    
    # Get all level spaces
    cursor.execute("SELECT space_id, space_name FROM spaces WHERE parent_space_id = ?", (root_space_id,))
    levels = {}
    for space_id, space_name in cursor.fetchall():
        levels[space_name] = {"space_id": space_id, "rooms": []}
    
    # Get all subject rooms for each level
    for level_name, level_data in levels.items():
        cursor.execute("SELECT room_id FROM subject_rooms WHERE space_id = ?", (level_data["space_id"],))
        level_data["rooms"] = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return levels

async def main():
    school_name = "Test School"
    
    print("=" * 80)
    print(f"JOINING USERS TO {school_name} (ADMIN API)")
    print("=" * 80)
    
    # Load school structure
    print("\nLoading school structure...")
    structure = get_school_rooms(school_name)
    if not structure:
        print(f"ERROR: School '{school_name}' not found!")
        return
    
    print(f"Found {len(structure)} levels")
    for level, data in structure.items():
        print(f"  - {level}: {len(data['rooms'])} rooms")
    
    # Load users from CSV
    print("\nLoading users from CSV...")
    users = []
    try:
        with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append(row)
    except FileNotFoundError:
        print(f"ERROR: CSV not found at {CSV_PATH}")
        return
    
    students = [u for u in users if u['role'] == 'student']
    teachers = [u for u in users if u['role'] == 'teacher']
    parents = [u for u in users if u['role'] == 'parent']
    
    print(f"Found {len(users)} users:")
    print(f"  - {len(students)} students")
    print(f"  - {len(teachers)} teachers")
    print(f"  - {len(parents)} parents")
    
    async with aiohttp.ClientSession() as session:
        # Join students
        print("\n" + "=" * 80)
        print("JOINING STUDENTS")
        print("=" * 80)
        for i, student in enumerate(students, 1):
            username = student['username']
            level = student['level']
            name = student['display_name']
            user_id = f"@{username}:local.synapse.server"
            
            print(f"\n[{i}/{len(students)}] {name}")
            
            # Join level space
            if level in structure:
                space_id = structure[level]['space_id']
                if await join_user_to_room_admin(session, user_id, space_id):
                    print(f"    ✓ Joined {level} space")
                
                # Join all subject rooms
                joined = 0
                for room_id in structure[level]['rooms']:
                    if await join_user_to_room_admin(session, user_id, room_id):
                        joined += 1
                    await asyncio.sleep(0.1)
                print(f"    ✓ Joined {joined}/{len(structure[level]['rooms'])} rooms")
            else:
                print(f"    ⚠ Level {level} not found in structure!")
        
        # Join teachers to ALL rooms
        print("\n" + "=" * 80)
        print("JOINING TEACHERS")
        print("=" * 80)
        for i, teacher in enumerate(teachers, 1):
            username = teacher['username']
            name = teacher['display_name']
            user_id = f"@{username}:local.synapse.server"
            
            print(f"\n[{i}/{len(teachers)}] {name}")
            
            total_joined = 0
            for level, data in structure.items():
                # Join level space
                if await join_user_to_room_admin(session, user_id, data['space_id']):
                    total_joined += 1
                
                # Join all rooms in this level
                for room_id in data['rooms']:
                    if await join_user_to_room_admin(session, user_id, room_id):
                        total_joined += 1
                    await asyncio.sleep(0.1)
            
            print(f"    ✓ Joined {total_joined} rooms/spaces")
        
        # Join parents to level spaces (read-only)
        print("\n" + "=" * 80)
        print("JOINING PARENTS")
        print("=" * 80)
        for i, parent in enumerate(parents, 1):
            username = parent['username']
            name = parent['display_name']
            user_id = f"@{username}:local.synapse.server"
            
            print(f"\n[{i}/{len(parents)}] {name}")
            
            total_joined = 0
            for level, data in structure.items():
                if await join_user_to_room_admin(session, user_id, data['space_id']):
                    total_joined += 1
                await asyncio.sleep(0.1)
            
            print(f"    ✓ Joined {total_joined} level spaces")
    
    print("\n" + "=" * 80)
    print("✓ COMPLETE!")
    print("=" * 80)
    print("\nAll users have been added to their rooms!")
    print("They can now see the rooms in Element at http://localhost:8008")

if __name__ == "__main__":
    asyncio.run(main())
