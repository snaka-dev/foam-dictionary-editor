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
├── app_config.json          # アプリ設定（初回ケースオープン時に作成、git 管理外）
├── schema_config.json       # スキーマモジュール一覧（スキーマ設定変更時に作成）
├── presets/
│   ├── standard.json                # features: terminal + blockmesh
│   ├── no-terminal.json             # features: terminal=false, blockmesh=false
│   └── no-terminal-blockmesh.json   # features: terminal=false, blockmesh=true
├── app_config/
│   ├── __init__.py
│   ├── app_config_manager.py
│   ├── constants.py
│   └── defaults.py
├── foam/
│   ├── block_mesh_extractor.py  # blockMeshDict の FoamNode ツリーから頂点・ブロック・境界を抽出。parse_vertices() はパブリック API
│   ├── diff.py                  # diff_trees(a, b) と diff_trees_reverse(b, a) — キー名で 2 つの FoamNode ツリーを比較し dict[FoamNode, DiffEntry] を返す
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
├── i18n/
│   ├── __init__.py             # tr()、set_language()、get_language()、available_languages()
│   └── ja.py                   # 日本語翻訳（LANGUAGE_NAME + TRANSLATIONS 辞書）
├── ui/
│   ├── _boundary_ops.py        # Mixin: バウンダリビューのパッチ操作
│   ├── _case_ops.py            # Mixin: ケースの開く・再読み込み・複製・名前を付けて保存・設定
│   ├── _file_ops.py            # Mixin: ファイルの読み込み・保存・作成・削除
│   ├── _tree_ops.py            # Mixin: ツリー編集、エディタ↔ツリー同期、_apply_comparison_value
│   ├── block_mesh_panel.py     # blockMeshDict 用 3D ビューア（pyVista/VTK、遅延初期化）
│   ├── add_files_dialog.py
│   ├── case_library_dialog.py
│   ├── clean_backups_dialog.py
│   ├── code_editor.py
│   ├── detail_panel.py
│   ├── duplicate_case_dialog.py
│   ├── comparison_tree_panel.py  # 読み取り専用の参照ケースツリー。use_value_requested(FoamNode) シグナルを発行
│   ├── editor_panel.py
│   ├── file_list_panel.py
│   ├── layout_constants.py
│   ├── keyboard_shortcuts_dialog.py
│   ├── main_window.py          # コア: __init__、_build_ui とサブビルダー、共通ヘルパー、diff/compare ロジック
│   ├── manage_extra_files_dialog.py
│   ├── rename_boundary_dialog.py  # Rename Boundary ダイアログ + find_rename_targets() スキャナ
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
    ├── test_parser_block_mesh_dict.py
    ├── test_parser_control_dict.py
    ├── test_parser_fv_schemes.py
    ├── test_parser_fv_solution.py
    ├── test_parser_set_fields_dict.py
    ├── test_schemas.py
    ├── test_terminal_panel.py
    ├── test_bool_nonuniform.py
    ├── test_source_lines.py
    ├── test_tree_color_lexer_dispatch.py
    ├── test_tree_copy_paste.py
    ├── test_rename_boundary.py
    ├── test_comparison_tree_panel.py
    ├── test_diff.py
    ├── test_tree_model.py
    ├── test_utils.py
    └── test_writer_roundtrip.py
```

`test_utils.py` は `is_large_non_foam_file` を検証します（小さいファイルはヘッダーの有無にかかわらずフラグが立たないこと、最初の 512 バイト内に `FoamFile` トークンを含む大きいファイルはフラグが立たないこと、含まない大きいファイルはフラグが立つこと、存在しないファイルは `(False, 0)` を返すこと、コメントの後にヘッダーがある場合も正しく検出されることを含む）。`test_diff.py` は `diff_trees` と `diff_trees_reverse` を検証します（同一ツリー、値の変更、片方のみに存在するキー、ネストした辞書、匿名ノードのスキップ、`field_value_block` エントリ、両関数の対称性を含む）。`FoamNode` は `__hash__ = object.__hash__` を持ち、差分マップのキーとして使用可能です。`test_comparison_tree_panel.py` は `ComparisonTreePanel` を検証します（`load` でヘッダーラベルを設定しプロキシを更新して FoamFile ノードを折りたたみ Type 列の表示を再適用すること、`clear` でモデルとヘッダーをリセットすること、`set_type_column_visible` で Type 列の表示を切り替え `load` をまたいで状態が維持されること、`use_value_requested` シグナルが接続可能なことを含む）。`test_tree_model.py` は `set_diff(reverse=True)` を検証します（`"only_here"` を `"only_in_ref"` にリマップし `"changed"` は変更しないこと、淡緑色の `BackgroundRole` を返すこと、`"only in reference case"` をツールチップに含むことを含む）。`test_file_list_panel.py` は差分フィルターを検証します（`set_diff_filter_enabled` でチェックボックスの表示・非表示・チェック解除、フィルターが差分件数 0 のファイルアイテムを非表示にしヘッダーは常に表示、`mark_diff` がフィルター有効時に即座にアイテムの表示を更新することを含む）。`test_case_loader.py` は `detect_time_dirs` と `TestExtraDirs`（フラット・再帰スキャン、存在しないディレクトリの許容、重複排除）を検証します。`test_case_files_config.py` は `TestCaseFilesConfigDirs`（`DirEntry` の追加・削除・インプレース更新、プレーン文字列 JSON の後方互換ロード、設定リセット）を検証します。`test_main_window_split.py` は Mixin 構造を検証します（各 Mixin が正しいメソッドを保有し（`_BoundaryOpsMixin` の `_on_patch_selected`、`_TreeOpsMixin` の `_apply_comparison_value` を含む）、Mixin 間の重複がなく、`MainWindow` が 4 つすべての Mixin を継承していることを確認します）。`test_bool_nonuniform.py` は bool/nonuniform_list のパースとパースエラー収集を検証します。`test_tree_color_lexer_dispatch.py` は `unknown_raw_entry` の琥珀色表示、レキサーの `//` 挙動、パーサの `_PAREN_DISPATCH` テーブルを検証します。`test_source_lines.py` はすべてのノード型に対する `source_line` および `source_end_line` の設定を検証します。`test_parser_block_mesh_dict.py` は `boundary_block`/`boundary_entry` の構造的パース、ライタの round-trip、および `blockMeshDict` に対する `extract_block_mesh_data` の出力を検証します。`test_rename_boundary.py` は `find_rename_targets()` を検証します（`blockMeshDict` 内の `boundary_entry` ノードおよび `boundaryField` ブロック内のパッチ `dictionary` ノードの検出、無関係な辞書への誤検出なし、空入力のエッジケースを含む）。

## 国際化（i18n）

`ui/` 内のユーザー向け文字列はすべて `i18n/__init__.py` の `tr()` でラップされています。英語の文字列がそのままキーとして機能し、翻訳が存在しない場合は英語にフォールバックします。

**実行時の流れ**
1. `main.py` がウィンドウ作成前に `set_language(get_app_config().get_language())` を呼び出します。
2. 各ウィジェットのコンストラクタが `tr("some string")` をインスタンス化時に呼び出すため、選択言語が起動時に UI 全体へ適用されます。
3. 言語変更はアプリ再起動後に反映されます（ライブ再翻訳なし）。

**新しい言語を追加する方法**

`i18n/<コード>.py` を作成するだけで、他のファイルの変更は不要です:

```python
LANGUAGE_NAME = "Italiano"          # Settings > Language メニューに表示される名前

TRANSLATIONS: dict[str, str] = {
    "Open Case": "Apri caso",
    "Save File": "Salva file",
    # ... 必要な分だけ追加。未翻訳キーは英語にフォールバック
}
```

`i18n/__init__.py` の `available_languages()` が `i18n/` ディレクトリ内の `.py` ファイルを自動検出するため、追加の変更なく新言語が Settings メニューに表示されます。

**保存形式** — 選択した言語コードは `app_config.json` の `"language"` キーに保存されます。デフォルトの `"en"` の場合はキー自体が省略され、設定ファイルをシンプルに保ちます。

## 追加ディレクトリ

`case_files_config.py` は、ケースごとの追加ディレクトリ一覧を `list[DirEntry]` として保存します。`DirEntry = tuple[str, bool]` は `(rel_path, recursive)` を表します。このフラグにより、ディレクトリをフラットスキャン（`Path.iterdir()`）するか再帰スキャン（`Path.rglob("*")`）するかが決まります。

- `add_dir(rel_path, recursive=False)` は新規エントリを追加するか、パスが既に存在する場合はフラグをインプレースで更新します。
- `remove_dir(rel_path)` はパスで絞り込んでエントリを除去します。
- JSON は `[{"path": "...", "recursive": true/false}]` 形式で保存されます。プレーン文字列を格納した旧 JSON は後方互換のため非再帰として読み込まれます。

`case_loader.py` の `list_case_files` は `extra_dirs: list[tuple[str, bool]] | None` を受け取ります。フラットエントリは `sorted(d.iterdir(), key=...)` で、再帰エントリは `sorted(d.rglob("*"), key=lambda p: (str(p.parent), p.name.lower()))` で処理され、ディレクトリ→ファイル名の順に並びます。`TARGET_FILES` と共有する重複排除セットにより、同一パスが 2 回現れることはありません。

`manage_extra_files_dialog.py` では **Toggle Recursive** ボタンで選択中のディレクトリエントリの再帰フラグを切り替えられます。生パスは各アイテムの `Qt.UserRole` に格納され、再帰が有効な場合は表示テキストに `[recursive]` が付加されます。`result_dirs` プロパティは最終的な `list[DirEntry]` を返します。`_file_ops.py` はこの値を使ってステータスバーの集計（追加・削除・フラグ変更の件数）を計算します。

## セットアップ

Python 3.10 以上を推奨します。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## 実行

```bash
python3 main.py                                   # 標準（ターミナル + BlockMesh）
python3 main.py --variant no-terminal             # ターミナルタブなし
python3 main.py --variant no-terminal-blockmesh   # ターミナルなし + BlockMesh 常時表示
```

`--variant` フラグは `presets/<name>.json` を読み込み、設定シングルトンの `features` 辞書を上書きして、終了時に `app_config.json` へ保存します。次回以降は `--variant` なしでも保存した設定が使われます。`features` キーがない場合はすべて `true` として扱われるため、開発者個人の `app_config.json`（git 管理外で通常 `features` キーを持たない）は常に標準モードで動作します。

起動後は **Case > Open Case** から OpenFOAM ケースディレクトリを選択し、ファイル一覧から対象ファイルを選んでください。`app_config.json` は初めてケースを開いたときに自動作成されます。`schema_config.json` は Settings メニューからスキーマ設定を変更したときにのみ作成されます。

選択したディレクトリに `system/` も `constant/` も存在しない場合は、有効な OpenFOAM ケースでない可能性を示す警告ダイアログが表示されます。それでも開くことは可能です。

## GPU / OpenGL に関する注意

Linux 上では、次の 2 つのサブシステムが GPU に同時アクセスします。

- **VTK / pyVista**（`block_mesh_panel.py`）— `QtInteractor` 経由で OpenGL を使用し 3D レンダリングを行います。`features.blockmesh=true` のときのみ存在します。
- **Qt WebEngine**（`terminal_panel.py`、xterm モード）— 独自の GPU プロセスを持ちます。`features.terminal=true` のときのみ存在します。

これら 2 つは同一 GPU コンテキストに安全に共存できません。`main.py` で次の回避策を適用しています。

1. `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --disable-vulkan --log-level=2` を設定し、WebEngine を SwiftShader（CPU ソフトウェアレンダリング）で強制起動することで GPU を VTK 専用に開放します。`--log-level=2` は `--disable-gpu` の副作用として表示される "GPUInfo not initialized on GpuInfoUpdate" という Chromium の警告を抑制します。
2. 起動時に `block_mesh_panel` が `None` でなく、かつターミナルが存在しないかシンプルモードの場合は、`QTimer.singleShot(0, block_mesh_panel._init_plotter)` で VTK を先行初期化し、ユーザー操作より前に OpenGL コンテキストを確保します。

ターミナルモードの切替（`TerminalPanel.mode_changed` シグナル）では、xterm 起動前に VTK をシャットダウンし、シンプルモードへ戻る際に 300 ms の遅延後に VTK を再初期化します。このシグナルは `terminal` と `blockmesh` の両方が有効なときのみ接続されます。

**View メニューのアクション** — `_build_menu_bar` 内の `_blockmesh_action`（`QAction`、チェック式）は、ターミナルモードとは独立して BlockMesh タブを表示・非表示にする第 2 の手段です。xterm が有効な場合はアクションが無効化され、テキストが `"BlockMesh 3-D Panel  (unavailable: xterm active)"` に変わって理由をホバーなしで表示します。`_on_terminal_mode_changed` がアクションの有効状態とラベルをターミナルモードと同期させ、`_on_toggle_blockmesh_panel` がユーザーのクリック時に実際のタブ追加・削除を処理します。

**Axes ウィジェット** — `add_axes()` は `vtkOrientationMarkerWidget` を生成します。このウィジェットはアクター（`plotter.clear()` で消去される）ではないため、`clear()` をまたいで持続します。そのため `_init_plotter()` で一度だけ呼び出します。`_render()` では毎フレーム再追加するのではなく `show_axes()` / `hide_axes()` でトグルします。

## ツリーとエディタの同期

ツリーノードを選択すると、対応するソース行がテキストエディタで琥珀色の背景でハイライトされ、オプションでその行にスクロールします。仕組みは以下の通りです。

**パーサ側** — `FoamNode` には 1 ベースの行番号フィールドが 2 つあります。`source_line`（ソース内のエントリの先頭行）と `source_end_line`（末尾行）です。パーサは `_finalize_node` および `_parse_dictionary_entry` 内で `_token_line(token_index)` を使ってこれらを設定します。`_token_line` はトークンの文字オフセットまでのソーステキスト中の改行数を数えることで行番号を求めます。

**UI 側** — `CodeEditor` は `_span_start_line` / `_span_end_line` を保持します。`set_span_highlight(start, end)` でこの範囲を保存し `highlight_current_line` をトリガーします。`highlight_current_line` は `setExtraSelections` で琥珀色のスパン（背景）と青い現在行ハイライト（前面）を重ねて描画します。`EditorPanel` は `jump_to_node(start, end, scroll=True)`（ハイライト＋オプショナルスクロール）と `clear_node_highlight()` を公開します。

**状態ガード** — `MainWindow._source_lines_valid` は `_load_tree` 呼び出し後（ファイル読み込みまたは Apply Text to Tree）に `True` になり、ユーザーがエディタテキストを編集した瞬間（`_on_user_text_changed`）に `False` になります。`on_tree_selection` はこのフラグが `False` の場合にジャンプとハイライトをスキップし、古い行番号への誤ジャンプを防ぎます。`_update_sync_checkbox` はこの有効/古いの状態をチェックボックスのラベル・スタイル・ツールチップに反映します。

**エディタ → ツリー方向** — `_sync_tree_to_editor_line` は現在のエディタカーソル行を読み取り、`_find_deepest(root, line)` を呼び出して `source_line ≤ line ≤ source_end_line` を満たす最も内側のノードを探します。結果が見つかればツリーをそのノードまでスクロールして選択します。一致したノードがプロキシモデルでフィルタリングされている場合は、表示中の最も近い祖先まで遡ります。このメソッドは Editor ツールバーの **Find in Tree** ボタンと `Ctrl+Shift+T` ショートカットで呼び出されます。

## バウンダリパネルとエディタのナビゲーション

Boundary パネルのセルをクリックすると `patch_selected(path, patch_name)` シグナルが発行され、`_BoundaryOpsMixin` の `_on_patch_selected` が処理します。ツリーのナビゲーション（`source_line` を使用）と異なり、バウンダリのナビゲーションはテキスト検索を使います。これは `write_root()` がバウンダリ編集後にテキストを再生成するため、ソース行番号がすぐに古くなるからです。

`EditorPanel.jump_to_text(text)` はドキュメント先頭から `QTextDocument.find(text, 0, FindWholeWords)` を呼び出します。一致が見つかった場合、マッチしたブロック番号に対して `set_span_highlight(line, line)` と `goto_line(line)` を呼び出します。`boundaryField` 内のパッチ名はファイル内で一意のため、最初のヒットが常に正しい位置です。

クリックしたセルのファイルが `current_file` と異なる場合、`_on_patch_selected` はまず `load_selected_file(path)` を呼び出して（`current_file` を設定）、続いて `file_list_panel.select_file(path)` でファイルリストのハイライトを同期します。その結果発行される `file_selected` シグナルによって再入する `load_selected_file` は、`current_file` が既に設定済みのため no-op になります。

Boundary パネルツールバーの **Auto-scroll editor** チェックボックスは `_on_cell_clicked` 内での `patch_selected` 発行を制御します。オフの場合、シングルクリックはエディタに影響しません。

`BoundaryViewPanel._table_data()` は現在の `QTableWidget` の状態から `(col_headers, row_headers, rows)` を取り出します。`_copy_as_markdown()` はこのデータから GitHub Flavored Markdown のパイプテーブルを構築し、システムクリップボードへ書き込みます（セルテキスト内の `\n` は `<br>` に変換）。`_copy_as_csv()` は RFC 4180 準拠の CSV を書き込み、複数行のセル内容は引用符付きフィールドとして保持されます。どちらのメソッドも既にレンダリング済みのテーブルから読み取るため、転置状態に自動的に対応します。

## テスト

```bash
python3 -m pytest -q
```

`pytest -q` だと import 周りで問題が出る場合は、プロジェクトルートの扱いが安定しやすい `python3 -m pytest -q` を使う方が安全です。

## 謝辞

- [PyInstaller](https://pyinstaller.org/) — スタンドアロン実行ファイルのビルドに使用。
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — `blockMeshDict` の 3D ビューア（BSD-3-Clause、オプション）。
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — テストフレームワーク。

[OpenFOAM Foundation](https://openfoam.org/) および [OpenCFD / ESI Group](https://www.openfoam.com/) をはじめ、OpenFOAM をフリーのオープンソース CFD ソフトウェアとして開発・維持してきたすべての貢献者の方々に深く感謝いたします。
