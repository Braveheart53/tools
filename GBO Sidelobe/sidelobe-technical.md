# Sidelobe Program Technical Reference

## Architecture Overview

The sidelobe program is a compiled C/C++ application designed for high-performance radio astronomy data processing. It implements sophisticated algorithms for telescope sidelobe computation and stray radiation correction.

### Binary Information
- **File Type**: ELF 64-bit LSB executable
- **Target Architecture**: x86-64 
- **Operating System**: GNU/Linux 2.6.9+
- **Linking**: Dynamically linked
- **Debug Information**: Not stripped (symbols available)
- **Interpreter**: /lib64/ld-linux-x86-64.so.2

## Dependencies

### System Libraries
- **libc.so.6**: Standard C library functions
- **libm.so.6**: Mathematical functions (trigonometry, logarithms)
- **System calls**: Socket operations, file I/O, memory management

### Key Functions Used
- Mathematical: `sin`, `cos`, `asin`, `acos`, `atan`, `atan2`, `sqrt`, `log`, `exp`, `floor`, `ceil`
- Memory: `malloc`, `realloc`, `calloc`, `memcpy`, `memset`
- File I/O: `fopen`, `fread`, `fwrite`, `fseek`, `ftell`, `fclose`
- String: `strcpy`, `strcat`, `strcmp`, `strlen`, `strstr`, `sscanf`, `sprintf`
- Time: `gmtime`, `localtime`, `ctime`, `strftime`

## Core Components

### File Format Handlers
The program includes multiple drivers for different file formats:

#### FITS File Support
- **ngp_**: FITS header parsing and navigation
- **ff**: CFITSIO-based FITS file operations
- **root_**: File system operations
- **smem_**: Shared memory management
- **mem_**: Memory-based file operations

#### Supported Formats
- **SDFITS**: Single Dish FITS binary tables
- **SDD**: Binary scan data files  
- **GLS cubes**: Gridded latitude-longitude survey data
- **Text files**: ASCII sun-scan data

### Telescope Models

#### Green Bank Telescope (GBT)
- Sidelobe pattern computation
- Near and far sidelobe matrices
- Non-isotropic beam modeling
- Atmospheric correction handling

#### NRAO 140-foot Telescope
- 43-meter dish sidelobe patterns
- Spherical and planar wave approximations
- Cassegrain and prime focus configurations

### Mathematical Algorithms

#### Sidelobe Computation
- **Beam convolution**: Integration of telescope patterns with sky surveys
- **Matrix operations**: Large-scale numerical computations
- **Interpolation**: Spatial and temporal data interpolation
- **Coordinate transformations**: RA/Dec, Galactic, Azimuth/Elevation

#### Atmospheric Corrections
- **Refraction calculations**: Atmospheric path corrections
- **Opacity modeling**: Atmospheric absorption effects
- **Temperature/pressure/humidity**: Environmental parameter handling

## Data Structures

### Scan Data Format
```c
// Typical scan structure (inferred from strings)
struct scan_data {
    double ra, dec;           // Coordinates
    double glon, glat;        // Galactic coordinates
    double azimuth, elevation; // Horizontal coordinates
    float *spectrum;          // Spectral data array
    int npoints;             // Number of spectral points
    char object[32];         // Object name
    char date_obs[32];       // Observation date/time
    // Additional metadata...
};
```

### Sidelobe Matrices
- **Near sidelobes**: Close-in pattern (< 9.2 arcmin for GBT)
- **Far sidelobes**: Extended pattern (> 9.2 arcmin)
- **Convolved patterns**: Pre-processed for efficiency
- **Version encoding**: Parameter-dependent matrix identification

## Processing Pipeline

### 1. Input Validation
- File format detection and validation
- Header consistency checking
- Coordinate system verification
- Data unit validation

### 2. Telescope Configuration
- Automatic telescope detection from headers
- Sidelobe matrix loading/computation
- Beam pattern initialization
- Ambient condition setup

### 3. Scan Processing
```
For each scan:
  1. Read scan metadata and spectrum
  2. Apply input calibrations
  3. Coordinate transformations
  4. Sidelobe computation/lookup
  5. Apply atmospheric corrections
  6. Generate output spectrum
  7. Update output file
```

### 4. Quality Control
- Scan validation and filtering
- Error detection and reporting  
- Statistical analysis
- Warning generation

## Memory Management

### Buffer Management
- **iobuffer**: I/O operation buffers
- **Shared memory**: Multi-process data sharing
- **Memory compression**: Efficient storage for large datasets
- **Chain management**: Linked data structures

### Performance Optimization
- **Buffered I/O**: Minimize disk operations
- **Memory mapping**: Efficient file access
- **Compression**: Reduce memory footprint
- **Caching**: Frequently accessed data

## Error Handling

### Error Categories
1. **Input/Output Errors**: File access, format issues
2. **Configuration Errors**: Invalid parameters, missing files  
3. **Computation Errors**: Numerical issues, convergence problems
4. **Memory Errors**: Allocation failures, buffer overruns
5. **System Errors**: Resource limits, permissions

### Error Recovery
- **Graceful degradation**: Continue processing when possible
- **Data validation**: Input sanitization and bounds checking
- **Resource cleanup**: Proper memory and file handle management
- **User feedback**: Clear error messages and suggestions

## Configuration Management

### Environment Variables
- **Telescope defaults**: Default sidelobe file locations
- **Path settings**: Search paths for data files
- **Processing parameters**: Default computation settings

### Parameter Encoding
- **Version numbers**: Encode processing parameters in identifiers
- **Checksum validation**: Verify data integrity
- **Compatibility checking**: Ensure parameter consistency

## Integration Interfaces

### CFITSIO Integration
- Standard FITS file operations
- Binary table access
- Header manipulation
- Multi-extension support

### GBTIDL Compatibility
- Atmospheric correction handling
- Data unit management  
- Coordinate system compatibility
- Error detection and correction

### Pipeline Integration
- **Batch processing**: Command-line automation
- **Error codes**: Standardized exit status
- **Logging**: Configurable output levels
- **File conventions**: Standard naming patterns

## Performance Characteristics

### Computational Complexity
- **Sidelobe computation**: O(N×M) where N=scans, M=matrix size
- **File I/O**: Linear with data volume
- **Memory usage**: Proportional to matrix size and scan count

### Scaling Factors
- **Matrix size**: Determines computation time
- **File size**: Affects I/O performance  
- **Scan count**: Linear processing time
- **Precision settings**: Trade-off between speed and accuracy

### Optimization Strategies
- **Pre-computed matrices**: Avoid real-time calculation
- **Efficient algorithms**: Optimized mathematical operations
- **Memory locality**: Cache-friendly data access patterns
- **Parallel processing**: Multi-threaded where applicable

## Debugging and Diagnostics

### Debug Information
- **Symbol table**: Available for debugging (not stripped)
- **Stack traces**: Detailed error location information
- **Memory debugging**: Allocation tracking capabilities

### Diagnostic Output
- **Verbose logging**: Detailed processing information
- **Statistics**: Processing metrics and performance data
- **Validation reports**: Data quality assessments
- **Warning systems**: Potential issue identification

This technical reference provides the foundation for understanding the sidelobe program's internal operation, enabling effective troubleshooting, optimization, and integration with other radio astronomy software systems.