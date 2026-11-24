$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repoRoot

try {
    docker compose up -d --wait db
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not start the PostgreSQL service. Check Docker Desktop and .env.'
    }

    $paperCount = docker compose exec -T db psql -U rc_admin -d research_commons -tAc 'SELECT count(*) FROM papers;'
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not query the papers table. Ensure the database schema has been initialized.'
    }

    if ([int]$paperCount.Trim() -gt 0) {
        Write-Host "The paper catalog already has $($paperCount.Trim()) rows; no import was needed."
        return
    }

    docker compose cp db/papers_data.sql db:/tmp/papers_data.sql
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not copy db/papers_data.sql into the database container.'
    }

    docker compose exec -T db psql -v ON_ERROR_STOP=1 -U rc_admin -d research_commons -f /tmp/papers_data.sql
    if ($LASTEXITCODE -ne 0) {
        throw 'Paper import failed. See the psql error above.'
    }

    Write-Host 'Paper catalog import completed.'
}
finally {
    Pop-Location
}
