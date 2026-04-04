---
name: reaktor-overview
description: Foundational knowledge of Native Instruments Reaktor 6 — architecture, hierarchy, signal types, file formats, and all resource links. Use as the base reference for any Reaktor session.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Reaktor 6 — Overview

## Architecture Hierarchy

- **Ensemble** — top-level container (the complete instrument/effect)
- **Instrument** — main functional unit within an ensemble
- **Structure** — container for organising modules (Macro level)
- **Cells** — functional blocks containing lower-level modules (Core level)
- **Modules** — individual processing units (oscillators, filters, math, etc.)

## Signal Types

- **Audio** — high-resolution signals processed at sample rate
- **Event** — discrete messages (MIDI notes, triggers, parameter changes)
- **Control** — lower-resolution modulation signals

## File Formats

- **.ens** — Ensemble files (complete instruments/effects)
- **.mdl** — Module files

---

## Documentation Priority

When looking up module behaviour, ports, or ranges:
1. **Reaktor 6 manual** (processed text in `docs/REAKTOR_6_Building_in_Primary_English_0419/`)
2. **Reaktor 5 Modules & Macros Reference** (processed text in `docs/Reaktor_5_Modules_and_Macros_Reference_English/`)
3. **In-app info hints** — hover over a port in Reaktor with Info Hints enabled. Often more detailed than manuals. Ask for a screenshot if needed.
4. General DSP knowledge

---

## Official Documentation (local processed copies in `docs/`)

| Manual | Local path |
|--------|-----------|
| Reaktor 6 Building in Primary | `docs/REAKTOR_6_Building_in_Primary_English_0419/` |
| Reaktor 6 Building in Core | `docs/reaktor-6-building-in-core/` |
| Reaktor 5.5 Core Reference | `docs/reaktor-5-5-core-reference/` |
| Reaktor 5 Modules & Macros Reference | `docs/Reaktor_5_Modules_and_Macros_Reference_English/` |
| VA Filter Design 2.1.0 | `docs/va-filter-design/` |

PDF source links:
- Reaktor 6 Getting Started: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/REAKTOR_6_Getting_Started_English_0419.pdf
- Reaktor 6 Diving Deeper: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/REAKTOR_6_Diving_Deeper_English_0817.pdf
- Reaktor 6 Building in Primary: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/REAKTOR_6_Building_in_Primary_English_0419.pdf
- Reaktor 6 Building in Core: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/REAKTOR_6_Building_in_Core_English_0618.pdf
- Reaktor 5.5 Core Reference: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/Reaktor_5_Core_Reference_English.pdf
- VA Filter Design 2.1.0: https://www.native-instruments.com/fileadmin/ni_media/downloads/pdf/VAFilterDesign_2.1.0.pdf

---

## Reaktor User Library

Base URL: https://www.native-instruments.com/de/reaktor-community/reaktor-user-library/

### Search pattern
Search URL format:
```
https://www.native-instruments.com/de/reaktor-community/reaktor-user-library/<category>/all/all/all/<keyword>/latest/1/<reaktor-version>/
```
- `<category>`: `effect`, `instrument`, `blocks`, `other`, or `all`
- `<keyword>`: search term (e.g. `spring`)
- `<reaktor-version>`: `3` = Reaktor 6, `1` = Reaktor 5 or lower, `all` = all versions

Example — search for "spring" effects made in Reaktor 6:
```
https://www.native-instruments.com/de/reaktor-community/reaktor-user-library/effect/all/all/all/spring/latest/1/3/
```

### Browsing workflow
1. Fetch the search URL — returns a list of entry IDs with download/vote counts
2. Fetch each `entry/show/<id>/` page for name, description, rating, and details
3. Download requires user login on the NI website

---

## Community Resources

### NI Forums
- Reaktor: https://community.native-instruments.com/categories/reaktor
- Building with Reaktor: https://community.native-instruments.com/categories/building-with-reaktor

### Other Forums
- Reddit r/reaktor: https://www.reddit.com/r/reaktor/
- LINES — Reaktor thread: https://llllllll.co/t/reaktor-thread/29950
- LINES — Share your ensembles: https://llllllll.co/t/share-your-reaktor-ensembles/6383
- KVR Audio: https://www.kvraudio.com/forum/
- Mod Wiggler: https://www.modwiggler.com/forum/
- Gearspace: https://gearspace.com/board/
