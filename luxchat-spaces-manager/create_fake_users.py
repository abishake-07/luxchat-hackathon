#!/usr/bin/env python3
"""
Create fake users on Synapse and add them to school rooms
"""

import asyncio
import aiohttp
import sqlite3
import random
import string
import csv
from datetime import datetime

# Configuration
SYNAPSE_URL = "http://local.synapse.server:8008"
ADMIN_TOKEN = "syt_YWRtaW4_DbZLNrxCeFIbyAXAPtln_0AuBvM"  # Your admin token
DB_PATH = "/bot/data/spaces.db"

# Fake user data
FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Emma", "Frank", "Grace", "Henry", "Isabel", "Jack",
               "Kate", "Liam", "Maria", "Noah", "Olivia", "Peter", "Quinn", "Rachel", "Sam", "Tina"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
TEACHER_SUBJECTS = ["German", "English", "Luxembourgish", "Mathematics", "Arts", "Sciences", "Physical Education"]

def generate_password():
    """Generate a random password"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

async def create_synapse_user(session, username, display_name, password):
    """Create a user on Synapse via Admin API"""
    url = f"{SYNAPSE_URL}/_synapse/admin/v2/users/@{username}:local.synapse.server"
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    data = {
        "password": password,
        "displayname": display_name,
        "admin": False
    }
    
    async with session.put(url, headers=headers, json=data) as resp:
        if resp.status in [200, 201]:
            result = await resp.json()
            return result.get("name")
        else:
            error = await resp.text()
            print(f"❌ Failed to create {username}: {error}")
            return None

async def join_user_to_room(session, user_id, room_id, access_token):
    """Join a user to a room"""
    url = f"{SYNAPSE_URL}/_matrix/client/v3/join/{room_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with session.post(url, headers=headers, json={}) as resp:
        return resp.status == 200

async def set_power_level(session, room_id, user_id, power_level):
    """Set power level for a user in a room"""
    url = f"{SYNAPSE_URL}/_synapse/admin/v1/rooms/{room_id}/make_room_admin"
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    data = {"user_id": user_id}
    
    async with session.post(url, headers=headers, json=data) as resp:
        return resp.status == 200

def get_school_rooms(school_name):
    """Get all rooms for a school from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get school
    cursor.execute('SELECT school_id, root_space_id FROM schools WHERE school_name = ?', (school_name,))
    school = cursor.fetchone()
    
    if not school:
        conn.close()
        return None
    
    school_id, root_space_id = school
    
    # Get all spaces
    cursor.execute('''
        SELECT space_id, space_name, space_type 
        FROM spaces 
        WHERE space_id = ? OR parent_space_id = ? OR parent_space_id IN (
            SELECT space_id FROM spaces WHERE parent_space_id = ?
        )
    ''', (root_space_id, root_space_id, root_space_id))
    spaces = cursor.fetchall()
    
    # Get all rooms
    cursor.execute('''
        SELECT sr.room_id, sr.room_name, sr.subject, s.space_name
        FROM subject_rooms sr
        JOIN spaces s ON sr.space_id = s.space_id
        WHERE s.space_id IN (
            SELECT space_id FROM spaces 
            WHERE space_id = ? OR parent_space_id = ? OR parent_space_id IN (
                SELECT space_id FROM spaces WHERE parent_space_id = ?
            )
        )
    ''', (root_space_id, root_space_id, root_space_id))
    rooms = cursor.fetchall()
    
    conn.close()
    return {'school_id': school_id, 'root_space_id': root_space_id, 'spaces': spaces, 'rooms': rooms}

def store_user_in_db(user_id, display_name, email, role):
    """Store user in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (user_id, display_name, email, role)
            VALUES (?, ?, ?, ?)
        ''', (user_id, display_name, email, role))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ DB error for {user_id}: {e}")
        return False
    finally:
        conn.close()

def enroll_student(student_id, school_id, level):
    """Enroll student in a level"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # For primary schools, extract P number (P1 -> 1)
    level_num = int(level.replace('P', '')) if 'P' in level else 1
    
    try:
        cursor.execute('''
            INSERT INTO enrollments (student_id, cycle_number, year_number, school_id, academic_year)
            VALUES (?, ?, ?, ?, ?)
        ''', (student_id, level_num, 1, school_id, "2025-2026"))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Enrollment error: {e}")
        return False
    finally:
        conn.close()

async def create_fake_users(school_name, num_students_per_level=5, num_teachers=5, num_parents=3):
    """Create fake users for a school"""
    
    print(f"\n{'='*80}")
    print(f"CREATING FAKE USERS FOR: {school_name}")
    print(f"{'='*80}\n")
    
    # Get school structure
    school_data = get_school_rooms(school_name)
    if not school_data:
        print(f"❌ School '{school_name}' not found in database")
        return
    
    school_id = school_data['school_id']
    rooms = school_data['rooms']
    spaces = school_data['spaces']
    
    print(f"📊 Found: {len(spaces)} spaces, {len(rooms)} rooms\n")
    
    # Group rooms by level
    rooms_by_level = {}
    for room_id, room_name, subject, space_name in rooms:
        if space_name not in rooms_by_level:
            rooms_by_level[space_name] = []
        rooms_by_level[space_name].append((room_id, room_name, subject))
    
    credentials = []
    
    async with aiohttp.ClientSession() as session:
        
        # Create students for each level
        print("👨‍🎓 Creating students...")
        for level_name, level_rooms in rooms_by_level.items():
            if not level_name.startswith('P'):
                continue
                
            print(f"\n  Level {level_name}:")
            for i in range(num_students_per_level):
                first = random.choice(FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                username = f"{first.lower()}.{last.lower()}.{level_name.lower()}"
                display_name = f"{first} {last}"
                password = generate_password()
                
                user_id = await create_synapse_user(session, username, display_name, password)
                if user_id:
                    print(f"    ✅ {display_name} (@{username})")
                    store_user_in_db(user_id, display_name, f"{username}@school.lu", "student")
                    enroll_student(user_id, school_id, level_name)
                    credentials.append({
                        'username': username,
                        'password': password,
                        'display_name': display_name,
                        'role': 'student',
                        'level': level_name
                    })
                    
                    # Join student to all rooms in their level
                    # (Would need user's access token - skipping for now)
        
        # Create teachers
        print(f"\n👨‍🏫 Creating teachers...")
        for i in range(num_teachers):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            subject = random.choice(TEACHER_SUBJECTS)
            username = f"teacher.{first.lower()}.{last.lower()}"
            display_name = f"{first} {last} ({subject})"
            password = generate_password()
            
            user_id = await create_synapse_user(session, username, display_name, password)
            if user_id:
                print(f"  ✅ {display_name} (@{username})")
                store_user_in_db(user_id, display_name, f"{username}@school.lu", "teacher")
                credentials.append({
                    'username': username,
                    'password': password,
                    'display_name': display_name,
                    'role': 'teacher',
                    'subject': subject
                })
        
        # Create parents
        print(f"\n👨‍👩‍👧 Creating parents...")
        for i in range(num_parents):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            username = f"parent.{first.lower()}.{last.lower()}"
            display_name = f"{first} {last} (Parent)"
            password = generate_password()
            
            user_id = await create_synapse_user(session, username, display_name, password)
            if user_id:
                print(f"  ✅ {display_name} (@{username})")
                store_user_in_db(user_id, display_name, f"{username}@school.lu", "parent")
                credentials.append({
                    'username': username,
                    'password': password,
                    'display_name': display_name,
                    'role': 'parent'
                })
    
    # Save credentials to CSV
    csv_file = f"/bot/data/fake_users_{school_name.replace(' ', '_')}.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['username', 'password', 'display_name', 'role', 'level', 'subject'])
        writer.writeheader()
        writer.writerows(credentials)
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETE!")
    print(f"{'='*80}")
    print(f"Created {len(credentials)} users:")
    print(f"  - Students: {sum(1 for c in credentials if c['role'] == 'student')}")
    print(f"  - Teachers: {sum(1 for c in credentials if c['role'] == 'teacher')}")
    print(f"  - Parents: {sum(1 for c in credentials if c['role'] == 'parent')}")
    print(f"\n📄 Credentials saved to: {csv_file}")
    print(f"\nUsers can now login at: http://localhost:8008")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python create_fake_users.py \"School Name\" [students_per_level] [num_teachers] [num_parents]")
        print("\nExample:")
        print('  python create_fake_users.py "St. Mary\'s Primary School" 10 5 5')
        sys.exit(1)
    
    school_name = sys.argv[1]
    students_per_level = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    num_teachers = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    num_parents = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    
    asyncio.run(create_fake_users(school_name, students_per_level, num_teachers, num_parents))
