#!/usr/bin/env python3
"""Generate KiCad serpentine strain-gauge copper for FPC projects."""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from pathlib import Path

RHO = 1.68e-8  # ohm*m
TRACE_W = 0.1  # mm
COPPER_T = 0.035  # mm (1 oz)
PITCH = 0.2  # mm centerline spacing (0.1 mm trace + 0.1 mm gap)
# U-turn radius > pitch/2 so inner trace width stays near 0.1 mm (not pinched).
R_TURN = PITCH * 0.75


def uid() -> str:
    return str(uuid.uuid4())


def target_length_mm(r_ohm: float) -> float:
    w_m = TRACE_W * 1e-3
    t_m = COPPER_T * 1e-3
    return r_ohm * w_m * t_m / RHO * 1e3  # mm


def estimate_resistance_ohm(length_mm: float) -> float:
    w_m = TRACE_W * 1e-3
    t_m = COPPER_T * 1e-3
    l_m = length_mm * 1e-3
    return RHO * l_m / (w_m * t_m)


@dataclass
class SerpentineResult:
    segments: list[tuple[tuple[float, float], tuple[float, float]]]
    arcs: list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]]
    length_mm: float
    n_legs: int
    active_w_mm: float
    active_h_mm: float
    origin_x: float
    origin_y: float


def generate_serpentine(
    x0: float,
    y0: float,
    n_legs: int,
    leg_height: float,
) -> SerpentineResult:
    """Vertical legs with semicircular U-turns; legs alternate direction."""
    y_bot = y0
    y_top = y0 + leg_height
    active_w = (n_legs - 1) * PITCH
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    arcs: list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]] = []
    length = 0.0

    for i in range(n_legs):
        x = x0 + i * PITCH
        if i % 2 == 0:
            ya, yb = y_bot, y_top
        else:
            ya, yb = y_top, y_bot
        length += abs(yb - ya)
        segments.append(((x, ya), (x, yb)))

        if i < n_legs - 1:
            x_next = x + PITCH
            if i % 2 == 0:
                start = (x, y_top)
                end = (x_next, y_top)
                mid = (x + PITCH / 2, y_top + R_TURN)
            else:
                start = (x, y_bot)
                end = (x_next, y_bot)
                mid = (x + PITCH / 2, y_bot - R_TURN)
            length += math.pi * R_TURN
            arcs.append((start, mid, end))

    return SerpentineResult(
        segments=segments,
        arcs=arcs,
        length_mm=length,
        n_legs=n_legs,
        active_w_mm=active_w,
        active_h_mm=leg_height,
        origin_x=x0,
        origin_y=y0,
    )


def size_for_target_length(target_mm: float) -> tuple[int, float]:
    """Choose leg count and height for ~target copper length (square-ish active area)."""
    # L = n*H + (n-1)*pi*r_turn, width = (n-1)*pitch
    n = max(4, int(round(math.sqrt(target_mm / PITCH))))
    best: tuple[int, float] | None = None
    best_err = float("inf")
    for n_try in range(max(4, n - 50), n + 200):
        h = (target_mm - (n_try - 1) * math.pi * R_TURN) / n_try
        if h < PITCH * 2:
            continue
        w = (n_try - 1) * PITCH
        err = abs(w - h)
        if err < best_err:
            best_err = err
            best = (n_try, h)
    if best is None:
        raise RuntimeError("Could not size serpentine")
    return best


NET_NAME = "GAUGE"
NET_CODE = 1


def fmt_net() -> str:
    return f'\t(net {NET_CODE} "{NET_NAME}")'


def fmt_seg(p1, p2) -> str:
    return f"""\t(segment
\t\t(start {p1[0]:.4f} {p1[1]:.4f})
\t\t(end {p2[0]:.4f} {p2[1]:.4f})
\t\t(width {TRACE_W:.4f})
\t\t(layer "F.Cu")
\t\t(net {NET_CODE})
\t\t(uuid "{uid()}")
\t)"""


def fmt_arc(start, mid, end) -> str:
    return f"""\t(arc
\t\t(start {start[0]:.4f} {start[1]:.4f})
\t\t(mid {mid[0]:.4f} {mid[1]:.4f})
\t\t(end {end[0]:.4f} {end[1]:.4f})
\t\t(width {TRACE_W:.4f})
\t\t(layer "F.Cu")
\t\t(net {NET_CODE})
\t\t(uuid "{uid()}")
\t)"""


def fmt_pad_footprint(ref: str, name: str, x: float, y: float, net: int = NET_CODE) -> str:
    return f"""\t(footprint "TerminalPad"
\t\t(layer "F.Cu")
\t\t(uuid "{uid()}")
\t\t(at {x:.4f} {y:.4f})
\t\t(property "Reference" "{ref}"
\t\t\t(at 0 -2.5 0)
\t\t\t(layer "F.SilkS")
\t\t\t(hide yes)
\t\t\t(uuid "{uid()}")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.016 1.016)
\t\t\t\t\t(thickness 0.1524)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Value" "Terminal"
\t\t\t(at 0 2.5 0)
\t\t\t(layer "F.Fab")
\t\t\t(hide yes)
\t\t\t(uuid "{uid()}")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.016 1.016)
\t\t\t\t\t(thickness 0.1524)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(pad "{name}" smd rect
\t\t\t(at 0 0)
\t\t\t(size 2.0000 3.0000)
\t\t\t(layers "F.Cu" "F.Mask")
\t\t\t(net {NET_CODE} "{NET_NAME}")
\t\t\t(uuid "{uid()}")
\t\t)
\t)"""


def fmt_edge_polygon(points: list[tuple[float, float]]) -> str:
    """Closed board outline — KiCad 10 GUI DRC expects solid Edge.Cuts geometry."""
    pts = "\n".join(f"\t\t\t(xy {x:.4f} {y:.4f})" for x, y in points)
    return f"""\t(gr_poly
\t\t(pts
{pts}
\t\t)
\t\t(stroke
\t\t\t(width 0.1000)
\t\t\t(type solid)
\t\t)
\t\t(fill no)
\t\t(layer "Edge.Cuts")
\t\t(uuid "{uid()}")
\t)"""


def fmt_silk(text: str, x: float, y: float) -> str:
    return f"""\t(gr_text "{text}"
\t\t(at {x:.4f} {y:.4f})
\t\t(layer "F.SilkS")
\t\t(uuid "{uid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.0000 1.0000)
\t\t\t\t(thickness 0.1500)
\t\t\t)
\t\t\t(justify left bottom)
\t\t)
\t)"""


def build_pcb(
    title: str,
    target_r_ohm: float,
    label: str,
    pad_lead_mm: float = 15.0,
    edge_margin_mm: float = 3.0,
    copper_edge_mm: float = 0.35,
) -> tuple[str, dict]:
    target_len = target_length_mm(target_r_ohm)
    n_legs, leg_h = size_for_target_length(target_len)
    tail_h = 10.0
    serp_x0 = max(edge_margin_mm + pad_lead_mm + copper_edge_mm, tail_h + copper_edge_mm + 2.0)
    serp_y0 = tail_h + copper_edge_mm + 2.0
    ser = generate_serpentine(serp_x0, serp_y0, n_legs, leg_h)

    # Pads outside active serpentine, aligned with electrical start/end (short leads only).
    path_start = ser.segments[0][0]
    path_end = ser.segments[-1][1]
    pad1 = (path_start[0] - pad_lead_mm, path_start[1])
    pad2 = (path_end[0] + pad_lead_mm, path_end[1])
    lead1 = (pad1, path_start)
    lead2 = (path_end, pad2)

    extra_len = math.dist(*lead1) + math.dist(*lead2)
    total_len = ser.length_mm + extra_len
    r_est = estimate_resistance_ohm(total_len)

    board_w = serp_x0 + ser.active_w_mm + pad_lead_mm + edge_margin_mm + copper_edge_mm
    board_h = max(
        serp_y0 + leg_h + edge_margin_mm + copper_edge_mm,
        max(pad1[1], pad2[1]) + 3.0,
    )

    # Strain-relief tail below pad1 (polyimide only — no copper in tail)
    tail_w = 8.0
    tail_x0 = max(0.0, pad1[0] - tail_w / 2)
    tail_y0 = 0.0
    # Single continuous net for the sensing element (two pads are the resistor terminals).
    parts = [
        fmt_net(),
        fmt_pad_footprint("J1", "1", pad1[0], pad1[1], NET_CODE),
        fmt_pad_footprint("J2", "2", pad2[0], pad2[1], NET_CODE),
        fmt_seg(lead1[0], lead1[1]),
    ]
    for seg in ser.segments:
        parts.append(fmt_seg(seg[0], seg[1]))
    for arc in ser.arcs:
        parts.append(fmt_arc(arc[0], arc[1], arc[2]))
    parts.append(fmt_seg(lead2[0], lead2[1]))

    # Board outline (convex): main rectangle + optional strain-relief tab at bottom-left
    tab_right = tail_x0 + tail_w
    outline = [
        (0.0, 0.0),
        (tab_right, 0.0),
        (tab_right, tail_h),
        (board_w, tail_h),
        (board_w, board_h),
        (0.0, board_h),
        (0.0, 0.0),
    ]
    # Single closed polygon (not open gr_line chain — fixes GUI "no edges on Edge.Cuts" DRC)
    parts.append(fmt_edge_polygon(outline[:-1]))

    # Silk omitted — 0.1 mm flex features are documented in README/metadata (silk DRC min 1.0 mm).

    meta = {
        "title": title,
        "label": label,
        "target_r_ohm": target_r_ohm,
        "target_length_m": target_len / 1000.0,
        "estimated_r_ohm": r_est,
        "total_length_m": total_len / 1000.0,
        "n_legs": ser.n_legs,
        "active_w_mm": ser.active_w_mm,
        "active_h_mm": ser.active_h_mm,
        "board_w_mm": board_w,
        "board_h_mm": board_h,
        "trace_width_mm": TRACE_W,
        "pitch_mm": PITCH,
        "copper_thickness_mm": COPPER_T,
    }
    return "\n".join(parts) + "\n", meta


def pcb_header(title: str, thickness_mm: float = 0.11) -> str:
    return f"""(kicad_pcb
\t(version 20260206)
\t(generator "generate_strain_gauge_pcb.py")
\t(generator_version "1.0")
\t(general
\t\t(thickness {thickness_mm:.3f})
\t\t(legacy_teardrops no)
\t)
\t(paper "A3")
\t(title_block
\t\t(title "{title}")
\t\t(date "2026-03-20")
\t\t(rev "0.1")
\t\t(company "Formula Slug")
\t\t(comment 1 "Riddhi Gaddamwar")
\t\t(comment 2 "FPC strain gauge — preliminary")
\t\t(comment 3 "Not fabrication-ready without DFM review")
\t)
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(2 "B.Cu" signal)
\t\t(9 "F.Adhes" user "F.Adhesive")
\t\t(11 "B.Adhes" user "B.Adhesive")
\t\t(13 "F.Paste" user)
\t\t(15 "B.Paste" user)
\t\t(5 "F.SilkS" user "F.Silkscreen")
\t\t(7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user)
\t\t(3 "B.Mask" user)
\t\t(17 "Dwgs.User" user "User.Drawings")
\t\t(19 "Cmts.User" user "User.Comments")
\t\t(21 "Eco1.User" user "User.Eco1")
\t\t(23 "Eco2.User" user "User.Eco2")
\t\t(25 "Edge.Cuts" user)
\t\t(27 "Margin" user)
\t\t(31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard")
\t\t(35 "F.Fab" user)
\t\t(33 "B.Fab" user)
\t)
\t(setup
\t\t(pad_to_mask_clearance 0.050)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(pcbplotparams
\t\t\t(mode 1)
\t\t\t(useauxorigin no)
\t\t\t(outputformat 1)
\t\t\t(outputdirectory "")
\t\t)
\t)
\t(net 0 "")
"""


def pcb_footer() -> str:
    return ")\n"


def write_pcb(path: Path, title: str, target_r: float, label: str) -> dict:
    body, meta = build_pcb(title, target_r, label)
    path.write_text(pcb_header(title) + body + pcb_footer(), encoding="utf-8")
    meta["file"] = str(path)
    return meta


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    meta350 = write_pcb(
        root / "fpc-suspension-strain-gauge-350ohm.kicad_pcb",
        "FPC Suspension Strain Gauge — 350 ohm (assignment)",
        350.0,
        "350R",
    )
    meta35 = write_pcb(
        root / "poc-strain-gauge-35ohm.kicad_pcb",
        "FPC Strain Gauge POC — ~35 ohm",
        35.0,
        "35R-POC",
    )
    (root / "generation-metadata.json").write_text(
        json.dumps({"350ohm": meta350, "35ohm_poc": meta35}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"350ohm": meta350, "35ohm_poc": meta35}, indent=2))


if __name__ == "__main__":
    main()
