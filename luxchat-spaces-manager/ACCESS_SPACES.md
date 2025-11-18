# How to Access Your Created Spaces

## Current Status

You have **2 instances** of "Lënster Lycée International School" created:
- Instance 1: `!JdWrDToGHtFHvLskin:local.synapse.server` (6 spaces, 18 rooms - incomplete)
- Instance 2: `!pcoELzPGxJmnyMkrVb:local.synapse.server` (6 spaces, 18 rooms - incomplete)

Both instances hit rate limits during creation, so they only have partial structures (Cycle 1 and part of Cycle 2).

## Method 1: Via Element Web Client

### Step 1: Open Element Web
1. Go to https://app.element.io
2. Click "Sign In"
3. Click "Edit" next to the homeserver
4. Enter: `http://localhost:8008` or `http://local.synapse.server:8008`
5. Login as `@admin:local.synapse.server`

### Step 2: Check for Pending Invites
Since the bot now auto-invites admin, you should see:
- A notification icon (if invites are pending)
- Click on "People" or notification bell
- Accept all pending room/space invites

### Step 3: View Spaces
1. Look at the **left sidebar**
2. Find the "Spaces" section (usually below "Home")
3. Click on "🏫 Lënster Lycée International School"
4. You'll see the hierarchy:
   - Cycle 1 → Cycle 1.1, Cycle 1.2 (with subject rooms)
   - Cycle 2 → Cycle 2.1 (with subject rooms)
   - Parents space

### Step 4: Navigate the Hierarchy
- Click on any space to see its child spaces/rooms
- Click on a room (e.g., "📖 Luxembourgish") to view/send messages
- Use breadcrumbs at top to navigate back up

---

## Method 2: Via API/Curl (Manual Join)

If invites didn't work, you can manually join rooms:

### Get Admin Access Token
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8008/_matrix/client/v3/login" `
    -Method Post `
    -ContentType "application/json" `
    -Body '{"type":"m.login.password","user":"admin","password":"admin"}'
$adminToken = $response.access_token
echo $adminToken
```

### Join Root Space
```powershell
Invoke-RestMethod -Uri "http://localhost:8008/_matrix/client/v3/join/!pcoELzPGxJmnyMkrVb:local.synapse.server" `
    -Method Post `
    -Headers @{"Authorization"="Bearer $adminToken"} `
    -ContentType "application/json" `
    -Body '{}'
```

### Join All Rooms in a Space
You can create a script to join all rooms. Here are some room IDs from Instance 2:

**Cycle 1.1 Rooms:**
- Luxembourgish: `!TyRFWWzuxlzAOfxIKK:local.synapse.server`
- German: `!AGtLIUxrIkeTFBFwfd:local.synapse.server`
- French: `!hLUwNFqJyXrhJEiNvE:local.synapse.server`
- Éveil aux Sciences: `!GIdlODJunuQRcSzrpk:local.synapse.server`
- Psychomotricité: `!GByXlVhaBTCweoErxP:local.synapse.server`
- Arts: `!KOHIOTnyHPkiEYIRLP:local.synapse.server`

**Example Join Command:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8008/_matrix/client/v3/join/!TyRFWWzuxlzAOfxIKK:local.synapse.server" `
    -Method Post `
    -Headers @{"Authorization"="Bearer $adminToken"} `
    -ContentType "application/json" `
    -Body '{}'
```

---

## Method 3: Create a Fresh Complete School

Since the previous runs hit rate limits, create a new complete school:

### Step 1: Send Command to Bot
In your management room (`!NZvjpkpcInIitdDHUB:local.synapse.server`):
```
!setup_fundamental_school "École Fondamentale Belair"
```

### Step 2: Wait for Completion
- The bot will create ~170 spaces and rooms
- This takes 5-10 minutes due to rate limiting
- Monitor logs: `docker logs -f spaces-bot`

### Step 3: Accept Invites
- The bot will automatically invite @admin to all spaces/rooms
- Check your Matrix client for ~170 pending invites
- Accept them to gain access

---

## Verifying Admin Access

### Check if Admin is in a Room
```powershell
# Get your access token first (from Method 2)
$roomId = "!TyRFWWzuxlzAOfxIKK:local.synapse.server"  # Example room

Invoke-RestMethod -Uri "http://localhost:8008/_matrix/client/v3/rooms/$roomId/joined_members" `
    -Method Get `
    -Headers @{"Authorization"="Bearer $adminToken"}
```

You should see `@admin:local.synapse.server` in the members list.

---

## Troubleshooting

### Issue: Can't See Spaces in Element
**Solution:** 
- Refresh the page
- Try logging out and back in
- Check if invites are pending (notification icon)

### Issue: M_FORBIDDEN Errors
**Solution:**
- The bot should have invited you automatically
- If not, run a new school creation (the code now includes auto-invites)
- Or manually join using Method 2 above

### Issue: Incomplete School Structure
**Solution:**
- The previous runs hit rate limits
- Create a new school with a different name
- Let it complete (monitor logs for "✅ School Created!")

### Issue: Too Many Test Spaces
**Solution:**
To clean up, you can delete spaces via API or just create new ones with clear names like:
- "Demo School for Testing"
- "Production School 2025"

---

## Next Steps

1. **Test the auto-invite feature**: Create a new school and verify admin receives invites
2. **Complete structure**: Wait for full school creation (all 4 cycles, 9 years, ~170 rooms)
3. **Integrate attendance**: Link attendance bot to subject rooms
4. **Demo preparation**: Use one clean school for your hackathon demo

## Database Query Commands

View school hierarchy anytime:
```powershell
docker exec -it spaces-bot python3 /bot/view_school_hierarchy.py
```

Count created entities:
```powershell
docker exec -it spaces-bot python3 -c "import sqlite3; conn = sqlite3.connect('/bot/data/spaces.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM spaces'); print(f'Spaces: {cursor.fetchone()[0]}'); cursor.execute('SELECT COUNT(*) FROM subject_rooms'); print(f'Rooms: {cursor.fetchone()[0]}'); conn.close()"
```
