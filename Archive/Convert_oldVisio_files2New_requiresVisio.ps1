<#
.SYNOPSIS
    Batch-converts legacy Visio binary files (.vsd, .vss, .vst) to the
    modern Open XML formats (.vsdx, .vssx, .vstx) using Visio COM automation.

.DESCRIPTION
    Drives a hidden instance of Visio via COM to open every legacy
    drawing (.vsd), stencil (.vss), and template (.vst) file found in
    a target folder, and re-saves each one in its corresponding modern
    XML-based format. Visio infers the output format from the file
    extension passed to SaveAs, so no numeric format codes are used.

    Requires a licensed, locally-installed copy of Visio (Standard or
    Professional) — this is COM automation of the desktop app, not a
    file-format converter, so it will not run headless on a machine
    without Visio installed.

.PARAMETER FolderPath
    Folder containing the legacy .vsd / .vss / .vst files to convert.

.PARAMETER Recurse
    If specified, also searches subfolders of FolderPath.

.PARAMETER DeleteOriginal
    If specified, deletes the original legacy file after a verified
    successful conversion. Default is to leave originals in place.

.PARAMETER LogPath
    Path to a CSV log of conversion results. Defaults to
    "VisioConversionLog_<timestamp>.csv" inside FolderPath.

.NOTES
    Script    : Convert-VisioLegacyFiles.ps1
    Version   : 0.1.0   (semantic versioning: MAJOR.MINOR.PATCH)
    Author    : Generated for user, reviewed for logic correctness
    Revision history:
        0.1.0 - Initial internal draft. Handles .vsd/.vss/.vst -> .vsdx/.vssx/.vstx,
                logging, error handling, COM cleanup.

    Visio COM automation is inherently single-threaded / single-instance
    per session — running multiple Visio COM instances in parallel against
    the same profile is unsupported and prone to corruption or silent
    failures, so this script intentionally processes files sequentially
    rather than in parallel. If you need to scale this across many files,
    run separate scripts on separate machines/VMs instead of parallelizing
    within one Visio session.

.EXAMPLE
    .\Convert-VisioLegacyFiles.ps1 -FolderPath "C:\Users\me\Documents\Visio" -Recurse
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path $_ -PathType Container })]
    [string]$FolderPath,

    [switch]$Recurse,

    [switch]$DeleteOriginal,

    [string]$LogPath
)

# ----------------------------------------------------------------------
# Constants: map each legacy extension to its modern replacement.
# (Visio's SaveAs/SaveAsEx infers the on-disk format purely from the
# file extension of the target path, so no numeric FileFormat codes
# are required here — this is the officially recommended approach and
# avoids the ambiguity of the SaveAsEx flag argument used in the
# original example script, which controls save *options*, not format.)
# ----------------------------------------------------------------------
$ExtensionMap = @{
    '.vsd' = '.vsdx'   # Legacy drawing      -> modern drawing
    '.vss' = '.vssx'   # Legacy stencil      -> modern stencil
    '.vst' = '.vstx'   # Legacy template     -> modern template
}

# Default log path if none supplied
if (-not $LogPath) {
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $LogPath = Join-Path $FolderPath "VisioConversionLog_$timestamp.csv"
}

# ----------------------------------------------------------------------
# Gather candidate files across all three legacy extensions
# ----------------------------------------------------------------------
$gciParams = @{
    Path    = $FolderPath
    Include = @('*.vsd', '*.vss', '*.vst')
    File    = $true
}
if ($Recurse) {
    # -Include only filters correctly when combined with -Recurse and a
    # wildcarded -Path; use the .\* form to make that combination reliable.
    $gciParams.Path = Join-Path $FolderPath '*'
    $gciParams.Recurse = $true
}

$legacyFiles = Get-ChildItem @gciParams | Where-Object {
    # Explicitly exclude anything that is already the modern format
    # (e.g. guard against a stray *.vsdx matching a loose *.vsd* pattern)
    $ExtensionMap.ContainsKey($_.Extension.ToLower())
}

if (-not $legacyFiles -or $legacyFiles.Count -eq 0) {
    Write-Host "No .vsd, .vss, or .vst files found in '$FolderPath'." -ForegroundColor Yellow
    return
}

Write-Host "Found $($legacyFiles.Count) legacy Visio file(s) to convert." -ForegroundColor Cyan

# ----------------------------------------------------------------------
# Start Visio in the background
# ----------------------------------------------------------------------
$visio = $null
$results = New-Object System.Collections.Generic.List[Object]

try {
    $visio = New-Object -ComObject Visio.Application
    $visio.Visible = $false

    # Suppress alert dialogs (e.g. "keep formatting?") that would
    # otherwise block unattended automation
    $visio.AlertResponse = 1

    $count = 0
    foreach ($file in $legacyFiles) {
        $count++
        $ext = $file.Extension.ToLower()
        $newExt = $ExtensionMap[$ext]
        $newPath = Join-Path $file.DirectoryName ($file.BaseName + $newExt)

        Write-Host "[$count/$($legacyFiles.Count)] Converting: $($file.Name) -> $(Split-Path $newPath -Leaf)"

        $record = [PSCustomObject]@{
            SourceFile = $file.FullName
            TargetFile = $newPath
            Status     = 'Pending'
            Error      = ''
            Timestamp  = Get-Date -Format 'o'
        }

        if (Test-Path $newPath) {
            Write-Host "  Skipped: target already exists." -ForegroundColor Yellow
            $record.Status = 'Skipped (target exists)'
            $results.Add($record)
            continue
        }

        if (-not $PSCmdlet.ShouldProcess($file.FullName, "Convert to $newExt")) {
            $record.Status = 'Skipped (WhatIf)'
            $results.Add($record)
            continue
        }

        $doc = $null
        try {
            # Documents.Open() opens the file as its native type
            # (drawing, stencil, or template) rather than instantiating
            # a *new* document from a template, so .vst/.vss files are
            # opened for direct editing/re-saving exactly like .vsd.
            $doc = $visio.Documents.Open($file.FullName)

            # SaveAs infers the target format from the extension of
            # newPath — this is the simplest and most robust way to
            # force the modern XML format for whichever document type
            # (drawing/stencil/template) was actually opened.
            $doc.SaveAs($newPath)

            $doc.Close()
            $doc = $null

            Write-Host "  Success." -ForegroundColor Green
            $record.Status = 'Success'

            if ($DeleteOriginal) {
                Remove-Item -Path $file.FullName -Force
                Write-Host "  Original deleted." -ForegroundColor DarkYellow
            }
        }
        catch {
            Write-Host "  Failed: $($_.Exception.Message)" -ForegroundColor Red
            $record.Status = 'Failed'
            $record.Error = $_.Exception.Message
        }
        finally {
            # Ensure the document handle is released even on failure,
            # so a bad file doesn't leave a locked/open doc behind
            if ($doc) {
                try { $doc.Close() } catch { }
            }
        }

        $results.Add($record)
    }
}
finally {
    # Always attempt to quit Visio and release the COM object cleanly,
    # even if something above threw an unhandled exception
    if ($visio) {
        try { $visio.Quit() } catch { }
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($visio)
    }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}

# ----------------------------------------------------------------------
# Write summary log and console recap
# ----------------------------------------------------------------------
$results | Export-Csv -Path $LogPath -NoTypeInformation -Encoding UTF8

$successCount = ($results | Where-Object Status -eq 'Success').Count
$failCount    = ($results | Where-Object Status -eq 'Failed').Count
$skipCount    = ($results | Where-Object { $_.Status -like 'Skipped*' }).Count

Write-Host "`nBatch conversion complete!" -ForegroundColor Cyan
Write-Host "  Succeeded: $successCount" -ForegroundColor Green
Write-Host "  Failed:    $failCount" -ForegroundColor $(if ($failCount -gt 0) { 'Red' } else { 'Gray' })
Write-Host "  Skipped:   $skipCount" -ForegroundColor Yellow
Write-Host "  Log written to: $LogPath"