# Foam Dictionary Editor (FoDE) — 開発者ガイド

ユーザー向けドキュメントは [USER_GUIDE_ja.md](USER_GUIDE_ja.md) を参照してください。
インストールと基本的な使い方は [README_ja.md](README_ja.md) を参照してください。

## プロジェクト構成

現在の代表的なディレクトリ構成は次の通りです。

```text
foam-dictionary-editor/
├── docs/
│   └── images/              # USER_GUIDE.md で使用するスクリーンショット
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── requirements-packaging.txt
├── README.md
├── README_ja.md
├── USER_GUIDE.md
├── USER_GUIDE_ja.md
├── app_config.json          # アプリ設定（初回ケースオープン時に作成）
├── schema_config.json       # スキーマモジュール一覧（スキーマ設定変更時に作成）
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
│   ├── _boundary_ops.py        # Mixin: バウンダリビューのパッチ操作
│   ├── _case_ops.py            # Mixin: ケースの開く・複製・名前を付けて保存・設定
│   ├── _file_ops.py            # Mixin: ファイルの読み込み・保存・作成・削除
│   ├── _tree_ops.py            # Mixin: ツリー編集とエディタ↔ツリー同期
│   ├── add_files_dialog.py
│   ├── case_library_dialog.py
│   ├── clean_backups_dialog.py
│   ├── code_editor.py
│   ├── detail_panel.py
│   ├── duplicate_case_dialog.py
│   ├── editor_panel.py
│   ├── file_list_panel.py
│   ├── layout_constants.py
│   ├── main_window.py          # コア: __init__、_build_ui、共通ヘルパー
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

`test_case_loader.py` は `detect_time_dirs` を、`test_file_list_panel.py` は `_make_time_dirs_indicator` とパネルの時刻ディレクトリ表示を検証します。`test_main_window_split.py` は Mixin 構造を検証します（各 Mixin が正しいメソッドを保有し、Mixin 間の重複がなく、`MainWindow` が 4 つすべての Mixin を継承していることを確認します）。

## セットアップ

Python 3.10 以上を推奨します。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## 実行

```bash
python3 main.py
```

起動後は **Case > Open Case** から OpenFOAM ケースディレクトリを選択し、ファイル一覧から対象ファイルを選んでください。`app_config.json` は初めてケースを開いたときに自動作成されます。`schema_config.json` は Settings メニューからスキーマ設定を変更したときにのみ作成されます。

選択したディレクトリに `system/` も `constant/` も存在しない場合は、有効な OpenFOAM ケースでない可能性を示す警告ダイアログが表示されます。それでも開くことは可能です。

## テスト

```bash
python3 -m pytest -q
```

`pytest -q` だと import 周りで問題が出る場合は、プロジェクトルートの扱いが安定しやすい `python3 -m pytest -q` を使う方が安全です。

## 謝辞

- [PyInstaller](https://pyinstaller.org/) — スタンドアロン実行ファイルのビルドに使用。
