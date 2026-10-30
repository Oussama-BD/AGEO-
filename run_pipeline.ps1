param([switch]$SkipCollect)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Run-Docker {
    param([string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw ('Commande Docker en echec : ' + ($Arguments -join ' ')) }
}
if (-not $SkipCollect) { Run-Docker -Arguments @('compose','exec','-T','api','python','collect_sources.py') }
$files = Get-ChildItem -LiteralPath data/raw -Filter '*.pdf'
foreach ($file in $files) {
    Run-Docker -Arguments @('compose','exec','-T','api','python','cli.py','ingest',('data/raw/' + $file.Name),'--defer-neo4j')
}
Run-Docker -Arguments @('compose','--profile','batch','run','--rm','spark')
Run-Docker -Arguments @('compose','exec','-T','api','python','cli.py','import-spark')
Write-Host 'Pipeline termine. Consulter le graphe dans http://localhost:8000'
