# Sidelobe Program User Guide

## Quick Start

### Basic Usage
```bash
# Standard usage with input and output files
sidelobe [OPTIONS] <inputScanFilename> <outputScanFilename>

# Alternative syntax
sidelobe [OPTIONS] --in <inputScanFilename> --out <outputScanFilename>

# List file contents without processing
sidelobe --list --log-min input_file.fits
```

### Common Examples
```bash
# Generate sidelobe corrections for GBT data
sidelobe --GBT --overwrite input_scan.fits stray_output.fits

# Apply corrections directly to data
sidelobe --correct-stray --140 input.fits corrected_output.fits

# Extract specific scans with minimal logging
sidelobe --extract --quiet --scan-range 1 100 input.fits subset.fits
```

## Command Line Options

### File Input/Output
- `--in <filename>`: Specify input scan filename
- `--out <filename>`: Specify output scan filename  
- `--overwrite`: Overwrite existing output files
- `--append`: Append to existing output files
- `--list`: List input file contents without processing

### Telescope Configuration
- `--GBT`: Use Green Bank Telescope configuration
- `--140`: Use NRAO 140-foot telescope configuration

### Processing Modes
- `--correct-stray`: Apply stray corrections to input data instead of outputting strayscans
- `--out-stray <filename>`: Output calculated strayscans to separate file
- `--in-stray <filename>`: Use pre-computed strayscans from file
- `--extract`: Copy input spectra to output (with optional filtering)

### Data Calibration
- `--in-cal <factor>`: Apply calibration factor to input spectra
- `--force`: Force processing of normally ignored spectra
- `--reset-units`: Correct erroneous data units in SDFITS files

### Data Selection
- `--scan-range <start> <end>`: Process specific scan number range
- `--index-range <start> <end>`: Process specific file index range
- `--object-keep <pattern>`: Keep only scans matching object name pattern
- `--not-object <pattern>`: Exclude scans matching object name pattern
- `--stokes-range <values>`: Process specific Stokes parameters

### Velocity Processing (SDFITS only)
- `--extract-v-index <low> <high>`: Extract specific velocity index range
- `--extract-v-LSR <Vlow> <Vhigh>`: Extract specific LSR velocity range

### Data Corrections
- `--fix-zero-ra`: Fix problematic RA values near 0.0 degrees
- `--fix-zero-glon`: Fix problematic galactic longitude values
- `--fix-date`: Correct DATE-OBS format issues (enabled by default)

### Atmospheric Corrections
- `--amb <filename>`: Specify ambient conditions file
- `--amb-dt <interp> <extrap>`: Set interpolation/extrapolation limits
- `--amb-set-def <temp> <pressure> <humidity>`: Set default ambient conditions

### Output Control
- `--log-min`: Minimize terminal output (show only scan numbers)
- `--quiet`: Minimal output (only status information)
- `--verbose`: Detailed processing information

## File Formats

### SDFITS Files
- FITS binary tables containing single dish observation data
- Standard format for radio astronomy spectral data
- Contains headers with observation metadata

### SDD Files  
- Binary scan data files
- Native format for some telescope systems
- Compact storage for spectral scan data

### Text Files
- Sun-scan text files for special observations
- Human-readable format for specific use cases

## Processing Workflow

### 1. Data Preparation
```bash
# Check input file contents
sidelobe --list input_data.fits

# Validate file format and scan information
sidelobe --list --log-min input_data.fits
```

### 2. Sidelobe Correction Generation
```bash
# Generate strayscans for GBT data
sidelobe --GBT --overwrite input_scans.fits strayscans.fits

# Include ambient conditions for better accuracy
sidelobe --GBT --amb ambient_data.txt input.fits output.fits
```

### 3. Apply Corrections
```bash
# Apply corrections directly to data
sidelobe --correct-stray --in-stray strayscans.fits input.fits corrected.fits

# Generate both corrected data and strayscans
sidelobe --correct-stray --out-stray stray.fits input.fits corrected.fits
```

### 4. Data Extraction and Filtering
```bash
# Extract specific velocity range
sidelobe --extract --extract-v-LSR -200 200 input.fits velocity_subset.fits

# Extract specific object types
sidelobe --extract --object-keep "NGC*" input.fits galaxy_scans.fits
```

## Troubleshooting

### Common Issues

**File Format Errors**
- Ensure input files are valid SDFITS or SDD format
- Check file permissions and accessibility

**Telescope Configuration**
- Specify telescope type explicitly if auto-detection fails
- Use `--GBT` or `--140` options as appropriate

**Memory/Processing Issues**  
- Use `--quiet` or `--log-min` for large files
- Process data in smaller chunks using range options

**Output File Conflicts**
- Use `--overwrite` to replace existing files
- Use `--append` to add to existing files
- Choose different output filenames

### Error Messages

**"Error: output filename is identical to input filename"**
- Solution: Use different names for input and output files

**"Error: cannot append to a FITS output GLS cube"**
- Solution: Use `--overwrite` instead of `--append` for FITS cubes

**"Error: bad telescope type cannot happen"**
- Solution: Specify telescope type with `--GBT` or `--140`

## Advanced Features

### Ambient Conditions
The program can use ambient condition data for atmospheric corrections:
- Temperature, pressure, and humidity data
- Interpolation between time points
- Default values for missing data

### Quality Control
- Automatic detection of problematic scans
- Warning messages for data inconsistencies  
- Options to skip or fix common issues

### Batch Processing
- Process multiple files with consistent parameters
- Use shell scripts for large-scale data processing
- Integrate with existing pipeline systems

## Performance Tips

1. **Use appropriate logging levels**: `--quiet` for batch processing
2. **Process in chunks**: Use range options for large datasets
3. **Pre-validate inputs**: Use `--list` to check files before processing
4. **Specify telescope type**: Avoid auto-detection overhead
5. **Use appropriate file formats**: Choose optimal format for your workflow

## Integration

The sidelobe program integrates with:
- **GBTIDL**: Green Bank Telescope data analysis environment
- **FITS processing tools**: Standard astronomy file format utilities  
- **Pipeline systems**: Automated data processing workflows
- **Archive systems**: Large-scale data storage and retrieval