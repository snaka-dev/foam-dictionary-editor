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
│   ├── block_mesh_extractor.py  # blockMeshDict の FoamNode ツリーから頂点・ブロック・境界を抽出。_build_var_map が任意の深さの $変数チェーン（`-$xMax` のような否定マクロ word ノードを含む）と #eval{} 式を反復的に解決。_HEX_FACE_VERTICES + _expand_compact_faces がコンパクト (blockIdx, faceIdx) 境界エントリを 4 頂点リストに展開。parse_vertices() はパブリック API
│   ├── diff.py                  # diff_trees(a, b) と diff_trees_reverse(b, a) — キー名で 2 つの FoamNode ツリーを比較し dict[FoamNode, DiffEntry] を返す
│   ├── lexer.py                 # OpenFoamLexer。_read_directive は '{' で読み取りを停止するため、#eval{...} の波括弧が LBRACE/RBRACE トークンになり深さ追跡が正しく機能する
│   ├── nodes.py
│   ├── parser.py
│   ├── utils.py
│   └── writer.py
├── model/
│   ├── boundary_model.py   # BoundaryModel（QAbstractTableModel）+ extract_boundary()
│   ├── file_list_model.py  # FileListModel（QAbstractListModel）
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
│   ├── app_state.py            # AppState データクラス: 共有可変フィールド 18 個。MainWindow が self.state = AppState() で生成
│   ├── mixins/
│   │   ├── _boundary_ops.py        # Mixin: バウンダリビューのパッチ操作
│   │   ├── _case_ops.py            # Mixin: ケースの開く・再読み込み・複製・名前を付けて保存・設定
│   │   ├── _diff_ops.py            # Mixin: サイドバイサイド比較、差分の計算・クリア
│   │   ├── _file_mgmt_ops.py       # Mixin: ファイルの作成・追加・バックアップ・削除・複製・クリーンアップ
│   │   ├── _file_ops.py            # Mixin: ファイルの読み込み・保存、ディレクトリスキャンヘルパー
│   │   ├── _foam_monitor_ops.py    # Mixin: foamMonitor の起動・停止・ポーリング、gnuplot reread パッチ
│   │   ├── _panel_ops.py           # Mixin: BlockMesh パネルおよびターミナルモード切替ハンドラ
│   │   └── _tree_ops.py            # Mixin: ツリー編集、エディタ↔ツリー同期、_apply_comparison_value
│   ├── layout_constants.py
│   ├── main_window.py          # コア: __init__、_build_ui とサブビルダー、共通ヘルパー、ドラッグ＆ドロップ（dragEnterEvent/dropEvent/eventFilter）
│   ├── dialogs/
│   │   ├── about_dialog.py
│   │   ├── add_files_dialog.py
│   │   ├── boundary_edit_dialog.py
│   │   ├── case_library_dialog.py
│   │   ├── clean_backups_dialog.py
│   │   ├── duplicate_case_dialog.py
│   │   ├── foam_monitor_dialog.py  # FoamMonitorDialog: ファイル選択 + foamMonitor オプション（対数スケール、グリッド、リフレッシュ間隔、アイドルタイムアウト、追加フラグ）
│   │   ├── keyboard_shortcuts_dialog.py
│   │   ├── manage_extra_files_dialog.py
│   │   ├── openfoam_resources_dialog.py
│   │   ├── rename_boundary_dialog.py  # Rename Boundary ダイアログ + find_rename_targets() スキャナ
│   │   ├── reset_settings_dialog.py
│   │   ├── save_as_new_case_dialog.py
│   │   └── schema_manager_dialog.py
│   ├── panels/
│   │   ├── block_mesh_panel.py     # blockMeshDict 用 3D ビューア（pyVista/VTK、遅延初期化）
│   │   ├── boundary_view_panel.py
│   │   ├── comparison_tree_panel.py  # 読み取り専用の参照ケースツリー。use_value_requested(FoamNode) シグナルを発行
│   │   ├── detail_panel.py
│   │   ├── editor_panel.py
│   │   ├── file_list_panel.py
│   │   └── terminal_panel.py       # TerminalPanel ラッパー: mode_changed シグナル、xterm/simple 切替ロジック
│   └── widgets/
│       ├── code_editor.py
│       ├── _simple_terminal_widget.py  # SimpleTerminalWidget: QProcess ベースターミナル（WebEngine 不要）
│       └── _xterm_widget.py            # PtyBackend、TerminalBridge、XtermTerminalWidget（Unix + QtWebEngine 専用）。_XTERM_AVAILABLE をエクスポート
└── tests/
    ├── conftest.py
    ├── foam/
    │   ├── test_diff.py
    │   ├── test_parser_block_mesh_dict.py
    │   ├── test_parser_control_dict.py
    │   ├── test_parser_fv_schemes.py
    │   ├── test_parser_fv_solution.py
    │   ├── test_parser_set_fields_dict.py
    │   ├── test_source_lines.py
    │   ├── test_utils.py
    │   └── test_writer_roundtrip.py
    ├── model/
    │   ├── test_bool_nonuniform.py
    │   ├── test_boundary_model.py
    │   ├── test_file_list_model.py
    │   └── test_tree_model.py
    ├── ui/
    │   ├── test_boundary_view_copy.py
    │   ├── test_comparison_tree_panel.py
    │   ├── test_drag_drop_open_case.py
    │   ├── test_duplicate_case.py
    │   ├── test_file_list_panel.py
    │   ├── test_main_window_split.py
    │   ├── test_manage_extra_files_dialog.py
    │   ├── test_rename_boundary.py
    │   ├── test_terminal_panel.py
    │   ├── test_tree_color_lexer_dispatch.py
    │   └── test_tree_copy_paste.py
    ├── services/
    │   ├── test_backup.py
    │   ├── test_case_files_config.py
    │   └── test_case_loader.py
    ├── app_config/
    │   └── test_app_config.py
    └── schemas/
        └── test_schemas.py
```

`test_utils.py` は `is_large_non_foam_file` を検証します（小さいファイルはヘッダーの有無にかかわらずフラグが立たないこと、最初の 512 バイト内に `FoamFile` トークンを含む大きいファイルはフラグが立たないこと、含まない大きいファイルはフラグが立つこと、存在しないファイルは `(False, 0)` を返すこと、コメントの後にヘッダーがある場合も正しく検出されることを含む）。`test_diff.py` は `diff_trees` と `diff_trees_reverse` を検証します（同一ツリー、値の変更、片方のみに存在するキー、ネストした辞書、匿名ノードのスキップ、`field_value_block` エントリ、両関数の対称性を含む）。`FoamNode` は `__hash__ = object.__hash__` を持ち、差分マップのキーとして使用可能です。`test_comparison_tree_panel.py` は `ComparisonTreePanel` を検証します（`load` でヘッダーラベルを設定しプロキシを更新して FoamFile ノードを折りたたみ Type 列の表示を再適用すること、`clear` でモデルとヘッダーをリセットすること、`set_type_column_visible` で Type 列の表示を切り替え `load` をまたいで状態が維持されること、`use_value_requested` シグナルが接続可能なことを含む）。`test_tree_model.py` は `set_diff(reverse=True)` を検証します（`"only_here"` を `"only_in_ref"` にリマップし `"changed"` は変更しないこと、淡緑色の `BackgroundRole` を返すこと、`"only in reference case"` をツールチップに含むことを含む）。`test_file_list_panel.py` は差分フィルターを検証します（`set_diff_filter_enabled` でチェックボックスの表示・非表示・チェック解除、フィルターが差分件数 0 のファイルアイテムを非表示にしヘッダーは常に表示、`mark_diff` がフィルター有効時に即座にアイテムの表示を更新することを含む）。`test_case_loader.py` は `detect_time_dirs` と `TestExtraDirs`（フラット・再帰スキャン、存在しないディレクトリの許容、重複排除）を検証します。`test_case_files_config.py` は `TestCaseFilesConfigDirs`（`DirEntry` の追加・削除・インプレース更新、プレーン文字列 JSON の後方互換ロード、設定リセット）を検証します。`test_main_window_split.py` は Mixin 構造を検証します（各 Mixin が正しいメソッドを保有し（`_BoundaryOpsMixin` の `_on_patch_selected`、`_TreeOpsMixin` の `_apply_comparison_value`、`_FoamMonitorOpsMixin` の foamMonitor 関連メソッドを含む）、Mixin 間の重複がなく、`MainWindow` がすべての Mixin を継承していることを確認します）。`test_bool_nonuniform.py` は bool/nonuniform_list のパースとパースエラー収集を検証します。`test_tree_color_lexer_dispatch.py` は `unknown_raw_entry` の琥珀色表示、レキサーの `//` 挙動、パーサの `_PAREN_DISPATCH` テーブルを検証します。`test_source_lines.py` はすべてのノード型に対する `source_line` および `source_end_line` の設定を検証します。`test_parser_block_mesh_dict.py` は `boundary_block`/`boundary_entry` の構造的パース、ライタの round-trip、`blockMeshDict` に対する `extract_block_mesh_data` の出力、変数解決（`$varName`、`${varName}`、マクロ参照、`-$xMax` のような否定マクロ word ノード、`#eval{ expr }` 算術式、多段依存チェーン）、コンパクト `(blockIndex, faceIndex)` 境界面記法（4 頂点リストへの展開、否定マクロ頂点変数との組み合わせを含む）を検証します。`test_rename_boundary.py` は `find_rename_targets()` を検証します（`blockMeshDict` 内の `boundary_entry` ノードおよび `boundaryField` ブロック内のパッチ `dictionary` ノードの検出、無関係な辞書への誤検出なし、空入力のエッジケースを含む）。

## パーサとデータモデル

### ノード型

**リーフ値型** — `foam/parser.py:387` の `_classify_value` と `foam/utils.py:113` の `classify_parenthesized_value` によって設定されます。

| `node_type` | `value` の Python 型 | 生成条件 |
|---|---|---|
| `int` | `int` | 裸の整数トークン（`"."` と `"e"` を含まない） |
| `scalar` | `float` | 裸の浮動小数点トークン |
| `bool` | `str` | `BOOL_WORDS` 内のトークン: `true` / `false` / `on` / `off` / `yes` / `no` |
| `word` | `str` | その他の単一トークン（フォールバック） |
| `string` | `str` | ダブルクォートで囲まれたトークン（`"…"`） |
| `macro` | `str` | `$` で始まるトークン |
| `compound` | `str` | 括弧なしの複数の空白区切りトークン |
| `nonuniform_list` | `str` | `nonuniform List<T> N (…)` — `compound` より先に検出される特殊ケース |
| `vector` | `list[float]`（長さ 3） | `(x y z)` — 括弧内にちょうど 3 つの数値トークン |
| `int_list` | `list[int]` | `(a b …)` — 括弧内がすべて整数トークン |
| `scalar_list` | `list[float]` | `(a b …)` — 括弧内がすべて数値トークン（3 つでないもの） |
| `raw_list` | `str`（内側テキスト） | `(…)` — 混在またはネストしたコンテンツ |
| `box_pair` | `list[list[float]]`（2×3） | `(x y z) (x y z)` — `box` キーにのみ生成 |

**構造型** — `_parse_entry` / `_parse_dictionary_entry` / `_parse_named_dict_block` によって設定されます。

| `node_type` | 説明 |
|---|---|
| `dictionary` | `key { … }` ブロック。`value=None`、子ノードが展開される |
| `field_value_block` | `defaultFieldValues / fieldValues ( … );` |
| `field_value` | `field_value_block` 内の個別アイテム |
| `region_block` | `regions ( … );` |
| `region_entry` | `region_block` 内の名前付き `{ … }` エントリ |
| `boundary_block` | `blockMeshDict` の `boundary ( … );` |
| `boundary_entry` | `boundary_block` 内の名前付き `{ … }` エントリ |
| `directive_entry` | `#include`、`#inputMode` など。`name=""` |
| `macro_entry` | 単独の `$macro;`。`name=""` |
| `unknown_raw_entry` | パース失敗時のフォールバック。生テキストが `value` に逐語的に保持される |

### 分類ロジック

`_classify_value(key, text)`（`foam/parser.py:387`）は、波括弧・特殊括弧以外のすべてのエントリに対して呼ばれます。優先順位は次の通りです。

1. **`box_pair`** — `key == "box"` かつ `foam/utils.py` の `parse_box_pair(text)` が成功する場合のみ。
2. **括弧付き** — `classify_parenthesized_value`（`foam/utils.py:113`）に委譲。`vector`（ちょうど 3 つの float）、`int_list`（すべて整数）、`scalar_list`（すべて数値で 3 つでない）、`raw_list`（それ以外）を返す。
3. **`string`** — `"` で始まり `"` で終わる。
4. **`macro`** — `$` で始まる。
5. **空白を含む** — `nonuniform List…` で始まる場合は `nonuniform_list`、それ以外は `compound`。
6. 単一トークン: `int` → `scalar` → `bool`（`BOOL_WORDS` 内のトークン）→ `word`（フォールバック）。

### 再パースのトリガー

パーサが実行され（ツリーが再構築され）るのは正確に 2 つのタイミングだけです。

- **ファイルオープン** — ファイル一覧でファイルが選択されたとき、またはプログラムから読み込まれたとき。
- **Apply Text to Tree** — アクションバーの手動ボタン。

キーストロークやファイル保存では自動再パースは行われません。テキストエディタを手動編集すると、ツリーとソース行番号は古い状態になります。この状態は、次のパースまで「Auto-scroll editor (stale)」というラベルで示されます。

### エラーリカバリ

`_parse_entry` が `ParseError` を送出すると、パーサは `start_index` まで巻き戻し、エラーを `self.errors` に記録して `_parse_unknown_raw_entry` を呼び出します。このメソッドは次の `;` または行末までトークンを消費し、生テキストを `unknown_raw_entry` ノードにラップしてパースを継続します。ファイルは引き続き利用可能で、生テキストは保存時にそのまま書き戻されます。パース完了後、`OpenFoamParser.errors` にすべてのリカバリイベントが格納され、呼び出し元がステータスバーに「N unrecognized entries」として件数を報告します。

### FoamNode フィールドの意味

`FoamNode`（`foam/nodes.py`）は `name`、`node_type`、`value` 以外にも、パーサとライタが連携して使用するフィールドを持ちます。

| フィールド | 型 | 用途 |
|---|---|---|
| `modified` | `bool` | `FoamTreeModel.setData` でキーまたは値が変更されたときに `True` になる。ライタの再生成判断を駆動する。 |
| `raw_text` | `str` | `_finalize_node` と `_parse_dictionary_entry` がキャプチャするノードの元のソーステキスト。変更されていないノードに対してライタが逐語的に出力する。 |
| `leading_trivia` | `list[str]` | ソース内でノードの前に現れる空白とコメント。ライタの `_with_leading_trivia` がエントリ間の空行を保持するために復元する。 |
| `inline_comment` | `str` | 同一行の値の直後にある `// …` または `/* … */` コメント。`_collect_inline_comment` が収集し、ライタが再現する。 |
| `source_line` / `source_end_line` | `int` | `_token_line` が設定する 1 ベースの行番号。エディタ同期ハイライトに使われる。`0` はツリーで追加されたノードでソース位置情報がないことを意味する。 |

### ライタの raw_text パススルー

`_write_node`（`foam/writer.py:29`）は 3 つの条件がすべて満たされる場合、再生成を完全にスキップします。

```python
if not node.modified and node.raw_text and not _has_modified_descendant(node):
    return _with_leading_trivia(node, node.raw_text)
```

3 つすべてが True の場合、元のソーステキストがそのまま出力され、フォーマット・インラインコメント・正確な空白が保持されます。`modified=True` のノード（または変更済みの子孫を含むノード）のみが再生成されます。未編集のファイルに対する「Reload from Tree」は、`raw_text` がキャプチャされたすべてのエントリでバイト同一の出力を生成します。

`_has_modified_descendant` はほとんどの型で `node.children` を再帰的に辿ります。`field_value_block` については `node.value` も直接チェックします（下記参照）。

### `field_value_block` の子ノードが `value` に格納される

`field_value_block` は子ノードを `node.children` ではなく `node.value`（`list[FoamNode]`）に格納する唯一の構造型です。`FoamTreeModel._child_list`（`model/tree_model.py:159`）がこの特殊ケースを処理します。

```python
if node.node_type == "field_value_block":
    return node.value if isinstance(node.value, list) else []
return node.children
```

`field_value_block` ノードの `node.children` は常に空のリストです。ツリーを汎用的に再帰処理するコードは、この型に対して `node.value` を反復処理する必要があります。ライタ（`foam/writer.py:72`）と `_has_modified_descendant` はどちらも明示的にこれを行います。

### レガシーな `"list"` 型

`"list"` ノード型名は `int_list` が導入される前の互換性のための残存物です。パーサは `"list"` ノードを生成したことがなく、`foam/writer.py` と `model/tree_model.py` にあったそれをチェックするデッドコードのディスパッチ分岐は削除されました。新しいコードでは `"int_list"` のみを生成・期待するようにしてください。

## スキーマシステム

スキーマモジュールは Detail ペインにキーの説明・対応バージョン情報・値の選択肢を提供します。実行時レジストリと基底データクラスは `schemas/` にあります。

### KeySchema と ChoiceItem

`schemas/_base.py` はスキーマモジュールがインポートする 2 つの frozen データクラスを定義します。

```python
@dataclass(frozen=True)
class ChoiceItem:
    value: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""

@dataclass(frozen=True)
class KeySchema:
    key: str
    label: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""
    choices: tuple[ChoiceItem, ...] = ()
```

`_base.py` は `supported_in` タプル用のバージョン文字列定数 `FOUNDATION_V13`、`OPENCFD_V2312`、`OPENCFD_V2512`、`OPENCFD_SERIES` もエクスポートします。スキーマモジュール間でバージョン文字列を統一するためにこれらをインポートします。

### SchemaRegistry

`SchemaRegistry`（`schemas/registry.py`）は `schemas/__init__.py` がインポート時にロードするシングルトンです。`schema_config.json`（ファイルが存在しない場合は組み込みデフォルト）のモジュール名リストから `_file_key_schemas[ファイル名][ドット区切りキー] → KeySchema` の 2 階層辞書を構築します。

`schema_for_file_key(file_path, key_name, parent_key, grandparent_key)` は次の 3 段階のルックアップを実施します。

1. `f"{parent_key}.{key_name}"` — 直接の親コンテキスト。
2. `f"{grandparent_key}.{key_name}"` — 祖父母コンテキスト（名前付き `refinementSurfaces` エントリなど、直接の親がユーザー定義の場合に使用）。
3. プレーンな `key_name` — フラットフォールバック。

`reload()` は `schema_config.json` をディスクから再読み込みしてテーブルを再構築します。`apply_and_reload()` はディスクに触れずに現在のインメモリ設定からテーブルを再構築します（同一セッション内で **Settings > Manage Schema Modules** が変更を適用した後に使用）。

## 差分アルゴリズム

`foam/diff.py` は 2 つの `FoamNode` ツリーを比較し、比較パネルの色付けに使うアノテーションマップを生成します。

### API

```python
DiffEntry = tuple[str, FoamNode | None]

def diff_trees(a: FoamNode, b: FoamNode) -> dict[FoamNode, DiffEntry]: ...
def diff_trees_reverse(b: FoamNode, a: FoamNode) -> dict[FoamNode, DiffEntry]: ...
```

どちらの関数も**第 1 引数**のノードを `(status, ref_node)` ペアにマッピングする `dict` を返します。`diff_trees_reverse` は `diff_trees(b, a)` を呼び出す薄いエイリアスで、アノテーションマップが `b`-ツリーのノードをキーとするため、UI が参照ケースペインをレンダリングする際に使われます。

### ステータス値

| ステータス | 意味 |
|---|---|
| `"changed"` | 両方のツリーにキーが存在するが `node_type` または `value` が異なる。`ref_node` は `b` の一致ノード。 |
| `"only_here"` | `a` にはあるが `b` にはないキー。`ref_node` は `None`。 |

`a` にはなく `b` だけにあるノードは `diff_trees` の結果には含まれません。`FoamTreeModel.set_diff(diff, reverse=True)` は参照ケースモデルにマップをアタッチする際に `"only_here"` を `"only_in_ref"` に再マップします。

### 再帰とスキップ

`_diff_node` は `_RECURSE_TYPES` にリストされた構造型に再帰します。

```python
_RECURSE_TYPES = frozenset({
    "dictionary",
    "boundary_block", "boundary_entry",
    "region_block", "region_entry",
    "field_value_block",
})
```

子ノードは `node.name` で照合します。無名ノード（`name` が空）はスキップします。`field_value_block` については `_diff_field_value_block` が `node.value` の `field_name` でアイテムを照合します（[`field_value_block` の子ノードが `value` に格納される](#field_value_block-の子ノードが-value-に格納される)と同じレイアウト）。

等値は `_equal(a, b)` で判定します: `a.node_type == b.node_type and a.value == b.value` のとき `True`。

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

`manage_extra_files_dialog.py` では **Toggle Recursive** ボタンで選択中のディレクトリエントリの再帰フラグを切り替えられます。生パスは各アイテムの `Qt.UserRole` に格納され、再帰が有効な場合は表示テキストに `[recursive]` が付加されます。`result_dirs` プロパティは最終的な `list[DirEntry]` を返します。`_file_mgmt_ops.py` はこの値を使ってステータスバーの集計（追加・削除・フラグ変更の件数）を計算します。

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

起動後は **Case > Open Case** から OpenFOAM ケースディレクトリを選択するか、ファイルマネージャからウィンドウ上の任意の場所にディレクトリをドロップしてください。その後、ファイル一覧から対象ファイルを選んでください。`app_config.json` は初めてケースを開いたときに自動作成されます。`schema_config.json` は Settings メニューからスキーマ設定を変更したときにのみ作成されます。

選択したディレクトリに `system/` も `constant/` も存在しない場合は、有効な OpenFOAM ケースでない可能性を示す警告ダイアログが表示されます。それでも開くことは可能です。

## アプリケーション設定

`AppConfigManager`（`app_config/app_config_manager.py`）はアプリケーションの永続設定を管理します。`get_app_config()` でシングルトンインスタンスを取得し、セッション全体で再利用します。

### save() のセマンティクス

`set_window_size()`、`set_default_case_dir()`、`set_language()` などのセッターはインメモリの状態のみを更新します。ディスクへの書き込みは行いません。呼び出し側は変更後に明示的に `cfg.save()` を呼び出す必要があります。

`main_window.py` では 2 つの呼び出し元がこれを行います。

- `closeEvent` — `cfg.set_window_size(w, h)` を呼び出した後に `cfg.save()` を呼び出し、最終的なウィンドウジオメトリを保存します。
- `reset_window_size` — 保存済みサイズをリセットしてすぐに保存します。

設定を変更する他の呼び出し元（ケースを開いた際のデフォルトケースディレクトリの更新など）も明示的に `cfg.save()` を呼び出す必要があります。終了前に `save()` が呼び出されなかった場合、`set_*` の変更は静かに破棄されます。

### app_config.json の場所

`app_config.json` はプロジェクトルート（`main.py` と同じディレクトリ）に書き込まれます。`.gitignore` 対象です。ファイルが存在しない場合は `_load()` がエラーなしで戻り、すべてのプロパティがデフォルト値を返します。

## GPU / OpenGL に関する注意

Linux 上では、次の 2 つのサブシステムが GPU に同時アクセスします。

- **VTK / pyVista**（`block_mesh_panel.py`）— `QtInteractor` 経由で OpenGL を使用し 3D レンダリングを行います。`features.blockmesh=true` のときのみ存在します。
- **Qt WebEngine**（`_xterm_widget.py`、`XtermTerminalWidget`）— 独自の GPU プロセスを持ちます。`features.terminal=true` のときのみ存在します。

これら 2 つは同一 GPU コンテキストに安全に共存できません。`main.py` で次の回避策を適用しています。

1. `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --disable-vulkan --log-level=2` を設定し、WebEngine を SwiftShader（CPU ソフトウェアレンダリング）で強制起動することで GPU を VTK 専用に開放します。`--log-level=2` は `--disable-gpu` の副作用として表示される "GPUInfo not initialized on GpuInfoUpdate" という Chromium の警告を抑制します。
2. 起動時に `block_mesh_panel` が `None` でなく、かつターミナルが存在しないかシンプルモードの場合は、`QTimer.singleShot(0, block_mesh_panel._init_plotter)` で VTK を先行初期化し、ユーザー操作より前に OpenGL コンテキストを確保します。

ターミナルモードの切替（`TerminalPanel.mode_changed` シグナル）では、xterm 起動前に VTK をシャットダウンし、シンプルモードへ戻る際に 300 ms の遅延後に VTK を再初期化します。このシグナルは `terminal` と `blockmesh` の両方が有効なときのみ接続されます。

**View メニューのアクション** — `_build_menu_bar` 内の `_blockmesh_action`（`QAction`、チェック式）は、ターミナルモードとは独立して BlockMesh タブを表示・非表示にする第 2 の手段です。xterm が有効な場合はアクションが無効化され、テキストが `"BlockMesh 3-D Panel  (unavailable: xterm active)"` に変わって理由をホバーなしで表示します。`_on_terminal_mode_changed` がアクションの有効状態とラベルをターミナルモードと同期させ、`_on_toggle_blockmesh_panel` がユーザーのクリック時に実際のタブ追加・削除を処理します。

**Axes ウィジェット** — `add_axes()` は `vtkOrientationMarkerWidget` を生成します。このウィジェットはアクター（`plotter.clear()` で消去される）ではないため、`clear()` をまたいで持続します。そのため `_init_plotter()` で一度だけ呼び出します。`_render()` では毎フレーム再追加するのではなく `show_axes()` / `hide_axes()` でトグルします。

**サイドバイサイドモード** — `⊞` トグルボタン（`_bm_side_by_side_btn`）が `QTabWidget` のコーナーウィジェットとして追加されます。有効化すると `_on_toggle_bm_side_by_side` が `block_mesh_panel` を `upper_tabs`（`QTabWidget`）から `_tree_bm_splitter`（`right_upper_splitter` をラップし Tree タブのコンテンツとなる `QSplitter(Qt.Horizontal)`）へ再ペアレント化します。リペアレント前にまず Tree タブへ切り替えてスプリッターを可視状態にし、`setSizes([1,1])` と `_init_plotter()` は `QTimer.singleShot(0, ...)` で次のイベントループティックまで遅延させます。サイドバイサイドモードを切ると `block_mesh_panel` は通常タブとして `upper_tabs` に戻されます。

**比較パネルの表示制御** — `comparison_panel` は起動時に `right_upper_splitter` へ追加されますが直後に非表示（`comparison_panel.hide()`）になります。`QSplitter` は非表示の子ウィジェットを無視するため、ハンドルや隙間は表示されません。`_on_side_by_side_toggled(True)` では `setSizes` 前に `comparison_panel.show()` を呼び、`_on_side_by_side_toggled(False)` と `_clear_diff` では `comparison_panel.hide()` を呼びます。

**プレビューモード** — `BlockMeshPanel` は `update_block_mesh()` 呼び出しごとに設定される 2 つのフラグを持ちます: `_has_variables`（`vertices` の raw_list 値に `$` 文字が含まれる場合 True）と `_preview_mode`（デフォルト False、**Preview** ボタンでトグル）。`_has_variables` が True の場合、Vertices グループボックス内のテーブル上部に `_vtx_info_bar`（琥珀色の **⚙ Variable-based** チップ + **Preview** トグルボタン）が表示され、X/Y/Z セルは読み取り専用になります（`rw_flags = ro_flags`）。`_preview_mode` が True の場合はセルが編集可能になり、`_on_cell_changed` は `vertices_changed` を emit する代わりに `_render()` を直接呼び出してツリーとファイルを変更しません。`_on_refresh()` はプレビューモード中に `self._root` から再抽出してから `_render()` を呼び出し、頂点データのリセットとプレビュー終了を同時に行います。

## ツリーとエディタの同期

ツリーノードを選択すると、対応するソース行がテキストエディタで琥珀色の背景でハイライトされ、オプションでその行にスクロールします。仕組みは以下の通りです。

**パーサ側** — `FoamNode` には 1 ベースの行番号フィールドが 2 つあります。`source_line`（ソース内のエントリの先頭行）と `source_end_line`（末尾行）です。パーサは `_finalize_node` および `_parse_dictionary_entry` 内で `_token_line(token_index)` を使ってこれらを設定します。`_token_line` はトークンの文字オフセットまでのソーステキスト中の改行数を数えることで行番号を求めます。

**UI 側** — `CodeEditor` は `_span_start_line` / `_span_end_line` を保持します。`set_span_highlight(start, end)` でこの範囲を保存し `highlight_current_line` をトリガーします。`highlight_current_line` は `setExtraSelections` で琥珀色のスパン（背景）と青い現在行ハイライト（前面）を重ねて描画します。`EditorPanel` は `jump_to_node(start, end, scroll=True)`（ハイライト＋オプショナルスクロール）と `clear_node_highlight()` を公開します。

**状態ガード** — `MainWindow._source_lines_valid` は `_load_tree` 呼び出し後（ファイル読み込みまたは Apply Text to Tree）に `True` になり、ユーザーがエディタテキストを編集した瞬間（`_on_user_text_changed`）に `False` になります。`on_tree_selection` はこのフラグが `False` の場合にジャンプとハイライトをスキップし、古い行番号への誤ジャンプを防ぎます。`_update_sync_checkbox` はこの有効/古いの状態をチェックボックスのラベル・スタイル・ツールチップに反映します。

**エディタ → ツリー方向** — `_sync_tree_to_editor_line` は現在のエディタカーソル行を読み取り、`_find_deepest(root, line)` を呼び出して `source_line ≤ line ≤ source_end_line` を満たす最も内側のノードを探します。結果が見つかればツリーをそのノードまでスクロールして選択します。一致したノードがプロキシモデルでフィルタリングされている場合は、表示中の最も近い祖先まで遡ります。このメソッドは Editor ツールバーの **Find in Tree** ボタンと `Ctrl+Shift+T` ショートカットで呼び出されます。

## バウンダリパネルとエディタのナビゲーション

Boundary パネルのセルをクリックすると `patch_selected(path, patch_name)` シグナルが発行され、`_BoundaryOpsMixin` の `_on_patch_selected` が処理します。ツリーのナビゲーション（`source_line` を使用）と異なり、バウンダリのナビゲーションはテキスト検索を使います。これは `write_root()` がバウンダリ編集後にテキストを再生成するため、ソース行番号がすぐに古くなるからです。

`EditorPanel.jump_to_text(text)` はドキュメント先頭から `QTextDocument.find(text, 0, FindWholeWords)` を呼び出します。一致が見つかった場合、マッチしたブロック番号に対して `set_span_highlight(line, line)` と `goto_line(line)` を呼び出します。`boundaryField` 内のパッチ名はファイル内で一意のため、最初のヒットが常に正しい位置です。

クリックしたセルのファイルが `state.current_file` と異なる場合、`_on_patch_selected` はまず `load_selected_file(path)` を呼び出して（`state.current_file` を設定）、続いて `file_list_panel.select_file(path)` でファイルリストのハイライトを同期します。その結果発行される `file_selected` シグナルによって再入する `load_selected_file` は、`state.current_file` が既に設定済みのため no-op になります。

Boundary パネルツールバーの **Auto-scroll editor** チェックボックスは `_on_cell_clicked` 内での `patch_selected` 発行を制御します。オフの場合、シングルクリックはエディタに影響しません。

`BoundaryViewPanel._table_data()` は現在の `QTableWidget` の状態から `(col_headers, row_headers, rows)` を取り出します。`_copy_as_markdown()` はこのデータから GitHub Flavored Markdown のパイプテーブルを構築し、システムクリップボードへ書き込みます（セルテキスト内の `\n` は `<br>` に変換）。`_copy_as_csv()` は RFC 4180 準拠の CSV を書き込み、複数行のセル内容は引用符付きフィールドとして保持されます。どちらのメソッドも既にレンダリング済みのテーブルから読み取るため、転置状態に自動的に対応します。

## ダーティ状態の追跡

`MainWindow` は 2 つの並行したダーティ状態変数を維持します。

- `state.text_dirty: bool` — 現在開いているファイルのインメモリエディタ内容がディスク上のものと異なるかどうか。`_mark_dirty()` で設定され、`save_file()`、Apply Text to Tree、Reload from Disk でクリアされます。
- `state.file_dirty: dict[str, bool]` — 現在のセッションで読み込まれたすべてのファイルのファイルごとのダーティ状態。ファイルを切り替えても未保存の編集が失われないよう、ファイルスイッチをまたいで保持されます。

`_mark_dirty()`（`ui/main_window.py:566`）は両方の値を `True` に設定し、ウィンドウタイトルに `*` サフィックスを追加し、`file_list_panel.mark_dirty()` を呼び出してファイルリストにインジケーターを表示します。これは `_after_model_edit()`（`write_root()` 経由でテキストを再生成するツリー編集後）と `_on_user_text_changed()`（エディタへの人間によるキー入力時）から呼び出されます。

`_save_current_buffer()`（`ui/main_window.py:520`）はファイルスイッチ前に `editor_panel.get_text()` を `state.file_buffers[state.current_file]` へフラッシュし、`state.text_dirty` を `state.file_dirty[state.current_file]` に書き戻します。これにより、スイッチをまたいでも未保存の編集がインメモリで保持されます。

`_mark_path_dirty(path)` は現在開いているファイルに関係なく特定のパスをダーティとしてマークします。複数のフィールドファイルにわたって境界パッチをリネームするような操作で使用されます。

## ツリーのコピー・ペーストショートカット

`_setup_tree_copy_paste()`（`ui/mixins/_tree_ops.py:29`）は `Qt.WidgetShortcut` スコープを使って Ctrl+C と Ctrl+V の `QShortcut` インスタンスを `tree` ウィジェットに直接アタッチします。

```python
copy_sc = QShortcut(QKeySequence.Copy, self.tree)
copy_sc.setContext(Qt.WidgetShortcut)

paste_sc = QShortcut(QKeySequence.Paste, self.tree)
paste_sc.setContext(Qt.WidgetShortcut)
```

`Qt.WidgetShortcut` は `self.tree` がキーボードフォーカスを持つ場合のみ発火するため、テキストエディタでの Ctrl+C は影響を受けません。ツリーセルがインライン編集モードの場合も発火しません。その状態では Qt がセルエディタ自身の選択コピー機能に Ctrl+C をルーティングします。

同じ 2 つのアクションはコンテキストメニューにも表示されます（**Copy Value** / **Paste Value**）。選択したノード型が値の編集をサポートしない場合、ペーストはメニューで無効化され静かに拒否されます。

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
