#!/usr/bin/env python3
"""
View parent-student relationships for a school
"""

import sqlite3
import sys

DB_PATH = "/bot/data/spaces.db"

def view_relationships(school_name="Test School", level=None):
    """Display parent-student relationships"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get school_id
    cursor.execute("SELECT school_id FROM schools WHERE school_name = ?", (school_name,))
    result = cursor.fetchone()
    if not result:
        print(f"ERROR: School '{school_name}' not found!")
        conn.close()
        return
    
    school_id = result[0]
    
    print("=" * 80)
    print(f"PARENT-STUDENT RELATIONSHIPS: {school_name}")
    print("=" * 80)
    
    # Get all relationships
    if level:
        query = """
            SELECT ps.parent_user_id, ps.student_user_id, ps.relationship
            FROM parent_students ps
            WHERE ps.student_user_id LIKE ?
            ORDER BY ps.parent_user_id
        """
        cursor.execute(query, (f"%{level.lower()}%",))
    else:
        query = """
            SELECT ps.parent_user_id, ps.student_user_id, ps.relationship
            FROM parent_students ps
            ORDER BY ps.parent_user_id
        """
        cursor.execute(query)
    
    relationships = cursor.fetchall()
    
    if not relationships:
        print("\nNo relationships found!")
        conn.close()
        return
    
    # Group by parent
    parent_children = {}
    for parent_id, student_id, relationship in relationships:
        if parent_id not in parent_children:
            parent_children[parent_id] = []
        parent_children[parent_id].append((student_id, relationship))
    
    print(f"\nTotal: {len(parent_children)} parents, {len(relationships)} students\n")
    
    # Display relationships
    for i, (parent_id, children) in enumerate(parent_children.items(), 1):
        # Extract display name from user_id
        parent_name = parent_id.split('@')[1].split(':')[0].replace('.', ' ').title()
        
        print(f"[{i}] 👨‍👩‍👧 {parent_name} ({parent_id})")
        for student_id, relationship in children:
            student_name = student_id.split('@')[1].split(':')[0]
            # Extract level from student_id (e.g., .p1, .p2)
            if '.' in student_name:
                level_part = student_name.split('.')[-1].upper()
                display_name = ' '.join(student_name.split('.')[:-1]).title()
                print(f"   └─ {display_name} - {level_part} ({student_id})")
            else:
                print(f"   └─ {student_name} ({student_id})")
        print()
    
    conn.close()

def view_by_student(school_name="Test School"):
    """Display relationships organized by student"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get school_id
    cursor.execute("SELECT school_id FROM schools WHERE school_name = ?", (school_name,))
    result = cursor.fetchone()
    if not result:
        print(f"ERROR: School '{school_name}' not found!")
        conn.close()
        return
    
    school_id = result[0]
    
    print("=" * 80)
    print(f"STUDENTS AND THEIR PARENTS: {school_name}")
    print("=" * 80)
    
    # Get all relationships
    cursor.execute("""
        SELECT student_user_id, parent_user_id
        FROM parent_students
        ORDER BY student_user_id
    """)
    
    relationships = cursor.fetchall()
    
    if not relationships:
        print("\nNo relationships found!")
        conn.close()
        return
    
    print(f"\nTotal: {len(relationships)} students\n")
    
    # Group by level
    levels = {}
    for student_id, parent_id in relationships:
        student_name = student_id.split('@')[1].split(':')[0]
        if '.' in student_name:
            level = student_name.split('.')[-1].upper()
            if level not in levels:
                levels[level] = []
            display_name = ' '.join(student_name.split('.')[:-1]).title()
            parent_name = parent_id.split('@')[1].split(':')[0].replace('.', ' ').title()
            levels[level].append((display_name, student_id, parent_name, parent_id))
    
    # Display by level
    for level in sorted(levels.keys()):
        print(f"📚 {level}:")
        for student_name, student_id, parent_name, parent_id in sorted(levels[level]):
            print(f"   • {student_name} → Parent: {parent_name}")
        print()
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "by-student":
            view_by_student()
        elif sys.argv[1] == "level":
            level = sys.argv[2] if len(sys.argv) > 2 else None
            view_relationships(level=level)
        else:
            view_relationships()
    else:
        view_relationships()
        print("\n" + "=" * 80)
        print("Other views:")
        print("  python3 view_parent_relationships.py by-student  # Group by student")
        print("  python3 view_parent_relationships.py level P1    # Filter by level")
        print("=" * 80)
