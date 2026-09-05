# Set your folder path containing the .vss files
$folderPath = "C:\Users\[Yo Shapes]"

# Initialize Visio in the background
$visio = New-Object -ComObject Visio.Application
$visio.Visible = $false

# Get all .vss files in the folder
$vssFiles = Get-ChildItem -Path $folderPath -Filter *.vss

foreach ($file in $vssFiles) {
    try {
        Write-Host "Converting: $($file.Name)"
        
        # Open legacy stencil
        $stencil = $visio.Documents.Open($file.FullName)
        
        # Define new path with .vssx extension
        $newPath = Join-Path $folderPath ($file.BaseName + ".vssx")
        
        # Save as format 32 (visDoSave + visSaveAsWS for vssx)
        # 11 specifies the modern stencil format code
        $stencil.SaveAsEx($newPath, 11)
        $stencil.Close()
        
        Write-Host "Successfully saved to: $newPath" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to convert $($file.Name): $_" -ForegroundColor Red
    }
}

# Quit Visio instance
$visio.Quit()
Write-Host "Batch conversion complete!" -ForegroundColor Cyan
