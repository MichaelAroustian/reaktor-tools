---
name: reaktor-tools
description: Expert knowledge of Native Instruments Reaktor 6 — Primary and Core building, modules, ensembles, DSP, and VA filter design. Use when the user asks about Reaktor architecture, building instruments or effects, .ens/.mdl files, signal routing, oscillators, filters, envelopes, or Reaktor performance optimisation.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Reaktor Tools and Modules

## Overview

Reaktor is a modular software synthesizer and sampler by Native Instruments. This skill provides knowledge about Reaktor's architecture, modules, and implementation details.

## Core Architecture

### Hierarchy
- **Ensemble**: Top-level container (the complete instrument)
- **Instrument**: Main functional unit within an ensemble
- **Structure**: Container for organizing modules (Macro level)
- **Cells**: Functional blocks that contain lower-level modules
- **Modules**: Individual processing units (oscillators, filters, etc.)

### Connection Types
- **Audio**: High-resolution audio signals (sample rate)
- **Event**: Discrete messages (MIDI notes, triggers)
- **Control**: Lower-resolution modulation signals

## Common Modules

(Add specific module documentation here as you learn)

### Oscillators
- TBD: Add oscillator module details

### Filters
- TBD: Add filter module details

### Envelopes
- TBD: Add envelope module details

### Utilities
- TBD: Add utility module details

## File Formats

- **.ens**: Ensemble files (complete instruments)
- **.mdl**: Module files
- TBD: Add more format details

## Best Practices

1. **Naming conventions**: Use clear, descriptive names for modules
2. **Organization**: Group related functionality in structures
3. **Documentation**: Add panel text and comments
4. **Testing**: Test with various input ranges
5. **Performance**: Monitor CPU usage and optimize

## Resources

### Official Documentation
- Reaktor 6 Getting Started: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/REAKTOR_6_Getting_Started_English_0419.pdf
- Reaktor 6 Diving Deeper: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/REAKTOR_6_Diving_Deeper_English_0817.pdf
- Reaktor 6 Building in Primary: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/REAKTOR_6_Building_in_Primary_English_0419.pdf
- Reaktor 6 Building in Core: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/REAKTOR_6_Building_in_Core_English_0618.pdf
- Reaktor 5.5 Core Reference: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/Reaktor_5_Core_Reference_English.pdf

### Reference Papers
- VA Filter Design 2.1.0 (Vadim Zavalishin): https://www.native-instruments.com/fileadmin/ni_media/downloads/pdf/VAFilterDesign_2.1.0.pdf

#### NI Community Forums
- Reaktor: https://community.native-instruments.com/categories/reaktor
- Building with Reaktor: https://community.native-instruments.com/categories/building-with-reaktor

## Notes

This is a living document. Add module details, tips, and patterns as you discover them.


## Common Modules (verified in Reaktor 6)

### Clock
- `Library > Clk Bundle > XR Unpack` — unpacks the SR/CR Bundle into C, R and Reset fibers.
  Needs explicit SR bus connection: right-click Bundle input → Pickup Std. Distribution Bus → Pickup SR.
  C = audio clock (fires every sample), R = sample rate in Hz, Reset = zero reset event.

### Math Mod (non-triggering parameter inputs)
- `Library > Math Mod > x div a` — divides signal x by parameter a. Only x triggers output.
- `Library > Math Mod > x mul a` — multiplies signal x by parameter a. Only x triggers output.
- `Library > Math Mod > x + a` — adds parameter a to signal x. Only x triggers output.

### Phase Accumulator (sawtooth oscillator) — IN PROGRESS
Modules placed so far:
1. XR Unpack (SR bus connected, C/R/Reset available)
2. x div a (Freq → x input, R → a input) — produces phase increment

Still to place:
3. `Library > Math Mod > x + a` — the accumulator (C → x input, increment → a input, feedback from 1 wrap → x input)
4. `Library > Math > 1 wrap` — wraps phase back to [0,1)

Wiring still to complete:
- x div a output → a input of x + a
- XR Unpack C output → x input of x + a  
- x + a output → 1 wrap input
- 1 wrap output → Phase output port
- 1 wrap output → feedback back into x + a (Reaktor 6 auto-resolves, wire turns orange)