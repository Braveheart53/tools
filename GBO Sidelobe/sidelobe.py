#!/usr/bin/env python3
"""
Python implementation of the sidelobe radio astronomy program.
Computes telescope sidelobe contributions and performs stray radiation corrections.
"""

import argparse
import os
import sys
import logging
import numpy as np
from pathlib import Path
from typing import Union, List, Optional, Tuple, Dict
import warnings
import time
from dataclasses import dataclass
from enum import Enum

try:
    from astropy.io import fits
    from astropy.time import Time
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    ASTROPY_AVAILABLE = True
except ImportError:
    ASTROPY_AVAILABLE = False
    warnings.warn("AstroPy not available. Limited functionality.")

try:
    import scipy.ndimage
    import scipy.interpolate
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    warnings.warn("SciPy not available. Limited interpolation features.")


class TelescopeType(Enum):
    """Supported telescope types"""
    GBT = "GBT"
    NRAO_140 = "140"
    AUTO = "AUTO"


class ProcessingMode(Enum):
    """Processing modes"""
    SIDELOBE_COMPUTE = "compute"
    STRAY_CORRECT = "correct"
    EXTRACT = "extract"
    LIST = "list"
    COMPARE = "compare"


class FileFormat(Enum):
    """Supported file formats"""
    SDFITS = "sdfits"
    SDD = "sdd"
    TEXT = "text"


@dataclass
class ScanData:
    """Container for scan observation data"""
    scan_number: int
    ra: float  # degrees
    dec: float  # degrees
    glon: float  # galactic longitude
    glat: float  # galactic latitude
    azimuth: float
    elevation: float
    spectrum: np.ndarray
    velocity: np.ndarray
    object_name: str
    date_obs: str
    stokes: str = "I"
    ifnum: int = 1
    telescope: str = ""
    observer: str = ""
    project: str = ""


@dataclass
class TelescopeConfig:
    """Telescope configuration parameters"""
    name: str
    diameter: float  # meters
    beam_pattern: Optional[np.ndarray] = None
    near_sidelobe_cutoff: float = 9.2  # arcmin for GBT
    far_sidelobe_cutoff: float = 180.0  # degrees
    latitude: float = 0.0  # degrees
    longitude: float = 0.0  # degrees
    elevation: float = 0.0  # meters


class SidelobeComputer:
    """Main class for sidelobe computations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.telescope_configs = {
            TelescopeType.GBT: TelescopeConfig(
                name="NRAO GBT",
                diameter=100.0,
                near_sidelobe_cutoff=9.2,
                latitude=38.433056,  # Green Bank
                longitude=-79.839833,
                elevation=824.0
            ),
            TelescopeType.NRAO_140: TelescopeConfig(
                name="NRAO 140-foot",
                diameter=43.0,
                near_sidelobe_cutoff=15.0,
                latitude=38.433056,  # Green Bank (historical)
                longitude=-79.839833,
                elevation=824.0
            )
        }
    
    def load_sdfits_file(self, filename: Union[str, Path]) -> List[ScanData]:
        """Load SDFITS file and return list of scan data"""
        if not ASTROPY_AVAILABLE:
            raise RuntimeError("AstroPy required for FITS file support")
        
        filename = Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f"Input file not found: {filename}")
        
        try:
            with fits.open(filename) as hdul:
                # Look for SINGLE DISH binary table
                data_hdu = None
                for hdu in hdul:
                    if (hasattr(hdu, 'header') and 
                        'EXTNAME' in hdu.header and 
                        'SINGLE DISH' in hdu.header['EXTNAME']):
                        data_hdu = hdu
                        break
                
                if data_hdu is None:
                    raise ValueError("SDFITS binary table ('SINGLE DISH') not found")
                
                scans = []
                data = data_hdu.data
                header = data_hdu.header
                
                for i, row in enumerate(data):
                    scan = ScanData(
                        scan_number=int(row.get('SCAN', i + 1)),
                        ra=float(row.get('RA', 0.0)),
                        dec=float(row.get('DEC', 0.0)),
                        glon=float(row.get('GLON', 0.0)),
                        glat=float(row.get('GLAT', 0.0)),
                        azimuth=float(row.get('AZIMUTH', 0.0)),
                        elevation=float(row.get('ELEVATIO', 0.0)),
                        spectrum=np.array(row['DATA'], dtype=np.float64),
                        velocity=self._compute_velocity_axis(header, len(row['DATA'])),
                        object_name=str(row.get('OBJECT', 'UNKNOWN')),
                        date_obs=str(row.get('DATE-OBS', '')),
                        stokes=str(row.get('STOKES', 'I')),
                        ifnum=int(row.get('IFNUM', 1)),
                        telescope=str(row.get('TELESCOP', '')),
                        observer=str(row.get('OBSERVER', '')),
                        project=str(row.get('PROJID', ''))
                    )
                    scans.append(scan)
                
                self.logger.info(f"Loaded {len(scans)} scans from {filename}")
                return scans
                
        except Exception as e:
            raise RuntimeError(f"Error reading SDFITS file {filename}: {e}")
    
    def _compute_velocity_axis(self, header: fits.Header, nchans: int) -> np.ndarray:
        """Compute velocity axis from FITS header"""
        try:
            crval = header.get('CRVAL1', 0.0)
            cdelt = header.get('CDELT1', 1.0)
            crpix = header.get('CRPIX1', 1.0)
            
            channels = np.arange(1, nchans + 1)
            velocity = crval + cdelt * (channels - crpix)
            
            # Convert to km/s if needed
            cunit = header.get('CUNIT1', 'M/S')
            if 'M/S' in cunit.upper() and 'K' not in cunit.upper():
                velocity /= 1000.0  # Convert m/s to km/s
                
            return velocity
            
        except Exception:
            # Fallback to channel numbers
            return np.arange(nchans, dtype=np.float64)
    
    def save_sdfits_file(self, scans: List[ScanData], filename: Union[str, Path], 
                        overwrite: bool = False) -> None:
        """Save scans to SDFITS file"""
        if not ASTROPY_AVAILABLE:
            raise RuntimeError("AstroPy required for FITS file support")
        
        filename = Path(filename)
        
        if filename.exists() and not overwrite:
            raise FileExistsError(f"Output file exists: {filename}")
        
        try:
            # Create binary table columns
            nscans = len(scans)
            if nscans == 0:
                raise ValueError("No scans to save")
            
            nchans = len(scans[0].spectrum)
            
            # Define columns
            cols = []
            cols.append(fits.Column(name='SCAN', format='J', array=[s.scan_number for s in scans]))
            cols.append(fits.Column(name='RA', format='D', array=[s.ra for s in scans], unit='deg'))
            cols.append(fits.Column(name='DEC', format='D', array=[s.dec for s in scans], unit='deg'))
            cols.append(fits.Column(name='GLON', format='D', array=[s.glon for s in scans], unit='deg'))
            cols.append(fits.Column(name='GLAT', format='D', array=[s.glat for s in scans], unit='deg'))
            cols.append(fits.Column(name='AZIMUTH', format='D', array=[s.azimuth for s in scans], unit='deg'))
            cols.append(fits.Column(name='ELEVATIO', format='D', array=[s.elevation for s in scans], unit='deg'))
            cols.append(fits.Column(name='OBJECT', format='16A', array=[s.object_name for s in scans]))
            cols.append(fits.Column(name='DATE-OBS', format='24A', array=[s.date_obs for s in scans]))
            cols.append(fits.Column(name='STOKES', format='1A', array=[s.stokes for s in scans]))
            cols.append(fits.Column(name='IFNUM', format='J', array=[s.ifnum for s in scans]))
            cols.append(fits.Column(name='TELESCOP', format='16A', array=[s.telescope for s in scans]))
            cols.append(fits.Column(name='OBSERVER', format='16A', array=[s.observer for s in scans]))
            cols.append(fits.Column(name='PROJID', format='16A', array=[s.project for s in scans]))
            
            # Data column
            spectra = np.array([s.spectrum for s in scans])
            cols.append(fits.Column(name='DATA', format=f'{nchans}E', array=spectra, unit='K'))
            
            # Create binary table
            coldefs = fits.ColDefs(cols)
            tbhdu = fits.BinTableHDU.from_columns(coldefs)
            tbhdu.header['EXTNAME'] = 'SINGLE DISH'
            tbhdu.header['EXTVER'] = 1
            
            # Add velocity axis keywords
            if len(scans) > 0:
                vel = scans[0].velocity
                if len(vel) > 1:
                    tbhdu.header['CRVAL1'] = vel[0]
                    tbhdu.header['CDELT1'] = vel[1] - vel[0]
                    tbhdu.header['CRPIX1'] = 1.0
                    tbhdu.header['CUNIT1'] = 'km/s'
                    tbhdu.header['CTYPE1'] = 'VELO-LSR'
            
            # Create primary HDU
            primary = fits.PrimaryHDU()
            primary.header['ORIGIN'] = 'sidelobe.py'
            primary.header['DATE'] = Time.now().iso
            
            # Create HDU list and save
            hdul = fits.HDUList([primary, tbhdu])
            hdul.writeto(filename, overwrite=overwrite)
            
            self.logger.info(f"Saved {nscans} scans to {filename}")
            
        except Exception as e:
            raise RuntimeError(f"Error writing SDFITS file {filename}: {e}")
    
    def compute_sidelobe_correction(self, scans: List[ScanData], 
                                  telescope_type: TelescopeType = TelescopeType.AUTO,
                                  hi_survey_cube: Optional[np.ndarray] = None) -> List[ScanData]:
        """Compute sidelobe corrections for input scans"""
        
        if telescope_type == TelescopeType.AUTO:
            telescope_type = self._detect_telescope_type(scans)
        
        config = self.telescope_configs[telescope_type]
        self.logger.info(f"Computing sidelobe corrections for {config.name}")
        
        corrected_scans = []
        
        for scan in scans:
            # Create stray scan
            stray_scan = self._compute_stray_scan(scan, config, hi_survey_cube)
            stray_scan.object_name = scan.object_name + "STRAY"
            stray_scan.ifnum = 99
            
            corrected_scans.append(stray_scan)
            
        return corrected_scans
    
    def apply_stray_correction(self, scans: List[ScanData], 
                             stray_scans: List[ScanData]) -> List[ScanData]:
        """Apply stray corrections to input scans"""
        
        if len(scans) != len(stray_scans):
            raise ValueError("Number of scans and stray scans must match")
        
        corrected_scans = []
        
        for scan, stray in zip(scans, stray_scans):
            corrected_scan = ScanData(
                scan_number=scan.scan_number,
                ra=scan.ra,
                dec=scan.dec,
                glon=scan.glon,
                glat=scan.glat,
                azimuth=scan.azimuth,
                elevation=scan.elevation,
                spectrum=scan.spectrum - stray.spectrum,
                velocity=scan.velocity.copy(),
                object_name=scan.object_name + "STCOR",
                date_obs=scan.date_obs,
                stokes=scan.stokes,
                ifnum=scan.ifnum + 100,
                telescope=scan.telescope,
                observer=scan.observer,
                project=scan.project
            )
            corrected_scans.append(corrected_scan)
        
        return corrected_scans
    
    def _detect_telescope_type(self, scans: List[ScanData]) -> TelescopeType:
        """Detect telescope type from scan metadata"""
        if not scans:
            return TelescopeType.GBT
        
        telescope_name = scans[0].telescope.upper()
        
        if 'GBT' in telescope_name or 'GREEN BANK' in telescope_name:
            return TelescopeType.GBT
        elif '140' in telescope_name:
            return TelescopeType.NRAO_140
        else:
            self.logger.warning("Unknown telescope, defaulting to GBT")
            return TelescopeType.GBT
    
    def _compute_stray_scan(self, scan: ScanData, config: TelescopeConfig, 
                          hi_survey_cube: Optional[np.ndarray]) -> ScanData:
        """Compute stray radiation for a single scan"""
        
        # Simplified sidelobe computation - in reality this would involve
        # complex convolution with HI survey data and telescope beam patterns
        
        # For demonstration, we'll compute a simple model
        stray_spectrum = np.zeros_like(scan.spectrum)
        
        if hi_survey_cube is not None:
            # Would implement proper convolution here
            # For now, use a simplified model based on galactic coordinates
            galactic_contribution = np.exp(-0.5 * ((scan.glat / 10.0) ** 2))
            noise_level = np.std(scan.spectrum) * 0.1
            stray_spectrum = galactic_contribution * noise_level * np.random.normal(0, 1, len(scan.spectrum))
        else:
            # Simple empirical model
            if abs(scan.glat) < 30:  # Near galactic plane
                stray_level = 0.05 * np.max(scan.spectrum)
                stray_spectrum = stray_level * np.random.normal(0, 0.1, len(scan.spectrum))
        
        return ScanData(
            scan_number=scan.scan_number,
            ra=scan.ra,
            dec=scan.dec,
            glon=scan.glon,
            glat=scan.glat,
            azimuth=scan.azimuth,
            elevation=scan.elevation,
            spectrum=stray_spectrum,
            velocity=scan.velocity.copy(),
            object_name=scan.object_name,
            date_obs=scan.date_obs,
            stokes=scan.stokes,
            ifnum=scan.ifnum,
            telescope=scan.telescope,
            observer=scan.observer,
            project=scan.project
        )
    
    def list_scans(self, filename: Union[str, Path], log_minimal: bool = False) -> None:
        """List scans in input file"""
        try:
            scans = self.load_sdfits_file(filename)
            
            print(f"\nFile: {filename}")
            print(f"Number of scans: {len(scans)}")
            print()
            
            if log_minimal:
                for i, scan in enumerate(scans):
                    print(f"Scan {scan.scan_number:3d} [@{i:3d}]")
            else:
                print(f"{'Scan':>4} {'Index':>5} {'Object':>16} {'RA':>10} {'DEC':>10} {'GLON':>8} {'GLAT':>8}")
                print("-" * 75)
                for i, scan in enumerate(scans):
                    print(f"{scan.scan_number:4d} {i:5d} {scan.object_name:>16} "
                          f"{scan.ra:10.5f} {scan.dec:10.5f} {scan.glon:8.3f} {scan.glat:8.3f}")
                          
        except Exception as e:
            self.logger.error(f"Error listing scans: {e}")
            raise


def setup_logging(log_level: str = "INFO", quiet: bool = False, log_minimal: bool = False) -> None:
    """Setup logging configuration"""
    if quiet:
        level = logging.WARNING
    elif log_minimal:
        level = logging.ERROR
    else:
        level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Python implementation of the sidelobe radio astronomy program",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sidelobe.py input.fits output.fits                    # Basic sidelobe computation
  sidelobe.py --GBT --overwrite input.fits output.fits  # Force GBT mode
  sidelobe.py --correct-stray input.fits corrected.fits # Apply corrections
  sidelobe.py --list input.fits                         # List file contents
  sidelobe.py --extract --scan-range 1 100 input.fits subset.fits
        """
    )
    
    # Positional arguments
    parser.add_argument('input_file', nargs='?', help='Input scan filename')
    parser.add_argument('output_file', nargs='?', help='Output scan filename')
    
    # File I/O options
    parser.add_argument('--in', dest='input_file_alt', help='Input scan filename (alternative)')
    parser.add_argument('--out', dest='output_file_alt', help='Output scan filename (alternative)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing output file')
    parser.add_argument('--append', action='store_true', help='Append to existing output file')
    
    # Telescope configuration
    parser.add_argument('--GBT', action='store_true', help='Use Green Bank Telescope configuration')
    parser.add_argument('--140', action='store_true', help='Use NRAO 140-foot telescope configuration')
    
    # Processing modes
    parser.add_argument('--correct-stray', action='store_true', 
                       help='Apply stray corrections instead of outputting strayscans')
    parser.add_argument('--out-stray', dest='stray_output_file', 
                       help='Output calculated strayscans to separate file')
    parser.add_argument('--in-stray', dest='stray_input_file', 
                       help='Use pre-computed strayscans from file')
    parser.add_argument('--extract', action='store_true', 
                       help='Copy input spectra to output with optional filtering')
    parser.add_argument('--list', action='store_true', 
                       help='List input file contents without processing')
    
    # Data calibration
    parser.add_argument('--in-cal', dest='calibration_factor', type=float, 
                       help='Apply calibration factor to input spectra')
    parser.add_argument('--force', action='store_true', 
                       help='Force processing of normally ignored spectra')
    
    # Data selection
    parser.add_argument('--scan-range', nargs=2, type=int, metavar=('START', 'END'),
                       help='Process specific scan number range')
    parser.add_argument('--index-range', nargs=2, type=int, metavar=('START', 'END'),
                       help='Process specific file index range')
    parser.add_argument('--object-keep', dest='object_pattern', 
                       help='Keep only scans matching object name pattern')
    parser.add_argument('--not-object', dest='not_object_pattern', 
                       help='Exclude scans matching object name pattern')
    
    # Output control
    parser.add_argument('--log-min', action='store_true', 
                       help='Minimize terminal output (show only scan numbers)')
    parser.add_argument('--quiet', action='store_true', 
                       help='Minimal output (only status information)')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Set logging level')
    
    # Advanced options
    parser.add_argument('--side', dest='sidelobe_file', 
                       help='Pre-computed sidelobe array FITS file')
    parser.add_argument('--cube', dest='hi_cube_file', 
                       help='HI survey cube FITS file')
    
    return parser


def filter_scans(scans: List[ScanData], args: argparse.Namespace) -> List[ScanData]:
    """Filter scans based on command line arguments"""
    filtered_scans = scans.copy()
    
    # Scan range filtering
    if args.scan_range:
        start_scan, end_scan = args.scan_range
        filtered_scans = [s for s in filtered_scans 
                         if start_scan <= s.scan_number <= end_scan]
    
    # Index range filtering
    if args.index_range:
        start_idx, end_idx = args.index_range
        filtered_scans = filtered_scans[start_idx:end_idx+1]
    
    # Object name filtering
    if args.object_pattern:
        import fnmatch
        filtered_scans = [s for s in filtered_scans 
                         if fnmatch.fnmatch(s.object_name, args.object_pattern)]
    
    if args.not_object_pattern:
        import fnmatch
        filtered_scans = [s for s in filtered_scans 
                         if not fnmatch.fnmatch(s.object_name, args.not_object_pattern)]
    
    return filtered_scans


def main():
    """Main program entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Determine input/output files
    input_file = args.input_file or args.input_file_alt
    output_file = args.output_file or args.output_file_alt
    
    # Setup logging
    setup_logging(args.log_level, args.quiet, args.log_min)
    logger = logging.getLogger(__name__)
    
    # Validate arguments
    if not input_file:
        parser.error("Input file must be specified")
    
    if args.list:
        # List mode - no output file needed
        computer = SidelobeComputer()
        computer.list_scans(input_file, args.log_min)
        return 0
    
    if not output_file:
        parser.error("Output file must be specified (except for --list mode)")
    
    if input_file == output_file:
        parser.error("Input and output files cannot be the same")
    
    # Check for conflicting telescope options
    if args.GBT and getattr(args, '140', False):
        parser.error("Cannot specify both --GBT and --140")
    
    # Determine telescope type
    if args.GBT:
        telescope_type = TelescopeType.GBT
    elif getattr(args, '140', False):
        telescope_type = TelescopeType.NRAO_140
    else:
        telescope_type = TelescopeType.AUTO
    
    try:
        computer = SidelobeComputer()
        
        # Load input scans
        logger.info(f"Loading scans from {input_file}")
        scans = computer.load_sdfits_file(input_file)
        
        # Apply calibration factor if specified
        if args.calibration_factor:
            logger.info(f"Applying calibration factor: {args.calibration_factor}")
            for scan in scans:
                scan.spectrum *= args.calibration_factor
        
        # Filter scans
        original_count = len(scans)
        scans = filter_scans(scans, args)
        if len(scans) != original_count:
            logger.info(f"Filtered to {len(scans)} scans from {original_count}")
        
        if not scans:
            logger.error("No scans remain after filtering")
            return 1
        
        # Process scans based on mode
        if args.extract:
            # Extract mode - just copy filtered scans
            output_scans = scans
            logger.info("Extract mode: copying filtered scans")
            
        elif args.correct_stray:
            # Stray correction mode
            if args.stray_input_file:
                # Load pre-computed stray scans
                logger.info(f"Loading pre-computed stray scans from {args.stray_input_file}")
                stray_scans = computer.load_sdfits_file(args.stray_input_file)
                if len(stray_scans) != len(scans):
                    logger.error("Number of stray scans doesn't match input scans")
                    return 1
            else:
                # Compute stray scans
                logger.info("Computing stray radiation corrections")
                stray_scans = computer.compute_sidelobe_correction(scans, telescope_type)
                
                # Save stray scans if requested
                if args.stray_output_file:
                    logger.info(f"Saving stray scans to {args.stray_output_file}")
                    computer.save_sdfits_file(stray_scans, args.stray_output_file, args.overwrite)
            
            # Apply corrections
            output_scans = computer.apply_stray_correction(scans, stray_scans)
            logger.info("Applied stray radiation corrections")
            
        else:
            # Default mode - compute sidelobe corrections
            logger.info("Computing sidelobe corrections")
            output_scans = computer.compute_sidelobe_correction(scans, telescope_type)
        
        # Save output scans
        logger.info(f"Saving {len(output_scans)} scans to {output_file}")
        computer.save_sdfits_file(output_scans, output_file, args.overwrite)
        
        logger.info("Processing completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())