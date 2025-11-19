#!/usr/bin/env python3
"""
Set custom profile fields to display parent-student relationships
Uses Matrix Client API to set custom profile fields
"""

import asyncio
import aiohttp
import sqlite3
import csv

SYNAPSE_URL = "http://local.synapse.server:8008"
ADMIN_TOKEN = "syt_YWRtaW4_DbZLNrxCeFIbyAXAPtln_0AuBvM"
DB_PATH = "/bot/data/spaces.db"
CSV_PATH = "/bot/data/bulk_created_users.csv"


async def set_profile_field(session, user_id, field_name, field_value, access_token):
    """Set a custom profile field for a user"""
    url = f"{SYNAPSE_URL}/_matrix/client/v3/profile/{user_id}/{field_name}"
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {field_name: field_value}
    
    try:
        async with session.put(url, headers=headers, json=data) as resp:
            if resp.status == 200:
                return True
            else:
                error = await resp.text()
                print(f"      Failed to set {field_name}: {error[:100]}")
                return False
    except Exception as e:
        print(f"      Error: {e}")
        return False


async def get_user_token_admin(session, user_id):
    """Get an access token for a user using admin API (impersonation)"""
    # For setting profile fields, we need actual user tokens
    # Admin API doesn't support setting custom profile fields directly
    # We'll use the stored passwords to login
    return None


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
        print(f"    Login error: {e}")
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


def get_relationships():
    """Get all parent-student relationships from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT parent_user_id, student_user_id, relationship
        FROM parent_students
    """)
    
    relationships = cursor.fetchall()
    conn.close()
    
    # Organize by parent and by student
    by_parent = {}
    by_student = {}
    
    for parent_id, student_id, rel in relationships:
        if parent_id not in by_parent:
            by_parent[parent_id] = []
        by_parent[parent_id].append(student_id)
        
        by_student[student_id] = parent_id
    
    return by_parent, by_student


async def set_parent_info_for_student(session, student_id, parent_display_name, token):
    """Set parent information in student's profile"""
    # Set custom field showing parent name
    success = await set_profile_field(
        session, 
        student_id, 
        "parent_contact",
        parent_display_name,
        token
    )
    return success


async def set_children_info_for_parent(session, parent_id, children_names, token):
    """Set children information in parent's profile"""
    # Set custom field showing children names
    children_str = ", ".join(children_names)
    success = await set_profile_field(
        session,
        parent_id,
        "children",
        children_str,
        token
    )
    return success


async def main():
    print("=" * 80)
    print("SETTING PROFILE RELATIONSHIP FIELDS")
    print("=" * 80)
    
    # Load users and credentials
    print("\n📋 Loading users from CSV...")
    users = load_users_from_csv()
    print(f"  ✅ Loaded {len(users)} users")
    
    # Load relationships
    print("\n👨‍👩‍👧 Loading parent-student relationships...")
    by_parent, by_student = get_relationships()
    print(f"  ✅ Found {len(by_parent)} parents with {len(by_student)} students")
    
    async with aiohttp.ClientSession() as session:
        # Update student profiles with parent info
        print("\n📝 Setting parent info for students...")
        for i, (student_id, parent_id) in enumerate(by_student.items(), 1):
            if student_id not in users or parent_id not in users:
                continue
            
            student_name = users[student_id]['display_name']
            parent_name = users[parent_id]['display_name']
            
            print(f"  [{i}/{len(by_student)}] {student_name} → Parent: {parent_name}")
            
            # Login as student
            token = await login_user(session, users[student_id]['username'], users[student_id]['password'])
            if not token:
                print(f"      ⚠️ Failed to login")
                continue
            
            # Set parent field
            if await set_parent_info_for_student(session, student_id, parent_name, token):
                print(f"      ✓ Set parent field")
            else:
                print(f"      ⚠️ Failed to set parent field")
            
            await asyncio.sleep(0.2)
        
        # Update parent profiles with children info
        print("\n📝 Setting children info for parents...")
        for i, (parent_id, student_ids) in enumerate(by_parent.items(), 1):
            if parent_id not in users:
                continue
            
            parent_name = users[parent_id]['display_name']
            children_names = [users[sid]['display_name'].split(' - ')[0] for sid in student_ids if sid in users]
            
            print(f"  [{i}/{len(by_parent)}] {parent_name} → {len(children_names)} children")
            
            # Login as parent
            token = await login_user(session, users[parent_id]['username'], users[parent_id]['password'])
            if not token:
                print(f"      ⚠️ Failed to login")
                continue
            
            # Set children field
            if await set_children_info_for_parent(session, parent_id, children_names, token):
                print(f"      ✓ Set children field: {', '.join(children_names[:3])}...")
            else:
                print(f"      ⚠️ Failed to set children field")
            
            await asyncio.sleep(0.2)
    
    print("\n" + "=" * 80)
    print("✓ COMPLETE!")
    print("=" * 80)
    print("\nProfile fields have been set!")
    print("\n📱 How to view in Element:")
    print("  1. Click on any user's avatar in a room")
    print("  2. View their profile")
    print("  3. Look for 'parent_contact' or 'children' fields")
    print("\n⚠️ Note: Element may not display custom profile fields by default.")
    print("   Teachers can query via bot commands instead.")


if __name__ == "__main__":
    asyncio.run(main())
