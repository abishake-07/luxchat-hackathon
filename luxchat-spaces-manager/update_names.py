#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/bot/data/spaces.db')
cursor = conn.cursor()

# Update P1 students
updates = [
    ('@peter.williams.p1:local.synapse.server', 'Luc Weber'),
    ('@bob.brown.p1:local.synapse.server', 'Marie Muller'),
    ('@frank.johnson.p1:local.synapse.server', 'Tom Schmit'),
    ('@grace.johnson.p1:local.synapse.server', 'Anna Jung'),
    ('@bob.smith.p1:local.synapse.server', 'Max Becker'),
    
    # Update P2 students
    ('@charlie.rodriguez.p2:local.synapse.server', 'Sophie Klein'),
    ('@sam.rodriguez.p2:local.synapse.server', 'Jean Wagner'),
    ('@charlie.smith.p2:local.synapse.server', 'Lisa Hoffmann'),
    ('@bob.miller.p2:local.synapse.server', 'Paul Fischer'),
    ('@alice.martinez.p2:local.synapse.server', 'Emma Koller'),
]

print("Updating display names in users table...")
for user_id, new_name in updates:
    cursor.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (new_name, user_id))
    print(f"  {user_id} -> {new_name}")

conn.commit()

# Verify updates
print("\n=== UPDATED USERS (First 10) ===")
cursor.execute("SELECT user_id, display_name FROM users LIMIT 10")
for row in cursor.fetchall():
    print(f"{row[0]} -> {row[1]}")

conn.close()
print("\n✅ Database updated successfully!")
