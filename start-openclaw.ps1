param(
  [int]$Port = 3000,
  [string]$OwnerId = ""
)

$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot
$env:PORT = [string]$Port

if ($OwnerId.Trim()) {
  $env:OPENCLAW_OWNER_ID = $OwnerId.Trim()
}

node server/index.js
