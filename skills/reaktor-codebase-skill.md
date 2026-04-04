---
name: reaktor-codebase
description: Expert knowledge of the Reaktor 6 C++ codebase — architecture, build system, key subsystems, conventions, and where to make changes. Use when the user asks about building, modifying, or navigating the Reaktor source code.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Reaktor 6 — Codebase Reference

## Repository
Local path: `/Users/michael.aroustian/Documents/_dev/repos/_NI/Komplete/KOM-Reaktor`

---

## Architecture Overview

Two delivery shapes, two startup paths:

### Path A — Desktop / Plugin (macOS, Windows)
```
application/app/mainModule.cpp  MainModule::init()
  └─ AppFactory::create()  →  AppBase (NGL/GUI layer)
        Standalone → app/Standalone/Desktop/App.h
        VST3/AU/AAX → app/Plugin/App.h
```
- `AppBase` (`application/app/AppBase.h`) extends `NI::NGL::App`
- Instance-level interfaces (AudioClock, MIDI, …) live in `application/instance/`

### Path B — Headless / Linux / NativeOS
- **B1** (`ReaktorStandaloneHeadless`, `ReaktorVST3Headless`): same entry point, `REAKTOR_HEADLESS=ON`
- **B2** (`ReaktorEngineLib`): `engine/app/mainModule.cpp` → `Engine::makeDefaultInterfaces()` → `Engine(params)` → `TReaktor`
  - `TReaktor` is owned by `Engine`, accessed via `Engine::getReaktor()`

---

## Key Source Layout

| Path | Contents |
|------|----------|
| `src/reaktor/` | `TReaktor` (main Reaktor class), undo, session, model, OSC |
| `src/audio/` | Audio processing, AudioLoop, signal routing, TMem* modules |
| `src/mod/` | Module definitions, audio/event function libraries, fgm compiler output, connection system |
| `src/mod/fgm/` | `.fgm` source files compiled by `fgm` → `mod/fgm/out/fgm_*.cpp/.h` |
| `src/mod/ModClasses/` | Per-module class implementations |
| `src/app/` | App model, feature toggles, access layer |
| `src/base/` | Low-level utilities (`ReaktorBaseLib`) |
| `engine/` | `ReaktorEngineLib` — headless host-embedding API |
| `osc/Core/` | OSC protocol support |
| `application/` | Standalone/plugin entry points, GUI, instance interfaces |
| `gui/` | GUI components |
| `tests/` | Unit tests (GTest/Catch2) + robot acceptance tests |

---

## Core CMake Targets

| Target | Type | Contents |
|--------|------|----------|
| `ReaktorCoreInterface` | INTERFACE | Aggregates nilibs + oscCore + spdlog |
| `ReaktorCore` | OBJECT | All of `src/**` (depends on `fgmGenerateSources`) |
| `ReaktorBaseLib` | STATIC | `src/base/**` utilities |
| `ReaktorAppLib` | STATIC | `src/app/model/**` + `access/**` |
| `ReaktorModelLib` | STATIC | `src/reaktor/model/**` |
| `ReaktorEngineLib` | — | Embeddable engine, headless only |
| `ReaktorStandaloneDesktop` | — | macOS/Windows standalone |
| `ReaktorTest` | test | GTest unit tests |
| `ReaktorEngineTests` | test | Catch2 engine tests |

`ReaktorCore` always depends on `fgmGenerateSources` — the fgm compiler must run before building.

---

## Build Toggles

| Toggle | Default | Effect |
|--------|---------|--------|
| `REAKTOR_BUILD_MODE` | `DEVELOPER` | `RELEASE`/`BETA`/`ALPHA`/`DEVELOPER` |
| `REAKTOR_DESKTOP` | `ON` | GUI targets; forced `OFF` on Linux |
| `REAKTOR_HEADLESS` | `OFF` | Headless variants; forced `ON` on Linux |
| `REAKTOR_TESTS` | `ON` | Includes unit + engine tests |
| `REAKTOR_UNITY_BUILDS` | `ON` | `DISABLE_COMPILE_HELPER` opts out per-TU |

Headless full cmake set:
```
-DREAKTOR_HEADLESS=ON -DREAKTOR_DESKTOP=OFF -DREAKTORX_HEADLESS=ON -DKILIBS_HEADLESS=ON -DNILIBS_HEADLESS=ON
```

---

## Developer Workflows

### Bootstrap (first time)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
nib
```

### Build (CLion recommended)
Open `CMakeLists.txt` as project root in CLion. Select target and build profile.

### Tests
```bash
ctest -N              # list all tests with indices
ctest -V -I 5,5       # run test #5 verbosely
```
Key test executables: `ReaktorTest`, `ReaktorBaseLibTest`, `ReaktorModelLibTest`, `persistenceTest`, `ReaktorEngineTests`

### Robot/acceptance tests
```bash
# from tests/robot_tests/acceptance_tests/
robot --outputdir robot-output --output test-results.xml --loglevel TRACE tests
```
Requires `reaktor-test-data` repo checked out and `REAKTOR_ROBOT_TEST_WORK_DIR` set.

---

## Conventions

- **Formatting**: 2-space indent, Allman braces, 120-column limit (`.clang-format`)
- **Clang-tidy**: minimal — only `modernize-loop-convert` by default (`src/.clang-tidy.in`)
- **Platform gates**: use `M_GP_IS_STANDALONE()`, `M_GP_IS_VST3_PLUGIN()`, `M_GP_IS_LINUX_PLATFORM()`, `M_GP_IS_ARM_ARCH()` — do NOT use `#ifdef`
- **Feature toggles**: SHA1-keyed GP toggles; check/set with `app::feature::isOn(Toggle::X)` in `src/app/Feature.cpp`
- **Unity builds**: `DISABLE_COMPILE_HELPER` entries in CMakeLists are deliberate — don't remove them
- **Commit prefixes**: Jira ID (`R6-1234:`), symbol name (`TReaktor:`), or task type (`Refactoring:`, `Cleanup:`, `Removal:`)
- **Branching**: `feature/*` for features/bugfixes, `experimental/*` for prototypes; always rebase to update

---

## Where to Make Changes

| Goal | Start here |
|------|------------|
| Plugin/standalone bundle IDs or packaging | `application/CMakeLists.txt` |
| Core behavior (all targets) | `src/CMakeLists.txt` → edit under `src/` |
| Headless-only behavior | `application/app/AppBaseHeadless.*`, `engine/app/App.*` |
| Engine host-embedding API | `engine/inc/Engine.h` → `engine/Engine.cpp` → `engine/interface_impl/` |
| Module definitions / audio functions | `src/mod/` |
| Test registration | `support/cmake/reaktor_add_test.cmake` |
| Feature toggles | `src/App/Feature.cpp` |
