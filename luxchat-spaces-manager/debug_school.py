#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/bot/data/spaces.db')
cursor = conn.cursor()

# Get school info
cursor.execute("SELECT school_id, root_space_id, school_type FROM schools WHERE school_name = 'Test School'")
school = cursor.fetchone()
print(f"School: id={school[0]}, root={school[1]}, type={school[2]}")

# Get root space
cursor.execute("SELECT space_id, space_name, space_type FROM spaces WHERE space_id = ?", (school[1],))
root = cursor.fetchone()
print(f"\nRoot space: {root}")

# Get child spaces
cursor.execute("SELECT space_id, space_name, space_type FROM spaces WHERE parent_space_id = ?", (school[1],))
children = cursor.fetchall()
print(f"\nChild spaces ({len(children)}):")
for child in children:
    print(f"  {child}")
    
    # Get rooms under this child space
    cursor.execute("SELECT room_id, room_name, subject FROM subject_rooms WHERE space_id = ?", (child[0],))
    rooms = cursor.fetchall()
    if rooms:
        print(f"    Rooms ({len(rooms)}):")
        for room in rooms:
            print(f"      {room}")

conn.close()
