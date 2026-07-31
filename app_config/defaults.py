# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from pathlib import Path

DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800

DEFAULT_CASE_DIRECTORY = str(Path.home())

# Theme mode: "system" follows the desktop, "light"/"dark" force a Fusion palette.
DEFAULT_THEME = "system"

# Reopen the last session's layout, case and files at startup. On by default:
# the window size has always been restored, so a clean-slate launch was never
# what this application promised. Settings > Restore Last Session turns it off.
DEFAULT_RESTORE_SESSION = True
