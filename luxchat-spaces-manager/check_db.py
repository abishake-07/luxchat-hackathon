#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/bot/data/spaces.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("=== TABLES IN DATABASE ===")
for table in tables:
    print(f"- {table[0]}")

# Get schema for parent_students
print("\n=== PARENT_STUDENTS SCHEMA ===")
cursor.execute("PRAGMA table_info(parent_students)")
for col in cursor.fetchall():
    print(f"{col[1]} ({col[2]})")

# Check parent_students data
print("\n=== PARENT-STUDENT RELATIONSHIPS (First 10) ===")
cursor.execute("SELECT * FROM parent_students LIMIT 10")
for row in cursor.fetchall():
    print(row)

# Check users table for names
print("\n=== USERS (First 10) ===")
cursor.execute("SELECT user_id, display_name FROM users LIMIT 10")
for row in cursor.fetchall():
    print(f"{row[0]} -> {row[1]}")

conn.close()
