# Reaktor Robot Framework Skill

## Overview

Reaktor 6.5.0 ships with a built-in Robot Framework XML-RPC server on port **8270**. It exposes GUI-automation keywords for programmatic control of Reaktor's structure, project management, and panel state. Activated by a feature flag + serial number in the macOS preferences.

---

## Activation (one-time setup)

Both keys survive Reaktor restarts and reboots.

```bash
# Feature flag — SHA1("Reaktor" + "Robot"). Integer 1 in the user plist is sufficient.
defaults write "com.native-instruments.Reaktor 6" "5d4e071323382551707559765a3322d24e9e3fcd" -int 1

# Serial number — 391 = Reaktor Full product ID
defaults write "com.native-instruments.Reaktor 6" "RobotSNO" -string "391"
```

Restart Reaktor after writing. The system plist (`/Library/Preferences/`) does NOT need to be modified — the user plist alone is sufficient.

### Verify

```bash
lsof -i :8270   # should show: Reaktor ... TCP *:8270 (LISTEN)
python3 -c "import xmlrpc.client; print(xmlrpc.client.ServerProxy('http://127.0.0.1:8270').run_keyword('Is Active', [], {}))"
# Expected: {'status': 'PASS', 'return': True}
```

### How it works

- Feature flag key is `SHA1("Reaktor" + "Robot")` = `5d4e071323382551707559765a3322d24e9e3fcd`
- Stored in `~/Library/Preferences/com.native-instruments.Reaktor 6.plist`
- `RobotSNO = "391"` sets product flavour to Reaktor Full (enables all keywords)
- `NI::GP::Registry::initSystemAndUser("Reaktor 6", ...)` reads both system and user plists at startup
- Source: `KOM-Reaktor/src/reaktor/robot/Setup.cpp`, `src/app/Feature.cpp`

---

## XML-RPC Protocol

Endpoint: `http://127.0.0.1:8270`  
Method: `run_keyword(keyword_name: str, args: list, kwargs: dict) → dict`

Response dict:
```python
{'status': 'PASS', 'return': <value>}   # success
{'status': 'FAIL', 'error': '<message>'}  # failure
```

### Python usage

```python
import xmlrpc.client
proxy = xmlrpc.client.ServerProxy("http://127.0.0.1:8270", allow_none=True)
result = proxy.run_keyword("Is Active", [], {})
# {'status': 'PASS', 'return': True}
```

### Via MCP tool

```
call_reaktor_robot(keyword="Is Active", args=[])
call_reaktor_robot(keyword="Create Instrument", args=[[]])   # [[]] = root path
```

---

## Path Argument Convention

Keywords marked with `path[]` or `parentPath[]` in the keyword table take a **structure path array** as their first positional argument.

| Target | `args` value |
|--------|-------------|
| Root level (ensemble top) | `[[]]` |
| Inside instrument at index 5 | `[["5"]]` |
| Nested deeper | `[["5", "2"]]` |

**IMPORTANT:** Pass `args=[[]]` not `args=[]` for root-level path keywords. `args=[]` means "no arguments" and will return `Parameter conversion error: not an Array at idx=0`.

---

## Complete Keyword Reference

All keywords confirmed from source `KOM-Reaktor/gui/gui/robot/*.cpp`.

### Project

| Keyword | Args | Returns | Notes |
|---------|------|---------|-------|
| `Is Active` | — | `bool` | Always `True` if server is reachable |
| `Get Version` | — | `str` | e.g. `"Reaktor 6.5.0 (R0)"` |
| `New Ensemble` | — | — | Creates blank ensemble; prompts to save if unsaved changes |
| `New Rack` | — | — | Creates blank rack |
| `Open Project` | `filename: str` | — | Opens `.ens` or `.nksr` by absolute path |
| `Save Project` | — | — | Saves current project |
| `Set Project File Name` | `path: str` | — | Sets save path without saving |
| `Get Project Name` | — | `str` | Returns current filename |
| `Is Touched` | — | `bool` | `True` if unsaved changes exist |
| `Touch Project` | — | — | Marks project as modified |
| `Is Edit Mode` | — | `bool` | `True` if in edit/build mode |
| `Is Ensemble Mode` | — | `bool` | |
| `Is Rack Mode` | — | `bool` | |
| `Process File Load Requests` | — | — | Flushes pending file-load queue |

### Structure

| Keyword | Args | Returns | Notes |
|---------|------|---------|-------|
| `Get Num Modules` | `path[]` | `int` | Count children at path |
| `Get Num Instruments` | `path[]` | `int` | Count instruments at path |
| `Get Num Selected Modules` | `path[]` | `int` | |
| `Create Instrument` | `parentPath[]` | `[str]` | Returns path index of new module |
| `Create Macro` | `parentPath[]` | `[str]` | |
| `Create Core Cell` | `parentPath[]` | `[str]` | |
| `Delete Module` | `path[]` | — | |
| `Find Module By Label` | `parentPath[], label: str` | — | |
| `Structure Unselect All` | — | — | |
| `Load Via Structure` | `files: [str], path[]` | — | Drops `.ens`/`.ism`/`.mdl`/`.rcc` into structure |

### Undo

| Keyword | Args | Notes |
|---------|------|-------|
| `Can Undo` | — | |
| `Can Redo` | — | |
| `Undo` | — | |
| `Redo` | — | |

### Panel / Workspace

| Keyword | Args | Notes |
|---------|------|-------|
| `Is Panel Visible` | — | |
| `Is Structure Visible` | — | |
| `Is Panel Locked` | — | |
| `Set Panel Locked` | `bool` | |
| `Panel.Is Compact View` | — | |
| `Panel.Is Ports Only View` | — | |
| `Panel.Is Ports And Wires View` | — | |
| `Panel.Is Wiring Visible` | — | |
| `Panel.Toggle Compact View` | — | |
| `Panel.Toggle Ports Only View` | — | |
| `Panel.Toggle Ports And Wires View` | — | |
| `Toggle Rack Split Structure View` | — | |
| `Toggle Rack Full Structure View` | — | |

### Automation

| Keyword | Notes |
|---------|-------|
| `Get Automation Base Id` | |
| `Get Automation Id` | |
| `Get Automation Max Id` | |
| `Set Automation Max Id` | |
| `Compress Automation` | |
| `Sort And Compress Automation` | |
| `Move Instrument Automation Up` | |
| `Move Instrument Automation Down` | |

---

## Known Limitations

**No wiring keyword exists.** There is no `Connect Ports`, `Wire`, or equivalent in the Robot server. This was confirmed by exhaustive grep of all `.cpp` files in `KOM-Reaktor/gui/gui/robot/`. Port connections must be made either:

1. Manually in Reaktor's GUI
2. Via a pre-wired template `.ens` file
3. Via future custom Robot keywords (requires C++ Reaktor build)
4. Via binary `.ens` format patching (research in progress)

**`New Ensemble` fails if unsaved changes exist.** It will throw `Unexpected message dialog: Save changes to ...?`. Workaround: call `Save Project` first, or dismiss the dialog via `Close No Save`.

---

## Workflow: Create Ensemble with Instrument

```python
import xmlrpc.client
proxy = xmlrpc.client.ServerProxy("http://127.0.0.1:8270", allow_none=True)

def kw(name, *args):
    r = proxy.run_keyword(name, list(args), {})
    assert r['status'] == 'PASS', f"{name} failed: {r.get('error')}"
    return r.get('return')

kw("New Ensemble")
assert kw("Is Edit Mode") == True
n_before = kw("Get Num Modules", [])      # root path = []
path = kw("Create Instrument", [])         # returns e.g. ['5']
n_after = kw("Get Num Modules", [])
assert n_after == n_before + 1
kw("Set Project File Name", "/path/to/output.ens")
kw("Save Project")
```

---

## Source File Map

| File | Contents |
|------|----------|
| `src/reaktor/robot/Setup.cpp` | Server init, gating on `app::feature::Toggle::Robot` |
| `src/app/Feature.cpp` | `Toggle::Robot` → `generateHashedKey("Robot")` → `5d4e07...` |
| `src/persistence/Registry.h` | `RobotSNO` plist key mapping |
| `gui/gui/robot/Project.cpp` | `New Ensemble`, `Open/Save Project`, `Get Project Name`, etc. |
| `gui/gui/robot/Structure.cpp` | `Create Instrument/Macro/Core Cell`, `Load Via Structure`, etc. |
| `gui/gui/robot/Panel.cpp` | Panel view toggle keywords |
| `gui/gui/robot/Undo.cpp` | Undo/Redo keywords |
| `gui/gui/robot/Automation.cpp` | Automation ID keywords |
| `tests/robot_tests/` | Acceptance and smoke tests showing real usage patterns |

All source in: `/Users/michael.aroustian/Documents/_dev/repos/_NI/Komplete/KOM-Reaktor/`

