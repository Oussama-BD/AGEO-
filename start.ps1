$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host 'Fichier .env cree. Configurez les mots de passe et la cle Gemini avant le lancement.'
    exit 1
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop inaccessible. Verifiez le moteur Linux et les droits du terminal.' }
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw 'Echec de lancement Docker. Consultez docker compose logs.' }
Write-Host 'Interface : http://localhost:8000'
Write-Host 'Neo4j : http://localhost:7474'
Write-Host 'HDFS : http://localhost:9870'
