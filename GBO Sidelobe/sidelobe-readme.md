# Sidelobe Program

## Overview

The **sidelobe** program is a specialized tool for radio astronomy data processing that computes telescope sidelobe contributions and performs stray radiation corrections. It is designed to work with data from NRAO radio telescopes, particularly the Green Bank Telescope (GBT) and the NRAO 140-foot telescope.

## Purpose

The program creates sidelobe correction ("strayscan") files by convolving the telescope's sidelobe pattern with an all-sky HI (neutral hydrogen) survey. This process helps correct for unwanted signals that enter the telescope through its sidelobes rather than the main beam.

## Key Features

- **Multi-telescope support**: Works with GBT and NRAO 140-foot telescope data
- **Multiple file formats**: Supports both SDD-file and SDFITS file formats
- **Stray radiation correction**: Can subtract computed strayscans from input data
- **Atmospheric correction handling**: Manages GBTIDL atmospheric correction inconsistencies
- **Flexible processing**: Offers various processing modes and output options

## System Requirements

- **Platform**: Linux x86-64 system
- **File type**: ELF 64-bit LSB executable
- **Dependencies**: Dynamically linked (requires standard Linux libraries)
- **Compatibility**: GNU/Linux 2.6.9 or later

## File Format Support

### Input Formats
- **SDFITS files**: FITS binary tables for single dish observations
- **SDD files**: Binary scan data files
- **Text files**: Sun-scan text files (special case)

### Output Formats
- **Corrected spectra**: Input spectra with sidelobe corrections applied
- **Strayscan files**: Computed sidelobe contribution data
- **GLS cubes**: Gridded latitude-longitude survey data
- **Plot files**: Visualization output for analysis

## Basic Operation Modes

1. **Sidelobe Computation**: Generate sidelobe correction files
2. **Stray Correction**: Apply corrections directly to input spectra
3. **Data Extraction**: Copy and filter input spectra
4. **File Analysis**: List and examine input file contents
5. **Comparison**: Compare scans between different files

## Telescope Configuration

The program automatically detects telescope type from input files but can be explicitly specified:

- **GBT**: Green Bank Telescope configuration
- **140-foot**: NRAO 140-foot (43m) telescope configuration

## Data Processing Features

- **Calibration factors**: Apply multiplicative corrections to input data
- **Velocity range extraction**: Process specific velocity ranges
- **Atmospheric corrections**: Handle and fix atmospheric correction issues
- **Coordinate fixes**: Correct problematic RA and galactic longitude values
- **Quality filtering**: Skip or process scans based on various criteria

## Output Identification

- **Strayscan outputs**: OBJECT names appended with "STRAY", IFNUM set to 99
- **Corrected spectra**: OBJECT names appended with "STCOR", IFNUM incremented by 100

## Use Cases

1. **Research Data Processing**: Prepare radio astronomy data for scientific analysis
2. **Calibration Workflows**: Apply sidelobe corrections as part of data reduction pipelines
3. **Quality Assessment**: Analyze and validate telescope performance
4. **Archive Processing**: Batch process historical observation data

## Integration

The sidelobe program is typically used as part of larger radio astronomy data processing pipelines, often integrated with:

- GBTIDL (Green Bank Telescope Interactive Data Language)
- FITS file processing systems
- Radio astronomy analysis software suites
- Observational data archives

## Data Quality

The program includes extensive error checking and warning systems to ensure data integrity and identify potential issues with:

- File format consistency
- Coordinate system problems
- Atmospheric correction parameters
- Telescope configuration mismatches
- Data unit specifications

This tool is essential for producing publication-quality radio astronomy data by removing the effects of telescope sidelobes that could otherwise contaminate scientific measurements.