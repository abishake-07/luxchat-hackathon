$SYNAPSE_URL = "http://localhost:8008"
$ADMIN_TOKEN = "syt_YWRtaW4_DbZLNrxCeFIbyAXAPtln_0AuBvM"

$firstNames = @("Alice", "Bob", "Charlie", "Diana", "Emma", "Frank", "Grace", "Henry")
$lastNames = @("Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis")

function Get-RandomName { return ($firstNames | Get-Random) + " " + ($lastNames | Get-Random) }
function Get-RandomPassword { return -join ((1..12) | ForEach-Object { ([char[]](65..90 + 97..122 + 48..57) | Get-Random) }) }

Write-Host "Creating 42 users for Test School..." -ForegroundColor Cyan
$csvData = @("username,password,display_name,role,level")

# P1-P5 Students
foreach ($level in @("P1","P2","P3","P4","P5")) {
    Write-Host "`nCreating $level Students..." -ForegroundColor Yellow
    for ($i = 1; $i -le 5; $i++) {
        $name = Get-RandomName
        $username = ($name -replace ' ', '.').ToLower() + ".$($level.ToLower())"
        $password = Get-RandomPassword
        $displayname = "$name $level"
        $userId = "@$($username):local.synapse.server"
        
        $body = @{ password = $password; displayname = $displayname; admin = $false } | ConvertTo-Json
        $headers = @{ "Authorization" = "Bearer $ADMIN_TOKEN"; "Content-Type" = "application/json" }
        
        try {
            Invoke-RestMethod -Uri "$SYNAPSE_URL/_synapse/admin/v2/users/$userId" -Method Put -Headers $headers -Body $body | Out-Null
            Write-Host "  [OK] $displayname" -ForegroundColor Green
            $csvData += "$username,$password,$displayname,student,$level"
        } catch { Write-Host "  [FAIL] $username" -ForegroundColor Red }
    }
}

# Teachers
Write-Host "`nCreating Teachers..." -ForegroundColor Yellow
foreach ($subject in @("German","English","Luxembourgish","Math","Arts","PE")) {
    for ($i = 1; $i -le 2; $i++) {
        $name = Get-RandomName
        $username = "teacher." + ($name -replace ' ', '.').ToLower()
        $password = Get-RandomPassword
        $displayname = "$name - $subject Teacher"
        $userId = "@$($username):local.synapse.server"
        
        $body = @{ password = $password; displayname = $displayname; admin = $false } | ConvertTo-Json
        $headers = @{ "Authorization" = "Bearer $ADMIN_TOKEN"; "Content-Type" = "application/json" }
        
        try {
            Invoke-RestMethod -Uri "$SYNAPSE_URL/_synapse/admin/v2/users/$userId" -Method Put -Headers $headers -Body $body | Out-Null
            Write-Host "  [OK] $displayname" -ForegroundColor Green
            $csvData += "$username,$password,$displayname,teacher,$subject"
        } catch { Write-Host "  [FAIL] $username" -ForegroundColor Red }
    }
}

# Parents
Write-Host "`nCreating Parents..." -ForegroundColor Yellow
for ($i = 1; $i -le 5; $i++) {
    $name = Get-RandomName
    $username = "parent." + ($name -replace ' ', '.').ToLower()
    $password = Get-RandomPassword
    $displayname = "$name - Parent"
    $userId = "@$($username):local.synapse.server"
    
    $body = @{ password = $password; displayname = $displayname; admin = $false } | ConvertTo-Json
    $headers = @{ "Authorization" = "Bearer $ADMIN_TOKEN"; "Content-Type" = "application/json" }
    
    try {
        Invoke-RestMethod -Uri "$SYNAPSE_URL/_synapse/admin/v2/users/$userId" -Method Put -Headers $headers -Body $body | Out-Null
        Write-Host "  [OK] $displayname" -ForegroundColor Green
        $csvData += "$username,$password,$displayname,parent,"
    } catch { Write-Host "  [FAIL] $username" -ForegroundColor Red }
}

if (-not (Test-Path ".\data")) { New-Item -ItemType Directory -Path ".\data" | Out-Null }
$csvData | Out-File -FilePath ".\data\bulk_created_users.csv" -Encoding UTF8
Write-Host "`nDONE! Credentials saved to .\data\bulk_created_users.csv" -ForegroundColor Green
