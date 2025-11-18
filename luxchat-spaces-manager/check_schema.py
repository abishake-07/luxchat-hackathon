#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/bot/data/spaces.db')
cursor = conn.cursor()

print("=" * 80)
print("CURRENT DATABASE SCHEMA")
print("=" * 80)

cursor.execute('SELECT name, sql FROM sqlite_master WHERE type="table"')
for name, sql in cursor.fetchall():
    print(f"\nTable: {name}")
    print("-" * 80)
    print(sql)
    print()

conn.close()
