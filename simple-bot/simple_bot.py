#!/usr/bin/env python3
"""
Attendance Bot for Matrix
Tracks student attendance with database persistence and automatic presence-based marking
Includes user management and bulk CSV import
"""
import asyncio
import logging
import sys
import sqlite3
import re
import csv
import io
import secrets
import string
import requests
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Tuple
from nio import AsyncClient, MatrixRoom, RoomMessageText, RoomMemberEvent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AttendanceDatabase:
    """Manages SQLite database for attendance tracking"""
    
    def __init__(self, db_path: str = "/bot/data/attendance.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                class_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Classes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                class_name TEXT PRIMARY KEY,
                room_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Attendance records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                date DATE,
                status TEXT,
                marked_by TEXT,
                room_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES students(user_id)
            )
        ''')
        
        # Class sessions (for tracking class periods)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS class_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_minutes INTEGER,
                started_by TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Presence tracking (who was in room during class)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS presence_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                user_id TEXT,
                join_time TIMESTAMP,
                leave_time TIMESTAMP,
                duration_seconds INTEGER,
                FOREIGN KEY (session_id) REFERENCES class_sessions(id)
            )
        ''')
        
        # User credentials (for auto-created users)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                user_id TEXT PRIMARY KEY,
                password TEXT,
                auto_generated BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES students(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def add_student(self, user_id: str, display_name: str, class_name: str = "default"):
        """Add a new student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO students (user_id, display_name, class_name) VALUES (?, ?, ?)",
                (user_id, display_name, class_name)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding student: {e}")
            return False
        finally:
            conn.close()
    
    def mark_attendance(self, user_id: str, status: str, marked_by: str, room_id: str, date_str: Optional[str] = None):
        """Mark attendance for a student"""
        attendance_date = date_str if date_str else date.today().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # Check if already marked today
            cursor.execute(
                "SELECT id FROM attendance WHERE user_id = ? AND date = ?",
                (user_id, attendance_date)
            )
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute(
                    "UPDATE attendance SET status = ?, marked_by = ?, timestamp = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, marked_by, existing[0])
                )
            else:
                cursor.execute(
                    "INSERT INTO attendance (user_id, date, status, marked_by, room_id) VALUES (?, ?, ?, ?, ?)",
                    (user_id, attendance_date, status, marked_by, room_id)
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking attendance: {e}")
            return False
        finally:
            conn.close()
    
    def get_daily_summary(self, date_str: Optional[str] = None) -> dict:
        """Get attendance summary for a date"""
        attendance_date = date_str if date_str else date.today().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                s.user_id, s.display_name, a.status, a.timestamp
            FROM students s
            LEFT JOIN attendance a ON s.user_id = a.user_id AND a.date = ?
            ORDER BY s.display_name
        ''', (attendance_date,))
        
        results = cursor.fetchall()
        conn.close()
        
        summary = {
            'present': [],
            'absent': [],
            'unmarked': []
        }
        
        for user_id, display_name, status, timestamp in results:
            if status == 'present':
                summary['present'].append((user_id, display_name))
            elif status == 'absent':
                summary['absent'].append((user_id, display_name))
            else:
                summary['unmarked'].append((user_id, display_name))
        
        return summary
    
    def get_student_history(self, user_id: str, days: int = 7) -> List[tuple]:
        """Get attendance history for a student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date, status, timestamp
            FROM attendance
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (user_id, days))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def start_class_session(self, room_id: str, started_by: str, duration_minutes: int = 60) -> int:
        """Start a new class session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO class_sessions (room_id, start_time, duration_minutes, started_by) VALUES (?, datetime('now'), ?, ?)",
                (room_id, duration_minutes, started_by)
            )
            session_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Started class session {session_id} in room {room_id} for {duration_minutes} minutes")
            return session_id
        except Exception as e:
            logger.error(f"Error starting class session: {e}")
            return 0
        finally:
            conn.close()
    
    def end_class_session(self, session_id: int) -> bool:
        """End a class session and calculate attendance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # Update session end time
            cursor.execute(
                "UPDATE class_sessions SET end_time = datetime('now'), status = 'completed' WHERE id = ?",
                (session_id,)
            )
            
            # Get session info
            cursor.execute(
                "SELECT room_id, start_time, end_time, duration_minutes FROM class_sessions WHERE id = ?",
                (session_id,)
            )
            session = cursor.fetchone()
            if not session:
                return False
            
            room_id, start_time, end_time, duration_minutes = session
            conn.commit()
            logger.info(f"Ended class session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error ending class session: {e}")
            return False
        finally:
            conn.close()
    
    def get_active_session(self, room_id: str) -> Optional[int]:
        """Get active session ID for a room"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM class_sessions WHERE room_id = ? AND status = 'active' ORDER BY start_time DESC LIMIT 1",
            (room_id,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def log_presence(self, session_id: int, user_id: str, join_time: datetime, leave_time: Optional[datetime] = None):
        """Log user presence in a class session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            if leave_time:
                duration = int((leave_time - join_time).total_seconds())
                cursor.execute(
                    "INSERT INTO presence_log (session_id, user_id, join_time, leave_time, duration_seconds) VALUES (?, ?, ?, ?, ?)",
                    (session_id, user_id, join_time.isoformat(), leave_time.isoformat(), duration)
                )
            else:
                cursor.execute(
                    "INSERT INTO presence_log (session_id, user_id, join_time) VALUES (?, ?, ?)",
                    (session_id, user_id, join_time.isoformat())
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging presence: {e}")
            return False
        finally:
            conn.close()
    
    def calculate_session_attendance(self, session_id: int, threshold_percent: float = 0.5) -> Dict[str, List[str]]:
        """Calculate attendance based on presence during session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get session duration
        cursor.execute(
            "SELECT duration_minutes, room_id FROM class_sessions WHERE id = ?",
            (session_id,)
        )
        session_info = cursor.fetchone()
        if not session_info:
            return {'present': [], 'absent': []}
        
        duration_minutes, room_id = session_info
        required_seconds = duration_minutes * 60 * threshold_percent
        
        # Get all students' presence time
        cursor.execute('''
            SELECT s.user_id, s.display_name, COALESCE(SUM(p.duration_seconds), 0) as total_seconds
            FROM students s
            LEFT JOIN presence_log p ON s.user_id = p.user_id AND p.session_id = ?
            GROUP BY s.user_id, s.display_name
        ''', (session_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        present = []
        absent = []
        
        for user_id, display_name, total_seconds in results:
            if user_id and total_seconds >= required_seconds:
                present.append((user_id, display_name, total_seconds))
            else:
                absent.append((user_id, display_name, total_seconds))
        
        return {'present': present, 'absent': absent}
    
    def store_credentials(self, user_id: str, password: str) -> bool:
        """Store user credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO credentials (user_id, password) VALUES (?, ?)",
                (user_id, password)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error storing credentials: {e}")
            return False
        finally:
            conn.close()
    
    def get_credentials(self, user_id: str) -> Optional[Tuple[str, str]]:
        """Get user credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password, created_at FROM credentials WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        return result if result else None
    
    def list_all_students(self) -> List[Tuple[str, str, str]]:
        """Get all registered students grouped by class"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, display_name, class_name 
            FROM students 
            ORDER BY class_name, display_name
        ''')
        results = cursor.fetchall()
        conn.close()
        return results
    
    def add_class(self, class_name: str, room_id: str) -> bool:
        """Add or update a class with its room ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO classes (class_name, room_id) VALUES (?, ?)",
                (class_name, room_id)
            )
            conn.commit()
            logger.info(f"Added class {class_name} -> {room_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding class: {e}")
            return False
        finally:
            conn.close()
    
    def get_class_room(self, class_name: str) -> Optional[str]:
        """Get room ID for a class"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT room_id FROM classes WHERE class_name = ?", (class_name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def get_all_classes(self) -> List[Tuple[str, str]]:
        """Get all classes with their room IDs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT class_name, room_id FROM classes ORDER BY class_name")
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_students_in_class(self, class_name: str) -> List[Tuple[str, str]]:
        """Get all students enrolled in a specific class"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, display_name FROM students WHERE class_name = ? ORDER BY display_name",
            (class_name,)
        )
        results = cursor.fetchall()
        conn.close()
        return results

class UserManager:
    """Manages user creation via Synapse Admin API"""
    
    def __init__(self, homeserver: str, admin_token: str):
        self.homeserver = homeserver
        self.admin_token = admin_token
        self.headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def generate_password(self, length: int = 12) -> str:
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def create_user(self, username: str, display_name: str, password: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Create a user on Synapse server
        Returns: (success, user_id, password)
        """
        logger.info(f"UserManager.create_user called: username={username}, display_name={display_name}")
        
        if not password:
            password = self.generate_password()
            logger.info("Generated random password")
        
        # Extract server name from homeserver URL
        server_name = self.homeserver.replace('http://', '').replace('https://', '').split(':')[0]
        user_id = f"@{username}:{server_name}"
        logger.info(f"Constructed user_id: {user_id}")
        
        # Synapse Admin API endpoint
        url = f"{self.homeserver}/_synapse/admin/v2/users/{user_id}"
        logger.info(f"API URL: {url}")
        
        payload = {
            "password": password,
            "displayname": display_name,
            "threepids": [],
            "admin": False,
            "deactivated": False
        }
        logger.info(f"Payload: {payload}")
        
        try:
            logger.info("Making PUT request to Synapse admin API...")
            response = requests.put(url, json=payload, headers=self.headers, timeout=10)
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text}")
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Created user: {user_id}")
                return True, user_id, password
            else:
                logger.error(f"❌ Failed to create user {username}: {response.status_code} - {response.text}")
                return False, user_id, password
        except Exception as e:
            logger.error(f"❌ Exception creating user {username}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, user_id, password
    
    def parse_csv(self, csv_content: str) -> List[Dict[str, str]]:
        """
        Parse CSV content
        Expected format: username,display_name,class,role
        """
        users = []
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        for row in reader:
            # Support flexible column names
            username = row.get('username') or row.get('Username') or row.get('user')
            display_name = row.get('display_name') or row.get('Display Name') or row.get('name') or row.get('Name')
            class_name = row.get('class') or row.get('Class') or 'default'
            role = row.get('role') or row.get('Role') or 'student'
            
            if username and display_name:
                users.append({
                    'username': username.strip(),
                    'display_name': display_name.strip(),
                    'class': class_name.strip(),
                    'role': role.strip()
                })
        
        return users

class AttendanceBot:
    def __init__(self, homeserver: str, user_id: str, access_token: str, device_id: str, management_room: str, admin_token: Optional[str] = None):
        self.homeserver = homeserver
        self.user_id = user_id
        self.access_token = access_token
        self.device_id = device_id
        self.management_room = management_room
        self.client = AsyncClient(homeserver, user_id, device_id=device_id)
        self.db = AttendanceDatabase()
        
        # User management (if admin token provided)
        self.admin_token = admin_token
        if admin_token:
            self.user_manager = UserManager(homeserver, admin_token)
        else:
            self.user_manager = None
        
        # Track current presence (user_id -> join_time)
        self.current_presence: Dict[str, Dict[str, datetime]] = {}  # room_id -> {user_id: join_time}
        
        # Track bot start time to ignore old messages
        self.start_time = datetime.now()
        
        # Add callbacks
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        self.client.add_event_callback(self.member_callback, RoomMemberEvent)
        
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle incoming messages"""
        # Ignore our own messages
        if event.sender == self.user_id:
            return
        
        # Ignore messages from before bot started (old messages in sync)
        message_time = datetime.fromtimestamp(event.server_timestamp / 1000)
        logger.info(f"Message time: {message_time}, Bot start time: {self.start_time}")
        if message_time < self.start_time:
            logger.info("Ignoring old message")
            return
            
        message = event.body.strip()
        logger.info(f"Received message in {room.display_name}: {message}")
        logger.info(f"Checking command routing...") 
        
        # Handle commands
        if message.startswith("!hello"):
            await self.send_message(room.room_id, "👋 Hello! I'm the Attendance Bot!")
            
        elif message.startswith("!ping"):
            await self.send_message(room.room_id, "🏓 Pong!")
        
        elif message.startswith("!register"):
            await self.handle_register(room.room_id, event.sender, message)
        
        elif message.startswith("!mark_present") or message.startswith("!present"):
            await self.handle_mark_present(room.room_id, event.sender, message)
        
        elif message.startswith("!mark_absent") or message.startswith("!absent"):
            await self.handle_mark_absent(room.room_id, event.sender, message)
        
        elif message.startswith("!attendance"):
            await self.handle_attendance_summary(room.room_id, message)
        
        elif message.startswith("!history"):
            await self.handle_history(room.room_id, event.sender, message)
        
        elif message.startswith("!start_class"):
            logger.info("!start_class command detected, calling handler")
            await self.handle_start_class(room.room_id, event.sender, message)
        
        elif message.startswith("!end_class"):
            logger.info("!end_class command detected, calling handler")
            await self.handle_end_class(room.room_id, event.sender)
        
        elif message.startswith("!class_status"):
            await self.handle_class_status(room.room_id)
        
        elif message.startswith("!import_csv"):
            await self.handle_import_csv(room.room_id, event.sender, message)
        
        elif message.startswith("!list_users"):
            await self.handle_list_users(room.room_id)
        
        elif message.startswith("!get_credentials"):
            await self.handle_get_credentials(room.room_id, message)
        
        elif message.startswith("!create_user"):
            logger.info("!create_user command detected, calling handler")
            await self.handle_create_single_user(room.room_id, event.sender, message)
        
        elif message.startswith("!create_class"):
            await self.handle_create_class(room.room_id, message)
        
        elif message.startswith("!enroll"):
            await self.handle_enroll(room.room_id, message)
        
        elif message.startswith("!list_classes"):
            await self.handle_list_classes(room.room_id)
        
        elif message.startswith("!invite"):
            await self.handle_invite(room.room_id, message)
            
        elif message.startswith("!help"):
            await self.show_help(room.room_id)
    
    async def member_callback(self, room: MatrixRoom, event: RoomMemberEvent):
        """Handle room member join/leave events for presence tracking"""
        # Ignore bot's own events
        if event.state_key == self.user_id:
            return
        
        room_id = room.room_id
        user_id = event.state_key
        
        # Check if there's an active class session
        session_id = self.db.get_active_session(room_id)
        if not session_id:
            return  # No active class, don't track
        
        # Initialize room tracking if needed
        if room_id not in self.current_presence:
            self.current_presence[room_id] = {}
        
        # Handle join
        if event.membership == "join" and user_id not in self.current_presence[room_id]:
            join_time = datetime.now()
            self.current_presence[room_id][user_id] = join_time
            logger.info(f"User {user_id} joined room {room_id} during class session {session_id}")
        
        # Handle leave
        elif event.membership in ["leave", "ban"] and user_id in self.current_presence[room_id]:
            join_time = self.current_presence[room_id][user_id]
            leave_time = datetime.now()
            self.db.log_presence(session_id, user_id, join_time, leave_time)
            del self.current_presence[room_id][user_id]
            duration = (leave_time - join_time).total_seconds()
            logger.info(f"User {user_id} left room {room_id}, was present for {duration:.0f} seconds")
    
    async def handle_register(self, room_id: str, sender: str, message: str):
        """Register a student: !register @user:server Name or !register Name (for self)"""
        parts = message.split(maxsplit=2)
        
        if len(parts) == 2:
            # Register self
            user_id = sender
            display_name = parts[1]
        elif len(parts) >= 3:
            # Register another user
            user_id = parts[1]
            display_name = parts[2]
        else:
            await self.send_message(room_id, "Usage: !register <name> or !register @user:server <name>")
            return
        
        if self.db.add_student(user_id, display_name):
            await self.send_message(room_id, f"✅ Registered: {display_name} ({user_id})")
        else:
            await self.send_message(room_id, "❌ Failed to register student")
    
    async def handle_mark_present(self, room_id: str, sender: str, message: str):
        """Mark students as present: !present @user1 @user2..."""
        # Extract mentioned users
        user_ids = re.findall(r'@[\w\-\.]+:[\w\-\.]+', message)
        
        if not user_ids:
            # Mark sender as present
            user_ids = [sender]
        
        marked = []
        for user_id in user_ids:
            if self.db.mark_attendance(user_id, "present", sender, room_id):
                marked.append(user_id)
        
        if marked:
            users_str = ", ".join(marked)
            await self.send_message(room_id, f"✅ Marked PRESENT: {users_str}")
        else:
            await self.send_message(room_id, "❌ Failed to mark attendance")
    
    async def handle_mark_absent(self, room_id: str, sender: str, message: str):
        """Mark students as absent: !absent @user1 @user2..."""
        user_ids = re.findall(r'@[\w\-\.]+:[\w\-\.]+', message)
        
        if not user_ids:
            await self.send_message(room_id, "Usage: !absent @user1 @user2...")
            return
        
        marked = []
        for user_id in user_ids:
            if self.db.mark_attendance(user_id, "absent", sender, room_id):
                marked.append(user_id)
        
        if marked:
            users_str = ", ".join(marked)
            await self.send_message(room_id, f"❌ Marked ABSENT: {users_str}")
        else:
            await self.send_message(room_id, "❌ Failed to mark attendance")
    
    async def handle_attendance_summary(self, room_id: str, message: str):
        """Show attendance summary: !attendance [date]"""
        parts = message.split()
        date_str = parts[1] if len(parts) > 1 else None
        
        summary = self.db.get_daily_summary(date_str)
        display_date = date_str if date_str else date.today().isoformat()
        
        response = f"📊 **Attendance Summary for {display_date}**\n\n"
        
        if summary['present']:
            response += f"✅ **Present ({len(summary['present'])}):**\n"
            for user_id, name in summary['present']:
                response += f"  • {name}\n"
            response += "\n"
        
        if summary['absent']:
            response += f"❌ **Absent ({len(summary['absent'])}):**\n"
            for user_id, name in summary['absent']:
                response += f"  • {name}\n"
            response += "\n"
        
        if summary['unmarked']:
            response += f"⚠️ **Not Marked ({len(summary['unmarked'])}):**\n"
            for user_id, name in summary['unmarked']:
                response += f"  • {name}\n"
        
        await self.send_message(room_id, response)
    
    async def handle_history(self, room_id: str, sender: str, message: str):
        """Show attendance history: !history [@user] [days]"""
        parts = message.split()
        
        # Determine user
        user_match = re.search(r'@[\w\-\.]+:[\w\-\.]+', message)
        user_id = user_match.group(0) if user_match else sender
        
        # Determine days
        days = 7
        for part in parts[1:]:
            if part.isdigit():
                days = int(part)
                break
        
        history = self.db.get_student_history(user_id, days)
        
        response = f"📜 **Attendance History for {user_id}** (Last {days} days)\n\n"
        
        if history:
            for date_val, status, timestamp in history:
                emoji = "✅" if status == "present" else "❌"
                response += f"{emoji} {date_val} - {status}\n"
        else:
            response += "No attendance records found.\n"
        
        await self.send_message(room_id, response)
    
    async def handle_start_class(self, room_id: str, sender: str, message: str):
        """Start a class session: !start_class [duration_minutes]"""
        try:
            logger.info("handle_start_class called")
            # Check if there's already an active session
            active_session = self.db.get_active_session(room_id)
            logger.info(f"Active session check: {active_session}")
            if active_session:
                await self.send_message(room_id, "⚠️ A class is already in progress! Use !end_class to finish it first.")
                return
            
            # Parse duration (default 60 minutes)
            parts = message.split()
            duration = 60
            if len(parts) > 1 and parts[1].isdigit():
                duration = int(parts[1])
            
            logger.info(f"Starting session with duration {duration}")
            # Start session
            session_id = self.db.start_class_session(room_id, sender, duration)
            logger.info(f"Started session {session_id}")
            
            if session_id:
                # Get current room members and track them
                try:
                    members_response = await self.client.joined_members(room_id)
                    if hasattr(members_response, 'members'):
                        if room_id not in self.current_presence:
                            self.current_presence[room_id] = {}
                        
                        now = datetime.now()
                        for member in members_response.members:
                            if member.user_id != self.user_id:  # Don't track the bot
                                self.current_presence[room_id][member.user_id] = now
                                logger.info(f"Tracking {member.user_id} from class start")
                except Exception as e:
                    logger.error(f"Error getting room members: {e}")
                
                await self.send_message(
                    room_id, 
                    f"🎓 **Class Started!**\n\nDuration: {duration} minutes\nSession ID: {session_id}\n\n"
                    f"Students present in the room will be tracked automatically.\n"
                    f"Use `!end_class` to finish and calculate attendance."
                )
            else:
                await self.send_message(room_id, "❌ Failed to start class session")
        except Exception as e:
            logger.error(f"Error in handle_start_class: {e}", exc_info=True)
            await self.send_message(room_id, f"❌ Error starting class: {str(e)}")
    
    async def handle_end_class(self, room_id: str, sender: str):
        """End the active class session and calculate attendance"""
        session_id = self.db.get_active_session(room_id)
        if not session_id:
            await self.send_message(room_id, "⚠️ No active class session in this room.")
            return
        
        # Log final presence for users still in room
        if room_id in self.current_presence:
            now = datetime.now()
            for user_id, join_time in self.current_presence[room_id].items():
                self.db.log_presence(session_id, user_id, join_time, now)
            self.current_presence[room_id].clear()
        
        # End the session
        if self.db.end_class_session(session_id):
            # Calculate attendance (50% threshold)
            attendance = self.db.calculate_session_attendance(session_id, threshold_percent=0.5)
            
            # Auto-mark attendance
            for user_id, display_name, duration in attendance['present']:
                minutes = int(duration / 60)
                self.db.mark_attendance(user_id, "present", "system_auto", room_id)
                logger.info(f"Auto-marked {user_id} as present ({minutes} minutes)")
            
            for user_id, display_name, duration in attendance['absent']:
                minutes = int(duration / 60)
                self.db.mark_attendance(user_id, "absent", "system_auto", room_id)
                logger.info(f"Auto-marked {user_id} as absent ({minutes} minutes)")
            
            # Send summary
            response = f"🎓 **Class Ended - Attendance Summary**\n\n"
            
            if attendance['present']:
                response += f"✅ **Present ({len(attendance['present'])}):**\n"
                for user_id, display_name, duration in attendance['present']:
                    minutes = int(duration / 60)
                    response += f"  • {display_name or user_id} ({minutes} min)\n"
                response += "\n"
            
            if attendance['absent']:
                response += f"❌ **Absent ({len(attendance['absent'])}):**\n"
                for user_id, display_name, duration in attendance['absent']:
                    minutes = int(duration / 60)
                    response += f"  • {display_name or user_id} ({minutes} min)\n"
            
            await self.send_message(room_id, response)
        else:
            await self.send_message(room_id, "❌ Failed to end class session")
    
    async def handle_class_status(self, room_id: str):
        """Show status of active class session"""
        session_id = self.db.get_active_session(room_id)
        if not session_id:
            await self.send_message(room_id, "ℹ️ No active class session in this room.")
            return
        
        # Count current attendees
        attendees = []
        if room_id in self.current_presence:
            for user_id in self.current_presence[room_id].keys():
                attendees.append(user_id)
        
        response = f"📊 **Active Class Session**\n\nSession ID: {session_id}\n"
        response += f"Currently tracking: {len(attendees)} student(s)\n\n"
        
        if attendees:
            response += "Present in room:\n"
            for user_id in attendees:
                response += f"  • {user_id}\n"
        
        await self.send_message(room_id, response)
    
    async def handle_import_csv(self, room_id: str, sender: str, message: str):
        """Import users from CSV data"""
        if not self.user_manager:
            await self.send_message(room_id, "❌ User management not enabled (admin token required)")
            return
        
        # Extract CSV data (everything after the command)
        parts = message.split('\n', 1)
        if len(parts) < 2:
            help_text = """
**CSV Import Format:**
```
!import_csv
username,display_name,class,role
john.doe,John Doe,Math-101,student
jane.smith,Jane Smith,Math-101,student
teacher1,Mr. Teacher,Math-101,teacher
```
"""
            await self.send_message(room_id, help_text)
            return
        
        csv_data = parts[1].strip()
        
        try:
            users = self.user_manager.parse_csv(csv_data)
            if not users:
                await self.send_message(room_id, "❌ No valid users found in CSV")
                return
            
            await self.send_message(room_id, f"📥 Processing {len(users)} users...")
            
            # Collect unique class names
            class_names = set(user_data['class'] for user_data in users)
            
            # Create class rooms if they don't exist
            for class_name in class_names:
                existing_room = self.db.get_class_room(class_name)
                if not existing_room:
                    await self.send_message(room_id, f"Creating room for {class_name}...")
                    await self.create_class_room(class_name)
            
            created = []
            failed = []
            
            for user_data in users:
                username = user_data['username']
                display_name = user_data['display_name']
                class_name = user_data['class']
                
                # Create user on Synapse
                success, user_id, password = self.user_manager.create_user(username, display_name)
                
                if success:
                    # Register in database
                    self.db.add_student(user_id, display_name, class_name)
                    self.db.store_credentials(user_id, password)
                    
                    # Auto-invite to management room
                    try:
                        await self.client.room_invite(room_id, user_id)
                    except:
                        pass  # Ignore invite errors
                    
                    # Auto-enroll in class room
                    await self.enroll_student(user_id, class_name)
                    
                    created.append((username, password))
                else:
                    failed.append(username)
            
            # Send summary
            response = f"✅ **Import Complete**\n\n"
            response += f"Created: {len(created)} users\n"
            if failed:
                response += f"Failed: {len(failed)} users\n\n"
            
            if created:
                response += "**Credentials:**\n```\n"
                for username, password in created[:10]:  # Limit to first 10
                    response += f"{username}: {password}\n"
                if len(created) > 10:
                    response += f"... and {len(created) - 10} more\n"
                response += "```\n"
                response += "\n⚠️ Save these credentials! Use `!get_credentials @user` to retrieve later."
            
            await self.send_message(room_id, response)
            
        except Exception as e:
            logger.error(f"CSV import error: {e}", exc_info=True)
            await self.send_message(room_id, f"❌ Import failed: {str(e)}")
    
    async def handle_create_single_user(self, room_id: str, sender: str, message: str):
        """Create a single user: !create_user username Display Name"""
        logger.info(f"handle_create_single_user called with message: {message}")
        
        if not self.user_manager:
            logger.error("User manager not initialized")
            await self.send_message(room_id, "❌ User management not enabled")
            return
        
        parts = message.split(maxsplit=2)
        logger.info(f"Parsed parts: {parts}")
        if len(parts) < 3:
            await self.send_message(room_id, "Usage: `!create_user username Display Name`")
            return
        
        username = parts[1]
        display_name = parts[2]
        logger.info(f"Creating user: {username} with display name: {display_name}")
        
        success, user_id, password = self.user_manager.create_user(username, display_name)
        logger.info(f"User creation result: success={success}, user_id={user_id}")
        
        if success:
            self.db.add_student(user_id, display_name)
            self.db.store_credentials(user_id, password)
            
            # Try to invite
            try:
                await self.client.room_invite(room_id, user_id)
            except:
                pass
            
            response = f"✅ **User Created**\n\n"
            response += f"User ID: {user_id}\n"
            response += f"Password: `{password}`\n\n"
            response += "⚠️ Save this password!"
            await self.send_message(room_id, response)
        else:
            await self.send_message(room_id, f"❌ Failed to create user {username}")
    
    async def handle_list_users(self, room_id: str):
        """List all registered students"""
        students = self.db.list_all_students()
        
        if not students:
            await self.send_message(room_id, "No registered students found.")
            return
        
        # Group by class
        by_class = {}
        for user_id, display_name, class_name in students:
            if class_name not in by_class:
                by_class[class_name] = []
            by_class[class_name].append((user_id, display_name))
        
        response = f"👥 **Registered Students ({len(students)} total)**\n\n"
        
        for class_name in sorted(by_class.keys()):
            response += f"**{class_name}:** ({len(by_class[class_name])})\n"
            for user_id, display_name in by_class[class_name][:15]:  # Limit per class
                response += f"  • {display_name} ({user_id})\n"
            if len(by_class[class_name]) > 15:
                response += f"  ... and {len(by_class[class_name]) - 15} more\n"
            response += "\n"
        
        await self.send_message(room_id, response)
    
    async def handle_invite(self, room_id: str, message: str):
        """Invite user(s) to the current room: !invite @user1 @user2..."""
        # Extract all user IDs from message
        user_ids = re.findall(r'@[\w\-\.]+:[\w\-\.]+', message)
        
        if not user_ids:
            await self.send_message(room_id, "Usage: `!invite @user:server [@user2:server ...]`")
            return
        
        invited = []
        failed = []
        
        for user_id in user_ids:
            try:
                await self.client.room_invite(room_id, user_id)
                invited.append(user_id)
                logger.info(f"Invited {user_id} to {room_id}")
            except Exception as e:
                failed.append(user_id)
                logger.error(f"Failed to invite {user_id}: {e}")
        
        response = ""
        if invited:
            response += f"✅ Invited {len(invited)} user(s):\n"
            for user_id in invited:
                response += f"  • {user_id}\n"
        
        if failed:
            response += f"\n❌ Failed to invite {len(failed)} user(s):\n"
            for user_id in failed:
                response += f"  • {user_id}\n"
        
        await self.send_message(room_id, response)
    
    async def handle_get_credentials(self, room_id: str, message: str):
        """Get credentials for a user: !get_credentials @user"""
        user_match = re.search(r'@[\w\-\.]+:[\w\-\.]+', message)
        if not user_match:
            await self.send_message(room_id, "Usage: `!get_credentials @user:server`")
            return
        
        user_id = user_match.group(0)
        creds = self.db.get_credentials(user_id)
        
        if creds:
            password, created_at = creds
            response = f"🔑 **Credentials for {user_id}**\n\n"
            response += f"Password: `{password}`\n"
            response += f"Created: {created_at}\n"
            await self.send_message(room_id, response)
        else:
            await self.send_message(room_id, f"❌ No credentials found for {user_id}")
    
    async def handle_create_class(self, room_id: str, message: str):
        """Create a new class room: !create_class Math-101"""
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            await self.send_message(room_id, "Usage: `!create_class ClassName`")
            return
        
        class_name = parts[1].strip()
        
        # Check if class already exists
        existing_room = self.db.get_class_room(class_name)
        if existing_room:
            await self.send_message(room_id, f"⚠️ Class {class_name} already exists (Room: {existing_room})")
            return
        
        # Create the room
        class_room_id = await self.create_class_room(class_name)
        
        if class_room_id:
            response = f"✅ **Class Created**\n\n"
            response += f"Class: {class_name}\n"
            response += f"Room ID: {class_room_id}\n\n"
            response += f"Use `!enroll @user {class_name}` to add students to this class."
            await self.send_message(room_id, response)
        else:
            await self.send_message(room_id, f"❌ Failed to create class {class_name}")
    
    async def handle_enroll(self, room_id: str, message: str):
        """Enroll a student in a class: !enroll @user:server ClassName"""
        parts = message.split()
        if len(parts) < 3:
            await self.send_message(room_id, "Usage: `!enroll @user:server ClassName`")
            return
        
        user_id = parts[1]
        class_name = parts[2]
        
        # Verify user exists
        # Update student's class in database
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE students SET class_name = ? WHERE user_id = ?",
            (class_name, user_id)
        )
        conn.commit()
        conn.close()
        
        # Enroll in class room
        success = await self.enroll_student(user_id, class_name)
        
        if success:
            await self.send_message(room_id, f"✅ Enrolled {user_id} in {class_name}")
        else:
            await self.send_message(room_id, f"❌ Failed to enroll {user_id} in {class_name}. Make sure the class exists.")
    
    async def handle_list_classes(self, room_id: str):
        """List all classes with enrollment counts"""
        classes = self.db.get_all_classes()
        
        if not classes:
            await self.send_message(room_id, "No classes created yet. Use `!create_class ClassName` to create one.")
            return
        
        response = f"🏫 **Available Classes ({len(classes)})**\n\n"
        
        for class_name, class_room_id in classes:
            students = self.db.get_students_in_class(class_name)
            response += f"**{class_name}**\n"
            response += f"  Room: {class_room_id}\n"
            response += f"  Enrolled: {len(students)} student(s)\n\n"
        
        await self.send_message(room_id, response)
    
    async def show_help(self, room_id: str):
        """Show help message"""
        help_text = """
📚 **Attendance Bot Commands**

**User Management:**
• `!import_csv` - Bulk import users from CSV
• `!create_user username Name` - Create single user
• `!list_users` - Show all registered students
• `!get_credentials @user` - Retrieve user password

**Class Management:**
• `!create_class ClassName` - Create a new class room
• `!enroll @user ClassName` - Enroll student in class
• `!list_classes` - Show all classes with enrollment

**Registration:**
• `!register <name>` - Register yourself
• `!register @user:server <name>` - Register another user

**Automatic Attendance (Presence-Based):**
• `!start_class [minutes]` - Start class (default 60 min)
• `!end_class` - End class & auto-mark attendance
• `!class_status` - Check active class session
  
  *Students present for >50% of class time are marked present automatically*

**Manual Attendance:**
• `!present` or `!mark_present` - Mark yourself present
• `!present @user1 @user2...` - Mark others present
• `!absent @user1 @user2...` - Mark users absent

**Reports:**
• `!attendance` - Today's attendance summary
• `!attendance 2025-11-15` - Summary for specific date
• `!history` - Your attendance history (7 days)
• `!history @user` - Another user's history
• `!history 30` - History for 30 days

**Other:**
• `!hello` - Greeting
• `!ping` - Test bot responsiveness
• `!help` - Show this help
        """
        await self.send_message(room_id, help_text)
    
    async def create_class_room(self, class_name: str) -> Optional[str]:
        """Create a Matrix room for a class"""
        try:
            response = await self.client.room_create(
                name=class_name,
                topic=f"Class room for {class_name}",
                is_public=False,
                preset="private_chat",
                invite=[],  # We'll invite students separately
                initial_state=[]
            )
            
            if hasattr(response, 'room_id'):
                room_id = response.room_id
                logger.info(f"Created room {room_id} for class {class_name}")
                
                # Store in database
                self.db.add_class(class_name, room_id)
                
                # Join the room as bot
                await self.client.join(room_id)
                
                return room_id
            else:
                logger.error(f"Failed to create room for {class_name}: {response}")
                return None
        except Exception as e:
            logger.error(f"Exception creating room for {class_name}: {e}")
            return None
    
    async def enroll_student(self, user_id: str, class_name: str) -> bool:
        """Enroll a student in a class (invite to class room)"""
        room_id = self.db.get_class_room(class_name)
        
        if not room_id:
            logger.error(f"No room found for class {class_name}")
            return False
        
        try:
            await self.client.room_invite(room_id, user_id)
            logger.info(f"Invited {user_id} to {class_name} ({room_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to invite {user_id} to {class_name}: {e}")
            return False
    
    async def send_message(self, room_id: str, message: str):
        """Send a text message to a room"""
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
        logger.info(f"Starting Attendance Bot as {self.user_id}")
        logger.info(f"Connecting to {self.homeserver}")
        
        # Set access token
        self.client.access_token = self.access_token
        self.client.user_id = self.user_id
        
        # Try to join management room
        try:
            logger.info(f"Joining management room: {self.management_room}")
            await self.client.join(self.management_room)
        except Exception as e:
            logger.warning(f"Could not join management room: {e}")
        
        # Send startup message
        startup_msg = "✅ **Attendance Bot Started!**\n\nType `!help` for commands."
        await self.send_message(self.management_room, startup_msg)
        
        # Start syncing
        logger.info("Starting sync loop...")
        await self.client.sync_forever(timeout=30000)
    
    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping Attendance Bot...")
        await self.send_message(self.management_room, "👋 Attendance Bot stopping...")
        await self.client.close()

async def main():
    """Main entry point"""
    # Configuration from environment variables or config file
    import os
    import configparser
    
    # Try to load from config file
    config_file = os.environ.get('CONFIG_FILE', '/bot/config.ini')
    
    if os.path.exists(config_file):
        logger.info(f"Loading config from {config_file}")
        config = configparser.ConfigParser()
        config.read(config_file)
        
        homeserver = config.get('homeserver', 'homeserver')
        user_id = config.get('homeserver', 'bot_uid')
        access_token = config.get('homeserver', 'access_token')
        device_id = config.get('homeserver', 'device_id')
        management_room = config.get('config', 'management_room')
        
        # Optional admin token for user management
        admin_token = config.get('homeserver', 'admin_token', fallback=None)
        
        # Add http:// if not present
        if not homeserver.startswith('http://') and not homeserver.startswith('https://'):
            homeserver = f"http://{homeserver}:8008"
    else:
        logger.error(f"Config file not found: {config_file}")
        sys.exit(1)
    
    # Create data directory if it doesn't exist
    os.makedirs('/bot/data', exist_ok=True)
    
    # Create and start bot
    bot = AttendanceBot(homeserver, user_id, access_token, device_id, management_room, admin_token)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        await bot.stop()
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        await bot.stop()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
