# Session Notes

## Session 1 — 2026-04-04

### Patch: Dual Cross-FM Oscillator Pair

#### What was built
Two pairs of cross-FM Sine FM oscillators with a crossfader blending between them.

**Structure per pair:**
```
Osc A Out → Multiply (top) → Osc A F input   [FM Depth A knob on Multiply bottom]
Osc B Out → Multiply (top) → Osc B F input   [FM Depth B knob on Multiply bottom]
Pitch A knob → Osc A P
Pitch B knob → Osc B P
Constant 1  → Osc A A
Constant 1  → Osc B A
```
Two pairs (A/B and C/D) fed into a Crossfader module → audio output + Scope.

#### Module paths (Reaktor 6 Primary)
- `Built-In Module > Oscillators > Sine FM`
- `Built-In Module > Math > Multiply`
- Controls added via: right-click port → **Create Control**

#### Key settings
- FM Depth range: **0–5000** (1 Hz per unit, typ. range from in-app info hint)
- Pitch range: **-63–127** (user preference; conservative alternative: 36–84)
- Amplitude: Constant value **1** connected to `A` input

---

### Things Learned

#### Reaktor 6 Primary conventions
- Built-In Modules (e.g. Multiply) **cannot be renamed** — only Macros and controls can
- Right-click port → **Create Control** (not "Create Knob")
- Port info hints (scale, typical range) are available by hovering over a port with Info Hints enabled — often more detailed than the manuals. Use screenshots to share this with Copilot.

#### Z symbol on module inputs
The **Z** on an input port means Reaktor has automatically inserted a 1-sample delay to resolve a feedback loop (R6 manual, ch.4). Expected and correct for cross-FM patches. No action needed.

#### FM Frequency Locking
Cross-FM patches can "lock" onto stable tones when carrier/modulator frequencies hit simple integer ratios (1:1, 2:1, 3:2 etc.). Not a bug — a fundamental FM property. To break the lock: slightly detune pitches, reduce FM depth, or blend with another pair via crossfader. The DX7 famously exploited these locked states for its glassy/metallic tones.

#### F input (Sine FM) — not fully documented in manuals
The R6 and R5 manuals only say "F — linear frequency control in Hz, added to P". The full detail (scale: 1 Hz per unit, typ. range: [0…5000]) only appears in Reaktor's in-app info hint overlay, not in any processed manual text.

#### Documentation priority
R6 manual → R5 manual → in-app info hints (screenshots) → general knowledge

#### Processed manuals available in docs/
- `REAKTOR_6_Building_in_Primary_English_0419/` — 18 chapters (chapters 10–18 were missing due to a bug in `pdf_to_chapters.py`, now fixed)
- `Reaktor_5_Modules_and_Macros_Reference_English/` — R5 module reference

---

### Next Steps (to continue)
- Add amplitude envelope (gate-triggered)
- Add MIDI pitch control (Note Pitch module → P inputs)
- Consider a filter after the crossfader
- Consider LFO modulation of FM depth for evolving timbres
