param([int]$Enrollments = 5000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectName = 'learning-dw-smoke-' + (Get-Date -Format 'yyyyMMddHHmmss')
$composeFile = Join-Path $projectRoot 'docker-compose.yml'
$env:PG_PORT = '15432'
$env:CH_PORT = '18123'
$env:DASHBOARD_PORT = '18501'
$env:DW_MIN_SOURCE_ROWS = '0'
$env:DW_ARTIFACTS_DIR = '/app/artifacts/verification/' + $projectName
function Invoke-Compose {
    & docker compose -f $composeFile -p $projectName @args
    if ($LASTEXITCODE -ne 0) { throw 'Verification command failed. Inspect the Docker output above.' }
}
try {
    Invoke-Compose build runner dashboard
    Invoke-Compose up -d --wait postgres clickhouse
    Invoke-Compose run --rm --no-deps runner python cli.py all --enrollments $Enrollments --runs 3
    Invoke-Compose run --rm --no-deps runner python -m unittest discover -s tests -v
    Invoke-Compose run --rm --no-deps -e DW_ALLOW_SCENARIOS=1 runner python -m tests.scenarios
    Invoke-Compose run --rm --no-deps dashboard python -m tests.dashboard_check
    Write-Host ('Verification passed. Evidence in artifacts/verification/' + $projectName)
}
finally {
    # Keep volumes for inspection. No -v and no deletion of project files.
    & docker compose -f $composeFile -p $projectName stop
}
