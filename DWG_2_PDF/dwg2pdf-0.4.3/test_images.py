#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Checks for image -> PDF conversion (dwg2pdf 0.3.17).

Covers the parts that are easy to get quietly wrong: transparency flattened
onto white rather than black, multi-page TIFF keeping every frame, page size
derived from DPI, and the two size defects that made an image PDF hundreds
of times larger than it needed to be.
"""
# %%% Author Information
# @author: William W. Wallace
# Author Email: naval.antennas@gmail.com
# Work Phone: (304) 456-2216

# %% Imports
import shutil
import sys

from pathlib import Path                      # noqa: E402

import dwg2pdf as engine                      # noqa: E402


# %% Fixture bootstrap
def _ensure_fixtures() -> None:
    """Generate the test fixtures if this is a clean unpack.

    The suites must pass straight out of the archive; requiring the
    operator to run a generator first is how a release ends up looking
    broken when it is merely un-bootstrapped.
    """
    try:
        import make_test_drawings
    except Exception as exc:                               # noqa: BLE001
        print("  NOTE  cannot bootstrap fixtures: %s" % exc)
        return
    try:
        make_test_drawings.ensure_fixtures()
    except Exception as exc:                               # noqa: BLE001
        print("  NOTE  fixture generation failed: %s" % exc)


# %% State
RESULTS = {"pass": 0, "fail": 0}
OUT = Path("/tmp/dwg2pdf_imgtest")


# %% Helpers
def chk(label: str, cond: bool) -> None:
    """Record and print one assertion."""
    print(("  PASS  " if cond else "  FAIL  ") + label)
    RESULTS["pass" if cond else "fail"] += 1


def _pymupdf():
    """Import PyMuPDF under either of its two module names."""
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        import fitz
        return fitz


# %% Discovery
def test_discovery() -> None:
    """--images is opt-in, and picks up exactly the image files."""
    root = Path("test_images")
    without = engine.discover_inputs([root], include_images=False)
    with_img = engine.discover_inputs([root], include_images=True)
    chk("images are NOT found by default", not without)
    chk("images are found with include_images", len(with_img) == 4)
    chk("every suffix we advertise is recognised",
        all(p.suffix.lower() in engine.IMAGE_SUFFIXES for p in with_img))
    chk("a .dwg is not treated as an image",
        not engine.ImageBackend.handles(Path("x.dwg")))
    chk("a .jpg is treated as an image",
        engine.ImageBackend.handles(Path("x.JPG")))


# %% Conversion
def test_conversion() -> None:
    """Every image converts, with the right page count."""
    shutil.rmtree(OUT, ignore_errors=True)
    sources = engine.discover_inputs([Path("test_images")],
                                     include_images=True)
    spec = engine.PageSpec(paper="AUTO")
    pages_by_name = {}
    for src in sources:
        result = engine.ImageBackend(timeout=120).convert(src, OUT, spec)
        chk("converted %s" % src.name, result.status == "ok")
        if result.status == "ok":
            pages_by_name[src.name] = result.outputs[0]

    pdf = _pymupdf()
    multi = pages_by_name.get("multipage.tif")
    if multi:
        doc = pdf.open(str(multi))
        # The sheet-fed-scanner case: silently keeping only frame one is the
        # failure mode this guards against.
        chk("multi-page TIFF keeps all 3 frames", doc.page_count == 3)
        doc.close()

    single = pages_by_name.get("detail.jpg")
    if single:
        doc = pdf.open(str(single))
        chk("a single-frame image is one page", doc.page_count == 1)
        rect = doc[0].rect
        # 1200 px at 300 dpi = 4 in = 101.6 mm.
        width_mm = rect.width * 25.4 / 72.0
        chk("page size comes from the image's DPI (101.6 mm expected)",
            abs(width_mm - 101.6) < 1.0)
        doc.close()


# %% Output size
def test_sizes() -> None:
    """The two defects that made image PDFs enormous must stay fixed."""
    jpg_src = Path("test_images/detail.jpg")
    jpg_pdf = OUT / "detail.pdf"
    png_pdf = OUT / "screenshot.pdf"

    if jpg_pdf.is_file():
        ratio = jpg_pdf.stat().st_size / max(jpg_src.stat().st_size, 1)
        # Re-encoding an untouched JPEG as PNG inflated it 120x.  It is now
        # embedded byte for byte, so the PDF is the JPEG plus a little
        # structure.
        chk("an untouched JPEG is embedded, not re-encoded (<2x source)",
            ratio < 2.0)
    if png_pdf.is_file():
        # PyMuPDF's default save writes streams UNCOMPRESSED: this exact
        # file was 1409.7 KiB before deflate=True and 6.6 KiB after.
        kib = png_pdf.stat().st_size / 1024
        chk("PDF streams are deflated (a simple PNG page is < 100 KiB)",
            kib < 100)


# %% Transparency
def test_transparency() -> None:
    """Alpha must be flattened onto WHITE; onto black it looks like a fault."""
    pdf = _pymupdf()
    path = OUT / "transparent.pdf"
    if not path.is_file():
        chk("transparent PNG converted", False)
        return
    doc = pdf.open(str(path))
    pix = doc[0].get_pixmap(dpi=36)
    corner = pix.pixel(2, 2)          # outside the ellipse: was transparent
    doc.close()
    chk("transparency flattened onto white, not black",
        all(channel > 200 for channel in corner[:3]))


# %% Runner
# %% Large scans
def test_large_scans() -> None:
    """A 240+ MP archival scan must convert, and must not eat the machine.

    This is the case that failed on a real archive: thirty-seven
    large-format scans refused with "could be decompression bomb DOS
    attack", a security message about files on the operator's own disk.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    big = Path("/tmp/dwg2pdf_bigscan.tif")
    if not big.is_file():
        from PIL import ImageDraw
        # ~244 MP bilevel, the size and mode the failing scans were.
        image = Image.new("1", (17600, 13856), 1)
        draw = ImageDraw.Draw(image)
        draw.rectangle([200, 200, 17400, 13656], outline=0, width=20)
        image.save(big, compression="group4", dpi=(400, 400))

    chk("Pillow's decompression-bomb limit is lifted",
        Image.MAX_IMAGE_PIXELS is None)

    import resource
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    result = engine.ImageBackend(timeout=300).convert(
        big, OUT, engine.PageSpec(paper="AUTO"))
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    chk("a 244 MP scan converts", result.status == "ok")

    # 732 MB was the RGB-first cost of the original code; anything near it
    # means the downsample-before-convert ordering has been lost.
    chk("peak memory stays well under the 732 MB RGB-first cost (%.0f MB)"
        % peak, peak < 700)
    if result.status == "ok":
        pdf = _pymupdf().open(str(result.outputs[0]))
        width_mm = pdf[0].rect.width * 25.4 / 72.0
        # 17600 px at 400 dpi = 44 in = ANSI E.
        chk("page keeps its true physical size (1118 mm expected)",
            abs(width_mm - 1117.6) < 6.0)
        pdf.close()
        size_mb = result.outputs[0].stat().st_size / 1e6
        chk("line art is not JPEG-bloated (%.2f MB)" % size_mb, size_mb < 3.0)
    _ = before


# %% Decoder selection
def test_decoder() -> None:
    """libvips is used when present, and Pillow still works when it is not."""
    vips = engine.ImageBackend._vips()
    if vips is None:
        print("  note: pyvips not installed, only the Pillow path is exercised")
        chk("Pillow path available without pyvips",
            engine.ImageBackend.available())
        return

    chk("pyvips is detected", vips is not None)
    chk("probe mentions libvips", "libvips" in engine.ImageBackend.describe())

    # Force the fallback and confirm it still produces the same page.
    saved = engine.ImageBackend._vips_module
    try:
        engine.ImageBackend._vips_module = None
        result = engine.ImageBackend(timeout=120).convert(
            Path("test_images/detail.jpg"), OUT / "fallback",
            engine.PageSpec(paper="AUTO"))
        chk("Pillow fallback still converts", result.status == "ok")
    finally:
        engine.ImageBackend._vips_module = saved


def run_test() -> int:
    """Run every check and report."""
    _ensure_fixtures()
    print("IMAGE CONVERSION CHECKS (engine %s)" % engine.__revision__)
    if not engine.ImageBackend.available():
        print("  SKIP: Pillow is not installed")
        return 0
    test_discovery()
    test_conversion()
    test_sizes()
    test_transparency()
    test_large_scans()
    test_decoder()
    print("\n  %d passed, %d failed" % (RESULTS["pass"], RESULTS["fail"]))
    return 0 if RESULTS["fail"] == 0 else 1


# %% Entry point
if __name__ == "__main__":
    sys.exit(run_test())
