#!/usr/bin/env python3
"""
Update student display names to include parent information
This makes parent info visible directly in the member list!

Example: "Charlie Williams P1" → "Charlie Williams P1 (Parent: Alice Smith)"
"""

import asyncio
import aiohttp
import sqlite3
import csv

SYNAPSE_URL = "http://local.synapse.server:8008"
DB_PATH = "/bot/data/spaces.db"
CSV_PATH = "/bot/data/bulk_created_users.csv"


async def update_display_name(session, user_id, new_display_name, access_token):
    """Update user's display name"""
    url = f"{SYNAPSE_URL}/_matrix/client/v3/profile/{user_id}/displayname"
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {"displayname": new_display_name}
    
    try:
        async with session.put(url, headers=headers, json=data) as resp:
            if resp.status == 200:
                return True
            else:
                error = await resp.text()
                print(f"      Failed: {error[:100]}")
                return False
    except Exception as e:
        print(f"      Error: {e}")
        return False


async def login_user(session, username, password):
    """Login a user and get access token"""
    url = f"{SYNAPSE_URL}/_matrix/client/v3/login"
    
    data = {
        "type": "m.login.password",
        "identifier": {
            "type": "m.id.user",
            "user": username
        },
        "password": password
    }
    
    try:
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("access_token")
            else:
                return None
    except Exception as e:
        return None


def load_users_from_csv():
    """Load users and their credentials from CSV"""
    users = {}
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        for row in reader:
            # Strip whitespace from keys to handle any formatting issues
            row = {k.strip(): v for k, v in row.items()}
            user_id = f"@{row['username']}:local.synapse.server"
            users[user_id] = {
                'username': row['username'],
                'password': row['password'],
                'display_name': row['display_name'],
                'role': row['role']
            }
    return users


def get_student_parent_mapping():
    """Get mapping of student to parent"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT student_user_id, parent_user_id
        FROM parent_students
    """)
    
    mapping = {}
    for student_id, parent_id in cursor.fetchall():
        mapping[student_id] = parent_id
    
    conn.close()
    return mapping


async def main():
    print("=" * 80)
    print("UPDATE STUDENT DISPLAY NAMES WITH PARENT INFO")
    print("=" * 80)
    
    # Load data
    print("\n📋 Loading users...")
    users = load_users_from_csv()
    
    print("\n👨‍👩‍👧 Loading relationships...")
    student_parent = get_student_parent_mapping()
    print(f"  ✅ Found {len(student_parent)} student-parent relationships")
    
    # Update student display names
    print("\n📝 Updating student display names...")
    
    async with aiohttp.ClientSession() as session:
        for i, (student_id, parent_id) in enumerate(student_parent.items(), 1):
            if student_id not in users or parent_id not in users:
                continue
            
            # Get names
            student_data = users[student_id]
            parent_name = users[parent_id]['display_name'].replace(' - Parent', '')
            
            # Create new display name with parent info
            # Extract just the student name without level
            base_name = student_data['display_name'].split(' - ')[0]  # "Charlie Williams P1"
            level = student_data['display_name'].split(' ')[-1]  # Get P1, P2, etc
            
            new_display_name = f"{base_name} (👨‍👩‍👧 {parent_name})"
            
            print(f"  [{i}/{len(student_parent)}] {base_name}")
            print(f"      Old: {student_data['display_name']}")
            print(f"      New: {new_display_name}")
            
            # Login as student
            token = await login_user(session, student_data['username'], student_data['password'])
            if not token:
                print(f"      ⚠️ Failed to login")
                continue
            
            # Update display name
            if await update_display_name(session, student_id, new_display_name, token):
                print(f"      ✓ Updated display name")
            else:
                print(f"      ⚠️ Failed to update")
            
            await asyncio.sleep(0.3)
    
    print("\n" + "=" * 80)
    print("✓ COMPLETE!")
    print("=" * 80)
    print("\n📱 Parent information now visible in Element!")
    print("\n   Teachers can see parent names directly in:")
    print("   • Room member lists")
    print("   • Chat messages")
    print("   • User profiles")
    print("\n   Format: 'Student Name (👨‍👩‍👧 Parent Name)'")


if __name__ == "__main__":
    asyncio.run(main())
