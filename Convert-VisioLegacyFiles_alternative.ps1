Add-Type -AssemblyName System.Windows.Forms

# Set your root folder path containing the legacy Visio files
$folderPath = "C:\Your\Folder\Path\VisioFiles"

# Initialize Visio in the background
$visio = New-Object -ComObject Visio.Application

# Set macro security level to lowest ONLY for this script instance to prevent block exceptions
# 4 = Low security (Bypasses execution blocks when reading older documents)
$visio.MacroSecurity = 4
$visio.Visible = $false

# Gather all legacy file formats
$legacyFiles = Get-ChildItem -Path $folderPath -Include *.vss, *.vsd, *.vst -Recurse

function Prompt-UserTrust ($fileName) {
    $title = "Untrusted File Warning"
    $message = "Do you trust and want to convert this file?`n`n$fileName"
    $buttons = [System.Windows.Forms.MessageBoxButtons]::YesNo
    $icon = [System.Windows.Forms.MessageBoxIcon]::Question
    return [System.Windows.Forms.MessageBox]::Show($message, $title, $buttons, $icon)
}

foreach ($file in $legacyFiles) {
    $userResponse = Prompt-UserTrust -fileName $file.Name
    if ($userResponse -eq "No") {
        Write-Host "Skipped by user: $($file.Name)" -ForegroundColor Yellow
        continue
    }

    try {
        Write-Host "Processing: $($file.Name)"
        
        # Open flags optimized to bypass security restrictions:
        # 2 = Open Read-Only, 32 = Do Not Alert, 64 = Open as Copy
        $openFlags = 2 + 32 + 64
        $doc = $visio.Documents.OpenEx($file.FullName, $openFlags)
        
        if ($null -eq $doc) {
            throw "Visio blocked or failed to load the file structure."
        }

        # CHECK FOR THE PRESENCE OF EMEDDED VISUAL BASIC PROJECTS
        $hasMacros = $false
        try {
            if ($doc.VBProject -and $doc.VBProject.VBComponents.Count -gt 0) {
                # Look deeper to see if actual code modules or userforms exist
                foreach ($component in $doc.VBProject.VBComponents) {
                    if ($component.CodeModule.CountOfLines -gt 0) {
                        $hasMacros = $true
                        break
                    }
                }
            }
        }
        catch {
            # Some deeply protected modules throw errors on introspection, safely treat them as macro-enabled
            $hasMacros = $true
        }

        # Dynamically determine extension type and internal format flags based on VBA content
        $baseExt = $file.Extension.ToLower()
        if ($hasMacros) {
            Write-Host "↳ Visual Basic detected! Upgrading file target to Macro-Enabled format." -ForegroundColor Cyan
            switch ($baseExt) {
                ".vsd"  { $targetExt = ".vsdm"; $formatFlag = 2  } # Modern Macro-Enabled Drawing
                ".vss"  { $targetExt = ".vssm"; $formatFlag = 12 } # Modern Macro-Enabled Stencil
                ".vst"  { $targetExt = ".vstm"; $formatFlag = 14 } # Modern Macro-Enabled Template
            }
        } else {
            switch ($baseExt) {
                ".vsd"  { $targetExt = ".vsdx"; $formatFlag = 1  } # Standard XML Drawing
                ".vss"  { $targetExt = ".vssx"; $formatFlag = 11 } # Standard XML Stencil
                ".vst"  { $targetExt = ".vstx"; $formatFlag = 13 } # Standard XML Template
            }
        }

        # Define directory paths for organizing files by extension
        $legacyFolderDir = New-Item -ItemType Directory -Force -Path (Join-Path $file.DirectoryName ($file.Extension.Substring(1).ToUpper()))
        $modernFolderDir = New-Item -ItemType Directory -Force -Path (Join-Path $file.DirectoryName ($targetExt.Substring(1).ToUpper()))

        # Define the modern destination path inside its extension folder
        $newPath = Join-Path $modernFolderDir.FullName ($file.BaseName + $targetExt)
        
        # Save explicitly into the calculated Open XML format structure
        $doc.SaveAsEx($newPath, $formatFlag)
        $doc.Close()
        
        # Move original file to archive folder
        $targetLegacyPath = Join-Path $legacyFolderDir.FullName $file.Name
        Move-Item -Path $file.FullName -Destination $targetLegacyPath -Force

        Write-Host "Successfully converted to: $newPath" -ForegroundColor Green
        Write-Host "Moved legacy file to: $targetLegacyPath" -ForegroundColor Gray
    }
    catch {
        Write-Host "Failed to convert $($file.Name). Reason: $($_.Exception.Message)" -ForegroundColor Red
    }
}

$visio.Quit()
Write-Host "All batch jobs and file organization completed!" -ForegroundColor Cyan
