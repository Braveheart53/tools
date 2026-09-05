#!/usr/bin/env python3
"""Generate a small synthetic 2D drawing set for exercising dwg2pdf.py.

Creates three DXF files in a nested tree, one of which carries a real
paperspace layout, so the ``--layouts`` paths get exercised too.
"""
from pathlib import Path
import ezdxf

ROOT = Path("test_drawings")


def title_block(msp, width, height, title):
    """Draw a simple border and title block in modelspace."""
    msp.add_lwpolyline(
        [(0, 0), (width, 0), (width, height), (0, height)],
        close=True, dxfattribs={"layer": "BORDER", "lineweight": 50},
    )
    msp.add_lwpolyline(
        [(width - 120, 0), (width, 0), (width, 40), (width - 120, 40)],
        close=True, dxfattribs={"layer": "BORDER", "lineweight": 35},
    )
    msp.add_text(title, height=6, dxfattribs={"layer": "TEXT"}).set_placement(
        (width - 114, 22)
    )
    msp.add_text("dwg2pdf self-test", height=4, dxfattribs={"layer": "TEXT"}).set_placement(
        (width - 114, 10)
    )


def sheet(path: Path, title: str, with_paperspace: bool = False):
    doc = ezdxf.new("R2018", setup=True)
    doc.layers.add("BORDER", color=7)
    doc.layers.add("TEXT", color=3)
    doc.layers.add("GEOM", color=1)
    doc.layers.add("HIDDEN", color=5, linetype="DASHED")
    msp = doc.modelspace()
    title_block(msp, 420, 297, title)

    # Some geometry with a mix of entity types and linetypes.
    msp.add_circle((120, 150), 60, dxfattribs={"layer": "GEOM", "lineweight": 35})
    msp.add_circle((120, 150), 40, dxfattribs={"layer": "HIDDEN"})
    msp.add_line((40, 150), (200, 150), dxfattribs={"layer": "HIDDEN"})
    msp.add_line((120, 70), (120, 230), dxfattribs={"layer": "HIDDEN"})
    msp.add_arc((260, 150), 50, 30, 150, dxfattribs={"layer": "GEOM"})
    msp.add_lwpolyline(
        [(230, 60), (330, 60), (330, 110), (280, 130), (230, 110)],
        close=True, dxfattribs={"layer": "GEOM", "lineweight": 50},
    )
    hatch = msp.add_hatch(color=8, dxfattribs={"layer": "GEOM"})
    hatch.paths.add_polyline_path(
        [(230, 60), (330, 60), (330, 110), (280, 130), (230, 110)], is_closed=True
    )
    hatch.set_pattern_fill("ANSI31", scale=2.0)
    msp.add_linear_dim(base=(40, 40), p1=(40, 70), p2=(200, 70),
                       dxfattribs={"layer": "TEXT"}).render()

    if with_paperspace:
        psp = doc.layouts.new("D-SIZE")
        psp.page_setup(size=(420, 297), margins=(10, 10, 10, 10), units="mm")
        psp.add_viewport(center=(210, 148), size=(380, 250),
                         view_center_point=(180, 150), view_height=280)
        psp.add_text("PAPERSPACE LAYOUT", height=8).set_placement((20, 20))

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    print("wrote", path)


if __name__ == "__main__":
    sheet(ROOT / "DEMO-001-plate.dxf", "DEMO-001 BASE PLATE")
    sheet(ROOT / "sub" / "DEMO-002-bracket.dxf", "DEMO-002 BRACKET")
    sheet(ROOT / "sub" / "DEMO-003-armature.dxf", "DEMO-003 ARMATURE", with_paperspace=True)
