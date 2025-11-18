#!/usr/bin/env python3
"""
Simple script to join bulk created users to Test School rooms
"""

import asyncio
import aiohttp
import sqlite3
import csv
import sys

SYNAPSE_URL = "http://local.synapse.server:8008"
BOT_TOKEN = "syt_c3BhY2VzLWJvdA_vWEpGsAKjZYSYUBWvcQS_3keCxk"
DB_PATH = "/bot/data/spaces.db"
CSV_PATH = "/bot/data/bulk_created_users.csv"

async def login_user(session, username, password):
    """Login as user to get access token"""
    url = f"{SYNAPSE_URL}/_matrix/client/v3/login"
    data = {
        "type": "m.login.password",
        "identifier": {
            "type": "m.id.user",
            "user": f"@{username}:local.synapse.server"
        },
        "password": password
    }
    
    try:
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("access_token")
            elif resp.status == 429:
                retry_data = await resp.json()
                retry_after = retry_data.get("retry_after_ms", 5000) / 1000
                print(f"    Rate limited, waiting {retry_after:.1f}s...")
                await asyncio.sleep(retry_after + 1)
                return await login_user(session, username, password)
    except Exception as e:
        print(f"    Login failed: {e}")
    return None

async def join_room(session, room_id, token):
    """Join a room"""
    url = f"{SYNAPSE_URL}/_matrix/client/v3/join/{room_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        async with session.post(url, headers=headers) as resp:
            return resp.status == 200
    except:
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
    print(f"JOINING USERS TO {school_name}")
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
        with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:  # utf-8-sig strips BOM
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
            password = student['password']
            level = student['level']
            name = student['display_name']
            
            print(f"\n[{i}/{len(students)}] {name}")
            
            # Login
            token = await login_user(session, username, password)
            if not token:
                print("    FAILED to login")
                continue
            
            # Join level space
            if level in structure:
                space_id = structure[level]['space_id']
                if await join_room(session, space_id, token):
                    print(f"    ✓ Joined {level} space")
                
                # Join all subject rooms
                joined = 0
                for room_id in structure[level]['rooms']:
                    if await join_room(session, room_id, token):
                        joined += 1
                    await asyncio.sleep(0.2)
                print(f"    ✓ Joined {joined}/{len(structure[level]['rooms'])} rooms")
            
            await asyncio.sleep(1)
        
        # Join teachers to ALL rooms
        print("\n" + "=" * 80)
        print("JOINING TEACHERS")
        print("=" * 80)
        for i, teacher in enumerate(teachers, 1):
            username = teacher['username']
            password = teacher['password']
            name = teacher['display_name']
            
            print(f"\n[{i}/{len(teachers)}] {name}")
            
            token = await login_user(session, username, password)
            if not token:
                print("    FAILED to login")
                continue
            
            total_rooms = 0
            for level, data in structure.items():
                if await join_room(session, data['space_id'], token):
                    total_rooms += 1
                for room_id in data['rooms']:
                    if await join_room(session, room_id, token):
                        total_rooms += 1
                    await asyncio.sleep(0.1)
            
            print(f"    ✓ Joined {total_rooms} rooms/spaces")
            await asyncio.sleep(1)
    
    print("\n" + "=" * 80)
    print("COMPLETE!")
    print("=" * 80)
    print("\nUsers can now see their rooms in Element!")

if __name__ == "__main__":
    asyncio.run(main())
