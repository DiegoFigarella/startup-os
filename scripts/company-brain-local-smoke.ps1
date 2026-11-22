$ErrorActionPreference = "Stop"

Get-Content .company-brain.env | ForEach-Object {
  if ($_ -match "^([^#][^=]*)=(.*)$") {
    Set-Variable -Name $matches[1] -Value $matches[2]
  }
}

$headers = @{ "X-Company-Brain-Key" = $COMPANY_BRAIN_API_KEY }
for ($attempt = 1; $attempt -le 20; $attempt++) {
  try {
    if ((Invoke-RestMethod -Uri "http://localhost:8088/health").status -eq "ok") { break }
  } catch {
    if ($attempt -eq 20) { throw }
    Start-Sleep -Seconds 1
  }
}
$itemId = "local-smoke-" + [guid]::NewGuid().ToString("N")
$item = @{
  source = "discord"
  external_id = $itemId
  occurred_at = "2026-11-14T12:00:00Z"
  author = "Maya"
  place = "#partnerships"
  text = "Acme asked for the sponsorship deck by Thursday."
  canonical_url = "https://discord.com/channels/local/partnerships/$itemId"
  revision = "initial"
  scopes = @("org:utmist-startups")
} | ConvertTo-Json

$first = Invoke-RestMethod -Method Post -Uri "http://localhost:8088/v1/items" -Headers $headers -ContentType "application/json" -Body $item
$second = Invoke-RestMethod -Method Post -Uri "http://localhost:8088/v1/items" -Headers $headers -ContentType "application/json" -Body $item
$items = Invoke-RestMethod -Method Get -Uri "http://localhost:8088/v1/items?scope=org:utmist-startups" -Headers $headers

if (-not $first.created -or $second.created -or $items.canonical_url -notcontains "https://discord.com/channels/local/partnerships/$itemId") {
  throw "Local smoke test failed."
}

Write-Output "Local smoke test passed: one cited Discord item was ingested and duplicate delivery was ignored."
