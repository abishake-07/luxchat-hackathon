# Homework & Attendance Features

## 📝 Homework Management

### Post Homework Assignment

Post a new homework assignment for a class:

```
!post_homework <class> <subject> "<title>" "<description>" "<due_date>"
```

**Example:**
```
!post_homework P1 Math "Algebra Practice" "Complete exercises 1-10 from page 42" "2025-11-25"
```

**Parameters:**
- `<class>`: Class name (P1, P2, P3, P4, P5, etc.)
- `<subject>`: Subject name (Math, English, German, etc.)
- `"<title>"`: Homework title (use quotes)
- `"<description>"`: Detailed description (use quotes)
- `"<due_date>"`: Due date in YYYY-MM-DD format (use quotes)

**Output:**
The bot will post a formatted homework announcement in the room with:
- Class and subject
- Title and description
- Due date
- Who assigned it

### List Homework

View the last 10 homework assignments for a class:

```
!homework_list <class>
```

**Example:**
```
!homework_list P1
```

**Output:**
- List of recent homework with titles, due dates, and descriptions
- Sorted by most recent first

---

## ✅ Attendance Tracking

### Mark Attendance

Mark a student's attendance for a specific date:

```
!mark_attendance <class> "<student_name>" <status> <date>
```

**Status Options:**
- `present` - Student is present ✅
- `absent` - Student is absent ❌
- `late` - Student arrived late ⏰
- `excused` - Student has excused absence 📝

**Example:**
```
!mark_attendance P1 "John Doe" present 2025-11-18
!mark_attendance P2 "Jane Smith" late 2025-11-18
!mark_attendance P3 "Bob Johnson" excused 2025-11-18
```

**Parameters:**
- `<class>`: Class name (P1-P5)
- `"<student_name>"`: Full student name (use quotes if name has spaces)
- `<status>`: One of: present, absent, late, excused
- `<date>`: Date in YYYY-MM-DD format

**Output:**
- Confirmation with emoji indicator
- Student name, class, status, and date
- Who marked the attendance

### View Attendance

View attendance records for a class on a specific date:

```
!view_attendance <class> <date>
```

**Example:**
```
!view_attendance P1 2025-11-18
```

**Output:**
- List of all students with their attendance status
- Visual emoji indicators (✅❌⏰📝)
- Summary statistics (counts by status)
- Total number of students

---

## 💡 Usage Tips

### Homework Tips:
1. **Use descriptive titles** - Makes it easier to identify assignments
2. **Include page numbers** - Add specific references in the description
3. **Set realistic due dates** - Allow sufficient time for completion
4. **Check homework list regularly** - Use `!homework_list` to avoid duplicates

### Attendance Tips:
1. **Mark attendance daily** - Keep records up to date
2. **Use correct status** - Distinguish between absent and excused
3. **Mark late arrivals** - Use "late" status for tardiness tracking
4. **Review attendance** - Use `!view_attendance` to check daily records
5. **Consistent date format** - Always use YYYY-MM-DD format

### Best Practices:
- **Post homework in subject rooms** - Keep assignments organized by subject
- **Mark attendance at start of day** - Establish a routine
- **Use quotes for multi-word entries** - Student names, titles, descriptions
- **Document excused absences** - Use "excused" status with notes

---

## 📊 Database Storage

All homework and attendance data is stored in the SQLite database at:
```
/bot/data/spaces.db
```

### Tables:
- **homework**: homework_id, room_id, class_name, subject, title, description, due_date, assigned_by, created_at
- **attendance**: attendance_id, room_id, class_name, student_name, date, status, marked_by, created_at

### Features:
- **Persistent storage** - Data survives bot restarts
- **Duplicate prevention** - Attendance uses UNIQUE constraint on (class, student, date)
- **Audit trail** - Tracks who assigned homework and marked attendance
- **Timestamps** - Automatic creation timestamps

---

## 🔧 Troubleshooting

### Command Not Working?

1. **Check quotes** - Use quotes around multi-word strings
2. **Check date format** - Must be YYYY-MM-DD
3. **Check status spelling** - Must be: present, absent, late, or excused
4. **Check class name** - Must match existing class (P1-P5)

### Common Errors:

**"Error parsing command"**
- Missing quotes around title, description, or student name
- Solution: Add quotes around any parameter with spaces

**"Missing arguments"**
- Not all required parameters provided
- Solution: Check command syntax with `!help`

**"Invalid status"**
- Wrong attendance status used
- Solution: Use only: present, absent, late, excused

---

## 🎓 Example Workflow

### Morning Routine:
```
# 1. Mark attendance for your class
!mark_attendance P1 "Alice Brown" present 2025-11-18
!mark_attendance P1 "Bob Wilson" present 2025-11-18
!mark_attendance P1 "Charlie Davis" late 2025-11-18
!mark_attendance P1 "Diana Evans" absent 2025-11-18

# 2. Review attendance
!view_attendance P1 2025-11-18
```

### Posting Homework:
```
# After lesson, post homework
!post_homework P1 Math "Multiplication Practice" "Complete worksheet on multiplication tables 6-9. Show your work." "2025-11-20"

# Post for another subject
!post_homework P1 English "Reading Assignment" "Read Chapter 3 of 'The Adventures' and answer questions 1-5." "2025-11-22"

# Check what homework is assigned
!homework_list P1
```

---

## 🚀 Future Enhancements

Potential additions to these features:
- Homework submission tracking
- Attendance statistics and reports
- Late homework tracking
- Automated parent notifications
- Bulk attendance marking
- Attendance trends analysis
- Homework completion rates
- Export to CSV for reporting

---

For more commands, type `!help` in the bot management room.
