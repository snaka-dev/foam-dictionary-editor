#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
#
# Regenerate the ParaView profile the demo takes use.
#
# `cavity-full-workflow` ends in ParaView, and ParaView is not ours: its clicks
# are pixel coordinates, so where its buttons sit has to be the same on every
# machine. Left to the recorder's own profile it is not -- the Apply button
# moved 80px between two takes here, silently, because a `point` step cannot
# miss -- and that profile also opens the window wider than the nested display,
# clipping the colour legend off the right edge.
#
# So the takes ship with a profile of their own. This regenerates it, which is
# needed when the ParaView version changes: the settings file is named for the
# version (ParaView<major>.<minor>.<patch>.ini) and a different build ignores
# one written by another. Qt restores this state all-or-nothing and ignores a
# hand-written file, so it has to come from a real ParaView -- hence driving
# one rather than writing the .ini by hand.
#
# Usage:  source <openfoam>/etc/bashrc && tools/make_paraview_demo_profile.sh
set -euo pipefail

OUT="$(cd "$(dirname "$0")" && pwd)/demo_paraview_profile"
W=1280
H=800

command -v paraview >/dev/null || { echo "paraview not on PATH" >&2; exit 1; }
command -v xdotool  >/dev/null || { echo "xdotool not on PATH" >&2; exit 1; }
command -v Xvfb     >/dev/null || { echo "Xvfb not on PATH" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/run.sh" <<'INNER'
#!/bin/bash
export XDG_CONFIG_HOME="$1"
export LIBGL_ALWAYS_SOFTWARE=1
W="$2"; H="$3"
paraview >/dev/null 2>&1 &
PV=$!
sleep 35

# The Getting Started splash covers the window on a first run. Tick "Don't
# show this window again", then close it, so a take never records it.
xdotool mousemove 249 580 click 1; sleep 1
xdotool mousemove 850 580 click 1; sleep 3

# Fit the window to the nested display. The recorder's own profile is wider
# than the screen, which is what clips the colour legend.
for win in $(xdotool search --name "^ParaView [0-9]" 2>/dev/null); do
    xdotool windowmove "$win" 0 0 windowsize "$win" "$W" "$H"
done
sleep 3

# Quit through the application so the settings are written; SIGTERM would
# leave nothing behind, which is the whole point of this script.
xdotool key --clearmodifiers ctrl+q; sleep 6
kill "$PV" 2>/dev/null || true
wait "$PV" 2>/dev/null || true
INNER
chmod +x "$TMP/run.sh"

echo "→ driving a throwaway ParaView to write its settings…"
xvfb-run -a -s "-screen 0 ${W}x${H}x24" "$TMP/run.sh" "$TMP/config" "$W" "$H" >/dev/null 2>&1 || true

[ -d "$TMP/config/ParaView" ] || { echo "ParaView wrote no settings; nothing to capture" >&2; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT"
cp -a "$TMP/config/ParaView/." "$OUT/"
echo "→ profile written to $OUT"
ls -la "$OUT"
