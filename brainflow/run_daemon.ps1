param(
  [int]$IntervalSec = 30,
  [int]$PushMinIntervalSec = 120,
  [string]$Workflow = 'auto'
)

$ErrorActionPreference = 'Stop'
$Base = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Base '.venv\Scripts\python.exe'
$Daemon = Join-Path $Base 'daemon.py'
$LogDir = Join-Path $Base 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $LogDir ("daemon-$ts.log")

# Run daemon, redirect all output to log
& $Py $Daemon --interval $IntervalSec --workflow $Workflow --push-min-interval $PushMinIntervalSec *>> $log
exit $LASTEXITCODE
