# Foam Dictionary Editor (FoDE) — Developer Guide

For user documentation, see [USER_GUIDE.md](USER_GUIDE.md).
For installation and basic usage, see [README.md](README.md).

## Project structure

A typical project layout is as follows.

```text
foam-dictionary-editor/
├── docs/
│   └── images/              # screenshots used in USER_GUIDE.md
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── requirements-packaging.txt
├── README.md
├── README_ja.md
├── USER_GUIDE.md
├── USER_GUIDE_ja.md
├── app_config.json          # application settings (created when a case is first opened)
├── schema_config.json       # schema module list (created when schema settings are changed)
├── app_config/
│   ├── __init__.py
│   ├── app_config_manager.py
│   ├── constants.py
│   └── defaults.py
├── foam/
│   ├── lexer.py
│   ├── nodes.py
│   ├── parser.py
│   ├── utils.py
│   └── writer.py
├── model/
│   └── tree_model.py
├── schemas/
│   ├── __init__.py
│   ├── _base.py
│   ├── builtin.py
│   ├── config_store.py
│   ├── block_mesh_dict.py
│   ├── control_dict.py
│   ├── fv_schemes.py
│   ├── fv_solution.py
│   ├── snappy_hex_mesh_dict.py
│   └── registry.py
├── services/
│   ├── case_copier.py
│   ├── case_files_config.py
│   └── case_loader.py
├── ui/
│   ├── _boundary_ops.py        # mixin: boundary view patch operations
│   ├── _case_ops.py            # mixin: open/duplicate/save-as case, settings
│   ├── _file_ops.py            # mixin: per-file load/save/create/delete
│   ├── _tree_ops.py            # mixin: tree mutations and editor↔tree sync
│   ├── add_files_dialog.py
│   ├── case_library_dialog.py
│   ├── clean_backups_dialog.py
│   ├── code_editor.py
│   ├── detail_panel.py
│   ├── duplicate_case_dialog.py
│   ├── editor_panel.py
│   ├── file_list_panel.py
│   ├── layout_constants.py
│   ├── main_window.py          # core: __init__, _build_ui, shared helpers
│   ├── manage_extra_files_dialog.py
│   ├── reset_settings_dialog.py
│   ├── save_as_new_case_dialog.py
│   ├── schema_manager_dialog.py
│   └── terminal_panel.py
└── tests/
    ├── conftest.py
    ├── test_app_config.py
    ├── test_backup.py
    ├── test_case_files_config.py
    ├── test_case_loader.py
    ├── test_duplicate_case.py
    ├── test_file_list_panel.py
    ├── test_main_window_split.py
    ├── test_parser_control_dict.py
    ├── test_parser_fv_schemes.py
    ├── test_parser_fv_solution.py
    ├── test_parser_set_fields_dict.py
    ├── test_schemas.py
    ├── test_terminal_panel.py
    ├── test_tree_copy_paste.py
    ├── test_tree_model.py
    ├── test_utils.py
    └── test_writer_roundtrip.py
```

`test_case_loader.py` covers `detect_time_dirs`; `test_file_list_panel.py` covers `_make_time_dirs_indicator` and the panel's time-dirs display; `test_main_window_split.py` verifies the mixin structure — that each mixin owns the right methods, there are no cross-mixin duplicates, and `MainWindow` inherits from all four mixins.

## Setup

Python 3.10 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Run

```bash
python3 main.py
```

After startup, use **Case > Open Case** to select an OpenFOAM case directory, and then choose a file from the file list. `app_config.json` is created automatically the first time a case is opened. `schema_config.json` is created only when schema settings are explicitly changed via the Settings menu.

If the selected directory does not contain a `system/` or `constant/` subdirectory, a warning dialog is shown before the case is loaded. You can open the directory anyway or cancel and select a different one.

## Testing

```bash
python3 -m pytest -q
```

If `pytest -q` causes import issues, running it as `python3 -m pytest -q` is safer because the project root is handled more reliably.

## Acknowledgements

- [PyInstaller](https://pyinstaller.org/) — Used to build standalone executables.
