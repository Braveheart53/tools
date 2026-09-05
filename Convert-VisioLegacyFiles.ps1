<#
.SYNOPSIS
    Batch-converts legacy Visio binary files (.vsd, .vss, .vst) to the
    modern Open XML formats (.vsdx, .vssx, .vstx, or their macro-enabled
    equivalents) using Visio COM automation, then sorts every file it
    manages into per-extension subfolders.

.DESCRIPTION
    Drives a hidden instance of Visio via COM to open every legacy
    drawing (.vsd), stencil (.vss), and template (.vst) file found in
    a target folder, and re-saves each one in its corresponding modern
    XML-based format (or the macro-enabled sibling, if the document
    carries a VBA project - see the 0.4.0 note below). Visio infers the
    output format from the file extension passed to SaveAs, so no
    numeric format codes are used.

    After conversion, every file in the nine extensions this script
    deals with (.vsd/.vss/.vst and their six modern counterparts) is
    sorted into a matching subfolder named after its extension (e.g.
    all .vstx files end up in a VSTX folder). This sorting pass always
    runs, even on a run that converts nothing - see the 0.5.0 note.

    Requires a licensed, locally-installed copy of Visio (Standard or
    Professional) - this is COM automation of the desktop app, not a
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

.PARAMETER TimeoutSeconds
    Maximum seconds to wait for a single file's conversion before it is
    treated as hung, killed, and logged as failed. Default 120.

.NOTES
    Script    : Convert-VisioLegacyFiles.ps1
    Version   : 0.5.0   (semantic versioning: MAJOR.MINOR.PATCH)
    Author    : Generated for user, reviewed for logic correctness
    Revision history:
        0.1.0 - Initial internal draft. Handles .vsd/.vss/.vst -> .vsdx/.vssx/.vstx,
                logging, error handling, COM cleanup.
        0.2.0 - Fixed indefinite hang: because Visio runs with Visible=$false,
                a native modal dialog on a problem file (format-update prompt,
                broken link, password, unsupported-feature warning on Save)
                is invisible and blocks forever with no way to dismiss it.
                Each file's open/save/close now runs in its own isolated
                background job with a hard timeout; a timed-out job is
                stopped, its orphaned VISIO.EXE process is killed, the file
                is logged as 'Failed (timeout)', and the batch continues
                with a fresh Visio instance for the next file.
        0.2.1 - Removed $visio.AutomationSecurity assignment: that property
                belongs to Word/Excel/PowerPoint's Office-core object model,
                not Visio's Application object, so setting it threw
                "cannot be found on this object" before any file was even
                opened - which is why every file failed identically
                regardless of type. AlertResponse (which IS valid on Visio)
                is retained.
        0.3.0 - Distinguished a second, separate failure mode: Trust Center's
                File Block Settings can refuse to open specific legacy
                formats/versions outright, throwing a catchable COM
                exception rather than hanging. These are now detected by
                message pattern, logged as 'Failed (Trust Center block)'
                (separate from generic failures and from timeouts), and
                called out in the console summary with the Trust Center
                setting path to fix them. This is distinct from the 0.2.0
                hang fix: File Block errors throw immediately, while the
                invisible-dialog case never throws and relies on the
                timeout instead - a batch can hit both simultaneously.
        0.3.1 - Replaced every em dash (U+2014) with a plain ASCII hyphen.
                The file had no UTF-8 BOM, and Windows PowerShell 5.1 reads
                BOM-less .ps1 files using the system ANSI codepage, not
                UTF-8; the misdecoded em dash landed on a Unicode "smart
                quote" byte, which PowerShell's tokenizer treats as
                equivalent to a real quote character (a documented
                convenience for text pasted from Word) - so it was silently
                terminating string literals mid-line. Script is now pure
                ASCII to remove any dependence on file encoding/BOM.
        0.3.2 - Fixed wrong OpenEx flag value: 16 is visOpenMinimized, not
                visOpenMacrosDisabled (that's 128) - per the Visio VBA
                reference's VisOpenSaveArgs enum. Macros were therefore
                never actually being disabled on open, which is one more
                thing (an Auto_Open macro) that could have contributed to
                an invisible hang on a problem file. Also added Trusted
                Locations as a second documented workaround in the
                console's Trust Center block guidance.
        0.4.0 - Added macro-enabled fallback: the modern "x" formats
                (.vsdx/.vssx/.vstx) are macro-free by definition and
                Visio refuses to save a document with an embedded VBA
                project into one ("VB projects cannot be saved in
                macro-free files"). Rather than pre-checking via
                Document.VBProject (which Microsoft's reference warns
                will silently CREATE an empty VBA project as a side
                effect of merely reading it on a file that has none),
                the job now attempts the macro-free save first and,
                only on that specific error, retries as the
                macro-enabled sibling (.vsdm/.vssm/.vstm). Successes
                using the fallback are called out distinctly in the
                console, the CSV log's TargetFile reflects the actual
                extension used, and a new Notes column records why.
                The pre-flight "target already exists" check now also
                considers the macro-enabled path, since which one
                will be produced isn't known until the file is opened.
        0.5.0 - Added a folder-sorting pass: after conversion, every
                file across the nine extensions this script deals with
                (.vsd/.vss/.vst plus their six modern counterparts) is
                moved into a same-named subfolder (VSD, VSTX, VSDM,
                etc.) directly under FolderPath. Nothing else present
                in FolderPath is touched.

                This pass always runs, even on a run that converts
                zero files - the previous unconditional 'return' on
                "no legacy files found" was removed so execution
                always reaches the sort step. It's driven by a new
                Get-VisioManagedFiles helper that, in addition to
                whatever -Recurse specifies, always also checks this
                script's own per-extension folders one level deep -
                so a file that failed conversion and got swept into
                its VSD/VSS/VST folder keeps being found by later
                non-recursive re-runs, instead of silently vanishing
                from view (which a naive top-level-only re-scan after
                sorting would otherwise cause).

                The CSV log is now written AFTER sorting instead of
                before, with SourceFile/TargetFile patched to final
                post-move locations - writing it beforehand, at the
                old conversion-time paths, would have made the log
                stale the instant the sort pass moved anything.
                Name collisions during a move (e.g. the same filename
                converted from two different -Recurse subfolders) are
                resolved by appending " (2)", " (3)", etc. rather than
                overwriting either file.

                Also fixed a duplication bug that sorting itself would
                otherwise cause: the pre-conversion "does the target
                already exist" check only ever looked next to the
                source file, but after sorting, a file's source (in
                VST) and its output (in VSTX) live in different
                folders. Without this fix, re-running the script to
                pick up a handful of still-failing files would fail to
                recognize every already-converted file as done and
                reconvert (and duplicate) all of them. The check now
                also looks in the properly-sorted location for both
                the macro-free and macro-enabled extensions.

    Visio COM automation is not thread-safe across processes - each job
    below spins up its own dedicated Visio.Application instance, which is
    why this uses per-file background *jobs* (isolated processes) rather
    than in-process parallelism. Jobs still run one-at-a-time, sequentially,
    because concurrent Visio instances competing for the same user profile
    are unsupported and prone to corruption; the isolation here is for
    fault-tolerance (a hang can't take down the batch), not for speed.

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

    [string]$LogPath,

    [int]$TimeoutSeconds = 120
)

# ----------------------------------------------------------------------
# Constants: map each legacy extension to its modern replacement.
# (Visio's SaveAs/SaveAsEx infers the on-disk format purely from the
# file extension of the target path, so no numeric FileFormat codes
# are required here - this is the officially recommended approach and
# avoids the ambiguity of the SaveAsEx flag argument used in the
# original example script, which controls save *options*, not format.)
# ----------------------------------------------------------------------
$ExtensionMap = @{
    '.vsd' = '.vsdx'   # Legacy drawing      -> modern drawing
    '.vss' = '.vssx'   # Legacy stencil      -> modern stencil
    '.vst' = '.vstx'   # Legacy template     -> modern template
}

# The three legacy binary extensions this script converts FROM.
$LegacyExtensions = @('vsd', 'vss', 'vst')
# All nine extensions this script ever produces or consumes - this is
# the exact and only scope of the folder-sorting pass near the end of
# the script. Anything else found under FolderPath (other document
# types, or even OTHER legacy Visio XML formats this script was never
# asked to convert, like .vdx/.vsx/.vtx) is left exactly where it is.
$AllManagedExtensions = @('vsd', 'vss', 'vst', 'vsdx', 'vssx', 'vstx', 'vsdm', 'vssm', 'vstm')

# ----------------------------------------------------------------------
# Finds files under FolderPath matching the given extensions (no dot,
# e.g. 'vsd'). Always checks the top level of FolderPath. If
# -DeepRecurse is set (this script passes its own -Recurse switch
# through), also searches every subfolder without limit. If NOT set,
# still always checks this script's own per-extension managed folders
# (VSD, VSTX, etc. - one per extension, uppercase, no dot, as created
# by the sorting pass) one level deep, so a file the sorting pass
# swept into one of those folders on a previous run keeps being found
# without requiring -Recurse. That's what lets "just re-run the
# script" work as a retry loop even after files have been organized.
# ----------------------------------------------------------------------
function Get-VisioManagedFiles {
    param(
        [string[]]$ExtList,
        [switch]$DeepRecurse
    )

    $found = New-Object System.Collections.Generic.List[System.IO.FileInfo]
    $includePatterns = $ExtList | ForEach-Object { "*.$_" }

    if ($DeepRecurse) {
        $params = @{
            Path    = Join-Path $FolderPath '*'
            Include = $includePatterns
            File    = $true
            Recurse = $true
        }
        Get-ChildItem @params | ForEach-Object { $found.Add($_) }
    }
    else {
        $topParams = @{ Path = $FolderPath; Include = $includePatterns; File = $true }
        Get-ChildItem @topParams | ForEach-Object { $found.Add($_) }

        foreach ($ext in $ExtList) {
            $managedFolder = Join-Path $FolderPath $ext.ToUpper()
            if (Test-Path $managedFolder -PathType Container) {
                Get-ChildItem -Path $managedFolder -Filter "*.$ext" -File |
                    ForEach-Object { $found.Add($_) }
            }
        }
    }

    # De-duplicate by full path (cheap insurance; shouldn't normally
    # be needed, since the two branches above are disjoint sources).
    return @($found | Sort-Object FullName -Unique)
}

# Default log path if none supplied
if (-not $LogPath) {
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $LogPath = Join-Path $FolderPath "VisioConversionLog_$timestamp.csv"
}

# ----------------------------------------------------------------------
# Gather candidate files across all three legacy extensions
# ----------------------------------------------------------------------
$legacyFiles = Get-VisioManagedFiles -ExtList $LegacyExtensions -DeepRecurse:$Recurse

if ($legacyFiles.Count -eq 0) {
    Write-Host "No .vsd, .vss, or .vst files found to convert in '$FolderPath' (including its own VSD/VSS/VST sort folders)." -ForegroundColor Yellow
    Write-Host "Proceeding to the folder-sort pass anyway, since that runs regardless of whether anything was converted." -ForegroundColor Yellow
}
else {
    Write-Host "Found $($legacyFiles.Count) legacy Visio file(s) to convert." -ForegroundColor Cyan
}

# ----------------------------------------------------------------------
# Scriptblock that does the actual COM work for ONE file. This runs
# inside its own background job (= its own process), so it gets its
# own private Visio.Application instance. That isolation is the whole
# point: if this file makes Visio throw an invisible modal dialog, the
# hang is confined to this one job and can be killed on a timeout
# without touching the main script or any other file's conversion.
# ----------------------------------------------------------------------
$conversionScriptBlock = {
    param($SrcPath, $DstPath)

    $visio = $null
    $doc = $null
    try {
        $visio = New-Object -ComObject Visio.Application
        $visio.Visible = $false

        # Suppress Visio's own scripted alert boxes
        $visio.AlertResponse = 1

        # Note: unlike Word/Excel/PowerPoint, Visio's Application object
        # does not expose an AutomationSecurity property (that's an
        # Office-core property those other apps opt into; Visio never
        # did) - do not set it, it throws "cannot be found on this object".

        # OpenEx flags, per the Visio VBA reference (VisOpenSaveArgs enum):
        #   visOpenRW             = &H20 = 32
        #   visOpenHidden         = &H40 = 64
        #   visOpenMacrosDisabled = &H80 = 128
        # (32 | 64 | 128 = 224). Open read/write, hidden, with VBA macros
        # disabled - macros-disabled matters here specifically because an
        # Auto_Open macro in an old file is one more thing that can pop a
        # dialog and hang an invisible session.
        $doc = $visio.Documents.OpenEx($SrcPath, 32 -bor 64 -bor 128)

        # SaveAs infers the target format purely from DstPath's
        # extension - works the same for drawings, stencils, and
        # templates, whichever type was actually opened. HOWEVER: if
        # the document carries a VBA project, Visio refuses to save it
        # into a macro-free extension (.vsdx/.vssx/.vstx) - only the
        # "m" siblings (.vsdm/.vssm/.vstm) can hold macros.
        #
        # Deliberately NOT checking this in advance via
        # Document.VBProject: Microsoft's own reference for that
        # property states that reading it on a document with no
        # existing VBA project SILENTLY CREATES an empty one - a
        # destructive side effect just from checking. It also requires
        # "Trust access to the VBA project object model" to be enabled
        # in Trust Center, which is unlikely to be on by default here.
        # So: attempt the macro-free save first, and fall back to the
        # macro-enabled extension only if Visio specifically rejects it
        # for that reason - this is also exactly what a human doing
        # this by hand in the Visio UI would do.
        $finalPath = $DstPath
        $usedMacroFallback = $false
        try {
            $doc.SaveAs($DstPath)
        }
        catch {
            if ($_.Exception.Message -match 'cannot be saved.*macro-free') {
                # Swap the trailing 'x' for 'm': vsdx->vsdm, vssx->vssm,
                # vstx->vstm - the one-letter difference between every
                # macro-free/macro-enabled pair in the modern Visio
                # format family.
                $macroPath = $DstPath.Substring(0, $DstPath.Length - 1) + 'm'
                $doc.SaveAs($macroPath)
                $finalPath = $macroPath
                $usedMacroFallback = $true
            }
            else {
                throw
            }
        }
        $doc.Close()
        $doc = $null

        $visio.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($visio)
        $visio = $null

        return @{ Success = $true; Error = $null; FinalPath = $finalPath; UsedMacroFallback = $usedMacroFallback }
    }
    catch {
        $msg = $_.Exception.Message
        # Trust Center's "File Block Settings" can refuse to open specific
        # legacy formats/versions outright - this throws a catchable COM
        # exception (unlike the invisible-dialog case, which times out
        # instead of throwing). Flag it distinctly so the two root causes
        # aren't confused in the log: this one needs a Trust Center /
        # Group Policy change, not a longer timeout.
        if ($msg -match 'blocked|Trust Center|not (a )?valid file') {
            return @{ Success = $false; Error = "Blocked by Trust Center File Block Settings: $msg" }
        }
        return @{ Success = $false; Error = $msg }
    }
    finally {
        # Best-effort cleanup even on failure; if Visio itself is the
        # thing that's hung, these calls may not return either - that's
        # fine, the caller's job-timeout handles that case by killing
        # the whole process instead of waiting on cleanup here.
        if ($doc) { try { $doc.Close() } catch { } }
        if ($visio) {
            try { $visio.Quit() } catch { }
            try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($visio) } catch { }
        }
    }
}

# ----------------------------------------------------------------------
# Drive one job per file, sequentially, each bounded by -TimeoutSeconds
# ----------------------------------------------------------------------
$results = New-Object System.Collections.Generic.List[Object]
$count = 0

foreach ($file in $legacyFiles) {
    $count++
    $ext = $file.Extension.ToLower()
    $newExt = $ExtensionMap[$ext]
    $newPath = Join-Path $file.DirectoryName ($file.BaseName + $newExt)
    # Precompute the macro-enabled sibling path too (e.g. .vstx -> .vstm):
    # we don't know until the job runs whether this file has an embedded
    # VBA project, so the pre-flight "does the target already exist"
    # check below has to consider both possible outcomes.
    $macroFallbackPath = $newPath.Substring(0, $newPath.Length - 1) + 'm'
    $macroExt = $newExt.Substring(0, $newExt.Length - 1) + 'm'

    # A file converted (and then sorted) on a PREVIOUS run no longer
    # sits next to its source: the sort pass at the end of the script
    # moves the source into a FolderPath\VST folder and the output
    # into a separate FolderPath\VSTX (or VSTM) folder. So the
    # existence check has to look in both the same-directory location
    # (fresh, not-yet-sorted run) AND the properly-sorted location
    # (a re-run after sorting) - otherwise a re-run to pick up a few
    # still-failing files would fail to recognize every already-done
    # file as done, and duplicate all of them.
    $sortedNewPath = Join-Path (Join-Path $FolderPath $newExt.TrimStart('.').ToUpper()) ($file.BaseName + $newExt)
    $sortedMacroPath = Join-Path (Join-Path $FolderPath $macroExt.TrimStart('.').ToUpper()) ($file.BaseName + $macroExt)

    Write-Host "[$count/$($legacyFiles.Count)] Converting: $($file.Name) -> $(Split-Path $newPath -Leaf)"

    $record = [PSCustomObject]@{
        SourceFile = $file.FullName
        TargetFile = $newPath
        Status     = 'Pending'
        Error      = ''
        Notes      = ''
        Timestamp  = Get-Date -Format 'o'
    }

    $existingTarget = @($newPath, $macroFallbackPath, $sortedNewPath, $sortedMacroPath) |
        Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($existingTarget) {
        Write-Host "  Skipped: already converted (found at $existingTarget)." -ForegroundColor Yellow
        $record.Status = 'Skipped (target exists)'
        $record.TargetFile = $existingTarget
        $results.Add($record)
        continue
    }

    if (-not $PSCmdlet.ShouldProcess($file.FullName, "Convert to $newExt")) {
        $record.Status = 'Skipped (WhatIf)'
        $results.Add($record)
        continue
    }

    # Snapshot existing VISIO.EXE process IDs so that, on timeout, we
    # only kill the orphan(s) this job spawned - not a Visio instance
    # the user may have open interactively elsewhere.
    $priorVisioPids = (Get-Process -Name VISIO -ErrorAction SilentlyContinue).Id

    $job = Start-Job -ScriptBlock $conversionScriptBlock -ArgumentList $file.FullName, $newPath
    $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds

    if (-not $completed) {
        Write-Host "  Failed: exceeded ${TimeoutSeconds}s timeout (likely a hidden modal dialog) - killing and continuing." -ForegroundColor Red
        Stop-Job -Job $job -ErrorAction SilentlyContinue

        $newVisioPids = (Get-Process -Name VISIO -ErrorAction SilentlyContinue).Id
        foreach ($procId in ($newVisioPids | Where-Object { $priorVisioPids -notcontains $_ })) {
            try { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue } catch { }
        }

        $record.Status = 'Failed (timeout)'
        $record.Error = "Exceeded ${TimeoutSeconds}s - file likely triggers a modal dialog (format-update prompt, broken link, password, unsupported feature on save). Open it manually in Visio to diagnose."
    }
    else {
        $jobResult = Receive-Job -Job $job
        if ($jobResult.Success) {
            if ($jobResult.UsedMacroFallback) {
                Write-Host "  Success (contains a VBA project - saved as $(Split-Path $jobResult.FinalPath -Leaf) instead)." -ForegroundColor Green
                $record.TargetFile = $jobResult.FinalPath
                $record.Notes = 'Document contains a VBA project; macro-free extension was rejected by Visio, saved with the macro-enabled extension instead.'
            }
            else {
                Write-Host "  Success." -ForegroundColor Green
            }
            $record.Status = 'Success'
            if ($DeleteOriginal) {
                Remove-Item -Path $file.FullName -Force
                Write-Host "  Original deleted." -ForegroundColor DarkYellow
            }
        }
        else {
            Write-Host "  Failed: $($jobResult.Error)" -ForegroundColor Red
            if ($jobResult.Error -like 'Blocked by Trust Center*') {
                $record.Status = 'Failed (Trust Center block)'
            }
            else {
                $record.Status = 'Failed'
            }
            $record.Error = $jobResult.Error
        }
    }

    Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    $results.Add($record)
}

# ----------------------------------------------------------------------
# Console recap of conversion results. The CSV log itself is written
# at the very end of the script, after the folder-sorting pass, so it
# reflects final file locations instead of going stale the moment
# sorting moves things.
# ----------------------------------------------------------------------
$successCount = ($results | Where-Object Status -eq 'Success').Count
$macroCount   = ($results | Where-Object { $_.Notes -like 'Document contains a VBA project*' }).Count
$failCount    = ($results | Where-Object Status -eq 'Failed').Count
$timeoutCount = ($results | Where-Object Status -eq 'Failed (timeout)').Count
$blockCount   = ($results | Where-Object Status -eq 'Failed (Trust Center block)').Count
$skipCount    = ($results | Where-Object { $_.Status -like 'Skipped*' }).Count

Write-Host "`nBatch conversion complete!" -ForegroundColor Cyan
Write-Host "  Succeeded: $successCount  (of which $macroCount saved macro-enabled, e.g. .vstm)" -ForegroundColor Green
Write-Host "  Failed:    $failCount" -ForegroundColor $(if ($failCount -gt 0) { 'Red' } else { 'Gray' })
Write-Host "  Timed out: $timeoutCount" -ForegroundColor $(if ($timeoutCount -gt 0) { 'Red' } else { 'Gray' })
Write-Host "  Blocked:   $blockCount" -ForegroundColor $(if ($blockCount -gt 0) { 'Red' } else { 'Gray' })
Write-Host "  Skipped:   $skipCount" -ForegroundColor Yellow

if ($blockCount -gt 0) {
    Write-Host "`n$blockCount file(s) were refused by Visio's Trust Center File Block Settings." -ForegroundColor Yellow
    Write-Host "  Fix: File > Options > Trust Center > Trust Center Settings > File Block Settings," -ForegroundColor Yellow
    Write-Host "  and either uncheck 'Open' for the relevant legacy Visio format, or ask your" -ForegroundColor Yellow
    Write-Host "  Group Policy administrator to adjust it - on a managed machine this is usually" -ForegroundColor Yellow
    Write-Host "  enforced via policy and local Trust Center changes will be overwritten." -ForegroundColor Yellow
    Write-Host "  Alternative: adding the source folder as a Trust Center 'Trusted Location' can" -ForegroundColor Yellow
    Write-Host "  also override File Block for files in that folder, per Microsoft's own guidance." -ForegroundColor Yellow
}

# ----------------------------------------------------------------------
# Sort files by extension into per-extension subfolders (VSD, VSS,
# VST, VSDX, VSSX, VSTX, VSDM, VSSM, VSTM). This always runs,
# independent of whether anything was converted above: a run that
# finds nothing new still tidies up whatever's already there, and a
# file that failed conversion this run still gets swept into its own
# legacy-format folder - which is exactly what lets the retry loop
# above find it again on a later run without needing -Recurse.
#
# Scope is deliberately narrow: only the nine extensions in
# $AllManagedExtensions are touched. Nothing else under FolderPath -
# other document types, or even other legacy Visio XML formats this
# script was never asked to convert, like .vdx/.vsx/.vtx - is moved.
# ----------------------------------------------------------------------
Write-Host "`nSorting files by extension..." -ForegroundColor Cyan

$filesToSort = Get-VisioManagedFiles -ExtList $AllManagedExtensions -DeepRecurse:$Recurse
$sortedCount = 0
$collisionCount = 0
# Tracks OriginalFullPath -> NewFullPath for every file actually moved,
# so the CSV log written below can be patched to reflect final
# locations instead of the paths recorded at conversion time.
$moveMap = @{}

foreach ($f in $filesToSort) {
    $extFolderName = $f.Extension.TrimStart('.').ToUpper()   # e.g. '.vstx' -> 'VSTX'
    $extFolder = Join-Path $FolderPath $extFolderName

    # Already correctly placed - nothing to do. (PowerShell's default
    # string comparison is case-insensitive, matching how Windows
    # paths behave.)
    if ($f.DirectoryName -eq $extFolder) { continue }

    $destination = Join-Path $extFolder $f.Name
    if (Test-Path $destination) {
        # Name collision - e.g. the same filename got converted from
        # two different source subfolders under -Recurse. Disambiguate
        # rather than silently overwrite either one.
        $i = 2
        do {
            $candidateName = "{0} ({1}){2}" -f $f.BaseName, $i, $f.Extension
            $candidate = Join-Path $extFolder $candidateName
            $i++
        } while (Test-Path $candidate)
        $destination = $candidate
        $collisionCount++
        Write-Host "  Name collision: $($f.Name) -> $(Split-Path $destination -Leaf)" -ForegroundColor Yellow
    }

    if ($PSCmdlet.ShouldProcess($f.FullName, "Move to $destination")) {
        try {
            if (-not (Test-Path $extFolder)) {
                New-Item -Path $extFolder -ItemType Directory -Force | Out-Null
            }
            Move-Item -Path $f.FullName -Destination $destination -Force -ErrorAction Stop
            $moveMap[$f.FullName] = $destination
            $sortedCount++
        }
        catch {
            Write-Host "  Failed to move $($f.Name): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Write-Host "Sorted $sortedCount file(s) into extension folders under '$FolderPath'." -ForegroundColor Cyan
if ($collisionCount -gt 0) {
    Write-Host "  ($collisionCount filename collision(s) resolved by renaming - see messages above.)" -ForegroundColor Yellow
}

# ----------------------------------------------------------------------
# Patch this run's logged paths for anything the sort pass just moved,
# then write the CSV log using final, accurate locations.
# ----------------------------------------------------------------------
foreach ($r in $results) {
    if ($moveMap.ContainsKey($r.TargetFile)) { $r.TargetFile = $moveMap[$r.TargetFile] }
    if ($moveMap.ContainsKey($r.SourceFile)) { $r.SourceFile = $moveMap[$r.SourceFile] }
}

if ($results.Count -gt 0) {
    $results | Export-Csv -Path $LogPath -NoTypeInformation -Encoding UTF8
    Write-Host "`nLog written to: $LogPath" -ForegroundColor Cyan
}
else {
    Write-Host "`nNo conversions were attempted this run, so no CSV log was written." -ForegroundColor Gray
}