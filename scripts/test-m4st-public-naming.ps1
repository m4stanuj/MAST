param(
    [string]$Root = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

$rootPath = Resolve-Path -LiteralPath $Root
$Root = $rootPath.Path

$publicDocs = @(
    "README.md",
    "README_PUBLIC_CLEAN.md",
    "ECOSYSTEM.md",
    "SOCIAL.md",
    "PRESENTATION.md",
    "DEMO_STORYBOARD.md",
    "ALGORITHM.md",
    "CHANGELOG.md",
    "SOUL_MAST.md"
)

$rules = @(
    @{ Label = "legacy-stack-label"; Pattern = ("m4st" + "claw") },
    @{ Label = "old-tooling-phrase"; Pattern = ("pentest" + "\s+MCPs") },
    @{ Label = "internal-path-label"; Pattern = ("bridge" + "_core") },
    @{ Label = "private-identity-layer"; Pattern = ("SOUL" + "\s+identity") },
    @{ Label = "versioned-workspace-label"; Pattern = ("Open" + "Work\s+v\d+") },
    @{ Label = "old-server-count-claim"; Pattern = ("15\s+hardened\s+MCP\s+servers") },
    @{ Label = "old-cache-label"; Pattern = ("semantic" + "[-\s]+cache") },
    @{ Label = "old-key-rotation-claim"; Pattern = ("56\s+API\s+key\s+rotation") },
    @{ Label = "legacy-agent-label"; Pattern = ("EIG" + "ENT") },
    @{ Label = "old-agent-count-claim"; Pattern = ("lean\s+6-agent\s+config") },
    @{ Label = "old-provider-branding"; Pattern = ("NVIDIA" + "\s+NIM") },
    @{ Label = "old-philosophy-label"; Pattern = ("working" + "-first\s+philosophy") }
)

$findings = New-Object System.Collections.Generic.List[object]
foreach ($doc in $publicDocs) {
    $path = Join-Path $Root $doc
    if (-not (Test-Path -LiteralPath $path)) {
        continue
    }
    $lineNumber = 0
    foreach ($line in Get-Content -LiteralPath $path) {
        $lineNumber += 1
        $lineForScan = $line -replace "https?://\S+", ""
        foreach ($rule in $rules) {
            if ($lineForScan -match "(?i)$($rule.Pattern)") {
                $findings.Add([PSCustomObject]@{
                    File = $path
                    Line = $lineNumber
                    Rule = $rule.Label
                })
            }
        }
    }
}

if ($findings.Count -gt 0) {
    $findings | Select-Object File, Line, Rule | ConvertTo-Json -Depth 3
    Write-Host ""
    Write-Host "Status: FAIL"
    exit 2
}

[PSCustomObject]@{
    Status = "PASS"
    FilesScanned = $publicDocs.Count
    RuleCount = $rules.Count
} | Format-List
