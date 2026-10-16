# FPC Suspension Strain Gauge (KiCad)

Formula Slug LV onboarding — flexible PCB serpentine resistor for suspension strain sensing.

**Author:** Riddhi Gaddamwar  
**Branch:** `riddhi-gaddamwar`  
**Status:** Preliminary layout for review — **not fabrication-ready** without mechanical bonding, calibration, and JLC DFM sign-off.

## Open in KiCad

1. Open **`fpc-suspension-strain-gauge.kicad_pro`** (350 Ω assignment design).
2. Open the **PCB Editor** (main board file: `fpc-suspension-strain-gauge.kicad_pcb`).
3. Optional POC: open **`poc-strain-gauge-35ohm.kicad_pro`** or `poc-strain-gauge-35ohm.kicad_pcb` (~35 Ω, smaller footprint).

**Inspect:** View → Zoom to Fit; enable **F.Cu** and **Edge.Cuts**; run **Inspect → Design Rules Checker** (should match project rules: 0.1 mm trace/clearance, 0.35 mm copper-to-edge).

## Designs included

| File | Purpose | Est. R | Board (mm) | Serpentine legs |
|------|---------|--------|------------|-----------------|
| `fpc-suspension-strain-gauge.kicad_pcb` | **350 Ω assignment target** | ~350 Ω (see metadata) | ~157 × 131 | 604 |
| `poc-strain-gauge-35ohm.kicad_pcb` | Small-footprint alternative | ~35 Ω | ~79 × 49 | 191 |

Numbers are from `generation-metadata.json` (regenerate with the script below).

## Electrical model

Copper trace resistor:

\[
R = \frac{\rho L}{w t}
\quad\Rightarrow\quad
L = \frac{R w t}{\rho}
\]

| Parameter | Value |
|-----------|--------|
| ρ (copper, ~20 °C) | 1.68×10⁻⁸ Ω·m |
| Trace width **w** | 0.1 mm |
| Copper thickness **t** | 35 µm (1 oz) |
| Pitch (width + gap) | 0.2 mm |
| Target **R** (assignment) | 350 Ω → **L ≈ 72.9 m** |

Active area (straight legs only): roughly **121 mm × 121 mm** for 350 Ω; the KiCad board is **larger** because of U-turn length, pad leads, edge clearance, and a **polyimide strain-relief tab** (no copper in the tab).

## Layout features

- Continuous **serpentine** on **F.Cu** (one net `GAUGE`, two terminal pads **J1** / **J2**).
- **Semicircular U-turns** (radius 0.15 mm centerline) to avoid pinched inner width at bends.
- Pads and short leads **outside** the sensing serpentine region.
- **No copper pour** — only the intentional gauge path.
- Regenerate geometry:  
  `python3 scripts/generate_strain_gauge_pcb.py`

## 350 Ω vs ~35 Ω POC (tradeoffs)

| | 350 Ω (assignment) | ~35 Ω POC |
|---|-------------------|-----------|
| Footprint | ~157 × 131 mm — impractical on a typical suspension tube | ~79 × 49 mm — still large but more plausible for a demo |
| DAQ | Wheatstone bridge / precision divider friendly (similar to commercial gauges) | Lower voltage swing for same excitation current; easier to drive with low noise but more sensitive to lead resistance |
| Sensitivity | Geometric gauge factor depends on bonding and direction — not automatically “better” at 350 Ω | Same material → same **ΔR/R** for same strain; lower R means more **current** for the same excitation |
| Temperature | Long copper path + polyimide — thermal and TCR effects need compensation | Shorter path, somewhat less spatial averaging |

**Do not assume** the POC behaves like a calibrated 350 Ω gauge without bonding tests.

## JLCPCB flex notes (verified from published capabilities)

- **1 oz (35 µm) copper:** minimum trace/space often **4/4 mil (~0.1 mm)** on 1 oz — our 0.1 / 0.1 mm design is at the limit; confirm in order review.
- **Copper to outline:** ≥ **0.3 mm** (layout uses **0.35 mm** inset in project DRC).
- **Coverlay:** exposed pad openings required for solder terminals; coverlay opening clearance to trace ≥ **0.15 mm** — add in layout before order.
- **Bend radius:** static bend ≥ **6×** finished thickness; **do not bend** across the serpentine — mount on straight section or use stiffener (document stiffener layer for JLC).
- **Not validated:** coverlay, stiffener, ENIG, panelization, or impedance — order only after JLC DFM upload.

## Schematic / ERC

Template schematic is minimal. Before fab, add a **Device:R** (350 or 35) symbol linked to **J1/J2**, plus DAQ connector symbols per LV standards. Run **Schematic → Update PCB** only after footprint refs match.

## Research document

`FPC_Suspension_Strain_Gauge_Corrected_Research.docx` — background, FSAE context, hand calculations.

## Limitations (show Luca)

1. **Copper strain gauge** vs constantan foil — unknown gauge factor and creep; team must validate against bonded commercial gauge.
2. **350 Ω board size** is a calculation demonstrator, not a mountable suspension sensor without major size reduction or different material (e.g. Nichrome, meander on shorter path with finer lithography).
3. **Temperature coefficient of copper** (~0.4%/°C) will swamp small strain signals without a dummy gauge or half-bridge.
4. **KiCad flex stackup** in generated PCB is simplified (0.11 mm thickness); update stackup to match JLC 1-layer 25 µm PI selection before Gerbers.
5. **CLI DRC** on PCB-only uses embedded geometry; always re-run DRC from the **.kicad_pro** after schematic links exist.

## Files

- `scripts/generate_strain_gauge_pcb.py` — serpentine generator
- `generation-metadata.json` — last computed lengths and estimates
- `StrainGauge.pretty/TerminalPad.kicad_mod` — terminal footprint
- Template tables copied from `lv/kicad-template`
