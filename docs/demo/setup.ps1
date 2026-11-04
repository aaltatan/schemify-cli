# Hidden setup for the tapes: run schemify from this checkout in a scratch folder.
$env:PYTHONIOENCODING = "utf-8"
$global:repo = (Resolve-Path "$PSScriptRoot/../..").Path
Set-Location (New-Item -ItemType Directory -Force "$env:TEMP/schemify-demo")
function global:schemify { uv run -q --project $repo schemify @args }
function global:prompt { "> " }
