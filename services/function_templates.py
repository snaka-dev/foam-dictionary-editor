# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free: OpenFOAM's function-object templates, read and filled in.

Behind Tools > Add Function Object…. Every installation ships a template for
each common function object -- probes, line graphs, forces, yPlus, … -- under
``etc/caseDicts/postProcessing`` (in Foundation-dev a symlink to the newer
``functions`` directory), each one a short description, the few entries a
user sets, and ``#includeEtc`` lines for everything else::

    points  (<points>);                 // Foundation 9+: a typed blank
    fields  (<fieldNames>);
    #includeEtc "caseDicts/functions/probes/probes.cfg"

    fields (p U);                       // OpenCFD, Foundation 7-8: an example
    probeLocations ((0 0 0));

The two forks name and shape the same function differently (OpenCFD's
``probeLocations`` is Foundation's ``points``; its ``singleGraph`` is
Foundation's ``graphUniform``, which adds ``nPoints``), and both change
between releases. So FoDE never has its own idea of a probes dictionary: it
reads the user's installation and builds the form from the template's own
entries, the kind of each inferred from Foundation's ``<placeholder>`` or
from the key and the example value -- a list of field names, a point, a
number -- with anything it cannot type (OpenCFD's nested ``surfaces``)
edited as text.

The result is written the way ``foamGet`` and the tutorials do it: the
template copied to ``system/<name>`` with only the edited values changed, and
``#includeFunc <name>`` in controlDict's ``functions`` -- both forks look in
the case's ``system/`` before their own ``etc`` for a function by name.
"""
from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Iterable, Mapping, Sequence

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser

TEMPLATE_SUBDIR = os.path.join("caseDicts", "postProcessing")

# What an entry asks for, and so which input the form gives it.
KINDS = (
    "fields",  # a list of field names: (p U)
    "field",  # one field name
    "patches",  # a list of patch names
    "patch",  # one patch name
    "points",  # a list of points: ((0 0 0) (1 0 0))
    "vector",  # one point or direction: (0 0 1)
    "number",
    "bool",
    "word",
    "surfaces",  # OpenCFD's sampled-surfaces list: cutting planes + the rest
    "text",  # anything else, edited as written
)

# Between the two parts of a "surfaces" value: the cutting-plane rows and
# the other members, kept as written. A control character, so no text a
# user types can be mistaken for it.
SURFACES_SEPARATOR = "\x1e"

# OpenCFD's surfaces.cfg defines these for its template's members to refer
# to ($x, $origin, …), and $cuttingPlane's own defaults. Used only to show a
# plane's starting point and normal in the form; what is written refers to
# nothing, giving both explicitly.
_CFG_VECTORS = {"x": "1 0 0", "y": "0 1 0", "z": "0 0 1", "origin": "0 0 0"}
_CUTTING_PLANE_DEFAULT = ("0 0 0", "1 0 0")

_PLACEHOLDER_RE = re.compile(r"<([^<>]+)>")
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.:+-]*")
_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_NUMBER_RE = re.compile(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?")
# Three components, none of them bracketed: "((0 0 0))" is a list of one
# point, not a point, and must not match.
_VECTOR_RE = re.compile(r"\(\s*([^\s()]+)\s+([^\s()]+)\s+([^\s()]+)\s*\)")

# Placeholder names that stand for a point or direction, a number. The rest
# is told apart by what the name contains (field, patch, point).
_VECTOR_NAMES = frozenset(
    {"point", "centre", "center", "cofr", "pitchaxis", "normal", "coordinate",
     "liftdir", "dragdir", "direction", "origin", "axis", "vector"}
)
_NUMBER_NAMES = frozenset(
    {"number", "npoints", "scalar", "value", "rhoinf", "maguinf", "lref", "aref",
     "rho", "cp", "pr", "prt", "maxdistance", "clocktime", "label", "integer"}
)
_BOOL_WORDS = frozenset({"true", "false", "yes", "no", "on", "off"})

# Entries that are plumbing, not settings: which function object this is and
# the library it lives in. Shown in the preview, never in the form.
FIXED_KEYS = frozenset({"type", "libs", "functionObjectLibs"})

# The values a control entry can take, in both forks, for the form to offer.
CONTROL_CHOICES = (
    "timeStep", "writeTime", "runTime", "adjustableRunTime", "clockTime",
    "cpuTime", "onEnd", "none",
)
CHOICES: dict[str, tuple[str, ...]] = {
    "writeControl": CONTROL_CHOICES,
    "executeControl": CONTROL_CHOICES,
    "outputControl": CONTROL_CHOICES,
}


@dataclasses.dataclass(frozen=True)
class FunctionTemplate:
    category: str  # the folder: probes, graphs, forces, …
    name: str  # the file: probes, graphUniform, …
    path: str
    description: str


@dataclasses.dataclass(frozen=True)
class TemplateEntry:
    """One entry of a template the user sets.

    ``value`` is the text after the key, without ``;`` or comment.
    ``required`` marks a Foundation ``<placeholder>``: the file is not
    usable until it is replaced. ``hint`` is the entry's own comment.
    """

    key: str
    kind: str
    value: str
    required: bool
    hint: str
    first_line: int  # 1-based, inclusive
    last_line: int
    # The comment after the ``;``, with its leading spaces, written back as
    # it was. Kept whole rather than found again later: a comment may itself
    # hold a ";" ("Far field density; e.g., 1.225").
    comment: str = ""


@dataclasses.dataclass(frozen=True)
class ParsedTemplate:
    """A template's text and its settable entries.

    ``formable`` is False for a template a form cannot describe -- one with
    embedded C++ (a ``codeStream``), which reads as repeated or code-like
    "keys". Such a template is edited as a whole, as text.
    """

    text: str
    entries: tuple[TemplateEntry, ...]
    formable: bool = True


def template_root(etc_dirs: Iterable[str | os.PathLike]) -> str | None:
    """The first ``etc/caseDicts/postProcessing`` among *etc_dirs*, or None."""
    for etc in etc_dirs:
        root = os.path.join(etc, TEMPLATE_SUBDIR)
        if os.path.isdir(root):
            return root
    return None


def _description(text: str) -> str:
    m = re.search(r"Description\s*\n(.*?)(?:\n\s*\n|\\\*)", text, re.S)
    return " ".join(m.group(1).split()) if m else ""


def list_templates(root: str) -> list[FunctionTemplate]:
    """Every template under *root*, by category then name.

    ``.cfg`` files are the fixed parts the templates include, not templates.
    """
    found = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in filenames:
            if name.startswith(".") or name.endswith((".cfg", "~", ".orig")):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            category = rel.split(os.sep)[0] if os.sep in rel else ""
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    description = _description(f.read(4096))
            except OSError:
                continue
            found.append(FunctionTemplate(category, name, path, description))
    return sorted(found, key=lambda t: (t.category.lower(), t.name.lower()))


def _value_text(lines: list[str], node: FoamNode) -> str:
    text = "\n".join(lines[node.source_line - 1 : node.source_end_line])
    comment = node.inline_comment
    if comment and text.endswith(comment):
        text = text[: -len(comment)]
    text = text.strip()
    if text.endswith(";"):
        text = text[:-1].rstrip()
    m = re.match(re.escape(node.name) + r"\s*", text)
    return text[m.end():] if m else text


def _kind_from_placeholder(key: str, node: FoamNode, value: str, names: list[str]) -> str:
    lowered = [n.lower().replace(" ", "").replace("_", "") for n in names]
    is_list = value.startswith("(")
    joined = " ".join(lowered)
    if "field" in joined:
        return "fields" if is_list or joined.endswith("s") else "field"
    if "patch" in joined:
        return "patches" if is_list or joined.endswith("names") else "patch"
    if is_list and "point" in joined:
        return "points"
    if not is_list and len(lowered) == 1:
        name = lowered[0]
        if name in _VECTOR_NAMES or name.endswith(("dir", "axis", "point")):
            return "vector"
        if name in _NUMBER_NAMES:
            return "number"
    # The placeholder's name does not say (field <specieName>): the key may.
    return _kind_from_example(key, node, "")


def _kind_from_example(key: str, node: FoamNode, value: str) -> str:
    if key in ("fields", "fieldNames"):
        return "fields"
    if key in ("patches", "patchNames"):
        return "patches"
    if key == "field":
        return "field"
    if key == "patch":
        return "patch"
    if node.node_type in ("int", "scalar"):
        return "number"
    if node.node_type == "bool" or value in _BOOL_WORDS:
        return "bool"
    if node.node_type == "vector" or _VECTOR_RE.fullmatch(value):
        return "vector"
    inner = value[1:-1].strip() if value.startswith("(") and value.endswith(")") else None
    if inner is not None and inner and _VECTOR_RE.sub("", inner).strip() == "":
        return "points"
    if node.node_type == "word" and _WORD_RE.fullmatch(value):
        return "word"
    return "text"



def _is_cutting_plane(member: FoamNode) -> bool:
    for c in member.children:
        if c.node_type == "macro_entry" and str(c.value).lstrip("$") == "cuttingPlane":
            return True
        if c.name == "type" and str(c.value) in ("cuttingPlane", "plane"):
            return True
    return False


def _plane_row(member: FoamNode) -> str:
    """``name  px py pz  nx ny nz`` for a cutting-plane member."""
    point, normal = _CUTTING_PLANE_DEFAULT
    holder = next(
        (c for c in member.children if c.name == "pointAndNormalDict"), member
    )
    for c in holder.children:
        if c.name in ("basePoint", "point", "normalVector", "normal"):
            if c.node_type == "vector":
                value = " ".join(f"{v:g}" for v in c.value)
            else:
                value = _CFG_VECTORS.get(str(c.value).lstrip("$"), "")
            if not value:
                continue
            if c.name in ("basePoint", "point"):
                point = value
            else:
                normal = value
    return f"{member.name}  {point}  {normal}"


def _surfaces_value(lines: list[str], node: FoamNode) -> str | None:
    """The "surfaces" kind's value, or None if *node* is not such a list."""
    if node.node_type != "named_dict_list":
        return None
    members = [m for m in node.children if m.name and m.source_line > 0]
    if not any(_is_cutting_plane(m) for m in members):
        return None
    planes = [_plane_row(m) for m in members if _is_cutting_plane(m)]
    others = [
        "\n".join(lines[m.source_line - 1 : m.source_end_line])
        for m in members if not _is_cutting_plane(m)
    ]
    return "\n".join(planes) + "\n" + SURFACES_SEPARATOR + "\n" + "\n\n".join(others)


def parse_template(text: str) -> ParsedTemplate:
    """The entries of a template a user sets, with their kinds.

    Directives (``#includeEtc``) are not entries: they stay as they are.
    An entry sharing a line with another cannot be rewritten on its own and
    is left out rather than risk changing its neighbour.
    """
    root = OpenFoamParser(text).parse()
    lines = text.split("\n")
    candidates = [
        c for c in root.children
        if c.node_type != "directive_entry" and c.name and c.source_line > 0
    ]
    shared: set[str] = set()
    for a, b in zip(candidates, candidates[1:]):
        if b.source_line <= a.source_end_line:
            shared.update((a.name, b.name))
    entries = []
    for node in candidates:
        if node.name in shared or node.name in FIXED_KEYS:
            continue
        value = _value_text(lines, node)
        names = _PLACEHOLDER_RE.findall(value)
        surfaces = _surfaces_value(lines, node) if node.name == "surfaces" else None
        if surfaces is not None:
            kind, shown = "surfaces", surfaces
        elif names:
            kind = _kind_from_placeholder(node.name, node, value, names)
            # An empty value, not the placeholder, so the form starts blank.
            shown = ""
        else:
            kind = _kind_from_example(node.name, node, value)
            shown = value
        hint = node.inline_comment.strip().lstrip("/").strip()
        entries.append(
            TemplateEntry(
                node.name, kind, shown, bool(names), hint,
                node.source_line, node.source_end_line or node.source_line,
                node.inline_comment,
            )
        )
    keys = [c.name for c in candidates]
    formable = len(keys) == len(set(keys)) and all(_WORD_RE.fullmatch(k) for k in keys)
    if not formable:
        return ParsedTemplate(text, (), False)
    return ParsedTemplate(text, tuple(entries))


def format_value(kind: str, value: str, *, legacy_plane_keys: bool = False) -> str:
    """The form's text for *kind* as OpenFOAM writes it.

    Lists of names arrive space- or comma-separated; points one per line as
    ``x y z`` (brackets optional).
    """
    if kind == "surfaces":
        return _format_surfaces(value, legacy_plane_keys)
    value = value.strip()
    if kind in ("fields", "patches"):
        words = [w for w in re.split(r"[\s,()]+", value) if w]
        return "(" + " ".join(words) + ")"
    if kind == "vector":
        nums = [w for w in re.split(r"[\s,()]+", value) if w]
        return "(" + " ".join(nums) + ")"
    if kind == "points":
        rows = []
        for line in value.replace(")(", ")\n(").split("\n"):
            nums = [w for w in re.split(r"[\s,()]+", line) if w]
            if nums:
                rows.append("    (" + " ".join(nums) + ")")
        return "(\n" + "\n".join(rows) + "\n)"
    return value


def legacy_plane_keywords(installation: str | None) -> bool:
    """Whether a cutting plane must be written with ``basePoint``/``normalVector``.

    The keywords are ``point``/``normal`` today, and OpenCFD (since v1612)
    warns on the old spelling. But Foundation 7 and 8 read the old one
    *first* -- ``found("basePoint") ? basePoint : point`` -- and the
    template's own ``surfaces.cfg`` always supplies a default ``basePoint``
    through ``$cuttingPlane``, so a ``point`` written there would be
    silently ignored and every plane would sit at the origin. Foundation 9+
    reads ``point`` first, like OpenCFD. The version comes from the
    installation's ``etc/bashrc``; unknown means current.
    """
    if not installation:
        return False
    try:
        with open(os.path.join(installation, "etc", "bashrc"), encoding="utf-8", errors="replace") as f:
            text = f.read(20_000)
    except OSError:
        return False
    m = re.search(r"^\s*(?:export\s+)?WM_PROJECT_VERSION=['\"]?([^'\"\s]+)", text, re.MULTILINE)
    version = m.group(1) if m else ""
    return version.isdigit() and int(version) <= 8


def _split_surfaces(value: str) -> tuple[list[list[str]], str]:
    planes_text, _, others = value.partition(SURFACES_SEPARATOR)
    rows = [line.split() for line in planes_text.split("\n") if line.strip()]
    return rows, others.strip("\n")


def _format_surfaces(value: str, legacy_plane_keys: bool = False) -> str:
    rows, others = _split_surfaces(value)
    point_key, normal_key = (
        ("basePoint   ", "normalVector") if legacy_plane_keys else ("point ", "normal")
    )
    members = []
    for row in rows:
        name, p, n = row[0], row[1:4], row[4:7]
        members.append(
            f"    {name}\n    {{\n        $cuttingPlane;\n"
            f"        pointAndNormalDict\n        {{\n"
            f"            {point_key} ({' '.join(p)});\n"
            f"            {normal_key} ({' '.join(n)});\n"
            f"        }}\n    }}"
        )
    if others.strip():
        members.append(others.rstrip())
    return "(\n" + "\n\n".join(members) + "\n)"


def form_text(kind: str, value: str) -> str:
    """The inverse of :func:`format_value`: what the form shows for *value*.

    ``(p U)`` -> ``p U``; ``(0 0 1)`` -> ``0 0 1``; a point list -> one
    ``x y z`` per line. Other kinds as written.
    """
    v = value.strip()
    if kind in ("fields", "patches", "vector"):
        return " ".join(w for w in re.split(r"[\s()]+", v) if w)
    if kind == "points":
        return "\n".join(" ".join(m) for m in _VECTOR_RE.findall(v))
    return v


def value_problem(kind: str, value: str) -> str:
    """Why *value* cannot be written for *kind*, or "" when it can.

    Returned as a short code for the UI to word: ``empty``, ``placeholder``,
    ``number``, ``vector``, ``points``, ``names``.
    """
    if kind == "surfaces":
        rows, others = _split_surfaces(value)
        if not rows and not others.strip():
            return "empty"
        for row in rows:
            if (
                len(row) != 7
                or not _NAME_RE.fullmatch(row[0])
                or not all(_NUMBER_RE.fullmatch(x) for x in row[1:])
            ):
                return "planes"
        return ""
    v = value.strip()
    if not v:
        return "empty"
    if _PLACEHOLDER_RE.search(v):
        return "placeholder"
    if kind == "number" and not _NUMBER_RE.fullmatch(v):
        return "number"
    if kind == "vector":
        nums = [w for w in re.split(r"[\s,()]+", v) if w]
        if len(nums) != 3 or not all(_NUMBER_RE.fullmatch(n) for n in nums):
            return "vector"
    if kind == "points":
        for line in v.replace(")(", ")\n(").split("\n"):
            nums = [w for w in re.split(r"[\s,()]+", line) if w]
            if nums and (len(nums) != 3 or not all(_NUMBER_RE.fullmatch(n) for n in nums)):
                return "points"
    if kind in ("fields", "patches", "field", "patch"):
        words = [w for w in re.split(r"[\s,()]+", v) if w]
        if not words or not all(_WORD_RE.fullmatch(w) for w in words):
            return "names"
        if kind in ("field", "patch") and len(words) != 1:
            return "names"
    return ""


def render(
    template: ParsedTemplate, values: Mapping[str, str], *, legacy_plane_keys: bool = False
) -> str:
    """The template's text with each entry in *values* given its new value.

    *values* maps a key to the form's text, formatted here for the entry's
    kind. Only entries whose value changed are rewritten: comments,
    ``#includeEtc`` lines, untouched examples and every other byte stay as
    the template has them.
    """
    lines = template.text.split("\n")
    by_key = {e.key: e for e in template.entries}
    def edited(entry: TemplateEntry, value: str) -> bool:
        # Compared as written out, so the form's "p U" for "(p U)" is no edit.
        if entry.required:
            return True
        def fmt(v: str) -> str:
            return format_value(entry.kind, v, legacy_plane_keys=legacy_plane_keys)

        return fmt(value) != fmt(form_text(entry.kind, entry.value))

    changed = [by_key[k] for k, v in values.items() if k in by_key and edited(by_key[k], v)]
    # Bottom up, so earlier line numbers stay valid as lines are replaced.
    for entry in sorted(changed, key=lambda e: -e.first_line):
        new_value = format_value(
            entry.kind, values[entry.key], legacy_plane_keys=legacy_plane_keys
        )
        first = lines[entry.first_line - 1]
        m = re.match(r"(\s*" + re.escape(entry.key) + r")(\s*)", first)
        lead, pad = (m.group(1), m.group(2)) if m else (entry.key, " ")
        tail = entry.comment
        if "\n" in new_value:
            replacement = f"{lead}\n{new_value};{tail}".split("\n")
        else:
            replacement = [f"{lead}{pad or ' '}{new_value};{tail}"]
        lines[entry.first_line - 1 : entry.last_line] = replacement
    return "\n".join(lines)


def is_valid_function_name(name: str) -> bool:
    """A name usable as ``system/<name>`` and ``#includeFunc <name>``."""
    return bool(_NAME_RE.fullmatch(name))


# ── controlDict ─────────────────────────────────────────────────────────────

_INCLUDE_FUNC_RE = r"#includeFunc\s+{name}\b"


def function_names(control_dict_text: str) -> set[str]:
    """Function objects already in controlDict's ``functions``, by name.

    Both forms count: a ``name { … }`` entry and an ``#includeFunc name``
    line (with or without arguments).
    """
    names = set(re.findall(r"#includeFunc\s+([A-Za-z0-9_]+)", control_dict_text))
    try:
        root = OpenFoamParser(control_dict_text).parse()
    except Exception:
        return names
    for node in root.children:
        if node.name == "functions" and node.node_type == "dictionary":
            names.update(c.name for c in node.children if c.name)
    return names


def add_include_func(control_dict_text: str, name: str) -> str | None:
    """*control_dict_text* with ``#includeFunc <name>`` in its ``functions``.

    A missing ``functions`` dictionary is added, before the closing divider
    when the file ends in one. Returns None when ``functions`` exists but is
    not a dictionary FoDE can add to (an ``#include`` of it, say), so the
    caller can say so rather than write a second one.
    """
    if re.search(_INCLUDE_FUNC_RE.format(name=re.escape(name)), control_dict_text):
        return control_dict_text
    root = OpenFoamParser(control_dict_text).parse()
    lines = control_dict_text.split("\n")
    line = f"    #includeFunc {name}"
    for node in root.children:
        if node.name != "functions":
            continue
        if node.node_type != "dictionary":
            return None
        first, last = node.source_line, node.source_end_line
        if first <= 0 or last < first:
            return None
        if first == last:
            # functions {} on one line: open it up.
            lines[first - 1 : last] = ["functions", "{", line, "}"]
        else:
            lines.insert(last - 1, line)
        return "\n".join(lines)
    block = ["functions", "{", line, "}", ""]
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith("// *"):
            lines[i:i] = block
            return "\n".join(lines)
        if lines[i].strip():
            break
    text = control_dict_text
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n" + "\n".join(block)


# ── what the case offers the form ───────────────────────────────────────────

_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
_TOKEN_RE = re.compile(r'"[^"]*"|[(){}]|[^\s(){};]+|;')


def _names_opening_blocks(text: str, list_depth: int, brace_depth: int) -> list[str]:
    """Words followed by ``{`` at the given bracket depths, in order."""
    names: list[str] = []
    parens = braces = 0
    previous = ""
    for token in _TOKEN_RE.findall(_COMMENT_RE.sub(" ", text)):
        if token == "{":
            if parens == list_depth and braces == brace_depth and _WORD_RE.fullmatch(previous):
                names.append(previous)
            braces += 1
        elif token == "}":
            braces -= 1
        elif token == "(":
            parens += 1
        elif token == ")":
            parens -= 1
        previous = token
    return names


def case_patch_names(case_dir: str) -> list[str]:
    """Patch names of the case's mesh, for the form's patch pickers.

    From ``constant/polyMesh/boundary``: the words opening a block directly
    inside its list. Before the mesh exists, from ``boundaryField`` in a
    ``0/`` field instead. Quoted regex keys (``".*Wall"``) are not patch
    names and are skipped. [] when neither is there.
    """
    boundary = os.path.join(case_dir, "constant", "polyMesh", "boundary")
    try:
        with open(boundary, encoding="utf-8", errors="replace") as f:
            text = f.read()
        body = re.sub(r"\bFoamFile\s*\{.*?\}", " ", text, count=1, flags=re.S)
        names = _names_opening_blocks(body, 1, 0)
        if names:
            return names
    except OSError:
        pass
    zero = os.path.join(case_dir, "0")
    for name in sorted(_field_files(zero)):
        try:
            with open(os.path.join(zero, name), encoding="utf-8", errors="replace") as f:
                text = f.read(200_000)
        except OSError:
            continue
        m = re.search(r"\bboundaryField\s*\{", text)
        if not m:
            continue
        names = _names_opening_blocks("{" + text[m.end():], 0, 1)
        if names:
            return names
    return []


def _field_files(directory: str) -> list[str]:
    try:
        entries = os.listdir(directory)
    except OSError:
        return []
    return [
        e for e in entries
        if not e.startswith(".") and not e.endswith((".orig", "~"))
        and os.path.isfile(os.path.join(directory, e))
    ]


def case_field_names(case_dir: str, latest_time: str | None = None) -> list[str]:
    """Field names to offer: those in ``0/`` (or ``0.orig/``) and the latest time.

    The latest time adds fields a run wrote that ``0/`` lacks (``phi``,
    ``nut``, ``vorticity`` from an earlier function object); compressed files
    count under their plain name.
    """
    names = set(_field_files(os.path.join(case_dir, "0"))) or set(
        _field_files(os.path.join(case_dir, "0.orig"))
    )
    if latest_time:
        names |= set(_field_files(os.path.join(case_dir, latest_time)))
    return sorted({n[:-3] if n.endswith(".gz") else n for n in names}, key=str.lower)


# ── starting places from the domain ─────────────────────────────────────────

# How far a sample line's ends are pulled in from the walls, as a fraction of
# its length: a point exactly on a boundary face may find no cell. OpenCFD's
# own singleGraph template offsets its example by 1e-6 for the same reason.
_LINE_INSET = 1e-3


def _xyz(values: Sequence[float]) -> str:
    return " ".join(f"{v:.6g}" for v in values)


def suggest_values(parsed: ParsedTemplate, bounds) -> dict[str, tuple[str, str]]:
    """Starting values for a template's geometry, from the domain *bounds*.

    Maps a key to ``(form text, reason)``; the reason -- ``centre``,
    ``line``, ``plane``, ``planes`` -- is for the form's note to word.
    Only geometry is touched: a probe list gets one point at the centre; a
    ``start``/``end`` pair a line through the centre along the longest axis,
    its ends pulled in from the walls; a top-level ``point``/``normal`` pair
    (Foundation's cutPlaneSurface) a plane through the centre normal to the
    thinnest direction -- a 2-D case's mid-plane; OpenCFD's cutting-plane
    rows keep their names and normals and move to the centre. A centre of
    rotation, a direction of lift, a patch -- physics, not position -- are
    left alone. *bounds* is a ``services.domain_bounds.DomainBounds``.
    """
    if bounds is None or not parsed.formable:
        return {}
    by_key = {e.key: e for e in parsed.entries}
    centre, span = bounds.centre, bounds.span
    out: dict[str, tuple[str, str]] = {}
    for key in ("probeLocations", "points"):
        entry = by_key.get(key)
        if entry is not None and entry.kind == "points":
            out[key] = (_xyz(centre), "centre")
    start, end = by_key.get("start"), by_key.get("end")
    if start is not None and end is not None and start.kind == end.kind == "vector":
        axis = max(range(3), key=lambda i: span[i])
        inset = span[axis] * _LINE_INSET
        a, b = list(centre), list(centre)
        a[axis] = bounds.lo[axis] + inset
        b[axis] = bounds.hi[axis] - inset
        out["start"] = (_xyz(a), "line")
        out["end"] = (_xyz(b), "line")
    point, normal = by_key.get("point"), by_key.get("normal")
    if point is not None and normal is not None and point.kind == normal.kind == "vector":
        thinnest = min(range(3), key=lambda i: span[i])
        out["point"] = (_xyz(centre), "plane")
        out["normal"] = (_xyz([1.0 if i == thinnest else 0.0 for i in range(3)]), "plane")
    surfaces = by_key.get("surfaces")
    if surfaces is not None and surfaces.kind == "surfaces":
        rows, others = _split_surfaces(surfaces.value)
        moved = [
            f"{row[0]}  {_xyz(centre)}  {' '.join(row[4:7])}" for row in rows if len(row) == 7
        ]
        if moved:
            out["surfaces"] = (
                "\n".join(moved) + "\n" + SURFACES_SEPARATOR + "\n" + others, "planes"
            )
    return out
