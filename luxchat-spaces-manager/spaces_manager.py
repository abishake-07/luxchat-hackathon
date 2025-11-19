#!/usr/bin/env python3
"""
Luxchat Spaces Manager Bot
Creates and manages Matrix spaces for schools, associations, and organizations
"""

import asyncio
import configparser
import logging
import sqlite3
import re
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from nio import AsyncClient, MatrixRoom, RoomMessageText, RoomCreateResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Luxembourg Fundamental Education subject templates
FUNDAMENTAL_SUBJECTS = {
    1: {  # Cycle 1 (Ages 3-5)
        "subjects": ["Luxembourgish", "German", "French", "Éveil aux Sciences", "Psychomotricité", "Arts"],
        "years": 2
    },
    2: {  # Cycle 2 (Ages 5-7)
        "subjects": ["Luxembourgish", "German", "French", "Mathematics", "Sciences", "Arts", "Music", "Sports"],
        "years": 2
    },
    3: {  # Cycle 3 (Ages 7-9)
        "subjects": ["Luxembourgish", "German", "French", "Mathematics", "Natural Sciences", 
                    "Human & Social Sciences", "ICT", "Arts", "Music", "Sports"],
        "years": 2
    },
    4: {  # Cycle 4 (Ages 9-12)
        "subjects": ["Luxembourgish", "German", "French", "English", "Mathematics", 
                    "Natural Sciences", "Human & Social Sciences", "ICT", "Arts", "Music", "Sports"],
        "years": 3
    }
}

# Primary Education subject templates (P1-P5)
PRIMARY_SUBJECTS = {
    "P1": ["German", "English", "Luxembourgish", "Mathematics", "Arts", "Physical Education"],
    "P2": ["German", "English", "Luxembourgish", "Mathematics", "Arts", "Physical Education"],
    "P3": ["German", "English", "Luxembourgish", "Mathematics", "Arts", "Sciences"],
    "P4": ["German", "English", "Luxembourgish", "Mathematics", "Arts", "Sciences"],
    "P5": ["German", "English", "Luxembourgish", "Mathematics", "Arts", "Sciences"]
}


class SpacesDatabase:
    """Manages SQLite database for spaces and rooms"""
    
    def __init__(self, db_path: str = "/bot/data/spaces.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Spaces table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spaces (
                space_id TEXT PRIMARY KEY,
                space_name TEXT NOT NULL,
                space_type TEXT NOT NULL,
                parent_space_id TEXT,
                cycle_number INTEGER,
                year_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_space_id) REFERENCES spaces(space_id)
            )
        ''')
        
        # Subject rooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subject_rooms (
                room_id TEXT PRIMARY KEY,
                room_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                space_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (space_id) REFERENCES spaces(space_id)
            )
        ''')
        
        # School configurations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schools (
                school_id TEXT PRIMARY KEY,
                school_name TEXT NOT NULL,
                school_type TEXT NOT NULL,
                root_space_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (root_space_id) REFERENCES spaces(space_id)
            )
        ''')
        
        # Homework table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS homework (
                homework_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                class_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT,
                assigned_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                class_name TEXT NOT NULL,
                student_name TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                marked_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(class_name, student_name, date)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def add_space(self, space_id: str, space_name: str, space_type: str, 
                  parent_space_id: Optional[str] = None, cycle: Optional[int] = None, 
                  year: Optional[int] = None) -> bool:
        """Add a space to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO spaces (space_id, space_name, space_type, parent_space_id, cycle_number, year_number)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (space_id, space_name, space_type, parent_space_id, cycle, year))
            conn.commit()
            logger.info(f"Added space: {space_name} ({space_id})")
            return True
        except Exception as e:
            logger.error(f"Error adding space: {e}")
            return False
        finally:
            conn.close()
    
    def add_room(self, room_id: str, room_name: str, subject: str, space_id: str) -> bool:
        """Add a room to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO subject_rooms (room_id, room_name, subject, space_id)
                VALUES (?, ?, ?, ?)
            ''', (room_id, room_name, subject, space_id))
            conn.commit()
            logger.info(f"Added room: {room_name} ({room_id}) to space {space_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding room: {e}")
            return False
        finally:
            conn.close()
    
    def add_school(self, school_id: str, school_name: str, school_type: str, root_space_id: str) -> bool:
        """Add a school configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO schools (school_id, school_name, school_type, root_space_id)
                VALUES (?, ?, ?, ?)
            ''', (school_id, school_name, school_type, root_space_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding school: {e}")
            return False
        finally:
            conn.close()
    
    def get_space_hierarchy(self, space_id: str) -> List[Dict]:
        """Get all child spaces and rooms"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get child spaces
        cursor.execute('''
            SELECT space_id, space_name, space_type, cycle_number, year_number
            FROM spaces
            WHERE parent_space_id = ?
            ORDER BY cycle_number, year_number, space_name
        ''', (space_id,))
        spaces = cursor.fetchall()
        
        # Get rooms in this space
        cursor.execute('''
            SELECT room_id, room_name, subject
            FROM subject_rooms
            WHERE space_id = ?
            ORDER BY subject
        ''', (space_id,))
        rooms = cursor.fetchall()
        
        conn.close()
        return {'spaces': spaces, 'rooms': rooms}
    
    def add_homework(self, room_id: str, class_name: str, subject: str, title: str, 
                     description: str, due_date: str, assigned_by: str) -> bool:
        """Add homework assignment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO homework (room_id, class_name, subject, title, description, due_date, assigned_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (room_id, class_name, subject, title, description, due_date, assigned_by))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding homework: {e}")
            return False
        finally:
            conn.close()
    
    def mark_attendance(self, room_id: str, class_name: str, student_name: str, 
                       date: str, status: str, marked_by: str) -> bool:
        """Mark student attendance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO attendance 
                (room_id, class_name, student_name, date, status, marked_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (room_id, class_name, student_name, date, status, marked_by))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking attendance: {e}")
            return False
        finally:
            conn.close()
    
    def get_attendance(self, class_name: str, date: str) -> List[Tuple]:
        """Get attendance for a class on a specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT student_name, status, marked_by, created_at
                FROM attendance
                WHERE class_name = ? AND date = ?
                ORDER BY student_name
            ''', (class_name, date))
            results = cursor.fetchall()
            return results
        finally:
            conn.close()
    
    def get_homework_list(self, class_name: str, limit: int = 10) -> List[Tuple]:
        """Get recent homework for a class"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT homework_id, subject, title, description, due_date, assigned_by, created_at
                FROM homework
                WHERE class_name = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (class_name, limit))
            results = cursor.fetchall()
            return results
        finally:
            conn.close()


class SpacesManagerBot:
    """Bot for managing Matrix spaces"""
    
    def __init__(self, homeserver: str, user_id: str, access_token: str, 
                 device_id: str, management_room: str):
        self.homeserver = homeserver
        self.user_id = user_id
        self.access_token = access_token
        self.device_id = device_id
        self.management_room = management_room
        
        # Initialize client
        self.client = AsyncClient(homeserver, user_id, device_id=device_id)
        
        # Initialize database
        self.db = SpacesDatabase()
        
        # Track bot start time to ignore old messages
        self.start_time = datetime.now()
        
        # Track pending deletion confirmation
        self.pending_deletion = None
        
        # Add callback
        self.client.add_event_callback(self.message_callback, RoomMessageText)
    
    async def create_space(self, name: str, topic: str = "", parent_space_id: Optional[str] = None) -> Optional[str]:
        """Create a Matrix space"""
        try:
            # Create the space using raw API call since matrix-nio doesn't directly support spaces
            # We need to send the creation_content with type: m.space
            import json
            
            url = f"{self.homeserver}/_matrix/client/v3/createRoom"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            initial_state = []
            if parent_space_id:
                initial_state.append({
                    "type": "m.space.parent",
                    "state_key": parent_space_id,
                    "content": {
                        "via": [self.homeserver.replace('http://', '').replace('https://', '').split(':')[0]],
                        "canonical": True
                    }
                })
            
            data = {
                "name": name,
                "topic": topic,
                "visibility": "private",
                "creation_content": {
                    "type": "m.space"
                },
                "initial_state": initial_state
            }
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    result = await resp.json()
                    
                    if resp.status == 200 and "room_id" in result:
                        space_id = result["room_id"]
                        logger.info(f"Created space: {name} ({space_id})")
                        
                        # If this space has a parent, add it as a child to the parent
                        if parent_space_id:
                            await self.add_child_to_space(parent_space_id, space_id)
                        
                        return space_id
                    elif resp.status == 429:
                        # Rate limited - wait and retry
                        retry_ms = result.get('retry_after_ms', 1000)
                        logger.warning(f"Rate limited creating space {name}, waiting {retry_ms}ms")
                        await asyncio.sleep(retry_ms / 1000)
                        # Retry once
                        async with session.post(url, headers=headers, json=data) as retry_resp:
                            retry_result = await retry_resp.json()
                            if retry_resp.status == 200 and "room_id" in retry_result:
                                space_id = retry_result["room_id"]
                                logger.info(f"Created space: {name} ({space_id}) after retry")
                                if parent_space_id:
                                    await self.add_child_to_space(parent_space_id, space_id)
                                return space_id
                            else:
                                logger.error(f"Failed to create space {name} after retry: {retry_result}")
                                return None
                    else:
                        logger.error(f"Failed to create space {name}: {result}")
                        return None
        except Exception as e:
            logger.error(f"Exception creating space {name}: {e}")
            return None
    
    async def add_child_to_space(self, parent_space_id: str, child_id: str):
        """Add a room or space as a child of a space"""
        try:
            await self.client.room_put_state(
                room_id=parent_space_id,
                event_type="m.space.child",
                content={
                    "via": [self.homeserver.replace('http://', '').replace('https://', '').split(':')[0]]
                },
                state_key=child_id
            )
            logger.info(f"Added {child_id} as child of {parent_space_id}")
        except Exception as e:
            logger.error(f"Failed to add child to space: {e}")
    
    async def create_room(self, name: str, topic: str = "", parent_space_id: Optional[str] = None) -> Optional[str]:
        """Create a regular Matrix room"""
        try:
            # Use HTTP API for consistency with space creation
            url = f"{self.homeserver}/_matrix/client/v3/createRoom"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            initial_state = []
            if parent_space_id:
                initial_state.append({
                    "type": "m.space.parent",
                    "state_key": parent_space_id,
                    "content": {
                        "via": [self.homeserver.replace('http://', '').replace('https://', '').split(':')[0]],
                        "canonical": True
                    }
                })
            
            data = {
                "name": name,
                "topic": topic,
                "visibility": "private",
                "initial_state": initial_state
            }
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    result = await resp.json()
                    
                    if resp.status == 200 and "room_id" in result:
                        room_id = result["room_id"]
                        logger.info(f"Created room: {name} ({room_id})")
                        
                        # Add as child to parent space
                        if parent_space_id:
                            await self.add_child_to_space(parent_space_id, room_id)
                        
                        return room_id
                    elif resp.status == 429:
                        # Rate limited - wait and retry
                        retry_ms = result.get('retry_after_ms', 1000)
                        logger.warning(f"Rate limited creating room {name}, waiting {retry_ms}ms")
                        await asyncio.sleep(retry_ms / 1000)
                        # Retry once
                        async with session.post(url, headers=headers, json=data) as retry_resp:
                            retry_result = await retry_resp.json()
                            if retry_resp.status == 200 and "room_id" in retry_result:
                                room_id = retry_result["room_id"]
                                logger.info(f"Created room: {name} ({room_id}) after retry")
                                if parent_space_id:
                                    await self.add_child_to_space(parent_space_id, room_id)
                                return room_id
                            else:
                                logger.error(f"Failed to create room {name} after retry: {retry_result}")
                                return None
                    else:
                        logger.error(f"Failed to create room {name}: {result}")
                        return None
        except Exception as e:
            logger.error(f"Exception creating room {name}: {e}")
            return None
    
    async def invite_admin(self, room_id: str):
        """Invite admin user to a room/space"""
        admin_user = "@admin:local.synapse.server"
        try:
            await self.client.room_invite(room_id, admin_user)
            logger.info(f"Invited admin to {room_id}")
        except Exception as e:
            logger.warning(f"Failed to invite admin to {room_id}: {e}")
    
    async def delete_school(self, school_name: str, room_id: str):
        """Delete an entire school hierarchy"""
        await self.send_message(room_id, f"🗑️ Searching for school: {school_name}...")
        
        # Find school in database
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT school_id, root_space_id FROM schools WHERE school_name = ?', (school_name,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            await self.send_message(room_id, f"❌ School '{school_name}' not found in database")
            return
        
        school_id, root_space_id = result
        
        # Get all spaces for this school
        cursor.execute('''
            WITH RECURSIVE school_hierarchy(space_id) AS (
                SELECT ? as space_id
                UNION
                SELECT s.space_id FROM spaces s
                JOIN school_hierarchy sh ON s.parent_space_id = sh.space_id
            )
            SELECT space_id FROM school_hierarchy
        ''', (root_space_id,))
        
        space_ids = [row[0] for row in cursor.fetchall()]
        
        # Get all rooms for these spaces
        cursor.execute('''
            SELECT room_id FROM subject_rooms 
            WHERE space_id IN ({})
        '''.format(','.join('?' * len(space_ids))), space_ids)
        
        room_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        total_entities = len(space_ids) + len(room_ids)
        await self.send_message(room_id, f"📊 Found: {len(space_ids)} spaces, {len(room_ids)} rooms")
        await self.send_message(room_id, f"🗑️ Deleting {total_entities} entities...")
        
        deleted_count = 0
        failed_count = 0
        
        # Delete all rooms first
        for room_id_to_delete in room_ids:
            try:
                # Use Synapse admin API to delete room
                url = f"{self.homeserver}/_synapse/admin/v2/rooms/{room_id_to_delete}"
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                # Admin API requires admin privileges
                # For non-admin bot, we'll just leave the room
                response = await self.client.room_leave(room_id_to_delete)
                logger.info(f"Left room: {room_id_to_delete}")
                deleted_count += 1
                await asyncio.sleep(0.2)  # Rate limit protection
            except Exception as e:
                logger.warning(f"Failed to delete room {room_id_to_delete}: {e}")
                failed_count += 1
        
        # Delete all spaces
        for space_id in reversed(space_ids):  # Delete children first
            try:
                response = await self.client.room_leave(space_id)
                logger.info(f"Left space: {space_id}")
                deleted_count += 1
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.warning(f"Failed to delete space {space_id}: {e}")
                failed_count += 1
        
        # Remove from database
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM subject_rooms WHERE space_id IN ({})'.format(','.join('?' * len(space_ids))), space_ids)
        cursor.execute('DELETE FROM spaces WHERE space_id IN ({})'.format(','.join('?' * len(space_ids))), space_ids)
        cursor.execute('DELETE FROM schools WHERE school_id = ?', (school_id,))
        
        conn.commit()
        conn.close()
        
        await self.send_message(room_id, f"✅ School deletion complete!")
        await self.send_message(room_id, f"📊 Left {deleted_count} rooms/spaces, {failed_count} failed")
        await self.send_message(room_id, f"🗄️ Removed from database")
        await self.send_message(room_id, f"\n⚠️ Note: Rooms still exist on server but bot has left them.")
    
    async def setup_primary_school(self, school_name: str, room_id: str):
        """Set up Primary Education structure (P1-P5 with 6 subjects each)"""
        await self.send_message(room_id, f"🏫 Setting up Primary School: {school_name}...")
        await self.send_message(room_id, "Creating 5 primary levels with 6 subjects each (30 rooms total)...")
        
        # Create root school space
        root_space_id = await self.create_space(
            name=school_name,
            topic=f"Primary Education - {school_name}"
        )
        
        if not root_space_id:
            await self.send_message(room_id, "❌ Failed to create root space")
            return
        
        # Invite admin to root space
        await self.invite_admin(root_space_id)
        
        self.db.add_space(root_space_id, school_name, "school")
        self.db.add_school(root_space_id, school_name, "primary", root_space_id)
        
        # Create P1-P5 levels
        for level_name, subjects in PRIMARY_SUBJECTS.items():
            level_space_id = await self.create_space(
                name=level_name,
                topic=f"Primary Level {level_name}",
                parent_space_id=root_space_id
            )
            
            if not level_space_id:
                continue
            
            # Invite admin to level space
            await self.invite_admin(level_space_id)
            
            # Store with primary_level instead of cycle/year
            self.db.add_space(level_space_id, level_name, "primary_level", root_space_id)
            
            # Create subject rooms for this level
            for subject in subjects:
                subject_room_id = await self.create_room(
                    name=f"{subject}",
                    topic=f"{subject} - {level_name}",
                    parent_space_id=level_space_id
                )
                
                if subject_room_id:
                    # Invite admin to subject room
                    await self.invite_admin(subject_room_id)
                    self.db.add_room(subject_room_id, subject, subject, level_space_id)
        
        # Create Administration space
        admin_space_id = await self.create_space(
            name="Administration",
            topic="School administration and staff",
            parent_space_id=root_space_id
        )
        
        if admin_space_id:
            await self.invite_admin(admin_space_id)
            self.db.add_space(admin_space_id, "Administration", "admin", root_space_id)
            
            # Create admin rooms
            room_id_temp = await self.create_room("Teachers' Room", "Staff communication", admin_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
            room_id_temp = await self.create_room("School Announcements", "Official announcements", admin_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
            room_id_temp = await self.create_room("Bot Management", "Bot commands", admin_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
        
        # Create Parents space
        parents_space_id = await self.create_space(
            name="Parents",
            topic="Parent communication",
            parent_space_id=root_space_id
        )
        
        if parents_space_id:
            await self.invite_admin(parents_space_id)
            self.db.add_space(parents_space_id, "Parents", "parents", root_space_id)
            
            # Create parent rooms
            room_id_temp = await self.create_room("Parent-Teacher Communication", "General communication", parents_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
            room_id_temp = await self.create_room("Events & Meetings", "School events", parents_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
        
        # Send completion message
        response = f"✅ **{school_name} Created!**\n\n"
        response += f"Root Space: {root_space_id}\n\n"
        response += "Structure:\n"
        response += "🏫 Primary School\n"
        response += "  ├── 📚 P1 (6 subjects)\n"
        response += "  ├── 📚 P2 (6 subjects)\n"
        response += "  ├── 📚 P3 (6 subjects)\n"
        response += "  ├── 📚 P4 (6 subjects)\n"
        response += "  ├── 📚 P5 (6 subjects)\n"
        response += "  ├── 👥 Administration (3 rooms)\n"
        response += "  └── 👨‍👩‍👧‍👦 Parents (2 rooms)\n\n"
        response += "**Total:** 5 levels, 30 subject rooms, 5 admin/parent rooms = 35+ rooms!\n\n"
        response += "Subjects per level: " + ", ".join(PRIMARY_SUBJECTS["P1"]) + "\n\n"
        response += "Check your Matrix client's space list to explore the hierarchy."
        
        await self.send_message(room_id, response)
    
    async def setup_fundamental_school(self, school_name: str, room_id: str):
        """Set up Fundamental Education structure (P1-P5 with subjects)"""
        await self.send_message(room_id, f"🏫 Setting up Fundamental School: {school_name}...")
        await self.send_message(room_id, "Creating 5 primary levels with subjects (30 rooms total)...")
        
        # Create root school space
        root_space_id = await self.create_space(
            name=school_name,
            topic=f"Fundamental Education - {school_name}"
        )
        
        if not root_space_id:
            await self.send_message(room_id, "❌ Failed to create root space")
            return
        
        # Invite admin to root space
        await self.invite_admin(root_space_id)
        
        self.db.add_space(root_space_id, school_name, "school")
        self.db.add_school(root_space_id, school_name, "fundamental", root_space_id)
        
        # Create P1-P5 levels with subjects
        for level_name, subjects in PRIMARY_SUBJECTS.items():
            level_space_id = await self.create_space(
                name=level_name,
                topic=f"Fundamental Level {level_name}",
                parent_space_id=root_space_id
            )
            
            if not level_space_id:
                continue
            
            # Invite admin to level space
            await self.invite_admin(level_space_id)
            
            # Store with fundamental_level instead of primary
            self.db.add_space(level_space_id, level_name, "fundamental_level", root_space_id)
            
            # Create subject rooms for this level
            for subject in subjects:
                subject_room_id = await self.create_room(
                    name=f"{subject}",
                    topic=f"{subject} - {level_name}",
                    parent_space_id=level_space_id
                )
                
                if subject_room_id:
                    # Invite admin to subject room
                    await self.invite_admin(subject_room_id)
                    self.db.add_room(subject_room_id, subject, subject, level_space_id)
        
        # Create Administration space
        admin_space_id = await self.create_space(
            name="Administration",
            topic="School administration and staff",
            parent_space_id=root_space_id
        )
        
        if admin_space_id:
            await self.invite_admin(admin_space_id)
            self.db.add_space(admin_space_id, "Administration", "admin", root_space_id)
            
            # Create admin rooms
            room_id_temp = await self.create_room("Teachers' Room", "Staff communication", admin_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
            room_id_temp = await self.create_room("School Announcements", "Official announcements", admin_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
            room_id_temp = await self.create_room("Bot Management", "Bot commands", admin_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
        
        # Create Parents space
        parents_space_id = await self.create_space(
            name="Parents",
            topic="Parent communication",
            parent_space_id=root_space_id
        )
        
        if parents_space_id:
            await self.invite_admin(parents_space_id)
            self.db.add_space(parents_space_id, "Parents", "parents", root_space_id)
            
            # Create parent rooms
            room_id_temp = await self.create_room("Parent-Teacher Communication", "General communication", parents_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
            room_id_temp = await self.create_room("Events & Meetings", "School events", parents_space_id)
            if room_id_temp:
                await self.invite_admin(room_id_temp)
        
        # Send completion message
        response = f"✅ **{school_name} Created!**\n\n"
        response += f"Root Space: {root_space_id}\n\n"
        response += "Structure:\n"
        response += "🏫 Fundamental School\n"
        response += "  ├── 📚 P1 (6 subjects)\n"
        response += "  ├── 📚 P2 (6 subjects)\n"
        response += "  ├── 📚 P3 (6 subjects)\n"
        response += "  ├── 📚 P4 (6 subjects)\n"
        response += "  ├── 📚 P5 (6 subjects)\n"
        response += "  ├── 👥 Administration (3 rooms)\n"
        response += "  └── 👨‍👩‍👧‍👦 Parents (2 rooms)\n\n"
        response += "**Total:** 5 levels, 30 subject rooms, 5 admin/parent rooms = 35+ rooms!\n\n"
        response += "Subjects per level: " + ", ".join(PRIMARY_SUBJECTS["P1"]) + "\n\n"
        response += "Check your Matrix client's space list to explore the hierarchy."
        
        await self.send_message(room_id, response)
    
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle incoming messages"""
        # Ignore own messages
        if event.sender == self.user_id:
            return
        
        # Ignore old messages
        message_time = datetime.fromtimestamp(event.server_timestamp / 1000)
        if message_time < self.start_time:
            return
        
        message = event.body.strip()
        logger.info(f"Received message in {room.display_name}: {message}")
        
        # Commands
        if message.startswith("!setup_primary_school"):
            await self.handle_setup_primary_school(room.room_id, message)
        
        elif message.startswith("!setup_fundamental_school"):
            await self.handle_setup_fundamental_school(room.room_id, message)
        
        elif message.startswith("!delete_school"):
            await self.handle_delete_school(room.room_id, message)
        
        elif message.startswith("!confirm_delete"):
            await self.handle_confirm_delete(room.room_id)
        
        elif message.startswith("!list_schools"):
            await self.handle_list_schools(room.room_id)
        
        elif message.startswith("!show_parent"):
            await self.handle_show_parent(room.room_id, message)
        
        elif message.startswith("!show_children"):
            await self.handle_show_children(room.room_id, message)
        
        elif message.startswith("!class_roster"):
            await self.handle_class_roster(room.room_id, message)
        
        elif message.startswith("!post_homework"):
            await self.handle_post_homework(room.room_id, message, event.sender)
        
        elif message.startswith("!homework_list"):
            await self.handle_homework_list(room.room_id, message)
        
        elif message.startswith("!mark_attendance"):
            await self.handle_mark_attendance(room.room_id, message, event.sender)
        
        elif message.startswith("!view_attendance"):
            await self.handle_view_attendance(room.room_id, message)
        
        elif message.startswith("!help"):
            await self.show_help(room.room_id)
    
    async def handle_setup_primary_school(self, room_id: str, message: str):
        """Handle !setup_primary_school command"""
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            await self.send_message(room_id, 'Usage: `!setup_primary_school "School Name"`')
            return
        
        # Extract school name (remove quotes if present)
        school_name = parts[1].strip().strip('"').strip("'")
        
        await self.setup_primary_school(school_name, room_id)
    
    async def handle_setup_fundamental_school(self, room_id: str, message: str):
        """Handle !setup_fundamental_school command"""
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            await self.send_message(room_id, 'Usage: `!setup_fundamental_school "School Name"`')
            return
        
        # Extract school name (remove quotes if present)
        school_name = parts[1].strip().strip('"').strip("'")
        
        await self.setup_fundamental_school(school_name, room_id)
    
    async def handle_delete_school(self, room_id: str, message: str):
        """Handle !delete_school command"""
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            await self.send_message(room_id, 'Usage: `!delete_school "School Name"`')
            return
        
        # Extract school name (remove quotes if present)
        school_name = parts[1].strip().strip('"').strip("'")
        
        # Confirm deletion
        await self.send_message(room_id, f"⚠️ Are you sure? This will remove the bot from all spaces/rooms of '{school_name}'")
        await self.send_message(room_id, "Type `!confirm_delete` within 30 seconds to proceed")
        
        # Store pending deletion
        self.pending_deletion = (school_name, room_id, datetime.now())
    
    async def handle_confirm_delete(self, room_id: str):
        """Handle !confirm_delete command"""
        if not self.pending_deletion:
            await self.send_message(room_id, "❌ No pending deletion. Use `!delete_school \"School Name\"` first")
            return
        
        school_name, pending_room_id, pending_time = self.pending_deletion
        
        # Check if confirmation is from same room
        if pending_room_id != room_id:
            await self.send_message(room_id, "❌ Please confirm in the same room where you started the deletion")
            return
        
        # Check if confirmation is within 30 seconds
        time_elapsed = (datetime.now() - pending_time).total_seconds()
        if time_elapsed > 30:
            await self.send_message(room_id, "❌ Confirmation timeout. Please start over with `!delete_school`")
            self.pending_deletion = None
            return
        
        # Proceed with deletion
        self.pending_deletion = None
        await self.delete_school(school_name, room_id)
    
    async def handle_list_schools(self, room_id: str):
        """Handle !list_schools command"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.school_name, s.school_type, s.created_at,
                   COUNT(DISTINCT sp.space_id) as space_count,
                   COUNT(DISTINCT sr.room_id) as room_count
            FROM schools s
            LEFT JOIN spaces sp ON sp.space_id = s.root_space_id 
                OR sp.parent_space_id IN (
                    SELECT space_id FROM spaces WHERE space_id = s.root_space_id 
                    OR parent_space_id = s.root_space_id
                )
            LEFT JOIN subject_rooms sr ON sr.space_id IN (
                SELECT space_id FROM spaces WHERE space_id = s.root_space_id 
                OR parent_space_id = s.root_space_id
            )
            GROUP BY s.school_id
            ORDER BY s.created_at DESC
        ''')
        
        schools = cursor.fetchall()
        conn.close()
        
        if not schools:
            await self.send_message(room_id, "📚 No schools found in database")
            return
        
        response = "📚 **Schools in Database:**\n\n"
        for school_name, school_type, created_at, space_count, room_count in schools:
            response += f"🏫 **{school_name}** ({school_type})\n"
            response += f"   Created: {created_at}\n"
            response += f"   Spaces: {space_count}, Rooms: {room_count}\n\n"
        
        await self.send_message(room_id, response)
    
    async def handle_show_parent(self, room_id: str, message: str):
        """Show parent of a student: !show_parent <student_name>"""
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            await self.send_message(room_id, 'Usage: `!show_parent student_name` or `!show_parent @student:server`')
            return
        
        query = parts[1].strip()
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Search by display name or user_id
        if query.startswith('@'):
            cursor.execute("""
                SELECT ps.parent_user_id, ps.student_user_id
                FROM parent_students ps
                WHERE ps.student_user_id = ?
            """, (query,))
        else:
            cursor.execute("""
                SELECT ps.parent_user_id, ps.student_user_id
                FROM parent_students ps
                WHERE ps.student_user_id LIKE ?
            """, (f"%{query}%",))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            await self.send_message(room_id, f"❌ No parent found for: {query}")
            return
        
        parent_id, student_id = result
        student_name = student_id.split('@')[1].split(':')[0].replace('.', ' ').title()
        parent_name = parent_id.split('@')[1].split(':')[0].replace('.', ' ').replace('parent ', '').title()
        
        response = f"👨‍👩‍👧 **Parent Information**\n\n"
        response += f"**Student:** {student_name}\n"
        response += f"**Parent:** {parent_name}\n"
        response += f"**Parent ID:** {parent_id}\n"
        
        await self.send_message(room_id, response)
    
    async def handle_show_children(self, room_id: str, message: str):
        """Show children of a parent: !show_children <parent_name>"""
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            await self.send_message(room_id, 'Usage: `!show_children parent_name` or `!show_children @parent:server`')
            return
        
        query = parts[1].strip()
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        if query.startswith('@'):
            cursor.execute("""
                SELECT student_user_id
                FROM parent_students
                WHERE parent_user_id = ?
            """, (query,))
        else:
            cursor.execute("""
                SELECT student_user_id
                FROM parent_students
                WHERE parent_user_id LIKE ?
            """, (f"%{query}%",))
        
        children = cursor.fetchall()
        conn.close()
        
        if not children:
            await self.send_message(room_id, f"❌ No children found for parent: {query}")
            return
        
        parent_name = query if not query.startswith('@') else query.split('@')[1].split(':')[0].replace('.', ' ').title()
        
        response = f"👨‍👩‍👧 **Children of {parent_name}:**\n\n"
        for i, (student_id,) in enumerate(children, 1):
            parts = student_id.split('@')[1].split(':')[0].split('.')
            student_name = ' '.join(parts[:-1]).title()
            level = parts[-1].upper()
            response += f"{i}. {student_name} ({level})\n"
            response += f"   ID: {student_id}\n"
        
        await self.send_message(room_id, response)
    
    async def handle_class_roster(self, room_id: str, message: str):
        """Show class roster with parent info: !class_roster P1"""
        parts = message.split()
        if len(parts) < 2:
            await self.send_message(room_id, 'Usage: `!class_roster P1` (or P2, P3, P4, P5)')
            return
        
        level = parts[1].upper()
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ps.student_user_id, ps.parent_user_id
            FROM parent_students ps
            WHERE ps.student_user_id LIKE ?
            ORDER BY ps.student_user_id
        """, (f"%{level}%",))
        
        roster = cursor.fetchall()
        conn.close()
        
        if not roster:
            await self.send_message(room_id, f"❌ No students found for level: {level}")
            return
        
        response = f"📚 **{level} Class Roster ({len(roster)} students)**\n\n"
        
        for i, (student_id, parent_id) in enumerate(roster, 1):
            student_parts = student_id.split('@')[1].split(':')[0].split('.')
            student_name = ' '.join(student_parts[:-1]).title()
            
            parent_parts = parent_id.split('@')[1].split(':')[0].replace('parent.', '').split('.')
            parent_name = ' '.join(parent_parts).title()
            
            response += f"**{i}. {student_name}**\n"
            response += f"   👨‍👩‍👧 Parent: {parent_name}\n"
            response += f"   📧 {parent_id}\n\n"
        
        await self.send_message(room_id, response)
    
    async def handle_post_homework(self, room_id: str, message: str, sender: str):
        """Post homework: !post_homework P1 Math "Algebra Practice" "Complete exercises 1-10" "2025-11-25" """
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            await self.send_message(room_id, 
                'Usage: `!post_homework <class> <subject> "<title>" "<description>" "<due_date>"`\n\n'
                'Example: `!post_homework P1 Math "Algebra Practice" "Complete exercises 1-10" "2025-11-25"`')
            return
        
        # Parse the command - extract quoted strings and non-quoted words
        import shlex
        try:
            args = shlex.split(parts[1])
        except ValueError as e:
            await self.send_message(room_id, f'❌ Error parsing command: {e}\n\nMake sure to use quotes around title, description, and due date.')
            return
        
        if len(args) < 5:
            await self.send_message(room_id, 
                '❌ Missing arguments.\n\n'
                'Usage: `!post_homework <class> <subject> "<title>" "<description>" "<due_date>"`')
            return
        
        class_name = args[0].upper()
        subject = args[1]
        title = args[2]
        description = args[3]
        due_date = args[4]
        assigned_by = sender
        
        # Add to database
        success = self.db.add_homework(room_id, class_name, subject, title, description, due_date, assigned_by)
        
        if success:
            # Create formatted message to post in the room
            homework_msg = f"""
📝 **New Homework Assignment**

**Class:** {class_name}
**Subject:** {subject}
**Title:** {title}

**Description:**
{description}

**📅 Due Date:** {due_date}
**👤 Assigned by:** {assigned_by}

---
_Use `!homework_list {class_name}` to see all assignments_
"""
            await self.send_message(room_id, homework_msg)
            logger.info(f"Homework posted: {class_name} - {subject} - {title}")
        else:
            await self.send_message(room_id, "❌ Failed to post homework. Check logs for details.")
    
    async def handle_homework_list(self, room_id: str, message: str):
        """List homework for a class: !homework_list P1"""
        parts = message.split()
        if len(parts) < 2:
            await self.send_message(room_id, 'Usage: `!homework_list <class>`\n\nExample: `!homework_list P1`')
            return
        
        class_name = parts[1].upper()
        homework_list = self.db.get_homework_list(class_name, limit=10)
        
        if not homework_list:
            await self.send_message(room_id, f"📚 No homework found for {class_name}")
            return
        
        response = f"📚 **Homework for {class_name}** (Last 10)\n\n"
        
        for hw_id, subject, title, description, due_date, assigned_by, created_at in homework_list:
            response += f"**{subject}: {title}**\n"
            response += f"📅 Due: {due_date}\n"
            response += f"📝 {description}\n"
            response += f"_Posted: {created_at[:10]}_\n\n"
        
        await self.send_message(room_id, response)
    
    async def handle_mark_attendance(self, room_id: str, message: str, sender: str):
        """Mark attendance: !mark_attendance P1 "John Doe" present 2025-11-18"""
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            await self.send_message(room_id,
                'Usage: `!mark_attendance <class> "<student_name>" <status> <date>`\n\n'
                'Status: present, absent, late, excused\n'
                'Example: `!mark_attendance P1 "John Doe" present 2025-11-18`')
            return
        
        import shlex
        try:
            args = shlex.split(parts[1])
        except ValueError as e:
            await self.send_message(room_id, f'❌ Error parsing command: {e}')
            return
        
        if len(args) < 4:
            await self.send_message(room_id, 
                '❌ Missing arguments.\n\n'
                'Usage: `!mark_attendance <class> "<student_name>" <status> <date>`')
            return
        
        class_name = args[0].upper()
        student_name = args[1]
        status = args[2].lower()
        date = args[3]
        marked_by = sender
        
        # Validate status
        valid_statuses = ['present', 'absent', 'late', 'excused']
        if status not in valid_statuses:
            await self.send_message(room_id, f'❌ Invalid status. Use: {", ".join(valid_statuses)}')
            return
        
        # Mark attendance
        success = self.db.mark_attendance(room_id, class_name, student_name, date, status, marked_by)
        
        if success:
            status_emoji = {
                'present': '✅',
                'absent': '❌',
                'late': '⏰',
                'excused': '📝'
            }
            
            response = f"{status_emoji.get(status, '📋')} **Attendance Marked**\n\n"
            response += f"**Student:** {student_name}\n"
            response += f"**Class:** {class_name}\n"
            response += f"**Status:** {status.title()}\n"
            response += f"**Date:** {date}\n"
            response += f"**Marked by:** {marked_by}"
            
            await self.send_message(room_id, response)
            logger.info(f"Attendance marked: {class_name} - {student_name} - {status}")
        else:
            await self.send_message(room_id, "❌ Failed to mark attendance. Check logs for details.")
    
    async def handle_view_attendance(self, room_id: str, message: str):
        """View attendance for a class: !view_attendance P1 2025-11-18"""
        parts = message.split()
        if len(parts) < 3:
            await self.send_message(room_id,
                'Usage: `!view_attendance <class> <date>`\n\n'
                'Example: `!view_attendance P1 2025-11-18`')
            return
        
        class_name = parts[1].upper()
        date = parts[2]
        
        attendance = self.db.get_attendance(class_name, date)
        
        if not attendance:
            await self.send_message(room_id, f"📋 No attendance records for {class_name} on {date}")
            return
        
        response = f"📋 **Attendance for {class_name}** - {date}\n\n"
        
        status_counts = {'present': 0, 'absent': 0, 'late': 0, 'excused': 0}
        
        for student_name, status, marked_by, created_at in attendance:
            status_emoji = {
                'present': '✅',
                'absent': '❌',
                'late': '⏰',
                'excused': '📝'
            }
            
            response += f"{status_emoji.get(status, '📋')} **{student_name}** - {status.title()}\n"
            status_counts[status] = status_counts.get(status, 0) + 1
        
        response += f"\n**Summary:**\n"
        response += f"✅ Present: {status_counts['present']} | "
        response += f"❌ Absent: {status_counts['absent']} | "
        response += f"⏰ Late: {status_counts['late']} | "
        response += f"📝 Excused: {status_counts['excused']}\n"
        response += f"**Total:** {len(attendance)} students"
        
        await self.send_message(room_id, response)
    
    async def show_help(self, room_id: str):
        """Show help message"""
        help_text = """
📚 Luxchat Spaces Manager Bot

School Setup:
• `!setup_fundamental_school "School Name"` - Create Fundamental school (P1-P5)
• `!setup_primary_school "School Name"` - Create Primary school (P1-P5)
• `!delete_school "School Name"` - Delete a school (bot leaves all spaces/rooms)
• `!list_schools` - Show all schools in database

Parent-Student Relationships:
• `!show_parent <student_name>` - Show parent of a student
• `!show_children <parent_name>` - Show all children of a parent
• `!class_roster P1` - Show class roster with parent contacts (P1-P5)

Homework Management:
• `!post_homework <class> <subject> "<title>" "<description>" "<due_date>"` - Post homework
  Example: `!post_homework P1 Math "Chapter 5" "Complete exercises 1-10" "2025-11-25"`
• `!homework_list <class>` - List recent homework for a class

Attendance Tracking:
• `!mark_attendance <class> "<student_name>" <status> <date>` - Mark attendance
  Status: present, absent, late, excused
  Example: `!mark_attendance P1 "John Doe" present 2025-11-18`
• `!view_attendance <class> <date>` - View attendance for a class

Need help? Check the README or ask in this room!
"""
        await self.send_message(room_id, help_text)
    
    async def send_message(self, room_id: str, message: str):
        """Send a message to a room"""
        try:
            await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": message
                }
            )
            logger.info(f"Sent message to {room_id}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def start(self):
        """Start the bot"""
        logger.info(f"Starting Spaces Manager Bot as {self.user_id}")
        logger.info(f"Connecting to {self.homeserver}")
        
        # Set access token
        self.client.access_token = self.access_token
        self.client.user_id = self.user_id
        
        # Join management room
        try:
            logger.info(f"Joining management room: {self.management_room}")
            await self.client.join(self.management_room)
            await self.send_message(self.management_room, "🏫 **Spaces Manager Bot Started!**\n\nType `!help` for commands.")
        except Exception as e:
            logger.error(f"Failed to join management room: {e}")
        
        # Start sync loop
        logger.info("Starting sync loop...")
        try:
            await self.client.sync_forever(timeout=30000)
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            await self.client.close()


async def main():
    """Main entry point"""
    # Load configuration
    config = configparser.ConfigParser()
    config.read('/bot/config.ini')
    
    homeserver = config.get('homeserver', 'homeserver')
    user_id = config.get('homeserver', 'bot_uid')
    access_token = config.get('homeserver', 'access_token')
    device_id = config.get('homeserver', 'device_id')
    management_room = config.get('config', 'management_room')
    
    # Create and start bot
    bot = SpacesManagerBot(homeserver, user_id, access_token, device_id, management_room)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Stopping Spaces Manager Bot...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
