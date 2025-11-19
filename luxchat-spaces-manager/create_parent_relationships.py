#!/usr/bin/env python3
"""
Create parent-student relationships for bulk created users
"""

import sqlite3
import csv
import random

DB_PATH = "/bot/data/spaces.db"
CSV_PATH = "/bot/data/bulk_created_users.csv"

def setup_relationships():
    """Assign students to parents randomly"""
    
    # Load users from CSV
    print("Loading users from CSV...")
    students = []
    parents = []
    
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = f"@{row['username']}:local.synapse.server"
            if row['role'] == 'student':
                students.append({
                    'user_id': user_id,
                    'name': row['display_name'],
                    'level': row['level']
                })
            elif row['role'] == 'parent':
                parents.append({
                    'user_id': user_id,
                    'name': row['display_name']
                })
    
    print(f"Found {len(students)} students and {len(parents)} parents")
    
    # Get school_id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT school_id FROM schools WHERE school_name = 'Test School'")
    result = cursor.fetchone()
    if not result:
        print("ERROR: Test School not found!")
        conn.close()
        return
    
    school_id = result[0]
    
    # Check if parent_students table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='parent_students'
    """)
    
    if not cursor.fetchone():
        print("\nCreating parent_students table...")
        cursor.execute("""
            CREATE TABLE parent_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_user_id TEXT NOT NULL,
                student_user_id TEXT NOT NULL,
                relationship TEXT DEFAULT 'parent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX idx_parent_student ON parent_students(parent_user_id, student_user_id)
        """)
        conn.commit()
        print("  ✓ Table created")
    else:
        # Table exists, clear it
        cursor.execute("DELETE FROM parent_students")
    
    # Shuffle students and assign to parents (5-6 students per parent)
    random.shuffle(students)
    students_per_parent = len(students) // len(parents)
    
    print(f"\nAssigning ~{students_per_parent} students per parent...\n")
    
    relationships = []
    student_idx = 0
    
    for parent in parents:
        # Assign 5-6 students to this parent
        num_children = students_per_parent
        if student_idx + num_children > len(students):
            num_children = len(students) - student_idx
        
        parent_children = students[student_idx:student_idx + num_children]
        student_idx += num_children
        
        print(f"👨‍👩‍👧 {parent['name']}")
        for child in parent_children:
            cursor.execute("""
                INSERT INTO parent_students (parent_user_id, student_user_id, relationship)
                VALUES (?, ?, 'parent')
            """, (parent['user_id'], child['user_id']))
            
            relationships.append({
                'parent': parent['name'],
                'parent_id': parent['user_id'],
                'student': child['name'],
                'student_id': child['user_id'],
                'level': child['level']
            })
            print(f"   └─ {child['name']} ({child['level']})")
        print()
    
    conn.commit()
    
    # Export relationships to CSV
    csv_output = "/bot/data/parent_student_relationships.csv"
    print(f"Saving relationships to {csv_output}...")
    
    with open(csv_output, 'w', encoding='utf-8') as f:
        f.write("parent_name,parent_user_id,student_name,student_user_id,student_level\n")
        for rel in relationships:
            f.write(f"{rel['parent']},{rel['parent_id']},{rel['student']},{rel['student_id']},{rel['level']}\n")
    
    print(f"  ✓ Saved {len(relationships)} relationships")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✓ COMPLETE!")
    print("=" * 80)
    print(f"\nCreated {len(relationships)} parent-student relationships")
    print(f"Relationships saved to: {csv_output}")
    print("\nTeachers can now see who the parent of each student is!")

if __name__ == "__main__":
    setup_relationships()
