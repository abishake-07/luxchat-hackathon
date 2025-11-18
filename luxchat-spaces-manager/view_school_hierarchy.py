#!/usr/bin/env python3
"""
View the complete school hierarchy from the database
"""

import sqlite3
from collections import defaultdict

def view_hierarchy():
    conn = sqlite3.connect('/bot/data/spaces.db')
    cursor = conn.cursor()
    
    # Get all schools
    cursor.execute('SELECT school_name, school_type, root_space_id FROM schools')
    schools = cursor.fetchall()
    
    print("=" * 80)
    print("SCHOOLS IN DATABASE")
    print("=" * 80)
    
    for school_name, school_type, root_space_id in schools:
        print(f"\n🏫 {school_name} ({school_type})")
        print(f"   Root Space ID: {root_space_id}")
        
        # Get all spaces for this school
        cursor.execute('''
            SELECT space_id, space_name, space_type, parent_space_id, cycle_number, year_number
            FROM spaces
            WHERE space_id = ? OR parent_space_id IN (
                SELECT space_id FROM spaces WHERE space_id = ? OR parent_space_id = ?
            )
            ORDER BY cycle_number, year_number
        ''', (root_space_id, root_space_id, root_space_id))
        
        spaces = cursor.fetchall()
        
        # Build hierarchy
        space_dict = {}
        for space in spaces:
            space_id, space_name, space_type, parent_id, cycle, year = space
            space_dict[space_id] = {
                'name': space_name,
                'type': space_type,
                'parent': parent_id,
                'cycle': cycle,
                'year': year,
                'children': []
            }
        
        # Get rooms for each space
        cursor.execute('''
            SELECT room_id, room_name, subject, space_id
            FROM subject_rooms
        ''')
        rooms = cursor.fetchall()
        
        rooms_by_space = defaultdict(list)
        for room_id, room_name, subject, space_id in rooms:
            rooms_by_space[space_id].append({
                'id': room_id,
                'name': room_name,
                'subject': subject
            })
        
        # Print hierarchy
        print(f"\n   📊 HIERARCHY:")
        print(f"   {'─' * 70}")
        
        def print_space(space_id, indent=1):
            if space_id not in space_dict:
                return
            
            space = space_dict[space_id]
            prefix = "   " + "  " * indent
            
            # Icon based on type
            icon = {
                'school': '🏫',
                'cycle': '🎓',
                'year': '📚',
                'admin': '👥',
                'parents': '👨‍👩‍👧‍👦'
            }.get(space['type'], '📁')
            
            print(f"{prefix}{icon} {space['name']}")
            print(f"{prefix}   ID: {space_id}")
            
            # Print rooms in this space
            if space_id in rooms_by_space:
                for room in rooms_by_space[space_id]:
                    print(f"{prefix}   └── 📖 {room['name']} ({room['id']})")
            
            # Print child spaces
            for sid, s in space_dict.items():
                if s['parent'] == space_id:
                    print_space(sid, indent + 1)
        
        print_space(root_space_id)
        
        # Statistics
        total_spaces = len(spaces)
        total_rooms = sum(len(rooms) for rooms in rooms_by_space.values())
        
        print(f"\n   📈 STATISTICS:")
        print(f"   {'─' * 70}")
        print(f"   Total Spaces: {total_spaces}")
        print(f"   Total Rooms: {total_rooms}")
        
        # Count by cycle
        cursor.execute('''
            SELECT cycle_number, COUNT(*)
            FROM spaces
            WHERE cycle_number IS NOT NULL
            GROUP BY cycle_number
        ''')
        cycle_counts = cursor.fetchall()
        
        if cycle_counts:
            print(f"\n   Spaces by Cycle:")
            for cycle, count in cycle_counts:
                print(f"   - Cycle {cycle}: {count} spaces")
        
        print("\n" + "=" * 80)
    
    conn.close()

if __name__ == "__main__":
    view_hierarchy()
