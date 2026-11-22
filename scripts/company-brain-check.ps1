param([switch]$Start)

$ErrorActionPreference = "Stop"

if (-not (Test-Path .company-brain.env)) {
  throw "Missing .company-brain.env. Copy .company-brain.env.example and replace both placeholder values."
}

Get-Content .company-brain.env | ForEach-Object {
  if ($_ -match "^([^#][^=]*)=(.*)$") { Set-Variable -Name $matches[1] -Value $matches[2] }
}
if ($POSTGRES_PASSWORD -like "replace-this-*" -or $COMPANY_BRAIN_API_KEY -like "replace-this-*") {
  throw "Replace the placeholder values in .company-brain.env before running the stack."
}

docker info | Out-Null
docker compose --env-file .company-brain.env -f compose.company-brain.yaml config --quiet
if ($Start) {
  docker compose --env-file .company-brain.env -f compose.company-brain.yaml up --build --detach
  .\scripts\company-brain-local-smoke.ps1
}

Write-Output "Company Brain configuration is ready."
