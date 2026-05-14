# Max/MSP MCP — Research & Lessons for Reaktor

## Projects Studied

| Project | URL | Notes |
|---------|-----|-------|
| Original | https://github.com/tiianhk/MaxMSP-MCP-Server | Haokun Tian & Shuoyang Zheng — foundation |
| Extended fork | https://github.com/ersatzben/maxmsp-mcp | +11 tools, validation layer, subpatcher nav |

Both enable LLMs to create, query, and modify Max/MSP patches programmatically via MCP. Max patches are **JSON text** — they can be read and written directly. Reaktor ensembles are **binary** — this is the fundamental difference that shapes everything.

---

## Architecture Comparison

### Max/MSP MCP
```
Claude ←─stdio─→ server.py (FastMCP)
                     │
                  Socket.IO (port 5002)
                     │
              max_mcp_node.js (Node.js inside Max)
                     │
              max_mcp.js (Max JS object)
```

- Python server sends commands/requests to Max over Socket.IO
- Max-side JS executes them against the live patch (JS API: `patcher.newobject`, `outlet.connect`, etc.)
- Bidirectional: tool calls can *query* state and *modify* structure in the same session

### Reaktor MCP (current)
```
Claude ←─stdio─→ reaktor_mcp.py (MCP)
                     │
           ┌─────────┴──────────┐
        Robot XML-RPC        OSC UDP
        (port 8270)         (port 10000)
           │                    │
        Reaktor 6           Reaktor 6
    (query + modify        (parameter
      structure)            control)
```

- No text-based patch format — binary `.ens` only
- Robot handles structure (create module, save, open) but **cannot wire**
- OSC handles parameter values — fire-and-forget, no query

---

## Tool Mapping: Max/MSP → Reaktor

| Max/MSP tool | Reaktor equivalent | Gap? |
|---|---|---|
| `add_max_object` | `Create Instrument` / `Create Macro` / `Create Core Cell` (Robot) | Partial — Reaktor creates generic modules, no type selection |
| `connect_max_objects` | ❌ None | **Critical gap — no wiring API exists** |
| `disconnect_max_objects` | ❌ None | Same |
| `get_objects_in_patch` | `Get Num Modules` (Robot, count only) | Gap — no object listing with labels/types |
| `get_object_connections` | ❌ None | Gap |
| `move_object` | ❌ None | Gap — no positional control |
| `send_messages_to_object` | `send_osc` | ✅ Covered |
| `get_object_doc` | `search_docs` / `read_doc_chapter` | ✅ Covered |
| `create_subpatcher` → `enter_subpatcher` | Structure path arrays (`[[]]`, `[["5"]]`) | Partial — no explicit nav, just path-addressed calls |
| `check_signal_safety` | ❌ None | Gap |
| `list_all_objects` | ❌ None | Gap — no module type enumeration |
| `encapsulate` | ❌ None | Gap |

---

## Key Lessons for Reaktor MCP

### 1. Wiring is the fundamental blocker
Max's killer feature here is `connect_max_objects` / `disconnect_max_objects`. Reaktor has **no equivalent**. The confirmed workaround (from `reaktor-robot-skill.md`) is pre-wired template `.ens` files. The more complete the template library, the better the agent can work without wiring.

**Action**: Grow `templates/` with use-case-specific pre-wired templates (e.g. `osc-controlled-synth.ens`, `effect-chain.ens`, `modulated-param.ens`).

### 2. Validation layer before sending commands
Max/MSP MCP enforces constraints *inside the MCP server* before forwarding to Max: float type requirements, object name aliases (`times~` → `*~`), parameter range checks (svf~ Q, onepole~ Hz). This prevents wasted round-trips and confusing failures.

For Reaktor: validate OSC address format (must start with `/`) already done. Could add:
- OSC arg type/range validation against known Reaktor parameter conventions
- Robot keyword args validation (e.g. path must be a list-of-lists)

### 3. Bidirectional state query
Max can answer: "what objects are in this patch right now?" Reaktor's Robot can answer partial state: `Get Num Modules`, `Find Module By Label`, `Is Edit Mode`, `Is Touched`, `Get Project Name`. A tool that walks the structure tree iteratively using `Get Num Modules` at nested paths could synthesise a patch overview.

**Potential new tool**: `describe_structure` — walk Robot's structure path tree to produce a hierarchical list of modules (using `Get Num Modules` + `Find Module By Label` iteration).

### 4. Subpatcher / hierarchy navigation pattern
Max has explicit `enter_subpatcher` / `exit_subpatcher` context stack. Reaktor's Robot uses **structure path arrays** for the same concept: `[[]]` = root, `[["5"]]` = 6th child, `[["5", "2"]]` = nested. No nav needed — just address by path directly.

This is actually cleaner than Max's stateful nav. Document it clearly in tool descriptions.

### 5. Object placement / spatial awareness
Max has `get_avoid_rect_position()` to prevent modules overlapping. Reaktor's Robot exposes **no positional data** for modules. Layouts must be manual. Not a blocker for functionality but means auto-created modules pile up in the default position.

### 6. Socket.IO bridge pattern (future reference)
If Reaktor ever exposes a JavaScript or plugin scripting API, the Socket.IO bridge (Python MCP ↔ in-app JS) is a proven pattern. Currently not applicable — Reaktor's only programmatic entry points are Robot (XML-RPC) and OSC.

### 7. Skill / checklist pattern
Max MCP uses a `SKILL.md` invoked before every patch-creation session (documents placement rules, float gotchas, flag requirements). For Reaktor, the equivalent is `skills/reaktor-robot-skill.md`. Pattern is sound — the pre-session skill checklist helps agents avoid known pitfalls.

---

## Proposed Reaktor MCP Enhancements (Priority Order)

### High impact, feasible now

1. **More pre-wired templates** — the only path to creating patched ensembles without wiring API.
   Suggested: `fm-synth.ens`, `fx-chain.ens`, `osc-filter.ens`, `sequenced-osc.ens`.

2. **`describe_structure` tool** — walk Robot structure paths recursively, return labelled module tree.
   ```
   Get Num Modules [[]]  →  N
   Find Module By Label [[]] each_label  →  iterate
   Get Num Modules [["0"]], [["1"]], ...  →  recurse
   ```

3. **`load_module` tool (wrapper)** — expose Robot's `Load Via Structure` more ergonomically:
   drop a `.ism` or `.mdl` into a specific path, abstracting the `args=[[]]` path convention.

### Medium impact, needs investigation

4. **OSC parameter map per template** — ship a sidecar `.json` beside each `.ens` template listing
   its OSC addresses, value ranges, and semantics. `list_templates` could return this metadata.
   Would make `send_osc` guided rather than blind.

5. **`get_patch_state` tool** — combine `Get Num Modules`, `Get Project Name`, `Is Edit Mode`,
   `Is Touched` into one structured summary call.

### Low impact / blocked by binary format

6. **Wire-by-template library** — pre-wired sub-structures as `.ism` files that `Load Via Structure`
   drops in fully connected. Would require manual Reaktor work to author.

7. **Binary format reverse engineering** — `skills/session-notes.md` already notes this is in
   progress. If `.ens` format is decoded, `connect_max_objects`-equivalent becomes possible.

---

## Reference: Max/MSP MCP Tool List (for completeness)

```
# Object CRUD
add_max_object, remove_max_object, move_object, recreate_with_args, autofit_existing

# Wiring
connect_max_objects, disconnect_max_objects

# Attributes / messaging
set_object_attribute, set_message_text, set_number, send_bang_to_object, send_messages_to_object

# Query
get_objects_in_patch, get_objects_in_selected, get_object_attributes, get_object_connections,
get_avoid_rect_position, list_all_objects, get_object_doc

# Subpatcher navigation
create_subpatcher, enter_subpatcher, exit_subpatcher, get_patcher_context, add_subpatcher_io

# Safety / organisation
check_signal_safety, encapsulate
```

