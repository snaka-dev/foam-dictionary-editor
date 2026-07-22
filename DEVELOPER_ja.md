# Foam Dictionary Editor (FoDE) — 開発者ガイド

ユーザー向けドキュメントは [USER_GUIDE_ja.md](USER_GUIDE_ja.md) を参照してください。
インストールと基本的な使い方は [README_ja.md](README_ja.md) を参照してください。

## プロジェクト構成

現在の代表的なディレクトリ構成は次の通りです。

```text
foam-dictionary-editor/
├── docs/
│   └── images/              # USER_GUIDE.md で使用するスクリーンショット
├── tools/
│   └── generate_foam_keywords.py  # app_config/keyword_generator.py の CLI ラッパー。--dir でインストールルートを指定（デフォルト: source 済み環境）
├── tutorials/               # 同梱サンプルケース（GPL-3.0、tutorials/README.md 参照）
├── main.py
├── _version.py              # アプリバージョンの単一情報源。get_version() はチェックアウトから実行時に git の開発ビルド接尾辞を付加
├── requirements.txt
├── requirements-dev.txt
├── requirements-packaging.txt
├── README.md
├── README_ja.md
├── USER_GUIDE.md
├── USER_GUIDE_ja.md
├── DEVELOPER.md
├── DEVELOPER_ja.md
├── RELEASE_NOTES.md
├── RELEASE_NOTES_ja.md
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
│   ├── defaults.py
│   └── keyword_generator.py  # OpenFOAM インストールをスキャン（etc/caseDicts テンプレート、src/ と applications/ ソース内の TypeName/ClassName + addNamedTo* マクロと辞書読み取り呼び出し — lookup("…")、get<…>("…")、readEntry("…") など）して foam_keywords.json を構築（ユーザー生成、gitignore 対象。トラック済みの foam_keywords.default.json ベースラインより優先）。インストールルートは generate(project_dir=…) か source 済み環境（services/foam_env.foam_env_dirs を遅延インポートで利用）から取得。出力は json_io.atomic_write_text でアトミックに書き込み。ペイロードには来歴メタデータ（source、version、generated、note — 識別子名のみで OpenFOAM のソースコードは含まない）を記録。tools/generate_foam_keywords.py と Settings メニューのアクションで共用
├── foam/
│   ├── block_mesh_extractor.py  # blockMeshDict の FoamNode ツリーから頂点・ブロック・境界を抽出。_HEX_FACE_VERTICES + _expand_compact_faces がコンパクト (blockIdx, faceIdx) 境界エントリを 4 頂点リストに展開。_compute_default_faces は、どのパッチにも割り当てられていない外部ブロック面（blockMesh の暗黙の defaultFaces — 擬似 2D ケースが boundary に列挙しない面）を BlockMeshData.default_faces に収集。parse_vertices() はパブリック API。変数解決は var_resolver に委譲
│   ├── var_resolver.py          # 共有の変数解決ロジック: build_var_map(root, skip_keys) が任意の深さの $変数（`-$xMax` のような否定マクロ word ノードを含む）と #eval{} チェーンを反復的に解決。substitute_vars() と eval_foam_expr() は両エクストラクタが使うパブリックヘルパー
│   ├── topo_set_extractor.py    # topoSetDict の action_entry ノードから描画可能なジオメトリ（box〈min/max・複数ボックス boxes 形式を含む〉、rotated box、sphere〈origin エイリアスと innerRadius を含む〉、cylinder、cone、点セット〈nearestTo*/insidePoints/nearPoint〉、planeToFaceZone の平面）を抽出。raw_list / マクロ形式のジオメトリ値内の $var と #eval を var_resolver 経由で解決し、TopoSetData(shapes=[TopoShape(...)]) を返す。すべてのエクストラクタ形状クラス（TopoShape/SnappyShape/SetFieldsShape）は label/kind というフィールド名（表示名 + ジオメトリ/ソースのキーワード）を共有する。ソースごとのジオメトリ分岐は resolve_source_geometry() / is_non_geometric_source() として公開され、set_fields_extractor.py と共有される
│   ├── set_fields_extractor.py  # setFieldsDict の regions ( … ) リスト（region_block → region_entry ノード。エントリの「名前」がソースタイプ — boxToCell、sphereToCell など — で、`source` 子ノードは持たない）から描画可能な領域ジオメトリを抽出。topo_set_extractor.resolve_source_geometry() を再利用し、各シェイプに fieldValues の要約（例: "alpha.water=1"）をラベル付けして SetFieldsData(shapes=[SetFieldsShape(...)]) を返す
│   ├── sampling_extractor.py    # 描画可能なサンプリングジオメトリ — probes の probeLocations（点マーカー）、sets タイプのサンプル線（start/end）、surfaces タイプの plane/cuttingPlane 円盤 — を controlDict の functions {} ブロックまたはスタンドアロンのサンプリング辞書（system/sample・probes・surfaces・singleGraph。.org 系のトップレベル start/end スタイルを含む）から抽出。入れ子のメンバーリストは 2 つの書式とも構造化パーサーノード: 辞書形式 sets {}/surfaces {} と、従来の丸括弧リスト形式 sets ( name {…} )（named_dict_list）。平面解決は tree_utils.resolve_plane_geometry を再利用。SamplingData(shapes=[SamplingShape(...)]) を返す
│   ├── snappy_hex_mesh_extractor.py  # snappyHexMeshDict の geometry {} プリミティブ（box、sphere〈ベクトル radius によるだ円体を含む〉、cylinder、cone、constant/triSurface/ から解決される triSurfaceMesh/distributedTriSurfaceMesh〈.gz サイドカーへの透過的な解決を含む〉、box ベースの collection メンバー）を抽出。castellatedMeshControls.refinementSurfaces/refinementRegions（正規表現パターンのサーフェス名を含む）と照合し surface/region/geometry に分類。locationInMesh/locationsInMesh も抽出し、SnappyHexMeshData(shapes=[SnappyShape(...)]) を返す
│   ├── tree_utils.py            # topo_set / snappy_hex_mesh / set_fields の各エクストラクタが共有する汎用 FoamNode ヘルパー: find_child、find_child_any、resolve_scalar、resolve_vector、resolve_point_list、expand_evals、および box/sphere/cylinder/cone の共有ジオメトリリゾルバ（resolve_box_geometry は min/max、`box (min) (max)` ペア、複数ボックス `boxes` の各形式をオプトインフラグで扱う）
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
│   ├── snappy_hex_mesh_dict/    # パッケージ: サブドメイン別に分割（geometry, castellated mesh, snap, layers, mesh quality）
│   │   ├── __init__.py          # 各サブモジュールの SCHEMAS を統合し、TARGET_FILE を再エクスポート
│   │   ├── _common.py           # 共有 SWITCH_CHOICES
│   │   ├── _geometry.py
│   │   ├── _castellated_mesh.py
│   │   ├── _snap_controls.py
│   │   ├── _add_layers.py
│   │   └── _mesh_quality.py
│   └── registry.py
├── services/
│   ├── case_copier.py
│   ├── case_files_config.py
│   ├── case_loader.py       # detect_poly_mesh() も含む -- constant/polyMesh/owner の FoamFile note フィールドから PolyMeshInfo(n_points, n_cells, n_faces, stale) を生成
│   ├── example_search.py    # discover_installations()/search_examples(): OpenFOAM インストールを検出（foam_env による環境変数読み取り → 既知のパス）し、その tutorials/ + etc/caseDicts/ をキーワード走査して SearchHit（一致行、囲むチュートリアルケースのルート）を返す
│   ├── foam_env.py          # foam_env_dirs(env) → FoamEnvDirs: $WM_PROJECT_DIR/$FOAM_TUTORIALS/$FOAM_ETC/$FOAM_SRC/$FOAM_APP を読む唯一の情報源（各フィールドはディレクトリが存在する場合のみ非 None、project_dir 配下へのフォールバック付き）。example_search、keyword_generator、AppConfigManager.foam_tutorials_dir が共有（後者 2 つは遅延インポート — app_config は services より下位のレイヤーのため）
│   ├── log_summary.py       # parse_log()/format_summary(): blockMesh/snappyHexMesh/topoSet およびソルバーの実行ログ（log.* の標準出力。FoamNode 辞書ツリーではない。ソルバーは名前ではなくタイムループの形で検出）を短い LogSummary レポートに要約
│   └── tool_options.py      # Tools メニュー「Run *」オプションダイアログ用の ToolSpec/ToolOption 仕様（TOOL_SPECS）+ build_args()/build_command()。常に log.<ツール名> へ tee する
├── i18n/
│   ├── __init__.py             # tr()、set_language()、get_language()、available_languages()
│   └── ja.py                   # 日本語翻訳（LANGUAGE_NAME + TRANSLATIONS 辞書）
├── ui/
│   ├── app_state.py            # AppState データクラス: 共有可変フィールドすべて（`current_case_dir`、`current_file`、`current_root`、`current_model`、`file_buffers`、`file_dirty`、`text_dirty`、`source_lines_valid`、`syncing`、`case_files_config`、`parsed_roots`、`diff`、`foam_monitor`、`run_tool_options`、`undo`、`bm_side_by_side`）。`diff` は `DiffState` サブデータクラス（`case_dir`、`parsed_roots`）。`foam_monitor` は `FoamMonitorState` サブデータクラス（`proc`、`script_tmp`、`last_file`、`last_options`）。`undo` は `UndoState` サブデータクラス（ファイルごとの `UndoSnapshot` スタックと `op_active`/`restoring` ガード）。`MainWindow.__init__` が `self.state = AppState()` を生成し、すべての Mixin が `self.state.<field>` として共有状態にアクセス
│   ├── main_window.py          # オーケストレータ。`MainWindow` は 13 個の Mixin を継承。自身のファイルは `__init__`、`_build_ui`、共有ヘルパーのみを扱う。`file_list_panel`、`tree`、`editor_panel` などの UI ウィジェット参照は素の `self` 属性のまま残り、可変データ状態はすべて `self.state` に置かれる
│   ├── mixins/
│   │   ├── _boundary_ops.py        # Mixin: バウンダリビューのパッチ操作
│   │   ├── _case_ops.py            # Mixin: ケースの開く・再読み込み・複製・名前を付けて保存・設定
│   │   ├── _diff_ops.py            # Mixin: サイドバイサイド比較、差分の計算・クリア。_reset_diff_for_case_dir は _load_case_dir 後にアクティブな比較を調整（ケース切り替え時はクリア、同一ディレクトリの再読み込み時は再アーム）。参照ファイルの解析失敗はステータスバーで報告（_recompute_diff ではファイル単位、事前計算スキャンの最後にはスキップ件数のサマリ）
│   │   ├── _file_mgmt_ops.py       # Mixin: ファイルの作成・追加・バックアップ・削除・複製・クリーンアップ
│   │   ├── _file_ops.py            # Mixin: ファイル単位の読み込み・保存、ディレクトリスキャンヘルパー
│   │   ├── _foam_monitor_ops.py    # Mixin: foamMonitor の起動・停止・ポーリング、gnuplot reread パッチ
│   │   ├── _model_ops.py           # Mixin: バッファ・ツリー状態、ダーティ追跡、パースキャッシュ
│   │   ├── _panel_ops.py           # Mixin: BlockMesh パネルおよびターミナルモード切替ハンドラ
│   │   ├── _tools_ops.py           # Mixin: Tools メニューのアクション — 0/ を 0.orig から復元、blockMesh/snappyHexMesh/topoSet/setFields/checkMesh の実行（いずれも _run_tool_with_options 経由: ツールごとの RunToolDialog を表示 — 仕様は services/tool_options.py —、最後に使った値を state.run_tool_options に記憶し、合成したコマンドを送信。プレフライト警告はダイアログに統合 — メッシュ系ツールは _rerun_over_results_warning の時間ディレクトリ注意、setFields は 0/ を直接書き換え再実行が重ねて適用されるため 0.orig/ が存在する場合デフォルトでチェックされた「先に 0/ を 0.orig/ から復元する」プレフィックスチェックボックス、checkMesh は読み取り専用なので警告なし）、Allrun/Allclean スクリプトの実行、foamCleanTutorials によるケースのクリーン（runApplication はログ済みステップをスキップするため、log.* が存在する場合 Allrun は「クリーンしてから実行」を提案）、ParaView を開く、ログ要約を表示（非モーダルの LogSummaryDialog、self._log_summary_dialog で参照を保持）、OpenFOAM の例を検索（非モーダルの FindExamplesDialog、self._find_examples_dialog で参照を保持。compare_requested は _diff_ops._start_comparison_with に、duplicate_requested はホームディレクトリをフォールバックのコピー先として _case_ops._duplicate_case_from に接続）
│   │   ├── _tree_crud_ops.py       # Mixin: ツリーエントリの CRUD（コピー・ペースト、追加、複製、コメントアウト、削除、復元）と _apply_comparison_value
│   │   ├── _tree_sync_ops.py       # Mixin: エディタ↔ツリー同期（Apply Text to Tree、Reload from Tree）
│   │   ├── _undo_ops.py            # Mixin: スナップショット方式のツリー編集 Undo/Redo（ツリーにスコープされた Ctrl+Z / Ctrl+Shift+Z。シリアライズ済みテキストのスナップショットからなる単一のグローバルタイムライン）
│   │   └── _ui_ops.py              # Mixin: ラベル更新、スキーママネージャ、ヘルプダイアログ、言語メニュー、ツリー列の表示切替
│   ├── layout_constants.py
│   ├── dialogs/
│   │   ├── about_dialog.py
│   │   ├── add_files_dialog.py
│   │   ├── boundary_edit_dialog.py
│   │   ├── case_library_dialog.py
│   │   ├── clean_backups_dialog.py
│   │   ├── duplicate_case_dialog.py
│   │   ├── export_stl_dialog.py  # ExportStlDialog: 読み込み済みの topoSetDict/snappyHexMeshDict シェイプをチェックリスト表示するモーダルダイアログ。チェックした各シェイプを BlockMeshRenderer._make_shape_mesh 経由でそれぞれ個別の .stl として書き出す
│   │   ├── find_examples_dialog.py  # FindExamplesDialog: 非モーダルのキーワード検索。インストールの tutorials/ + etc/caseDicts/ を対象（services/example_search.py をバックグラウンド QThread で実行）、シンタックスハイライト付きプレビュー、コピー、「このケースと比較」（compare_requested を発行）、「このケースを複製…」（duplicate_requested を発行）。インストール選択は共有ウィジェット widgets/installation_selector.InstallationSelector
│   │   ├── foam_monitor_dialog.py  # FoamMonitorDialog: ファイル選択 + foamMonitor オプション（対数スケール、グリッド、リフレッシュ間隔、アイドルタイムアウト、追加フラグ）
│   │   ├── generate_keywords_dialog.py  # GenerateKeywordsDialog: app_config/keyword_generator.py をバックグラウンド QThread で実行し進捗ログを表示。インストール選択は共有ウィジェット widgets/installation_selector.InstallationSelector（FindExamplesDialog と同じ検出 + 永続化 openfoam_dir キー）
│   │   ├── keyboard_shortcuts_dialog.py
│   │   ├── log_summary_dialog.py  # LogSummaryDialog: 非モーダル（find_examples_dialog と同様。他のモーダルダイアログとは異なる）のファイル選択 + Summary/Raw Log タブ、services/log_summary.py を利用
│   │   ├── manage_extra_files_dialog.py
│   │   ├── openfoam_resources_dialog.py
│   │   ├── rename_boundary_dialog.py  # Rename Boundary ダイアログ + find_rename_targets() スキャナ
│   │   ├── reset_settings_dialog.py
│   │   ├── run_tool_dialog.py  # RunToolDialog: services/tool_options.TOOL_SPECS から構築される Tools メニュー「Run *」の汎用オプションダイアログ — 主要フラグのウィジェット、自由記述の追加オプション、ライブコマンドプレビュー、任意のプレフライト警告とシェルプレフィックスチェックボックス
│   │   ├── save_as_new_case_dialog.py
│   │   └── schema_manager_dialog.py
│   ├── panels/
│   │   ├── block_mesh_panel.py     # blockMeshDict 用 3D ビューア（pyVista/VTK、遅延初期化）。topoSetDict（topoSet ▾ メニュー）、snappyHexMeshDict（snappyHexMesh ▾ メニュー）、setFieldsDict の領域（setFields ▾ メニュー）、サンプリング定義（sample ▾ メニュー。controlDict の functions {} とスタンドアロンの system/sample 系辞書の合算を _sampling_by_file に元ファイル名ごとに保持）のジオメトリもそれぞれシェイプ単位の表示切替・Show all/Hide all アクション・描画不能エントリ用の「Non-geometric sources (N)」サブメニュー付きで重ねて表示する。アクター構築は block_mesh_renderer.BlockMeshRenderer に委譲。STL ▾ メニューの「Export Shapes as STL…」は dialogs/export_stl_dialog.ExportStlDialog を開く
│   │   ├── block_mesh_renderer.py  # BlockMeshRenderer: RenderSettings データクラス経由の blockMeshDict/topoSetDict/snappyHexMeshDict/setFieldsDict ジオメトリ用 VTK レンダリングパイプライン。_make_shape_mesh はジオメトリ辞書のキー（box、boxes、centre+radius〈リスト radius によるだ円体と innerRadius による中空球を含む〉、p1+p2+radius、origin+i+j+k、stl_path、planePoint+planeNormal〈plane_size で寸法指定される円板〉。points は None を返しマーカーとして別途描画）で分岐し全オーバーレイソースで共有される。オーバーレイシェイプは _clip_to_bounds により、ブロックメッシュの AABB を各軸 10% 拡大した範囲へ（表示上のみ）クリップされる — ラベルには「✂ clipped」/「⚠ outside block mesh」マークが付き、シーンを包み込むシェイプは AABB の重なりボックスにフォールバックし、STL エクスポートはクリップされない。_render_boundary_faces は BlockMeshData.default_faces も薄い "empty" グレーで描画する。pyvista のガードを通過した後にのみインポートされる
│   │   ├── boundary_view_panel.py
│   │   ├── comparison_tree_panel.py  # 読み取り専用の参照ケースツリー。use_value_requested(FoamNode) シグナルを発行
│   │   ├── detail_panel.py
│   │   ├── editor_panel.py
│   │   ├── file_list_panel.py
│   │   └── terminal_panel.py       # TerminalPanel ラッパー: mode_changed シグナル、xterm/simple 切替ロジック
│   └── widgets/
│       ├── code_editor.py
│       ├── flow_layout.py              # FlowLayout（QLayout）: 折り返し式ツールバーレイアウト — 最小幅は最も幅の広い 1 項目分。BlockMesh パネルのツールバーで使用
│       ├── installation_selector.py    # InstallationSelector（QWidget）: services/example_search.discover_installations() と永続化 openfoam_dir キーに基づくコンボ + Browse… 行。installations_available/error シグナル。find_examples_dialog と generate_keywords_dialog で共用
│       ├── _foam_highlighter.py        # FoamHighlighter（QSyntaxHighlighter）: OpenFOAM トークンの色付け。app_config/foam_keywords.json（ユーザー生成）、無ければ app_config/foam_keywords.default.json（同梱ベースライン）を 1,000 キーワード単位の QRegularExpression チャンクで読み込む。数値ルール（_NUMBER_RE）とすべてのキーワードルールは前後判定（lookaround）で守られており、識別子に付いた数字（"wall0"）やドット付き名前のキーワード接頭辞（"y0.1" の "y0"）が部分的に色付けされることはない
│       ├── _simple_terminal_widget.py  # SimpleTerminalWidget: QProcess ベースターミナル（WebEngine 不要）
│       └── _xterm_widget.py            # PtyBackend、TerminalBridge、XtermTerminalWidget（Unix + QtWebEngine 専用）。_XTERM_AVAILABLE をエクスポート
└── tests/
    ├── conftest.py
    ├── test_lint.py             # pytest スイートの一部として ruff + mypy を実行（foam/, model/, app_config/, schemas/, services/, ui/app_state.py にスコープ）
    ├── test_version.py          # _version.get_version(): git describe の整形（タグ一致、タグより先行、dirty、ハッシュのみ、git 無しフォールバック）
    ├── foam/
    │   ├── test_diff.py
    │   ├── test_parser_block_mesh_dict.py
    │   ├── test_parser_control_dict.py
    │   ├── test_parser_fv_schemes.py
    │   ├── test_parser_fv_solution.py
    │   ├── test_parser_named_dict_list.py
    │   ├── test_parser_set_fields_dict.py
    │   ├── test_parser_topo_set_dict.py
    │   ├── test_sampling_extractor.py
    │   ├── test_set_fields_extractor.py
    │   ├── test_snappy_hex_mesh_extractor.py
    │   ├── test_source_lines.py
    │   ├── test_topo_set_extractor.py
    │   ├── test_topo_set_shapes_tutorial.py
    │   ├── test_tree_utils.py
    │   ├── test_utils.py
    │   ├── test_var_resolver.py
    │   └── test_writer_roundtrip.py
    ├── model/
    │   ├── test_bool_nonuniform.py
    │   ├── test_boundary_model.py
    │   ├── test_file_list_model.py
    │   └── test_tree_model.py
    ├── ui/
    │   ├── test_apply_comparison_value.py
    │   ├── test_block_mesh_panel_sampling_select.py
    │   ├── test_block_mesh_panel_set_fields_select.py
    │   ├── test_block_mesh_panel_snappy_select.py
    │   ├── test_block_mesh_panel_topo_select.py
    │   ├── test_block_mesh_renderer_topo.py
    │   ├── test_bm_side_by_side_multi_dict.py
    │   ├── test_boundary_view_copy.py
    │   ├── test_case_switch_clears_block_mesh_panel.py
    │   ├── test_code_editor.py
    │   ├── test_comparison_tree_panel.py
    │   ├── test_diff_state_reset_on_case_change.py
    │   ├── test_drag_drop_open_case.py
    │   ├── test_duplicate_case.py
    │   ├── test_editor_panel.py
    │   ├── test_export_stl_action_state.py
    │   ├── test_export_stl_dialog.py
    │   ├── test_file_list_panel.py
    │   ├── test_find_examples_dialog.py
    │   ├── test_flow_layout.py
    │   ├── test_foam_highlighter.py
    │   ├── test_log_summary_dialog.py
    │   ├── test_main_window_save_refresh.py
    │   ├── test_main_window_split.py
    │   ├── test_manage_extra_files_dialog.py
    │   ├── test_rename_boundary.py
    │   ├── test_run_tool_dialog.py
    │   ├── test_stays_open_menu.py
    │   ├── test_terminal_panel.py
    │   ├── test_tools_ops_mesh_actions.py
    │   ├── test_tree_color_lexer_dispatch.py
    │   ├── test_tree_copy_paste.py
    │   ├── test_tree_inline_edit_dirty.py
    │   ├── test_tree_undo_redo.py
    │   └── test_view_log_summary_action.py
    ├── services/
    │   ├── test_backup.py
    │   ├── test_case_copier.py
    │   ├── test_case_files_config.py
    │   ├── test_case_loader.py
    │   ├── test_example_search.py
    │   ├── test_foam_env.py
    │   ├── test_log_summary.py
    │   └── test_tool_options.py
    ├── app_config/
    │   ├── test_app_config.py
    │   ├── test_json_io.py
    │   └── test_keyword_generator.py
    └── schemas/
        └── test_schemas.py
```

### ドキュメントマップ

| ファイル | 役割 |
|---|---|
| `README.md` | 短い導入: インストール、クイックスタート、ユーザーガイドへディープリンクする要約版の機能一覧。 |
| `USER_GUIDE.md` | 全機能リファレンス。**ユーザーに見える機能を追加したら、「目的別ガイド」テーブルと目次にも必ず追加すること** — これらのナビゲーションは放っておくと静かに実態とずれていきます。 |
| `DEVELOPER.md` | このファイル: プロジェクト構成、内部構造、開発環境のセットアップ、テスト。 |
| `RELEASE_NOTES.md` | ユーザー向け変更履歴。新しい項目は `## Unreleased` の下に蓄積し、リリース時に見出しをバージョン番号へ変更します。 |
| `docs/SCREENSHOTS.md` | メインウィンドウ・BlockMesh 3D オーバーレイ・主要ダイアログ/メニューの注釈付きスクリーンショットギャラリー。 |

各英語ドキュメントには日本語版（`*_ja.md`）があり、一方を編集したら必ずもう一方にも反映します。日本語ドキュメントではメニューラベルなどの UI 文字列は英語のまま表記します。

### テストカバレッジ一覧

ディレクトリごとにテストファイル 1 行の一覧です。テストファイルの追加・削除時はここも更新してください — 以前サイレントにドリフトしたのはまさにこの部分です。

**`tests/foam/`**
- `test_diff.py` — `diff_trees`/`diff_trees_reverse`: 同一ツリー、値の変更、片方のみに存在するキー、ネストした辞書、匿名ノードのスキップ、`field_value_block` エントリ、両関数の対称性。
- `test_parser_block_mesh_dict.py` — `boundary_block`/`boundary_entry` の構造的パース、ライタの round-trip、`extract_block_mesh_data` の出力。変数解決（`$varName`、`${varName}`、マクロ、`-$xMax` のような否定マクロ word ノード、`#eval{ expr }`、多段チェーン）。コンパクト `(blockIndex, faceIndex)` 境界面記法（否定マクロ頂点変数との組み合わせを含む）。`default_faces` の抽出（境界が全面を占有 → 空、未割り当ての外部面の収集、任意の頂点回転での占有判定、ブロック間で共有される内部面の除外）。
- `test_parser_control_dict.py` — `controlDict` のパース: FoamFile ヘッダー、int/scalar/word の値、`#directives`、`functions` サブ辞書、パース失敗時に空の root へフォールバックすること。
- `test_parser_fv_schemes.py` — `fvSchemes` のパース: compound 値、`ddtSchemes`/`divSchemes`/`interpolationSchemes`/`snGradSchemes` ブロック、すべてのトップレベルブロックの存在、round-trip 書き込み。
- `test_parser_fv_solution.py` — `fvSolution` のパース: マクロおよび正規表現パターンのソルバーキー、`PIMPLE` ブロック、ソルバーの `tolerance`/`smoother` エントリ、round-trip 書き込み。
- `test_parser_named_dict_list.py` — 省略可能な名前付き辞書リスト構文: `sets`/`surfaces` の名前付き辞書の丸括弧リストが `named_dict_list`/`named_dict_entry` として解析されること（トップレベルとファンクションオブジェクト辞書内の入れ子の両方）、先読みにより単純な単語/文字列リスト（`sets (setA setB);`）や空リストが通常の値パスに留まること、未変更時のラウンドトリップがバイト単位で一致すること、エントリ変更時に兄弟エントリの名前が保持されること。
- `test_parser_set_fields_dict.py` — `setFieldsDict` のパース: `defaultFieldValues`/`regions` のフィールド値エントリ（ベクトル値を含む）、`box_pair` のパース、編集後の round-trip 書き込み。
- `test_parser_topo_set_dict.py` — `action_list`/`action_entry` の構造的パース: ノード型、エントリ数、名前付き子ノードの値、`box_pair` 座標、ソースなしエントリ、round-trip 書き込み、`_diff_action_list` による位置ベースの差分検出。
- `test_snappy_hex_mesh_extractor.py` — `extract_snappy_hex_mesh_data`: `geometry` の box/sphere（スカラーおよびベクトル/だ円体 radius）/cylinder/cone の抽出、`name` による上書き解決（`geom.stl { name geom; }`）、`triSurfaceMesh`/`distributedTriSurfaceMesh` の `constant/triSurface/` に対するファイル解決（明示的な `file` 子ノード、キー名からの暗黙のファイル名、ファイル不在時の扱い）— `.gz` への透過的な解決を含む（プレーン名のエントリがディスク上に `.gz` のみ存在するファイルへ解決されるケース、`.gz` 付きのエントリキー／ファイルがそのまま解決されるケース、`.gz` 付きの参照がディスク上の非圧縮ファイルへフォールバックするケース）、`collection`（searchableSurfaceCollection）の box メンバーを `rotation none` および `e1`/`e3` 軸で解決（実際に回転するケースを含む）し、box 以外のベースや未指定・未対応の `transform` はスキップされること、`refinementSurfaces`/`refinementRegions` の完全一致および正規表現パターンキー（例：`"iglo.*"`）による照合、`locationInMesh`（単数）と `locationsInMesh`（複数）の点抽出、`$var`/`#eval{}` の解決。
- `test_source_lines.py` — すべてのノード型に対する `source_line` および `source_end_line` の設定。
- `test_topo_set_extractor.py` — `extract_topo_set_data`: box・sphere・cylinder の 3 種類すべてに対するプレーンな型付き値、ベクトルとスカラーでの `$var` 解決、`raw_list` 内の `#eval{...}`、連鎖した変数/eval 解決、解決不能な変数のスキップ、すべての face/point ソースバリアント。
- `test_sampling_extractor.py` — `extract_sampling_data`: `functions {}` ブロック内の probes、辞書形式 `sets {}` の line/cloud メンバーと、丸括弧リスト形式（`functions {}` ブロック内とファイルルートの sampleDict スタイルの両方）、`plane`/`cuttingPlane`/`patch` サーフェスメンバー、トップレベルの `singleGraph` スタイル `start`/`end`、スタンドアロンの `sample`/`probes` ファイル、`$var` の解決、サンプリング以外のファンクションオブジェクトの無視。
- `test_set_fields_extractor.py` — `extract_set_fields_data`: box/sphere/cylinder 領域の抽出（エントリ名がソースタイプ）、`fieldValues` のラベル要約（スカラー値とベクトル値）、ジオメトリを持たないソースの分類（`zoneToCell`）、`$var` の解決、解決不能なジオメトリックソースのケース。
- `test_topo_set_shapes_tutorial.py` — 同梱の `tutorials/topoSetShapes` ケースに対する `extract_topo_set_data`: すべてのジオメトリソースが抽出され、すべての形状がドメイン内に収まっていること。
- `test_tree_utils.py` — `tree_utils` の各リゾルバの直接契約テスト（エクストラクタのテストは間接的にしか通らない）: `find_child`/`find_child_any` のエイリアス優先順、`expand_evals`、`resolve_scalar`（scalar/int/macro/`${…}`/`#eval`）、`resolve_vector` の要素数・数値ガード、`resolve_point_list`、オプトインフラグ付きの sphere/cylinder/cone リゾルバ、`resolve_box_geometry`（min/max・`box` ペア・複数 `boxes` の優先順とフラグによる有効化）。
- `test_utils.py` — `is_large_non_foam_file`: 小さいファイルはヘッダーの有無にかかわらずフラグが立たないこと、最初の 512 バイト内に `FoamFile` トークンを含む大きいファイルはフラグが立たないこと、含まない大きいファイルはフラグが立つこと、存在しないファイルは `(False, 0)` を返すこと、コメントの後にヘッダーがある場合も正しく検出されること。
- `test_var_resolver.py` — `build_var_map`、`substitute_vars`、`eval_foam_expr`: スカラー/整数のシード、マクロチェーン、`#eval` 式、否定マクロ word ノード、解決不能な変数が値を持たないままになること、`skip_keys` による除外、辞書ノードが収集対象にならないこと。
- `test_writer_roundtrip.py` — `write_root`/`write_node` 全般: 未変更ノードが `raw_text` で再現されること、変更された word/int/scalar/vector ノードが再生成されること、directive/unknown_raw/macro エントリが保持されること、ネストした辞書、余分な空行の抑制、`field_value_block`/`region_block` の round-trip（リージョン内のフィールド値編集を含む）、および 1 つの region エントリの再生成時に未変更の兄弟エントリの名前が失われていたリグレッション（エントリの `raw_text` が名前トークンから始まるようになった）。

**`tests/model/`**
- `test_bool_nonuniform.py` — bool/nonuniform_list のパースと round-trip、`FoamTreeModel` の bool 編集（大文字小文字を区別しない、拒否シグナル）、`nonuniform_list` の表示・編集不可、不正エントリに対するパーサエラー収集。
- `test_boundary_model.py` — `extract_boundary()` と `BoundaryModel`: 読み込み、フィールド更新、ディレクトリごとの境界セット、`_is_in_dir` の多階層照合、モデルのクリア。
- `test_file_list_model.py` — `FileListModel`: 読み込み、ソート済みグループ、アイテムごとのダーティ状態・差分状態、追加ファイルの扱い、クリア。
- `test_tree_model.py` — `set_diff(reverse=True)`: `"only_here"` を `"only_in_ref"` にリマップし `"changed"` は変更しないこと、淡緑色の `BackgroundRole` を返すこと、`"only in reference case"` をツールチップに含むこと。`FoamNode` は `__hash__ = object.__hash__` を持ち、差分マップのキーとして使用可能です。

**`tests/ui/`**
- `test_apply_comparison_value.py` — `_apply_comparison_value`（「Use this value」）: ネストしたエントリの取り込み時に不足している親辞書を作成すること（例: `functions {}` を持たないケースへの `functions/forces1/rhoInf` の適用）、名前のない `#includeFunc` ディレクティブを既存ブロックを上書きせず内容で照合して末尾に追加すること、同一のディレクティブは複製せずスキップすること、名前付きの値の通常の上書きパス、囲むキーが存在するものの辞書ではない場合に適用を拒否すること。
- `test_block_mesh_panel_sampling_select.py` — `sample ▾` の形状別表示メニュー: controlDict の `functions {}` ブロックからのメニュー生成（行には元ファイル名のタグ付き）、個別/マスタートグル、ジオメトリを持たないエントリのグレーアウト表示、複数ファイルの合算（controlDict + system/sample）とファイル単位の再読み込み置換、`clear()` による `_sampling_by_file` のリセット。
- `test_block_mesh_panel_set_fields_select.py` — `setFields ▾` の形状別表示メニュー: 同梱の damBreak チュートリアルの `setFieldsDict` からのメニュー生成（行は `fieldValues` の要約でラベル付け）、個別/マスタートグル、ジオメトリを持たないソースのグレーアウト表示、STL エクスポートへの包含、再読み込み時のクリア。
- `test_block_mesh_panel_snappy_select.py` — `snappyHexMesh ▾` の形状別表示メニュー: メニューの生成、個別/マスタートグル、surface/region/geometry カテゴリカラーの凡例、ジオメトリを持たないソースのグレーアウト表示、`locationInMesh`/`locationsInMesh` キープポイントのトグル。
- `test_block_mesh_panel_topo_select.py` — `topoSet ▾` の形状別表示メニュー: メニューの生成、個別/マスタートグル、Show all/Hide all、アクションカラーの凡例、ジオメトリを持たないソースをまとめた「Non-geometric sources (N)」サブメニュー、点/平面シェイプの STL エクスポートからの除外。
- `test_block_mesh_renderer_topo.py` — `_make_shape_mesh` によるジオメトリ生成: 真のコーンとフラスタム（円錐台）、中空の円環、`rotatedBoxToCell`、球（スカラー radius およびベクトル radius によるだ円体）、`stl_path` によるメッシュ読み込み（ファイルあり／なし、および `read_surface_mesh` 経由の gzip 圧縮された `.stl.gz` ファイル）。`read_surface_mesh` のプレーンファイルのパススルー。オーバーレイクリップヘルパー（`_expanded_bounds` の軸ごとのパディング〈退化した 2D 軸を含む〉、`_clip_to_bounds` の範囲内／クリップ／完全に外側／包含時のスタンドインの各ケース）。
- `test_bm_side_by_side_multi_dict.py` — `⊞` サイドバイサイドコーナーボタン（`_update_bm_side_by_side_btn`）: `blockMeshDict`・`topoSetDict`・`snappyHexMeshDict`・`controlDict`（サンプリングオーバーレイ）では有効化され、無関係な辞書（例: `fvSchemes`）では無効化されることを検証。ツリー/BlockMesh スプリッターの両ペインが折りたたみ不可であることと、パネルが 150 px の最小幅を保つことも検証。
- `test_flow_layout.py` — `FlowLayout`（ui/widgets/flow_layout.py）: 最小幅が最も幅の広い 1 項目分に等しいこと、狭めたときの `heightForWidth` による折り返し、折り返し後の項目の順序と位置、`takeAt` の管理を検証。
- `test_boundary_view_copy.py` — `BoundaryViewPanel._table_data()` と Copy Table: 両方の向きでの Markdown・CSV 出力。
- `test_case_switch_clears_block_mesh_panel.py` — 別のケースに切り替えたとき、`_load_case_dir()` が `BlockMeshPanel` の状態を（`_topo_shapes`/`_snappy_shapes` の一覧だけでなく）`clear()` 経由で完全にリセットすること: シェイプ別メニューアクション、`non_geometric` 一覧、`locationInMesh`/`locationsInMesh` マーカー、`Export Shapes as STL…` アクションの有効/無効状態がすべてクリアされること。
- `test_code_editor.py` — `CodeEditor` の折りたたみマップ計算、折りたたみ/展開のトグル、`FoamFile { … }` ヘッダーとファイル先頭のコメントバナーの自動折りたたみ。
- `test_comparison_tree_panel.py` — `ComparisonTreePanel`: `load` でヘッダーラベルを設定しプロキシを更新して FoamFile ノードを折りたたみ Type 列の表示を再適用すること、`clear` でモデルとヘッダーをリセットすること、`set_type_column_visible` で Type 列の表示を切り替え `load` をまたいで状態が維持されること、`use_value_requested` シグナルが接続可能なこと。
- `test_diff_state_reset_on_case_change.py` — `_reset_diff_for_case_dir` の回帰テスト: 別のケースを開くとアクティブな比較（差分状態・バー・パネル・解析キャッシュ）がクリアされること、同じケースの再読み込みでは維持されること、比較が無いときは何もしないこと。
- `test_drag_drop_open_case.py` — `MainWindow` のドラッグ＆ドロップによるケースオープン: `dragEnterEvent`、`dropEvent`、すべての子ウィジェットを有効なドロップ先にする `eventFilter`。
- `test_duplicate_case.py` — ケース複製: 「全ファイル」モードと「アプリ表示ファイルのみ」モードでコピーされる内容、コピー先の作成、ケースに登録された追加ファイルもコピーされること。
- `test_editor_panel.py` — `EditorPanel` の `user_text_changed` の抑制: プログラム的なパス（`set_text()`、`reload_highlighting()` — `QSyntaxHighlighter.rehighlight()` は書式しか変わらなくても `textChanged` を発火させ、以前は Generate OpenFOAM Keywords の後にファイルが編集済みになっていた）では発火せず、ドキュメントへの直接編集では発火すること。
- `test_export_stl_action_state.py` — `STL ▾` メニューの「Export Shapes as STL…」アクション（`_export_stl_act`）: 初期状態は無効、`update_topo_set`/`update_snappy_hex_mesh` で描画可能なシェイプを読み込むと有効化、`clear()` や空の辞書の再読み込み後は再び無効化されること。
- `test_export_stl_dialog.py` — `ExportStlDialog`: topoSet と snappyHexMesh を合わせたシェイプの行数とラベル付け、渡された可視状態セットが初期チェック状態に反映されること、Select All/Deselect All、チェックした各シェイプが 1 つの `.stl` として書き出され `pyvista.read()` でラウンドトリップ確認できること、ラベル衝突時のファイル名重複排除、縮退ジオメトリを例外を投げずにスキップすること、`_safe_filename` のサニタイズ処理。
- `test_file_list_panel.py` — 差分フィルター: `set_diff_filter_enabled` でチェックボックスの表示・非表示・チェック解除、フィルターが差分件数 0 のファイルアイテムを非表示にしヘッダーは常に表示、`mark_diff` がフィルター有効時に即座にアイテムの表示を更新すること。
- `test_find_examples_dialog.py` — `FindExamplesDialog`: 非モーダルなウィンドウモダリティ、インストールコンボの初期化（`discover_installations` を偽インストールにモンキーパッチ）、スレッド検索後の Tutorials/caseDicts グループ化結果、チュートリアル一致と caseDicts 一致でのプレビュー表示と比較/複製ボタンの有効/無効、クリップボードへのコピー、チュートリアルケースルートを渡す `compare_requested`/`duplicate_requested` の発行、一致なし・空クエリ・検索対象なしのステータスメッセージ、ファイル名フィルタ。
- `test_foam_highlighter.py` — `FoamHighlighter`: コメント、文字列、`#directives`、`$macro` 参照、予約キーワード、数値（`wall0`/`inlet-1` のような識別子内の数字を色付けしない lookaround ガードを含む）、同じガードを共有するキーワードルール（`y0.1` や `off.1`、シェルの `config.fi` のようなドット付き識別子が分割されない）、スキーマレジストリとキーワード JSON（ユーザーの `foam_keywords.json` 優先、同梱の `foam_keywords.default.json` にフォールバック、両方無ければ空集合）から得られる辞書キーの色付け、1,000 キーワード単位の `QRegularExpression` チャンク分割、有効/無効の切り替え。
- `test_log_summary_dialog.py` — `LogSummaryDialog`: 非モーダルなウィンドウモダリティ、ケースディレクトリ内で最も新しく更新された `log.*` ファイルをデフォルト選択してその要約を表示すること、ファイルフィールド変更時の再パース、空のケースディレクトリでのフォールバックメッセージ。
- `test_main_window_save_refresh.py` — `test_main_window_split.py` の構造チェックのみとは異なる、初めての振る舞いレベルの `MainWindow` テスト: 保存せずに編集しても `constant/polyMesh` メッシュインジケーターが変化しないこと、`save_file()`/`save_all_files()` のどちらも即座にファイル一覧を更新して、フル「Reload Case」なしで staleness インジケーターが更新されること。
- `test_main_window_split.py` — Mixin 構造: 各 Mixin が正しいメソッドを保有すること（`_BoundaryOpsMixin` の `_on_patch_selected`、`_TreeCrudOpsMixin` の `_apply_comparison_value`、`_FoamMonitorOpsMixin` の foamMonitor 関連メソッドを含む）、Mixin 間の重複がないこと、`MainWindow` がすべての Mixin を継承していること。
- `test_manage_extra_files_dialog.py` — `ManageExtraFilesDialog`: 登録済みの追加ファイル・ディレクトリの表示と削除操作。
- `test_rename_boundary.py` — `find_rename_targets()`: `blockMeshDict` 内の `boundary_entry` ノードおよび `boundaryField` ブロック内のパッチ `dictionary` ノードの検出、無関係な辞書への誤検出なし、空入力のエッジケース。
- `test_run_tool_dialog.py` — `RunToolDialog`: 初期状態のライブプレビューが `get_command()` と一致すること、チェックボックス/値編集によるコマンド更新、`last_values` の復元と `get_values()` の新しいダイアログへのラウンドトリップ、解析不能な追加オプションでの実行ボタン無効化、プレフィックスチェックボックスによるシェルプレフィックスの付加、Browse によるケース相対パスの挿入（ケース外は絶対パス）。
- `test_stays_open_menu.py` — ツールバーのドロップダウンメニュー（`Vertices ▾`、`Blocks ▾`、`Scale ▾`、`topoSet ▾`、`snappyHexMesh ▾`）がチェック可能項目のクリックでは開いたままになり、チェック不可のアクションでは通常どおり閉じること。
- `test_terminal_panel.py` — `SimpleTerminalWidget` と `TerminalPanel`: 初期状態、作業ディレクトリの切替、クリーンアップ、コマンド履歴、タブラベル、`run_command()`（シェル準備前のキューイングを含む）。
- `test_tools_ops_mesh_actions.py` — Tools メニューの「Run *」アクションと Run Allrun/Run Allclean/Clean Case: blockMesh/snappyHexMesh/topoSet/setFields/checkMesh の（実物の、exec をパッチした）`RunToolDialog` を受理した後に偽のターミナルパネルへ送信される正確なコマンド文字列、キャンセル時に何も送信されないこと、時間ディレクトリが存在する場合にダイアログへ渡される再実行警告テキスト、`state.run_tool_options` からの前回オプションの復元、setFields の 0/ 復元プレフィックスチェックボックス（`0.orig/` があれば存在しデフォルトでチェック、なければ非表示、チェックを外せば「そのまま実行」）。Allrun/Allclean のスクリプト欠如警告、`log.*` が存在する場合の Allrun 三択プレフライト — クリーンしてから実行・そのまま実行・キャンセル —、Allclean への委譲または `-auto` による 0/ 削除に言及する Clean Case ダイアログ、`_update_tools_actions()` によるこれらのアクションおよび View Log Summary（ターミナルは不要でケースのみ必要）の有効化。
- `test_tree_color_lexer_dispatch.py` — `unknown_raw_entry` の琥珀色表示、レキサーの `//` 挙動、パーサの `_PAREN_DISPATCH` テーブル。
- `test_tree_copy_paste.py` — ツリーの Copy/Paste Value: コピーした値の round-trip、異なる型のノード間でのペースト、サポート対象外のノード型を拒否するガード。
- `test_tree_undo_redo.py` — スナップショット方式のツリー Undo/Redo: インライン編集の Undo が値・エディタテキスト・クリーンなダーティフラグを復元すること（Redo で再適用）、複数ステップの Undo、新しい編集による Redo ブランチのクリア、拒否された編集の迷子スナップショットのスキップ、削除/エントリ追加の往復、1 つの CRUD 操作がちょうど 1 つのスナップショットを生むこと（シグナルによる二重チェックポイントなし）、複数ファイルのスナップショットが全ファイルを復元すること、ケース再読み込みでのスタッククリア、深さ上限。
- `test_tree_inline_edit_dirty.py` — Tree パネルのインラインセル編集がファイルをダーティにしエディタテキストを再生成すること、拒否された編集はファイルをクリーンなままにすること。
- `test_view_log_summary_action.py` — `_on_view_log_summary_clicked`: ダイアログを閉じた後の再表示（閉じても破棄はされず非表示になるだけなので、キャッシュ済みインスタンスは再度 raise するのではなく show し直す必要がある）、ケースディレクトリ未設定時の no-op、ケース切り替えへの追従（`_load_case_dir` が次のメニュークリックを待たず、開いたままのダイアログへ `set_case_dir()` で即座に新しいディレクトリを反映する）。

**`tests/services/`**
- `test_backup.py` — バックアップファイルの命名（`.bak_<タイムスタンプ>`）と内容（ファイルが開いている場合はインメモリバッファ、それ以外はディスク上の内容をキャプチャ）。
- `test_case_copier.py` — `copy_visible_files`: 可視ファイルがレイアウトを保ってコピーされること、非表示エントリ（ルートの `log.*`、時刻ディレクトリ、未登録ファイル）はスキップされること、登録済み追加ファイルと `.foam-editor-files.json` 自体が引き継がれること、設定ファイルなしでも動作すること、ネストしたコピー先の作成。
- `test_case_files_config.py` — `TestCaseFilesConfigDirs`: `DirEntry` の追加・削除・インプレース更新、プレーン文字列 JSON の後方互換ロード、設定リセット。
- `test_case_loader.py` — `detect_time_dirs` と `TestExtraDirs`: フラット・再帰スキャン、存在しないディレクトリの許容、重複排除。
- `test_example_search.py` — `example_search`: インストールルート／素の tutorials ディレクトリ／非インストールディレクトリに対する `installation_from_dir`、環境変数マッピングの注入・`extra_roots` の優先・重複排除を含む `discover_installations`、`stop` 境界付きで祖先を遡る `case_root_for`、両ソースでの一致（source/case_root/line_numbers/snippet フィールド）・大文字小文字を区別しない一致・`file_name` と `sources` フィルタ・`max_hits` 上限・`cancelled` による早期終了・バイナリ／サイズ超過ファイルのスキップ・一致行番号の 50 行上限・空クエリの `ValueError`・`progress` コールバックを検証する `search_examples`。
- `test_foam_env.py` — `foam_env_dirs`: 明示的な `FOAM_*` 変数が `WM_PROJECT_DIR` フォールバックより優先されること、サブディレクトリ単位のフォールバックはディレクトリが存在する場合のみ働くこと、無効・空白の変数は未設定扱いになること、バージョンの解決。
- `test_log_summary.py` — `parse_log`/`format_summary`: `blockMesh` の Mesh Information/Patches 抽出と致命的エラー検出、`snappyHexMesh` の `Wrote mesh in` マーカーによるフェーズ分割・カテゴリごとの細分化反復回数・最終的なパッチ別レイヤーテーブル・件数付きの警告重複排除、`topoSet` のマルチソースセットの集約（`Read set` チェックポイントは新規セットではなく同一セットの継続として扱われること）、ソルバーログ — 収束した定常計算（Run/Residuals フェーズ、収束メッセージ、合計時間）、Courant 行と ESI 形式の `Time = 0.005s` 単位サフィックスを含む非定常計算、致命的エラーや `End` 未到達の実行が FAILED になること、`Time =` 行はあるが残差のない `checkMesh` 型のログが汎用パスに留まること、未知のユーティリティに対する末尾行フォールバック。
- `test_tool_options.py` — `tool_options`: 期待される `TOOL_SPECS` の集合とデフォルトコマンド（snappyHexMesh のデフォルトでオンの `-overwrite`）、`build_args` の bool/value/file の仕様順処理、空値の省略、追加テキストの shlex 分割（閉じていない引用符 → `ValueError`）、古い未知フラグの無視、`build_command` のクォート・生プレフィックス・`tee log.<ツール名>` サフィックス。

**`tests/app_config/`**
- `test_app_config.py` — `AppConfigManager`: ウィンドウサイズ、デフォルトケースディレクトリ、Case Library ディレクトリ（`$WM_PROJECT_DIR/tutorials` フォールバックを含む）、`save()`/`reset()` のセマンティクス、`app_config.json` が存在しない場合のフォールバック、設定の組み合わせ、JSON 構造、フィーチャーフラグの扱い（`set_feature`/`set_features`）。
- `test_json_io.py` — `load_json` の欠落・破損・正常 JSON の扱い、`save_json` のラウンドトリップと親ディレクトリ作成、`atomic_write_text` が成功時に `.tmp` を残さないこと、最終リネームやシリアライズが失敗しても元ファイルが無傷のまま（一時ファイルも掃除される）こと。
- `test_keyword_generator.py` — `keyword_generator`: `*.C`/`*.H` から辞書読み取り呼び出し（`lookup`/`get<…>`/`readEntry`/`found` など）を収集する `scan_src_lookup_keywords()`（キーワードでない形式は除外）、フィクスチャのインストールツリーに対する `generate(project_dir=…)` — 環境変数は無視、`version` はディレクトリ名由来、ペイロードの来歴メタデータ、何も収集できない場合の `RuntimeError`。

**`tests/schemas/`**
- `test_schemas.py` — `ChoiceItem`/`KeySchema`、`schema_config.json` の読み込み・保存・リセット・削除、`SchemaRegistry` のプレーン/親修飾/祖父母修飾ルックアップ、`snappyHexMeshDict` スキーマモジュール、設定済みモジュール一覧。

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
| `action_list` | `topoSetDict` の `actions ( … );`; `value=None`、子ノードは `action_entry` |
| `action_entry` | `action_list` 内の無名 `{ … }` ブロック; `name=""`、子ノードは辞書エントリ |
| `named_dict_list` | 名前付き辞書の丸括弧リスト（省略可能な構文）— `sets ( y0.1 { … } … );` / `surfaces ( … );`（従来の sampleDict スタイル）。`(` の後に `name {` が続く場合のみ先読みで生成されるため、単純な単語リスト（`sets (setA setB);`）は従来どおり `raw_list` として解析される |
| `named_dict_entry` | `named_dict_list` 内の名前付き `{ … }` エントリ |
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
    "named_dict_list", "named_dict_entry",
    "field_value_block",
    "action_list",
})
```

子ノードは `node.name` で照合します。無名ノード（`name` が空）はスキップします。`field_value_block` については `_diff_field_value_block` が `node.value` の `field_name` でアイテムを照合します（[`field_value_block` の子ノードが `value` に格納される](#field_value_block-の子ノードが-value-に格納される)と同じレイアウト）。`action_list` については `_diff_action_list` が `action_entry` の子ノードを**インデックス順（位置）** で照合し、各エントリの名前付きサブエントリをキーで比較します。`action_entry` ノード自体は無名（`name=""`）のため名前で照合できません。

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

`FIELD_DIRS` のスキャン（`0/`、`0.orig/`）はまず直下のファイルを収集し、次に存在するサブディレクトリを 1 階層だけ下ります。これにより `chtMultiRegionFoam` ケースでよく見られる `0/heater/T` や `0/bottomWater/p` のようなリージョンごとのフィールドファイルが拾われます。`_group_name` はこれらのパスに対してすでに `"0/heater"` を返すため、ファイル一覧では自動的に専用のグループヘッダーの下に表示されます。バウンダリパネルの `_available_field_dirs` はこの検出をミラーし、Directory セレクタに `"0/heater"` などを表示します。`_is_in_dir` は複数階層のディレクトリ名を正しく照合するために `Path.is_relative_to` を使用します。

`manage_extra_files_dialog.py` では **Toggle Recursive** ボタンで選択中のディレクトリエントリの再帰フラグを切り替えられます。生パスは各アイテムの `Qt.UserRole` に格納され、再帰が有効な場合は表示テキストに `[recursive]` が付加されます。`result_dirs` プロパティは最終的な `list[DirEntry]` を返します。`_file_mgmt_ops.py` はこの値を使ってステータスバーの集計（追加・削除・フラグ変更の件数）を計算します。

## ケースルートのスクリプト

`list_case_files` はケースルート直下も `ROOT_SCRIPT_GLOB`（`All*`）で glob するため、`Allrun`、`Allrun.pre`、`Allclean` などが自動的に一覧へ追加されます — これらは Tools メニューが実行するスクリプトであり、一覧に含めることで `copy_visible_files` が複製ケースにも引き継ぎます（`shutil.copy2` が実行権限を保持）。それ以外のルート直下のファイル（ログ、`*.foam`、結果）は従来どおり表示されません。`model/file_list_model.py` はルート直下のファイルを `ROOT_GROUP`（`"."`）キーでグループ化して最後にソートし、`file_list_panel.py` はそのヘッダーを「case root」と表示します（`group_display_name` 経由。ヘッダーのコンテキストメニューや Add files ダイアログのラベルにも使用）。`[+]` マーカーは付けません（ルートにはほぼ常に未表示のログが存在し、マーカーが常時点灯してしまうため）。ヘッダーには他のグループと同じ New file / Add files コンテキストメニューがあり — pathlib が `"."` を正規化するためどちらのハンドラもそのまま動作します —、`list_directory_files` はドットファイルを除外するため、Add ダイアログに `.foam-editor-files.json` が現れることはありません。

スクリプトは辞書ではなくシェルファイルなので、テキスト専用の処理経路を通ります。`is_script_text` / `is_script_path`（`foam/utils.py`）が `#!` シバンを検出し、`is_log_filename` は同じ経路を `log.*` 実行ログ（ユーザーの追加ディレクトリ経由で一覧に入り得る）にも拡張します。`load_selected_file` と `save_file` はどちらの場合も解析をスキップし（ツリーには `_clear_current_file` と同様に空のルートが読み込まれます）、`apply_text_to_tree` はステータスメッセージを出して拒否し、diff の両経路（`_recompute_diff`、`_precompute_diff_step`）もスキップするため、無意味なツリー diff は表示されません。`log.*` の行はさらに `file_list_panel.py` の `_TEXT_ONLY_ROLE` によりグレーで薄く描画されます（色の優先順位: dirty > diff > text-only > extra）。保存は通常の `Path.write_text` で既存ファイルをそのまま書き換えるため、実行権限は保持されます。

エディタはスクリプトをシェルコードとしてハイライトします。`EditorPanel.set_text` がシバンを検出して `CodeEditor.set_shell_mode` を呼び、`FoamHighlighter`（`ui/widgets/_foam_highlighter.py`）を `"shell"` モードに切り替えます — `#` コメント、引用符付き文字列、`$変数`、OpenFOAM の RunFunctions（`_SHELL_KEYWORD_RE`）、さらに通常の `_build_value_kw_rules()` キーワードチャンクも適用されるため、ユーティリティ・ソルバー名も色分けされます。シェルモードでは `/* */` ブロックコメントの状態機械はバイパスされます。

`list_case_files` の追加ディレクトリスキャンは隠しエントリ（`.` で始まるパス要素）を常にスキップするため、ケースルート（`"."`）を追加ディレクトリとして登録してもアプリ自身の `.foam-editor-files.json` がアプリ内で編集可能になることはありません。

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

`_mark_dirty()`（`ui/mixins/_model_ops.py:102`）は両方の値を `True` に設定し、ウィンドウタイトルに `*` サフィックスを追加し、`file_list_panel.mark_dirty()` を呼び出してファイルリストにインジケーターを表示します。これは `_after_model_edit()`（`write_root()` 経由でテキストを再生成するツリー編集後）と `_on_user_text_changed()`（エディタへの人間によるキー入力時）から呼び出されます。

`_after_model_edit()` 自体は 2 つの経路で呼ばれます。1 つは明示的な呼び出しで、Detail パネルの「Apply」ハンドラとツリー CRUD 操作（`_tree_crud_ops.py`）が `FoamTreeModel.setData()` / `insert_node()` / `remove_node()` を呼び出した直後に行われます。もう 1 つは `_load_tree()` 経由で、これは `FoamTreeModel.dataChanged` を `_on_tree_data_changed()`（`ui/mixins/_model_ops.py`）に接続し、`Qt.EditRole` を伴う発行だけにフィルタします。この signal 接続が、Tree パネルのインラインセルエディタで直接行われた編集を捕捉する仕組みです — Qt のアイテムデリゲートはビューから直接 `setData()` を呼び出すため、そのパスには明示的な `_after_model_edit()` 呼び出しがどこにもありません。この `dataChanged` フックがなければ、インラインでのツリー編集はノードを変更するだけで、エディタテキストの再生成もファイルのダーティマークも行われません。`Qt.EditRole` フィルタは差分ハイライトの再描画（`set_diff()` / `clear_diff()`、`BackgroundRole` のみで `dataChanged` を発行）を除外します。

`_save_current_buffer()`（`ui/mixins/_model_ops.py:29`）はファイルスイッチ前に `editor_panel.get_text()` を `state.file_buffers[state.current_file]` へフラッシュし、`state.text_dirty` を `state.file_dirty[state.current_file]` に書き戻します。これにより、スイッチをまたいでも未保存の編集がインメモリで保持されます。

`_mark_path_dirty(path)` は現在開いているファイルに関係なく特定のパスをダーティとしてマークします。複数のフィールドファイルにわたって境界パッチをリネームするような操作で使用されます。

## ツリーのコピー・ペーストショートカット

`_setup_tree_copy_paste()`（`ui/mixins/_tree_crud_ops.py:27`）は `Qt.WidgetShortcut` スコープを使って Ctrl+C と Ctrl+V の `QShortcut` インスタンスを `tree` ウィジェットに直接アタッチします。

```python
copy_sc = QShortcut(QKeySequence.Copy, self.tree)
copy_sc.setContext(Qt.WidgetShortcut)

paste_sc = QShortcut(QKeySequence.Paste, self.tree)
paste_sc.setContext(Qt.WidgetShortcut)
```

`Qt.WidgetShortcut` は `self.tree` がキーボードフォーカスを持つ場合のみ発火するため、テキストエディタでの Ctrl+C は影響を受けません。ツリーセルがインライン編集モードの場合も発火しません。その状態では Qt がセルエディタ自身の選択コピー機能に Ctrl+C をルーティングします。

同じ 2 つのアクションはコンテキストメニューにも表示されます（**Copy Value** / **Paste Value**）。選択したノード型が値の編集をサポートしない場合、ペーストはメニューで無効化され静かに拒否されます。

## ツリー編集の Undo/Redo

`ui/mixins/_undo_ops.py` はスナップショット方式のツリー編集 Undo/Redo を実装しています。ツリーの変更はすべて `write_root()` による完全な再シリアライズで終わるため、変更前の状態はシリアライズ済み*テキスト*としてチェックポイントされます — 操作が触れるすべてのファイルの `{path: text}` とダーティフラグを 1 つの `UndoSnapshot`（`ui/app_state.py`）として保持します。Undo はスナップショットを再パースし、既存の `_load_tree()` によるフル再構築パスでツリーを再読み込みします。ツリーの展開・選択状態は保持されません。履歴は**単一のグローバルタイムライン**（`UndoState.undo_stack` / `redo_stack`）で、ファイルごとではありません: Ctrl+Z はどのファイルを表示中かに関わらず最後のツリー操作を取り消し（`_restore_undo_snapshot` は、カレントファイルがスナップショットに含まれない場合、対象ファイルへ表示を切り替えます）、*いかなる*新規編集も Redo ブランチをクリアします。複数のフィールドファイルにまたがる境界操作は全ファイルを 1 つのスナップショットに格納するため、1 回の Undo で触れたすべてのファイルが復元されます。スタックは件数上限（`_UNDO_DEPTH` = 50）と総バイト数上限（`_UNDO_MAX_BYTES`）の両方で制限され、ケース切り替え時にクリアされます。

チェックポイントは `_after_model_edit()` への到達経路と対応する 2 つの経路でスタックに積まれます:

- **`FoamTreeModel.about_to_change`** — `setData()` の先頭で、編集が検証される*前*に emit されるため、スナップショットを push せず `pending` として退避するだけです。`_on_tree_data_changed`（`setData` 成功時のみ発火）が `_commit_pending_undo` を呼び、pending を push して Redo をクリアします — 結果の状態が同一なら（値が変わらない編集）破棄します。拒否された編集は `dataChanged` を emit しないため、退避したスナップショットは静かに破棄され、スタックは変化しません。これがインラインデリゲート、Paste Value、Detail パネルの Apply ハンドラをカバーします。
- **明示的な `_checkpoint_for_undo(paths)` 呼び出し** — ノードを直接変更するすべての操作の先頭行（`_tree_crud_ops.py` の CRUD、`_tree_sync_ops.py` の `apply_text_to_tree` / `_on_blockmesh_vertices_changed`、`_boundary_ops.py` の全境界操作）。呼び出し側が実際の変更を保証するため即座に commit します。次のイベントループティックでリセットされる `UndoState.op_active` が、その操作が内部で行う `setData` からの余分な `about_to_change` 退避を抑制します。

カレントファイルのスナップショットテキストは常にエディタテキストです: 同期している間は読み込んだファイルとバイト単位で一致し（完全に Undo し終えたファイルはディスクと比較してクリーンになる）、ユーザーが未適用のフリーテキストを入力している場合は画面に表示されている内容そのもの — いずれも Undo が復元できるべき状態です。スナップショットが「クリーン」を主張するファイルは、ダーティフラグを下ろす前にディスクと照合されます（変更と Undo の間に保存が行われた可能性があるため）。

コピー・ペーストと同様、Ctrl+Z / Ctrl+Shift+Z のショートカットはツリーに `Qt.WidgetShortcut` スコープで割り当てられているため、下部のテキストエディタは自身のネイティブ Undo を保ちます。両アクションはツリーのコンテキストメニューにも表示されます（**Undo Tree Edit** / **Redo Tree Edit**）。

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

`AppConfigManager`（`app_config/app_config_manager.py`）はアプリケーションの永続設定を管理します。`get_app_config()` でシングルトンインスタンスを取得し、セッション全体で再利用します。読み込み/保存の実処理は `app_config/json_io.py`（`load_json`/`save_json`）に委譲しており、これは `services/case_files_config.py` とも共有しています。`save_json` はアトミックに書き込みます（`atomic_write_text`: 隣接する `.tmp` ファイル + `os.replace` なので、書き込みが失敗しても既存の設定ファイルが壊れることはありません。`tempfile.mkstemp` ではなく名前付き一時ファイルを使うことで umask デフォルトのパーミッションを保ちます）。

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

**サイドバイサイドモード** — `⊞` トグルボタン（`_bm_side_by_side_btn`）が `QTabWidget` のコーナーウィジェットとして追加されます。有効化すると `_on_toggle_bm_side_by_side` が `block_mesh_panel` を `upper_tabs`（`QTabWidget`）から `_tree_bm_splitter`（`right_upper_splitter` をラップし Tree タブのコンテンツとなる `QSplitter(Qt.Horizontal)`）へ再ペアレント化します。リペアレント前にまず Tree タブへ切り替えてスプリッターを可視状態にし、`setSizes([1,1])` と `_init_plotter()` は `QTimer.singleShot(0, ...)` で次のイベントループティックまで遅延させます。サイドバイサイドモードを切ると `block_mesh_panel` は通常タブとして `upper_tabs` に戻されます。`_update_bm_side_by_side_btn`（`ui/mixins/_panel_ops.py`）は、現在のファイル名が `blockMeshDict`・`topoSetDict`・`snappyHexMeshDict`・`setFieldsDict`、またはサンプリング名（`SAMPLING_DICT_NAMES`: `controlDict`・`sample`・`probes`・`surfaces`・`singleGraph`）のいずれか（いずれも同じ 3D ビューに描画される — `block_mesh_extractor.py`、`topo_set_extractor.py`、`snappy_hex_mesh_extractor.py`、`set_fields_extractor.py`、`sampling_extractor.py` を参照）で、BlockMesh タブ自体が有効、かつ xterm が非アクティブなときにボタンを有効化します。それ以外はボタンを無効化し、サイドバイサイドモードが有効であれば強制的に解除します。

**比較パネルの表示制御** — `comparison_panel` は起動時に `right_upper_splitter` へ追加されますが直後に非表示（`comparison_panel.hide()`）になります。`QSplitter` は非表示の子ウィジェットを無視するため、ハンドルや隙間は表示されません。`_on_side_by_side_toggled(True)` では `setSizes` 前に `comparison_panel.show()` を呼び、`_on_side_by_side_toggled(False)` と `_clear_diff` では `comparison_panel.hide()` を呼びます。

**プレビューモード** — `BlockMeshPanel` は `update_block_mesh()` 呼び出しごとに設定される 2 つのフラグを持ちます: `_has_variables`（`vertices` の raw_list 値に `$` 文字が含まれる場合 True）と `_preview_mode`（デフォルト False、**Preview** ボタンでトグル）。`_has_variables` が True の場合、Vertices グループボックス内のテーブル上部に `_vtx_info_bar`（琥珀色の **⚙ Variable-based** チップ + **Preview** トグルボタン）が表示され、X/Y/Z セルは読み取り専用になります（`rw_flags = ro_flags`）。`_preview_mode` が True の場合はセルが編集可能になり、`_on_cell_changed` は `vertices_changed` を emit する代わりに `_render()` を直接呼び出してツリーとファイルを変更しません。`_on_refresh()` はプレビューモード中に `self._root` から再抽出してから `_render()` を呼び出し、頂点データのリセットとプレビュー終了を同時に行います。

## テスト

```bash
python3 -m pytest -q
```

`pytest -q` だと import 周りで問題が出る場合は、プロジェクトルートの扱いが安定しやすい `python3 -m pytest -q` を使う方が安全です。

`tests/test_lint.py` はテストスイートの一部として `ruff` と `mypy` を実行するため（後述）、`pytest -q` を実行するだけで lint / 型チェックの regression も検出できます。

## Lint と型チェック

設定は `pyproject.toml` にあります。`ruff` にはリポジトリ全体を対象とする `include`/`exclude` 制限はありませんが、現時点でクリーンなのは `foam/`、`model/`、`app_config/`、`schemas/`、`services/`、`ui/app_state.py` のみです（それ以外の `ui/` には未整理の既存違反があります）。そのためスコープを指定して実行します。

```bash
ruff check foam model app_config schemas services ui/app_state.py
```

`mypy` は `pyproject.toml` の `[tool.mypy] files` で `foam/`、`model/`、`app_config/`、`schemas/`、`services/`、`ui/app_state.py` に明示的にスコープされています。静的型付けの効果が最も高い、ほぼ純粋な Python 層に加え、スコープを拡張したこの `ui/` の 1 ファイルが対象です。それ以外の `ui/` は対象外です。PySide6 のスタブは UI 層全体で使われているフラット化された enum アクセス（`Qt.Horizontal` など。完全修飾形は `Qt.Orientation.Horizontal`）を認識せず、含めると大量の誤検出が発生するためです。

```bash
mypy
```

`foam/nodes.py` の `NodeType` という `Literal` が、有効な `node_type` 値の確定的な一覧です。この集合に含まれない値への代入や比較は `mypy` が検出します。各値の意味は上記の「ノード型」セクションを参照してください。

## 更新候補

将来のリリースに向けたメモ（現時点では未計画）:

- **比較モードでのサイドバイサイドの参照*テキスト*エディタ** — 比較モードは現在、参照ケースを読み取り専用の*ツリー*として表示している。参照ファイルのテキストを読み取り専用エディタとしてメインの Editor タブの横に表示できれば、キーや値を自由にコピー＆ペーストできる（現状、例のケースについては非モーダルな Find OpenFOAM Examples のプレビュー + 「選択範囲をコピー」で代用できるが、任意の参照ケースには使えない）。比較モードの更新の一環として再検討する。


### 保留中のレビュー指摘（Undo/Redo・サンプリング）

Undo/Redo とサンプリング機能のコードレビューで挙がったが、その時点では未修正のまま残した軽微な項目（いずれも「確定」ではなく「可能性あり」— トリガーが狭い、潜在的、または設計の堅牢化にとどまる、と判断）。これらの領域に次に手を入れる変更に合わせて取り込む価値がある:

- **`_restored_dirty` が復元ファイルを誤ってダーティにする可能性**（`ui/mixins/_undo_ops.py`）— `write_root` でシリアライズしたスナップショットを生のディスクファイルと比較しているが、`state.parsed_roots` にのみキャッシュされたクリーンなファイル（ノードに `raw_text` がない）は再整形されたテキストになりディスクと差が出るため、複数ファイル操作の Undo でダーティ扱いになり、次の Save All で整形のみの書き換えが行われてしまう。ディスクを再読み込みする代わりに、メモリ上のバッファと比較するか、スナップショットが記録したフラグを信頼する。
- **`UndoState.op_active` のリセットタイミングが脆い**（`ui/mixins/_undo_ops.py`）— 二重チェックポイント防止ガードを `QTimer.singleShot(0, ...)` でクリアしているが、これはネストしたイベントループ（`QMessageBox`/`QDialog.exec`）内で発火する。現状、`_checkpoint_for_undo` とその変更の間にダイアログを開く呼び出し箇所はないため潜在的だが、将来そのような操作があるとモデルの `about_to_change` が変更途中の 2 つ目のスナップショットを積み（1 回の編集に 2 回の Undo が必要になる）。ガードを同期的な操作スコープに限定（例: コンテキストマネージャ）すればタイミング依存を除去できる。
- **変更パスが Undo チェックポイントを取ることを強制する仕組みがない**（`ui/mixins/_tree_crud_ops.py`・`_tree_sync_ops.py`・`_boundary_ops.py`）— Undo のカバレッジは手動で配置した約 18 個の `_checkpoint_for_undo` 呼び出しと、`setData` 経由編集の `about_to_change` シグナルに依存している。将来、明示的な呼び出しを忘れた直接変更パスは静かに Undo 不可になる（後の Ctrl+Z がそれを飛び越す）。変更後の 1 箇所のチョークポイントで直前のシリアライズ済みテキストを差分比較するか、カバレッジテストを設ければ堅牢になる。
- **サンプリングオーバーレイがファイルをベース名でキーイングしている**（`ui/panels/block_mesh_panel.py`）— `_sampling_by_file` は `Path(path).name` をキーにしているため、ベース名が同じ 2 つのサンプリング辞書（ユーザーが 2 つ目の `sample` を含む追加ディレクトリを加えた場合にのみ到達）が互いのシェイプを上書きし、`source_file` の表示も誤る。フルパスでキーイングする（表示はベース名）。

## 謝辞

- [PyInstaller](https://pyinstaller.org/) — スタンドアロン実行ファイルのビルドに使用。
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — `blockMeshDict` の 3D ビューア（BSD-3-Clause、オプション）。
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — テストフレームワーク。

[OpenFOAM Foundation](https://openfoam.org/) および [OpenCFD / ESI Group](https://www.openfoam.com/) をはじめ、OpenFOAM をフリーのオープンソース CFD ソフトウェアとして開発・維持してきたすべての貢献者の方々に深く感謝いたします。
