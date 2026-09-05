# Set your folder path containing the .vsd files
$folderPath = "C:\Users\[Yo Vds]"

# Initialize Visio in the background
$visio = New-Object -ComObject Visio.Application
$visio.Visible = $false

# Get all .vsd files in the folder
$vsdFiles = Get-ChildItem -Path $folderPath -Filter *.vsd

foreach ($file in $vsdFiles) {
    try {
        Write-Host "Converting: $($file.Name)"
        
        # Open legacy drawing
        $diagram = $visio.Documents.Open($file.FullName)
        
        # Define new path with .vsdx extension
        $newPath = Join-Path $folderPath ($file.BaseName + ".vsdx")
        
        # Save as format 1 specifying modern VSDX format
        $diagram.SaveAsEx($newPath, 1)
        $diagram.Close()
        
        Write-Host "Successfully saved to: $newPath" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to convert $($file.Name): $_" -ForegroundColor Red
    }
}

# Quit Visio instance
$visio.Quit()
Write-Host "Batch conversion complete!" -ForegroundColor Cyan
