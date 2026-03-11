param(
  [int]$IntervalSec = 30,
  [int]$PushMinIntervalSec = 120,
  [string]$Workflow = 'auto',
  [int]$OutboxRecentMinutes = 20,
  [int]$StaleMinutes = 60
)

$ErrorActionPreference = 'Stop'
$Base = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Base 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$WatchdogLog = Join-Path $LogDir 'watchdog.log'
$StateDir = Join-Path $Base 'state'
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
$StatePath = Join-Path $StateDir 'watchdog_state.json'

function Log($msg){
  $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
  $line | Out-File -FilePath $WatchdogLog -Encoding utf8 -Append
}

function Get-ProcByCmdLike($pattern){
  try {
    return Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -like $pattern) }
  } catch { return @() }
}

# --- Detect processes ---
# Match by absolute base path to avoid false negatives/positives.
$daemonProcs = @(Get-ProcByCmdLike ("*" + $Base + "*daemon.py*"))
$supervisorProcs = @(Get-ProcByCmdLike ("*" + $Base + "*supervisor.ps1*"))

$daemonCount = $daemonProcs.Count
$supervisorCount = $supervisorProcs.Count

# --- Outbox freshness ---
$outbox = Join-Path $Base 'outbox\candidates.jsonl'
$outboxMTimeUtc = $null
$outboxBytes = $null
$outboxAgeMin = $null
if (Test-Path $outbox) {
  $fi = Get-Item $outbox
  $outboxMTimeUtc = $fi.LastWriteTimeUtc
  $outboxBytes = $fi.Length
  $outboxAgeMin = [math]::Round((((Get-Date).ToUniversalTime() - $outboxMTimeUtc).TotalMinutes), 2)
}

$outboxIsRecent = $false
if ($outboxAgeMin -ne $null) { $outboxIsRecent = ($outboxAgeMin -le $OutboxRecentMinutes) }
$outboxIsStale = $false
if ($outboxAgeMin -ne $null) { $outboxIsStale = ($outboxAgeMin -ge $StaleMinutes) }

# --- Load state (dedup) ---
$state = @{}
if (Test-Path $StatePath) {
  try { $state = (Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json) } catch { $state = @{} }
}
if (-not $state) { $state = @{} }
if (-not ($state.PSObject.Properties.Name -contains 'lastMilestoneSentUtc')) {
  $state | Add-Member -NotePropertyName lastMilestoneSentUtc -NotePropertyValue $null
}
if (-not ($state.PSObject.Properties.Name -contains 'lastRepairUtc')) {
  $state | Add-Member -NotePropertyName lastRepairUtc -NotePropertyValue $null
}

$actions = @()

# --- Self-repair policy (Level-3) ---
# Prefer running supervisor; let supervisor manage daemon single-instance.
$shouldStartSupervisor = ($supervisorCount -eq 0)

if ($shouldStartSupervisor) {
  try {
    $sup = Join-Path $Base 'supervisor.ps1'
    $args = @(
      '-NoProfile','-ExecutionPolicy','Bypass',
      '-File', $sup,
      '-IntervalSec', $IntervalSec,
      '-PushMinIntervalSec', $PushMinIntervalSec,
      '-Workflow', $Workflow
    )
    Start-Process -FilePath 'powershell' -ArgumentList $args -WindowStyle Hidden | Out-Null
    $actions += 'start_supervisor'
    $state.lastRepairUtc = (Get-Date).ToUniversalTime().ToString('o')
    Log "Repair: started supervisor (IntervalSec=$IntervalSec PushMin=$PushMinIntervalSec Workflow=$Workflow)"
  } catch {
    $actions += 'start_supervisor_failed'
    Log "Repair failed: start supervisor: $($_.Exception.Message)"
  }
}

# If multiple daemons exist, enforce single-instance (keep the newest PID).
if ($daemonCount -gt 1) {
  try {
    $keep = ($daemonProcs | Sort-Object ProcessId -Descending | Select-Object -First 1)
    foreach($p in $daemonProcs){
      if($p.ProcessId -eq $keep.ProcessId) { continue }
      try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; Log "Repair: killed extra daemon PID=$($p.ProcessId) keep=$($keep.ProcessId)" } catch {}
    }
    $actions += 'kill_extra_daemons'
    $state.lastRepairUtc = (Get-Date).ToUniversalTime().ToString('o')
  } catch {
    $actions += 'kill_extra_daemons_failed'
    Log "Repair failed: kill extras: $($_.Exception.Message)"
  }
}

# If outbox is very stale but supervisor exists, restart supervisor as a coarse recovery.
if (($supervisorCount -gt 0) -and $outboxIsStale) {
  try {
    foreach($p in $supervisorProcs){
      try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; Log "Repair: killed stale supervisor PID=$($p.ProcessId)" } catch {}
    }
    $actions += 'restart_supervisor_due_to_stale_outbox'
    $state.lastRepairUtc = (Get-Date).ToUniversalTime().ToString('o')
  } catch {
    $actions += 'restart_supervisor_failed'
    Log "Repair failed: restart supervisor: $($_.Exception.Message)"
  }
}

# --- Milestone condition (for your old watcher) ---
# Condition requested: DaemonCount==1 and outbox updating recently.
$milestone = (($daemonCount -eq 1) -and $outboxIsRecent)

# Dedup milestone notifications (send at most once per 6h unless state cleared)
$sendMilestone = $false
if ($milestone) {
  $nowUtc = (Get-Date).ToUniversalTime()
  $last = $null
  if ($state.lastMilestoneSentUtc) {
    try { $last = [datetime]::Parse($state.lastMilestoneSentUtc).ToUniversalTime() } catch { $last = $null }
  }
  if (-not $last -or (($nowUtc - $last).TotalHours -ge 6)) {
    $sendMilestone = $true
    $state.lastMilestoneSentUtc = $nowUtc.ToString('o')
  }
}

# Save state
try { ($state | ConvertTo-Json -Depth 6) | Out-File -FilePath $StatePath -Encoding utf8 } catch {}

# Output JSON summary for the caller (OpenClaw)
[pscustomobject]@{
  ok = $true
  base = $Base
  daemonCount = $daemonCount
  supervisorCount = $supervisorCount
  outboxPath = $outbox
  outboxMTimeUtc = $outboxMTimeUtc
  outboxAgeMinutes = $outboxAgeMin
  outboxBytes = $outboxBytes
  outboxIsRecent = $outboxIsRecent
  outboxIsStale = $outboxIsStale
  milestone = $milestone
  sendMilestone = $sendMilestone
  actions = $actions
} | ConvertTo-Json -Depth 6
