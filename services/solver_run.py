# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Qt-free case inspection behind Tools > Run Solver… and Run decomposePar….

Reads the solver a case is set up for from ``system/controlDict``, the
subdomain count from ``system/decomposeParDict``, and whether the case has
already been decomposed. Every reader takes dictionary *text* rather than a
path, so the caller can hand over an unsaved editor buffer; a dictionary that
fails to parse is an ordinary "unknown", never an exception.
"""
from __future__ import annotations

import dataclasses
import os
import re
import shlex
import shutil
from collections.abc import Callable, Iterable

from foam.nodes import FoamNode
from foam.parser import OpenFoamParser
from foam.tree_utils import find_child
from services.case_loader import detect_time_dirs
from services.field_integrity import Cancelled, MeshSizes, inspect_file, read_mesh_sizes
from services.process_tree import processes_in_directory

# Foundation v11+ runs every solver module through one of these two
# executables; the module itself is named by controlDict's ``solver`` entry
# (``foamRun``) or by ``regionSolvers`` (``foamMultiRun``). Both executables
# read those entries themselves, so the command line stays the bare name.
MODULE_RUNNERS = ("foamRun", "foamMultiRun")

# Suggestions for the editable solver field. The field is free text, so this
# only has to cover what people reach for most often in either fork.
COMMON_SOLVERS: tuple[str, ...] = (
    "foamRun",
    "foamMultiRun",
    "icoFoam",
    "simpleFoam",
    "pisoFoam",
    "pimpleFoam",
    "potentialFoam",
    "interFoam",
    "interIsoFoam",
    "multiphaseEulerFoam",
    "rhoSimpleFoam",
    "rhoPimpleFoam",
    "buoyantSimpleFoam",
    "buoyantPimpleFoam",
    "chtMultiRegionFoam",
    "reactingFoam",
    "sonicFoam",
    "scalarTransportFoam",
    "laplacianFoam",
)

# An executable name: no path, no whitespace, nothing the shell would read.
_SOLVER_NAME_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*")
# A suffix for a kept log: one path component, never hidden, never empty.
_LOG_SUFFIX_RE = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*")
_PART_SUFFIX_RE = re.compile(r"part(\d+)")
# ``processorN`` (uncollated) and ``processorsN`` / ``processorsN_A-B``
# (collated, written with ``-fileHandler collated``).
_PROCESSOR_DIR_RE = re.compile(r"processors?(\d+)(?:_\d+-\d+)?")


@dataclasses.dataclass(frozen=True)
class SolverInfo:
    """What ``system/controlDict`` says about how the case is run."""

    # The ``application`` entry, or None when absent/unreadable.
    application: str | None = None
    # foamRun's ``solver`` module, when application is foamRun.
    module: str | None = None
    # foamMultiRun's ``regionSolvers`` as (region, module) pairs.
    region_modules: tuple[tuple[str, str], ...] = ()
    # ``startFrom`` / ``startTime``, for the "existing results" note.
    start_from: str | None = None
    start_time: str | None = None


def is_valid_solver_name(name: str) -> bool:
    """True when ``name`` is safe to put on the command line as an executable."""
    return _SOLVER_NAME_RE.fullmatch(name) is not None


def is_valid_log_suffix(suffix: str) -> bool:
    """True when ``log.<app>.<suffix>`` is a plain file name in the case dir."""
    return _LOG_SUFFIX_RE.fullmatch(suffix) is not None


def next_part_suffix(case_dir: str, log_name: str) -> str:
    """``partN`` for the next kept copy of ``log_name``, one past the highest.

    One past the highest rather than the first gap, so the numbers stay in
    the order the runs happened even after a part has been deleted.
    """
    try:
        names = os.listdir(case_dir)
    except OSError:
        names = []
    highest = 0
    prefix = log_name + "."
    for name in names:
        if not name.startswith(prefix):
            continue
        match = _PART_SUFFIX_RE.fullmatch(name[len(prefix):])
        if match:
            highest = max(highest, int(match.group(1)))
    return f"part{highest + 1}"


def keep_log_prefix(log_name: str, kept_name: str) -> str:
    """Shell prefix that moves the previous log aside before the run."""
    return f"mv {shlex.quote(log_name)} {shlex.quote(kept_name)} && "


def _parse(text: str) -> FoamNode | None:
    try:
        return OpenFoamParser(text).parse()
    except Exception:  # a broken dictionary means "unknown", not a crash
        return None


def _word(root: FoamNode, key: str) -> str | None:
    node = find_child(root, key)
    if node is None or node.value is None or node.children:
        return None
    text = str(node.value).strip().strip('"').strip()
    return text or None


def read_solver_info(control_dict_text: str) -> SolverInfo:
    """Read the run-related entries of a controlDict."""
    root = _parse(control_dict_text)
    if root is None:
        return SolverInfo()
    application = _word(root, "application")
    module = _word(root, "solver") if application == "foamRun" else None
    region_modules: tuple[tuple[str, str], ...] = ()
    if application == "foamMultiRun":
        regions = find_child(root, "regionSolvers")
        if regions is not None:
            region_modules = tuple(
                (child.name, str(child.value).strip('"'))
                for child in regions.children
                if child.name and child.value is not None
            )
    return SolverInfo(
        application=application,
        module=module,
        region_modules=region_modules,
        start_from=_word(root, "startFrom"),
        start_time=_word(root, "startTime"),
    )


def read_subdomain_count(decompose_par_dict_text: str) -> int | None:
    """``numberOfSubdomains`` of a decomposeParDict, or None if not a positive int."""
    root = _parse(decompose_par_dict_text)
    if root is None:
        return None
    text = _word(root, "numberOfSubdomains")
    try:
        count = int(text) if text is not None else 0
    except ValueError:
        return None
    return count if count > 0 else None


def processor_dirs(case_dir: str) -> list[str]:
    """The case's decomposed-data directories, sorted by processor number."""
    try:
        names = os.listdir(case_dir)
    except OSError:
        return []
    found = [
        n
        for n in names
        if _PROCESSOR_DIR_RE.fullmatch(n) and os.path.isdir(os.path.join(case_dir, n))
    ]
    return sorted(found, key=_processor_sort_key)


def _processor_sort_key(name: str) -> tuple[int, str]:
    match = _PROCESSOR_DIR_RE.fullmatch(name)
    assert match is not None
    return int(match.group(1)), name


def decomposed_count(case_dir: str) -> int | None:
    """How many pieces the case is decomposed into, or None if it is not.

    Collated data (``processorsN``) states N in its name; uncollated data is
    one ``processorN`` directory per piece.
    """
    dirs = processor_dirs(case_dir)
    if not dirs:
        return None
    collated = [d for d in dirs if d.startswith("processors")]
    if collated:
        return _processor_sort_key(collated[0])[0]
    return len(dirs)


def unreconstructed_times(case_dir: str) -> list[str]:
    """Time directories in the decomposed data that the case root lacks.

    Those are parallel-run results that have not been through reconstructPar
    yet, and ``decomposePar -force`` deletes them along with the processor
    directories. A time present at the case root too (the decomposed start
    time, or anything already reconstructed) is not counted.
    """
    at_root = set(detect_time_dirs(case_dir))
    found: dict[str, float] = {}
    for name in processor_dirs(case_dir):
        for t in detect_time_dirs(os.path.join(case_dir, name)):
            if t not in at_root:
                found[t] = float(t)
    return sorted(found, key=found.__getitem__)


def _newest_file_mtime(directory: str) -> float | None:
    """Newest mtime among the regular files directly inside ``directory``."""
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return None
    times = [e.stat().st_mtime for e in entries if e.is_file()]
    return max(times) if times else None


def stale_decomposition(
    case_dir: str, pending: Iterable[str] = ()
) -> list[str]:
    """Case-root inputs changed since decomposePar, as case-relative dirs.

    A parallel run reads ``processor*/``, never the case root, so a field
    edited in ``0/`` or a mesh regenerated after decomposing is silently
    ignored. Compares ``0/`` and ``constant/polyMesh`` against the first
    processor directory. Later time directories are deliberately left out:
    reconstructPar writes them at the root *after* the processor copies, so
    every reconstructed time would read as "changed". ``pending``
    names files about to be written (unsaved buffers the dialog will save),
    which count as changed now.
    """
    dirs = processor_dirs(case_dir)
    if not dirs:
        return []
    proc = os.path.join(case_dir, dirs[0])
    pending_dirs = {os.path.dirname(os.path.abspath(p)) for p in pending}
    stale: list[str] = []
    for rel in ("0", os.path.join("constant", "polyMesh")):
        root_dir = os.path.join(case_dir, rel)
        proc_dir = os.path.join(proc, rel)
        if not (os.path.isdir(root_dir) and os.path.isdir(proc_dir)):
            continue
        if os.path.abspath(root_dir) in pending_dirs:
            stale.append(rel)
            continue
        root_t = _newest_file_mtime(root_dir)
        proc_t = _newest_file_mtime(proc_dir)
        if root_t is not None and proc_t is not None and root_t > proc_t:
            stale.append(rel)
    return stale


# Files decomposePar/reconstructPar keep only in the decomposed copy: the map
# from each processor's cells/faces/points back to the whole mesh. A root time
# directory never has them, and must not be required to.
_PROCESSOR_ONLY_FILES = frozenset(
    {"cellProcAddressing", "faceProcAddressing", "pointProcAddressing", "boundaryProcAddressing"}
)


@dataclasses.dataclass(frozen=True)
class DeletionProblem:
    """One reason deleting processor* would lose data. ``kind`` is a code:

    - ``collated``: collated ``processorsN`` data, whose contents this check
      cannot read -- refused rather than guessed at;
    - ``time_missing``: ``time`` exists in a processor directory but not at
      the case root (``detail`` names the processors);
    - ``files_missing``: files under ``time`` exist only in the decomposed
      copy (``detail`` lists them, case-relative to the time directory);
    - ``mesh_missing``: the processors hold a mesh and the case root has none;
    - ``mesh_differs``: the root mesh's cell count is not the processors'
      total -- e.g. a mesh made with ``snappyHexMesh -parallel`` and not yet
      through ``reconstructParMesh``, leaving the old background mesh at the
      root (``detail``: "root N, processors M");
    - ``mesh_unknown``: a cell count could not be read, so the meshes cannot
      be compared;
    - ``sets_missing``: cell/face/point sets (``constant/polyMesh/sets/``)
      that exist only in the decomposed copy -- reconstructPar skips them
      under ``-noSets`` (``detail`` names them).

    The rest are about the case-root copy being *sound*, not merely present
    (see services/field_integrity.py); ``detail`` lists the files, relative
    to the time directory:

    - ``files_cut_off``: no closing ``// *** //`` line, or a compressed
      stream that ends early -- a reconstructPar killed while writing it;
    - ``files_bad_header``: no ``FoamFile`` header naming the file;
    - ``files_wrong_size``: an ``internalField`` whose value count is not the
      mesh's (each entry "file: in file ≠ mesh") -- a complete file left
      from a run on another mesh;
    - ``processes_running``: something other than FoDE is working in the
      case right now (``detail``: "name (pid N)"), so what is on disk may
      still be changing.

    A root file is only held to a standard its processor copy meets, so a
    file OpenFOAM writes without a closing line or header is never flagged.
    """

    kind: str
    time: str = ""
    detail: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class DeletionCheck:
    dirs: tuple[str, ...]
    # Bytes the deletion frees: whole directories, or with ``kept_time`` only
    # the time directories it removes.
    total_bytes: int
    problems: tuple[DeletionProblem, ...]
    # Keep-latest mode: delete only processor time directories, leaving each
    # processor's constant/ and its latest time (``kept_time``; None when the
    # processors hold no time at all) so the run can continue in parallel.
    # A field of its own rather than inferred from kept_time, because "keep
    # mode with nothing to keep" must never be read as "delete everything".
    keep_latest: bool = False
    kept_time: str | None = None
    # The newest time at the case root, for the "root is ahead" note.
    latest_root_time: str | None = None
    # Compressed root files whose end was not read -- only their head was --
    # as (time, path within it), and their compressed size in all.
    # verify_compressed() reads them to the end.
    unverified_gz: tuple[tuple[str, str], ...] = ()
    unverified_gz_bytes: int = 0

    @property
    def safe(self) -> bool:
        return bool(self.dirs) and not self.problems


def _files_under(root: str) -> set[str]:
    """Every file under *root*, as paths relative to it."""
    found: set[str] = set()
    for dirpath, _dirs, files in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        for name in files:
            if name in _PROCESSOR_ONLY_FILES:
                continue
            found.add(name if rel == "." else os.path.join(rel, name))
    return found


def _owner_cell_count(mesh_dir: str) -> int | None:
    """nCells from ``owner``'s header note (``owner.gz`` too), reading only the header."""
    owner = os.path.join(mesh_dir, "owner")
    sizes = read_mesh_sizes(owner if os.path.exists(owner) else owner + ".gz")
    return sizes.n_cells if sizes is not None else None


def _uncompressed(rel: str) -> str:
    """*rel* without a ``.gz`` suffix: the name a file is compared under.

    With ``writeCompression on`` decomposePar writes ``processor*/0/U.gz``
    from an uncompressed ``0/U``, so the two copies of one file need not
    share a name.
    """
    return rel[:-3] if rel.endswith(".gz") else rel


def _tree_bytes(root: str) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            try:
                total += os.lstat(os.path.join(dirpath, name)).st_size
            except OSError:
                pass
    return total


def _times_of(directory: str) -> set[str]:
    times = set(detect_time_dirs(directory))
    if os.path.isdir(os.path.join(directory, "0")):
        times.add("0")
    return times


def _latest(times: set[str]) -> str | None:
    return max(times, key=float) if times else None


class _RootMeshes:
    """The mesh each root field is read against, memoised per case.

    A field at time *t* uses the newest ``<t'>/polyMesh`` with t' ≤ t (a
    topology-changing run writes one per time), else ``constant/polyMesh``;
    a field under ``<t>/<region>/`` uses that region's mesh the same way.
    """

    def __init__(self, case_dir: str) -> None:
        self._case = case_dir
        self._times = sorted(_times_of(case_dir), key=float)
        self._cache: dict[str, MeshSizes | None] = {}

    def region_of(self, rel: str) -> str:
        first = rel.split(os.sep, 1)[0]
        if first != rel and os.path.isdir(
            os.path.join(self._case, "constant", first, "polyMesh")
        ):
            return first
        return ""

    def sizes(self, time: str, region: str) -> MeshSizes | None:
        for t in reversed(self._times):
            if float(t) > float(time):
                continue
            owner = os.path.join(self._case, t, region, "polyMesh", "owner")
            if os.path.exists(owner) or os.path.exists(owner + ".gz"):
                return self._read(owner)
        return self._read(os.path.join(self._case, "constant", region, "polyMesh", "owner"))

    def _read(self, owner: str) -> MeshSizes | None:
        if owner not in self._cache:
            path = owner if os.path.exists(owner) else owner + ".gz"
            self._cache[owner] = read_mesh_sizes(path)
        return self._cache[owner]


def _processor_copy(case_dir: str, dirs: Iterable[str], time: str, rel: str) -> str | None:
    """The first processor copy of root file *rel*, compressed or not."""
    plain = _uncompressed(rel)
    for d in dirs:
        for name in (rel, plain, plain + ".gz"):
            path = os.path.join(case_dir, d, time, name)
            if os.path.isfile(path):
                return path
    return None


def _soundness_problems(
    case_dir: str, time: str, rels: Iterable[str], holders: list[str], meshes: _RootMeshes
) -> tuple[list[DeletionProblem], list[str]]:
    """The root copy of *rels* under *time*, held to its processor copy.

    Returns the problems and the compressed files whose end went unread.
    """
    cut: list[str] = []
    bad_header: list[str] = []
    wrong_size: list[str] = []
    unread_gz: list[str] = []
    for rel in sorted(rels):
        path = os.path.join(case_dir, time, rel)
        state = inspect_file(path)
        if not state.readable:
            cut.append(rel)
            continue
        names_itself = state.names(path)
        if state.ended is False or not names_itself:
            base_path = _processor_copy(case_dir, holders, time, rel)
            base = inspect_file(base_path, full=True) if base_path else None
            if state.ended is False and base is not None and base.ended:
                cut.append(rel)
                continue
            if not names_itself and base is not None and base_path and base.names(base_path):
                bad_header.append(rel)
                continue
        if state.ended is None:
            unread_gz.append(rel)
        if state.field_class is not None and state.count is not None:
            mesh = meshes.sizes(time, meshes.region_of(rel))
            expected = mesh.expected_count(state.field_class) if mesh else None
            if expected is not None and expected != state.count:
                wrong_size.append(f"{rel}: {state.count} ≠ {expected}")
    problems = [
        DeletionProblem(kind, time, tuple(found))
        for kind, found in (
            ("files_cut_off", cut),
            ("files_bad_header", bad_header),
            ("files_wrong_size", wrong_size),
        )
        if found
    ]
    return problems, unread_gz


def case_activity_problem(case_dir: str, *, proc_root: str = "/proc") -> DeletionProblem | None:
    """``processes_running`` if anything outside FoDE is working in the case."""
    procs = processes_in_directory(case_dir, exclude_tree_of=os.getpid(), proc_root=proc_root)
    if not procs:
        return None
    return DeletionProblem(
        "processes_running", detail=tuple(f"{p.name} (pid {p.pid})" for p in procs)
    )


def verify_compressed(
    case_dir: str,
    check: DeletionCheck,
    progress: Callable[[int, int, str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> tuple[DeletionProblem, ...] | None:
    """Read every file in ``check.unverified_gz`` to its end; None if cancelled.

    ``progress(done_bytes, total_bytes, relative_path)`` counts compressed
    bytes, the unit the work is proportional to.
    """
    total = check.unverified_gz_bytes
    done = 0
    cut: dict[str, list[str]] = {}
    for time, rel in check.unverified_gz:
        path = os.path.join(case_dir, time, rel)
        shown = os.path.join(time, rel)
        if progress is not None:
            progress(done, total, shown)

        def advance(n: int, shown: str = shown) -> None:
            nonlocal done
            done += n
            if progress is not None:
                progress(done, total, shown)

        start = done
        try:
            state = inspect_file(path, full=True, progress=advance, cancelled=cancelled)
        except Cancelled:
            return None
        try:
            # Whole files, whatever the read consumed: one cut off stops early.
            done = start + os.path.getsize(path)
        except OSError:
            pass
        if not state.readable or state.ended is False:
            base_path = _processor_copy(case_dir, check.dirs, time, rel)
            base = inspect_file(base_path, full=True) if base_path else None
            if not state.readable or (base is not None and base.ended):
                cut.setdefault(time, []).append(rel)
    if progress is not None:
        progress(done, total, "")
    return tuple(
        DeletionProblem("files_cut_off", t, tuple(found))
        for t, found in sorted(cut.items(), key=lambda item: float(item[0]))
    )


def check_processor_deletion(case_dir: str, *, keep_latest: bool = False) -> DeletionCheck:
    """Whether deleting every processor* directory would lose any data.

    With ``keep_latest`` the question is narrower: deleting every processor
    time directory *except the latest*, keeping each processor's
    ``constant/`` too, so the run can carry on in parallel without
    decomposePar -- which is serial and holds the whole mesh in memory, the
    expensive step on exactly the cases where processor* is large. Only what
    would be deleted is checked; the mesh and sets stay, so they are not.

    Safe only when everything in them also exists at the case root: every
    time directory, every file in it (fields, ``uniform/``, ``lagrangian/``
    …, so a ``reconstructPar -fields`` subset is caught), and a mesh whose
    cell count is the processors' total. This is a check of what is on disk,
    deliberately not of whether reconstructPar exited cleanly: a run that
    succeeded with ``-latestTime`` or ``-fields`` still leaves data that
    exists nowhere else.
    """
    dirs = tuple(processor_dirs(case_dir))
    if not dirs:
        return DeletionCheck((), 0, ())
    at_root = _times_of(case_dir)
    latest_root = _latest(at_root)
    if any(d.startswith("processors") for d in dirs):
        total = sum(_tree_bytes(os.path.join(case_dir, d)) for d in dirs)
        return DeletionCheck(dirs, total, (DeletionProblem("collated"),))

    kept = None
    if keep_latest:
        kept = _latest(set().union(*(_times_of(os.path.join(case_dir, d)) for d in dirs)))
    problems: list[DeletionProblem] = []

    # time -> processors holding it, and the union of their files
    holders: dict[str, list[str]] = {}
    files: dict[str, set[str]] = {}
    for d in dirs:
        proc = os.path.join(case_dir, d)
        for t in _times_of(proc) - {kept}:
            holders.setdefault(t, []).append(d)
            files.setdefault(t, set()).update(_files_under(os.path.join(proc, t)))

    meshes = _RootMeshes(case_dir)
    unverified: list[tuple[str, str]] = []
    for t in sorted(holders, key=float):
        if t not in at_root:
            problems.append(DeletionProblem("time_missing", t, tuple(holders[t])))
            continue
        root_files = {_uncompressed(r): r for r in _files_under(os.path.join(case_dir, t))}
        missing = {f for f in files[t] if _uncompressed(f) not in root_files}
        if missing:
            problems.append(DeletionProblem("files_missing", t, tuple(sorted(missing))))
        present = {
            root_files[_uncompressed(f)] for f in files[t] if _uncompressed(f) in root_files
        }
        found, unread = _soundness_problems(case_dir, t, present, holders[t], meshes)
        problems += found
        unverified += [(t, rel) for rel in unread]
    unverified_bytes = 0
    for t, rel in unverified:
        try:
            unverified_bytes += os.path.getsize(os.path.join(case_dir, t, rel))
        except OSError:
            pass

    if not keep_latest:
        # The whole of each processor directory goes, constant/ included.
        proc_meshes = [
            os.path.join(case_dir, d, "constant", "polyMesh")
            for d in dirs
            if os.path.isdir(os.path.join(case_dir, d, "constant", "polyMesh"))
        ]
        root_mesh = os.path.join(case_dir, "constant", "polyMesh")
        proc_sets: set[str] = set()
        for m in proc_meshes:
            proc_sets |= _files_under(os.path.join(m, "sets"))
        root_sets = {_uncompressed(r) for r in _files_under(os.path.join(root_mesh, "sets"))}
        sets_missing = {s for s in proc_sets if _uncompressed(s) not in root_sets}
        if sets_missing:
            problems.append(DeletionProblem("sets_missing", detail=tuple(sorted(sets_missing))))
        if proc_meshes:
            if not os.path.isdir(root_mesh):
                problems.append(DeletionProblem("mesh_missing"))
            else:
                root_cells = _owner_cell_count(root_mesh)
                counts = [_owner_cell_count(m) for m in proc_meshes]
                if root_cells is None or any(c is None for c in counts):
                    problems.append(DeletionProblem("mesh_unknown"))
                elif root_cells != sum(c for c in counts if c is not None):
                    problems.append(
                        DeletionProblem(
                            "mesh_differs",
                            detail=(str(root_cells), str(sum(c for c in counts if c is not None))),
                        )
                    )
        total = sum(_tree_bytes(os.path.join(case_dir, d)) for d in dirs)
    else:
        total = sum(
            _tree_bytes(os.path.join(case_dir, d, t))
            for d in dirs
            for t in _times_of(os.path.join(case_dir, d)) - {kept}
        )
    return DeletionCheck(
        dirs, total, tuple(problems), keep_latest, kept, latest_root,
        tuple(unverified), unverified_bytes,
    )


@dataclasses.dataclass(frozen=True)
class DecompositionStatus:
    """What the file list's "Decomposed" line says about processor*."""

    count: int  # processor directories, or the collated count
    collated: bool
    times: tuple[str, ...]  # in processor0 (or the collated dir), ascending
    unreconstructed: tuple[str, ...]  # of those, not at the case root


def decomposition_status(case_dir: str) -> DecompositionStatus | None:
    """None when the case is not decomposed. Directory listings only."""
    dirs = processor_dirs(case_dir)
    if not dirs:
        return None
    collated = any(d.startswith("processors") for d in dirs)
    count = decomposed_count(case_dir) or len(dirs)
    times = tuple(sorted(_times_of(os.path.join(case_dir, dirs[0])), key=float))
    return DecompositionStatus(count, collated, times, tuple(unreconstructed_times(case_dir)))


def deletion_targets(case_dir: str, check: DeletionCheck) -> list[str]:
    """What *check* covers, as paths in the order they are deleted.

    One time directory at a time, so progress is fine-grained and stopping
    part-way leaves only whole, already-verified pieces removed: in whole
    mode each processor's time directories go first and then the directory
    itself (constant/ and all); in keep-latest mode only the time
    directories other than the kept one.
    """
    targets: list[str] = []
    for d in check.dirs:
        proc = os.path.join(case_dir, d)
        times = sorted(_times_of(proc) - {check.kept_time}, key=float)
        targets += [os.path.join(proc, t) for t in times]
        if not check.keep_latest:
            targets.append(proc)
    return targets


@dataclasses.dataclass(frozen=True)
class DeletionResult:
    failed: tuple[str, ...]  # "relative/path: error"
    stopped: bool  # cancelled before the last target
    done: int  # targets deleted (or attempted)
    total: int
    # Found by the last-moment checks before anything was deleted (then
    # ``done`` is 0): a process working in the case, a compressed file cut off.
    problems: tuple[DeletionProblem, ...] = ()


def delete_processor_data(
    case_dir: str,
    check: DeletionCheck,
    progress: Callable[[int, int, str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> DeletionResult:
    """Delete exactly what *check* covered.

    ``progress(done, total, relative_path)`` is called before each target and
    ``cancelled()`` is polled between them -- the same convention as
    ``app_config/keyword_generator.py`` -- so a caller on a worker thread can
    show progress and stop. Stopping between targets is always safe: each
    target is a whole time directory that the check found at the case root.
    The caller has confirmed ``check.safe``; this does not re-check.
    """
    targets = deletion_targets(case_dir, check)
    failed: list[str] = []
    for n, target in enumerate(targets):
        if cancelled is not None and cancelled():
            return DeletionResult(tuple(failed), True, n, len(targets))
        rel = os.path.relpath(target, case_dir)
        if progress is not None:
            progress(n, len(targets), rel)
        try:
            shutil.rmtree(target)
        except OSError as e:
            failed.append(f"{rel}: {e}")
    return DeletionResult(tuple(failed), False, len(targets), len(targets))


def has_mesh(case_dir: str) -> bool:
    """True when the case has a polyMesh anywhere a solver could read one.

    Covers the single-region ``constant/polyMesh``, a multi-region
    ``constant/<region>/polyMesh``, and a decomposed ``processorN/constant/…``.
    """
    candidates = [os.path.join(case_dir, "constant")]
    candidates += [
        os.path.join(case_dir, d, "constant") for d in processor_dirs(case_dir)
    ]
    for constant in candidates:
        if os.path.isdir(os.path.join(constant, "polyMesh")):
            return True
        try:
            regions = os.listdir(constant)
        except OSError:
            continue
        if any(os.path.isdir(os.path.join(constant, r, "polyMesh")) for r in regions):
            return True
    return False
