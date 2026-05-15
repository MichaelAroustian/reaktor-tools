"""
reaktor_mcp.py
--------------
MCP server for Reaktor file access.
Provides tools for browsing, organising, and creating Reaktor ensembles.

Note: All Reaktor files (.ens, Core, Primary modules) are binary format
and cannot be read as text. Tools here support browsing, metadata, and
ensemble creation (via copy) only.

Write access is restricted to the User Ensembles root only.

Configuration (environment variables):
    REAKTOR_FACTORY_LIBRARY — path to Reaktor Factory Library (factory Core/Primary modules)
    REAKTOR_USER_LIBRARY    — path to Reaktor User Library (my Core/Primary modules)
    REAKTOR_USER_ENSEMBLES  — path to Reaktor User Ensembles (my ensembles)
    REAKTOR_TEMPLATES       — path to local ensemble templates (default: templates/ in this repo)
    REAKTOR_APP             — path to Reaktor 6.app (default: /Applications/Native Instruments/Reaktor 6/Reaktor 6.app)
"""

import asyncio
import json
import logging
import os
import plistlib
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import httpx
from pythonosc import udp_client as osc_udp_client
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ── Logging ────────────────────────────────────────────────────────────────────
# Logs to a file alongside this script so stdout stays clean for MCP stdio transport
log_path = Path(__file__).parent / "reaktor_mcp.log"
logging.basicConfig(
    filename=log_path,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
REAKTOR_FACTORY_LIBRARY = Path(
    os.environ.get(
        "REAKTOR_FACTORY_LIBRARY",
        "/Applications/Native Instruments/Reaktor 6/Library",
    )
).resolve()

REAKTOR_USER_LIBRARY = Path(
    os.environ.get(
        "REAKTOR_USER_LIBRARY",
        Path.home() / "Documents/Native Instruments/Reaktor 6/Library",
    )
).resolve()

REAKTOR_USER_ENSEMBLES = Path(
    os.environ.get(
        "REAKTOR_USER_ENSEMBLES",
        Path.home() / "Documents/Native Instruments/User Content/Reaktor/Ensembles",
    )
).resolve()

REAKTOR_TEMPLATES = Path(
    os.environ.get(
        "REAKTOR_TEMPLATES",
        Path(__file__).parent / "templates",
    )
).resolve()

# Path to the Reaktor 6 app bundle (used by open_in_reaktor)
REAKTOR_APP = Path(
    os.environ.get(
        "REAKTOR_APP",
        "/Applications/Native Instruments/Reaktor 6/Reaktor 6.app",
    )
)

ALLOWED_ROOTS = {
    "factory library": REAKTOR_FACTORY_LIBRARY,
    "user library": REAKTOR_USER_LIBRARY,
    "ensembles": REAKTOR_USER_ENSEMBLES,
    "templates": REAKTOR_TEMPLATES,
}

log.info("Factory Library: %s", REAKTOR_FACTORY_LIBRARY)
log.info("User Library:    %s", REAKTOR_USER_LIBRARY)
log.info("User Ensembles:  %s", REAKTOR_USER_ENSEMBLES)
log.info("Templates:       %s", REAKTOR_TEMPLATES)
log.info("Reaktor app:     %s", REAKTOR_APP)

# ── OSC ────────────────────────────────────────────────────────────────────────
OSC_HOST = os.environ.get("REAKTOR_OSC_HOST", "127.0.0.1")
OSC_PORT = int(os.environ.get("REAKTOR_OSC_PORT", "10000"))   # Reaktor 6 default: 10000

log.info("OSC target:      %s:%d", OSC_HOST, OSC_PORT)

# ── Reaktor preferences ────────────────────────────────────────────────────────
# macOS: ~/Library/Preferences/com.native-instruments.Reaktor 6.plist
REAKTOR_PREFS_PLIST = Path.home() / "Library/Preferences/com.native-instruments.Reaktor 6.plist"

# ── Docs ───────────────────────────────────────────────────────────────────────
DOCS_ROOT = Path(__file__).parent / "docs"

DOCS_MANUALS = {
    "getting-started": DOCS_ROOT / "REAKTOR_6_Getting_Started_English_0419",
    "diving-deeper":   DOCS_ROOT / "REAKTOR_6_Diving_Deeper_English_0817",
    "primary":         DOCS_ROOT / "REAKTOR_6_Building_in_Primary_English_0419",
    "core":            DOCS_ROOT / "reaktor-6-building-in-core",
    "modules":         DOCS_ROOT / "Reaktor_5_Modules_and_Macros_Reference_English",
    "core5":           DOCS_ROOT / "reaktor-5-5-core-reference",
    "va-filter":       DOCS_ROOT / "va-filter-design",
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def resolve_safe(root: Path, subpath: str) -> Path | None:
    """Resolve subpath within root. Returns None if the result escapes the root."""
    try:
        target = (root / subpath).resolve()
        if str(target).startswith(str(root)):
            return target
    except Exception as e:
        log.warning("Path resolution error: %s", e)
    return None


def get_root(location: str) -> Path | None:
    """Return the root Path for a given location name, or None if invalid."""
    return ALLOWED_ROOTS.get(location.lower())


def format_directory(target: Path) -> str:
    """Return a readable directory listing with file sizes."""
    entries = []
    for p in sorted(target.iterdir()):
        if p.is_dir():
            entries.append(f"DIR   {p.name}/")
        else:
            size_kb = p.stat().st_size / 1024
            entries.append(f"FILE  {p.name}  ({size_kb:.1f} KB)")
    return "\n".join(entries) if entries else "(empty)"


def _extract_ens_strings(data: bytes) -> dict:
    """Extract and categorize human-readable strings from a Reaktor .ens binary.

    Reaktor stores module names, parameter labels, port descriptions, help text,
    and preset names as plain ASCII inside the binary. This function extracts and
    categorizes them, filtering out binary noise and format tokens.

    Returns a dict with:
      labels       — short strings: module names, parameter/preset/port labels
      descriptions — longer sentences: help text, port descriptions
      file_refs    — embedded file:// paths (samples, modules)
      osc_hints    — strings starting with '/' that may be OSC addresses
    """
    import re as _re

    # Extract all printable ASCII sequences >= 4 chars
    raw_matches = _re.findall(rb'[\x20-\x7e]{4,}', data)
    seen: set[str] = set()
    labels: list[str] = []
    descriptions: list[str] = []
    file_refs: list[str] = []
    osc_hints: list[str] = []

    # Noise: internal format tokens and Reaktor binary-section markers
    _SKIP_PREFIXES = (
        "KSModul", "KEnsemble", "KInPort", "KOutPort", "KParam", "KStat",
        "BTN_", "KNB_", "LBL_", "TBN_", "BG_", "RNG_", "LED_", "ANIM_",
        "GUI_", "SCL_", "VALUE_", "Align ", "Numeral", "ModA ", "ModB ",
        "Mod A:", "Mod B:", "INIT -", "blend_", "splitter", "separator",
        "slider", "lamp", "button logic",
    )
    _NOISE_PATTERNS = [
        _re.compile(r'^[A-Z]{2,8}[a-z]{0,2}$'),          # DSIN, RTKR, hsin, etc.
        _re.compile(r'^[0-9a-fA-F]{5,}$'),                # pure hex
        _re.compile(r'^\d+\.?\d*\s*(kHz|Hz|ms|dB|s)$'),  # "5.50 kHz", "100 ms"
        _re.compile(r'^\d+\s*\.\.\.\s*\d+'),              # "0...100", "0 ms ... 999 ms"
        _re.compile(r'^[A-Z_]{4,}[_A-Z0-9]{2,}$'),       # ALL_CAPS_IDENTIFIERS
        _re.compile(r'^[0-9\s.,]+$'),                      # pure numbers/spacing
        _re.compile(r'^file:'),                            # handled separately
    ]

    def _is_noise(s: str) -> bool:
        if not any(c.isalpha() for c in s):
            return True
        # Strings containing ? are almost always binary artifacts in .ens files
        if '?' in s:
            return True
        alnum_ratio = sum(c.isalnum() or c.isspace() for c in s) / len(s)
        if alnum_ratio < 0.65:
            return True
        for pat in _NOISE_PATTERNS:
            if pat.match(s):
                return True
        return False

    for raw in raw_matches:
        try:
            s = raw.decode('ascii').strip()
        except Exception:
            continue
        if not s or len(s) < 3 or s in seen:
            continue
        seen.add(s)

        # File references
        if s.startswith('file:///'):
            file_refs.append(s)
            continue

        # Skip internal UI/format tokens
        if any(s.startswith(p) for p in _SKIP_PREFIXES):
            continue

        if _is_noise(s):
            continue

        # OSC address hint: starts with / followed by word chars, min length 4
        if s.startswith('/') and len(s) >= 4 and _re.match(r'^/[a-zA-Z][a-zA-Z0-9/_.-]{2,}$', s):
            osc_hints.append(s)
            continue

        # Longer sentences with a capital start → description / help text
        if len(s) >= 30 and ' ' in s and (s[0].isupper() or s[0].isdigit()):
            descriptions.append(s)
        elif 3 <= len(s) <= 80:
            labels.append(s)

    # Sort labels by quality before capping:
    # multi-word title-case strings first (likely component/module names),
    # then uppercase-start single words (likely parameter names),
    # then everything else.
    def _label_priority(s: str) -> tuple:
        has_space = ' ' in s
        starts_upper = bool(s) and s[0].isupper()
        return (
            -int(has_space and starts_upper),  # multi-word capital first
            -int(starts_upper),                 # uppercase-start second
            -len(s),                            # longer strings before short
        )
    labels.sort(key=_label_priority)

    return {
        "labels": labels[:600],
        "descriptions": descriptions[:100],
        "file_refs": list(dict.fromkeys(file_refs))[:30],
        "osc_hints": osc_hints[:20],
    }


# ── Server ─────────────────────────────────────────────────────────────────────
app = Server("reaktor-tools")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_files",
            description=(
                "List files and folders in a Reaktor directory. "
                "Use location='factory library' for the Factory Library (factory Core/Primary modules), "
                "location='user library' for the User Library (my Core/Primary modules), "
                "location='ensembles' for User Ensembles (my patches), "
                "or location='templates' for the local ensemble templates folder."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "enum": ["factory library", "user library", "ensembles", "templates"],
                        "description": "Which Reaktor root to browse.",
                    },
                    "subpath": {
                        "type": "string",
                        "description": "Subdirectory within the root. Use '.' for the root itself.",
                        "default": ".",
                    },
                },
                "required": ["location"],
            },
        ),
        Tool(
            name="get_file_info",
            description=(
                "Get metadata about a file in the Reaktor library or ensembles — "
                "name, size, and modification date. "
                "Note: Reaktor files are binary and cannot be read as text."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "enum": ["factory library", "user library", "ensembles", "templates"],
                        "description": "Which Reaktor root the file lives in.",
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file, relative to the chosen root.",
                    },
                },
                "required": ["location", "filepath"],
            },
        ),
        Tool(
            name="copy_ensemble",
            description=(
                "Create a new ensemble by copying an existing .ens file into the User Ensembles folder. "
                "Since Reaktor ensembles are binary, this is the only way to create one programmatically. "
                "The source can be any location (factory library, user library, or ensembles). "
                "The destination is always within the 'ensembles' root."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source_location": {
                        "type": "string",
                        "enum": ["factory library", "user library", "ensembles", "templates"],
                        "description": "Location of the source ensemble file.",
                    },
                    "source_path": {
                        "type": "string",
                        "description": "Path to the source .ens file, relative to the source location root.",
                    },
                    "dest_path": {
                        "type": "string",
                        "description": (
                            "Destination path for the new ensemble file, relative to the ensembles root. "
                            "Should end in .ens. Parent directories are created automatically."
                        ),
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Whether to overwrite if the destination already exists. Defaults to false.",
                        "default": False,
                    },
                },
                "required": ["source_location", "source_path", "dest_path"],
            },
        ),
        Tool(
            name="create_folder",
            description=(
                "Create a new subfolder within the User Ensembles directory for organising ensembles. "
                "Parent directories are created automatically if needed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path of the new folder to create, relative to the ensembles root.",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="search_docs",
            description=(
                "Full-text search across the processed Reaktor manual text files stored in docs/. "
                "Returns matching lines with chapter and line-number context. "
                "Manuals: 'getting-started' (R6 Getting Started), 'diving-deeper' (R6 Diving Deeper), "
                "'primary' (R6 Building in Primary), 'core' (R6 Building in Core), "
                "'modules' (R5 Modules & Macros Reference), 'core5' (R5.5 Core Reference), "
                "'va-filter' (VA Filter Design 2.1.0), or 'all'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term or phrase (case-insensitive).",
                    },
                    "manual": {
                        "type": "string",
                        "enum": ["all", "getting-started", "diving-deeper", "primary", "core", "modules", "core5", "va-filter"],
                        "description": "Which manual to search. Defaults to 'all'.",
                        "default": "all",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of matching lines to return. Defaults to 20.",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="send_osc",
            description=(
                "Send an OSC message to a running Reaktor instance. "
                "Reaktor must be configured to receive OSC on the target host and port. "
                "Enable OSC in Reaktor via File → OSC Settings. "
                "Use this to control parameters, trigger events, or communicate with any "
                "OSC-enabled ensemble. "
                "Default host/port come from REAKTOR_OSC_HOST / REAKTOR_OSC_PORT env vars "
                f"(currently {OSC_HOST}:{OSC_PORT})."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "OSC address string, must start with '/' (e.g. '/Reaktor/param/Volume').",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": ["number", "string", "boolean"]},
                        "description": "OSC arguments — floats, ints, or strings.",
                        "default": [],
                    },
                    "host": {
                        "type": "string",
                        "description": f"OSC target host. Defaults to REAKTOR_OSC_HOST ({OSC_HOST}).",
                    },
                    "port": {
                        "type": "integer",
                        "description": f"OSC target port. Defaults to REAKTOR_OSC_PORT ({OSC_PORT}).",
                    },
                },
                "required": ["address"],
            },
        ),
        Tool(
            name="get_reaktor_prefs",
            description=(
                "Read Reaktor 6's live preferences — OSC configuration, last-opened ensemble, "
                "MIDI devices, browser paths, and working directories — directly from the "
                "macOS preferences plist. Reaktor does not need to be running. "
                "Useful for checking the actual OSC port before calling send_osc."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="read_doc_chapter",
            description=(
                "Read the full text of a specific chapter from the processed Reaktor manuals. "
                "Use search_docs first to find which chapter contains what you need, "
                "then read the full chapter here. "
                "Accepts a partial chapter name (e.g. 'filter', 'oscillator', 'core-fundamentals')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "manual": {
                        "type": "string",
                        "enum": ["getting-started", "diving-deeper", "primary", "core", "modules", "core5", "va-filter"],
                        "description": "Which manual to read from.",
                    },
                    "chapter": {
                        "type": "string",
                        "description": (
                            "Chapter filename (without .txt) or any substring of it. "
                            "E.g. 'filter', 'chapter-10', 'oscillators'. "
                            "If ambiguous, the first alphabetical match is returned."
                        ),
                    },
                },
                "required": ["manual", "chapter"],
            },
        ),
        Tool(
            name="list_doc_chapters",
            description=(
                "List all available chapters in a Reaktor manual. "
                "Use this to discover what's in a manual before calling read_doc_chapter."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "manual": {
                        "type": "string",
                        "enum": ["getting-started", "diving-deeper", "primary", "core", "modules", "core5", "va-filter"],
                        "description": "Which manual to list chapters for.",
                    },
                },
                "required": ["manual"],
            },
        ),
        Tool(
            name="write_session_note",
            description=(
                "Append a timestamped note to .ai/skills/session-notes.md. "
                "Use this to record important findings, verified module settings, patch patterns, "
                "or techniques discovered during a session so they persist for future sessions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The note body to append. Markdown is supported.",
                    },
                    "heading": {
                        "type": "string",
                        "description": "Optional heading for this note entry.",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="search_user_library",
            description=(
                "Search the Reaktor User Library on the Native Instruments website. "
                "Returns a list of matching community ensembles with their entry IDs, "
                "download counts, and ratings. "
                "Use category='effect', 'instrument', 'blocks', 'other', or 'all'. "
                "Use version='r6' for Reaktor 6 ensembles, 'r5' for Reaktor 5, or 'all'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword (e.g. 'spring reverb', 'fm synth', 'sequencer').",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["all", "effect", "instrument", "blocks", "other"],
                        "description": "Entry category to filter by. Defaults to 'all'.",
                        "default": "all",
                    },
                    "version": {
                        "type": "string",
                        "enum": ["all", "r6", "r5"],
                        "description": "Reaktor version filter. 'r6' = Reaktor 6 only, 'r5' = R5 or lower, 'all' = any. Defaults to 'r6'.",
                        "default": "r6",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_templates",
            description=(
                "List the ensemble template files available in the local templates/ folder. "
                "Templates are minimal .ens files that can be copied as starting points "
                "for new ensembles using copy_ensemble with source_location='templates'."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="open_in_reaktor",
            description=(
                "Open an ensemble file in Reaktor 6. "
                "If Reaktor is already running, the file is loaded into the existing instance. "
                "If Reaktor is not running, it will be launched with the file. "
                "Use this after copy_ensemble to immediately load a new ensemble for editing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "enum": ["factory library", "user library", "ensembles", "templates"],
                        "description": "Which root the file is in.",
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to the .ens file, relative to the chosen root.",
                    },
                },
                "required": ["location", "filepath"],
            },
        ),
        Tool(
            name="call_reaktor_robot",
            description=(
                "Call a Robot Framework keyword on the running Reaktor 6 instance via its built-in "
                "XML-RPC server on port 8270. Reaktor must be running with the Robot server enabled "
                "(feature flag 5d4e071323382551707559765a3322d24e9e3fcd=1 in com.native-instruments.Reaktor 6 prefs). "
                "Core keywords: 'Is Active', 'Get Version', 'Stop Remote Server'. "
                "Project: 'New Ensemble', 'New Rack', 'Save Project', 'Close No Save', 'Open Project', "
                "'Get Project Name', 'Set Project File Name', 'Is Edit Mode', 'Is Rack Mode', 'Is Ensemble Mode', "
                "'Is Touched', 'Touch Project', 'Is Null', 'Process File Load Requests'. "
                "Structure: 'Get Num Modules', 'Get Num Instruments', 'Create Instrument', 'Create Macro', "
                "'Create Core Cell', 'Delete Module', 'Find Module By Label', 'Load Via Structure', "
                "'Structure Unselect All'. "
                "Dialogs: 'Is System Dialog Pending', 'Expect Message Dialog', 'Close No Save'. "
                "Panel: 'Is Panel Visible', 'Is Structure Visible', 'Is Panel Locked', 'Set Panel Locked', "
                "'Panel.Toggle Compact View', 'Panel.Toggle Ports And Wires View', 'Panel.To A View', 'Panel.To B View'. "
                "Undo: 'Can Undo', 'Undo', 'Can Redo', 'Redo'. "
                "IMPORTANT: Keywords that take a structure path (Get Num Modules, Create Instrument, "
                "Create Macro, Create Core Cell, Delete Module, Find Module By Label) require the path "
                "as an array argument. Use [[]] for the root level, e.g. args=[[]] not args=[]. "
                "See .ai/skills/reaktor-robot-skill.md for the complete keyword reference."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "The Robot Framework keyword name to invoke on Reaktor.",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Positional arguments for the keyword.",
                        "default": [],
                    },
                },
                "required": ["keyword"],
            },
        ),
        Tool(
            name="read_ensemble_strings",
            description=(
                "Extract human-readable strings from a Reaktor .ens binary file. "
                "Reaktor stores module names, parameter labels, port descriptions, help text, "
                "preset names, and embedded file paths as plain text inside the binary. "
                "This tool surfaces that content without requiring Reaktor to be running. "
                "Useful as the first step in understanding an unknown ensemble."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "enum": ["factory library", "user library", "ensembles", "templates"],
                        "description": "Which root the .ens file lives in.",
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to the .ens file, relative to the chosen root.",
                    },
                },
                "required": ["location", "filepath"],
            },
        ),
        Tool(
            name="describe_structure",
            description=(
                "Walk the structure tree of the currently-loaded Reaktor ensemble via the "
                "Robot XML-RPC server (port 8270). Shows a hierarchical map of module "
                "containers (instruments, macros) and leaf modules at each path level. "
                "Requires Reaktor running with the Robot feature enabled. "
                "⚠️ Robot causes a crash on File > Open — see reaktor-robot-skill.md before enabling. "
                "Use max_depth to control recursion depth (default 3)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "max_depth": {
                        "type": "integer",
                        "description": "How many levels deep to recurse (default 3, max 6).",
                        "default": 3,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="explain_ensemble",
            description=(
                "Analyse a Reaktor .ens file and produce a structured explanation of what it is "
                "and how it works. Extracts module names, parameter labels, preset names, "
                "port descriptions, and help text from the binary. Does not require Reaktor "
                "to be running. For deeper analysis, follow up with search_docs using "
                "module names from the output, or describe_structure if Robot is available."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "enum": ["factory library", "user library", "ensembles", "templates"],
                        "description": "Which root the .ens file lives in.",
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to the .ens file, relative to the chosen root.",
                    },
                },
                "required": ["location", "filepath"],
            },
        ),
        Tool(
            name="restart_reaktor",
            description=(
                "Quit Reaktor 6 (if running) and reopen it. "
                "Use this after changing preferences that require a restart, such as enabling "
                "the Robot server. Optionally open a specific ensemble file on launch."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ensemble": {
                        "type": "string",
                        "description": "Optional absolute path to a .ens file to open on launch.",
                    },
                },
                "required": [],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    log.info("Tool called: %s | args: %s", name, arguments)

    # ── list_files ─────────────────────────────────────────────────────────────
    if name == "list_files":
        location = arguments.get("location", "")
        subpath = arguments.get("subpath", ".")

        root = get_root(location)
        if root is None:
            return [TextContent(type="text", text=f"Error: unknown location '{location}'. Use 'factory library', 'user library', or 'ensembles'.")]

        target = resolve_safe(root, subpath)
        if target is None:
            return [TextContent(type="text", text="Error: path is outside the allowed root.")]

        if not target.exists():
            return [TextContent(type="text", text=f"Directory not found: {subpath}")]

        if not target.is_dir():
            return [TextContent(type="text", text=f"Not a directory: {subpath}")]

        listing = format_directory(target)
        header = f"[{location.upper()}] {target}\n{'─' * 60}\n"
        log.debug("list_files: %d entries in %s", len(list(target.iterdir())), target)
        return [TextContent(type="text", text=header + listing)]

    # ── get_file_info ──────────────────────────────────────────────────────────
    elif name == "get_file_info":
        location = arguments.get("location", "")
        filepath = arguments.get("filepath", "")

        root = get_root(location)
        if root is None:
            return [TextContent(type="text", text=f"Error: unknown location '{location}'.")]

        target = resolve_safe(root, filepath)
        if target is None:
            return [TextContent(type="text", text="Error: path is outside the allowed root.")]

        if not target.exists():
            return [TextContent(type="text", text=f"File not found: {filepath}")]

        if not target.is_file():
            return [TextContent(type="text", text=f"Not a file: {filepath}")]

        stat = target.stat()
        size_kb = stat.st_size / 1024
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        info = (
            f"Name:     {target.name}\n"
            f"Location: {location}\n"
            f"Path:     {target}\n"
            f"Size:     {size_kb:.1f} KB\n"
            f"Modified: {modified}\n"
            f"Format:   binary (Reaktor proprietary)"
        )
        log.debug("get_file_info: %s", target)
        return [TextContent(type="text", text=info)]

    # ── copy_ensemble ──────────────────────────────────────────────────────────
    elif name == "copy_ensemble":
        source_location = arguments.get("source_location", "")
        source_path = arguments.get("source_path", "")
        dest_path = arguments.get("dest_path", "")
        overwrite = arguments.get("overwrite", False)

        source_root = get_root(source_location)
        if source_root is None:
            return [TextContent(type="text", text=f"Error: unknown source location '{source_location}'.")]

        source = resolve_safe(source_root, source_path)
        if source is None:
            return [TextContent(type="text", text="Error: source path is outside the allowed root.")]

        if not source.exists():
            return [TextContent(type="text", text=f"Source file not found: {source_path}")]

        if not source.is_file():
            return [TextContent(type="text", text=f"Source is not a file: {source_path}")]

        dest = resolve_safe(REAKTOR_USER_ENSEMBLES, dest_path)
        if dest is None:
            return [TextContent(type="text", text="Error: destination path is outside the ensembles root.")]

        if dest.exists() and not overwrite:
            return [TextContent(type="text", text=f"Error: destination already exists: {dest_path}\nUse overwrite=true to replace it.")]

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(dest))
        log.info("copy_ensemble: %s -> %s", source, dest)
        return [TextContent(type="text", text=(
            f"Ensemble created.\n"
            f"  Source:      {source}\n"
            f"  Destination: {dest}"
        ))]

    # ── create_folder ──────────────────────────────────────────────────────────
    elif name == "create_folder":
        folder_path = arguments.get("path", "")

        target = resolve_safe(REAKTOR_USER_ENSEMBLES, folder_path)
        if target is None:
            return [TextContent(type="text", text="Error: path is outside the ensembles root.")]

        if target.exists():
            if target.is_dir():
                return [TextContent(type="text", text=f"Folder already exists: {target}")]
            return [TextContent(type="text", text=f"Error: a file already exists at that path: {folder_path}")]

        target.mkdir(parents=True, exist_ok=True)
        log.info("create_folder: %s", target)
        return [TextContent(type="text", text=f"Folder created: {target}")]

    # ── search_docs ────────────────────────────────────────────────────────────
    elif name == "search_docs":
        query = arguments.get("query", "")
        manual = arguments.get("manual", "all").lower()
        max_results = int(arguments.get("max_results", 20))

        if not query:
            return [TextContent(type="text", text="Error: query must not be empty.")]

        if manual == "all":
            search_dirs = list(DOCS_MANUALS.items())
        elif manual in DOCS_MANUALS:
            search_dirs = [(manual, DOCS_MANUALS[manual])]
        else:
            return [TextContent(type="text", text=f"Error: unknown manual '{manual}'. Use 'primary', 'core', 'modules', or 'all'.")]

        results = []
        query_lower = query.lower()

        for manual_name, doc_dir in search_dirs:
            if not doc_dir.exists():
                continue
            for txt_file in sorted(doc_dir.glob("*.txt")):
                for line_no, line in enumerate(txt_file.read_text(errors="replace").splitlines(), start=1):
                    if query_lower in line.lower():
                        results.append((manual_name, txt_file.stem, line_no, line.strip()))
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        if not results:
            return [TextContent(type="text", text=f"No results found for '{query}'.")]

        out = [f"Search: '{query}' — {len(results)} match(es)\n"]
        for manual_name, chapter, line_no, line in results:
            out.append(f"[{manual_name}] {chapter}  (line {line_no})")
            out.append(f"  {line}")
        log.debug("search_docs: '%s' → %d results", query, len(results))
        return [TextContent(type="text", text="\n".join(out))]

    # ── send_osc ───────────────────────────────────────────────────────────────
    elif name == "send_osc":
        address = arguments.get("address", "")
        args = arguments.get("args", [])
        host = arguments.get("host") or OSC_HOST
        port = int(arguments.get("port") or OSC_PORT)

        if not address.startswith("/"):
            return [TextContent(type="text", text="Error: OSC address must start with '/'.")]

        try:
            client = osc_udp_client.SimpleUDPClient(host, port)
            if not args:
                client.send_message(address, None)
            elif len(args) == 1:
                client.send_message(address, args[0])
            else:
                client.send_message(address, args)
            log.info("send_osc: %s %s → %s:%d", address, args, host, port)
            return [TextContent(type="text", text=f"OSC sent: {address} {args} → {host}:{port}")]
        except Exception as e:
            log.error("send_osc error: %s", e)
            return [TextContent(type="text", text=f"Error sending OSC: {e}")]

    # ── get_reaktor_prefs ──────────────────────────────────────────────────────
    elif name == "get_reaktor_prefs":
        if not REAKTOR_PREFS_PLIST.exists():
            return [TextContent(type="text", text=f"Reaktor preferences not found at {REAKTOR_PREFS_PLIST}")]

        try:
            # Use plutil to read the live (possibly cached) preferences via the daemon
            result = subprocess.run(
                ["plutil", "-convert", "json", "-o", "-", str(REAKTOR_PREFS_PLIST)],
                capture_output=True, text=True, timeout=5,
            )
            prefs = json.loads(result.stdout)
        except Exception as e:
            log.warning("plutil failed (%s), falling back to plistlib", e)
            with open(REAKTOR_PREFS_PLIST, "rb") as f:
                prefs = plistlib.load(f)

        # ── OSC ────────────────────────────────────────────────────────────────
        osc_running = bool(prefs.get("OscWasRunning", 0))
        osc_port    = prefs.get("OscLocalPort", "?")
        osc_ident   = prefs.get("OscLocalIdent", "?")
        targets = [v for k, v in sorted(prefs.items()) if k.startswith("OscTarget")]

        osc_section = (
            f"OSC\n"
            f"  Enabled:   {'YES ✓' if osc_running else 'NO  (enable via Reaktor: File → OSC Settings)'}\n"
            f"  Receive port: {osc_port}\n"
            f"  Identity:  {osc_ident}\n"
        )
        if targets:
            osc_section += "  Send targets: " + ", ".join(targets) + "\n"

        # ── last opened ensemble ───────────────────────────────────────────────
        last_ens = prefs.get("File2_v2", prefs.get("File1_v2", ""))
        last_section = f"\nLast opened ensemble\n  {last_ens or '(none)'}\n"

        # ── MIDI devices ───────────────────────────────────────────────────────
        midi_lines = []
        i = 0
        while f"AB2 MidiDevice{i} Name" in prefs:
            name = prefs[f"AB2 MidiDevice{i} Name"]
            kind = "IN " if prefs.get(f"AB2 MidiDevice{i} Type", -1) == 0 else "OUT"
            midi_lines.append(f"  {kind}  {name}")
            i += 1
        midi_section = "\nMIDI devices\n" + ("\n".join(midi_lines) if midi_lines else "  (none)") + "\n"

        # ── working dirs ───────────────────────────────────────────────────────
        dirs_section = (
            f"\nWorking directories\n"
            f"  User Library:  {prefs.get('InstrumentWorkDir_v2', '?')}\n"
            f"  Factory:       {prefs.get('FactoryContentDir_v2', '?')}\n"
        )

        log.debug("get_reaktor_prefs: osc_port=%s osc_running=%s", osc_port, osc_running)
        return [TextContent(type="text", text=osc_section + last_section + midi_section + dirs_section)]

    # ── read_doc_chapter ───────────────────────────────────────────────────────
    elif name == "read_doc_chapter":
        manual = arguments.get("manual", "").lower()
        chapter = arguments.get("chapter", "").lower()

        if manual not in DOCS_MANUALS:
            return [TextContent(type="text", text=f"Error: unknown manual '{manual}'. Use 'primary', 'core', or 'modules'.")]

        doc_dir = DOCS_MANUALS[manual]
        if not doc_dir.exists():
            return [TextContent(type="text", text=f"Manual directory not found: {doc_dir}")]

        candidates = sorted(p for p in doc_dir.glob("*.txt") if chapter in p.stem.lower())
        if not candidates:
            available = ", ".join(p.stem for p in sorted(doc_dir.glob("*.txt")))
            return [TextContent(type="text", text=f"No chapter matching '{chapter}' in [{manual}].\nAvailable: {available}")]

        target = candidates[0]
        text = target.read_text(errors="replace")
        header = f"[{manual}] {target.stem}\n{'─' * 60}\n"
        log.debug("read_doc_chapter: %s", target)
        return [TextContent(type="text", text=header + text)]

    # ── list_doc_chapters ──────────────────────────────────────────────────────
    elif name == "list_doc_chapters":
        manual = arguments.get("manual", "").lower()

        if manual not in DOCS_MANUALS:
            return [TextContent(type="text", text=f"Error: unknown manual '{manual}'. Use 'primary', 'core', or 'modules'.")]

        doc_dir = DOCS_MANUALS[manual]
        if not doc_dir.exists():
            return [TextContent(type="text", text=f"Manual directory not found: {doc_dir}")]

        chapters = sorted(p.stem for p in doc_dir.glob("*.txt"))
        if not chapters:
            return [TextContent(type="text", text=f"No chapters found in [{manual}].")]

        lines = [f"[{manual}] — {len(chapters)} chapter(s)\n"]
        lines += [f"  {ch}" for ch in chapters]
        return [TextContent(type="text", text="\n".join(lines))]

    # ── write_session_note ─────────────────────────────────────────────────────
    elif name == "write_session_note":
        content = arguments.get("content", "").strip()
        heading = arguments.get("heading", "").strip()

        if not content:
            return [TextContent(type="text", text="Error: content must not be empty.")]

        notes_path = Path(__file__).parent / ".ai" / "skills" / "session-notes.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        entry_parts = [f"\n---\n\n### {heading}\n\n_{timestamp}_\n\n{content}\n" if heading
                       else f"\n---\n\n_{timestamp}_\n\n{content}\n"]
        entry = "".join(entry_parts)

        with open(notes_path, "a", encoding="utf-8") as f:
            f.write(entry)

        log.info("write_session_note: %d chars appended to %s", len(entry), notes_path)
        return [TextContent(type="text", text=f"Note appended to {notes_path.name}:\n{entry.strip()}")]

    # ── search_user_library ────────────────────────────────────────────────────
    elif name == "search_user_library":
        query    = arguments.get("query", "").strip()
        category = arguments.get("category", "all").lower()
        version  = arguments.get("version", "r6").lower()

        if not query:
            return [TextContent(type="text", text="Error: query must not be empty.")]

        version_map = {"r6": "3", "r5": "1", "all": "all"}
        ver_param = version_map.get(version, "3")

        url = (
            f"https://www.native-instruments.com/en/reaktor-community/reaktor-user-library"
            f"/{category}/all/all/all/{query}/latest/1/{ver_param}/"
        )

        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                })
            html = resp.text
            status = resp.status_code
        except Exception as e:
            log.error("search_user_library fetch error: %s", e)
            return [TextContent(type="text", text=f"Error fetching Reaktor User Library: {e}\n\nOpen manually: {url}")]

        if status == 403:
            return [TextContent(type="text", text=(
                f"The NI website blocked automated access (HTTP 403).\n\n"
                f"Open this URL in your browser to see results:\n{url}"
            ))]

        if status != 200:
            return [TextContent(type="text", text=f"Unexpected HTTP {status} from NI website.\n\nURL: {url}")]

        # Extract entry IDs and names from the listing HTML
        entry_ids = list(dict.fromkeys(re.findall(r"/entry/show/(\d+)/", html)))

        if not entry_ids:
            return [TextContent(type="text", text=f"No results found for '{query}'.\n\nURL: {url}")]

        results = []
        for eid in entry_ids[:20]:
            idx = html.find(f"/entry/show/{eid}/")
            snippet = html[max(0, idx - 300):idx + 600]
            title_match = re.search(r'<a[^>]+/entry/show/' + eid + r'/[^>]*>\s*([^<]{3,100})\s*</a>', snippet)
            title = title_match.group(1).strip() if title_match else "(unknown)"
            dl_match = re.search(r'(\d[\d,]+)\s*(?:downloads?|Downloads?)', snippet)
            downloads = dl_match.group(1) if dl_match else "?"
            results.append(f"  ID {eid:>7}  {title}  [{downloads} downloads]")

        header = f"Reaktor User Library — '{query}' ({len(results)} result(s))\n{'─' * 60}\n"
        footer = f"\n\nEntry URL pattern:\nhttps://www.native-instruments.com/en/reaktor-community/reaktor-user-library/entry/show/<ID>/"
        log.info("search_user_library: '%s' → %d results", query, len(results))
        return [TextContent(type="text", text=header + "\n".join(results) + footer)]

    # ── list_templates ────────────────────────────────────────────────────────
    elif name == "list_templates":
        if not REAKTOR_TEMPLATES.exists():
            return [TextContent(type="text", text=f"Templates directory not found: {REAKTOR_TEMPLATES}")]

        listing = format_directory(REAKTOR_TEMPLATES)
        header = f"[TEMPLATES] {REAKTOR_TEMPLATES}\n{'─' * 60}\n"
        log.debug("list_templates: %s", REAKTOR_TEMPLATES)
        return [TextContent(type="text", text=header + listing)]

    # ── open_in_reaktor ───────────────────────────────────────────────────────
    elif name == "open_in_reaktor":
        location = arguments.get("location", "")
        filepath = arguments.get("filepath", "")

        root = get_root(location)
        if root is None:
            return [TextContent(type="text", text=f"Error: unknown location '{location}'.")]

        target = resolve_safe(root, filepath)
        if target is None:
            return [TextContent(type="text", text="Error: path is outside the allowed root.")]

        if not target.exists():
            return [TextContent(type="text", text=f"File not found: {filepath}")]

        if not target.is_file():
            return [TextContent(type="text", text=f"Not a file: {filepath}")]

        try:
            if REAKTOR_APP.exists():
                subprocess.Popen(["open", "-a", str(REAKTOR_APP), str(target)])
            else:
                subprocess.Popen(["open", "-a", "Reaktor 6", str(target)])
            log.info("open_in_reaktor: %s", target)
            return [TextContent(type="text", text=f"Opening in Reaktor 6: {target}")]
        except Exception as e:
            log.error("open_in_reaktor error: %s", e)
            return [TextContent(type="text", text=f"Error opening file: {e}")]

    # ── call_reaktor_robot ────────────────────────────────────────────────────
    elif name == "call_reaktor_robot":
        import xmlrpc.client

        keyword = arguments.get("keyword", "")
        args = arguments.get("args", [])

        if not keyword:
            return [TextContent(type="text", text="Error: 'keyword' is required.")]

        robot_url = "http://127.0.0.1:8270"
        try:
            proxy = xmlrpc.client.ServerProxy(robot_url, allow_none=True)
            result = proxy.run_keyword(keyword, args, {})
            log.info("call_reaktor_robot: %s(%s) → %s", keyword, args, result)
            status = result.get("status", "UNKNOWN") if isinstance(result, dict) else str(result)
            ret = result.get("return", "") if isinstance(result, dict) else ""
            error = result.get("error", "") if isinstance(result, dict) else ""
            if status == "PASS":
                text = f"OK: {keyword}\nReturn: {ret}" if ret != "" else f"OK: {keyword}"
            else:
                text = f"FAIL: {keyword}\nError: {error}"
            return [TextContent(type="text", text=text)]
        except ConnectionRefusedError:
            return [TextContent(type="text", text=(
                "Error: Reaktor Robot server not reachable on port 8270. "
                "Ensure Reaktor is running with the Robot feature enabled."
            ))]
        except Exception as e:
            log.error("call_reaktor_robot error: %s", e)
            return [TextContent(type="text", text=f"Error: {e}")]

    # ── restart_reaktor ───────────────────────────────────────────────────────
    elif name == "restart_reaktor":
        ensemble = arguments.get("ensemble", "")
        try:
            # Quit gracefully via AppleScript (no-op if not running)
            subprocess.run(
                ["osascript", "-e", 'tell application "Reaktor 6" to quit'],
                timeout=10,
            )
            import time
            time.sleep(2)
            # Reopen
            if ensemble:
                cmd = ["open", "-a", str(REAKTOR_APP), ensemble] if REAKTOR_APP.exists() else ["open", "-a", "Reaktor 6", ensemble]
            else:
                cmd = ["open", str(REAKTOR_APP)] if REAKTOR_APP.exists() else ["open", "-a", "Reaktor 6"]
            subprocess.Popen(cmd)
            msg = f"Reaktor 6 restarted" + (f" with {ensemble}" if ensemble else "")
            log.info("restart_reaktor: %s", msg)
            return [TextContent(type="text", text=msg)]
        except Exception as e:
            log.error("restart_reaktor error: %s", e)
            return [TextContent(type="text", text=f"Error restarting Reaktor: {e}")]

    # ── read_ensemble_strings ─────────────────────────────────────────────────
    elif name == "read_ensemble_strings":
        location = arguments.get("location", "")
        filepath = arguments.get("filepath", "")

        root = get_root(location)
        if root is None:
            return [TextContent(type="text", text=f"Error: unknown location '{location}'.")]

        target = resolve_safe(root, filepath)
        if target is None:
            return [TextContent(type="text", text="Error: path is outside the allowed root.")]

        if not target.exists():
            return [TextContent(type="text", text=f"File not found: {filepath}")]

        if not target.is_file():
            return [TextContent(type="text", text=f"Not a file: {filepath}")]

        data = target.read_bytes()
        extracted = _extract_ens_strings(data)

        lines = [f"Strings extracted from: {target.name}  ({target.stat().st_size / 1024:.1f} KB)\n{'─' * 60}"]

        if extracted["labels"]:
            lines.append(f"\nLABELS  ({len(extracted['labels'])} items)")
            lines.append("  " + "\n  ".join(extracted["labels"]))

        if extracted["descriptions"]:
            lines.append(f"\nDESCRIPTIONS / HELP TEXT  ({len(extracted['descriptions'])} items)")
            for d in extracted["descriptions"]:
                lines.append(f"  • {d}")

        if extracted["osc_hints"]:
            lines.append(f"\nOSC ADDRESS HINTS")
            for o in extracted["osc_hints"]:
                lines.append(f"  {o}")

        if extracted["file_refs"]:
            lines.append(f"\nEMBEDDED FILE REFERENCES")
            for f_ref in extracted["file_refs"]:
                lines.append(f"  {f_ref}")

        if not any(extracted.values()):
            lines.append("No readable strings found.")

        log.debug("read_ensemble_strings: %s → %d labels, %d descriptions",
                  target.name, len(extracted["labels"]), len(extracted["descriptions"]))
        return [TextContent(type="text", text="\n".join(lines))]

    # ── describe_structure ────────────────────────────────────────────────────
    elif name == "describe_structure":
        import xmlrpc.client as _xmlrpc

        max_depth = min(int(arguments.get("max_depth", 3)), 6)
        robot_url = "http://127.0.0.1:8270"

        def _rk(proxy, keyword, path):
            """Call a Robot structure keyword that takes a single path argument."""
            try:
                r = proxy.run_keyword(keyword, [path], {})
                if isinstance(r, dict) and r.get("status") == "PASS":
                    return r.get("return")
            except Exception:
                pass
            return None

        def _walk(proxy, path, depth, max_d, lines, prefix):
            if depth > max_d:
                lines.append(f"{prefix}  … (max depth reached)")
                return
            n = _rk(proxy, "Get Num Modules", path)
            if n is None:
                return
            if n == 0 and depth > 0:
                return
            for i in range(min(n, 25)):
                child_path = path + [str(i)]
                child_n = _rk(proxy, "Get Num Modules", child_path) or 0
                child_instr = _rk(proxy, "Get Num Instruments", child_path) or 0
                if child_n > 0:
                    kind = "Instrument" if child_instr > 0 else "Macro/Group"
                    lines.append(f"{prefix}📦 [{i}]  {kind}  ({child_n} children)")
                    if depth < max_d:
                        _walk(proxy, child_path, depth + 1, max_d, lines, prefix + "    ")
                else:
                    lines.append(f"{prefix}◻  [{i}]  leaf module")
            if n > 25:
                lines.append(f"{prefix}  … ({n - 25} more modules not shown)")

        try:
            proxy = _xmlrpc.ServerProxy(robot_url, allow_none=True)

            active = proxy.run_keyword("Is Active", [], {})
            if not isinstance(active, dict) or active.get("status") != "PASS":
                return [TextContent(type="text", text="Error: Reaktor Robot server not responding.")]

            project_name = _rk(proxy, "Get Project Name", []) or "(unknown)"
            is_edit = proxy.run_keyword("Is Edit Mode", [], {}).get("return", False)
            is_touched = proxy.run_keyword("Is Touched", [], {}).get("return", False)
            root_n = _rk(proxy, "Get Num Modules", []) or 0

            lines = [
                f"Structure: {project_name}",
                f"Edit mode: {'YES' if is_edit else 'no'}   Unsaved changes: {'YES' if is_touched else 'no'}",
                f"Root modules: {root_n}",
                "─" * 60,
            ]
            _walk(proxy, [], 0, max_depth, lines, "")
            log.info("describe_structure: %s  root_n=%d", project_name, root_n)
            return [TextContent(type="text", text="\n".join(lines))]

        except ConnectionRefusedError:
            return [TextContent(type="text", text=(
                "Error: Reaktor Robot server not reachable on port 8270. "
                "Ensure Reaktor is running with the Robot feature enabled."
            ))]
        except Exception as e:
            log.error("describe_structure error: %s", e)
            return [TextContent(type="text", text=f"Error: {e}")]

    # ── explain_ensemble ──────────────────────────────────────────────────────
    elif name == "explain_ensemble":
        location = arguments.get("location", "")
        filepath = arguments.get("filepath", "")

        root = get_root(location)
        if root is None:
            return [TextContent(type="text", text=f"Error: unknown location '{location}'.")]

        target = resolve_safe(root, filepath)
        if target is None:
            return [TextContent(type="text", text="Error: path is outside the allowed root.")]

        if not target.exists():
            return [TextContent(type="text", text=f"File not found: {filepath}")]

        if not target.is_file():
            return [TextContent(type="text", text=f"Not a file: {filepath}")]

        data = target.read_bytes()
        stat = target.stat()
        size_kb = stat.st_size / 1024
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        extracted = _extract_ens_strings(data)

        labels = extracted["labels"]
        descriptions = extracted["descriptions"]
        file_refs = extracted["file_refs"]
        osc_hints = extracted["osc_hints"]

        # ── Classify labels into categories ───────────────────────────────────
        import re as _re

        def _clean_label(s: str) -> bool:
            """Return True if s looks like a genuine UI label (no binary noise)."""
            return bool(_re.match(r'^[\w\s.()\-/\'&!,+#%°]+$', s))

        def _looks_like_word(s: str) -> bool:
            """Return True if s follows a recognizable Reaktor label word pattern.

            Rejects Base64-like mixed-case strings (e.g. 'VPAPpVi', 'AyxZMxL').
            Accepts: Title case ('Attack'), ALL-CAPS ('ADSR'), acronym+digit ('LFO1'),
            compound with separator ('Bi/Uni', 'Key Tracking').
            """
            if not s:
                return False
            # Compound labels with space/slash/dash — check each token
            tokens = _re.split(r'[ /\-]', s)
            for tok in tokens:
                if not tok:
                    continue
                # Each token: Title Case, ALL_CAPS, all lowercase, or acronym+digit
                if not (_re.match(r'^[A-Z][a-z]+\d*$', tok)   # Title: "Attack"
                        or _re.match(r'^[A-Z]{2,6}\d{0,2}$', tok)  # Acronym: "LFO1"
                        or _re.match(r'^[a-z]{2,}$', tok)           # lower: "reverb"
                        or _re.match(r'^\d{1,3}$', tok)):            # digits: "4"
                    return False
            return True

        module_names = [l for l in labels
                        if len(l) >= 6 and ' ' in l and _clean_label(l)
                        and l[0].isupper()
                        and not l.endswith('.')
                        and not _re.match(r'^\d', l)]
        # Params: only accept strings that follow a recognisable label case pattern
        param_names = [l for l in labels
                       if 4 <= len(l) <= 22
                       and l[0].isupper()
                       and _re.match(r'^[A-Za-z][A-Za-z\s/\-]+$', l)
                       and _looks_like_word(l)
                       and (
                           ' ' not in l
                           or all(len(w) >= 2 for w in l.split())
                       )
                       and not _re.match(r'^[A-Z]{4,}$', l)]
        preset_names = [l for l in module_names
                        if not l.endswith('.')
                        and not any(kw in l.lower() for kw in
                                    ('bento', 'rounds', 'blocks', 'modul', 'port', 'panel',
                                     'instrument', 'macro', 'ensemble', 'file', 'core',
                                     'channel', 'velocity', 'tracking', 'control', 'output',
                                     'input', 'trigger', 'feedback', 'mode', 'type', 'data',
                                     'display', 'value', 'select', 'button', 'knob', 'scale',
                                     'range', 'pitch', 'bend', 'glide', 'priority', 'util',
                                     'note in', 'note out', 'midi', 'init', 'enable'))]
        preset_names = [l for l in module_names
                        if not any(kw in l.lower() for kw in
                                   ('bento', 'rounds', 'blocks', 'modul', 'port', 'panel',
                                    'instrument', 'macro', 'ensemble', 'file', 'core'))]
        component_names = [l for l in module_names
                           if any(kw in l.lower() for kw in
                                  ('bento', 'rounds', 'blocks', 'vco', 'vcf', 'vca', 'lfo',
                                   'adsr', 'env', 'osc', 'filter', 'amp', 'delay', 'reverb',
                                   'chorus', 'distort', 'compress', 'eq ', 'synth', 'sampler',
                                   'sequencer', 'step', 'arp', 'mixer', 'modulator'))]

        # ── Infer ensemble type from labels ───────────────────────────────────
        all_text = " ".join(labels + descriptions).lower()
        type_hints = []
        if any(kw in all_text for kw in ("reverb", "delay", "chorus", "flanger", "phaser", "distort", "compress")):
            type_hints.append("effects processor")
        if any(kw in all_text for kw in ("vco", "oscillator", "sawtooth", "wavetable", "fm", "adsr")):
            type_hints.append("synthesizer")
        if any(kw in all_text for kw in ("sequencer", "step", "pattern", "arp", "clock", "gate")):
            type_hints.append("sequencer/arpeggiator")
        if any(kw in all_text for kw in ("sampler", "sample", "playback", "loop")):
            type_hints.append("sampler")
        if any(kw in all_text for kw in ("lfo", "envelope", "modulation", "modulator")):
            type_hints.append("has modulation")
        ensemble_type = " + ".join(type_hints) if type_hints else "unknown type"

        # ── Assemble output ───────────────────────────────────────────────────
        lines = [
            f"Ensemble: {target.stem}",
            f"File:     {target}",
            f"Size:     {size_kb:.1f} KB   Modified: {modified}",
            f"Type:     {ensemble_type}",
            "─" * 60,
        ]

        if component_names:
            lines.append(f"\nCOMPONENTS  (named module/instrument blocks)")
            for c in list(dict.fromkeys(component_names))[:20]:
                lines.append(f"  • {c}")

        if param_names:
            lines.append(f"\nPARAMETERS / CONTROLS  (knobs, buttons, sliders)")
            # Deduplicate and show top-level ones first (shorter names first)
            params_sorted = sorted(set(param_names), key=len)[:40]
            lines.append("  " + ",  ".join(params_sorted))

        if preset_names and len(preset_names) > len(component_names):
            # Only show preset section if there are clearly preset names
            preset_display = [p for p in list(dict.fromkeys(preset_names))
                              if p not in component_names][:25]
            if preset_display:
                lines.append(f"\nPRESETS / SNAPSHOTS")
                lines.append("  " + ",  ".join(preset_display))

        if descriptions:
            lines.append(f"\nHELP TEXT & PORT DESCRIPTIONS  (from embedded documentation)")
            for d in descriptions[:15]:
                lines.append(f"  • {d}")
            if len(descriptions) > 15:
                lines.append(f"  … ({len(descriptions) - 15} more — use read_ensemble_strings for full list)")

        if osc_hints:
            lines.append(f"\nOSC ADDRESSES FOUND")
            for o in osc_hints:
                lines.append(f"  {o}")

        if file_refs:
            lines.append(f"\nEMBEDDED FILE REFERENCES  (samples, sub-modules)")
            for f_ref in file_refs[:10]:
                lines.append(f"  {f_ref}")
            if len(file_refs) > 10:
                lines.append(f"  … ({len(file_refs) - 10} more)")

        lines.append(f"\n{'─' * 60}")
        lines.append("To go deeper:")
        lines.append("  search_docs — look up any component or parameter name in the Reaktor manuals")
        lines.append("  read_ensemble_strings — full raw string dump from this file")
        lines.append("  describe_structure — live module tree (requires Reaktor + Robot on port 8270)")

        log.info("explain_ensemble: %s  type=%s  labels=%d", target.name, ensemble_type, len(labels))
        return [TextContent(type="text", text="\n".join(lines))]

    # ── unknown ────────────────────────────────────────────────────────────────
    log.error("Unknown tool: %s", name)
    return [TextContent(type="text", text=f"Error: unknown tool '{name}'")]


# ── Entry point ────────────────────────────────────────────────────────────────
async def main():
    log.info("reaktor-tools MCP server starting")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
    log.info("reaktor-tools MCP server stopped")


if __name__ == "__main__":
    asyncio.run(main())