<#
.SYNOPSIS
    Configure and build a CMake project with a memory-bounded job count.

.DESCRIPTION
    Written to be called by a model with no arguments, which is the point:
    every value a model could get wrong is derived rather than passed.

    Two problems this solves that a bare `cmake --build` does not:

    1.  TOOLCHAIN DISCOVERY.  The configure lines recorded in this
        deployment's setup notes pass absolute paths to cl.exe with the MSVC
        toolset version embedded, for example
        ...\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe
        That path changes on every Visual Studio update, and a model has no
        way to discover the new one.  This script locates the toolchain with
        vswhere, which ships at a fixed path with every VS 2017+ installer.

    2.  JOB COUNT.  A model told to "build the project" reaches for
        -j$(nproc).  On a machine simultaneously holding a 19 GB model
        resident, memory and not core count is the binding constraint, and
        overshooting does not fail cleanly: the machine swaps, the build
        slows by an order of magnitude, and the resident model may be
        evicted.  The job count here is
            j = min(cores, floor(free_memory / memory_per_job))
        which is the relation published on local-code-build-test.html.

.PARAMETER SourceDir
    CMake source directory.  Defaults to the current directory.

.PARAMETER BuildDir
    Build directory.  Defaults to .\build.

.PARAMETER Config
    Build configuration.  Debug, Release or RelWithDebInfo.

.PARAMETER Jobs
    Explicit job count.  0, the default, derives it from cores and free
    memory as described above.

.PARAMETER MemPerJobGB
    Expected peak resident set of one compiler process, in GiB.  2.0 is a
    planning estimate for template-heavy C++; measure your own by watching
    peak working set during a single-job build of your heaviest translation
    unit.  Plain C is nearer 0.5.

.PARAMETER Generator
    CMake generator.  "Ninja Multi-Config" is the default because Ninja's
    errors are the compiler's own text, where MSBuild interleaves project
    banners and timing that a model will try to interpret as diagnostics.

.PARAMETER ExtraArgs
    Additional arguments passed through to the configure step, for example
    -DGGML_CUDA=ON.

.EXAMPLE
    .\build_cpp.ps1
    Configure and build the current directory in Release with a derived job
    count.

.EXAMPLE
    .\build_cpp.ps1 -Config RelWithDebInfo -ExtraArgs '-DGGML_VULKAN=ON','-DGGML_RPC=ON'
    The llama.cpp configuration used in this deployment.

.NOTES
    Author : William W. Wallace
    Version: 0.0.1
    Created: 2026-10-18

    Requires: CMake, Ninja, and the Visual Studio C++ build tools.
    Run from an ordinary PowerShell prompt; the script does not need a
    Developer PowerShell because it imports the MSVC environment itself.
#>

[CmdletBinding()]
param(
    [string]   $SourceDir   = ".",
    [string]   $BuildDir    = "build",

    [ValidateSet("Debug", "Release", "RelWithDebInfo", "MinSizeRel")]
    [string]   $Config      = "Release",

    [ValidateRange(0, 256)]
    [int]      $Jobs        = 0,

    [ValidateRange(0.1, 64.0)]
    [double]   $MemPerJobGB = 2.0,

    [string]   $Generator   = "Ninja Multi-Config",

    [string[]] $ExtraArgs   = @()
)

# Stop on the first error rather than carrying on with a half-built tree,
# which is what makes the exit code meaningful to a caller.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# ===========================================================================
# 1. Preconditions
# ===========================================================================

function Assert-Command {
    <#
    .SYNOPSIS
        Fail with a actionable message if a required executable is missing.
    #>
    param(
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][string] $Hint
    )
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "'$Name' is not on PATH. $Hint"
    }
}

Assert-Command -Name "cmake" -Hint "Install CMake, or add it to PATH."

if ($Generator -like "Ninja*") {
    Assert-Command -Name "ninja" `
        -Hint "Install Ninja, or pass -Generator 'Visual Studio 17 2022'."
}

if (-not (Test-Path (Join-Path $SourceDir "CMakeLists.txt"))) {
    throw "No CMakeLists.txt in '$SourceDir'. Pass -SourceDir to point at the project root."
}

# ===========================================================================
# 2. Locate the MSVC toolchain
# ===========================================================================

# vswhere lives at a fixed path for every VS 2017 and later installation, so
# this lookup is stable where a hard-coded toolset path is not.
$vswhere = Join-Path ${env:ProgramFiles(x86)} `
    "Microsoft Visual Studio\Installer\vswhere.exe"

if (-not (Test-Path $vswhere)) {
    throw @"
vswhere.exe not found at:
  $vswhere
Install the Visual Studio Build Tools (vs_BuildTools_2022.exe or
vs_BuildTools_2026.exe alongside these pages) with the
'Desktop development with C++' workload.
"@
}

$vsRoot = & $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath

if (-not $vsRoot) {
    throw "vswhere found no installation with the MSVC x64 C++ toolset. " +
          "Add the 'Desktop development with C++' workload."
}

Write-Host "MSVC installation : $vsRoot"

# Import the MSVC environment into this PowerShell session.  vcvars64.bat is
# a batch file, so its exports are captured by running it and reading back
# the resulting environment rather than by dot-sourcing.
$vcvars = Join-Path $vsRoot "VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvars)) {
    throw "vcvars64.bat not found under $vsRoot. The C++ toolset may be incomplete."
}

Write-Host "Importing MSVC environment..."
# `set` after the batch file prints every variable; each NAME=VALUE line is
# applied to this session. cmd /c keeps the batch file's own shell separate.
& cmd.exe /c "`"$vcvars`" >nul 2>&1 && set" | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        # Set-Item on Env: is the supported way to write an environment
        # variable whose name is held in a variable.
        Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2] -ErrorAction SilentlyContinue
    }
}

$clPath = (Get-Command cl.exe -ErrorAction SilentlyContinue).Source
if (-not $clPath) {
    throw "cl.exe still not on PATH after importing the MSVC environment."
}
Write-Host "Compiler          : $clPath"

# ===========================================================================
# 3. Derive the job count
# ===========================================================================

if ($Jobs -le 0) {
    $cores = [Environment]::ProcessorCount

    # FreePhysicalMemory is reported in KiB; 1MB here is PowerShell's
    # 1048576 literal, which converts KiB to GiB.
    $freeGiB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB

    $byMemory = [Math]::Floor($freeGiB / $MemPerJobGB)
    $Jobs = [Math]::Max(1, [Math]::Min($cores, $byMemory))

    Write-Host ("Jobs              : {0}  (cores {1}, free {2:N1} GiB, {3} GiB/job -> memory bound {4})" `
                -f $Jobs, $cores, $freeGiB, $MemPerJobGB, $byMemory)

    if ($byMemory -lt $cores) {
        # Build the whole message first: `Write-Warning (expr) + "str"` does
        # not concatenate in PowerShell, it silently drops the second part.
        $warning = ("Memory-bound: only {0} of {1} cores are usable at " +
                    "{2} GiB per job. Close the model server or add RAM " +
                    "to use the rest.") -f $Jobs, $cores, $MemPerJobGB
        Write-Warning $warning
    }
} else {
    Write-Host "Jobs              : $Jobs  (explicit)"
}

# CMAKE_BUILD_PARALLEL_LEVEL is documented as equivalent to passing
# --parallel, and setting it in the environment means the cap also applies
# to any nested cmake --build this project's own scripts may invoke.
$env:CMAKE_BUILD_PARALLEL_LEVEL = $Jobs

# ===========================================================================
# 4. Configure
# ===========================================================================

$configureArgs = @(
    "-S", $SourceDir
    "-B", $BuildDir
    "-G", $Generator
    # compile_commands.json lets a model read the exact flags for one file
    # instead of inferring them, which removes a class of wrong guesses.
    "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
)
if ($ExtraArgs) { $configureArgs += $ExtraArgs }

Write-Host "`n--- configure ---"
Write-Host "cmake $($configureArgs -join ' ')"
& cmake @configureArgs
if ($LASTEXITCODE -ne 0) {
    throw "CMake configure failed with exit code $LASTEXITCODE."
}

# ===========================================================================
# 5. Build
# ===========================================================================

Write-Host "`n--- build ---"
$buildStart = Get-Date

& cmake --build $BuildDir --config $Config --parallel $Jobs
$buildExit = $LASTEXITCODE

$elapsed = (Get-Date) - $buildStart

if ($buildExit -ne 0) {
    Write-Host ("`nBuild FAILED after {0:N1} s (exit {1})." -f $elapsed.TotalSeconds, $buildExit)
    throw "Build failed with exit code $buildExit."
}

Write-Host ("`nBuild succeeded in {0:N1} s." -f $elapsed.TotalSeconds)
Write-Host "  configuration : $Config"
Write-Host "  jobs          : $Jobs"
Write-Host "  output        : $(Resolve-Path $BuildDir)"

# Amdahl's relation, published on local-code-build-test.html, sets the
# ceiling on what more cores can buy: S_inf = 1/(1-p). Reported here so the
# number is in front of whoever reads the log.
$serialHint = [Math]::Round(1.0 / (1.0 - 0.85), 1)
Write-Host ("`nNote: with a parallel fraction p = 0.85 the speed-up ceiling is " +
            "{0}x regardless of job count; the serial tail is configure and link." -f $serialHint)

exit 0
