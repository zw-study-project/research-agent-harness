param(
    [string]$PythonCommand = "python"
)

$validator = Join-Path $PSScriptRoot "validate-state.py"
if (-not (Test-Path -LiteralPath $validator -PathType Leaf)) {
    Write-Error "Missing project-local research validator: $validator"
    exit 2
}

& $PythonCommand $validator
exit $LASTEXITCODE
