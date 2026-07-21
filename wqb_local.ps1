param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$launcher = Join-Path $PSScriptRoot "wqb_local.py"
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -ne $python) {
    & $python.Source $launcher @Arguments
    exit $LASTEXITCODE
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $py) {
    & $py.Source "-3.14" $launcher @Arguments
    exit $LASTEXITCODE
}

throw "Python was not found. Install Python 3.14 or add it to PATH."
