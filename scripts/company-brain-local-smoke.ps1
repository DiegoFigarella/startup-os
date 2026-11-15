$ErrorActionPreference = "Stop"

Get-Content .company-brain.env | ForEach-Object {
  if ($_ -match "^([^#][^=]*)=(.*)$") {
    Set-Variable -Name $matches[1] -Value $matches[2]
  }
}

$headers = @{ "X-Company-Brain-Key" = $COMPANY_BRAIN_API_KEY }
$item = @{
  source = "discord"
  external_id = "local-smoke-001"
  occurred_at = "2026-11-14T12:00:00Z"
  author = "Maya"
  place = "#partnerships"
  text = "Acme asked for the sponsorship deck by Thursday."
  canonical_url = "https://discord.com/channels/local/partnerships/local-smoke-001"
  revision = "initial"
  scopes = @("org:utmist-startups")
} | ConvertTo-Json

$first = Invoke-RestMethod -Method Post -Uri "http://localhost:8088/v1/items" -Headers $headers -ContentType "application/json" -Body $item
$second = Invoke-RestMethod -Method Post -Uri "http://localhost:8088/v1/items" -Headers $headers -ContentType "application/json" -Body $item
$items = Invoke-RestMethod -Method Get -Uri "http://localhost:8088/v1/items?scope=org:utmist-startups" -Headers $headers

if (-not $first.created -or $second.created -or $items.Count -ne 1 -or $items[0].canonical_url -ne "https://discord.com/channels/local/partnerships/local-smoke-001") {
  throw "Local smoke test failed."
}

Write-Output "Local smoke test passed: one cited Discord item was ingested and duplicate delivery was ignored."
