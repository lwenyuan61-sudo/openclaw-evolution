Set-Location "$env:USERPROFILE\.openclaw\workspace\brainflow"

Write-Output "LATEST TRACES"
if (Test-Path runs) {
  Get-ChildItem runs -Filter 'trace-*.jsonl' | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name,LastWriteTime,Length | Format-Table -AutoSize
  $latestObj = Get-ChildItem runs -Filter 'trace-*.jsonl' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $latest = $null
  if ($latestObj) { $latest = $latestObj.FullName }
  Write-Output "TAIL"
  if ($latest) { Get-Content -LiteralPath $latest -Tail 60 }
} else {
  Write-Output "no runs dir"
}

Write-Output "KEY STATE FILES"
$paths = @(
  'state_task_queue.json',
  'state_goal_tree.json',
  'state_acc.json',
  'state_cycle.json',
  'state\\world_model.json',
  'state\\proactive_state.json',
  'memory\\procedural\\scorecard_latest.json'
)
foreach ($p in $paths) {
  $fp = Join-Path (Get-Location) $p
  if (Test-Path -LiteralPath $fp) {
    $it = Get-Item -LiteralPath $fp
    Write-Output ("$p\t$($it.LastWriteTime)\t$($it.Length)")
  } else {
    Write-Output ("$p\tMISSING")
  }
}
