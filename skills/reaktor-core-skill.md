---
name: reaktor-core
description: Knowledge of building in Reaktor 6 Core — cells, buses, clocking, math modules, and low-level DSP patterns. Use when the user is building or modifying a Reaktor Core-level structure.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Building in Reaktor 6 Core

## Key Differences from Primary

- Core operates at the **cell** level — lower level than Primary modules
- Uses **fibers** (typed signals) rather than generic wires
- Requires explicit clock/SR bus connections
- Feedback wires turn **orange** in Core (unlike Primary where a Z symbol appears)

---

## Clock

### XR Unpack (`Library > Clk Bundle > XR Unpack`)
Unpacks the SR/CR Bundle into three fibers:
- `C` — audio clock (fires every sample)
- `R` — sample rate in Hz
- `Reset` — zero reset event

**Important:** Needs explicit SR bus connection:
right-click Bundle input → **Pickup Std. Distribution Bus → Pickup SR**

---

## Math Modules (non-triggering parameter inputs)

These modules only output when their signal input (`x`) receives a value — parameter inputs (`a`) do not trigger output.

- `Library > Math Mod > x div a` — divides signal x by parameter a
- `Library > Math Mod > x mul a` — multiplies signal x by parameter a
- `Library > Math Mod > x + a` — adds parameter a to signal x

---

## Phase Accumulator (sawtooth oscillator) — IN PROGRESS

### Modules placed
1. XR Unpack (SR bus connected, C/R/Reset available)
2. `x div a` (Freq → x input, R → a input) — produces phase increment per sample

### Still to place
3. `Library > Math Mod > x + a` — the accumulator
   - C → x input (clock triggers each sample)
   - phase increment → a input
   - feedback from `1 wrap` output → x input
4. `Library > Math > 1 wrap` — wraps phase back to [0, 1)

### Wiring still to complete
```
x div a Out → a input of accumulator (x + a)
XR Unpack C → x input of accumulator
accumulator Out → 1 wrap In
1 wrap Out → Phase output port
1 wrap Out → feedback back into accumulator x input  (wire turns orange — Reaktor auto-resolves)
```
