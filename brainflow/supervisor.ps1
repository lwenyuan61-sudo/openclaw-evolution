param(
  [int]$IntervalSec = 30,
  [int]$PushMinIntervalSec = 120,
  [string]$Workflow = 'auto',
  [int]$RestartDelaySec = 5
)

$ErrorActionPreference = 'Stop'
$Base = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Base 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$SupervisorLog = Join-Path $LogDir 'supervisor.log'

$LockPath = Join-Path $Base '.daemon.lock'

function Log($msg){
  $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
  $line | Out-File -FilePath $SupervisorLog -Encoding utf8 -Append
}

# Single-instance lock using a named mutex (more reliable than file locks on Windows).
$mutexName = 'Local\BrainFlowSupervisor'
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$createdNew)
if (-not $createdNew) {
  Log "Another supervisor instance is running (mutex busy). Exiting."
  exit 0
}

Log "Supervisor started. interval=$IntervalSec pushMin=$PushMinIntervalSec workflow=$Workflow"

$Py = Join-Path $Base '.venv\\Scripts\\python.exe'
$Daemon = Join-Path $Base 'daemon.py'

function GetDaemons() {
  try {
    return Get-CimInstance Win32_Process | Where-Object {
      $_.CommandLine -and $_.CommandLine -like ('*' + $Base + '*daemon.py*')
    }
  } catch { return @() }
}

function KillDaemons($exceptPid = $null) {
  try {
    $procs = GetDaemons
    foreach($p in $procs){
      if($exceptPid -and ($p.ProcessId -eq $exceptPid)) { continue }
      try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; Log "Killed daemon PID=$($p.ProcessId)" } catch {}
    }
  } catch {}
}

# Clean slate on start.
KillDaemons

while ($true) {
  try {
    # Enforce single daemon before starting a new one.
    KillDaemons

    Log "Starting daemon..."
    $p = Start-Process -FilePath $Py -ArgumentList @(
      $Daemon,
      '--interval', $IntervalSec,
      '--workflow', $Workflow,
      '--push-min-interval', $PushMinIntervalSec
    ) -PassThru -WindowStyle Hidden

    # Enforce single-daemon: only kill extras if more than one daemon is present.
    Start-Sleep -Milliseconds 800
    try {
      $ds = @(GetDaemons)
      if($ds.Count -gt 1){
        foreach($d in $ds){
          if($d.ProcessId -ne $p.Id){
            try { Stop-Process -Id $d.ProcessId -Force -ErrorAction Stop; Log "Killed extra daemon PID=$($d.ProcessId) keep=$($p.Id)" } catch {}
          }
        }
      }
    } catch {}

    $p.WaitForExit()
    $code = $p.ExitCode
    Log "Daemon exited code=$code. Restart in $RestartDelaySec sec"
  } catch {
    Log "Supervisor error: $($_.Exception.Message)"
  }

  Start-Sleep -Seconds $RestartDelaySec
}
