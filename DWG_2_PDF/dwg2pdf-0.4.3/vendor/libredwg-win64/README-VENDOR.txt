LibreDWG 0.14.8593 -- Windows x86-64 binaries
=============================================

What this is
------------
GNU LibreDWG's DWG decoder, built for 64-bit Windows.  dwg2pdf uses
dwg2dxf.exe to turn a .dwg into a .dxf, which ezdxf then renders to PDF.
This is the route that needs NO Autodesk software at all.

Files
-----
  dwg2dxf.exe     DWG -> DXF converter (the one dwg2pdf calls)
  dwgread.exe     DWG -> JSON/DXF dumper (diagnostics)
  dwglayers.exe   list layers in a DWG (diagnostics)
  libredwg.dll    the decoder library -- REQUIRED, keep beside the .exe
  libssp-0.dll    MinGW stack-protector runtime -- REQUIRED
  COPYING-LibreDWG-GPL3.txt   the GNU GPL v3, LibreDWG's licence

Install
-------
Nothing to install.  Keep this folder next to dwg2pdf.py and it is found
automatically.  To use it from anywhere, add this folder to PATH.

Provenance and verification
---------------------------
Built from the official source (github.com/LibreDWG/libredwg, the GNU
project's own mirror) at commit 8a1ae76, version 0.14.8593, cross-compiled
with MinGW-w64 GCC 13 and verified by:

  * PE inspection      -- PE32+ console executable, x86-64
  * execution          -- `dwg2dxf.exe --version` runs and self-reports
  * a real conversion  -- an R2013 DWG decoded to DXF with all 67
                          modelspace entities intact

Licence
-------
LibreDWG is free software under the GNU GPL v3 (see the COPYING file).
There is NO restriction on commercial use.  This matters: the ODA File
Converter, the usual alternative, may be used by non-members for
non-commercial purposes only.

Do not pass --as= to dwg2dxf
----------------------------
Requesting an output DXF version silently produces a file with an EMPTY
entities section whenever the requested version does not match the
source's era -- exit code 0, correct file size, no geometry.  dwg2pdf
never passes it.  See README.md section 8.3 for the measured matrix.
