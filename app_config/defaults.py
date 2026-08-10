# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from pathlib import Path

DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800

DEFAULT_CASE_DIRECTORY = str(Path.home())

# Theme mode: "system" follows the desktop, "light"/"dark" force a Fusion palette.
DEFAULT_THEME = "system"

# Extra scaling for the whole interface, in percent. 100 means "none": Qt's own
# high-DPI handling is left to do the job, which is right whenever the desktop
# tells Qt the display's real DPI. This setting is for the case where it does
# not — Qt derives its scale factor from Xft.dpi on X11, so a session that
# scales through GDK, or a fractionally scaled XWayland one, leaves Qt at 1×
# and every window looks half-size next to its GTK neighbours.
DEFAULT_UI_SCALE = 100

# Offered in Settings > UI Scale. Any percentage works when written into the
# config by hand; these are just the ones worth a menu row.
UI_SCALE_CHOICES = (100, 125, 150, 175, 200)

# Bounds for what is accepted from the config file or the command line. A
# hand-edited 5000 would open a window with room for about two menu items and
# no way to reach the setting that caused it.
MIN_UI_SCALE, MAX_UI_SCALE = 50, 400

# Reopen the last session's layout, case and files at startup. On by default:
# the window size has always been restored, so a clean-slate launch was never
# what this application promised. Settings > Restore Last Session turns it off.
DEFAULT_RESTORE_SESSION = True
