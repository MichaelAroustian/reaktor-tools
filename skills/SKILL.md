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
- Reaktor 5.5 Module Reference: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/Reaktor_5_Modules_and_Macros_Reference_English.pdf
- Reaktor 5 Manual Addendum: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/Reaktor_5_Manual_Addendum_English.pdf
- Reaktor 5 Core Tutorial: https://www.native-instruments.com/fileadmin/redaktion_upload/pdf/NI_REAKTOR5_Core_Manual_EN.pdf

### Reference Papers
- VA Filter Design 2.1.0 (Vadim Zavalishin): https://www.native-instruments.com/fileadmin/ni_media/downloads/pdf/VAFilterDesign_2.1.0.pdf

#### NI Community Forums
- Reaktor: https://community.native-instruments.com/categories/reaktor
- Building with Reaktor: https://community.native-instruments.com/categories/building-with-reaktor

## Notes

This is a living document. Add module details, tips, and patterns as you discover them.