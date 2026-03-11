$ErrorActionPreference = 'Stop'

$base = 'C:\Users\15305\.openclaw\workspace\brainflow'
$outbox = Join-Path $base 'outbox'
$candPath = Join-Path $outbox 'candidates.jsonl'
$idxPath  = Join-Path $outbox 'dedup_index.json'
$stateCtrl= Join-Path $base 'state_control.json'
$learnQ   = Join-Path $base 'learning_queue'

function AssertOrReport($p){
  [pscustomobject]@{ Path=$p; Exists=(Test-Path $p) }
}

# 0decc...1: key paths
$paths = @(
  $outbox,
  $candPath,
  $idxPath,
  $learnQ,
  $stateCtrl,
  (Join-Path $base 'memory'),
  (Join-Path $base 'memory\semantic'),
  (Join-Path $base 'memory\episodic')
)
$pathStatus = $paths | ForEach-Object { AssertOrReport $_ }

# Stats + plan on tail N
$n = 200
if (!(Test-Path $candPath)) {
  $res = [pscustomobject]@{ ok=$false; error='missing candidates.jsonl'; pathStatus=$pathStatus }
  $res | ConvertTo-Json -Depth 6
  exit 2
}

$allLines = Get-Content -LiteralPath $candPath -ErrorAction SilentlyContinue
$totalAll = $allLines.Count
$tailStart = [Math]::Max(0, $totalAll - $n)
$tailLines = @()
if ($totalAll -gt 0) { $tailLines = $allLines[$tailStart..($totalAll-1)] }

$nonEmpty = ($tailLines | Where-Object { $_ -and $_.Trim().Length -gt 0 }).Count
$parsed = 0
$hashes = @()
foreach($l in $tailLines){
  try {
    $o = $l | ConvertFrom-Json -ErrorAction Stop
    $parsed++
    if ($o.dedup_hash) { $hashes += [string]$o.dedup_hash }
    else { $hashes += $l }
  } catch {
    $hashes += $l
  }
}
$uniq = ($hashes | Select-Object -Unique).Count
$dup = $hashes.Count - $uniq

# Build archive plan: mark empty/json_parse_fail/duplicate_in_tail/no_sources
$seen = @{}
$plan = @()
$tagCounts = @{}
for($i=0; $i -lt $tailLines.Count; $i++){
  $l = $tailLines[$i]
  $reasonTags = @()
  $trim = ($l|Out-String).Trim()
  if(!$trim){ $reasonTags += 'empty' }
  $o = $null
  try { $o = $trim | ConvertFrom-Json -ErrorAction Stop } catch { $reasonTags += 'json_parse_fail' }

  $h = $null
  if($o -and $o.dedup_hash){ $h = [string]$o.dedup_hash } else { $h = $trim }
  if($seen.ContainsKey($h)){ $reasonTags += 'duplicate_in_tail' } else { $seen[$h] = $true }

  if($o){
    if(-not $o.sources -and -not $o.source){ $reasonTags += 'no_sources' }
  }

  if($reasonTags.Count -gt 0){
    foreach($t in $reasonTags){ if(-not $tagCounts.ContainsKey($t)){$tagCounts[$t]=0}; $tagCounts[$t]++ }
    $plan += [pscustomobject]@{ TailIndex=($i+1); GlobalLineIndex=($tailStart + $i); DedupKey=$h; Tags=($reasonTags -join ',') }
  }
}

# Ensure archive dir + choose unique file
$archDir = Join-Path $outbox 'archive'
if(!(Test-Path $archDir)){ New-Item -ItemType Directory -Path $archDir | Out-Null }
$date = Get-Date -Format 'yyyy-MM-dd'
$archBase = Join-Path $archDir ("$date.jsonl")
$archPath = $archBase
$k = 1
while(Test-Path $archPath){
  $archPath = Join-Path $archDir ("$date-$k.jsonl")
  $k++
}

# Backup original before any rewrite
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$bakPath = Join-Path $archDir ("candidates.bak-$ts.jsonl")
Copy-Item -LiteralPath $candPath -Destination $bakPath -Force

# Apply non-destructive clean: remove only tail lines that are empty/json_parse_fail/duplicate_in_tail
$removeSet = @{}
foreach($p in $plan){
  $tags = [string]$p.Tags
  if($tags -match 'empty' -or $tags -match 'json_parse_fail' -or $tags -match 'duplicate_in_tail'){
    $removeSet[[int]$p.GlobalLineIndex] = $true
  }
}

$archived = @()
$kept = @()
for($gi=0; $gi -lt $allLines.Count; $gi++){
  if($removeSet.ContainsKey($gi)){
    $archived += $allLines[$gi]
  } else {
    $kept += $allLines[$gi]
  }
}

# Write archive (append archived lines with metadata header as comments)
"# archived_from=$candPath" | Out-File -LiteralPath $archPath -Encoding utf8
"# backup=$bakPath" | Out-File -LiteralPath $archPath -Encoding utf8 -Append
"# removed_count=$($archived.Count) total_before=$($allLines.Count) total_after=$($kept.Count)" | Out-File -LiteralPath $archPath -Encoding utf8 -Append
$archived | Out-File -LiteralPath $archPath -Encoding utf8 -Append

# Rewrite candidates.jsonl with kept lines
$kept | Out-File -LiteralPath $candPath -Encoding utf8

# Update intent in state_control.json (minimal patch + backup)
$intentPatch = $null
$stateBak = $null
try {
  if(Test-Path $stateCtrl){
    $raw = Get-Content -LiteralPath $stateCtrl -Raw
    $obj = $raw | ConvertFrom-Json
    $stateBak = "$stateCtrl.bak-$ts"
    Copy-Item -LiteralPath $stateCtrl -Destination $stateBak -Force
    if(-not ($obj.PSObject.Properties.Name -contains 'intent')){
      $obj | Add-Member -NotePropertyName intent -NotePropertyValue (@{})
    }
    $obj.intent.topic = 'anti-aging_evidence_triage'
    $obj.intent.reason = 'reflect: reduce duplicate/parse-failed candidates; keep conversation-aligned breakthroughs + stability alerts + decision requests'
    $obj.intent.updated_at = (Get-Date).ToString('o')
    ($obj | ConvertTo-Json -Depth 12) | Out-File -LiteralPath $stateCtrl -Encoding utf8
    $intentPatch = $obj.intent
  }
} catch {
  $intentPatch = @{ error = $_.Exception.Message }
}

# Write last_processed pointer
$lp = Join-Path $outbox 'last_processed.txt'
@(
  "last_processed_at=$((Get-Date).ToString('o'))",
  "note=reflect cleanup applied; archived duplicates/parse-fails from tail $n; archive_file=$archPath"
) | Out-File -LiteralPath $lp -Encoding utf8

# Output summary JSON
$tagSummary = ($tagCounts.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join '; '
[pscustomobject]@{
  ok = $true
  total_before = $allLines.Count
  total_after = $kept.Count
  removed = $archived.Count
  backup_candidates = $bakPath
  archive_written = $archPath
  plan_count = $plan.Count
  tail_stats = @{ tailN=$n; tailLines=$tailLines.Count; nonEmpty=$nonEmpty; parsedJson=$parsed; duplicateHash=$dup }
  tag_summary = $tagSummary
  state_control_backup = $stateBak
  intent = $intentPatch
  last_processed = $lp
  pathStatus = $pathStatus
} | ConvertTo-Json -Depth 8
