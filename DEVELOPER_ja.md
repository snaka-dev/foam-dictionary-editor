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
│   ├── capture_screenshots.py     # tools/screenshot_specs.json から docs/SCREENSHOTS.md のギャラリーを再生成する。保存されたウィンドウ状態を実際の MainWindow に適用し、ImageMagick の `import -frame` で撮影する。ショット × テーマごとに別プロセスで実行するため、light/dark のペアはテーマ以外が完全に一致する（「スクリーンショットの撮影」参照）
│   ├── screenshot_specs.json      # ギャラリーのショット一覧。画像 1 枚につき ui/window_state.py の WindowState 1 つと、テーマごとの出力ファイル名
│   ├── capture_dialog.py          # ギャラリーのもう半分であるダイアログを撮影する。ダイアログは独立したトップレベル X ウィンドウであり capture_screenshots.py からは手が届かないため。ショットは JSON spec ではなく DIALOG_SHOTS 辞書に置く（ダイアログは型付き Python 引数から構築するため）。テーマ・言語・import のルールは共通（「スクリーンショットの撮影」参照）
│   ├── demo_driver.py             # tools/demo_specs.json をもとに docs/DEMO_SCRIPTS.md の動画を操作・収録する。開始状態はスクリーンショット spec と同じ WindowState で、その後を実際の X 入力（xdotool）で操作し、収録専用のネストされたディスプレイ上で ffmpeg により収録する（「デモ動画の収録」参照）
│   ├── demo_specs.json            # 動画のシーン一覧。シーンごとの開始状態と、それを操作する steps・ナレーション・表示時間
│   ├── generate_foam_keywords.py  # app_config/keyword_generator.py の CLI ラッパー。--dir でインストールルートを指定（デフォルト: source 済み環境）
│   └── roundtrip_corpus.py        # インストール済み tutorials の全辞書を parse+write してバイト単位で一致した件数を数える。リリースノートのラウンドトリップ数値の測定元
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
│   ├── foam_env.py          # foam_env_dirs(env) → FoamEnvDirs: $WM_PROJECT_DIR/$FOAM_TUTORIALS/$FOAM_ETC/$FOAM_SRC/$FOAM_APP を読む唯一の情報源（各フィールドはディレクトリが存在する場合のみ非 None、project_dir 配下へのフォールバック付き）。純粋な標準ライブラリのみに依存し services/ には依存しないため、services/example_search.py からも import されるものの services/ ではなくここに置く。example_search、keyword_generator、AppConfigManager.foam_tutorials_dir が共有
│   └── keyword_generator.py  # OpenFOAM インストールをスキャン（etc/caseDicts テンプレート、src/ と applications/ ソース内の TypeName/ClassName + addNamedTo* マクロと辞書読み取り呼び出し — lookup("…")、get<…>("…")、readEntry("…") など）して foam_keywords.json を構築（ユーザー生成、gitignore 対象。トラック済みの foam_keywords.default.json ベースラインより優先）。インストールルートは generate(project_dir=…) か source 済み環境（foam_env.foam_env_dirs を利用）から取得。出力は json_io.atomic_write_text でアトミックに書き込み。ペイロードには来歴メタデータ（source、version、generated、note — 識別子名のみで OpenFOAM のソースコードは含まない）を記録。tools/generate_foam_keywords.py と Settings メニューのアクションで共用
├── foam/
│   ├── block_mesh_extractor.py  # blockMeshDict の FoamNode ツリーから頂点・ブロック・境界を抽出。_HEX_FACE_VERTICES + _expand_compact_faces がコンパクト (blockIdx, faceIdx) 境界エントリを 4 頂点リストに展開。_compute_default_faces は、どのパッチにも割り当てられていない外部ブロック面（blockMesh の暗黙の defaultFaces — 擬似 2D ケースが boundary に列挙しない面）を BlockMeshData.default_faces に収集。parse_vertices() はパブリック API。変数解決は var_resolver に委譲
│   ├── var_resolver.py          # 共有の変数解決ロジック: build_var_map(root, skip_keys) が任意の深さの $変数（`-$xMax` のような否定マクロ word ノードを含む）と #eval{} チェーンを反復的に解決。substitute_vars() と eval_foam_expr() は両エクストラクタが使うパブリックヘルパー
│   ├── shapes.py                # SourceShape: すべてのエクストラクタ形状クラス（TopoShape、SnappyShape、SetFieldsShape、SamplingShape）が共有する label/kind/geometry の基底データクラス — 表示名 + ジオメトリ/ソースのキーワード + 解析済みジオメトリ dict。BlockMesh パネル/レンダラーと Export-STL コードが利用する。各サブクラスは独自の追加フィールド（action、category/level/mode、source_file）のみを宣言する
│   ├── topo_set_extractor.py    # topoSetDict の action_entry ノードから描画可能なジオメトリ（box〈min/max・複数ボックス boxes 形式を含む〉、rotated box、sphere〈origin エイリアスと innerRadius を含む〉、cylinder、cone、点セット〈nearestTo*/insidePoints/nearPoint〉、planeToFaceZone の平面）を抽出。raw_list / マクロ形式のジオメトリ値内の $var と #eval を var_resolver 経由で解決し、TopoSetData(shapes=[TopoShape(...)]) を返す。TopoShape は shapes.SourceShape のサブクラス（追加フィールド: action）。ソースごとのジオメトリ分岐は resolve_source_geometry() / is_non_geometric_source() として公開され、set_fields_extractor.py と共有される
│   ├── set_fields_extractor.py  # setFieldsDict の regions ( … ) リスト（region_block → region_entry ノード。エントリの「名前」がソースタイプ — boxToCell、sphereToCell など — で、`source` 子ノードは持たない）から描画可能な領域ジオメトリを抽出。topo_set_extractor.resolve_source_geometry() を再利用し、各シェイプに fieldValues の要約（例: "alpha.water=1"）をラベル付けして SetFieldsData(shapes=[SetFieldsShape(...)]) を返す。SetFieldsShape は shapes.SourceShape のサブクラス（追加フィールドなし）
│   ├── sampling_extractor.py    # 描画可能なサンプリングジオメトリ — probes の probeLocations（点マーカー）、sets タイプのサンプル線（start/end）、surfaces タイプの plane/cuttingPlane 円盤 — を controlDict の functions {} ブロックまたはスタンドアロンのサンプリング辞書（system/sample・probes・surfaces・singleGraph。.org 系のトップレベル start/end スタイルを含む）から抽出。入れ子のメンバーリストは 2 つの書式とも構造化パーサーノード: 辞書形式 sets {}/surfaces {} と、従来の丸括弧リスト形式 sets ( name {…} )（named_dict_list）。平面解決は tree_utils.resolve_plane_geometry を再利用。SamplingData(shapes=[SamplingShape(...)]) を返す。SamplingShape は shapes.SourceShape のサブクラス（追加フィールド: source_file）
│   ├── snappy_hex_mesh_extractor.py  # snappyHexMeshDict の geometry {} プリミティブ（box、sphere〈ベクトル radius によるだ円体を含む〉、cylinder、cone、constant/triSurface/ から解決される triSurfaceMesh/distributedTriSurfaceMesh〈.gz サイドカーへの透過的な解決を含む〉、box ベースの collection メンバー）を抽出。castellatedMeshControls.refinementSurfaces/refinementRegions（正規表現パターンのサーフェス名を含む）と照合し surface/region/geometry に分類。locationInMesh/locationsInMesh も抽出し、SnappyHexMeshData(shapes=[SnappyShape(...)]) を返す。SnappyShape は shapes.SourceShape のサブクラス（追加フィールド: category/level/mode）
│   ├── include_resolver.py      # Qt 非依存・標準ライブラリのみ: parse_include_directive() が directive_entry の生テキストを IncludeRef（#include/#sinclude/#includeIfPresent/#includeEtc/#includeFunc）に変換し、#codeStream 本体が取り込む C++ ヘッダーを除外する。resolve_include() が ResolvedInclude へ解決し、$VAR と先頭の <case>/<system>/<constant>/<etc> トークンを展開する。etc_dirs は引数として受け取るため foam/ の無依存ルールが保たれる
│   ├── tree_utils.py            # topo_set / snappy_hex_mesh / set_fields の各エクストラクタが共有する汎用 FoamNode ヘルパー: find_child、find_child_any、resolve_scalar、resolve_vector、resolve_point_list、expand_evals、および box/sphere/cylinder/cone の共有ジオメトリリゾルバ（resolve_box_geometry は min/max、`box (min) (max)` ペア、複数ボックス `boxes` の各形式をオプトインフラグで扱う）
│   ├── diff.py                  # diff_trees(a, b) と diff_trees_reverse(b, a) — キー名で 2 つの FoamNode ツリーを比較し dict[FoamNode, DiffEntry] を返す
│   ├── lexer.py                 # OpenFoamLexer。_read_directive は '{' で読み取りを停止するため、#eval{...} の波括弧が LBRACE/RBRACE トークンになり深さ追跡が正しく機能する
│   ├── nodes.py
│   ├── parser.py
│   ├── utils.py
│   ├── value_parse.py           # FoamTreeModel.setData を支える Qt 非依存のテキスト→型付き値の検証。parse_text_for_node_type(node_type, text) は文字列を node_type に対して再パース（int は浮動小数点風の文字列で scalar に昇格、vector/int_list/scalar_list は parse_parenthesized_numbers 経由、box_pair は foam/utils.parse_box_pair 経由、bool は単語一致、文字列系タイプはそのまま通過）。set_node_value(node, value) が全体の契約 — node.value/node_type/modified をその場で書き換え、編集が受理されたかを返す。model/tree_model.py の setData はこの戻り値をそのまま使って dataChanged と edit_rejected を切り替える
│   └── writer.py
├── model/
│   ├── boundary_model.py   # BoundaryModel（QAbstractTableModel）+ extract_boundary()
│   ├── file_list_model.py  # FileListModel（QAbstractListModel）
│   └── tree_model.py       # FoamTreeModel（QAbstractItemModel）。setData の Value 列検証は foam/value_parse.set_node_value に委譲し、node_type/テキスト解析を Qt 非依存に保つ
├── schemas/
│   ├── __init__.py
│   ├── _base.py
│   ├── builtin.py
│   ├── config_store.py
│   ├── block_mesh_dict.py
│   ├── control_dict.py
│   ├── fv_schemes.py
│   ├── fv_solution.py
│   ├── _turbulence_coeffs.py    # foamlore から取り込んだ生成ファイル: 全 29 モデルの係数ファクトと build_schemas(target_file)
│   ├── momentum_transport.py    # foamlore から取り込んだ生成ファイル: 薄いモジュール、TARGET_FILE = constant/momentumTransport（Foundation v8-v13）
│   ├── snappy_hex_mesh_dict/    # パッケージ: サブドメイン別に分割（geometry, castellated mesh, snap, layers, mesh quality）
│   │   ├── __init__.py          # 各サブモジュールの SCHEMAS を統合し、TARGET_FILE を再エクスポート
│   │   ├── _common.py           # 共有 SWITCH_CHOICES
│   │   ├── _structure.py        # 4 つの制御辞書とその中のサブ辞書
│   │   ├── _geometry.py
│   │   ├── _castellated_mesh.py
│   │   ├── _snap_controls.py
│   │   ├── _add_layers.py
│   │   └── _mesh_quality.py
│   ├── turbulence_properties.py # foamlore から取り込んだ生成ファイル: 薄いモジュール、TARGET_FILE = constant/turbulenceProperties（OpenCFD v2106-v2606、Foundation v7）
│   ├── turbulence_structure.py  # 手書き: simulationType、RAS/LES、model セレクタ、LES delta — TARGET_FILES で両方のファイル名に対応
│   └── registry.py
├── services/
│   ├── case_copier.py
│   ├── case_files_config.py
│   ├── case_loader.py       # detect_poly_mesh() も含む -- constant/polyMesh/owner の FoamFile note フィールドから PolyMeshInfo(n_points, n_cells, n_faces, stale) を生成
│   ├── include_scan.py      # インクルード対応のディスク側: foam_etc_dirs() が OpenFOAM の etc 検索パスを構築し、scan_includes()/included_files() が list_case_files の返したファイルに foam/include_resolver を適用する（パースではなく安価な正規表現の行スキャン。mtime+size でメモ化、1 段階のみで再帰しない）。copy_destination_for() は「ケースにコピー」の配置先を決める
│   ├── example_search.py    # discover_installations()/search_examples(): OpenFOAM インストールを検出（app_config/foam_env による環境変数読み取り → 既知のパス）し、その tutorials/ + etc/caseDicts/ をキーワード走査して SearchHit（一致行、囲むチュートリアルケースのルート）を返す
│   ├── log_summary/         # パッケージ: parse_log()/format_summary() が blockMesh/snappyHexMesh/topoSet およびソルバーの実行ログ（log.* の標準出力。FoamNode 辞書ツリーではない。ソルバーは名前ではなくタイムループの形で検出）を短い LogSummary レポートに要約
│   │   ├── __init__.py          # LogSummary/LogWarning/PhaseSummary を再エクスポート。parse_log() はユーティリティ名/形状で分岐し、format_summary() がレポートを整形
│   │   ├── _types.py            # LogSummary/LogWarning/PhaseSummary データクラス + すべての文法が共有するヘッダー・FOAM Warning/FATAL ERROR の汎用パース
│   │   ├── _block_mesh.py       # blockMesh 文法: Mesh Information ブロック
│   │   ├── _snappy_hex_mesh.py  # snappyHexMesh 文法: "Wrote mesh in" マーカーで区切られる castellation/snapping/レイヤー追加フェーズ
│   │   ├── _topo_set.py         # topoSet 文法: セットごとのソース/サイズの集約
│   │   ├── _solver.py           # ソルバー文法: タイムループのステップ・残差・Courant 数・実行時間
│   │   └── _generic.py          # フォールバック文法: 未認識ログの末尾表示
│   └── tool_options.py      # Tools メニュー「Run *」オプションダイアログ用の ToolSpec/ToolOption 仕様（TOOL_SPECS）+ build_args()/build_command()。常に log.<ツール名> へ tee する
├── i18n/
│   ├── __init__.py             # tr()、set_language()、get_language()、available_languages()
│   └── ja.py                   # 日本語翻訳（LANGUAGE_NAME + TRANSLATIONS 辞書）
├── ui/
│   ├── app_state.py            # AppState データクラス: 共有可変フィールドすべて（`current_case_dir`、`current_file`、`current_root`、`current_model`、`file_buffers`、`file_dirty`、`text_dirty`、`source_lines_valid`、`syncing`、`case_files_config`、`parsed_roots`、`diff`、`foam_monitor`、`run_tool_options`、`undo`、`bm_side_by_side`）。`diff` は `DiffState` サブデータクラス（`case_dir`、`parsed_roots`）。`foam_monitor` は `FoamMonitorState` サブデータクラス（`proc`、`script_tmp`、`last_file`、`last_options`）。`undo` は `UndoState` サブデータクラス（ファイルごとの `UndoSnapshot` スタックと `op_active`/`restoring` ガード）。`MainWindow.__init__` が `self.state = AppState()` を生成し、すべての Mixin が `self.state.<field>` として共有状態にアクセス
│   ├── theme.py               # テーマモード（system/light/dark）、Qt がデスクトップから継承する Highlight/HighlightedText の組を修復する readable_selection_pair() のコントラスト規則、および colors() 経由で解決されるすべての UI 意味色を保持する ThemeColors テーブル
│   ├── window_state.py         # WindowState / BlockMeshViewState データクラスと capture_window_state() / apply_window_state()。レイアウトのうち「結果」ではなく「選択」である部分（ジオメトリ、スプリッタ、タブ、開いているファイル、ツリー選択、3-D のトグルとカメラ）を扱う。JSON 化できるため、状態をプロセス間で受け渡せる。strict / lenient の使い分け（from_dict と apply_window_state の `strict` フラグ、load_saved_state）は、2 つの利用側の要求が逆であることに由来する: スクリーンショット spec は失敗を大きく報せるべきで、復元されるセッションは静かに劣化すべき
│   ├── session_restore.py      # window_state.py の上に載る「実行間の配線」。save_session() は MainWindow.closeEvent から（パネル破棄前、自動保存はしない）、restore_session() は main.py の show() 後から呼ばれる。レイアウトは AppConfigManager.session_key() ごとに保存し、ケース読み込み時の描画が reset_camera() で終わるため 3-D カメラはタイマーで再適用、スキップした部分はステータスバーに表示
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
│   │   ├── _ui_ops.py              # Mixin: ラベル更新、スキーママネージャ、ヘルプダイアログ、言語メニュー、ツリー列の表示切替
│   │   └── _protocol.py            # mypy 専用の MainWindowProtocol。各 mixin の TYPE_CHECKING 用基底クラスがこれを指すことで `self.tree`/`self.state`/mixin 間呼び出しが型チェックされる。詳細は下記「ui/mixins/ 分割の型付け」を参照
│   ├── layout_constants.py
│   ├── dialogs/
│   │   ├── about_dialog.py
│   │   ├── add_files_dialog.py
│   │   ├── boundary_edit_dialog.py
│   │   ├── _case_dest_dialog.py  # _CaseDestDialogBase（QDialog）: DuplicateCaseDialog と SaveAsNewCaseDialog が共有するソース/宛先（親+名前）/プレビュー/コピーモード UI の基底クラス。サブクラスは自身のコピーモードラジオグループを構築し _finish_layout を呼ぶ
│   │   ├── case_library_dialog.py
│   │   ├── clean_backups_dialog.py
│   │   ├── duplicate_case_dialog.py  # DuplicateCaseDialog（_CaseDestDialogBase）: 名前サフィックスは "_copy"、デフォルトで「Copy all files」が選択済み
│   │   ├── export_stl_dialog.py  # ExportStlDialog: 読み込み済みの topoSetDict/snappyHexMeshDict シェイプをチェックリスト表示するモーダルダイアログ。チェックした各シェイプを BlockMeshRenderer._make_shape_mesh 経由でそれぞれ個別の .stl として書き出す
│   │   ├── find_examples_dialog.py  # FindExamplesDialog: 非モーダルのキーワード検索。インストールの tutorials/ + etc/caseDicts/ を対象（services/example_search.py をバックグラウンド QThread、_SearchThread(_worker_thread._CancellableWorkerThread) で実行)、シンタックスハイライト付きプレビュー、コピー、「このケースと比較」（compare_requested を発行）、「このケースを複製…」（duplicate_requested を発行）。インストール選択は共有ウィジェット widgets/installation_selector.InstallationSelector
│   │   ├── foam_monitor_dialog.py  # FoamMonitorDialog: ファイル選択 + foamMonitor オプション（対数スケール、グリッド、リフレッシュ間隔、アイドルタイムアウト、追加フラグ）
│   │   ├── generate_keywords_dialog.py  # GenerateKeywordsDialog: app_config/keyword_generator.py をバックグラウンド QThread（_GeneratorThread(_worker_thread._CancellableWorkerThread)）で実行し進捗ログを表示。インストール選択は共有ウィジェット widgets/installation_selector.InstallationSelector（FindExamplesDialog と同じ検出 + 永続化 openfoam_dir キー）
│   │   ├── keyboard_shortcuts_dialog.py
│   │   ├── log_summary_dialog.py  # LogSummaryDialog: 非モーダル（find_examples_dialog と同様。他のモーダルダイアログとは異なる）のファイル選択 + Summary/Raw Log タブ、services/log_summary/ を利用
│   │   ├── manage_extra_files_dialog.py
│   │   ├── openfoam_resources_dialog.py
│   │   ├── rename_boundary_dialog.py  # Rename Boundary ダイアログ + find_rename_targets() スキャナ
│   │   ├── reset_settings_dialog.py
│   │   ├── run_tool_dialog.py  # RunToolDialog: services/tool_options.TOOL_SPECS から構築される Tools メニュー「Run *」の汎用オプションダイアログ — 主要フラグのウィジェット、自由記述の追加オプション、ライブコマンドプレビュー、任意のプレフライト警告とシェルプレフィックスチェックボックス
│   │   ├── save_as_new_case_dialog.py  # SaveAsNewCaseDialog（_CaseDestDialogBase）: 名前サフィックスは "_new"、デフォルトで「Copy app-visible files only」が選択済み、未保存の編集についての斜体注記ラベルを追加
│   │   ├── schema_manager_dialog.py
│   │   └── _worker_thread.py  # _CancellableWorkerThread（QThread）: find_examples_dialog の _SearchThread と generate_keywords_dialog の _GeneratorThread が共有する progress/finished_err シグナルと cancel() フラグ。各サブクラスは自身の finished_ok シグナルと run() を追加する
│   ├── panels/
│   │   ├── block_mesh_panel.py     # blockMeshDict 用 3D ビューア（pyVista/VTK、遅延初期化）。topoSetDict（topoSet ▾ メニュー）、snappyHexMeshDict（snappyHexMesh ▾ メニュー）、setFieldsDict の領域（setFields ▾ メニュー）、サンプリング定義（sample ▾ メニュー。controlDict の functions {} とスタンドアロンの system/sample 系辞書の合算を _sampling_by_file に元ファイル名ごとに保持）のジオメトリもそれぞれシェイプ単位の表示切替・Show all/Hide all アクション・描画不能エントリ用の「Non-geometric sources (N)」サブメニュー付きで重ねて表示する。アクター構築は block_mesh_renderer.BlockMeshRenderer に委譲。STL ▾ メニューには読み込み済み STL/OBJ サーフェス用の同じファイル別の行（block_mesh_renderer.LoadedSurface。1 ファイル 1 色、Unload サブメニュー付き）があり、「Export Shapes as STL…」は dialogs/export_stl_dialog.ExportStlDialog を開く
│   │   ├── block_mesh_renderer.py  # BlockMeshRenderer: RenderSettings データクラス経由の blockMeshDict/topoSetDict/snappyHexMeshDict/setFieldsDict ジオメトリ用 VTK レンダリングパイプライン。_make_shape_mesh はジオメトリ辞書のキー（box、boxes、centre+radius〈リスト radius によるだ円体と innerRadius による中空球を含む〉、p1+p2+radius、origin+i+j+k、stl_path、planePoint+planeNormal〈plane_size で寸法指定される円板〉。points は None を返しマーカーとして別途描画）で分岐し全オーバーレイソースで共有される。オーバーレイシェイプは _clip_to_bounds により、ブロックメッシュの AABB を各軸 10% 拡大した範囲へ（表示上のみ）クリップされる — ラベルには「(clipped)」/「(outside block mesh)」マークが付き（ASCII のみ: VTK のラベルフォントは絵文字記号のグリフをまったく描画しない）、シーンを包み込むシェイプは AABB の重なりボックスにフォールバックし、STL エクスポートはクリップされない。_render_boundary_faces は BlockMeshData.default_faces も薄い "empty" グレーで描画する。pyvista のガードを通過した後にのみインポートされる
│   │   ├── boundary_view_panel.py
│   │   ├── comparison_tree_panel.py  # 読み取り専用の参照ケースツリー。use_value_requested(FoamNode) シグナルを発行
│   │   ├── detail_panel.py
│   │   ├── editor_panel.py
│   │   ├── file_list_panel.py
│   │   └── terminal_panel.py       # TerminalPanel ラッパー: mode_changed シグナル、xterm/simple 切替ロジック
│   └── widgets/
│       ├── code_editor.py
│       ├── _checkable_list.py          # checked_items()/set_all_check_states(): clean_backups_dialog.py と manage_extra_files_dialog.py が使うチェック可能 QListWidget パターン向けの共有 Select All/Deselect All + 「N selected」ヘルパー
│       ├── flow_layout.py              # FlowLayout（QLayout）: 折り返し式ツールバーレイアウト — 最小幅は最も幅の広い 1 項目分。BlockMesh パネルのツールバーで使用
│       ├── installation_selector.py    # InstallationSelector（QWidget）: services/example_search.discover_installations() と永続化 openfoam_dir キーに基づくコンボ + Browse… 行。installations_available/error シグナル。find_examples_dialog と generate_keywords_dialog で共用
│       ├── _foam_highlighter.py        # FoamHighlighter（QSyntaxHighlighter）: OpenFOAM トークンの色付け。app_config/foam_keywords.json（ユーザー生成）、無ければ app_config/foam_keywords.default.json（同梱ベースライン）を 1,000 キーワード単位の QRegularExpression チャンクで読み込む。数値ルール（_NUMBER_RE）とすべてのキーワードルールは前後判定（lookaround）で守られており、識別子に付いた数字（"wall0"）やドット付き名前のキーワード接頭辞（"y0.1" の "y0"）が部分的に色付けされることはない
│       ├── _simple_terminal_widget.py  # SimpleTerminalWidget: QProcess ベースターミナル（WebEngine 不要）
│       └── _xterm_widget.py            # PtyBackend、TerminalBridge、XtermTerminalWidget（Unix + QtWebEngine 専用）。_XTERM_AVAILABLE をエクスポート
└── tests/
    ├── conftest.py
    ├── test_lint.py             # pytest スイートの一部として ruff + mypy（どちらもリポジトリ全体）を実行
    ├── test_version.py          # _version.get_version(): git describe の整形（タグ一致、タグより先行、dirty、ハッシュのみ、git 無しフォールバック）
    ├── test_i18n.py             # i18n/ja.py の TRANSLATIONS に重複キーがないこと（dict リテラルは最後のものだけを黙って残すため、AST で走査して検査）
    ├── foam/
    │   ├── test_block_mesh_extractor.py
    │   ├── test_diff.py
    │   ├── test_lexer.py
    │   ├── test_parser_block_mesh_dict.py
    │   ├── test_parser_control_dict.py
    │   ├── test_parser_fv_schemes.py
    │   ├── test_parser_fv_solution.py
    │   ├── test_parser_block_list.py
    │   ├── test_parser_named_dict_list.py
    │   ├── test_parser_region_properties.py
    │   ├── test_parser_set_fields_dict.py
    │   ├── test_parser_topo_set_dict.py
    │   ├── test_include_resolver.py
    │   ├── test_sampling_extractor.py
    │   ├── test_set_fields_extractor.py
    │   ├── test_snappy_hex_mesh_extractor.py
    │   ├── test_sampling_shapes_tutorial.py
    │   ├── test_source_lines.py
    │   ├── test_topo_set_extractor.py
    │   ├── test_topo_set_shapes_tutorial.py
    │   ├── test_tree_utils.py
    │   ├── test_utils.py
    │   ├── test_value_parse.py
    │   ├── test_var_resolver.py
    │   └── test_writer_roundtrip.py
    ├── model/
    │   ├── test_bool_nonuniform.py
    │   ├── test_boundary_model.py
    │   ├── test_file_list_model.py
    │   └── test_tree_model.py
    ├── ui/
    │   ├── test_app_state.py
    │   ├── test_apply_comparison_value.py
    │   ├── test_block_mesh_panel_load_stl.py
    │   ├── test_block_mesh_panel_sampling_select.py
    │   ├── test_block_mesh_panel_set_fields_select.py
    │   ├── test_block_mesh_panel_snappy_select.py
    │   ├── test_block_mesh_panel_topo_select.py
    │   ├── test_block_mesh_renderer_topo.py
    │   ├── test_block_mesh_selected_block.py
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
    │   ├── test_included_files.py
    │   ├── test_log_summary_dialog.py
    │   ├── test_main_window_save_refresh.py
    │   ├── test_main_window_split.py
    │   ├── test_manage_extra_files_dialog.py
    │   ├── test_rename_boundary.py
    │   ├── test_reset_all_settings.py
    │   ├── test_run_tool_dialog.py
    │   ├── test_stays_open_menu.py
    │   ├── test_terminal_panel.py
    │   ├── test_theme.py
    │   ├── test_tools_ops_mesh_actions.py
    │   ├── test_tree_block_crud.py
    │   ├── test_tree_color_lexer_dispatch.py
    │   ├── test_tree_copy_paste.py
    │   ├── test_tree_inline_edit_dirty.py
    │   ├── test_tree_undo_redo.py
    │   ├── test_update_viewer_panels.py
    │   ├── test_view_log_summary_action.py
    │   ├── test_session_restore.py
    │   └── test_window_state.py
    ├── services/
    │   ├── test_backup.py
    │   ├── test_case_copier.py
    │   ├── test_case_files_config.py
    │   ├── test_include_scan.py
    │   ├── test_case_loader.py
    │   ├── test_example_search.py
    │   ├── test_log_summary.py
    │   └── test_tool_options.py
    ├── app_config/
    │   ├── test_app_config.py
    │   ├── test_foam_env.py
    │   ├── test_json_io.py
    │   └── test_keyword_generator.py
    ├── schemas/
    │   ├── test_schemas.py
    │   ├── test_schema_coverage.py
    │   └── test_turbulence_schemas.py
    └── tools/
        ├── test_capture_dialog.py
        └── test_demo_specs.py
```

### ドキュメントマップ

| ファイル | 役割 |
|---|---|
| `README.md` | 短い導入: インストール、クイックスタート、ユーザーガイドへディープリンクする要約版の機能一覧。 |
| `USER_GUIDE.md` | 全機能リファレンス。**ユーザーに見える機能を追加したら、「目的別ガイド」テーブルと目次にも必ず追加すること** — これらのナビゲーションは放っておくと静かに実態とずれていきます。 |
| `DEVELOPER.md` | このファイル: プロジェクト構成、内部構造、開発環境のセットアップ、テスト。 |
| `RELEASE_NOTES.md` | ユーザー向け変更履歴。新しい項目は `## Unreleased` の下に蓄積し、リリース時に見出しをバージョン番号へ変更します。 |
| `docs/SCREENSHOTS.md` | メインウィンドウ・BlockMesh 3D オーバーレイ・主要ダイアログ/メニューの注釈付きスクリーンショットギャラリー。 |
| `docs/DEMO_SCRIPTS.md` | デモ動画のショットごとの台本と収録方法。いずれも `tools/demo_specs.json` の実行可能なシーンなので、台本と実際の収録結果が食い違うことはない。 |

各英語ドキュメントには日本語版（`*_ja.md`）があり、一方を編集したら必ずもう一方にも反映します。日本語ドキュメントではメニューラベルなどの UI 文字列は英語のまま表記します。

### テストカバレッジ一覧

ディレクトリごとにテストファイル 1 行の一覧です。テストファイルの追加・削除時はここも更新してください — 以前サイレントにドリフトしたのはまさにこの部分です。

**`tests/foam/`**
- `test_block_mesh_extractor.py` — `extract_block_mesh_data` の出力: 境界面の抽出（パッチの間に置かれた `#include` によって `outlet` が名前と面を失っていたリグレッションを含む）、`#include` を含む `blocks` リストおよび先読みが `raw_list` に落としたリストからの hex 抽出、`default_faces`（境界が全面を占有 → 空、未割り当ての外部面の収集、任意の頂点回転での占有判定、ブロック間で共有される内部面の除外）、`parse_vertices` の公開 API（正常系と三つ組でない要素の許容）、インラインコメントおよびパッチコメントを伴う頂点/ブロック抽出、変数解決（`$varName`、`${varName}`、マクロ、`-$xMax` のような否定マクロ word ノード、`#eval{ expr }`、多段チェーン）、コンパクト `(blockIndex, faceIndex)` 境界面記法（否定マクロ頂点変数との組み合わせを含む）。
- `test_diff.py` — `diff_trees`/`diff_trees_reverse`: 同一ツリー、値の変更、片方のみに存在するキー、ネストした辞書、匿名ノードのスキップ、`field_value_block` エントリ、両関数の対称性。
- `test_lexer.py` — `foam.lexer.OpenFoamLexer` の `//` 挙動: 引用符付き文字列内の二重スラッシュはコメントにならないこと、空白の後の二重スラッシュは直前の word を飲み込まずに `LINE_COMMENT` を開始すること、単独行の `//` は先頭トークンからコメントとして扱われること。加えて `${…}` 形式の波括弧付きマクロ参照: 参照全体が 1 つの WORD になること（スコープパス付き、および入れ子の波括弧が釣り合うこと）、その後続トークンが影響を受けないこと、素の `$macro` と単独の `{` が従来どおりであること、閉じられていない `${` がループせずテキスト末尾まで進むこと、`#eval{…}` が従来どおり DIRECTIVE + LBRACE + 本体 + RBRACE に分割されること（`#eval` のパースがこれに依存している）。
- `test_parser_block_mesh_dict.py` — `boundary_block`/`boundary_entry` の構造的パース（パッチ数・名前・型・面）、ライタの round-trip。パッチ名と波括弧の間、および `vertices` 内のインライン `//`・`/* */` コメントがノード型を壊さないこと。パッチの間に置かれた `#include` がブロック全体を失敗させずに `directive_entry` の子ノードになること（パースエラーなし、パッチ名が保持される、round-trip がバイト単位で一致）。埋め込み括弧値内のインラインコメントを読み飛ばす `_read_parenthesized_text`。
- `test_parser_control_dict.py` — `controlDict` のパース: FoamFile ヘッダー、int/scalar/word の値、`#directives`、`functions` サブ辞書、パース失敗時に空の root へフォールバックすること。
- `test_parser_fv_schemes.py` — `fvSchemes` のパース: compound 値、`ddtSchemes`/`divSchemes`/`interpolationSchemes`/`snGradSchemes` ブロック、すべてのトップレベルブロックの存在、round-trip 書き込み、辞書を閉じる余分な `;`（`divSchemes { … };`）が解析エラーとして数えられずに独立したノードになること。
- `test_parser_fv_solution.py` — `fvSolution` のパース: マクロおよび正規表現パターンのソルバーキー、`PIMPLE` ブロック、ソルバーの `tolerance`/`smoother` エントリ、round-trip 書き込み。
- `test_parser_block_list.py` — `blockMeshDict` の `blocks ( … );` の展開: `hex` のみのリストが匿名・1 行の `block_list`/`block_entry` として解析されること、先読みにより空リスト・単純なマクロ単語リスト・ディレクティブのみのリスト・`hex` 以外の先頭形状（`hex2D`、`prism`）が通常の `raw_list` パスに留まること、hex ブロックと*併存*する `#include` は逆に `directive_entry` の子ノードを伴って展開され（リスト先頭でも途中でも）バイト単位で一致してラウンドトリップすること、各種の記法がそれぞれ 1 エントリとして解析されること（ゾーン名 + `grading`、`$blockInfo` のみの末尾、12 要素の `edgeGrading`、3 行にまたがるブロック、blockMesh の `name <blockName> hex …` プレフィックス。単独の `name` 単語ではエントリが分割されないことも確認）、コメントの配置（インライン / 次エントリの `leading_trivia`）、未変更時のラウンドトリップがバイト単位で一致すること、エントリ変更時に兄弟エントリが原文のまま出力されること。
- `test_parser_named_dict_list.py` — 省略可能な名前付き辞書リスト構文: `sets`/`surfaces` の名前付き辞書の丸括弧リストが `named_dict_list`/`named_dict_entry` として解析されること（トップレベルとファンクションオブジェクト辞書内の入れ子の両方）、先読みにより単純な単語/文字列リスト（`sets (setA setB);`）や空リストが通常の値パスに留まること、未変更時のラウンドトリップがバイト単位で一致すること、エントリ変更時に兄弟エントリの名前が保持されること。
- `test_parser_region_properties.py` — 無関係な 2 つの辞書が同じ `regions` というキーを使っている問題: `setFieldsDict` の名前付き辞書はこれまでどおり `region_block`/`region_entry` として解析され、`constant/regionProperties` の 名前と単語リストの組は、以前のような名前のない `unknown_raw_entry` ノード 2 つ ではなく `raw_list` に落ちること。いずれも解析エラーがなく、バイト単位の ラウンドトリップが一致することを確認します。同梱チュートリアルの両ファイルを 直接検証し、単純な `regions ( a b c );` と空リストも対象にしています。さらに、同じ内容を別のキーの下に置いたときとまったく同じ解析結果になることを検証する テストで、この修正が取り戻した原則を固定しています。
- `test_parser_set_fields_dict.py` — `setFieldsDict` のパース: `defaultFieldValues`/`regions` のフィールド値エントリ（ベクトル値を含む）、`box_pair` のパース、編集後の round-trip 書き込み。
- `test_parser_topo_set_dict.py` — `action_list`/`action_entry` の構造的パース: ノード型、エントリ数、名前付き子ノードの値、`box_pair` 座標、ソースなしエントリ、round-trip 書き込み、`_diff_action_list` による位置ベースの差分検出。
- `test_snappy_hex_mesh_extractor.py` — `extract_snappy_hex_mesh_data`: `geometry` の box/sphere（スカラーおよびベクトル/だ円体 radius）/cylinder/cone の抽出、`name` による上書き解決（`geom.stl { name geom; }`）、`triSurfaceMesh`/`distributedTriSurfaceMesh` の `constant/triSurface/` に対するファイル解決（明示的な `file` 子ノード、キー名からの暗黙のファイル名、ファイル不在時の扱い）— `.gz` への透過的な解決を含む（プレーン名のエントリがディスク上に `.gz` のみ存在するファイルへ解決されるケース、`.gz` 付きのエントリキー／ファイルがそのまま解決されるケース、`.gz` 付きの参照がディスク上の非圧縮ファイルへフォールバックするケース）、`collection`（searchableSurfaceCollection）の box メンバーを `rotation none` および `e1`/`e3` 軸で解決（実際に回転するケースを含む）し、box 以外のベースや未指定・未対応の `transform` はスキップされること、`refinementSurfaces`/`refinementRegions` の完全一致および正規表現パターンキー（例：`"iglo.*"`）による照合、`locationInMesh`（単数）と `locationsInMesh`（複数）の点抽出、`$var`/`#eval{}` の解決。
- `test_source_lines.py` — すべてのノード型に対する `source_line` および `source_end_line` の設定。
- `test_topo_set_extractor.py` — `extract_topo_set_data`: box・sphere・cylinder の 3 種類すべてに対するプレーンな型付き値、ベクトルとスカラーでの `$var` 解決、`raw_list` 内の `#eval{...}`、連鎖した変数/eval 解決、解決不能な変数のスキップ、すべての face/point ソースバリアント。
- `test_include_resolver.py` — `parse_include_directive`/`resolve_include`: 5 つのディレクティブ種別、オプション扱い（`#sinclude`/`#includeIfPresent`）の判定、末尾 `;`・コメント・引用符の除去、`#includeFunc mag(U)` のベース名への還元、拡張子とトークン全体の山括弧による C++ ヘッダー除外（`<constant>/…` は意図的に残ること）、`<case>`/`<system>`/`<constant>`/`<etc>` と `$VAR` の展開、取り込み元ディレクトリをケースより先に見る順序、`.gz` 兄弟ファイル、`#includeEtc` のルート探索順、`#includeFunc` が `system/` を優先すること、4 つの status それぞれ。
- `test_sampling_extractor.py` — `extract_sampling_data`: `functions {}` ブロック内の probes、辞書形式 `sets {}` の line/cloud メンバーと、丸括弧リスト形式（`functions {}` ブロック内とファイルルートの sampleDict スタイルの両方）、`plane`/`cuttingPlane`/`patch` サーフェスメンバー、トップレベルの `singleGraph` スタイル `start`/`end`、スタンドアロンの `sample`/`probes` ファイル、`$var` の解決、サンプリング以外のファンクションオブジェクトの無視。
- `test_set_fields_extractor.py` — `extract_set_fields_data`: box/sphere/cylinder 領域の抽出（エントリ名がソースタイプ）、`fieldValues` のラベル要約（スカラー値とベクトル値）、ジオメトリを持たないソースの分類（`zoneToCell`）、`$var` の解決、解決不能なジオメトリックソースのケース。
- `test_topo_set_shapes_tutorial.py` — 同梱の `tutorials/topoSetShapes` ケースに対する `extract_topo_set_data`: すべてのジオメトリソースが抽出され、すべての形状がドメイン内に収まっていること。
- `test_sampling_shapes_tutorial.py` — `tutorials/samplingShapes` と `extract_sampling_data` について同じことを行うテスト: `controlDict` の `functions {}` ブロックから読み取る probes と、その隣に置いたサンプリングでない function object が完全に無視されること、メンバーリストの 2 通りの記法（`sets { … }` と `surfaces ( … );`）、始点・終点ではなく点列を持つ cloud、平面の 2 通りの記法、非ジオメトリとして一覧される `patch` サーフェス、そして名前付きの点がすべてドメイン内にあること。加えて、網羅性チェックでは見落とす点も検証します: 各シェイプのバッジをギャラリーのカメラで投影し、互いに離れていることを確認します。ケース内でシェイプを動かすと別のシェイプのバッジがその背後に隠れてしまうためで、実際にこのケースの作成中は 6 つのうち 2 つが見えなくなっていました。
- `test_tree_utils.py` — `tree_utils` の各リゾルバの直接契約テスト（エクストラクタのテストは間接的にしか通らない）: `find_child`/`find_child_any` のエイリアス優先順、`expand_evals`、`resolve_scalar`（scalar/int/macro/`${…}`/`#eval`）、`resolve_vector` の要素数・数値ガード、`resolve_point_list`、オプトインフラグ付きの sphere/cylinder/cone リゾルバ、`resolve_box_geometry`（min/max・`box` ペア・複数 `boxes` の優先順とフラグによる有効化）。
- `test_utils.py` — `is_large_non_foam_file`: 小さいファイルはヘッダーの有無にかかわらずフラグが立たないこと、最初の 512 バイト内に `FoamFile` トークンを含む大きいファイルはフラグが立たないこと、含まない大きいファイルはフラグが立つこと、存在しないファイルは `(False, 0)` を返すこと、コメントの後にヘッダーがある場合も正しく検出されること。
- `test_value_parse.py` — `parse_parenthesized_numbers`/`parse_text_for_node_type`/`set_node_value` を Qt なしで直接検証: int の受理・拒否と浮動小数点風文字列での scalar への昇格、scalar の受理・拒否、vector/int_list/scalar_list/box_pair の受理・拒否、raw_list の括弧除去、bool の大文字小文字を区別しない受理・拒否、word/string/macro/compound のそのまま通過、サポート対象外の node_type の拒否、および `set_node_value` の field_value/directive_entry/unknown_raw_entry の特殊ケースとインプレース変更の契約（拒否された編集はノードを一切変更しないこと）。
- `test_var_resolver.py` — `build_var_map`、`substitute_vars`、`eval_foam_expr`: スカラー/整数のシード、マクロチェーン、`#eval` 式、否定マクロ word ノード、解決不能な変数が値を持たないままになること、`skip_keys` による除外、辞書ノードが収集対象にならないこと。
- `test_writer_roundtrip.py` — `write_root`/`write_node` 全般: 未変更ノードが `raw_text` で再現されること、変更された word/int/scalar/vector ノードが再生成されること、directive/unknown_raw/macro エントリが保持されること、ネストした辞書、空行の連続がそのまま保持されること、`field_value_block`/`region_block` の round-trip（リージョン内のフィールド値編集を含む）、および 1 つの region エントリの再生成時に未変更の兄弟エントリの名前が失われていたリグレッション（エントリの `raw_text` が名前トークンから始まるようになった）。さらに、実際のチュートリアル `blockMeshDict` を模したフィクスチャ `_CORPUS_SHAPED_DICT` に対するバイト単位一致ラウンドトリップ群: `// * * *` バナーの直後の空行が保たれること、エントリ間の複数空行が残ること、末尾の `// ****` フッタバナーが `root.trailing_trivia` から再出力されること、最終改行がないファイルに改行が付加されないこと、`x1 14; x2 6;` が 1 行に留まること、1 エントリの編集がその行だけを変更すること、トリビアなしで追加されたノードが独立した行になること、`}` の直後の余分な `;` が独立した（インデント付きの）行に送り出されず波括弧と同じ行に留まること、ネストしたノードを型を問わず再生成してもソースのインデントが二重にならず再現されること（dictionary/simple/directive/macro/region/action/field-value/深いネストでパラメータ化）、およびトリビアがインデントを持たない場合はライタが従来どおりインデントを補うこと。さらに `macro_entry` 群として、以前は解析失敗だった 2 つの記法を検証する: 波括弧付きの `${../_bladeForces}` と `;` の無い裸の `$minX` がいずれも `macro_entry` ノードになること、裸のマクロが解析エラーにならず後続エントリに属するトリビアを飲み込まないこと、5 つの記法すべてがバイト単位で一致してラウンドトリップすること、ノード再生成時に `_macro_suffix` が元ソースの終端子を（インラインコメントを伴う場合も含めて）再現すること、アプリが `raw_text` 無しで構築したノードには従来どおり `;` が付くこと。

**`tests/model/`**
- `test_bool_nonuniform.py` — bool/nonuniform_list のパースと round-trip、`FoamTreeModel` の bool 編集（大文字小文字を区別しない、拒否シグナル）、`nonuniform_list` の表示・編集不可、不正エントリに対するパーサエラー収集。
- `test_boundary_model.py` — `extract_boundary()` と `BoundaryModel`: 読み込み、フィールド更新、ディレクトリごとの境界セット、`_is_in_dir` の多階層照合、モデルのクリア。
- `test_file_list_model.py` — `FileListModel`: 読み込み、ソート済みグループ、アイテムごとのダーティ状態・差分状態、追加ファイルの扱い、クリア。
- `test_tree_model.py` — `set_diff(reverse=True)`: `"only_here"` を `"only_in_ref"` にリマップし `"changed"` は変更しないこと、淡緑色の `BackgroundRole` を返すこと、`"only in reference case"` をツールチップに含むこと。`FoamNode` は `__hash__ = object.__hash__` を持ち、差分マップのキーとして使用可能です。ブロック番号: `block N` キーは `directive_entry` の行を飛ばすため、`#include` の直下の最初のブロックも `block 0` と表示されること、およびその番号付けを支えるリストごとのキャッシュが挿入時に破棄されること。

**`tests/ui/`**
- `test_app_state.py` — `ui/app_state.py` の `AppState` の既定値: `diff` が `DiffState` であること、スカラーのフィールドが空で始まること、可変フィールドが書き換え可能であること、そして 2 つのインスタンスが `parsed_roots` を共有しないこと — クラス属性にしてしまうと起きる誤りです。
- `test_apply_comparison_value.py` — `_apply_comparison_value`（「Use this value」）: ネストしたエントリの取り込み時に不足している親辞書を作成すること（例: `functions {}` を持たないケースへの `functions/forces1/rhoInf` の適用）、名前のない `#includeFunc` ディレクティブを既存ブロックを上書きせず内容で照合して末尾に追加すること、同一のディレクティブは複製せずスキップすること、名前付きの値の通常の上書きパス、囲むキーが存在するものの辞書ではない場合に適用を拒否すること。
- `test_block_mesh_panel_load_stl.py` — `STL ▾` メニューの読み込み済みサーフェス: 1 回の `getOpenFileNames` での複数ファイル選択、読み込めないファイルがあっても読める分は読み込まれること（失敗分をまとめた警告 1 回）、ダイアログのキャンセルが何もしないこと。さらにファイル別の行について: ファイルごとに 1 行・パレットから 1 色（最初は `lightgray`）、個別の非表示とアンロードの違い、アンロード後や同一パスの再読み込み後（重複行ではなく既存行の再読み込み）も各行のチェック状態が保たれること、`blockMeshDict` が無い状態で読み込んだサーフェスがレンダラーに届くこと（スタブレンダラー経由。最後の 1 つをアンロードしたときのクリア用レンダリングを含む）。
- `test_block_mesh_panel_sampling_select.py` — `sample ▾` の形状別表示メニュー: controlDict の `functions {}` ブロックからのメニュー生成（行には元ファイル名のタグ付き）、個別/マスタートグル、ジオメトリを持たないエントリのグレーアウト表示、複数ファイルの合算（controlDict + system/sample）とファイル単位の再読み込み置換、ベース名が同じ 2 つの辞書が別ディレクトリにあっても分離されること（`_sampling_by_file` はフルパスをキーとし、表示はベース名）、`clear()` による `_sampling_by_file` のリセット。
- `test_block_mesh_panel_set_fields_select.py` — `setFields ▾` の形状別表示メニュー: 同梱の damBreak チュートリアルの `setFieldsDict` からのメニュー生成（行は `fieldValues` の要約でラベル付け）、個別/マスタートグル、ジオメトリを持たないソースのグレーアウト表示、STL エクスポートへの包含、再読み込み時のクリア。
- `test_block_mesh_panel_snappy_select.py` — `snappyHexMesh ▾` の形状別表示メニュー: メニューの生成、個別/マスタートグル、surface/region/geometry カテゴリカラーの凡例、ジオメトリを持たないソースのグレーアウト表示、`locationInMesh`/`locationsInMesh` キープポイントのトグル。
- `test_block_mesh_panel_topo_select.py` — `topoSet ▾` の形状別表示メニュー: メニューの生成、個別/マスタートグル、Show all/Hide all、アクションカラーの凡例、ジオメトリを持たないソースをまとめた「Non-geometric sources (N)」サブメニュー、点/平面シェイプの STL エクスポートからの除外。
- `test_block_mesh_renderer_topo.py` — `_make_shape_mesh` によるジオメトリ生成: 真のコーンとフラスタム（円錐台）、中空の円環、`rotatedBoxToCell`、球（スカラー radius およびベクトル radius によるだ円体）、`stl_path` によるメッシュ読み込み（ファイルあり／なし、および `read_surface_mesh` 経由の gzip 圧縮された `.stl.gz` ファイル）。`read_surface_mesh` のプレーンファイルのパススルー。オーバーレイクリップヘルパー（`_expanded_bounds` の軸ごとのパディング〈退化した 2D 軸を含む〉、`_clip_to_bounds` の範囲内／クリップ／完全に外側／包含時のスタンドインの各ケース、およびクリップが切断面をふさぐこと — 両端を切られたボックスと円柱がどちらも開いた辺を持たずに返り、ボックスの側面が三角形の対ではなく四角形のまま保たれ、平面はふた付きの経路を辞退してフォールバックすること）。VTK が描画するシーンテキスト（`_mark_label` の接尾辞付与、および `block_mesh_renderer.py` の docstring 以外のすべての文字列リテラルが ASCII であることを AST 走査で検査 — このフォントは以前のクリップマーク `✂`/`⚠` と範囲表示の `→` を何も描画しなかったため）。
- `test_block_mesh_selected_block.py` — ツリー → 3D のブロックハイライト: 初期状態ではどのブロックもハイライトされないこと、`set_selected_block` が `RenderSettings.selected_block` に届くこと、解除、別メッシュ読み込みでの破棄。`_highlight_selected_block` が `block_entry` 行の番号を転送し、それ以外の行では解除すること。`_render_selected_block` が `None` や範囲外の番号では何も描画しないこと（`None` のプロッタを渡して検証。`add_mesh` が呼ばれれば例外になる）。
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
- `test_included_files.py` — `MainWindow` における `#include` 対応のエンドツーエンド。`tmp_path` 上に偽の OpenFOAM `etc` ツリーを作るため実インストールに依存しない: ケース外のインクルードが `<included>` グループに入り、ケース内のものは本来のグループに入ること、既に一覧にある対象にマークが付かないこと、読み取り専用の契約（エディタ、`flags()`、`_mark_dirty`、`save_file`、`save_all_files`、バックアップ、`apply_text_to_tree`、次のファイルでのフラグ解除）、ケース内外双方に対する **Open Included File** と missing/optional/非インクルードの各ケース、ツールチップの注記、既存名と `../` による脱出の拒否を含む **Copy into case…**。
- `test_foam_highlighter.py` — `FoamHighlighter`: コメント、文字列、`#directives`、`$macro` 参照、予約キーワード、数値（`wall0`/`inlet-1` のような識別子内の数字を色付けしない lookaround ガードを含む）、同じガードを共有するキーワードルール（`y0.1` や `off.1`、シェルの `config.fi` のようなドット付き識別子が分割されない）、スキーマレジストリとキーワード JSON（ユーザーの `foam_keywords.json` 優先、同梱の `foam_keywords.default.json` にフォールバック、両方無ければ空集合）から得られる辞書キーの色付け、1,000 キーワード単位の `QRegularExpression` チャンク分割、有効/無効の切り替え。
- `test_log_summary_dialog.py` — `LogSummaryDialog`: 非モーダルなウィンドウモダリティ、ケースディレクトリ内で最も新しく更新された `log.*` ファイルをデフォルト選択してその要約を表示すること、ファイルフィールド変更時の再パース、空のケースディレクトリでのフォールバックメッセージ。
- `test_main_window_save_refresh.py` — `test_main_window_split.py` の構造チェックのみとは異なる、初めての振る舞いレベルの `MainWindow` テスト: 保存せずに編集しても `constant/polyMesh` メッシュインジケーターが変化しないこと、`save_file()`/`save_all_files()` のどちらも即座にファイル一覧を更新して、フル「Reload Case」なしで staleness インジケーターが更新されること。
- `test_main_window_split.py` — Mixin 構造: 各 Mixin が正しいメソッドを保有すること（`_BoundaryOpsMixin` の `_on_patch_selected`、`_TreeCrudOpsMixin` の `_apply_comparison_value`、`_FoamMonitorOpsMixin` の foamMonitor 関連メソッドを含む）、Mixin 間の重複がないこと、`MainWindow` がすべての Mixin を継承していること。
- `test_manage_extra_files_dialog.py` — `ManageExtraFilesDialog`: 登録済みの追加ファイル・ディレクトリの表示と削除操作。
- `test_rename_boundary.py` — `find_rename_targets()`: `blockMeshDict` 内の `boundary_entry` ノードおよび `boundaryField` ブロック内のパッチ `dictionary` ノードの検出、無関係な辞書への誤検出なし、空入力のエッジケース。
- `test_reset_all_settings.py` — **Reset All Settings** の後に `app_config.json` がどうなるかを検証します。ファイルを削除するだけでは処理の半分でしかありません。アプリケーションは動き続けており、`closeEvent` が終了時にセッションレイアウトとウィンドウサイズを保存していたため、ファイルが再生成され、ユーザーが消したばかりの設定がそのまま戻ってきていました。設定ファイルが削除された後の終了では何も書き込まないこと、削除されていない場合は従来どおり書き込むことを固定します。
- `test_run_tool_dialog.py` — `RunToolDialog`: 初期状態のライブプレビューが `get_command()` と一致すること、チェックボックス/値編集によるコマンド更新、`last_values` の復元と `get_values()` の新しいダイアログへのラウンドトリップ、解析不能な追加オプションでの実行ボタン無効化、プレフィックスチェックボックスによるシェルプレフィックスの付加、Browse によるケース相対パスの挿入（ケース外は絶対パス）。
- `test_stays_open_menu.py` — ツールバーのドロップダウンメニュー（`Vertices ▾`、`Blocks ▾`、`Scale ▾`、`topoSet ▾`、`snappyHexMesh ▾`）がチェック可能項目のクリックでは開いたままになり、チェック不可のアクションでは通常どおり閉じること。
- `test_terminal_panel.py` — `SimpleTerminalWidget` と `TerminalPanel`: 初期状態、作業ディレクトリの切替、クリーンアップ、コマンド履歴、タブラベル、`run_command()`（シェル準備前のキューイングを含む）。
- `test_theme.py` — `ui/theme.py` の配色テーブルをデータとして検証します: コントラスト計算、選択行の前景・背景ペアに関する慣習ルール（Windows のアクセントカラー `#0078d4` を明示的に指定したリグレッションテストを含む。黒と白のうちコントラストが高い方を選ぶ実装だと、この不具合を再現してしまうため）、どのアクセントカラーでも判読不能なペアが生じないことを網羅的に確認するテスト、両テーブルのすべての前景色がそのテーマの `Base` に対して 3:1 を下回らないこと、差分スウォッチと凡例の塗りが分離していること、そしてビューポートの文字色が `viewport_bg` に対して 3:1 を下回らないこと。いずれもテーブル単位の検査で、成立しない配色は検出しますが、単に見栄えが悪いだけの配色は検出しません。「テーマと配色」を参照。
- `test_tools_ops_mesh_actions.py` — Tools メニューの「Run *」アクションと Run Allrun/Run Allclean/Clean Case: blockMesh/snappyHexMesh/topoSet/setFields/checkMesh の（実物の、exec をパッチした）`RunToolDialog` を受理した後に偽のターミナルパネルへ送信される正確なコマンド文字列、キャンセル時に何も送信されないこと、時間ディレクトリが存在する場合にダイアログへ渡される再実行警告テキスト、`state.run_tool_options` からの前回オプションの復元、setFields の 0/ 復元プレフィックスチェックボックス（`0.orig/` があれば存在しデフォルトでチェック、なければ非表示、チェックを外せば「そのまま実行」）。Allrun/Allclean のスクリプト欠如警告、`log.*` が存在する場合の Allrun 三択プレフライト — クリーンしてから実行・そのまま実行・キャンセル —、Allclean への委譲または `-auto` による 0/ 削除に言及する Clean Case ダイアログ、`_update_tools_actions()` によるこれらのアクションおよび View Log Summary（ターミナルは不要でケースのみ必要）の有効化。
- `test_tree_block_crud.py` — `block_entry` 行に対する追加/複製/削除: `_new_sibling_for` が生成する `block_entry` のデフォルト値が実際のブロックとして再解析されること（辞書が親の場合は `word` エントリ）、`_delete_label` がブロックを位置で呼ぶこと、ブロックの削除・追加後に書き出されるファイル（兄弟はそのまま、リストは自分の行で閉じる、残りのブロックは位置で振り直される）、および MainWindow を通した削除 → エディタテキスト → Ctrl+Z の一連の往復。
- `test_tree_color_lexer_dispatch.py` — `unknown_raw_entry` の琥珀色表示、パーサの `_PAREN_DISPATCH` テーブル。
- `test_tree_copy_paste.py` — ツリーの Copy/Paste Value: コピーした値の round-trip、異なる型のノード間でのペースト、サポート対象外のノード型を拒否するガード。
- `test_tree_undo_redo.py` — スナップショット方式のツリー Undo/Redo: インライン編集の Undo が値・エディタテキスト・クリーンなダーティフラグを復元すること（Redo で再適用）、複数ステップの Undo、新しい編集による Redo ブランチのクリア、拒否された編集の迷子スナップショットのスキップ、削除/エントリ追加の往復、1 つの CRUD 操作がちょうど 1 つのスナップショットを生むこと（シグナルによる二重チェックポイントなし）、複数ファイルのスナップショットが全ファイルを復元すること、ケース再読み込みでのスタッククリア、深さ上限。
- `test_update_viewer_panels.py` — `MainWindow._update_viewer_panels`: ファイル名から 3D ビューアへのディスパッチを、オーバーレイを駆動する各辞書についてパラメータ化して検証し、無関係な辞書では何もディスパッチされないこと、そして Apply Text to Tree が snappyHexMesh オーバーレイを更新することを確認します。最後の 1 つがこのヘルパーの存在理由です: ディスパッチは読み込み・保存・ツリー編集の各パスにコピー&ペーストされており、apply 側のコピーには snappyHexMeshDict のケースが抜けていたため、編集した snappy のテキストを適用しても 3D 表示が更新されませんでした。
- `test_tree_inline_edit_dirty.py` — Tree パネルのインラインセル編集がファイルをダーティにしエディタテキストを再生成すること、拒否された編集はファイルをクリーンなままにすること。
- `test_view_log_summary_action.py` — `_on_view_log_summary_clicked`: ダイアログを閉じた後の再表示（閉じても破棄はされず非表示になるだけなので、キャッシュ済みインスタンスは再度 raise するのではなく show し直す必要がある）、ケースディレクトリ未設定時の no-op、ケース切り替えへの追従（`_load_case_dir` が次のメニュークリックを待たず、開いたままのダイアログへ `set_case_dir()` で即座に新しいディレクトリを反映する）。
- `test_window_state.py` — `ui/window_state.py` とそこへ渡すスクリーンショット spec: 全フィールドの JSON ラウンドトリップ、未知キーと不正なカメラ値の拒否、デフォルトのマージ（`side_by_side` が必要とする、`False` が `True` のデフォルトを上書きする挙動を含む）、名前によるキーパス指定と匿名エントリの行番号指定、実際の `MainWindow` からのキャプチャ、それらすべての寛容版（未知キーの破棄、不正なカメラ・サイズ・スプリッタサイズの破棄、使用不能な blob が `None` になること。存在しないケースディレクトリ・ファイル、辞書ではない大きなファイル、未知のタブ・スプリッタ、消えたツリー行は、例外ではなく戻り値のノートに記録してスキップされること）、`tools/screenshot_specs.json` の構造検査（state の妥当性、同一ファイルへ書き込むショットがないこと、パスのプレースホルダが既知であること、比較ショットが 2 つのケースをどちらも `$HOME` の外に指定していること — 差分バーが参照ケースのフルパスを画像に出力するため）。撮影ツール自体は実 X ディスプレイを要するため対象外。
- `test_session_restore.py` — `ui/session_restore.py`: 終了時に正しいキーでレイアウトが保存されること、設定オフでは何も保存しないこと、適用対象がないときに restore が正直に報告すること、壊れた blob（改名されたフィールド、形の変わったフィールド、切り詰められたカメラ、移動したケース、別言語のタブラベル）で例外を出さないこと、そして実際の `MainWindow` から別の `MainWindow` へケース・開いているファイル・選択ツリー行が往復すること。

**`tests/services/`**
- `test_backup.py` — バックアップファイルの命名（`.bak_<タイムスタンプ>`）と内容（ファイルが開いている場合はインメモリバッファ、それ以外はディスク上の内容をキャプチャ）。
- `test_case_copier.py` — `copy_visible_files`: 可視ファイルがレイアウトを保ってコピーされること、非表示エントリ（ルートの `log.*`、時刻ディレクトリ、未登録ファイル）はスキップされること、登録済み追加ファイルと `.foam-editor-files.json` 自体が引き継がれること、設定ファイルなしでも動作すること、ネストしたコピー先の作成。
- `test_include_scan.py` — `scan_includes`/`included_files`/`copy_destination_for`/`foam_etc_dirs`: パーサーが保存するのと同じ生ディレクティブテキストを hit が持つこと（ツールチップ検索のキー）、`#codeStream` の C++ ヘッダーのスキップ、非再帰性、サイズ・ログ・スクリプトのガード、mtime メモが未変更ファイルを読み直さず変更時には読み直すこと、ケース内／外の振り分け、既に一覧にあるファイルに対するシンボリックリンク考慮の重複排除、`+N more` の由来ラベル、`.gz` 対象の除外、etc ルート探索がユーザー設定を優先し `()` に縮退すること。
- `test_case_files_config.py` — `TestCaseFilesConfigDirs`: `DirEntry` の追加・削除・インプレース更新、プレーン文字列 JSON の後方互換ロード、設定リセット。
- `test_case_loader.py` — `detect_time_dirs` と `TestExtraDirs`: フラット・再帰スキャン、存在しないディレクトリの許容、重複排除。
- `test_example_search.py` — `example_search`: インストールルート／素の tutorials ディレクトリ／非インストールディレクトリに対する `installation_from_dir`、環境変数マッピングの注入・`extra_roots` の優先・重複排除を含む `discover_installations`、`stop` 境界付きで祖先を遡る `case_root_for`、両ソースでの一致（source/case_root/line_numbers/snippet フィールド）・大文字小文字を区別しない一致・`file_name` と `sources` フィルタ・`max_hits` 上限・`cancelled` による早期終了・バイナリ／サイズ超過ファイルのスキップ・一致行番号の 50 行上限・空クエリの `ValueError`・`progress` コールバックを検証する `search_examples`。
- `test_log_summary.py` — `parse_log`/`format_summary`: `blockMesh` の Mesh Information/Patches 抽出と致命的エラー検出、`snappyHexMesh` の `Wrote mesh in` マーカーによるフェーズ分割・カテゴリごとの細分化反復回数・最終的なパッチ別レイヤーテーブル・件数付きの警告重複排除、`topoSet` のマルチソースセットの集約（`Read set` チェックポイントは新規セットではなく同一セットの継続として扱われること）、ソルバーログ — 収束した定常計算（Run/Residuals フェーズ、収束メッセージ、合計時間）、Courant 行と ESI 形式の `Time = 0.005s` 単位サフィックスを含む非定常計算、致命的エラーや `End` 未到達の実行が FAILED になること、`Time =` 行はあるが残差のない `checkMesh` 型のログが汎用パスに留まること、未知のユーティリティに対する末尾行フォールバック。
- `test_tool_options.py` — `tool_options`: 期待される `TOOL_SPECS` の集合とデフォルトコマンド（snappyHexMesh のデフォルトでオンの `-overwrite`）、`build_args` の bool/value/file の仕様順処理、空値の省略、追加テキストの shlex 分割（閉じていない引用符 → `ValueError`）、古い未知フラグの無視、`build_command` のクォート・生プレフィックス・`tee log.<ツール名>` サフィックス。

**`tests/app_config/`**
- `test_app_config.py` — `AppConfigManager`: ウィンドウサイズ、デフォルトケースディレクトリ、Case Library ディレクトリ（`$WM_PROJECT_DIR/tutorials` フォールバックを含む）、`save()`/`reset()` のセマンティクス、`app_config.json` が存在しない場合のフォールバック、設定の組み合わせ、JSON 構造、フィーチャーフラグの扱い（`set_feature`/`set_features`）。
- `test_foam_env.py` — `foam_env_dirs`: 明示的な `FOAM_*` 変数が `WM_PROJECT_DIR` フォールバックより優先されること、サブディレクトリ単位のフォールバックはディレクトリが存在する場合のみ働くこと、無効・空白の変数は未設定扱いになること、バージョンの解決。
- `test_json_io.py` — `load_json` の欠落・破損・正常 JSON の扱い、`save_json` のラウンドトリップと親ディレクトリ作成、`atomic_write_text` が成功時に `.tmp` を残さないこと、最終リネームやシリアライズが失敗しても元ファイルが無傷のまま（一時ファイルも掃除される）こと。
- `test_keyword_generator.py` — `keyword_generator`: `*.C`/`*.H` から辞書読み取り呼び出し（`lookup`/`get<…>`/`readEntry`/`found` など）を収集する `scan_src_lookup_keywords()`（キーワードでない形式は除外）、フィクスチャのインストールツリーに対する `generate(project_dir=…)` — 環境変数は無視、`version` はディレクトリ名由来、ペイロードの来歴メタデータ、何も収集できない場合の `RuntimeError`。

**`tests/schemas/`**
- `test_schemas.py` — `ChoiceItem`/`KeySchema`、`schema_config.json` の読み込み・保存・リセット・削除、`SchemaRegistry` のプレーン/親修飾/祖父母修飾ルックアップ、他の名前空間の内側でフラットフォールバックを抑止する閉じた名前空間ルール（2 モデル構成の合成モジュールによる検証と、実在する `snappyHexMeshDict` の名前空間で過剰抑止が起きないことの確認）、`snappyHexMeshDict` スキーマモジュール、設定済みモジュール一覧。
- `test_schema_coverage.py` — モジュールが丸ごと機能停止したことを検出できたはずのテスト。`tests/fixtures/schemas/` にある実際の辞書（v2606 のチュートリアルから無改変でコピーしたもの。スキーマに合わせて手を加えていない点が重要）をパースし、`DetailPanel` とまったく同じ方法（`node.name`、`node.parent.name`、`node.parent.parent.name`）で走査して、辞書ごとのカバレッジ下限を検証します。`fv_schemes.py` はかつてキーを `"<key>.<parent>"` と綴っていた一方でレジストリは `"<parent>.<key>"` で引いていたため、全エントリが到達不能で実際の fvSchemes の 0% しか解決されませんでした。それでもユニットテストが通っていたのは、UI が実際に行う呼び出しではなく内部テーブルの形を検証していたからです。さらにテーブルの不変条件を 2 つ検査します。ドット区切りキーのサフィックスは `KeySchema.key` と一致しなければならないこと（当該モジュールが破っていたまさにその規則）と、`use_instead`／`renamed_from` の参照先がそのファイルに documented なキーとして存在すること。加えて来歴の各ケースをエンドツーエンドで検証します。motorBike の `minFlatness` が `ineffective` として報告されること、`minMedianAxisAngle` が後継とバージョン付きの `renamed` であること、`mergeType` が無効な `merge` を決して提示しないことです。
- `test_turbulence_schemas.py` — foamlore が生成した `turbulence_properties`/`momentum_transport` モジュール: `TARGET_FILE` と `SCHEMAS` の形状（値はすべて `KeySchema`、選択肢はすべて `ChoiceItem`）、`schemas/builtin.py` のモジュール一覧に両方が既定で登録されていること、`SchemaRegistry` による親修飾形式（`kOmegaSSTCoeffs.beta1`）と `RAS` 辞書直下へのプレーンなフォールバックの両方でのルックアップ、バージョン別の `supported_in` タグとソース既定値の選択肢（`decayControl` の OpenCFD 限定である旨の注記を含む）、そして `GENERATED` バナーがそのまま残っていること — これらのファイルは foamlore で再生成するものであり、手で編集してはいけません。 加えて手書きモジュールとの接合部: `RAS`/`LES` モデルセレクタを `DetailPanel` と同じ形（実際のファイルパスと親キー、`<Model>Coeffs` 辞書はどこにも存在しない状態）でルックアップし、その選択肢が `MODEL_DOCS` の説明と引用を持つことを検証します。これはこの変更自体が対象としたチェックです — レジストリ API 経由の確認だけでは、通常のケースでは何も表示されないのに散文が到達可能だと報告されていました。

**`tests/tools/`**
- `test_capture_dialog.py` — `tools/capture_dialog.py` のショット一覧を素のデータとして検証するテストで、`test_window_state.py` のスクリーンショット spec 検査に対応するものです: 名前がキーと一致すること、同じファイルへ書き込むショットが 2 つないこと、すべてのショットが両言語のギャラリーページから参照されていて画像も存在すること、`requires()` がトレースバックではなく不足しているものを名指しすること。ショットは入力の出どころ（撮影マシンかリポジトリか）で分類され、3 つ目のテストがすべてのショットがそのどちらかに分類されていることを検証するため、ショットを追加すると必ずどちらかを選ぶことになります。さらに `find-examples` ショットが操作する `FindExamplesDialog` のプライベート属性名を固定し、run-tool ショットの警告文と前置き文字列が `ui/mixins/_tools_ops.py` に今も存在することを検証します。これによりアプリが決して表示しないダイアログをギャラリーが見せてしまうことはありません。キャプチャ自体は実 X ディスプレイを要するため対象外です。
- `test_demo_specs.py` — `tools/demo_specs.json` のシーンを素のデータとして検証します。この中で最も費用対効果が高い検査です。収録には実 X ディスプレイと OpenFOAM のインストール、そして 1 分程度の実時間が必要なため、リネームされたメニュー項目を指しているシーンは、本来なら収録の途中で初めて失敗します。検証内容は、spec が strict な `WindowState` の経路で読み込めること、各ステップの種類と必須フィールド、ターゲットを取るステップがちょうど 1 つだけターゲットを指定していること（取らないステップは 1 つも指定していないこと）、パスと入力テキストのプレースホルダが `_expand` の知っているものであること、スクラッチ用 workdir がリポジトリの外にあること、そして同梱ケースについてのみ（`{cases}` のシーンは収録マシンに依存するため）ケースが存在し、シーンが開くファイルをすべて含んでいること。ラベルは上記 run-tool ショットと同じ考え方でUI のソースと突き合わせます: メニューバーのタイトル、省略記号付きのメニュー項目（ダイアログを開くアクションの慣習であり、ケースから読み出される形状名の行とは違ってソース中のリテラル）、ボタンのラベル、ウィジェットの属性名。実際に起きた不具合のためだけのテストも 1 つあります: ステップのマウスボタンは `with` であり、`button` は既にターゲット（クリックするボタンの名前）なので、`"button": "left"` は "left" という名前のターゲットとして解釈され、収録時にしか失敗しません。ステップの語彙は列挙ではなく `Runner` の `_step_*` メソッドから読み取るため、ドライバに新しいステップ種別を足してここが古いまま取り残されることはありません。操作と収録自体はディスプレイを要するため対象外です。

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
| `region_block` | 中身が名前付き辞書である `regions ( … );`。`constant/regionProperties` は同じキーを単純なリストに使っており、そちらは `raw_list` に落ちるため、先読みで判定する |
| `region_entry` | `region_block` 内の名前付き `{ … }` エントリ |
| `boundary_block` | `blockMeshDict` の `boundary ( … );` |
| `boundary_entry` | `boundary_block` 内の名前付き `{ … }` エントリ。`boundary_block` は `directive_entry` の子ノードを持つこともある: パッチの代わりに置かれた `#include`（`boundary ( #include "…caseBoundary" outlet { … } );`）はブロック全体を失敗させずに独立した子ノードとしてパースされるため、その前後のパッチは構造的パースを維持する |
| `action_list` | `topoSetDict` の `actions ( … );`; `value=None`、子ノードは `action_entry` |
| `action_entry` | `action_list` 内の無名 `{ … }` ブロック; `name=""`、子ノードは辞書エントリ |
| `named_dict_list` | 名前付き辞書の丸括弧リスト（省略可能な構文）— `sets ( y0.1 { … } … );` / `surfaces ( … );`（従来の sampleDict スタイル）。`(` の後に `name {` が続く場合のみ先読みで生成されるため、単純な単語リスト（`sets (setA setB);`）は従来どおり `raw_list` として解析される |
| `named_dict_entry` | `named_dict_list` 内の名前付き `{ … }` エントリ |
| `block_list` | `blockMeshDict` の `blocks ( … );`。`value=None`、子ノードは `block_entry`。すべてのエントリが `BLOCK_SHAPE_WORDS`（現状は `hex` のみ。`name <blockName>` プレフィックスは許容）で始まるリストの場合のみ、先読みによって生成される。それ以外 — 空リスト、単純な単語リスト、`hex` 以外の形状 — は従来どおり `raw_list` として解析される。`directive_entry` の子ノードを持つこともある: 別ファイルからブロックを取り込む `#include` は独立した子ノードとして保持され、その前後のブロックは行を維持する（ディレクティブのみのリストは展開すべきブロックがないため `raw_list` のまま） |
| `block_entry` | `block_list` 内の 1 ブロック。`name=""`、`value` は正規化したブロック全文（`hex (…) (…) simpleGrading (…)`）。セル数とグレーディングは子ノードにせず value 文字列のまま保持する — 現時点で参照する箇所がなく、グレーディングの文法も揺れが大きいため。行の並びは 3D ビューアのブロック番号と一致する。`hex` のみを展開対象とするのはそのため。同じリストに `directive_entry` が含まれる場合は `foam/utils.py` の `block_number` がその分を差し引き、両者の一致を保つ（後述の「`#include` があるときのブロック番号」を参照） |
| `directive_entry` | `#include`、`#inputMode` など。`name=""` |
| `macro_entry` | 文として単独で現れるマクロ参照。`name=""`、`value` は終端子を含まない参照そのもの。綴りは 4 通りあるがすべて同じノード型: `$p;`、裸の `$p`（OpenFOAM は辞書内でマクロ単独を完全な文として受け付ける。例 `maxX { $minX }`）、およびそれぞれをスコープパス付きで波括弧に包んだ形（`${../_bladeForces}`）。末尾の `;` はパース時に省略可能で `value` には保存しないため、writer は常に付加するのではなく `raw_text` から読み取る（`_macro_suffix`）。そうしないと裸の `$p` を編集した際に、元ファイルに無かった `;` が黙って追加されてしまう |
| `unknown_raw_entry` | パース失敗時のフォールバック。生テキストが `value` に逐語的に保持される |

### 分類ロジック

`_classify_value(key, text)`（`foam/parser.py:387`）は、波括弧・特殊括弧以外のすべてのエントリに対して呼ばれます。優先順位は次の通りです。

1. **`box_pair`** — `key == "box"` かつ `foam/utils.py` の `parse_box_pair(text)` が成功する場合のみ。
2. **括弧付き** — `classify_parenthesized_value`（`foam/utils.py:113`）に委譲。`vector`（ちょうど 3 つの float）、`int_list`（すべて整数）、`scalar_list`（すべて数値で 3 つでない）、`raw_list`（それ以外）を返す。
3. **`string`** — `"` で始まり `"` で終わる。
4. **`macro`** — `$` で始まる。
5. **空白を含む** — `nonuniform List…` で始まる場合は `nonuniform_list`、それ以外は `compound`。
6. 単一トークン: `int` → `scalar` → `bool`（`BOOL_WORDS` 内のトークン）→ `word`（フォールバック）。

`_classify_value` の前に、`key ( … );` 形式のエントリはまず `_try_parse_special_parenthesized_entry`
が処理を試みます。エントリの形ごとに 4 つのテーブルを順に参照します。

| テーブル | エントリの形 | 先読み |
|---|---|---|
| `_NAMED_BLOCK_PARAMS` | `name { … }` | なし — キーのみで決定 |
| `_ANONYMOUS_BLOCK_PARAMS` | `{ … }` | なし |
| `_OPTIONAL_NAMED_BLOCK_PARAMS` | `name { … }` | あり — `_looks_like_named_dict_list` |
| `_POSITIONAL_BLOCK_PARAMS` | `hex ( … ) ( … ) simpleGrading ( … )` | あり — `_looks_like_block_list` |

2 つの先読みはトークンを消費しません（`finally` で `self.index` を復元します）。そのため
不採用となったエントリは何も消費しないまま通常の値解析経路に落ちます。`sets` や `blocks` が
あるファイルでは構造化ブロック、別のファイルでは単なる `raw_list` になれるのはこのためです。

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
| `leading_trivia` | `list[str]` | ソース内でノードの前に現れる空白とコメント。**直前のエントリの行を終わらせる改行も含む**。ライタの `_with_leading_trivia` がエントリ間の空行を保持するために復元する。下記「トリビアの所有権」を参照。 |
| `trailing_trivia` | `list[str]` | ルートノード専用。最後のエントリより後ろのトリビア、すなわち閉じの `// ****` フッタバナーとその前の空行。`write_root` が最後に再出力する。 |
| `inline_comment` | `str` | 同一行の値の直後にある `// …` または `/* … */` コメント。`_collect_inline_comment` が収集し、ライタが再現する。 |
| `source_line` / `source_end_line` | `int` | `_token_line` が設定する 1 ベースの行番号。エディタ同期ハイライトに使われる。`0` はツリーで追加されたノードでソース位置情報がないことを意味する。 |

### ライタの raw_text パススルー

`_write_node`（`foam/writer.py:61`）は 3 つの条件がすべて満たされる場合、再生成を完全にスキップします。

```python
if not node.modified and node.raw_text and not _has_modified_descendant(node):
    return _with_leading_trivia(node, node.raw_text)
```

3 つすべてが True の場合、元のソーステキストがそのまま出力され、フォーマット・インラインコメント・正確な空白が保持されます。`modified=True` のノード（または変更済みの子孫を含むノード）のみが再生成されます。未編集のファイルに対する「Reload from Tree」は、`raw_text` がキャプチャされたすべてのエントリでバイト同一の出力を生成します。

`_has_modified_descendant` はほとんどの型で `node.children` を再帰的に辿ります。`field_value_block` については `node.value` も直接チェックします（下記参照）。

### トリビアの所有権

上記のパススルーが元のソースを逐語的に再現できるのは、エントリ**間**の空白を誰が所有するかについてパーサとライタの取り決めが一致しているからです。

> **ノードのテキストは、そのノードの最後の内容文字で終わる。** その行を終わらせる改行はノードの一部ではなく、次に来るもの — 次の兄弟ノードの `leading_trivia`、または外側のブロックの閉じ括弧 — が所有する。

したがって `scale 0.001;` の `raw_text` は `;` で終わり、次のエントリとの間を隔てる `\n\n` は次のエントリの `leading_trivia` に入ります。この結果、`root.children` にわたって `"".join(node.leading_trivia) + node.raw_text` を連結すると、ソースがバイト単位で復元されます。

ここから 2 つの要素が導かれます。

- **`root.trailing_trivia`**（`foam/nodes.py`）は最後のエントリより後ろに残ったトリビア — 通常の OpenFOAM 辞書では空行と閉じの `// ****` フッタバナー — を保持します。どのノードにも属さないため、`parse()` がルートに預け、`write_root` が最後に再出力します。このフィールドを使うのはここだけで、他のノードの後続空白はすべて次のノードの `leading_trivia` です。
- **`_join`**（`foam/writer.py`）はレンダリングされたパートを連結し、自分自身では間隔を確保できないパート — ツリーで追加されたノードと、ライタ自身が生成する括弧やヘッダ — に対してのみ改行を挿入します。この判断を文字列の検査で行ってはいけません。2 つのエントリの区切りは半角スペース 1 個であることが正当にあり得る（`x1 14; x2 6;`）ため、生成されたインデントと区別できないからです。そこで `_part` がフラグを明示的に渡します。

  `leading_trivia` を持たないノードが自動的に「改行が必要なノード」になるわけでは**ありません**。ソース上で直前のエントリに何も挟まずに接していた解析済みノードであることも同様にあり得ます — 一部の辞書が末尾に付ける `;`（`divSchemes { … };`）がそれで、独立したエントリでありながら `}` と同じ行に留まらなければなりません。`_continues_previous_line` は、解析済みノードだけが持つ `source_line` によってこの 2 つを区別します。`_write_inline_entry` も同じ判定を参照し、そのままでは前置してしまうインデント（`}    ;`）を抑止します。

- **`_own_indent`**（`foam/writer.py`）はノード*自身の最初の行*のインデントを決めるもので、上のルールと対になります。`_with_leading_trivia` がソースのインデントをそのまま再出力するため、レンダラ側でさらに `_indent(indent)` を前置すると行が二重にインデントされます。ネストしたエントリを再生成したときに実際にそうなっていました — `PIMPLE { … }` の中の `nCorrectors` を編集すると 4 スペースから 8 スペースに動いていました。行を開始するヘルパーはすべて `_own_indent` を経由します（`_write_block` の名前/開き括弧、`_write_field_value_block`、`_write_simple_entry`、`_write_inline_entry`、`_write_block_entry`）。その最初の行の*下*にライタが生成する開き括弧・閉じ括弧は、自身のトリビアを持たないため従来どおり `_indent(indent)` のままです。

  ルールは次のとおりです: トリビアが空白かタブで終わっている場合、または直前の行に続くノードの場合はインデントなし。それ以外は生成インデント — ツリーで追加されたノードに必要なもので、ソースが桁 0 に書いたエントリにも適用されます。

`write_root` は独自の文字を一切追加しません。最終改行なしで終わるソースファイルは、最終改行なしのままラウンドトリップします。**ライタに「保存時にファイルを整形する」ポリシーは存在せず、今後も持たせてはいけません。** 未編集のチュートリアルケースを保存したらバイト単位で同一でなければならず、編集済みのケースを保存したら編集したエントリだけを書き換えなければなりません。

この修正以前は、そのどちらも満たしていませんでした。`write_root` がすべてのチャンクに `\n` を強制付加し、次のノードのトリビアが既に持っている改行を二重計上していました。2 つの `re.sub` による応急処置（`MAX_CONSECUTIVE_NEWLINES` と `re.sub(r'\n{2,}$', '\n', leading)`）が二重化を糊塗していましたが、これらは非可逆でした — 実際の空行の連続を潰し、`// * * *` バナー周りの空行を移動させ、さらに `parse()` が EOF のトリビアを破棄していたことと相まって、フッタバナーを丸ごと削除していました。OpenFOAM v2512 チュートリアル内で解析可能な `system/blockMeshDict` 439 件すべてが保存時に書き換えられていました。`tests/foam/test_writer_roundtrip.py` の `_CORPUS_SHAPED_DICT` は、それ以前のフィクスチャに欠けていた形状（バナー、複数行の空行、フッタ）を固定します。テストがずっと通り続けていたのはこの欠落が理由です。

`tools/roundtrip_corpus.py` は OpenFOAM インストール全体でこれを測定するため、リリースノートの数値は鵜呑みにせず再導出できます:

```bash
python3 tools/roundtrip_corpus.py --dir /usr/lib/openfoam/openfoam2512
```

チュートリアルケースの `system/`・`constant/`・`0/`・`0.orig/` 配下の全ファイルを走査し、解析できた件数とバイト単位で一致した件数を報告します。`--list-differing` を付けると一致しなかったファイル名を列挙します。v2512 では 9620 ファイルを読み、9620 件すべてが解析でき、その 9620 件すべてがラウンドトリップします。トリビア所有権の修正前は、同じコーパスで 286 件でした。解析可能件数は、マクロエントリの修正（波括弧付き `${…}` 参照と省略可能な `;`）が最後の 119 件を解消するまでは 9501 件でした。

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
    status: KeyStatus = "valid"
    use_instead: str = ""
    deprecated_since: str = ""

@dataclass(frozen=True)
class KeySchema:
    key: str
    label: str
    description: str
    supported_in: tuple[str, ...] = ()
    note: str = ""
    choices: tuple[ChoiceItem, ...] = ()
    status: KeyStatus = "valid"
    use_instead: str = ""
    renamed_from: tuple[str, ...] = ()
    deprecated_since: str = ""
```

`_base.py` はバージョン文字列定数もエクスポートします。`FOUNDATION_V7` 〜 `FOUNDATION_V13`、`OPENCFD_V2106` 〜 `OPENCFD_V2606` に加え、総称ラベルの `FOUNDATION_SERIES`、`OPENCFD_SERIES`、`BOTH_FORKS` です。共有ライブラリである `finiteVolume`/`lduMatrix` に属するキーには総称ラベルを使ってください。個別リリースを 1 つだけ指定すると、詳細ペインでは「そのリリースでしか使えない」と読めてしまいます。実際、61 個のエントリが中核キーを Foundation 限定であるかのように OpenCFD ユーザーへ表示していました。

### キーが何であるかの記録: `status` フィールド

実際の辞書には、すでに現行ではない名前や、そもそも一度も機能したことのない名前が数多く含まれます。`KeyStatus` は 3 値で、詳細ペインはこれに応じて説明文を切り替えます（`DetailPanel._apply_provenance`）。

| status | 意味 | 例 |
|---|---|---|
| `valid` | 現行のキー | `scale` |
| `renamed` | 旧称。`use_instead` が後継、`deprecated_since` がバージョンを示す | `convertToMeters` → `scale`（v1012） |
| `ineffective` | 公式チュートリアルに現れるがどのリーダも読まないため、書いても何も起きない | `minFlatness` → `minFaceFlatness` |

`renamed`／`ineffective` のキーは削除せず**残します**。旧称を含むケースを開いたユーザーにこそ、それが何なのかを伝える必要があるからです。`renamed_from` は**現行**キー側に置き、その旧称を列挙します。

リネーム情報の出所: OpenCFD は `getCompat("newName", {{"oldName", apiVersion}})`、Foundation は `lookupBackwardsCompatible<T>({"newName", "oldName"})` という形で、リネームを機械可読な形でソースに宣言しています。この 2 系統の呼び出しをソースツリー全体から抽出すると、フォーク別のバージョン範囲付きで約 100 組の旧称→新称が得られます。そのうち 4 組は互換エントリが後に削除されたため古いツリーにしか残っておらず、たとえば `minMedianAxisAngle` は OpenCFD では v2206 まで、Foundation では現在も受け付けられます。FoDE 側にはこのためのジェネレータを意図的に置いていません。抽出は一度きりの調査であり、結果は手作業で転記します。

### 生成モジュール（foamlore からのベンダリング）

`schemas/_turbulence_coeffs.py`・`schemas/turbulence_properties.py`・`schemas/momentum_transport.py` は**生成ファイル**で、姉妹リポジトリ foamlore の `facts/tools/generate_fode_schemas.py` から取り込んでいます。**29 モデル**（RAS 16、LES/DES 13 — 両フォークが出荷する全モデル）の乱流モデル係数を、17 リリース全部（Foundation 7–13、OpenCFD v2106–v2606）の OpenFOAM `.C` コンストラクタから機械的に抽出し、それらのリリースにわたって実測した `supported_in` タグとソース既定値の `ChoiceItem` 付きで収録します。係数キーは親修飾（`kOmegaSSTCoeffs.beta1`）で出力され、OpenFOAM の `optionalSubDict` 読み取りイディオムに合わせて素のフォールバックキーも付きます。同じ名前を複数のモデルが読む場合、素のエントリは所有する全モデルを列挙し、各モデルの既定値を提示します。ここでは編集せず、foamlore で再生成して再コピーしてください（テストが `GENERATED` バナーの存在を検証します）。

ファイルが 2 つではなく 3 つなのは、foundation が OpenFOAM 8 で `constant/turbulenceProperties` を `constant/momentumTransport` に改名したためです。`_turbulence_coeffs.py` が係数のファクトを 1 度だけ保持して `build_schemas(target_file)` を提供し、残り 2 つはそれぞれ約 25 行で自身の `TARGET_FILE` を宣言してこれを呼びます。`_turbulence_coeffs` は import されるだけで登録しません — `TARGET_FILE` を持たないので、どのみち `SchemaRegistry` は読み飛ばします。

**この 2 つを `TARGET_FILES` の 1 モジュールに統合しないでください。** `_build_file_key_schemas` は複数ファイルを挙げたモジュールのテーブルを各ファイルへ**同一のまま**マージするため、OpenCFD 専用のキー（`decayControl`、`GEKOCoeffs` 全体）が `constant/momentumTransport` の中で解決してしまいます — OpenCFD のどのリリースも読まないファイルです。2 つの間で共有しているのはファクトだけで、バージョンタグ・注記・既定値一覧はすべて対象ファイルに依存します。文字どおりの統合を安全にするには、レジストリにキー単位の対象フィルタが必要です。

`_turbulence_coeffs` は `MODEL_DOCS`（`モデル名 → (説明, 注記)`。モデル自身のヘッダにある要約と、引用している論文）も公開しており、`turbulence_structure.py` がこれを import して `RAS`/`LES` モデルセレクタの選択肢を組み立てます。手書きと生成の境界を意図的に跨いでおり、向きが重要です。選択肢の*リスト*とその `supported_in` タグは辞書についての構造的な事実であり手書きモジュールが所有し、各名前に対する散文は抽出されたものです。これがないと、モデルの説明は `<Model>Coeffs` — 既定値を上書きするケースにしか存在しないキー — 経由でしか到達できません。import する側のモジュールは `TARGET_FILE` を宣言せず登録もされないため、`schemas/builtin.py` の読み込み順は関係しません。セレクタのキー自体はこれとは異なり、生成側では意図的に出力していません（生成モジュールは `turbulence_structure` の*後*に読み込まれるため、出力すると衝突ではなく暗黙の上書きになります）。

### SchemaRegistry

`SchemaRegistry`（`schemas/registry.py`）は `schemas/__init__.py` がインポート時にロードするシングルトンです。`schema_config.json`（ファイルが存在しない場合は組み込みデフォルト）のモジュール名リストから `_file_key_schemas[ファイル名][ドット区切りキー] → KeySchema` の 2 階層辞書を構築します。

モジュールは対象を `TARGET_FILES`（タプル）または従来どおり単一の `TARGET_FILE` で宣言します。テーブルはファイルごとに**マージ**され（置換ではありません）、複数のモジュールが 1 つの辞書に寄与できます。衝突時は後のモジュールが優先されます。これにより、手書きの `turbulence_structure` モジュールを同じファイルの生成係数モジュールと併存させることができ、また 1 つのモジュールが `turbulenceProperties` と `momentumTransport` の両方を担当できます。

`schema_for_file_key(file_path, key_name, parent_key, grandparent_key)` は次のルックアップを実施します。

1. `f"{parent_key}.{key_name}"` — 直接の親コンテキスト。
2. `f"{grandparent_key}.{key_name}"` — 祖父母コンテキスト（名前付き `refinementSurfaces` エントリなど、直接の親がユーザー定義の場合に使用）。
3. `f"{parent_key}.*"` — ワイルドカード。子の名前がケース依存で列挙できない辞書のためのものです（`divSchemes { div(phi,U) … }`、`relaxationFactors { equations { U 0.7; } }`、`residualControl { p 1e-3; }`）。意図的に**直接の親のみ**に限定しています。祖父母からもワイルドカードを照合すると 1 階層行き過ぎてしまい、関数オブジェクト 1 つを説明する `functions.*` がその**中身**のすべてのキーにも答えてしまうためです。`*` サフィックスは接頭辞を名前空間として登録しますが、所有キー集合からは除外されます。含めると 5 のガードがファイル全体に対して発動してしまいます。
4. プレーンな `key_name` — フラットフォールバック。ただし 5 が抑止する場合を除く。
5. ドット区切りの接頭辞は**閉じた名前空間**です。あるモジュールが `kOmegaSSTCoeffs` の下にキーを 1 つでも修飾した時点で、そこに修飾されていないキーはその辞書のキーではなく、3 が代わりに答えてはいけません。したがってフラットフォールバックは、親（または祖父母）がそのファイルで宣言済みの接頭辞であり、**かつ**そのキーが別の接頭辞の下に修飾されている場合に抑止されます。どの接頭辞にも属さないキーは影響を受けず、これまでどおりどのコンテキストからでもフォールバックします。`snappyHexMeshDict` の 9 つの名前空間（いずれのキーもフラットな双子を持ちません）が従来どおり解決されるのはこのためです。このルールが必要なのは、係数が OpenFOAM の `optionalSubDict` 経由で読まれるため、各係数が修飾形とフラット形の 2 通り（`kOmegaSSTCoeffs.beta1` と、`RAS { beta1 …; }` という書き方のための `beta1`）で登録されているからです。これがないと、そのモデルが読まない係数を紛れ込ませた `kOmegaSSTCoeffs { C1 1.44; }` がフラットな `C1` で解決され、kOmegaSST の辞書の中で kEpsilon の係数を表示してしまいます。

`_build_qualified_index` は 2 つの集合（そのファイルが宣言する接頭辞と、そのいずれかの下に修飾されたサフィックス）をキーテーブル自体から導出します。したがってモジュールはドット区切りキーを使うだけでこのルールの対象になります。

名前空間でありながら任意のキーを正当に含む辞書もあります。`RAS` は自身の構造キー（`model`、`turbulence`）を持つ一方で、OpenFOAM の `optionalSubDict` イディオムによりモデル係数を直接書くこと（`RAS { Cmu 0.09; }`）も許されます。構造だけでは `kOmegaSSTCoeffs` と区別できないため、モジュールはそうした接頭辞を **`OPEN_NAMESPACES`** に列挙し、それらはフラットフォールバックを維持します。`schemas/turbulence_structure.py` は `RAS`、`LES`、`laminar` を宣言しています。`<model>Coeffs` 辞書は閉じたままです。

### 設定: デフォルトは置換ではなくマージ

`load_schema_config()` は保存されたファイルをそのまま返し、`SchemaRegistry._effective_config` が `union(組み込みデフォルト, 保存値) - disabled_modules` を計算します。以前は保存済みリストが唯一の正でした。そのため後のリリースで `schemas/builtin.py` にモジュールを追加しても、**Manage Schema Modules** を一度でも開いたことのあるユーザーには永久に届きませんでした。設定はその日のリストに固定されてしまうからです。現在は、ユーザーが明示的に削除したモジュール（`set_schema_modules` が `disabled_modules` に記録）だけが除外されます。`disabled_modules` が存在する前に書かれた設定には意図の記録がないため、当時削除したモジュールは一度だけ再表示されます。これは安全側の選択です。余分なスキーマは目に見えてクリック 1 回で削除できますが、欠けたスキーマは目に見えません。

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

## インクルードの解決

辞書は `#include` 系のディレクティブで別のファイルを取り込むことができ、OpenFOAM チュートリアルではそのおよそ半数がケースの**外**、インストール先の `etc/caseDicts/` を指しています。`foam/parser.py` は従来どおり全ディレクティブを不透明な `directive_entry`（`name=""`、`value` は生のソース行）として保持します。インクルードされた内容が取り込み元のツリーに展開されることはありません。代わりに対象を実ファイルとして解決し、シンボリックリンクされたファイルと同じように**独立したファイル**として一覧に表示します。

**2 層構成。** `foam/include_resolver.py` はテキスト→パスの純粋なロジックで、Qt 非依存・標準ライブラリのみです。`etc_dirs` を*引数*として受け取るため、`foam/` の無依存ルールが保たれます。`services/include_scan.py` がディスク側を担当し、`etc` 検索パスの供給、ケース全体への適用、キャッシュを行います。

`parse_include_directive(text) -> IncludeRef | None` は末尾のコメント・`;`・空白・引用符 1 層を取り除いたうえで、追跡対象でないものを弾きます。`resolve_include(ref, source_file=…, case_dir=…, etc_dirs=…) -> ResolvedInclude` は常に値を返し、`path is None` が未解決を表して `status` がその理由を示します。

| status | 意味 |
|---|---|
| `resolved` | `path` がディスク上のファイル |
| `missing_optional` | `#sinclude`/`#includeIfPresent` の対象が存在しない — OpenFOAM として正当であり、警告扱いにも一覧掲載もしない |
| `no_installation` | `etc` 系なのに `etc_dirs` が空。「ファイルが無い」ではなくインストール選択を促せるよう区別する |
| `missing` | それ以外 |

**解決順序** — 最初に見つかった候補が採用され、各候補は `foam/utils.py` の `resolve_optionally_gzipped` を通ります。

| 種別 | 候補（順に） |
|---|---|
| `include` / `sinclude` / `includeIfPresent` | 先頭トークン展開 → `<取り込み元ファイルのディレクトリ>/target` → `<case>/target` |
| `includeEtc` | 各 etc ルートについて `<root>/target` |
| `includeFunc` | `<case>/system/<name>` → 各 etc ルートの `<root>/caseDicts/postProcessing` を再帰探索した名前→パスの索引 |

「取り込み元ディレクトリを先に、次にケース」という 1 つの規則で実際の形をすべて賄えます。`0/U` + `"include/initialConditions"` は `0/include/…` を、`system/snappyHexMeshDict` + `"meshQualityDict"` は `system/meshQualityDict` を見つけます。`includeFunc` でケース内の `system/<name>` が優先されることが、**ケースにコピー**をディレクティブの編集なしに効くオーバーライドにしています。

その前段として `os.path.expandvars`（`$FOAM_CASE`、`${WM_PROJECT_DIR}`。未設定の変数はそのまま残って単に解決に失敗します — OpenFOAM 環境を読み込まずに起動することはエラーではありません）が走り、続いて OpenFOAM の `fileName::expand` と同じく*先頭の*パストークン `<case>`、`<system>`、`<constant>`、`<etc>`（etc ルートごとに候補を 1 つ生成）を展開します。

**etc 検索パス**は `include_scan.foam_etc_dirs()` が構築します。キャッシュ・重複排除のうえ実在するディレクトリのみを残し、`~/.OpenFOAM/<version>/`（OpenFOAM 自身の第 1 候補）→ 設定キー `openfoam_dir` + `/etc`（共有の `InstallationSelector` が保存）→ `foam_env_dirs().etc_dir` → `discover_installations()` の各ルート + `/etc` の順です。インストールが 1 つも無ければ `()` を返し、etc 系 2 種は `no_installation` を報告します。なおケースがどの OpenFOAM バージョン向けかは判別できないため、ユーザーが明示的に選ばない限り古いリリース向けのケースでも最新の `etc` に対して解決されます。

**なぜパースではなく正規表現の行スキャンなのか。** `scan_includes` はファイル一覧の更新のたびに走り、その更新は 400 ms デバウンスの `QFileSystemWatcher` が駆動します。そのためディレクトリを走査せず（`list_case_files` が既に返したパスのみを読む）、正規表現より先に部分文字列（`"#include"`/`"#sinclude"`）で大半を弾き、512 KB 超のファイルとスクリプト・`log.*` を除外し、ファイルごとに `(mtime, size)` でメモ化します。`_dedupe_key` の `Path.resolve()` もメモ化しています — シンボリックリンク解決のため全パス要素を辿るので、対策前は更新コストの大半を占めていました（54 ファイルのケースでウォーム 4.4 ms → 1.5 ms）。`setConstraintTypes` のような参照は全フィールドファイルに現れるため、解決自体も 1 回のスキャン内で重複排除されます。

**C++ ヘッダーの除外。** `#codeStream` の本体には C++ ソースを取り込む本物の `#include` 行が含まれ、これらがファイル一覧に混入してはいけません。両方の入口に 2 つの規則を適用します。トークン全体が山括弧のもの（`^<.*>$`。`<constant>/caseSettings` は `>` で*終わらない*ため対象外）と、`.H/.h/.C/.cc/.cpp/.hpp/.hxx` の拡張子です。v2512 チュートリアルに対して実測したところ、これで過不足なく機能します。当該コーパスの誤検出（`createTime.H`、`argList.H`、`fvCFD.H`、`setRootCase.H` など）はすべて `.H` で終わり、辞書のインクルードで終わるものは 1 つもありません。とはいえ証明ではなくヒューリスティックです（「更新候補」を参照）。

v2512 チュートリアル全体では 1081 件中 1072 件のディレクティブが解決します。残る 9 件は `Allrun` が生成するファイル（`blockMeshDict.caseBlocks`、`constant/ignitionPoint`）か、`0.orig/` をコピーして初めて存在する `0/` 配下のファイルで、未実行のケースでは「見つからない」が正しい報告です。

**解決は 1 段階のみで、再帰的ではありません。** インクルードされたファイル自身はスキャンしません。

**一覧への反映。** `services/case_loader.list_case_files` はあえて変更していません。これはケースの許可リストであり、`services/case_copier.copy_visible_files`（ケースの複製時に `/usr/lib/openfoam/…` をコピーしてはいけない）と Add-files ダイアログの `loaded_set` が依存しています。インクルードはその後に `_case_file_paths`（`ui/mixins/_file_ops.py`）が追加し、`_load_case_dir` と `_reload_file_list` の両方がこれを呼びます。既に一覧にある対象は通常の見た目のままで、スキャンが*追加した*行だけが `_INCLUDED_ROLE` と `↳` マーカーを持ちます。重複排除は解決後の実パス（シンボリックリンクの別名も一致）で行い、*表示*パスはインクルードの綴りのままです。`.gz` に解決した場合は `resolved` と報告しつつ一覧からは除外します（`foam/utils.py` の `read_foam_file` が展開できないため）。

`model/file_list_model.py` の `_group_name` は 1 箇所だけ変更しました。`except ValueError`（ケースディレクトリ配下でないパス）の分岐が新しい `INCLUDED_GROUP` センチネル（`"<included>"`、順序 2000 で `ROOT_GROUP` より下）を返します。ケース*内*のインクルードは `relative_to` に成功して `constant`/`system`/`0/heater` などの本来のグループへ自動的に収まります — グループ分けの規則はこれだけです。`case_dir is None` の経路のために従来の `p.parent.name` フォールバックは残しています。

**読み取り専用の契約。** ケース外のインクルードは表示のみで書き込みません。編集すれば全ケースが共有するファイルを変えてしまうためです。述語は `_is_read_only(path)`（`ui/mixins/_model_ops.py`）1 つだけで、一覧読み込みのたびに `_case_file_paths` が再構築する `state.read_only_files` を参照します。ゲートは 9 箇所です。`_mark_dirty`/`_mark_path_dirty`（**実質的な錠前**。dirty にならないことで `*` マーカー・Save All・未保存確認がまとめて成立しなくなります）、`save_file`、`save_all_files`、`EditorPanel.set_read_only`、`FoamTreeModel.flags`（`ItemIsEditable` を与えないことでインライン編集*と*値の貼り付けの両方が無効化されます）、`DetailPanel._populate_normal`、ツリーのコンテキストメニューの変更系項目、`apply_text_to_tree`、そして `_create_backup`/`_on_delete_file_requested`/`_on_duplicate_file_requested`（いずれも当該ファイルかその隣に書き込みます）。`ui/mixins/_diff_ops.py` は変更不要です — `_recompute_diff` と `_precompute_diff_step` は既に `relative_to(case_path)` を `try/except ValueError` で囲んでおり、ケース外ファイルは自動的にスキップされます。この既存のガードが今や本質的な役割を担っています。

**ケースにコピー**（`_on_copy_into_case_requested`、`ui/mixins/_file_mgmt_ops.py`）が逃げ道で、読み取り専用の行にのみ表示されます。コピー先は `include_scan.copy_destination_for` が決めます。`includeFunc`/`includeEtc` は `system/<name>` に平坦化し、相対パスを持つ素の `#include` はその相対パスを維持するので、ディレクティブを一切編集せずにコピー先へ再解決されます。包含チェックは事前に正規化します — `Path.relative_to` は純粋に字句的なので、そうしないと `<case>/../escaped` が通ってしまいます。処理後は `_reload_file_list()` を呼びます。`_load_case_dir` では未保存バッファがすべて失われるためです。

**ツリー側の導線。** `directive_entry` の行はコンテキストメニューに **Open Included File** を持ち、Key/Type 列のダブルクリックにも反応します（Value 列はディレクティブが値編集可能なのでインライン編集のままです）。どちらも `_open_included_target` に繋がります。解決結果の注記は `FoamTreeModel.set_include_notes` 経由でツールチップと Detail パネルの注記行に届きます。これは `_load_tree` の直後にキャッシュ済みのスキャン結果から与えられるため、モデルがツールチップ描画のためにディスクへ触ることはありません。注記はディレクティブのソーステキストそのものをキーにするので、`IncludeHit` は再構成ではなく生の一致行を保持しています。

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

## ブロックの選択と CRUD

`blockMeshDict` の `blocks ( … )` は、無名の `block_entry` 行からなる `block_list` としてツリーに届きます。これらの行が*位置指定*であることから 2 つの帰結があり、どちらも設計の要になっています。

- 行の `block N` というキーは保存されているのではなく `index.row()` から合成されます（`model/tree_model.py` の `_display_key`）。行を挿入・削除すれば、それ以降のキーは自動的に振り直されます。
- 同じ番号を `BlockMeshRenderer._render_blocks` が各ブロックの重心に描画します。どちらも `data.hex_blocks` の解析順から来ているためです。**ツリーの行番号はビューアのブロック番号そのもの**であり、間に変換は不要です。

### `#include` があるときのブロック番号

「行番号 = ブロック番号」が唯一崩れるのは、`block_list` が `directive_entry` も含む場合です。`boundary` と同様に、別ファイルで定義されたブロックを取り込む `#include` です:

```
blocks
(
    #include "blockMeshDict.caseBlocks"
    hex ( 48  52  53  49  64  68  69  65) ($yc $zc $x4) simpleGrading (1 1 1)
    …
);
```

このディレクティブはブロックではないのに 1 行を占めます。一方 `block_mesh_extractor` は `hex` エントリのみを数えるため、素の行番号では `#include` の直下の最初のブロックが `block 1` となり、ビューアが描画する `0` と食い違います。`foam/utils.py` の `block_number(parent, row, skipped=None)` がこの補正の唯一の実装で、3 つの利用箇所すべてがこれを通ります: モデルのキー列とツールチップ（`_block_number` 経由。リストごとに `non_block_rows` をメモ化し、`insert_node`/`remove_node` でキャッシュを破棄することで、ディレクティブがない通常のケースを O(1) に保ち、キー列が避けなければならない O(N²) の全走査を再導入しない）、`_delete_label`、`_highlight_selected_block`。

このとき両者が数えているのは*このファイルに書かれた*ブロックのみです。`#include` が取り込む内容は FoDE からは不可視で、この書き方をしている唯一のチュートリアル `compressible/rhoPimpleFoam/laminar/helmholtzResonance` では、`blockMeshDict.caseBlocks` は `Allrun` が実行時に作成するシンボリックリンク（`blockMeshDict.resolvedBlocks` = 23 ブロック、または `blockMeshDict.modelledBlocks` = 0 ブロックを指す）であり、未実行のケースには存在しません。したがってこれらの番号は、include を解決した後の blockMesh 自身の番号とはずれ得ます。ずれてはならないのは両者*の間*であり、それがツリーとビューアの対応が依拠する不変条件です。

**CRUD。** Add Entry After・Duplicate・Delete は、親が `dictionary` でなくても `block_entry` 行で有効です（`ui/mixins/_tree_crud_ops.py` の `parent_is_block_list`）。ブロック固有の点が 2 つあります。

- `_new_sibling_for` は、他の場所で使われる `newKey / newValue` のプレースホルダではなく、実在する `hex ( … ) ( … ) simpleGrading ( … )` を与えます。プレースホルダではブロックとして再解析されないため、次の Apply Text to Tree で行が消えてしまいます。
- `_delete_label` は確認ダイアログ用に位置でノードを呼びます。`node.name` が `""` だからです。

**Comment Out は無効のままです。** 括弧の中の `// hex …` という行は OpenFOAM としては正当ですが、*トリビア*として再解析されます。そのため、コメントアウトされて復元可能な行になるのではなく、行そのものが消えてしまいます。

**ハイライト。** `on_tree_selection`（`ui/mixins/_tree_sync_ops.py`）が選択行を `BlockMeshPanel.set_selected_block` に転送し、パネルはそれを保持して再描画します。`RenderSettings.selected_block` がそれを `BlockMeshRenderer._render_selected_block` に運びます。ハイライトは共有のブロックグリッド上のスカラーではなく独立したアクタ（太い wireframe と `viewport_selected_block` の半透明サーフェス）です。ブロックは単一の `UnstructuredGrid` として描画されるため、**Block edges** と **Solid blocks** の両方がオフでもハイライトは表示される必要があるからです。他の行を選択すると解除され、別のメッシュを読み込むと破棄されます — そうしないと番号が別ファイルのブロックを指してしまいます。パネルがツリーとは別のファイルのメッシュを保持している可能性があるため、レンダラ側でも範囲チェックを行います。

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
python3 main.py --theme dark                      # この実行のみ。保存された設定は変更されない
```

`--theme` フラグ（`system`/`light`/`dark`）は、保存済みの **Settings > Appearance** の値をそのプロセスに限って上書きし、書き戻しません。異なるテーマのウィンドウを同時に起動しても、次回起動時のテーマは変わりません。`tools/capture_screenshots.py` はこの動作を利用しています。

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

## テーマと配色

`ui/theme.py` は UI が描画するすべての色の唯一の出所であり、`QPalette` に触れる唯一のモジュールです。`main.py` で `MainWindow` の構築前に一度だけ適用されます:

```python
apply_theme(app, get_app_config().get_theme())   # "system" | "light" | "dark"
```

**モード。** `system` はプラットフォームのスタイルとデスクトップのパレットを維持し（Windows のアクセントカラーや Linux のデスクトップテーマがそのまま反映されます）、選択行の色の組だけを正規化します。`light`/`dark` は `app.setStyle("Fusion")` を呼んで FoDE 独自のパレットを適用するため、結果がプラットフォームスタイルに依存しません。モードは `app_config.json` の `theme` キーとして永続化され（`AppConfigManager.get_theme`/`set_theme`。他のセッターと同じく自動保存はしません）、言語設定と同様に再起動後に反映されます — パネルのスタイルシートはウィジェット構築時に焼き込まれるため、実行中の切り替えではウィンドウが中途半端な状態になってしまいます。

**選択行の色を計算し直す理由。** Qt は `QPalette.Highlight` と `QPalette.HighlightedText` をデスクトップから独立に読み取り、互いの組み合わせを検証しません。Windows では塗り色だけがユーザーのアクセントカラーに追従するため、彩度の高い塗りの上に暗い文字が乗ります。

ここで注意すべきは、素朴な修正 — 黒と白のうち WCAG コントラストが高いほうを選ぶ — では**問題が再現してしまう**ことです。Windows 11 の既定アクセント `#0078d4` は黒に対して 4.64:1、白に対しては 4.53:1 しかないため、数値では黒が勝ちます。中間輝度付近では数値上の勝者はわずかな差で入れ替わります。そこで `readable_selection_pair` は、数値ではなくデスクトップの慣習を実装しています:

1. 塗り色の上で `_MIN_CONTRAST`（4.5:1）を満たすなら白文字。
2. 相対輝度が `_LIGHT_FILL_LUMINANCE`（0.45）を超える塗り色（黄色やパステル系のアクセント）では黒文字 — そのほうが自然に読めます。
3. どちらでもない場合は白文字のまま、色相と彩度を保って HSV の明度を段階的に下げ、基準を満たすまで塗り色を暗くします。

`_normalise_selection` はこれを Active・Inactive・Disabled のカラーグループに**無条件で**適用します — 閾値を下回った場合だけではありません。Windows の既定値は素朴な閾値判定を通過してしまうにもかかわらず、報告された問題そのものだからです。

スタイルによって `CE_ItemViewItem` の描画方法が異なる（Windows 11 スタイルは単純に `Highlight` で塗りつぶすわけではない）ため、パレットの設定だけでは実際にその組が使われる保証がありません。`item_view_qss` はさらに、`QTreeView`/`QListWidget`/`QListView`/`QTableView` を対象としたアプリケーションスタイルシートで、`:active` と `:!active` の両方の状態について塗り色と文字色の双方を明示的に固定します。

**意味色。** `ThemeColors` は各フィールド名が**役割**を表す frozen dataclass（`file_dirty_fg`、`diff_changed`、`syntax_keyword`、`banner_bg` など）で、`_LIGHT` と `_DARK` の 2 つのインスタンスを持ちます。利用側は import 時にキャッシュせず、描画・生成のタイミングで `colors()` を呼びます。これがテーブル差し替えを可能にしています。押さえておくべき点が 2 つあります:

- `_build_diff_bar` の差分凡例のスウォッチと `FoamTreeModel` の差分行背景は**同じ**フィールドを読むため、両者が食い違うことはありません。
- `model/tree_model.py` と `ui/widgets/_foam_highlighter.py` はどちらも `ui.theme` を import します。これはテーブルを二重管理する代わりに、レイヤリングの意図的な例外としています（`ui/theme.py` は PySide6 以外に依存しないため循環参照は生じません）。

**凡例バーが独自の塗り色を持つ理由。** 差分凡例は、見た目上は共有しそうな `banner_*` の通知色ではなく、`legend_bg`/`legend_fg`/`legend_border` でスタイル指定されています。このバーは 3 つの差分スウォッチを**載せる**ため、その塗り色はすべての `diff_*` 値から離れている必要があります。`banner_bg` を使っていた間、ダークテーブルでは `banner_bg == diff_changed == #4A4526` となっており、「changed」のスウォッチは自分が載っているバーに溶け込んで見えませんでした。スウォッチの背後に描画されるものはすべて同じ制約を受けます。これは `test_diff_swatches_are_visible_on_the_legend_bar` が両テーブルに対して検証するようになりました。

**3D ビューア。** VTK はパレットを持たず自前でテキストを描画するため、必要な色はすべて明示的に命名され（`viewport_bg`、`viewport_text`、`viewport_grid`、`viewport_label_fg`/`_bg`、`viewport_vertex_label_fg`、`viewport_block_label_fg`）、`block_mesh_panel.init_plotter` と `block_mesh_renderer` で `colors()` 経由で読まれます。ダークの `viewport_bg` はパネルのほぼ黒ではなく中間的な暗い青灰色（`#2E3238`）です — メッシュとオーバーレイは彩度の高い中間調で描画されるため、極端に暗いシーンでは色相が失われるからです。`viewport_geometry_opacity` は色ではなく**倍率**です — 半透明の面は背景に向かってブレンドされるため、白を前提に調整した alpha はダークでは濁ります。`_opacity()` がこれを適用し 1.0 でクランプします。パッチやオーバーレイの色相自体（`_PATCH_COLORS`、`_ACTION_COLORS` など）は、装飾ではなく意味を担うため、意図的にテーマ非依存のままにしています。

モデルが返す `ForegroundRole` は選択行の色付けには使えません: `QStyledItemDelegate.initStyleOption` はそれを `palette.Text` にコピーしますが、`QCommonStyle` は選択行を `HighlightedText` で描画するため、上書きは画面に反映されません。

`tests/ui/test_theme.py` は、コントラスト計算、慣習ルール（`#0078d4` を明示的に指定した回帰テストを含む）、どのアクセントカラーでも判読不能な組が生じないことを確認する走査、両テーブルのすべての前景色がそのテーマの `Base` に対して 3:1 を下回らないこと、上述のスウォッチと凡例バー塗り色の分離、およびビューアのテキスト色が `viewport_bg` に対して 3:1 を下回らないことを検証します。ただしこれらはテーブルレベルの検査です — 「成立し得ない色」は捕捉できますが「その場で見て違和感がある色」は捕捉できないため、3D ビューアを変更した際は実際のシーンを目視する価値があります（下記参照）。

VTK パネルを目視確認のためにレンダリングするには実際の X ディスプレイが必要です — `QT_QPA_PLATFORM=offscreen` では `QtInteractor` が `BadWindow` で異常終了し、またネイティブ子ウィンドウであるため `QWidget.grab()` は黒画像を返します。シーン自体のキャプチャには `plotter.screenshot(path)` を使ってください。

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

**テキストを描画するのは Qt ではなく VTK** — 3D シーン自身のテキスト（形状名バッジ、頂点番号とブロック番号、範囲表示、方位軸の文字、グリッドの目盛りラベル）は VTK の組み込みラベルフォントで描画され、Qt が使うデスクトップのフォントスタックとは別物です。このフォントはグリフを持たない文字に対して**何も描画しません** — 代替の四角い枠さえ描きません — そのため Qt のメニューでは正しく見える記号が、3D ラベルの中では幅だけを占めて消えることがあります。2026-07-30 まで 2 か所が実際にそうなっていました: `_CLIP_MARK_SUFFIX` の `✂`/`⚠` と、**Dimensions** の範囲表示で各軸の 2 つの数値を区切っていた `→` で、後者は画面上では `X  0   3  (3 m)` になっていました。角括弧も同様に不可で、丸括弧として描画されます。`block_mesh_renderer.py` 内のすべての文字列は ASCII に限定してください。`tests/ui/test_block_mesh_renderer_topo.py` がモジュールの AST を走査して（docstring を除き）まさにこれを検査します。範囲表示はインラインの f-string だったため、定数ごとの検査では見逃されていたからです。ただしこのテストが捕捉できるのは「描画できない文字」であって「見た目が不適切な文字」ではないため、新しく追加したシーン表示は画面で確認してください — グリフの欠落は `assert` では検出できません。なお `block_mesh_panel.py` の `▾`・`·`・`📍`・`…` は対象外です。これらは Qt のウィジェットテキストです。

**サイドバイサイドモード** — `⊞` トグルボタン（`_bm_side_by_side_btn`）が `QTabWidget` のコーナーウィジェットとして追加されます。有効化すると `_on_toggle_bm_side_by_side` が `block_mesh_panel` を `upper_tabs`（`QTabWidget`）から `_tree_bm_splitter`（`right_upper_splitter` をラップし Tree タブのコンテンツとなる `QSplitter(Qt.Horizontal)`）へ再ペアレント化します。リペアレント前にまず Tree タブへ切り替えてスプリッターを可視状態にし、`setSizes([1,1])` と `_init_plotter()` は `QTimer.singleShot(0, ...)` で次のイベントループティックまで遅延させます。サイドバイサイドモードを切ると `block_mesh_panel` は通常タブとして `upper_tabs` に戻されます。`_update_bm_side_by_side_btn`（`ui/mixins/_panel_ops.py`）は、現在のファイル名が `blockMeshDict`・`topoSetDict`・`snappyHexMeshDict`・`setFieldsDict`、またはサンプリング名（`SAMPLING_DICT_NAMES`: `controlDict`・`sample`・`probes`・`surfaces`・`singleGraph`）のいずれか（いずれも同じ 3D ビューに描画される — `block_mesh_extractor.py`、`topo_set_extractor.py`、`snappy_hex_mesh_extractor.py`、`set_fields_extractor.py`、`sampling_extractor.py` を参照）で、BlockMesh タブ自体が有効、かつ xterm が非アクティブなときにボタンを有効化します。それ以外はボタンを無効化し、サイドバイサイドモードが有効であれば強制的に解除します。

**比較パネルの表示制御** — `comparison_panel` は起動時に `right_upper_splitter` へ追加されますが直後に非表示（`comparison_panel.hide()`）になります。`QSplitter` は非表示の子ウィジェットを無視するため、ハンドルや隙間は表示されません。`_on_side_by_side_toggled(True)` では `setSizes` 前に `comparison_panel.show()` を呼び、`_on_side_by_side_toggled(False)` と `_clear_diff` では `comparison_panel.hide()` を呼びます。

**プレビューモード** — `BlockMeshPanel` は `update_block_mesh()` 呼び出しごとに設定される 2 つのフラグを持ちます: `_has_variables`（`vertices` の raw_list 値に `$` 文字が含まれる場合 True）と `_preview_mode`（デフォルト False、**Preview** ボタンでトグル）。`_has_variables` が True の場合、Vertices グループボックス内のテーブル上部に `_vtx_info_bar`（琥珀色の **⚙ Variable-based** チップ + **Preview** トグルボタン）が表示され、X/Y/Z セルは読み取り専用になります（`rw_flags = ro_flags`）。`_preview_mode` が True の場合はセルが編集可能になり、`_on_cell_changed` は `vertices_changed` を emit する代わりに `_render()` を直接呼び出してツリーとファイルを変更しません。`_on_refresh()` はプレビューモード中に `self._root` から再抽出してから `_render()` を呼び出し、頂点データのリセットとプレビュー終了を同時に行います。

## スクリーンショットの撮影

`docs/SCREENSHOTS.md` のギャラリーは、`tools/screenshot_specs.json` のショット一覧をもとに `tools/capture_screenshots.py` が撮影します。手作業で撮った画像は古くなるためです。メインウィンドウのショットは 2026 年 5 月から 2026-07-30 まで撮り直されず、その時点では Tools メニュー・キーフィルタ入力欄・case root と included files のグループが写っていませんでした。1 つの spec に対して `--theme` を変えて 2 回実行すれば、色以外がまったく同一の light/dark ペアが得られます。

```bash
DISPLAY=:1 python3 tools/capture_screenshots.py --all                    # ギャラリー全体、両テーマ
DISPLAY=:1 python3 tools/capture_screenshots.py main-window-tree-editor --theme dark --out /tmp/shots
python3 tools/capture_screenshots.py --list                              # spec が定義しているショット
DISPLAY=:1 python3 tools/capture_screenshots.py <shot> --interactive     # 手で調整し、その状態を JSON で出力
```

**実際の X ディスプレイが必須です。** オフスクリーン Qt では VTK が abort するため、ヘッドレスモードはありません。`--out` のデフォルトは `docs/images/` なので、最初の実行は別のディレクトリに向けてください。

**撮影は Qt ではなく ImageMagick 経由で行います。** `QWidget.grab()` は BlockMesh パネルのネイティブ子ウィンドウを黒く返す（前節の GPU の注意と同じ原因）ため、`import -frame -window <winId()>` でウィンドウを撮影します。`-frame` は既存のギャラリー画像と同じくタイトルバーと枠を含むため、1200×800 のウィンドウが同じ 1228×866 になります。ウィンドウ ID は `QWidget.winId()` から得るので、ウィンドウマネージャへの問い合わせやタイトル一致は不要です。ただし `import` は*画面*を読むため、ウィンドウは (0, 0) に移動して前面に出します。重なっているウィンドウがあればそれが写ります。

**`app_config.json` には何も書き戻しません。** テーマは保存済み設定ではなく `--theme` から来ます（通常起動でも `main.py` の `--theme` が同じ働きをします）。言語は英語に固定し、ウィンドウは決して閉じません。ウィンドウサイズを保存するのは `MainWindow.closeEvent` なので、これを呼ばないことが撮影でユーザー設定を変えないための要点です。

**ショット × テーマごとに 1 プロセス。** スクリプトは自分自身を再実行（`--_worker`）するため、前のショットの状態を引き継ぐことがありません。各ワーカーは `os._exit` で終了します。VTK は `shutdown()` を正しく呼んでもインタプリタ終了時に abort することがあり、成功した撮影が失敗として報告されてしまうためです。

### spec が固定するもの・固定しないもの

ショットの `state` は `WindowState`（`ui/window_state.py`）です。フィールド一覧は同モジュールの docstring を参照してください。 spec の読み込みと適用は **strict** 経路を通ります。この方針は維持してください: 未知のフィールド、存在しないタブラベル、spec の知らないうちに改名されたツリー行は spec 側の不具合であり、間違ったウィンドウを黙って撮影するくらいなら失敗したほうがましです。隣にある寛容な経路（`load_saved_state`、`apply_window_state(..., strict=False)`）は `ui/session_restore.py` のものであり、誤って使ってしまいやすい点に注意してください。spec の `defaults` はすべてのショットの下敷きになります。`case_dir` にはリポジトリルートを表す `{repo}` と、撮影マシンの OpenFOAM 実行ディレクトリを表す `{cases}`（`--cases-dir` または `$FODE_CASES_DIR`）を使えます。ギャラリーが使うチュートリアルケースはリポジトリ外にあるためです。

固定するのは「選択」だけです。選択行の祖先を超えるツリー展開、スクロール位置、エディタのカーソルと折りたたみ状態、詳細パネルの内容は、開いているファイルと選択行から導かれます。そのため spec は選択のみを固定し、残りは追従させます（それで足りるショットを選んでいます）。`tree_expand` だけが例外で、選択せずに開いておきたい行のためにあります。

spec で間違えやすい点が 2 つあります。

- **`preload_files`** — 3-D ビューアは読み込んだ辞書のジオメトリを蓄積するため、`snappyHexMeshDict` のオーバーレイがブロックメッシュの中に描かれるのは `blockMeshDict` も開いた場合だけです。3-D のショットはすべてこれをプリロードします。
- **`block_mesh_visible`** — ターミナルを xterm から切り替えると **View > BlockMesh 3-D Panel** のメニュー項目は有効化されますがチェックは付かないため、タブは自動では戻りません。3-D パネルが必要なショットは明示的に指定します。

### 比較モード

ショットは `state` と並べて `compare_with` キーを持つことができ、比較モードの参照ケースを指定します。これは意図的に `WindowState` のフィールドにしていません。あのデータクラスは `ui/session_restore.py` と共有されているため、そこにフィールドを足すと保存済みセッションが復元する内容が変わってしまい、それはスクリーンショットの都合ではなく製品としての判断になるからです。加えて、比較モードは `WindowState` が保持する「選択」ではなく「結果」の側です — 比較を開始すると side-by-side が強制的にオンになります。そこでツールは `MainWindow._start_comparison_with` を呼びます。**Case > Compare with Case…** と Find Examples ダイアログが使うのと同じ入口なので、ショットには実際の動作がそのまま写ります。

`apply_window_state` の内部ではなく後で呼ぶことから、2 つの帰結があります。ファイルごとの差分数はゼロタイマーで事前計算されるため、ファイル一覧のマーカーが現れるまでにイベントループを 1 回まわす必要があります。また比較を開始すると参照ペインの非表示が解除され、Qt がスプリッタの領域を配分し直すため、固定したいサイズは後からもう一度、スプリッタだけを適用し直します。

**比較ショットは 2 つのケースをどちらも `$HOME` の外に置く必要があり**、そのため `{repo}` ではなく絶対パスを書いています。差分バーが参照ケースのフルパスを画像に出力するのに対し、このリポジトリはホームディレクトリ配下にあるためです。ルールも理由も `capture_dialog.py` のログ要約用ケースと同じです:

```bash
mkdir -p /tmp/OpenFOAM/run && cp -r tutorials/cavity/cavity tutorials/cavity/cavityGrade /tmp/OpenFOAM/run/
```

サイズは `QSplitter.saveState()` / `QWidget.saveGeometry()` の blob（JSON では base64）として持ち運びます。ピクセル値の一覧と違い、これは正確に往復し Qt のバージョンをまたいでも有効です。ただし blob は手で書けないため、`splitter_sizes`（`setSizes` に渡す素のピクセル幅）が記述用の形式です。これは選んだときの `window_size` と同じ精度しか持たないため、両者は必ずセットで固定します。

カメラは `plotter.camera_position`（`(position, focal point, view up)`）で、3 つの 3-tuple として往復します。`BlockMeshRenderer.render` の最後が `reset_camera()` であるため、最後の描画の*あとに*適用する必要があります。`apply_block_mesh_view` が単独で呼べるのはこのためで、ツールは settle 待ち後にもう一度呼びます（ターミナルモード切り替え後に遅延実行される VTK の再初期化がその待ち時間の中で走ります）。

### ダイアログ

ダイアログはメインウィンドウのフレームの一部ではなく、それ自体が独立したトップレベルの X ウィンドウです。そのため `MainWindow` 1 つに `WindowState` を適用して撮影する `capture_screenshots.py` からは手が届きません。もう半分を担うのが `tools/capture_dialog.py` です:

```bash
DISPLAY=:1 python3 tools/capture_dialog.py --all
DISPLAY=:1 python3 tools/capture_dialog.py log-summary --out /tmp/shots
python3 tools/capture_dialog.py --list
```

ショットは JSON spec ではなくモジュール内の `DIALOG_SHOTS` 辞書に置いています。ダイアログは型付きの Python 引数から構築するものであり、この規模でそれをスキーマで表現しても得るものがないためです。それ以外は上記と同じルール・同じ理由に従います: 保存された設定ではなく `--theme` と英語固定の言語、`QWidget.grab()` ではなく `import -frame`、`app_config.json` へは一切書き戻さないこと。

**ショットに撮影者のユーザー名を写り込ませてはいけません。** ログ要約はログファイル自身の `Case:` 行をそのまま再現するため、ホームディレクトリ配下で実行したケースはそのパスを画像に印字してしまいます。`DEFAULT_CASE` を `/tmp/OpenFOAM/run/pitzDaily` にしているのはこのためで、次の手順で用意します。チュートリアルは決定論的なので、どのマシンでも同じ数値になります:

```bash
mkdir -p /tmp/OpenFOAM/run && cp -r "$FOAM_TUTORIALS/incompressible/simpleFoam/pitzDaily" /tmp/OpenFOAM/run/ && cd /tmp/OpenFOAM/run/pitzDaily && blockMesh > log.blockMesh 2>&1 && simpleFoam > log.simpleFoam 2>&1
```

同じルールは今後追加するショットにも適用されます。コミット前に画像へ `/home/<name>` が写っていないか確認してください。`find_foam_example.png` はこのルールより前の画像ですが、たまたま条件を満たしています。ユーザー名が `user` のマシンで撮影されており、写っているパスもインストール先の `/usr/lib/openfoam/openfoam2606/...` だけであるためです。

各ショットは `build` と対になる `requires` を持ちます。`requires` は「このマシンにショットが読むものが揃っているか」に答え、足りないものを名指しして例外を送出します。これを `build` から分離しているため、`QApplication` なしにその判定ができ、結果としてテストで検証できます。2 つのショットは撮影マシン側が用意するもの（実行済みケース、OpenFOAM インストール）を読みますが、`run-tool` は同梱の `tutorials/damBreak` を読みます。このショットが見せたい「`0/` を復元する」前置きは、`0.orig/` を持つケースでしか現れないためです。つまりこのショットの入力はチェックアウトに同梱されています。

`run-tool` ショットは、`ui/mixins/_tools_ops.py` が渡すのと同じ警告文と前置き文字列を `RunToolDialog` に渡します。import ではなくコピーしているのは、それらがミックスイン内のインラインなリテラルであり、参照するには `MainWindow` を立ち上げる必要があるためです。テストスイートがそれらの文字列が当該ファイルに今も存在することを検証するので、アプリが決して表示しないダイアログをギャラリーが見せてしまうことはありません。

構築時点では内容が揃わないダイアログには `prepare` フックがあります。`show()` の後に呼ばれ、イベントループを回すための `pump(ms)` が渡されます。これが必要になったのが `find-examples` です: 検索が `QThread` で走るため、ショットはクエリを入力し、検索を開始し、結果ツリーが埋まるのを待ち（上限付き — キャプチャがハングしてはいけません）、続いて結果を 1 つ選択してプレビューを表示させます。このフックは `FindExamplesDialog` のプライベートなウィジェットを直接触ります。製品側のダイアログにキャプチャ専用のアクセサを足さないための引き換えです。参照している名前は `tests/tools/test_capture_dialog.py` で固定しているため、リネームは X ディスプレイを要するキャプチャ実行の途中ではなく、テストスイートで失敗します。

`capture_screenshots.py` と同様、このツールもショットごとに自身を再実行します（`--_worker`）。あちらの理由は「どのショットも直前のショットの状態を引き継がないこと」ですが、こちらにはより強い理由もあります。`QApplication` はシングルトンであり、同一プロセス内で 2 つ目のショットが QApplication を持つことはできません。

### 対象外

`tools-menu.png` には spec もショットもありません。開いたメニューは独立したウィンドウでもメインウィンドウのフレームの一部でもなく、フォーカスが移った瞬間に閉じるポップアップであるため、ギャラリーで唯一、従来どおり手作業で撮影する画像です。

spec は `light` で撮影し、`system` は使いません。system テーマのウィンドウは撮影マシンのデスクトップパレットを継承するため、他の環境で再現できない唯一の要素になります。ギャラリーの light 画像は 2026-07-30 まで `system` モードで手作業撮影されていました。現在の画像で選択行の塗りがデスクトップのアクセントカラーではなく FoDE 自身の青になり、ウィジェットがデスクトップのスタイルではなく Fusion になっているのはこのためです。

## デモ動画の収録

`docs/DEMO_SCRIPTS_ja.md` の動画は、`tools/demo_specs.json` のシーン定義をもとに `tools/demo_driver.py` が操作・収録します。`capture_screenshots.py` の姉妹ツールで、出発点も同じです。シーンの `state` は同じ `WindowState` で、同じ `defaults` を下敷きにします。その上に、`ffmpeg` で収録しながらウィンドウを操作する `steps` のリストが加わります。

```bash
python3 tools/demo_driver.py --list                                            # spec に定義されたシーン一覧
DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end                    # リハーサル: 操作のみ、収録なし
DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end --record out.mp4   # 収録
DISPLAY=:1 python3 tools/demo_driver.py damBreak-end-to-end --stage            # 開始状態にしてウィンドウを手渡す
```

スクリーンショットツールが必要とする X ディスプレイに加えて、`ffmpeg`・`xdotool`・`Xephyr`（`xserver-xephyr`）が必要です。

**ステップは実際の X 入力です。** `xdotool` がポインタを動かしてクリックするため、アプリは通常のマウス・キーボードイベントを受け取り、収録映像には実際のカーソルが実際のホバー状態の上を動く様子が写ります。アプリ内部に手を入れてクリックを偽装する処理はありません。カーソルはターゲット間をイーズインアウトの曲線で移動し、瞬間移動はしません。ステップはターゲットを意味的に指定し（メニュー項目、キーパスで指定したツリー行、ファイル行、ラベルで指定したボタン）、それが画面上の座標に解決されるのは**ステップの実行時**です。メニュー項目は、その前のクリックでメニューが開くまで存在しないからです。

**収録は専用のネストされたディスプレイ上で行われます。** 実際の入力は、ウィンドウマネージャが最前面に置いたウィンドウと、フォーカスが移った先に届きます。使用中のデスクトップではそれは誰かのエディタであり、収録は不安定かつ迷惑なものになります。実際にテスト中に起きた失敗は、チャットウィンドウが自分を最前面に上げてクリックを奪い、次のステップが辞書の値をそこにタイプするというものでした。そのため、ドライバは Xephyr サーバを起動してその中で実行し、終了後に停止します。誰も操作していないマシンでは `--on-this-display` で無効化できます。`--stage` は決してネストしません。人にウィンドウを手渡すことがその目的だからです。副次的な利点として、ネストされたディスプレイにはウィンドウマネージャがないため装飾がなく、収録されるのはアプリケーションだけになります。

**ステップはネストしたイベントループではなく `QTimer` チェーンで実行されます。** モーダルダイアログは自前のイベントループを回すため、`QEventLoop` を回して待つドライバは、自分が開いたダイアログの上でブロックし、それを閉じるステップを待ち続けることになります。タイマーはダイアログのループの中でも発火するので、チェーンは進み続けます。同じ事実は終了時にもう一度効いてきます。`app.quit()` は最も外側のループしか終わらせないため、ダイアログを開いたまま止まった収録は、終了前にそれを閉じます。さもなければハングします。

チェーンは*アトム*（解決・移動・クリック）のキューで、`push` はそれらを**先頭**に積みます。これにより、あるアトムが後続より前に実行される処理を予約できます。この順序をわざわざ書き残すのは、逆にしたときに何も言わずに壊れるからです。移動を積んでからクリックを積むクリックステップは、クリックが**先に**、そのときポインタがあった場所で実行され、収録はほぼ正しく見えたまま進んでしまいます。

**収録のたびにケースは新しくコピーされます。** シーンは `case_source` と `workdir` を指定し、ウィンドウを開く前に無条件でコピーされます。前回の収録の残骸（すでに生成されたメッシュ、すでに設定された `0/`）から始まった収録は、台本と違うものを記録します。また `blockMesh` を実行するシーンは、そうしなければリポジトリの `tutorials/` を汚します。`terminal_prelude` は収録開始前のステージング時に OpenFOAM 環境を Terminal タブに読み込ませます。シェルの設定作業を見せることはデモではないからです。`clean` はその対になるもので、ステージングがコピーするものではなく*ステップ*が作るものを対象にします。ケースを複製するシーンは `case_source` にも `copy_also` にも書かれていないディレクトリを作るので、前回の収録のものが残っていると次のステップが「上書きしますか？」のダイアログになってしまいます。`prepare_case` はリポジトリ内のパスの削除を拒否します。

**`app_config.json` も収録ごとに新しくなります。** `seed_app_config` が workdir にスクラッチの設定ファイルを書き、`MainWindow` を組み立てる前にシングルトンをそちらへ向けます。理由は 2 つあり、2 つめがすべてのシーンで実行する理由です。収録が収録者の設定を*書いて*はいけません。「複製したケースを開きますか？」に Yes と答えると、その途中で新しい既定ケースディレクトリが保存されます。ウィンドウを閉じないだけでは防げません。そして収録が設定を*読んで*もいけません。機能フラグ、既定のケースディレクトリ、ケースライブラリはすべてこのファイル由来なので、そうしなければある機械で撮った動画が別の機械では違う場所を開くことになります。

`case_library` はその上に乗ります。指定したディレクトリが、ケースライブラリの唯一の項目になります。同時に `$FOAM_TUTORIALS` にも代入します。`get_case_library_dirs` はこの変数を登録済みリストの先頭に足すので、項目が 2 つあるとファイル選択の前に「どちらのライブラリを見るか」を訊くダイアログが出てしまい、その中身は収録シェル次第になるからです。同じディレクトリを指させれば 2 つは 1 つに畳まれます。変数を消すのではなくこの向きにしているのは、`paraFoam` が OpenFOAM 環境の残りを必要とするためです。

**ネストされたディスプレイには 2 つの代償があり、いずれもドライバ側で処理しています。** 閉じたメニューはピクセルを画面に残し、自力で再描画しないものの上に居座ります。3D ビューは VTK が描き直すので影響を受けず、結果としてエディタの上にメニュー型の穴が残り、そこに何かが描かれるまで消えません。`repaint()` でも `xrefresh` でも動かせませんが、1 ピクセルのリサイズなら消えます。内容だけでなく全ウィジェットのジオメトリを無効化するからです。ポップアップを閉じたステップの後にこれを実行しています。もう 1 つ、収録では Qt 自身のファイルダイアログを強制します（`AA_DontUseNativeDialogs`）。デスクトップのポータル製ファイル選択ダイアログは別プロセスなのでウィジェットに一切手が届かず、キーボードショートカットもデスクトップごとに異なります。さらにホームディレクトリを開いた状態で上部にユーザのアカウント名を表示するため、公開する動画には映せません。

**収録はハングしません。** ステップが送出した例外はすべて収録を終了させます。メッセージとともに、そのとき画面に何が表示されていたかのスクリーンショットも残ります。メニュー項目の改名でターゲットを見失った状態は、外から見るとこう見えます。それ以外の理由で止まった収録はウォッチドッグが終了させます。止まった収録はディスプレイを占有したまま何も報告しないからです。

細かい点が 2 つ、いずれも痛い目を見て分かったものです。`xdotool mousemove --sync` は、ポインタが**現在いる位置**への移動では決して発生しないモーションイベントを待ち、数秒間ブロックします。イージングによって、ゆっくり動く区間の複数ティックが同じピクセルに丸められるため、移動しない移動はスキップしなければなりません。もう 1 つ、ステップのマウスボタンは `button` ではなく `with` です。`button` はすでにターゲット（クリックするプッシュボタンの名前）だからです。

スクリーンショットツールがユーザの設定を汚さないために行っていることは、すべてそのまま当てはまります。テーマは保存された設定ではなく spec から取り、言語は英語に固定し、ウィンドウを閉じないので `closeEvent` が `app_config.json` を書くこともなく、VTK の後始末がクリーンな `shutdown()` の後でも abort しうるためプロセスは `os._exit` で終わります。

**1 つだけ、FoDE 以外のアプリケーションを操作するシーンがあります。** `cavity-full-workflow` は ParaView で終わります。ParaView は意味的には何も解決できないので、そのクリックは `point` ステップ、つまりリハーサルのスクリーンショットから読み取ったピクセル座標です。収録が既知のサイズでウィンドウマネージャのないディスプレイ上で行われ、ParaView が毎回原点に 1280×800 で開くからこそ成立しています。このシーンはさらに、OpenFOAM を source したシェルからドライバを起動する必要があります。`_on_open_paraview_clicked` は `PATH` 上の `paraFoam` を探し、無ければエラーにせず何も読み込んでいない素の `paraview` にフォールバックするからです。ネストされたディスプレイ上で ParaView を描画させるのは `LIBGL_ALWAYS_SOFTWARE=1` です。どちらも `docs/DEMO_SCRIPTS_ja.md` の「収録」節にあります。収録する人が見るのはそちらだからです。

## テスト

```bash
python3 -m pytest -q
```

`pytest -q` だと import 周りで問題が出る場合は、プロジェクトルートの扱いが安定しやすい `python3 -m pytest -q` を使う方が安全です。

`tests/test_lint.py` はテストスイートの一部として `ruff` と `mypy` を実行するため（後述）、`pytest -q` を実行するだけで lint / 型チェックの regression も検出できます。

## Lint と型チェック

設定は `pyproject.toml` にあります。`ruff` はリポジトリ全体を対象とします（`.venv/` などの ruff 自身の既定の除外を除き、`include`/`exclude` 制限はありません）。リポジトリ全体がクリーンなので、スコープ指定なしで実行します。

```bash
ruff check
```

`i18n/ja.py` の翻訳文字列リテラル（英語の `tr()` キーとその日本語訳文）は、`pyproject.toml` の `[tool.ruff.lint.per-file-ignores]` により `E501`（行長超過）の対象から除外されています。どちらを折り返しても、キーの参照が壊れるか、翻訳文が変わってしまうおそれがあるためです。

`mypy` もリポジトリ全体を対象とします。`pyproject.toml` の `[tool.mypy] files` には `foam/`、`model/`、`app_config/`、`schemas/`、`services/`、`ui/`(すべて)が列挙されています。`ui/` 内の PySide6 属性アクセスはすべて、スタブが要求する完全修飾形の enum(`Qt.Horizontal` のようなフラット形ではなく `Qt.Orientation.Horizontal`)を使用しています — この2つのスタイルを混在させることが、PySide6 コードベースにおける `mypy` ノイズの最大の原因になります。

```bash
mypy
```

`[[tool.mypy.overrides]]` の設定で `numpy.*`/`numpy` を `follow_imports = "skip"`(および `follow_imports_for_stubs = true`)に緩和しています。numpy に同梱されたスタブは `python_version >= 3.12` でしかパースできない PEP 695 の `type` 文を使用しており、本プロジェクトの `python_version = "3.10"`(サポートする最小ランタイム)ターゲットと衝突するためです。`ui/panels/block_mesh_*.py` の `vtk`/`pyvista`/`pyvistaqt` はスタブが一切存在しないため `ignore_missing_imports = true` にフォールバックし、それらのオブジェクトは `Any` として扱われます。

### `ui/mixins/` 分割の型付け

`ui/main_window.py` の `MainWindow` は 13 個の mixin と `QMainWindow` から構成されています(上記「プロジェクト構成」の `ui/mixins/` の項目を参照)。各 mixin はランタイム上は共通の基底クラスを持たないただのクラスであり、実際の合成は `MainWindow` がそれらすべてを継承した時点で初めて成立します。これは `mypy` にとって問題です。`mypy` は各 mixin モジュールを単独で型チェックするため、素の `class _FileOpsMixin:` では `self` がいずれ `.tree` や `.state`、`._load_tree()` を持つことを知る術がありません。

`ui/mixins/_protocol.py` の `MainWindowProtocol`(`QMainWindow` を継承する通常のクラスであり、`typing.Protocol` ではありません — mypy は非 protocol を基底に持つ protocol を拒否します)が、その結合済みの全体像を宣言しています。`MainWindow.__init__`/`_build_ui()` が設定するすべてのウィジェット/状態属性、そしてどの mixin が定義するメソッドも、実物と一致するシグネチャで宣言されています。各 mixin は次のようにします:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui.mixins._protocol import MainWindowProtocol as _Base
else:
    _Base = object

class _FileOpsMixin(_Base):
    ...
```

こうすることで、mypy が見ている間は `_Base` は `MainWindowProtocol`(そのファイル内のすべてのメソッドに完全な属性/メソッドの全体像を与える)になり、ランタイムでは単なる `object`(無害な基底クラスで、mixin の実際の MRO、ひいては `MainWindow` 自体の MRO も変わらない)になります。`ui/mixins/_protocol.py` は `ui.main_window` や `ui.mixins.*` のどのモジュールもインポートしてはいけません。それをしてしまうと、mixin の `TYPE_CHECKING` 用の基底クラスが、ランタイムでは mixin 自身を継承するクラスを継承することになり、単なる循環 *インポート* ではなく本物の継承サイクルになってしまい、mypy はこれを問答無用で拒否します。他の mixin から呼び出されるメソッドを mixin に追加する場合は、`MainWindowProtocol` にも同じシグネチャを追加してください(ここでスタブのシグネチャが一致していないと、mixin 側の本物のメソッドに「スーパータイプと非互換」という見せかけのエラーが出ます)。

`foam/nodes.py` の `NodeType` という `Literal` が、有効な `node_type` 値の確定的な一覧です。この集合に含まれない値への代入や比較は `mypy` が検出します。各値の意味は上記の「ノード型」セクションを参照してください。

## 更新候補

将来のリリースに向けたメモ（現時点では未計画）:

- **比較モードでのサイドバイサイドの参照*テキスト*エディタ** — 比較モードは現在、参照ケースを読み取り専用の*ツリー*として表示している。参照ファイルのテキストを読み取り専用エディタとしてメインの Editor タブの横に表示できれば、キーや値を自由にコピー＆ペーストできる（現状、例のケースについては非モーダルな Find OpenFOAM Examples のプレビュー + 「選択範囲をコピー」で代用できるが、任意の参照ケースには使えない）。比較モードの更新の一環として再検討する。
- **`foam/parser.py` の 4 つの括弧ブロック振り分けテーブルの統合** — `_NAMED_BLOCK_PARAMS`、`_ANONYMOUS_BLOCK_PARAMS`、`_OPTIONAL_NAMED_BLOCK_PARAMS`、`_POSITIONAL_BLOCK_PARAMS` はそれぞれ `(...)` で区切られたブロックに対する異なる先読み/振り分け経路を担っている。個別に参照される 4 つの辞書ではなく、先読みフラグ付きのエントリ名をキーとする 1 つのテーブルにまとめられる可能性がある。
- **3D のピッキング → ツリー** — ツリー → 3D の方向は実装済み（後述の「ブロックの選択と CRUD」を参照）。逆方向、つまりビューア上でブロックをクリックして該当ツリー行を選択する機能は、本コードベースで初の VTK ピッキング利用になる。
- **その他の位置指定リストに対する CRUD** — 追加/複製/削除は `block_entry` 行では有効になったが、`region_entry`、`boundary_entry`、`action_entry` は引き続き親が `dictionary` であることを条件としている（`ui/mixins/_tree_crud_ops.py`）。この 3 つは*名前付き*であり、新規追加エントリの名前を与える手段（プロンプト、またはプレースホルダに対するインライン編集）がそれぞれ必要になるため、ブロックと一緒には対応していない。
- **セル数/グレーディングの `block_entry` 子ノード化** — 現状は value 文字列に保持している（ノード型テーブル参照）。3D パネルでのブロックごとのセル数表示など、参照する機能が生まれた場合は、再生成する `value` と併存する名前付き子ノードという形で追加できる。
- **`block_mesh_extractor.py` のレガシーな生テキスト境界ブロックフォールバック（~164〜250 行目）の去就の判断** — 到達可能性は推測ではなく実測済み。v2512 tutorials の `blockMeshDict` 489 件のうち、この経路に到達したのはちょうど 1 件（`compressible/rhoPimpleFoam/laminar/helmholtzResonance`）で、しかもそこでの出力は*誤っていた*: 正規表現ベースの走査が先頭の `#include` をパッチ名として読み、次のパッチの面をそれに割り当てて `outlet` を失っていた。このトリガーはパーサ側で修正済み（`boundary ( … )` 内のディレクティブは `ParseError` ではなく `directive_entry` の子ノードになる）のため、フォールバックはコーパス全体で 0 ヒットになった。ただしデッドコードだと証明されたわけではなく（他の理由で構造化パースに失敗した `boundary` ブロックの受け皿としては残る）、テストのない受け皿を残すか、削除してそうしたファイルを目に見える形で劣化させるか、が残された論点。
- **インクルードの再帰的解決** — `services/include_scan.py` は `list_case_files` が返したファイルから 1 段階だけインクルードを辿る。訪問済み集合を持つ深さ制限付きの再帰が素直な拡張形であり、これは机上の話ではない。`compressible/rhoPimpleFoam/RAS/annularThermalMixer` では `constant/caseSettings` 自身がインクルード対象であるため、その中の `#include "<constant>/boundaryConditions"` は辿られず、`constant/boundaryConditions` は一覧に出ない（代わりに `constant` ヘッダーに `[+]` が付く）。`etc/caseDicts/*.cfg` も相互にインクルードし合う。
- **辞書ファイルの gzip 透過読み込み** — `foam/include_resolver.py` は候補を `resolve_optionally_gzipped` に通すため、圧縮された辞書にインクルードが解決し*得る*が、`foam/utils.py` の `read_foam_file` は展開できない。そのため `resolved` と報告しつつファイル一覧からは意図的に除外している。`read_foam_file` に gzip 分岐を入れればこの非対称が解消し、圧縮された `0/` フィールドにも効く。
- **インクルードスキャンの `#codeStream` 本体認識** — `parse_include_directive` の C++ ヘッダー除外（山括弧、`.H` 系拡張子）はヒューリスティックで、v2512 チュートリアルではたまたま過不足なく機能している（当該コーパスでは該当インクルードがすべて `.H` で終わる）。`#{ … #}` の深さ追跡なら厳密だが、安価な行スキャンに留めるべき処理の中で本物の字句解析が必要になる。現状の失敗様態は無害（認識されない対象は単に解決されないだけ）。
- **ディレクティブの統一レジストリ** — `foam/lexer.py` は今も全 `#word` を 1 種類の `DIRECTIVE` トークンに潰しており、`foam/include_resolver.py` がコードベース初のディレクティブ別知識になっている。`#remove`、`#calc`、`#codeStream`、`#eval` とインクルード系を 1 つのテーブルにまとめれば、レキサーの一律トークンとテキストを読み直す 1 モジュールという現在の分裂を解消できる。
- **インクルード解決におけるバージョン対応の `etc` 選択** — `include_scan.foam_etc_dirs()` はケースがどの OpenFOAM バージョン向けかを知り得ないため、ユーザーが明示的にインストールを選ばない限り、古いリリース向けに書かれたケースでも `#includeEtc` は最新の `etc` に対して解決される。ケースの `FoamFile` ヘッダーのバージョンを読むか、ケースごとの選択を記憶すれば驚きを減らせる。
- **パーサに残る 4 つの失敗パターン** — 文法から推論するのではなく v2606 のチュートリアルを走査することで、パーサの不具合を 3 件修正した（エントリの値の中に入った辞書、値を持たないエントリ、キーと開き波括弧の間のコメント）。これによりコーパス上でパースエラーの出るファイルは 288 → 38 に減った。残る 38 ファイル・217 件のエラーはロングテールではなく、明確な形を持つ 4 つの原因に分かれる。いずれも「対応漏れ」ではなく実際のトレードオフを伴うため、意図的に手を付けていない。`/usr/lib/openfoam/openfoam2606/tutorials` の辞書ファイル 4435 件に対する実測値は次のとおり。

  | 原因 | エラー数 | ファイル数 | 主な辞書 |
  |---|---|---|---|
  | `#{ … #}` の逐語コードブロック | 153 | 27 | blockMeshDict, controlDict |
  | 複数行にわたる値の中のコメント | 49 | 11 | fvSchemes |
  | 名前付きエントリを持つ `actions ( name { … } )` | 10 | 6 | setFieldsDict, topoSetDict |
  | field-value リスト中のコメントや裸の語 | 5 | 3 | setFieldsDict |

  **`#{ … #}`** が最大の原因で、これはパーサではなく**レキサ**の欠落である。`foam/lexer.py` には逐語ブロックという概念がないため、`codeExecute #{ … #};` の中の C++ が通常の辞書テキストとしてトークン化される。その波括弧が辞書を閉じ、その `;` がエントリを終わらせ、被害はファイル末尾まで波及する（153 件中 110 件が "unexpected EOF" として現れるのはこのため）。修正は `#{ … #}` を 1 つの不透明なトークンとして出すレキサの状態を追加するだけの追加的な変更だが、ここで実施しないのは、`#{` がディレクティブの一形態であり、レキサが現状すべての `#word` を 1 つのトークンに潰している以上、上記の「ディレクティブの一元的なレジストリ」と併せて扱うべきだからである。

  **複数行の値の中のコメント**は、真にトレードオフのある項目である。`_read_value_text_until_semicolon` は深さ 0 のコメントで値を終わらせる。エントリがそこで終わるなら正しいが、値が次の行へ続く場合は誤りになる。fvSchemes の DEShybrid エントリがまさにそれで、10 行にわたる値の各行に行末コメントが付く。コメントを終端扱いしなければこの 49 件は解消するが、今度は `;` を本当に書き忘れたファイルがローカルに失敗せず EOF まで読み進んでしまう。つまり「正確なエラー」を「広範なエラー」と引き換えにすることになり、きちんとやるには先読みが要る。なお 49 件のうち 30 件は**カスケード**である。実際の発生箇所は 6 か所で、それぞれが再同期に失敗して後続行をエントリとして誤読した結果にすぎない。

  **名前付きの `actions ( … )`** はパースではなく振り分けテーブルの問題である。`actions` は `_ANONYMOUS_BLOCK_PARAMS` に登録されているため `( { … } { … } )` を期待するが、`topoSetDict` は各ブロックの前に名前を置く `( heater { … } )` も許す。これは `_OPTIONAL_NAMED_BLOCK_PARAMS` が `sets`/`surfaces` に対してすでに行っている「名前は任意」の先読みと同じものである。ここで修正せず記載にとどめたのは、上記の「4 つの括弧ブロック振り分けテーブルの統合」に真正面から重なる項目であり、単独で対応すると、その項目が減らそうとしている 4 経路に 5 本目を足すことになるからである。

  なお、これらはラウンドトリップの忠実性には影響しない。4435 件すべてが 3 つの修正の前後を通じてバイト単位で同一に書き戻される。パースに失敗したエントリは `unknown_raw_entry` としてそのまま保持されるためである。損なわれるのはディスク上のファイルではなく、該当エントリのツリー表示とスキーマヘルプ（誤りまたは非表示）である。

- **`block_mesh_renderer._make_shape_mesh` のジオメトリ振り分けの型付け** — 現状は呼び出し側で dict のキー（`box`、`boxes`、`centre`+`radius`、`p1`+`p2`+`radius`、`origin`+`i`+`j`+`k`、`stl_path`、`planePoint`+`planeNormal` など）に対して duck-typing で振り分けており、今回のリファクタでは意図的にそのままにした。型付きのジオメトリ共用体（例: 種類ごとの dataclass）があれば、実行時のキーの有無に頼らず mypy で振り分けをチェックできる。


### 保留中のレビュー指摘（Undo/Redo・サンプリング）

Undo/Redo とサンプリング機能のコードレビューで挙がったが、その時点では未修正のまま残した軽微な項目（いずれも「確定」ではなく「可能性あり」— トリガーが狭い、潜在的、または設計の堅牢化にとどまる、と判断）。これらの領域に次に手を入れる変更に合わせて取り込む価値がある:

- **`_restored_dirty` がダーティ判定のためにディスクを再読み込みしている**（`ui/mixins/_undo_ops.py`）— 当初は「`state.parsed_roots` にキャッシュされた root はノードに `raw_text` がないため、再シリアライズするとディスクと差が出る」という前提で実在の不具合として挙げられた。しかしこの前提は成り立たない: `parsed_roots` への書き込みはすべて `OpenFoamParser.parse()` の結果であり `raw_text` は設定されるうえ、`tools/roundtrip_corpus.py` の実測では v2512 tutorials の 9620/9620 件がバイト単位で一致して再シリアライズされる。加えて `_undo_text_for` は `file_buffers` を優先するため、シリアライズ結果とディスクの比較に到達するのはディスクから直接パースしたファイルのみ。設計上のメモに格下げ: メモリ上のバッファと比較すれば I/O も round-trip 100% への依存も無くせるが、現状のコードが誤動作する入力は確認されていない。
- **`UndoState.op_active` のリセットタイミングが脆い**（`ui/mixins/_undo_ops.py`）— 二重チェックポイント防止ガードを `QTimer.singleShot(0, ...)` でクリアしているが、これはネストしたイベントループ（`QMessageBox`/`QDialog.exec`）内で発火する。現状、`_checkpoint_for_undo` とその変更の間にダイアログを開く呼び出し箇所はないため潜在的だが、将来そのような操作があるとモデルの `about_to_change` が変更途中の 2 つ目のスナップショットを積み（1 回の編集に 2 回の Undo が必要になる）。ガードを同期的な操作スコープに限定（例: コンテキストマネージャ）すればタイミング依存を除去できる。
- **変更パスが Undo チェックポイントを取ることを強制する仕組みがない**（`ui/mixins/_tree_crud_ops.py`・`_tree_sync_ops.py`・`_boundary_ops.py`）— Undo のカバレッジは手動で配置した約 18 個の `_checkpoint_for_undo` 呼び出しと、`setData` 経由編集の `about_to_change` シグナルに依存している。将来、明示的な呼び出しを忘れた直接変更パスは静かに Undo 不可になる（後の Ctrl+Z がそれを飛び越す）。変更後の 1 箇所のチョークポイントで直前のシリアライズ済みテキストを差分比較するか、カバレッジテストを設ければ堅牢になる。

## 謝辞

- [PyInstaller](https://pyinstaller.org/) — スタンドアロン実行ファイルのビルドに使用。
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — `blockMeshDict` の 3D ビューア（BSD-3-Clause、オプション）。
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — テストフレームワーク。

[OpenFOAM Foundation](https://openfoam.org/) および [OpenCFD / ESI Group](https://www.openfoam.com/) をはじめ、OpenFOAM をフリーのオープンソース CFD ソフトウェアとして開発・維持してきたすべての貢献者の方々に深く感謝いたします。
