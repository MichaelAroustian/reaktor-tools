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

---

## Session 2 — 2026-04-05

### Inspiration
Based on the work of Éliane Radigue — specifically *Geelriandre* — and a YouTube video by La Synthèse Humaine inspired by Daniel Silliman's work on the same subject.

### Patch: Extended to Dual Cross-FM + AM + Filters + Reverb

#### Full signal chain
```
Pair A/B (cross-FM) ──► Crossfader (X-Fade control)
Pair C/D (cross-FM) ──►

Crossfader Out ──► Multiply (× Osc B) → Pro-52 Filter A → Level ──► Mixer → Springtime Reverb → Out
               └──► Multiply (× Osc D) → Pro-52 Filter B → Level ──►
```

- **Osc B and D** used as AM modulators (ring modulation — bipolar)
- **Osc A and C** are the FM carriers, blended via crossfader
- Two **parallel** AM branches, each filtered independently, then mixed
- **Springtime** spring reverb (from NI Reaktor User Library, boscomac) added after mixer

#### AM / Ring modulation
- Bipolar (full ring mod) — carrier signal disappears, only sidebands remain
- Each branch modulated by one sub-audio oscillator (Osc B or D at pitch ~-30 to -5)
- Sub-audio AM creates slow amplitude beating — the "breathing" quality of Radigue's work

#### Pro-52 Filter
- `P` input used for cutoff (logarithmic, range 20–120)
- `Res` input exposed as control
- One filter per AM branch for independent timbral shaping
- `F` input available for audio-rate cutoff modulation (not yet wired)

#### Spectrum 2048 and Scope
Both added to the output for visual feedback.

#### Available Studio Effects (Library > 06 - Studio Effects)
3-Band EQ, Auto Pan, Chorus, Fbk Delay, Flanger, Frequency Shift, Overdrive, Phaser, Tape-ish Delay, Tremolo.
No built-in spring reverb — used Reaktor User Library instead.

#### Reaktor User Library search pattern
```
https://www.native-instruments.com/de/reaktor-community/reaktor-user-library/<category>/all/all/all/<keyword>/latest/1/<version>/
```
version: `3` = R6, `1` = R5. Fetch search page for entry IDs, then fetch each `entry/show/<id>/` for details.

---

### Next Steps
- Explore modulating Pro-52 `F` input with a sub-audio oscillator for slow filter sweeps
- Consider MIDI pitch input for the oscillators
- LFO modulation of FM depth for evolving timbres
- Mix Osc B into crossfader properly (currently unconnected)

---

### Reaktor Stability — File > Open Crash (resolved 2026-04-05)

Three crash reports generated today (`Reaktor 6-2026-04-05-213522.ips`, `-214456.ips`, `-215226.ips`) while using **File > Open**. The crashes no longer reproduce as of this session.

**Likely cause:** Reaktor Robot XML-RPC server (port 8270) and/or the feature-flag plist write during initial setup interacting with a file-open dialog operation. After Reaktor was restarted cleanly the dialog became stable.

**Resolution:** No code changes required. Reaktor 6 now opens the File > Open dialog without crashing.

