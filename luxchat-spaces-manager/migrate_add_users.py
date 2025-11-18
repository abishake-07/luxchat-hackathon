#!/usr/bin/env python3
"""
Database migration to add user roles and permissions tables
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database(db_path='/bot/data/spaces.db'):
    """Add user, role, and permission tables to existing database"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    logger.info("Starting database migration...")
    
    try:
        # 1. Users table
        logger.info("Creating users table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                email TEXT,
                role TEXT NOT NULL CHECK(role IN ('student', 'parent', 'teacher', 'head_of_department', 'administrator')),
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Room memberships with power levels
        logger.info("Creating room_memberships table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS room_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                room_id TEXT NOT NULL,
                power_level INTEGER DEFAULT 0 CHECK(power_level >= 0 AND power_level <= 100),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, room_id)
            )
        ''')
        
        # 3. Student enrollments
        logger.info("Creating enrollments table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                cycle_number INTEGER NOT NULL,
                year_number INTEGER NOT NULL,
                school_id TEXT NOT NULL,
                academic_year TEXT,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unenrolled_at TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE
            )
        ''')
        
        # 4. Teacher assignments to subject rooms
        logger.info("Creating teacher_assignments table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id TEXT NOT NULL,
                room_id TEXT NOT NULL,
                subject TEXT,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unassigned_at TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (room_id) REFERENCES subject_rooms(room_id) ON DELETE CASCADE,
                UNIQUE(teacher_id, room_id)
            )
        ''')
        
        # 5. Parent-student relationships
        logger.info("Creating parent_students table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parent_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                relationship TEXT CHECK(relationship IN ('mother', 'father', 'guardian', 'other')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(parent_id, student_id)
            )
        ''')
        
        # 6. Role permissions (predefined)
        logger.info("Creating role_permissions table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL CHECK(role IN ('student', 'parent', 'teacher', 'head_of_department', 'administrator')),
                room_type TEXT NOT NULL CHECK(room_type IN ('subject_room', 'admin_space', 'parent_space', 'teacher_space', 'any')),
                default_power_level INTEGER NOT NULL CHECK(default_power_level >= 0 AND default_power_level <= 100),
                can_invite BOOLEAN DEFAULT 0,
                can_kick BOOLEAN DEFAULT 0,
                can_ban BOOLEAN DEFAULT 0,
                can_redact BOOLEAN DEFAULT 0,
                can_set_name BOOLEAN DEFAULT 0,
                can_set_topic BOOLEAN DEFAULT 0,
                can_set_avatar BOOLEAN DEFAULT 0,
                UNIQUE(role, room_type)
            )
        ''')
        
        # 7. Audit log for role changes
        logger.info("Creating role_audit_log table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                old_role TEXT,
                new_role TEXT NOT NULL,
                changed_by TEXT NOT NULL,
                reason TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default role permissions
        logger.info("Inserting default role permissions...")
        default_permissions = [
            # Students
            ('student', 'subject_room', 0, 0, 0, 0, 0, 0, 0, 0),
            ('student', 'parent_space', 0, 0, 0, 0, 0, 0, 0, 0),  # read-only
            
            # Parents
            ('parent', 'parent_space', 15, 0, 0, 0, 0, 0, 0, 0),
            ('parent', 'subject_room', 0, 0, 0, 0, 0, 0, 0, 0),  # read-only (optional)
            
            # Teachers
            ('teacher', 'subject_room', 50, 1, 1, 0, 1, 1, 1, 0),
            ('teacher', 'teacher_space', 50, 1, 1, 0, 1, 1, 1, 0),
            ('teacher', 'parent_space', 50, 1, 0, 0, 1, 1, 1, 0),
            
            # Head of Department
            ('head_of_department', 'subject_room', 75, 1, 1, 1, 1, 1, 1, 1),
            ('head_of_department', 'teacher_space', 75, 1, 1, 1, 1, 1, 1, 1),
            ('head_of_department', 'admin_space', 50, 1, 0, 0, 1, 1, 1, 0),
            ('head_of_department', 'parent_space', 75, 1, 1, 0, 1, 1, 1, 1),
            
            # Administrator
            ('administrator', 'any', 100, 1, 1, 1, 1, 1, 1, 1),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO role_permissions 
            (role, room_type, default_power_level, can_invite, can_kick, can_ban, can_redact, 
             can_set_name, can_set_topic, can_set_avatar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', default_permissions)
        
        # Create indexes for performance
        logger.info("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memberships_user ON room_memberships(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memberships_room ON room_memberships(room_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_school ON enrollments(school_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_teacher_assignments_teacher ON teacher_assignments(teacher_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_teacher_assignments_room ON teacher_assignments(room_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parent_students_parent ON parent_students(parent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parent_students_student ON parent_students(student_id)')
        
        conn.commit()
        logger.info("✅ Migration completed successfully!")
        
        # Show summary
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Database now has {len(tables)} tables: {', '.join(tables)}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

def show_schema(db_path='/bot/data/spaces.db'):
    """Display the new schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "=" * 80)
    print("UPDATED DATABASE SCHEMA")
    print("=" * 80)
    
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
    for name, sql in cursor.fetchall():
        print(f"\nTable: {name}")
        print("-" * 80)
        if sql:
            print(sql)
    
    print("\n" + "=" * 80)
    print("ROLE PERMISSIONS")
    print("=" * 80)
    
    cursor.execute('''
        SELECT role, room_type, default_power_level, can_invite, can_kick, can_ban, can_redact
        FROM role_permissions
        ORDER BY default_power_level DESC, role
    ''')
    
    print(f"\n{'Role':<20} {'Room Type':<15} {'Power':<6} {'Invite':<7} {'Kick':<5} {'Ban':<5} {'Redact':<7}")
    print("-" * 80)
    for row in cursor.fetchall():
        role, room_type, power, invite, kick, ban, redact = row
        print(f"{role:<20} {room_type:<15} {power:<6} {bool(invite)!s:<7} {bool(kick)!s:<5} {bool(ban)!s:<5} {bool(redact)!s:<7}")
    
    conn.close()

if __name__ == "__main__":
    migrate_database()
    show_schema()
