---
name: reaktor-primary
description: Knowledge of building in Reaktor 6 Primary — modules, wiring conventions, verified port details, and patch patterns. Use when the user is building or modifying a Reaktor Primary-level ensemble.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Building in Reaktor 6 Primary

## General Conventions

- Add modules: right-click empty space in Structure view → **Built-In Module** → category → module name
- Add Library macros: right-click → **Library** → numbered category → macro name
- Add a control to a port: right-click the port → **Create Control**
- Built-In Modules (e.g. Multiply) **cannot be renamed** — only Macros and controls can be renamed (double-click the name)
- Port info (scale, typical range) is available via **Info Hints** — hover over the port. Ask for a screenshot if the manual doesn't cover it.
- **Z symbol** on a module input = Reaktor has auto-inserted a 1-sample delay to resolve a feedback loop. Expected and correct. (R6 manual ch.4)

---

## Verified Modules (Reaktor 6 Primary)

### Sine FM (`Built-In Module > Oscillators > Sine FM`)
Sine oscillator with audio-rate FM input. Use as carrier or modulator.

| Port | Type | Description |
|------|------|-------------|
| `P` | Event | Pitch, logarithmic semitone scale [0…127]. 69 = A4 (440 Hz) |
| `F` | Audio | Linear frequency modulation in Hz, added to frequency from P. Scale: 1 Hz/unit. Typ. range: [0…5000] *(from in-app info hint)* |
| `A` | Audio | Amplitude. Output range is [-A…A]. Use Constant = 1 for unity. |
| `Out` | Audio | Sine wave output |

Note: FM and Sync variants have higher CPU than plain Sine — only use when the extra input is needed.

### Multiply (`Built-In Module > Math > Multiply`)
Multiplies two signals. Standard uses:
- **FM depth scaling**: audio signal → top input, depth control → bottom input
- **Ring modulation / AM**: carrier → top input, modulator → bottom input

### Pro-52 Filter (`Library > 05 - Filters > Pro-52` or `Built-In Module > Filter > Pro-52`)
4-pole 24dB/oct lowpass, modelled on the Prophet-5 filter.

| Port | Type | Description |
|------|------|-------------|
| `P` | Event | Cutoff pitch, logarithmic semitones. Useful range: [20…120] (≈26 Hz–8370 Hz). Default (disconnected) = 0 = 8 Hz |
| `F` | Audio | Linear cutoff modulation in Hz, added to frequency from P |
| `Res` | Event | Resonance [0…1]. At 1, filter self-oscillates at cutoff as a sine tone |
| `In` | Audio | Signal input |
| `Out` | Audio | Filtered output |

Use `P` (not a linear control) for the cutoff knob — logarithmic matches human pitch perception.

### Crossfade (`Library > 07 - Mixer > Crossfade` or similar)
Blends between two signals using an X input [0…1].

---

## Cross-FM Patch Pattern

Two Sine FM oscillators modulating each other:
```
Osc A Out → Multiply A (top) → Osc A F    [FM Depth A control on Multiply bottom]
Osc B Out → Multiply B (top) → Osc B F    [FM Depth B control on Multiply bottom]
Pitch A control → Osc A P
Pitch B control → Osc B P
Constant 1 → Osc A A
Constant 1 → Osc B A
```
- FM Depth range: **0–5000** (typ. range per in-app info hint)
- Pitch range: **-63–127** (allows sub-audio; 36–84 for conservative musical range)
- Feedback wires show **Z** symbol — 1-sample delay, expected

### FM Frequency Locking
Cross-FM patches lock onto stable tones when frequencies hit simple integer ratios (1:1, 2:1, 3:2 etc.). Not a bug — fundamental FM property. Break the lock by: slightly detuning pitches, reducing FM depth, or crossfading to another pair.

---

## AM / Ring Modulation Pattern

Bipolar ring mod (carrier disappears, only sidebands):
```
Carrier → Multiply top
Modulator → Multiply bottom
Multiply Out → audio out
```

Classic AM (carrier preserved, unipolar modulator):
```
Modulator → Add (+1) → Multiply (×0.5) → Multiply bottom   [shifts [-1…1] to [0…1]]
Carrier → Multiply top
```

For Radigue-style slow amplitude beating: set modulator pitch below 0 (sub-audio). Range -30 to -5 gives slow tremolo rates.

---

## Library — 06 Studio Effects

Available in `Library > 06 - Studio Effects`:
- 3-Band EQ, Auto Pan, Chorus, Fbk Delay, Flanger, Frequency Shift, Overdrive, Phaser, Tape-ish Delay, Tremolo

No built-in spring reverb — use Reaktor User Library (see `reaktor-overview.md` for search pattern).
