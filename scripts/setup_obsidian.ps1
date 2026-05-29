# ============================================================
# setup_obsidian.ps1 - scarica/aggiorna i plugin community
# del vault MeetWiki da GitHub Releases.
# ============================================================
[CmdletBinding()]
param(
    [switch]$Force  # forza il re-download anche se main.js esiste gia'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pluginsDir = Join-Path $root 'MeetWiki\.obsidian\plugins'
$headers = @{ 'User-Agent' = 'meetwiki' }

# id cartella -> repo GitHub (owner/name)
$plugins = [ordered]@{
    'obsidian-kanban'         = 'mgmeyers/obsidian-kanban'
    'dataview'                = 'blacksmithgu/obsidian-dataview'
    'copilot'                 = 'logancyang/obsidian-copilot'
    'obsidian-iconize'        = 'FlorianWoelki/obsidian-iconize'
    'obsidian-style-settings' = 'mgmeyers/obsidian-style-settings'
    'editing-toolbar'         = 'PKM-er/obsidian-editing-toolbar'
    'better-search-views'     = 'ivan-lednev/better-search-views'
    'metadatamenu'            = 'mdelobelle/metadatamenu'
    'obsidian-tasks-plugin'   = 'obsidian-tasks-group/obsidian-tasks'
    'calendar'                = 'liamcain/obsidian-calendar-plugin'
}

New-Item -ItemType Directory -Force -Path $pluginsDir | Out-Null

foreach ($id in $plugins.Keys) {
    $repo = $plugins[$id]
    $dir = Join-Path $pluginsDir $id
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    $main = Join-Path $dir 'main.js'
    if ((Test-Path $main) -and (-not $Force)) {
        Write-Host ("  {0,-25} skip (use -Force to update)" -f $id) -ForegroundColor DarkGray
        continue
    }

    try {
        $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest" -Headers $headers
        $got = @()
        foreach ($n in 'main.js', 'manifest.json', 'styles.css') {
            $a = $rel.assets | Where-Object name -eq $n | Select-Object -First 1
            if ($a) {
                Invoke-WebRequest -Uri $a.browser_download_url -OutFile (Join-Path $dir $n) -UseBasicParsing | Out-Null
                $got += $n
            }
        }
        Write-Host ("  {0,-25} {1,-12} [{2}]" -f $id, $rel.tag_name, ($got -join ',')) -ForegroundColor Green
    }
    catch {
        Write-Host ("  {0,-25} ERROR: {1}" -f $id, $_.Exception.Message) -ForegroundColor Red
    }
}

# Aggiorna community-plugins.json con la lista corrente
$enabled = @($plugins.Keys)
$json = $enabled | ConvertTo-Json
Set-Content -Path (Join-Path $root 'MeetWiki\.obsidian\community-plugins.json') -Value $json -Encoding UTF8
Write-Host "`nSetup completato. Plugin in: $pluginsDir" -ForegroundColor Cyan
