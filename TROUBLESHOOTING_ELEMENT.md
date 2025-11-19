# Element Web Access Troubleshooting

## Current Status ✅

**Synapse Server:** Running & Healthy
- Container: Up and running (49+ minutes)
- Health Check: Passing
- API Endpoint: Responding correctly
- Static Page: Serving properly

## How to Access Element

### Correct URL:
```
http://localhost:8008
```

**Note:** Use `http://` NOT `https://`

### What Should Happen:

1. Browser navigates to `http://localhost:8008`
2. Redirects to `http://localhost:8008/_matrix/static/`
3. Shows Element login page

---

## Common Issues & Solutions

### Issue 1: "Internal Server Error"

**Possible Causes:**

#### A) Browser Cache
**Solution:**
1. Clear browser cache (Ctrl+Shift+Delete)
2. Or use Incognito/Private mode (Ctrl+Shift+N in Chrome)
3. Try again

#### B) Mixed Content (HTTP/HTTPS)
**Solution:**
- Ensure URL is `http://localhost:8008` (NOT https)
- Some browsers auto-upgrade to HTTPS
- Try different browser (Firefox, Chrome, Edge)

#### C) JavaScript Errors
**Solution:**
1. Press F12 to open Developer Tools
2. Go to Console tab
3. Look for red error messages
4. Share error messages for diagnosis

---

### Issue 2: "Connection Refused" or "Can't Reach"

**Check:**
```powershell
# Check if Synapse is running
docker ps | Select-String "synapse"

# Check if port is accessible
Invoke-WebRequest -Uri "http://localhost:8008/_matrix/client/versions" -UseBasicParsing
```

**Solution:**
- Restart Synapse: `docker restart synapse`
- Check Docker is running
- Check firewall settings

---

### Issue 3: Blank Page or Endless Loading

**Solution:**
1. Check browser console (F12 → Console)
2. Clear cookies for localhost
3. Try different browser
4. Check if port 8008 is being used by another service

---

## Testing Steps

### 1. Test Synapse API
```powershell
Invoke-WebRequest -Uri "http://localhost:8008/_matrix/client/versions" -UseBasicParsing
```
**Expected:** JSON response with versions

### 2. Test Static Page
```powershell
Invoke-WebRequest -Uri "http://localhost:8008/_matrix/static/" -UseBasicParsing
```
**Expected:** 200 OK status

### 3. Access in Browser
Open: `http://localhost:8008`
**Expected:** Element login page

---

## Alternative Access Methods

### Option 1: Use Public Element Web
Instead of the built-in Element, use the public hosted version:

1. Go to: https://app.element.io
2. Click "Sign In"
3. Click "Edit" next to homeserver
4. Enter: `http://localhost:8008`
5. Click "Continue"
6. Enter your credentials

**Note:** Your browser might block mixed content (HTTPS→HTTP). You may need to allow it.

### Option 2: Access via Docker
```bash
# Access from inside Docker network
docker exec -it spaces-bot curl http://synapse:8008/_matrix/static/
```

---

## Current Test Results ✅

Just tested (11/18/2025 13:51):
- ✅ Synapse container: Running
- ✅ Health check: Passed
- ✅ API versions endpoint: Responding
- ✅ Static page: Returning 200 OK
- ✅ Bots: Connected and syncing

**Conclusion:** Server is working fine. Issue is likely browser-related.

---

## What To Do Now

1. **Try Incognito Mode:**
   - Press Ctrl+Shift+N (Chrome) or Ctrl+Shift+P (Firefox)
   - Go to `http://localhost:8008`

2. **Check Browser Console:**
   - Press F12
   - Go to Console tab
   - Look for errors
   - Share screenshot if needed

3. **Try Different Browser:**
   - If using Chrome, try Firefox or Edge
   - Some browsers handle localhost differently

4. **Use Public Element:**
   - Go to https://app.element.io
   - Configure homeserver as `http://localhost:8008`
   - May require allowing mixed content

---

## Credentials Reminder

### Admin Account:
- Username: `admin`
- Password: (your admin password)
- Matrix ID: `@admin:local.synapse.server`

### Teacher Accounts:
Check: `luxchat-spaces-manager/data/bulk_created_users.csv`

### Student Accounts:
Check: `luxchat-spaces-manager/data/bulk_created_users.csv`

---

## Need More Help?

**Provide these details:**
1. Exact URL you're accessing
2. Browser name and version
3. Error message (exact text or screenshot)
4. Browser console errors (F12 → Console tab)
5. Network tab status (F12 → Network tab, look for red items)

**Check logs:**
```powershell
# Synapse logs
docker logs synapse --tail 20

# Check for errors
docker logs synapse 2>&1 | Select-String "ERROR"
```
