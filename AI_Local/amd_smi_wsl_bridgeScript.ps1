while($true) {
    try {
        # Check if the WSL distro is actually running
        $wsl_info = wsl --list --verbose | Select-String "Ubuntu"
        if ($wsl_info -match "Running") {
            $wsl_ip = (wsl hostname -I).Trim().Split(" ")[0]
            
            if ($wsl_ip) {
                $port = 9101

                # Update the Windows portproxy to the current WSL IP
                netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0
                netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wsl_ip

                # Ensure the Windows Firewall allows the port
                if (!(Get-NetFirewallRule -Name "WSL_AMD_Exporter" -ErrorAction SilentlyContinue)) {
                    New-NetFirewallRule -DisplayName "WSL_AMD_Exporter" -Name "WSL_AMD_Exporter" -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow
                }
                Write-Output "Bridge updated: 0.0.0.0:$port -> $wsl_ip"
            }
        }
    } catch {
        Write-Error "Bridge update failed: $_"
    }
    # Re-verify every hour (or whenever the service starts)
    Start-Sleep -Seconds 3600
}
