# Foam Dictionary Editor (FoDE) — 開発者ガイド

ユーザー向けドキュメントは [USER_GUIDE_ja.md](USER_GUIDE_ja.md) を参照してください。インストールと基本的な使い方は [README_ja.md](README_ja.md) を参照してください。

## 概要

FoDE は、OpenFOAM のケース辞書を編集するための PySide6 製デスクトップエディタです。辞書をコメントと空白を保持したツリーにパースするため、触れていないテキストはバイト単位でそのまま書き戻されます。ツリーを生テキストと並べて表示し、ファイルごとのスキーマでキーを説明し、`blockMeshDict`・`topoSetDict`・`snappyHexMeshDict`・`setFieldsDict`・サンプリングのジオメトリを 3-D ビューアに描画します。本ガイドはコントリビュータ向けで、コードがどう構成され、なぜそうなっているかを説明します。コードを読むだけでは判断の理由が分からない箇所は、意図的に詳しく書いています。アプリケーションの*使い方*は [USER_GUIDE_ja.md](USER_GUIDE_ja.md) を参照してください。

基本のデータフローは次の通りです。

```text
disk file
  → OpenFoamParser  → FoamNode tree
  → FoamTreeModel   → QTreeView (centre panel)
  → write_root()    → CodeEditor (bottom Editor tab)
```

編集は双方向に流れます。ツリーの編集は `write_root()` を呼んでテキストをエディタへ反映し、エディタで編集したテキストは **Apply Text to Tree** で再パースされます。

コードは層構造になっており、下位の層が上位の層を import することはありません。

- `foam/` — パーサ、ライタ、`FoamNode` ツリー、3-D ジオメトリ抽出器。純粋な Python で Qt に依存しません。
- `model/` — パース済みツリー、ファイルリスト、ケースナビゲータ用の Qt アイテムモデル。
- `services/` — UI の背後にある Qt 非依存のロジック。ケースファイルの一覧、ケースのコピー・移動、ツールの実行、ログの読み取り、processor 削除のチェックなど。
- `ui/` — ウィジェット。`panels/`・`dialogs/`・`widgets/`・`mixins/`（`MainWindow` のメソッドをドメイン別に分割したもの）に分かれ、テーマ・フォント・ウィンドウ状態のヘルパも含みます。
- `schemas/` — 辞書ファイルごとのキー説明、バージョンタグ、値の選択肢。一部のモジュールは姉妹リポジトリ foamlore で生成されます。
- `app_config/` — 永続設定、OpenFOAM 環境リーダ、キーワードスキャナ。`i18n/` は日本語訳、`tools/` は保守・ドキュメント用スクリプトです。

**目次**

- [はじめに](#はじめに)：[セットアップ](#セットアップ)、[実行](#実行)、[アプリケーション設定](#アプリケーション設定)
- [コントリビューション](#コントリビューション)：[コミットメッセージ](#コミットメッセージ)、[一緒に更新するドキュメント](#一緒に更新するドキュメント)、[リリースノートとリリースの切り方](#リリースノートとリリースの切り方)、[パッケージのビルド](#パッケージのビルド)、[コミットの前に](#コミットの前に)、[tools/ の保守スクリプト](#tools-の保守スクリプト)、[用語集](#用語集)
- [テスト](#テスト)：[テスト実行が開発者の設定を書き換えないこと](#テスト実行が開発者の設定を書き換えないこと)、[並列実行](#並列実行)、[カバレッジの計測](#カバレッジの計測)、[ダイアログのスタブ](#ダイアログのスタブ)、[テストにおけるウィジェットの破棄](#テストにおけるウィジェットの破棄)
- [Lint と型チェック](#lint-と型チェック)：[`ui/mixins/` 分割の型付け](#uimixins-分割の型付け)
- [プロジェクト構成](#プロジェクト構成)：[ドキュメントマップ](#ドキュメントマップ)
- [パーサとデータモデル](#パーサとデータモデル)：[ノード型](#ノード型)、[分類ロジック](#分類ロジック)、[再パースのトリガー](#再パースのトリガー)、[エラーリカバリ](#エラーリカバリ)、[FoamNode フィールドの意味](#foamnode-フィールドの意味)、[ライタの raw_text パススルー](#ライタの-raw_text-パススルー)、[トリビアの所有権](#トリビアの所有権)、[`field_value_block` の子ノードが `value` に格納される](#field_value_block-の子ノードが-value-に格納される)
- [スキーマシステム](#スキーマシステム)：[スキーマモジュールの書き方](#スキーマモジュールの書き方)、[KeySchema と ChoiceItem](#keyschema-と-choiceitem)、[キーが何であるかの記録: `status` フィールド](#キーが何であるかの記録-status-フィールド)、[キーを省略したときどうなるか: `default` と `required`](#キーを省略したときどうなるか-default-と-required)、[生成モジュール（foamlore からのベンダリング）](#生成モジュールfoamlore-からのベンダリング)、[SchemaRegistry](#schemaregistry)、[設定: デフォルトは置換ではなくマージ](#設定-デフォルトは置換ではなくマージ)
- [差分アルゴリズム](#差分アルゴリズム)：[API](#api)、[ステータス値](#ステータス値)、[再帰とスキップ](#再帰とスキップ)
- [インクルードの解決](#インクルードの解決)：[3-D ビューア向けのインクルード展開](#3-d-ビューア向けのインクルード展開)
- [ケースとファイル](#ケースとファイル)：[書き込みはケースの中に留める](#書き込みはケースの中に留める)、[サフィックス付きの派生ファイル](#サフィックス付きの派生ファイル)、[ケースナビゲーション](#ケースナビゲーション)、[追加ディレクトリ](#追加ディレクトリ)、[ケースルートのスクリプト](#ケースルートのスクリプト)、[同じ辞書が複数あるケース](#同じ辞書が複数あるケース)、[ツールメニュー](#ツールメニュー)（[Run ダイアログ](#run-ダイアログの仕組み)、[postProcess](#postprocess-とソルバ)、[バックグラウンド実行](#バックグラウンド実行)、[processor\* の削除](#processor-ディレクトリの削除)、[Allrun のステップ](#allrun-のステップ)、[ログから Allrun を作成](#ログから-allrun-を作成)、[ログの助言](#ログの助言)、[Check Case](#check-case)、[Plot Results](#plot-results)、[モジュール](#tools-メニューの背後のモジュール)）
- [メインウィンドウの挙動](#メインウィンドウの挙動)：[ツリーとエディタの同期](#ツリーとエディタの同期)、[バウンダリパネルとエディタのナビゲーション](#バウンダリパネルとエディタのナビゲーション)、[ダーティ状態の追跡](#ダーティ状態の追跡)、[ツリーのコピー・ペーストショートカット](#ツリーのコピーペーストショートカット)、[ブロックの選択と CRUD](#ブロックの選択と-crud)、[ツリー編集の Undo/Redo](#ツリー編集の-undoredo)、[3-D ビューアのオーバーレイ](#3-d-ビューアのオーバーレイ)、[レイアウトとパネル](#レイアウトとパネル)、[セッションの復元](#セッションの復元)
- [UI の規約](#ui-の規約)：[国際化（i18n）](#国際化i18n)、[テーマと配色](#テーマと配色)、[フォントサイズと表示スケーリング](#フォントサイズと表示スケーリング)、[GPU / OpenGL に関する注意](#gpu--opengl-に関する注意)、[ツールバーとメニューの構造](#ツールバーとメニューの構造)、[キーワードスキャナ](#キーワードスキャナ)、[ウィジェットと補助モジュール](#ウィジェットと補助モジュール)
- [ドキュメント用ツール](#ドキュメント用ツール)：[スクリーンショットの撮影](#スクリーンショットの撮影)、[デモ動画の収録](#デモ動画の収録)
- [テストカバレッジ一覧](#テストカバレッジ一覧) — テストファイルごとに 1 行
- [更新候補](#更新候補)：[次に行う](#次に行う)、[価値はあるが設計が要る](#価値はあるが設計が要る)、[保留](#保留)
- [謝辞](#謝辞)

## はじめに

チェックアウトからアプリケーションを起動する方法と、設定の置き場所です。

### セットアップ

Python 3.10 以上が必要です。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 実行

`main.py` のフラグはすべて任意で、認識されない引数は Qt に渡されます。`--variant`・`--theme`・`--ui-scale`・`--no-restore` は、特記のない限り 1 回の実行にだけ作用します。

```bash
python3 main.py                                   # 標準（ターミナル + BlockMesh）
python3 main.py --variant no-terminal             # ターミナルタブなし
python3 main.py --variant no-terminal-blockmesh   # ターミナルなし + BlockMesh 常時表示
python3 main.py --no-restore                      # 既定のレイアウトで起動。保存済みセッションは残る
python3 main.py --theme dark                      # この実行のみ。保存された設定は変更されない
python3 main.py --ui-scale 150                    # この実行のみ。QT_SCALE_FACTOR より優先される
```

`--theme` フラグ（`system`/`light`/`dark`）は、保存済みの **Settings > Appearance** の値をそのプロセスに限って上書きし、書き戻しません。異なるテーマのウィンドウを同時に起動しても、次回起動時のテーマは変わりません。`tools/capture_screenshots.py` はこの動作を利用しています。

`--ui-scale` フラグ（50〜400、パーセント）は、保存済みの **Settings > UI Scale** の値と環境変数 `QT_SCALE_FACTOR` の両方を、そのプロセスに限って上書きします。書き戻しは行いません。実際の動作は後述の「フォントサイズと表示スケーリング」を参照してください。

`--no-restore` フラグは、前回のセッションの代わりに既定のレイアウトで起動します。保存済みのセッションはそのまま残るので、次の通常起動では再び復元されます（`ui/session_restore.py` を参照）。

`--variant` フラグは `presets/<name>.json` を読み込み、設定シングルトンの `features` 辞書を上書きして、終了時に `app_config.json` へ保存します。次回以降は `--variant` なしでも保存した設定が使われます。`features` キーがない場合はすべて `true` として扱われるため、開発者個人の `app_config.json`（git 管理外で通常 `features` キーを持たない）は常に標準モードで動作します。

プリセットは `presets/standard.json`（ターミナルと BlockMesh）、`presets/no-terminal.json`（どちらもなし）、`presets/no-terminal-blockmesh.json`（ターミナルなしの BlockMesh）です。`no-terminal` 系は `QtWebEngineWidgets` への依存を避けられるため、xterm.js ターミナルが不要な環境（たとえば Windows）で推奨されます。同じフラグは `app_config.json` に手で書くこともできます。

```json
{ "features": { "terminal": false, "blockmesh": true } }
```

レイアウトはバリアント名ではなく機能の組ごとに記憶されるため、バリアント同士が保存済みセッションを上書きし合うことはありません。

起動後は **Case > Open Case…** から OpenFOAM ケースディレクトリを選択するか、ファイルマネージャからウィンドウ上の任意の場所にディレクトリをドロップしてください。その後、ファイル一覧から対象ファイルを選んでください。`app_config.json` は初めてケースを開いたときに自動作成されます。`schema_config.json` は Settings メニューからスキーマ設定を変更したときにのみ作成されます。

選択したディレクトリに `system/` も `constant/` も存在しない場合は、有効な OpenFOAM ケースでない可能性を示す警告ダイアログが表示されます。それでも開くことは可能です。

### アプリケーション設定

`AppConfigManager`（`app_config/app_config_manager.py`）はアプリケーションの永続設定を管理します。`get_app_config()` でシングルトンインスタンスを取得し、セッション全体で再利用します。読み込み/保存の実処理は `app_config/json_io.py`（`load_json`/`save_json`）に委譲しており、これは `services/case_files_config.py` とも共有しています。`save_json` はアトミックに書き込みます（`atomic_write_text`: ランダムな名前で排他的に作る隣接の一時ファイル + `os.replace` なので、書き込みが失敗しても既存の設定ファイルが壊れることはなく、予測できる名前に何かを置かれても書き込み先は変わりません。既存のファイルはモードを保ち、新しいファイルは `new_mode` から umask を引いたものになります（`app_config.json` は `0o600`）— [書き込みはケースの中に留める](#書き込みはケースの中に留める) を参照）。

#### 設定が読めない・書けないとき

`AppConfigManager` は失敗を `_warnings` に積む形で報告します。`take_warnings()` がそれを取り出し、`main.py` が `restore_session` の後にステータスバーへ表示します。これ以上直接的なことはできません。`app_config/` は階層として `ui/` より下にあり、ダイアログを出す手段がなく、置き換え前の 4 つの `print()` は、FoDE をデスクトップエントリから起動したときには存在しない stdout へ出力していました。

読み込み経路では、報告に加えてもう 1 つやることがあります。パースできないファイルは、デフォルト値を読み込む前に **`app_config.json.bad` へリネーム** します。これがないと、そのファイルは静かに破壊されます。パースに失敗し、`reset()` がデフォルト値をメモリに置き、必ず保存を行う `closeEvent` がそのデフォルト値をファイルに上書きするからです。ユーザから見れば、理由も分からず全設定が初期化され、復元する手がかりも残りません。削除ではなくリネームにしているのは、壊れた箇所の周囲の JSON はたいてい目視で読めますし、ケースライブラリを記憶から作り直すのは面倒だからです。

`delete_config_file()` が bool を返すのは、`services/case_files_config.py` にある同名のものと同じ理由です。どちらも「このファイルを削除します」とユーザに約束したコードから呼ばれます。`reset_file_list` は従来どちらの場合も成功と報告しており、直後にケースを再読み込みするため、削除に失敗した場合は「消えました」と伝えた直後に全エントリが一覧へ戻っていました。

#### save() のセマンティクス

`set_window_size()`、`set_default_case_dir()`、`set_language()` などのセッターはインメモリの状態のみを更新します。ディスクへの書き込みは行いません。呼び出し側は変更後に明示的に `cfg.save()` を呼び出す必要があります。

`main_window.py` では 2 つの呼び出し元がこれを行います。

- `closeEvent` — `cfg.set_window_size(w, h)` を呼び出した後に `cfg.save()` を呼び出し、最終的なウィンドウジオメトリを保存します。
- `reset_window_size` — 保存済みサイズをリセットしてすぐに保存します。

設定を変更する他の呼び出し元（ケースを開いた際のデフォルトケースディレクトリの更新など）も明示的に `cfg.save()` を呼び出す必要があります。終了前に `save()` が呼び出されなかった場合、`set_*` の変更は静かに破棄されます。

#### app_config.json の場所

`app_config.json` はプロジェクトルート（`main.py` と同じディレクトリ）に書き込まれます。`.gitignore` 対象です。ファイルが存在しない場合は `_load()` がエラーなしで戻り、すべてのプロパティがデフォルト値を返します。

**このセクションに関わるモジュール。**

- `app_config/foam_env.py` — `foam_env_dirs(env)` → `FoamEnvDirs`: `$WM_PROJECT_DIR/$FOAM_TUTORIALS/$FOAM_ETC/$FOAM_SRC/$FOAM_APP` を読む唯一の情報源（各フィールドはディレクトリが存在する場合のみ非 None、`project_dir` 配下へのフォールバック付き）。純粋な標準ライブラリのみに依存し `services/` には依存しないため、`services/example_search.py` からも import されるものの `services/` ではなくここに置く。`example_search`、`keyword_generator`、`AppConfigManager.foam_tutorials_dir` が共有。
- `app_config/json_io.py` — `load_json`・`save_json`・`atomic_write_text`。`app_config.json`・`.foam-editor-files.json`・キーワード生成器が共用。

## コントリビューション

変更を送る前に知っておくべきこと — コミットメッセージの書き方、一緒に更新するドキュメント、リリースの切り方、そしてこのガイドが前提とする用語です。

### コミットメッセージ

コミットは `type(scope): summary` という Conventional な形式で、動詞は命令形にします。例: `feat(tools): start probes, lines and planes inside the domain`、`fix(schemas): density aborted the run`。使う type は `feat`・`fix`・`docs`・`refactor`・`test`・`release` で、scope は領域名（`tools`・`viewer`・`schemas`・`ui`・`demo`・`readme` など）です。機能開発は `feat/…` ブランチで行い、マージコミットで取り込みます。コードとそのドキュメントに触れる変更は、可能なら 1 つのコミットにまとめます。

### 一緒に更新するドキュメント

英語のドキュメントにはすべて `*_ja.md` という日本語版があり、片方を編集したら同じ変更でもう片方も編集します。英語のみの少数の文書は[ドキュメントマップ](#ドキュメントマップ)に示しています。日本語版は識別子とメニューラベルを英語のまま残し、散文だけを訳します。本ガイドとその日本語版は見出しの並びも一致させる必要があるため、片方に見出しを足したらもう片方にも足します。

段落は 1 つにつき 1 行の長い行で書き、ハードラップしません。折り返すと 1 語の修正の差分が読めなくなり、日本語の再整形も壊れます。コードのコメントと docstring は英語で書き、説明を引く必要があるときは本ガイドの節名を挙げます。

ユーザーに見える機能は、その機能自身の節だけでなく、読者が探す場所にも書きます。その機能のコミットで、README の機能一覧、ユーザーガイドの **目的別ガイド** の表と **機能** の一覧、よくある問題に答えるものなら **トラブルシューティング** にも、両方の言語で加えます。`tests/test_docs.py` が本ガイドの規則のうち機械的な半分を確かめます: すべての節が目次にあること、すべての `#アンカー` リンクが解決すること、`_ja` ミラーが同じ見出しを保つこと、すべてのテストファイルが[テストカバレッジ一覧](#テストカバレッジ一覧)に載っていること、README の動画の本数、空行が続かないこと。

### リリースノートとリリースの切り方

`RELEASE_NOTES.md` と `RELEASE_NOTES_ja.md` では、新しい項目を `## Unreleased` 見出しの下に積み上げます。項目は追記のみで、1 段落 1 行の長い行とし、リリースまでは統合しません。その節が漏れなく揃っていると信じる前に、最後のタグ以降の `git log` と突き合わせてください。

リリースで触れるファイルはちょうど 3 つです。`_version.py`（`__version__`）と、`RELEASE_NOTES.md`・`RELEASE_NOTES_ja.md` の `## Unreleased` 見出し（バージョン番号に改名）です。コミットは `release: vX.Y.Z` とし、`vX.Y.Z` のタグを付けます。`get_version()` は常に `__version__` を報告し、チェックアウトから動かすと開発用の接尾辞（タグからのコミット数、短いハッシュ、未コミット変更があれば `*`）を付けるので、開発ビルドからの不具合報告でもビルドを特定できます。番号をタグから取ることはありません: タグを取得しないクローンでは、1.21.1 のコードが `1.15.1 (dev+117, …)` と表示されていました。コミット数は `git describe` がこのバージョン自身のタグを見つけたときだけ表示し、それ以外はハッシュだけでビルドを特定します。

**リリースを切る前に**、`tests/test_docs.py` では判断できない点を読んで確かめます:

- **リリースノート。** `## Unreleased` を最後のタグ以降の `git log` と突き合わせ、まだリリースしていない 1 つの機能の段階を語る項目は 1 つの項目にまとめます。
- **読者は新しい機能を見つけられるか。** リリースノートにある新しい機能ごとに、README（機能一覧、クイックスタート）、ユーザーガイドの **最初の一歩**・**目的別ガイド**・**機能**・**トラブルシューティング**・**用語集**、開発者ガイドのモジュール一覧を確かめます。
- **古くなった事実。** 機能によって変わった数や比較（「唯一の非モーダルダイアログ」「デモ動画 N 本」）や、何かを新しいと書いた文言。
- **スクリーンショット。** ダイアログやメニューが変わったものを撮り直します（`tools/capture_screenshots.py`、`tools/capture_dialog.py`。[スクリーンショットの撮影](#スクリーンショットの撮影)を参照）。
- **デモ動画。** 手順が変わったシーンを撮り直し、新しい動画の Vimeo リンクを記入します。

### パッケージのビルド

`build_linux.sh` は `requirements-packaging.txt` をインストールし、`build/` と `dist/` を掃除して、`foam-dictionary-editor.spec` を onedir モードで PyInstaller に掛け、README と実行時メモを `dist/foam-dictionary-editor/` に追加します。`foam_dict_editor.spec` と `main.spec` は参考用に残してある以前の spec です。xterm.js のターミナル資産は同梱しません。`package.json`（と `package-lock.json`）は、ターミナルが実行時にダウンロードするパッケージを正確なバージョンで記録しています。実際に使う URL と SHA-256 チェックサムは `ui/widgets/_xterm_widget.py` の `_XTERM_FILES` にあり、両者のバージョンが食い違うと `tests/ui/test_xterm_download.py` が失敗します。

### コミットの前に

テストとリンタを実行してください（[テスト](#テスト)と [Lint と型チェック](#lint-と型チェック)を参照）。`ui/` のユーザーに見える文字列はすべて `tr()` を通し、`i18n/ja.py` に対応する項目を置く必要があります。規則とガードテストは[国際化（i18n）](#国際化i18n)にあります。

### tools/ の保守スクリプト

`tools/` のスクリプトはアプリケーションからではなく手動で実行します。ディスプレイや外部プログラムを必要とするものは、それぞれの節（[スクリーンショットの撮影](#スクリーンショットの撮影)、[デモ動画の収録](#デモ動画の収録)）に書いてあります。

- `tools/capture_screenshots.py` — `tools/screenshot_specs.json` から `docs/SCREENSHOTS.md` のギャラリーを再生成する。保存されたウィンドウ状態を実際の `MainWindow` に適用し、ImageMagick の `import -frame` で撮影する。ショット × テーマごとに別プロセスで実行するため、`light/dark` のペアはテーマ以外が完全に一致する（「スクリーンショットの撮影」参照）。
- `tools/screenshot_specs.json` — ギャラリーのショット一覧。画像 1 枚につき `ui/window_state.py` の `WindowState` 1 つと、テーマごとの出力ファイル名。
- `tools/capture_dialog.py` — ギャラリーのもう半分であるダイアログを撮影する。ダイアログは独立したトップレベル X ウィンドウであり `capture_screenshots.py` からは手が届かないため。ショットは JSON spec ではなく `DIALOG_SHOTS` 辞書に置く（ダイアログは型付き Python 引数から構築するため）。テーマ・言語・import のルールは共通（「スクリーンショットの撮影」参照）。
- `tools/demo_driver.py` — `tools/demo_specs.json` をもとに `docs/DEMO_SCRIPTS.md` の動画を操作・収録する。開始状態はスクリーンショット spec と同じ `WindowState` で、その後を実際の X 入力（xdotool）で操作し、収録専用のネストされたディスプレイ上で ffmpeg により収録する（「デモ動画の収録」参照）。
- `tools/demo_paraview_profile/` — 収録時の ParaView 設定。Qt はこの状態を全部まとめて復元するため手書きではなく `make_paraview_demo_profile.sh` で生成する。初回起動の ParaView がウィンドウ全面に出す Getting Started スプラッシュを抑止する。
- `tools/make_ja_srt.py` — `docs/demo/<scene>.ja.srt` を書く。英語のキューの時刻を使い、各行は `docs/DEMO_SCRIPTS_ja.md` の対応する行から取る。`--check` は古いトラックを報告し、デモ spec のテストがこれを実行する。
- `tools/make_paraview_demo_profile.sh` — 上記プロファイルを使い捨ての ParaView を操作して再生成する。ParaView のバージョンが変わったときに必要: 設定ファイル名にバージョンが入るため、別のビルドは他バージョンが書いたものを無視する。
- `tools/demo_specs.json` — 動画のシーン一覧。シーンごとの開始状態と、それを操作する steps・ナレーション・表示時間。
- `tools/generate_foam_keywords.py` — `app_config/keyword_generator.py` の CLI ラッパー。`--dir` でインストールルートを指定（デフォルト: source 済み環境）。
- `tools/gen_reader_paths.py` — `tools/fode-reader-paths.json` を出力する。バージョンタグ・オラクルの FoDE 側: 各スキーマ辞書のキーがどこで読まれるかを示し、foamlore が `supported_in` を測定できるようにする。
- `tools/scan_foundation14_keys.py` — まとめてタグ付けされた Foundation のキーを新しいチェックアウトに対して差分スキャンする — `FOUNDATION_SERIES` を延長する根拠となる測定。
- `tools/roundtrip_corpus.py` — インストール済み tutorials の全辞書を parse+write してバイト単位で一致した件数を数える。リリースノートのラウンドトリップ数値の測定元。

### 用語集

- **Fork** — OpenFOAM は 2 系統で開発されています。OpenFOAM Foundation 版（openfoam.org、7 から 14 のような番号付きリリース）と OpenCFD 版（openfoam.com、v2606 のような日付番号のリリース）です。辞書名・キー・チュートリアルが異なり、FoDE は両方に対応します。スキーマ項目はリリースごとの `supported_in` タグを持ち、`services/case_loader.py` は改名された辞書の両方の綴りを一覧に出します。
- **Case** — OpenFOAM のケースディレクトリ。`system/`、`constant/`、`0/` などの時刻ディレクトリを持ちます。ディレクトリがケースとみなされるかは `services/case_loader.py` の `is_openfoam_case` の緩い判定によります。
- **Viewer dictionary** — 3-D オーバーレイに供給する辞書。`blockMeshDict`、`topoSetDict`、`snappyHexMeshDict`、`setFieldsDict`、またはサンプリングを定義するファイル。[3-D ビューアのオーバーレイ](#3-d-ビューアのオーバーレイ)を参照。
- **Trivia** — `FoamNode` が保持するコメントと空白。未編集のファイルをバイト単位で往復させるためのものです。[トリビアの所有権](#トリビアの所有権)を参照。
- **Schema module** — `schemas/` 配下の Python モジュールで、`TARGET_FILE`（または `TARGET_FILES`）と `KeySchema` 項目の `SCHEMAS` 表を宣言します。[スキーマシステム](#スキーマシステム)を参照。
- **Vendored module** — 姉妹リポジトリ foamlore で生成され、バイト単位でそのままコピーされるスキーマモジュール。このリポジトリでは編集しません。[生成モジュール（foamlore からのベンダリング）](#生成モジュールfoamlore-からのベンダリング)を参照。
- **foamlore** — OpenFOAM のソースツリーを測定し、スキーマの一部を生成する姉妹リポジトリ。

## テスト

スイートは pytest（ウィジェットのテストには pytest-qt）で動きます。この節では、実行のしかたと触ってはならないものを説明します。各テストファイルが何を固定しているかは、モジュールを変更するときに引けるよう、本書の終わり近くの [テストカバレッジ一覧](#テストカバレッジ一覧) にまとめています。

```bash
python3 -m pytest -q
```

素の `pytest -q` よりも `python3 -m pytest -q` を使ってください。素の方はプロジェクトルートの扱いが不安定で、import で問題が出ることがあります。lint と型チェックもスイートの一部として実行されます。詳細は [Lint と型チェック](#lint-と型チェック)を参照してください。

### テスト実行が開発者の設定を書き換えないこと

`tests/conftest.py` の autouse フィクスチャ `temp_config` は、**すべての**テストについて設定シングルトンと `$FODE_CONFIG` を `tmp_path` 上のファイルに向けます。無条件に適用しているのは、テストが `app_config.json` を書いてしまう経路がテスト自身からは見えないためです。ウィンドウを閉じれば保存され、`save()` を呼ぶものはすべて保存し、動作を軽くするために機能フラグを false にするテストは、それを実行した開発者のチェックアウトでフラグを false のまま残します。最後の事例が実際に発生したため、個々のテストの心がけに任せるのをやめました。フィクスチャが適用されなくなった場合は `tests/test_config_isolation.py` が失敗します。

`AppConfigManager` はパスが渡されなかったときに **`$FODE_CONFIG`** を読みます。pytest の外でも同じ保護が効くので、実際のチェックアウトに対して `MainWindow` を作るような使い捨てスクリプトではこれを設定してください。

```bash
FODE_CONFIG=/tmp/throwaway.json python3 some_scratch_script.py
```

明示的な `config_path=` は環境変数より優先されます。また環境変数は import 時ではなく呼び出しごとに読むため、同一プロセス内で変数を設定してからマネージャを構築できます。

このフィクスチャに手を入れる場合の注意が 2 つあります。1 つは、`monkeypatch` ではなく素朴な保存・復元で実装している点です。autouse フィクスチャが `monkeypatch` を要求すると、全テストで monkeypatch が最初に生成されるフィクスチャとなり、その取り消しが teardown の最後に回ります。`tests/ui/test_included_files.py` は `include_scan.foam_etc_dirs`（`lru_cache`）をパッチし、自身の teardown でそのキャッシュをクリアするため、先にパッチが取り消されている必要があります。もう 1 つは、`main_window` が autouse の順序に頼らず `temp_config` を明示的に要求している点です。このフィクスチャが作るウィンドウ自体が、保存を行うものの 1 つだからです。

### 並列実行

`pytest-xdist` は導入済み（requirements-dev.txt）ですが、既定では**有効にしていません**。そして起動オプションの選び方は、見た目以上に効きます。

```bash
python3 -m pytest -q -n 16          # 約 10 秒  <- コア数の多いマシンではこれ
python3 -m pytest -q -n auto        # 約 17 秒  64 コア機ではむしろ遅い（下記参照）
python3 -m pytest -q                # 約 96 秒  逐次実行
```

**ここでは `-n auto` が最速ではありません。** これはコア数ぶんのワーカを起動しますが、各ワーカは何かを実行する前に PySide6 と pyvista・pyvistaqt のインポート（約 1 秒）を支払います。64 ワーカではその起動コストが支配的になり、実測でも `-n auto`（17.1 秒）は `-n 16`（10.9 秒）より遅く、`-n 8`（12.2 秒）ともほとんど変わりません。コア数ではなく中間の数を選んでください。

分散モードはどちらでも通ります。`--dist load`（xdist の既定。テスト単位のラウンドロビン）が通るということは、このスイートがファイル単位だけでなくテスト単位で独立しているということです。`--dist loadfile` はファイル内のテストを同じワーカにまとめるので、将来順序依存が紛れ込んだ場合により安全です。速度差は 1 秒程度です。

既定で無効にしているのは意図的です。マシン非依存な唯一の設定である `-n auto` はここでは不適切であり、固定値は小さなマシンで不適切になります。さらに並列実行は出力が混ざり、`-s` やブレークポイントが毎回使いにくくなります。それで節約できるのは、もはや苦痛ではない 1 分半です。常に有効にしたい場合は `pytest.ini` に `addopts = -n 16` を足してください。デバッグ時は `-n0` で無効に戻せます。

`real_config_untouched` のガードは xdist 下でも機能します。各ワーカがそれぞれ独立したセッションなので、各々が `app_config.json` をスナップショットして検査します（テストにわざと書き込ませ、全ワーカが失敗することを確認済み）。

### カバレッジの計測

`coverage` は requirements-dev.txt に入っています。スイート自体は使っておらず、閾値も課していません。「何がテストされていないか」に答えるためのものです。この問いは当て推量では答えを誤ります。

```bash
python3 -m coverage run --source=foam,model,services,ui,app_config -m pytest -q
python3 -m coverage report --sort=cover | head -20      # カバー率の低い順
python3 -m coverage report --skip-covered               # 穴のあるものだけ
python3 -m coverage html && xdg-open htmlcov/index.html # 行単位で確認
```

数値を読む前に 2 点。`ui/mixins/_protocol.py` は 0% と出ますし、今後もそうです。これは実行されない mypy 専用のスタブなので、追いかけずに除外してください。もう 1 点、上の並列実行の `-n` を併用する場合は `coverage` 側の combine 処理を挟まないと合計値が正しくなりません。面倒がなければ逐次で計測してください。

この数値は目標ではありません。最初に計測したときの合計は 75% でしたが、有用だったのは合計値ではありませんでした。`ui/mixins/_boundary_ops.py` が 17% である一方、そのパネル側のコピー用ヘルパーは十分カバーされていた、という事実です。つまりテストは、複数のフィールドファイルを一度に書き換える部分ではなく、テストしやすい部分に付いていたということです。

### ダイアログのスタブ

`tests/conftest.py` の autouse な `no_unstubbed_modals` が、ブロックするダイアログ呼び出しをすべて — `QDialog.exec`、`QMessageBox` の `exec`/`question`/`warning`/`information`/`critical`、`QFileDialog.get*`、`QInputDialog.getText`/`getItem` — 例外を送出するものに差し替えます。テストがスタブし忘れたダイアログにハンドラが到達すると、実行がハングするのではなく、クラス名とメソッド名を示して*失敗*します。ある午後に起きた 5 件のハングはすべて同じ間違いでしたが、ハングはテスト名を一切示しません。特定には手作業の二分探索が要り、CI では単なるタイムアウトになります。これらが例外を投げる状態でもスイート全体が通ります。これは「正当にダイアログを開くテストは 1 つもない」という言明と同じことです。

もう半分、ダイアログに答えるための fixture は `tests/ui/conftest.py` にあります:

| fixture | 応答対象 |
|---|---|
| `stub_dialog("pkg.mod.DialogClass", accepted=…, **attrs)` | ダイアログクラス全体（ハンドラから見える名前で指定） |
| `answer_message_box(button)` | `QMessageBox` の static 全部。プロンプト文字列のリストを返す |
| `choose_directory(path)` | `QFileDialog.getExistingDirectory` |
| `answer_input(value, ok=…)` | `QInputDialog.getText`/`getItem` |

`answer_message_box` が 4 つの static をまとめて差し替えるのは意図的です。ハンドラは複数に到達することが多く、思い浮かべた 1 つだけをスタブすると、もう一方でハングします。

ボタンを手組みしているダイアログには、今もローカルなスタブが必要です。ハンドラが `clickedButton()` を自前のオブジェクトと同一性で比較するためで、`tests/ui/test_file_mgmt_ops.py` の `_answer_delete_dialog` がその唯一の例です。

### テストにおけるウィジェットの破棄

Qt ウィジェットを生成する fixture は、それを破棄しなければなりません。本スイートはイベントループを持たないため、放っておいてウィジェットが回収されることはありません:

- `deleteLater()` は何もしません。ループレベル 0 では `processEvents()` が `DeferredDelete` を配送しないため、呼び出し後もウィジェットは `QApplication.allWidgets()` に残ります。
- `del` と `gc.collect()` も同様です。Python 側のラッパーは消えても C++ オブジェクトは残ります。`MainWindow` 1 個あたり 237 個の `QWidget` が生き続けます。
- 実際に解放するのは `shiboken6.delete()` です。`tests/conftest.py` の `_destroy_widget` がこれをラップしています。ウィジェットを所有する fixture では引数に `destroy_widget` を、テスト本体で生成するウィジェットには `qt_widget` を取ってください。`tests/test_lint.py` には、ウィジェットfixture がこれを忘れた場合に失敗するガードがあります。

これは整理整頓の話ではありません。`apply_theme()` → `setStyle`/`setPalette`/`setStyleSheet` は
*ブロードキャスト* です。Qt はプロセス内の生存するウィジェットすべてを走査して再 polish し、その
コストは 1 個あたり約 0.5 ミリ秒です。テストごとにウィンドウが 1 個漏れる状態では生存ウィジェットが数万個に達し、`tests/ui/test_theme.py` と `tests/ui/test_icons.py` は — **単独実行なら 0.31 秒**なのに — 1700 秒の実行のうち約 1300 秒を、パレットに一切触れないテストの teardown で消費していました。このリークの修正により、スイートは **28 分から 2 分未満** になりました。

省略できない 2 つの規則。いずれも反対のことを実際にやって学んだものです:

**テスト内で `MainWindow` を `close()` してはいけません。** `closeEvent` は`_confirm_discard_if_needed()` を呼び、エディタがダーティな場合はモーダルな `QMessageBox` を表示します — そしてテストはエディタをダーティなまま残します。応答する者がいないため、実行は失敗ではなく *ハング* します。さらに `closeEvent` はセッションレイアウトとウィンドウサイズを設定に書き戻します。`hide()` で十分です。`closeEvent` が行うパネル固有のシャットダウンは、各 fixture が既に実施しています。

**`QApplication.topLevelWidgets()` から無差別に削除してはいけません。** このリストは所有関係のルートではなく *フラグ上のウィンドウ* の一覧です。`Qt::Popup` は `Qt::Window` ビットを持つため、`MainWindow` 1 個につき約 10 個の `QMenu` が含まれ、その親は生ポインタでそれらを参照しています。所有者が生きているまま子を削除するとポインタが宙に浮き、プロセスは segfault します。`QComboBox` のポップアップコンテナ、`QToolTip` の static、QtWebEngine の delegate ウィジェット、そして pyvistaqt の`QtInteractor`（VTK のレンダーウィンドウは QWidget が存在するうちに閉じる必要があるため、`BlockMeshPanel.shutdown()` を破棄より *前* に実行）も同じ分類です。

いずれも 1 つの原則から導かれます: **fixture 自身が生成したものだけを、生成した fixture から破棄する**。これがグローバルな `pytest_runtest_teardown` フックではなく fixture 単位にしている理由でもあります。フックの場合、`trylast` を付けない限り fixture のファイナライザより *前* に走り、上記の `shutdown()`より先に破棄が実行されてしまいます。

## Lint と型チェック

設定は `pyproject.toml` にあります。`ruff` はリポジトリ全体を対象とします（`.venv/` などの ruff 自身の既定の除外を除き、`include`/`exclude` 制限はありません）。リポジトリ全体がクリーンなので、スコープ指定なしで実行します。

```bash
ruff check
```

`i18n/ja.py` の翻訳文字列リテラル（英語の `tr()` キーとその日本語訳文）は、`pyproject.toml` の `[tool.ruff.lint.per-file-ignores]` により `E501`（行長超過）の対象から除外されています。どちらを折り返しても、キーの参照が壊れるか、翻訳文が変わってしまうおそれがあるためです。

`pyproject.toml` の `[tool.mypy] files` には `foam/`、`model/`、`app_config/`、`schemas/`、`services/`、`ui/`(すべて)に加えて `main.py`・`i18n/`・`tools/` が列挙されています — トップレベルのソースパッケージすべてです。`tools/` を含めているのは、これらのスクリプトが実ディスプレイ上で手動実行されるため、型エラーがキーボードの前ではなくキャプチャ実行の途中で表面化するからです。`ui/` 内の PySide6 属性アクセスはすべて、スタブが要求する完全修飾形の enum(`Qt.Horizontal` のようなフラット形ではなく `Qt.Orientation.Horizontal`)を使用しています。この 2 つのスタイルを混在させることが、PySide6 コードベースにおける `mypy` ノイズの最大の原因になります。

```bash
mypy
```

`[[tool.mypy.overrides]]` の設定で `numpy.*`/`numpy` を `follow_imports = "skip"`(および `follow_imports_for_stubs = true`)に緩和しています。numpy に同梱されたスタブは `python_version >= 3.12` でしかパースできない PEP 695 の `type` 文を使用しており、本プロジェクトの `python_version = "3.10"`(サポートする最小ランタイム)ターゲットと衝突するためです。`ui/panels/block_mesh_*.py` および `ui/panels/shape_mesh.py` の `vtk`/`pyvista`/`pyvistaqt` はスタブが一切存在しないため `ignore_missing_imports = true` にフォールバックし、それらのオブジェクトは `Any` として扱われます。

**テストスイートの中で。** `tests/test_lint.py` が `ruff check` と `mypy` をテストとして実行する（どちらかが未インストールならスキップ）ため、素の `python3 -m pytest -q` で lint と型の regression を検出できます。CI ワークフローはないので、これが唯一の自動チェックです。同じファイルがテスト衛生の 2 つの規則も守ります。テストモジュールが独自の `QApplication` フィクスチャを定義しないこと、そしてウィジェットを生成するフィクスチャは必ずそれを破棄することです（[テストにおけるウィジェットの破棄](#テストにおけるウィジェットの破棄)を参照）。

### `ui/mixins/` 分割の型付け

`ui/main_window.py` の `MainWindow` は 21 個の mixin と `QMainWindow` から構成されています(下記「プロジェクト構成」の `ui/mixins/` の項目を参照)。各 mixin はランタイム上は共通の基底クラスを持たないただのクラスであり、実際の合成は `MainWindow` がそれらすべてを継承した時点で初めて成立します。これは `mypy` にとって問題です。`mypy` は各 mixin モジュールを単独で型チェックするため、素の `class _FileOpsMixin:` では `self` がいずれ `.tree` や `.state`、`._load_tree()` を持つことを知る術がありません。

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

**このセクションに関わるモジュール。**

- `ui/mixins/_protocol.py` — mypy 専用の `MainWindowProtocol`。各 mixin の `TYPE_CHECKING` 用基底クラスがこれを指すことで `self.tree`/`self.state`/mixin 間呼び出しが型チェックされる。

## プロジェクト構成

現在の代表的なディレクトリ構成は次の通りです。

```text
foam-dictionary-editor/
├── docs/
│   ├── DEMO_SCRIPTS.md, DEMO_SCRIPTS_ja.md  # デモ動画のショットごとの台本
│   ├── SCREENSHOTS.md, SCREENSHOTS_ja.md  # 注釈付きスクリーンショットギャラリー
│   ├── OPENFOAM_VERSIONS.md, OPENFOAM_VERSIONS_ja.md  # リリース間・フォーク間の辞書名の変更
│   ├── SCHEMA_CANDIDATES.md, SCHEMA_CANDIDATES_ja.md  # 次にスキーマを書くべき辞書の候補
│   ├── foamlore-schema-spec.md, foamlore-schema-spec_ja.md  # foamlore ジェネレータへの決着済みの依頼
│   ├── demo/                         # デモ動画の字幕（*.srt）。.mp4 は追跡しない
│   └── images/                       # ユーザーガイドとギャラリーが使うスクリーンショット
├── tools/
│   ├── capture_screenshots.py        # screenshot_specs.json から docs/SCREENSHOTS.md のギャラリーを再生成
│   ├── screenshot_specs.json         # ギャラリーのショット一覧（画像ごとに WindowState 1 つ）
│   ├── capture_dialog.py             # ギャラリーのダイアログ（独立した X ウィンドウ）を撮影
│   ├── demo_driver.py                # demo_specs.json から DEMO_SCRIPTS.md の動画を操作・収録
│   ├── demo_paraview_profile/        # 収録時の ParaView 設定（生成物）
│   ├── make_paraview_demo_profile.sh  # 上記プロファイルを使い捨ての ParaView で再生成
│   ├── make_ja_srt.py                 # 日本語の字幕トラックを、英語のキューと DEMO_SCRIPTS_ja から作る
│   ├── demo_specs.json               # 動画のシーン一覧（開始状態・手順・ナレーション）
│   ├── generate_foam_keywords.py     # app_config/keyword_generator.py の CLI ラッパー
│   ├── gen_reader_paths.py           # fode-reader-paths.json（バージョンタグ・オラクルの FoDE 側）を出力
│   ├── fode-reader-paths.json        # その対応表（生成物。テストがレジストリと同期を保つ）
│   ├── scan_foundation14_keys.py     # 集合タグ付き Foundation キーの差分スキャン
│   └── roundtrip_corpus.py           # tutorials を parse+write してバイト一致数を数える
├── tutorials/                        # 同梱サンプルケース（GPL-3.0、tutorials/README.md 参照）
├── main.py
├── pyproject.toml                    # ruff・mypy の設定
├── pytest.ini                        # pytest 設定（pythonpath = .）
├── _version.py                       # アプリバージョンの単一情報源
├── requirements.txt
├── requirements-dev.txt
├── requirements-packaging.txt
├── build_linux.sh                    # foam-dictionary-editor.spec による PyInstaller ビルド
├── foam-dictionary-editor.spec, foam_dict_editor.spec, main.spec  # PyInstaller の spec ファイル
├── package.json, package-lock.json   # ターミナルが実行時にダウンロードする xterm.js パッケージのバージョン指定（同梱はしない）
├── README.md
├── README_ja.md
├── USER_GUIDE.md
├── USER_GUIDE_ja.md
├── DEVELOPER.md
├── DEVELOPER_ja.md
├── RELEASE_NOTES.md
├── RELEASE_NOTES_ja.md
├── LICENSE                           # AGPL-3.0-or-later のライセンス本文
├── COPYRIGHT.txt                     # 著作権とライセンスの表示
├── THIRD-PARTY.md                    # 生成スキーマが引用する OpenFOAM 文書のクレジット（foamlore からコピー）
├── .gitignore                        # app_config.json・schema_config.json・.venv/・ビルド成果物を除外
├── serena_hooks_activate_project_fix.patch  # Serena MCP のセッション開始フックへのローカルパッチ（開発用）
├── app_config.json                   # アプリ設定（初回ケースオープン時に作成、git 管理外）
├── schema_config.json                # スキーマモジュール一覧（スキーマ設定変更時に作成）
├── presets/
│   ├── standard.json                 # features: terminal + blockmesh
│   ├── no-terminal.json              # features: terminal=false, blockmesh=false
│   └── no-terminal-blockmesh.json    # features: terminal=false, blockmesh=true
├── app_config/
│   ├── __init__.py
│   ├── app_config_manager.py
│   ├── constants.py
│   ├── defaults.py
│   ├── foam_env.py                   # foam_env_dirs(env): source 済み OpenFOAM 環境の読み取り
│   ├── json_io.py                    # load_json/save_json（アトミック）と atomic_write_text
│   ├── keyword_generator.py          # インストールをスキャンしてハイライタ用 foam_keywords.json を再生成
│   └── foam_keywords.default.json    # 同梱のキーワード基準（生成ファイルが優先）
├── foam/
│   ├── __init__.py
│   ├── block_mesh_extractor.py       # blockMeshDict から頂点・hex ブロック・境界面を抽出
│   ├── var_resolver.py               # $var と #eval{} の共通解決: build_var_map()
│   ├── shapes.py                     # SourceShape: 各抽出器の形状クラスの共通基底
│   ├── topo_set_extractor.py         # topoSetDict の action_entry から描画用ジオメトリを抽出
│   ├── set_fields_extractor.py       # setFieldsDict の regions ( … ) から領域ジオメトリを抽出
│   ├── sampling_extractor.py         # controlDict／サンプリング辞書からプローブ・線・平面を抽出
│   ├── snappy_hex_mesh_extractor.py  # snappyHexMeshDict の geometry {} と保持点を抽出
│   ├── include_resolver.py           # Qt 非依存の #include 系ディレクティブの解析と解決
│   ├── include_expand.py             # expand_includes(): include を読み取り専用の木コピーへ展開
│   ├── tree_utils.py                 # FoamNode 検索ヘルパと box/sphere/cylinder/cone 共通リゾルバ
│   ├── diff.py                       # diff_trees / diff_trees_reverse: キー名による木の比較
│   ├── boundary_patch.py             # 境界パッチ用の Qt 非依存 FoamNode 操作
│   ├── lexer.py                      # OpenFoamLexer（#eval{...} の波括弧は LBRACE/RBRACE）
│   ├── nodes.py
│   ├── parser.py
│   ├── utils.py
│   ├── value_parse.py                # FoamTreeModel.setData を支える Qt 非依存の値検証
│   └── writer.py
├── model/
│   ├── __init__.py
│   ├── boundary_model.py             # BoundaryModel（QAbstractTableModel）+ extract_boundary()
│   ├── case_tree_model.py            # CaseTreeModel: ケースナビゲータの木（ケースは印付き・非展開）
│   ├── file_list_model.py            # FileListModel（QAbstractListModel）
│   └── tree_model.py                 # FoamTreeModel(QAbstractItemModel)（setData は value_parse で検証）
├── schemas/
│   ├── __init__.py
│   ├── _base.py
│   ├── builtin.py
│   ├── config_store.py
│   ├── block_mesh_dict.py
│   ├── control_dict.py
│   ├── fv_schemes.py
│   ├── fv_solution.py
│   ├── _turbulence_coeffs.py         # 生成物（foamlore からベンダリング）: 29 モデルの係数
│   ├── _transport.py                 # 生成物: transportProperties の粘度モデル
│   ├── _generalised_newtonian.py     # 生成物: 一般化ニュートン流体の係数
│   ├── _laminar_models.py            # 生成物: 層流応力モデルの説明文（MODEL_DOCS）
│   ├── _delta_models.py              # 生成物: LES delta モデルの説明文（MODEL_DOCS）
│   ├── transport_properties.py       # 生成物: constant/transportProperties 用の薄いモジュール
│   ├── physical_properties.py        # 生成物: constant/physicalProperties 用の薄いモジュール
│   ├── turbulence_properties_viscosity.py  # 生成物: turbulenceProperties の viscosityModel 係数
│   ├── momentum_transport_viscosity.py  # 生成物: momentumTransport の viscosityModel 係数
│   ├── momentum_transport.py         # 生成物: constant/momentumTransport 用（Foundation v8 以降）
│   ├── snappy_hex_mesh_dict/         # パッケージ: サブドメイン別に分割（geometry, castellated mesh, snap, layers, mesh quality）
│   │   ├── __init__.py               # 各サブモジュールの SCHEMAS を統合し、TARGET_FILE を再エクスポート
│   │   ├── _common.py                # 共有 SWITCH_CHOICES
│   │   ├── _structure.py             # 4 つの制御辞書とその中のサブ辞書
│   │   ├── _geometry.py
│   │   ├── _castellated_mesh.py
│   │   ├── _snap_controls.py
│   │   ├── _add_layers.py
│   │   └── _mesh_quality.py
│   ├── turbulence_properties.py      # 生成物: constant/turbulenceProperties 用の薄いモジュール
│   ├── turbulence_structure.py       # 手書き: simulationType・モデルセレクタ・LES delta
│   └── registry.py
├── services/
│   ├── __init__.py
│   ├── background_run.py             # FoDE より長く続く実行: 切り離し起動・pid 記録・停止手順
│   ├── case_copier.py
│   ├── domain_bounds.py              # blockMeshDict から求めるケースの範囲（polyMesh/points は使わない）
│   ├── field_integrity.py            # OpenFOAM 出力ファイルが完全か（先頭と末尾を読む）
│   ├── function_templates.py         # インストール側の関数オブジェクト・テンプレートの読み取りと入力
│   ├── foam_monitor.py               # patched_foam_monitor(): gnuplot reread 修正済みの foamMonitor
│   ├── backup_files.py               # find_backup_files(case_dir): <name>.bak_YYYYMMDD_HHMMSS を列挙
│   ├── case_files_config.py
│   ├── case_fs_ops.py                # ケースの move/rename/copy/delete/新規フォルダ（安全規則付き）
│   ├── case_loader.py                # list_case_files(): 固定の対象リスト・0/ のファイル・variant・ルートスクリプト
│   ├── case_scan.py                  # ケースナビゲータ用のディレクトリ一覧: list_subdirectories()
│   ├── include_scan.py               # include 対応のディスク側: etc 検索パスと 1 段スキャン
│   ├── example_search.py             # discover_installations()/search_examples()（tutorials/ を検索）
│   ├── log_summary/                  # パッケージ: 実行ログの parse_log()/format_summary()
│   │   ├── __init__.py               # データクラスの再エクスポート、ディスパッチと描画
│   │   ├── _types.py                 # LogSummary/LogWarning/PhaseSummary と共通のヘッダ・警告解析
│   │   ├── _block_mesh.py            # blockMesh 文法: Mesh Information ブロック
│   │   ├── _snappy_hex_mesh.py       # snappyHexMesh 文法: 「Wrote mesh in」で段階を分割
│   │   ├── _topo_set.py              # topoSet 文法: セットごとのソース/サイズの集約
│   │   ├── _solver.py                # ソルバー文法: タイムループのステップ・残差・Courant 数・実行時間
│   │   └── _generic.py               # フォールバック文法: 未認識ログの末尾表示
│   ├── plot_data/                    # パッケージ: Plot Results のデータ — find_sources()/load_source()
│   │   ├── __init__.py               # 再エクスポート
│   │   ├── _reader.py                # 自己完結した表・ログ読み込み。エクスポートしたスクリプトに埋め込む
│   │   └── _discover.py              # postProcessing/ の走査、リスタートの区間、ソルバーログ、キャッシュ
│   ├── plot_animation.py             # Plot Results のアニメーション: コマ、固定した範囲、GIF/MP4/PNG の書き出し
│   ├── plot_export.py                # データを見出し付き CSV と .source.txt に
│   ├── plot_output.py                # Plot Results が書き込んでよい場所、アトミックな書き込み
│   ├── plot_render.py                # draw(): PlotSpec を matplotlib の Figure に描く
│   ├── plot_script.py                # python_script()/gnuplot_script(): プロットをスクリプトとして書き出す
│   ├── plot_spec.py                  # PlotSpec/Series/Axis + resolve(): プロットが何を示すか
│   ├── post_process.py               # 既存結果への関数オブジェクト実行（postProcess）
│   ├── process_tree.py               # Linux /proc: Terminal タブのシェルが実行中のもの
│   ├── solver_run.py                 # Run Solver/decomposePar と processor* 削除チェックの読み取り
│   └── tool_options.py               # ToolSpec とコマンド組み立て build_args()/build_command()
├── i18n/
│   ├── __init__.py                   # tr()、set_language()、get_language()、available_languages()
│   └── ja.py                         # 日本語翻訳（LANGUAGE_NAME + TRANSLATIONS 辞書）
├── ui/
│   ├── __init__.py
│   ├── fonts.py                      # UI の全フォントサイズ（QApplication.font() から導出）
│   ├── icons.py                      # icon(name) → QIcon: アルファマスクで着色した SVG
│   ├── label_fit.py                  # fit_wrapped_labels(root): 折り返し QLabel に、実際の幅で必要な高さを与える
│   ├── assets/icons/                 # 手書きの黒一色のツールバー/メニュー用 SVG 9 個
│   ├── xterm_terminal.html           # xterm ターミナルが読み込む xterm.js のページ。フォントサイズは <!--XTERM_FONT_SIZE--> に注入
│   ├── app_state.py                  # AppState: 共有する可変フィールド（DiffState/UndoState 含む）
│   ├── case_navigation.py            # CaseNavigator: Cases タブと Case Browser の共通コントローラ
│   ├── viewer_dicts.py               # viewer_dict_kind(path, root): ファイルが供給する 3-D オーバーレイ
│   ├── theme.py                      # テーマモード・全 UI 色・QPalette に触れる唯一のモジュール
│   ├── pane_minimize.py              # PaneMinimizer: QSplitter の 1 ペインをワンクリックで畳む/戻す
│   ├── menu_builder.py               # MenuBuilder/exec_menu: コンテキストメニューをデータとして構築
│   ├── processor_deletion.py         # processor* 削除をワーカースレッド＋進捗ダイアログで実行
│   ├── window_state.py               # WindowState とレイアウトの選択の取得・適用
│   ├── session_restore.py            # window_state.py を使い実行間でレイアウトを保存・復元
│   ├── main_window.py                # コア: __init__・_build_ui と各ビルダ・ドラッグ＆ドロップ
│   ├── mixins/
│   │   ├── __init__.py
│   │   ├── _background_run_ops.py    # mixin: バックグラウンド実行・停止・ポーリング・ツールバーのバッジ
│   │   ├── _boundary_ops.py          # Mixin: バウンダリビューのパッチ操作
│   │   ├── _case_ops.py              # Mixin: ケースの開く・再読み込み・複製・名前を付けて保存・設定
│   │   ├── _case_nav_ops.py          # mixin: Case Browser／Cases タブのハンドラ、_close_case()
│   │   ├── _diff_ops.py              # mixin: 並べて比較、差分の計算とクリア
│   │   ├── _file_mgmt_ops.py         # Mixin: ファイルの作成・追加・バックアップ・削除・複製・クリーンアップ
│   │   ├── _file_ops.py              # Mixin: ファイル単位の読み込み・保存、ディレクトリスキャンヘルパー
│   │   ├── _foam_monitor_ops.py      # Mixin: foamMonitor の起動・停止・ポーリング、gnuplot reread パッチ
│   │   ├── _function_object_ops.py   # mixin: Tools > Add Function Object…
│   │   ├── _menu_bar_ops.py          # mixin: Case/Settings/View/Tools/Help メニューの構築
│   │   ├── _model_ops.py             # Mixin: バッファ・ツリー状態、ダーティ追跡、パースキャッシュ
│   │   ├── _panel_ops.py             # Mixin: BlockMesh パネルおよびターミナルモード切替ハンドラ
│   │   ├── _plot_ops.py              # mixin: Tools > Plot Results…
│   │   ├── _processor_ops.py         # mixin: Tools > Delete processor* Directories…
│   │   ├── _tools_ops.py             # mixin: Tools メニューの各アクション（ツール・ソルバ・Allrun・ParaView 等）
│   │   ├── _tree_crud_ops.py         # mixin: ツリー項目の CRUD（コピペ・追加・複製・コメントアウト・削除）
│   │   ├── _tree_sync_ops.py         # Mixin: エディタ↔ツリー同期（Apply Text to Tree、Reload from Tree）
│   │   ├── _undo_ops.py              # mixin: スナップショット方式のツリー Undo/Redo
│   │   ├── _ui_ops.py                # Mixin: ラベル更新、スキーママネージャ、ヘルプダイアログ、言語メニュー、ツリー列の表示切替
│   │   └── _protocol.py              # mypy 専用の MainWindowProtocol（型チェック時に各 mixin が継承）
│   ├── layout_constants.py
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── about_dialog.py
│   │   ├── add_files_dialog.py
│   │   ├── boundary_edit_dialog.py
│   │   ├── _case_dest_dialog.py      # _CaseDestDialogBase: ケース複製と新規ケース保存の共通 UI
│   │   ├── case_browser_dialog.py    # CaseBrowserDialog: 非モーダルの 2 ペイン Case Browser
│   │   ├── case_library_dialog.py
│   │   ├── clean_backups_dialog.py
│   │   ├── data_file_viewer.py       # DataFileViewer: Plot Results のデータファイルを読み取り専用で表示
│   │   ├── duplicate_case_dialog.py  # DuplicateCaseDialog: 「_copy」接尾辞、既定で全ファイルをコピー
│   │   ├── export_stl_dialog.py      # ExportStlDialog: 選択した形状を .stl に書き出す
│   │   ├── find_examples_dialog.py   # FindExamplesDialog: 非モーダルのチュートリアル検索（QThread）
│   │   ├── foam_monitor_dialog.py    # FoamMonitorDialog: ファイル選択と foamMonitor オプション
│   │   ├── function_object_dialog.py  # FunctionObjectDialog: テンプレート木・生成フォーム・ライブプレビュー
│   │   ├── generate_keywords_dialog.py  # GenerateKeywordsDialog: keyword_generator を QThread で実行
│   │   ├── keyboard_shortcuts_dialog.py
│   │   ├── line_settings_dialog.py   # LineSettingsDialog: プロットした線 1 本の凡例・X の列・スタイル
│   │   ├── log_summary_dialog.py     # LogSummaryDialog: 非モーダルの Summary／Raw Log ビューア
│   │   ├── manage_extra_files_dialog.py
│   │   ├── openfoam_resources_dialog.py
│   │   ├── plot_results_dialog.py    # PlotResultsDialog: 非モーダルのプロットウィンドウ（matplotlib）
│   │   ├── processor_delete_dialog.py  # ProcessorDeleteDialog: Delete processor* の確認
│   │   ├── rename_boundary_dialog.py  # Rename Boundary ダイアログ + find_rename_targets() スキャナ
│   │   ├── reset_settings_dialog.py
│   │   ├── run_tool_dialog.py        # RunToolDialog: Run * 共通のオプションダイアログ
│   │   ├── run_post_process_dialog.py  # RunPostProcessDialog: 関数リスト・ソルバ経由の実行
│   │   ├── run_solver_dialog.py      # RunSolverDialog(RunToolDialog) と ExecutableChoice
│   │   ├── save_as_new_case_dialog.py  # SaveAsNewCaseDialog: 「_new」接尾辞、既定でアプリが扱うファイルのみ
│   │   ├── schema_manager_dialog.py
│   │   └── _worker_thread.py         # _CancellableWorkerThread: 進捗・完了シグナルと cancel()
│   ├── panels/
│   │   ├── __init__.py
│   │   ├── _shape_overlay_menu.py    # _ShapeOverlayMenu: 形状ごとのチェック式オーバーレイメニュー
│   │   ├── _view_image_export.py     # Save Image ダイアログと画像書き出し
│   │   ├── block_mesh_panel.py       # blockMesh とオーバーレイの 3-D ビューアパネル（pyVista/VTK）
│   │   ├── block_mesh_renderer.py    # BlockMeshRenderer: VTK 描画パイプライン（RenderSettings）
│   │   ├── boundary_view_panel.py
│   │   ├── case_nav_panel.py         # CaseNavPanel: ファイルリスト横の Cases タブ
│   │   ├── comparison_tree_panel.py  # 読み取り専用の参照ケースツリー。use_value_requested(FoamNode) シグナルを発行
│   │   ├── detail_panel.py
│   │   ├── editor_panel.py
│   │   ├── file_list_panel.py
│   │   ├── shape_mesh.py             # Qt 非依存の形状ジオメトリ: make_shape_mesh() とクリップ
│   │   └── terminal_panel.py         # TerminalPanel ラッパー: mode_changed シグナル、xterm/simple 切替ロジック
│   └── widgets/
│       ├── __init__.py
│       ├── code_editor.py
│       ├── _checkable_list.py        # チェック式リスト用の checked_items()/set_all_check_states()
│       ├── flow_layout.py            # FlowLayout: 折り返すツールバーレイアウト
│       ├── installation_selector.py  # InstallationSelector: インストール選択コンボと Browse…
│       ├── _foam_highlighter.py      # FoamHighlighter: OpenFOAM のトークン着色
│       ├── _simple_terminal_widget.py  # SimpleTerminalWidget: QProcess ベースターミナル（WebEngine 不要）
│       └── _xterm_widget.py          # PtyBackend・TerminalBridge・XtermTerminalWidget（Unix + WebEngine）
└── tests/                            # パッケージ構成を写す。「テストカバレッジ一覧」を参照
```

各ファイルは 1 行の要約を持ちます。以前ここのコメントにあった詳細は、主題ごとの節に移しています: [ツールメニュー](#ツールメニュー)、[3-D ビューアのオーバーレイ](#3-d-ビューアのオーバーレイ)、[スキーマシステム](#スキーマシステム)、[UI の規約](#ui-の規約)、[ドキュメント用ツール](#ドキュメント用ツール)。`tests/` はパッケージ構成を写しており、ファイルごとの一覧は[テストカバレッジ一覧](#テストカバレッジ一覧)にあります。

### ドキュメントマップ

| ファイル | 役割 |
|---|---|
| `README.md` | 短い導入: インストール、クイックスタート、ユーザーガイドへディープリンクする要約版の機能一覧。 |
| `USER_GUIDE.md` | 全機能リファレンス。**ユーザーに見える機能を追加したら、「目的別ガイド」テーブルと目次にも必ず追加すること** — これらのナビゲーションは放っておくと静かに実態とずれていきます。 |
| `DEVELOPER.md` | このファイル: プロジェクト構成、内部構造、開発環境のセットアップ、テスト。 |
| `RELEASE_NOTES.md` | ユーザー向け変更履歴。新しい項目は `## Unreleased` の下に蓄積し、リリース時に見出しをバージョン番号へ変更します。 |
| `docs/SCREENSHOTS.md` | メインウィンドウ・BlockMesh 3D オーバーレイ・主要ダイアログ/メニューの注釈付きスクリーンショットギャラリー。 |
| `docs/DEMO_SCRIPTS.md` | デモ動画のショットごとの台本と収録方法。いずれも `tools/demo_specs.json` の実行可能なシーンなので、台本と実際の収録結果が食い違うことはない。 |
| `docs/OPENFOAM_VERSIONS.md` | ユーザー向け: OpenFOAM のリリース間・フォーク間で起きた辞書ファイルの改名を、チュートリアルツリーの実測に基づいてまとめたもの。`services/case_loader.py` が新旧両方の綴りを持つ理由の出典。 |
| `docs/SCHEMA_CANDIDATES.md` | 次にどの辞書のスキーマを書くか。実測した出現頻度とキー数で順位付けし、FoDE で手書きすべきか foamlore で生成すべきかを示す。 |
| `docs/foamlore-schema-spec.md` | foamlore とのやり取りのうち確定した側: FoDE がジェネレータに出した依頼すべてを番号付きで、測定・決定された内容とともに記録。新しい依頼はここではなく foamlore の `HANDOFF.md` に書く。 |
| `THIRD-PARTY.md` | 生成スキーマモジュールが引用する OpenFOAM ドキュメントのクレジット。`revendor.sh` が foamlore からコピーするため、ここでは編集しない。 |
| `tutorials/README.md` | 同梱サンプルケースそれぞれの出典と、何を確かめるためのものか。 |

各英語ドキュメントには日本語版（`*_ja.md`）があります（英語のみの `THIRD-PARTY.md` と `tutorials/README.md` を除く）。日本語ドキュメントではメニューラベルなどの UI 文字列は英語のまま表記します。

## パーサとデータモデル

この節では、辞書ファイルがどのように `FoamNode` ツリーになり、また元に戻るかを説明します。パーサが生成するノード型、値の分類とエラーからの回復、そして変更していないテキストをライタがそのまま再現する仕組みを扱います。

**このセクションに関わるモジュール。**

- `foam/boundary_patch.py` — 境界パッチに対する Qt 非依存の `FoamNode` 操作: `value_complexity`/`get_patch_type`/`patch_inner_text`/`parse_patch_content`（境界編集ダイアログ用のパッチ内容の読み取り/パース）と `find_rename_targets`（パース済みルート群から名前が一致する `boundary_entry` / `boundaryField` 辞書ノードを走査）。`ui/dialogs/boundary_edit_dialog.py` と `ui/dialogs/rename_boundary_dialog.py` から分離 — `QDialog` モジュールに置かれていた Qt 非依存ロジックが、パッケージ間でアンダースコア付きプライベートとしてインポートされていたため。`ui/panels/boundary_view_panel.py` と `ui/mixins/_boundary_ops.py` でも共有される。
- `foam/lexer.py` — `OpenFoamLexer`。`_read_directive` は '{' で読み取りを停止するため、`#eval{...}` の波括弧が `LBRACE/RBRACE` トークンになり深さ追跡が正しく機能する。
- `foam/value_parse.py` — `FoamTreeModel.setData` を支える Qt 非依存のテキスト→型付き値の検証。
  - `parse_text_for_node_type(node_type, text)` は文字列を `node_type` に対して再パース（int は浮動小数点風の文字列で scalar に昇格、`vector`/`int_list`/`scalar_list` は `parse_parenthesized_numbers` 経由、`box_pair` は `foam/utils.parse_box_pair` 経由、bool は単語一致、文字列系タイプはそのまま通過）。
  - `set_node_value(node, value)` が全体の契約 — `node.value`/`node_type`/`modified` をその場で書き換え、編集が受理されたかを返す。
  - `model/tree_model.py` の `setData` はこの戻り値をそのまま使って `dataChanged` と `edit_rejected` を切り替える。
- `model/tree_model.py` — `FoamTreeModel`（`QAbstractItemModel`）。`setData` の Value 列検証は `foam/value_parse.set_node_value` に委譲し、`node_type/`テキスト解析を Qt 非依存に保つ。

### ノード型

`foam/nodes.py` の `NodeType` という `Literal` が、有効な `node_type` 値の確定的な一覧です。この集合に含まれない値への代入や比較は `mypy` が検出します。各値の意味は下の表のとおりです。

**リーフ値型** — `foam/parser.py` の `_classify_value` と `foam/utils.py` の `classify_parenthesized_value` によって設定されます。

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
| `valueless` | `None` | キーの直後が `;` のもの — `fluxRequired { p; pcorr; }`、`cache { grad(U); }` など。OpenFOAM は名前の集合として読み、キーそのものが意味を担う。`_classify_value` より前に `_parse_entry` で判定し、`key;` として書き戻す |

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

`_classify_value(key, text)`（`foam/parser.py`）は、波括弧・特殊括弧以外のすべてのエントリに対して呼ばれます。優先順位は次の通りです。

1. **`box_pair`** — `key == "box"` かつ `foam/utils.py` の `parse_box_pair(text)` が成功する場合のみ。
2. **括弧付き** — `classify_parenthesized_value`（`foam/utils.py`）に委譲。`vector`（ちょうど 3 つの float）、`int_list`（すべて整数）、`scalar_list`（すべて数値で 3 つでない）、`raw_list`（それ以外）を返す。
3. **`string`** — `"` で始まり `"` で終わる。
4. **`macro`** — `$` で始まる。
5. **空白を含む** — `nonuniform List…` で始まる場合は `nonuniform_list`、それ以外は `compound`。
6. 単一トークン: `int` → `scalar` → `bool`（`BOOL_WORDS` 内のトークン）→ `word`（フォールバック）。

`_classify_value` の前に、`key ( … );` 形式のエントリはまず `_try_parse_special_parenthesized_entry`が処理を試みます。エントリの形ごとに 4 つのテーブルを順に参照します。

| テーブル | エントリの形 | 先読み |
|---|---|---|
| `_NAMED_BLOCK_PARAMS` | `name { … }` | なし — キーのみで決定 |
| `_ANONYMOUS_BLOCK_PARAMS` | `{ … }` | なし |
| `_OPTIONAL_NAMED_BLOCK_PARAMS` | `name { … }` | あり — `_looks_like_named_dict_list` |
| `_POSITIONAL_BLOCK_PARAMS` | `hex ( … ) ( … ) simpleGrading ( … )` | あり — `_looks_like_block_list` |

2 つの先読みはトークンを消費しません（`finally` で `self.index` を復元します）。そのため不採用となったエントリは何も消費しないまま通常の値解析経路に落ちます。`sets` や `blocks` があるファイルでは構造化ブロック、別のファイルでは単なる `raw_list` になれるのはこのためです。

### 再パースのトリガー

パーサが実行され（ツリーが再構築され）るのは正確に 2 つのタイミングだけです。

- **ファイルオープン** — ファイル一覧でファイルが選択されたとき、またはプログラムから読み込まれたとき。
- **Apply Text to Tree** — 下段タブバー右上の手動ボタン。

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

`_write_node`（`foam/writer.py`）は 3 つの条件がすべて満たされる場合、再生成を完全にスキップします。

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

`field_value_block` は子ノードを `node.children` ではなく `node.value`（`list[FoamNode]`）に格納する唯一の構造型です。`FoamTreeModel._child_list`（`model/tree_model.py`）がこの特殊ケースを処理します。

```python
if node.node_type == "field_value_block":
    return node.value if isinstance(node.value, list) else []
return node.children
```

`field_value_block` ノードの `node.children` は常に空のリストです。ツリーを汎用的に再帰処理するコードは、この型に対して `node.value` を反復処理する必要があります。ライタ（`foam/writer.py`）と `_has_modified_descendant` はどちらも明示的にこれを行います。

## スキーマシステム

スキーマモジュールは Detail ペインにキーの説明・対応バージョン情報・値の選択肢を提供します。実行時レジストリと基底データクラスは `schemas/` にあります。

### スキーマモジュールの書き方

スキーマモジュールはモジュールレベルで 2 つの名前を定義します。`TARGET_FILE` はモジュールが適用される辞書のファイル名（`"controlDict"`）です。リリース間で改名された辞書のように同じ項目が複数の名前に当てはまる場合は、タプルの `TARGET_FILES`（`("turbulenceProperties", "momentumTransport")`）を使います。その場合、挙げた各ファイルに同じ表が適用される点に注意してください。`SCHEMAS` は `dict[str, KeySchema]` です。1 つのファイルを複数のモジュールが対象にしてもよく、表はマージされ、両方が定義するキーは後に読み込まれたモジュールが勝ちます。乱流スキーマが構造キーと係数を別モジュールに分けているのはこのためです。レジストリは設定された各モジュールを import してこの 2 つの名前を読むので、この規約に従うモジュールは **Settings > Manage Schema Modules…**（**Add Module from File**）から他の設定なしに追加できます。

`KeySchema` と `ChoiceItem` のフィールドは [KeySchema と ChoiceItem](#keyschema-と-choiceitem) が正本です。最小のモジュールは次の通りです。

```python
from schemas._base import ChoiceItem, KeySchema, FOUNDATION_SERIES, OPENCFD_SERIES

TARGET_FILE = "myDict"

SCHEMAS = {
    "myKey": KeySchema(
        key="myKey",
        label="My Key",
        description="Controls what myKey does.",
        supported_in=(FOUNDATION_SERIES, OPENCFD_SERIES),
        choices=(
            ChoiceItem("optionA", "Use option A."),
            ChoiceItem("optionB", "Use option B."),
        ),
    ),
}
```

`SCHEMAS` のキーは単純なもの（`"startFrom"`）か、ドット付きの接頭辞で修飾したもので、サブ辞書ごとの同名キーが衝突しないようにします。`"snapControls.nRelaxIter"` はノードの直接の親が `snapControls` のときに一致します。親の名前がユーザー定義の場合（`refinementSurfaces`・`refinementRegions`・`layers` 内のエントリ）は、接頭辞を祖父母にします: `"refinementSurfaces.level"`、`"layers.nSurfaceLayers"`。ワイルドカードと閉じた名前空間の規則を含む完全な検索順序は [SchemaRegistry](#schemaregistry) にあります。

**組み込みモジュール。** `schemas/builtin.py` の `get_default_schema_config()` が既定で読み込むモジュールを列挙します。順に `control_dict`・`fv_schemes`・`fv_solution`・`block_mesh_dict`・`snappy_hex_mesh_dict/` パッケージ・`turbulence_structure`、そして生成物の `turbulence_properties`・`momentum_transport`・`transport_properties`・`physical_properties` と 2 つの `*_viscosity` モジュールです。`schema_config.json` はユーザーが選んだリストを記録します。スキーマ設定を初めて変更したとき（または設定をリセットしたとき）に作られ、それまでは既定値がディスクへ書かずにメモリから提供されます。形式は次の通りです。

```json
{
  "schema_modules": [
    "schemas.control_dict",
    "schemas.fv_schemes"
  ]
}
```

保存済みのリストには既定値が置換ではなくマージされます。[設定: デフォルトは置換ではなくマージ](#設定-デフォルトは置換ではなくマージ)を参照してください。

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
    default: str = ""
    required: bool = False
    only_in_files: tuple[str, ...] = ()
```

`KeySchema` の表示用フィールドは Detail ペインに次のように対応します。

| フィールド | 型 | 表示先 |
|---|---|---|
| `key` | `str` | 説明対象の辞書キー（単純な項目では `SCHEMAS` のキーと同じ） |
| `label` | `str` | Detail ペインのヘッダの短いラベル |
| `description` | `str` | **Key Help** フィールド |
| `supported_in` | `tuple[str, ...]` | **Key Supported In** フィールド |
| `note` | `str` | **Key Note** フィールド |
| `choices` | `tuple[ChoiceItem, ...]` | **Choices** ドロップダウン |

`ChoiceItem` が持つのは `value`・`description`・`supported_in`・`note`・`status`・`use_instead`・`deprecated_since` です。`KeySchema` の表示用以外のフィールドは次の通りです。`use_instead` は `renamed` では現在のキー名、`ineffective` では OpenFOAM が実際に読むキー。`renamed_from` は旧名の綴りで、旧名からスキーマを見つけられるようにする。`default` はキーがないときに OpenFOAM が使う値で、空は「ここには記録していない」の意味であって「デフォルトがない」ではない。`required` は読み取り側にフォールバックがないことを表し、`default` とは排他。`only_in_files` はキーをモジュールの `TARGET_FILES` の一部に限定し（空なら全ファイル）、`supported_in` から導かれ、両者が一致することをテストが確認する。各フィールドの定義は `schemas/_base.py` にあります。

`_base.py` はバージョン文字列定数をエクスポートします。`FOUNDATION_V7` 〜 `FOUNDATION_V14`、`OPENCFD_V2106` 〜 `OPENCFD_V2606`、いくつかの範囲ラベル（`FOUNDATION_V8_V14` 〜 `FOUNDATION_V12_V14`、`FOUNDATION_V7_V13`、`FOUNDATION_V7_V8`）、そして総称ラベルの `FOUNDATION_SERIES`・`OPENCFD_SERIES`・`BOTH` です。使い分けは次の通りです。

- **総称ラベル**は、共有ライブラリの `finiteVolume`/`lduMatrix` に属するキーに使います。個別リリースを 1 つだけ指定すると、詳細ペインでは「そのリリースでしか使えない」と読めてしまいます。実際、61 個のエントリが中核キーを Foundation 限定であるかのように OpenCFD ユーザーへ表示していました。
- **ただでは得られません。** 総称ラベルが免除するのは個別リリース名を挙げることであって、実測することではありません。ラベル中の区間は検証の記録で、Foundation 7-13 と OpenCFD v2106-v2606 にわたって対象エントリを監査して得たものです。新しいリリースが出ても自動的には伸びません。`FOUNDATION_SERIES` が v14 に届いているのは `tools/scan_foundation14_keys.py` がそこまで実測したからです。
- **閉じた区間と `deprecated_since` の組**は、実測して**存在しなかった**キーに使い、「確認した」ことを意味します。現在これに当たるのは `processorAgglomerator` の `FOUNDATION_V7_V13` だけです。`OPEN_ENDED_SERIES` は、フォークの終端ではなく実測の終端で止まるラベルを挙げ、詳細ペインがそれに注記を添えます。現在は空で、戻すときの規則は `tests/ui/test_supported_in_caveat.py` が強制します（`docs/foamlore-schema-spec.md` の項目 9）。
- **選択肢の値に付ける範囲ラベル**は、一方のフォークが改名した値に使います。層流応力モデル `generalizedNewtonian` に付く `FOUNDATION_V7_V8` がそれで、Foundation は v9 でクラスを*改名*した一方、OpenCFD は旧綴りを唯一の名前として今も登録しています。この選択肢は `OPENCFD_SERIES` の傍らで `status="valid"` を保ちます — `renamed` にすると、その綴りしか通らない OpenCFD ユーザーにもう一方を書けと伝えることになるためです。`deprecated_since` は Foundation 側の実測された終端を記録し、それがこのラベルを `OPEN_ENDED_SERIES` の外に留めます。

### キーが何であるかの記録: `status` フィールド

実際の辞書には、すでに現行ではない名前や、そもそも一度も機能したことのない名前が数多く含まれます。`KeyStatus` は 3 値で、詳細ペインはこれに応じて説明文を切り替えます（`DetailPanel._apply_provenance`）。

| status | 意味 | 例 |
|---|---|---|
| `valid` | 現行のキー | `scale` |
| `renamed` | 旧称。`use_instead` が後継、`deprecated_since` がバージョンを示す | `convertToMeters` → `scale`（v1012） |
| `ineffective` | 公式チュートリアルに現れるがどのリーダも読まないため、書いても何も起きない | `minFlatness` → `minFaceFlatness` |

`renamed`／`ineffective` のキーは削除せず**残します**。旧称を含むケースを開いたユーザーにこそ、それが何なのかを伝える必要があるからです。`renamed_from` は**現行**キー側に置き、その旧称を列挙します。

### キーを省略したときどうなるか: `default` と `required`

もう 2 つのフィールドが 1 つの問いに答えます。そのため Detail パネルでは両者に**「省略した場合」**という単一の行を与えています(`_if_omitted_text`)。`default` は OpenFOAM が代わりに使う値で、ソースの書き方そのままを記します。`required` はフォールバックが一切ないこと、つまり省略はエラーであることを示します。両者は**排他**であり、いずれかのスキーマが両方を設定すると `tests/schemas/test_default_and_required.py` が失敗します。

両者を健全に保つ規則: **ある事実は `default`／`required` か `description` のどちらかに置き、両方には置かない。** `description` はキーの**意味**を述べ、これらは省略したときに何が起きるかを述べます。したがって空の `default` は**沈黙**であって主張ではありません。生成された乱流モジュールは既定値を prose として `description` に持ち、フィールドは空のままなので、`""` を「既定値が存在しない」と読むとそれらすべてが必須扱いになってしまいます。不在を主張するのは `required=True` だけです。

存在意義が明確なのは `required` の方で、理由は `CrossPowerLaw.C:71-78` です。`nu0`・`nuInf`・`m`・`n` をフォールバックなしで読んでおり、これまでそれを表現する手段は、コードが解釈できない一文しかありませんでした。機械可読であるため、`required` は将来の「ケースに OpenFOAM が必要とするキーが欠けている」検査の裏付けになり得ます。prose の既定値ではそれができません。`default` は 2 つのうち弱い方で、主な意義は、スキーマが既に持つ事実を生成 prose が重複して述べるのをやめられる点にあります。どちらのフィールドも `ChoiceItem` には付けません。既定値はキーに属するものであり、その値の 1 つに属するものではないからです。

リネーム情報の出所: OpenCFD は `getCompat("newName", {{"oldName", apiVersion}})`、Foundation は `lookupBackwardsCompatible<T>({"newName", "oldName"})` という形で、リネームを機械可読な形でソースに宣言しています。抽出は**手作業の転記ではなく生成**です。foamlore の `facts/tools/scan_renames.py` がこの 2 系統の呼び出しを全 19 チェックアウトにわたって走査し `facts/derived/renames.json` にまとめ、`render_renames.py` がそれを [docs/OPENFOAM_VERSIONS.md](docs/OPENFOAM_VERSIONS_ja.md) の生成領域 `renames-table` にスプライスされる表へ変換します。現在の走査範囲での実測は、**重複のない改名対 21 件、未解決 0 件**です。互換エントリが後に削除されて古いツリーにしか残らないものもあり、たとえば `minMedianAxisAngle` は OpenCFD では v2206 まで、Foundation では現在も受け付けられます。

この走査は `sources/*/`、つまり**チェックアウトされているものだけ**を読みます。そのため到達範囲はチェックアウトとともに広がります。`controlDict` が範囲に入った途端に `turbOnFinalIterOnly` の 3 リリース分の不具合が見つかりました(`docs/foamlore-schema-spec.md` 項目 10)。一方で**生成されない**のはキー単位の帰結です。個々の `KeySchema` の `renamed_from`・`use_instead`・`deprecated_since`・`status` は、導出された表をもとに手で設定します。ある対が全体的な改名なのかフォーク間の不一致なのかは、表が下せない判断だからです。`turbOnFinalIterOnly` が典型例で、Foundation は改名しましたが OpenCFD は現行名として読むため、無条件に `renamed` と印を付けると OpenCFD 利用者に「自分のフォークが無視するキーを書け」と言うことになります。

### 生成モジュール（foamlore からのベンダリング）

`GENERATED by foamlore` バナーを持つモジュールが `schemas/` に 11 個あります。これらは**生成ファイル**で、姉妹リポジトリ foamlore（`facts/tools/generate_fode_schemas.py` と `generate_transport_schemas.py`）から、引用検証済みのファクトストアをもとに取り込んでおり、説明文は OpenFOAM のソースを引用しています（クレジットは `THIRD-PARTY.md`）。ここでは編集せず、foamlore で再生成して再コピーしてください（テストがバナーの存在を検証します）。5 つの系統があります。

- **乱流モデルの係数** — `_turbulence_coeffs.py` と、薄いファイル別モジュール `turbulence_properties.py`（`constant/turbulenceProperties`: OpenCFD v2106-v2606 と Foundation v7）、`momentum_transport.py`（`constant/momentumTransport`: Foundation v8 以降）。`_turbulence_coeffs.py` は **29 モデル**（RAS 16、LES/DES 13 — 両フォークが出荷する全モデル）の係数を保持し、19 リリース全部（Foundation 7-14、OpenCFD v2106-v2606）の `.C` コンストラクタから機械的に抽出して、それらのリリースにわたって実測した `supported_in` タグとソース既定値の `ChoiceItem` を付けています。係数キーは親修飾（`kOmegaSSTCoeffs.beta1`）で出力され、OpenFOAM の `optionalSubDict` 読み取りイディオムに合わせて素のフォールバックキーも付きます。同じ名前を複数のモデルが読む場合、素のエントリは所有する全モデルを列挙し、各モデルの既定値を提示します。薄いモジュールがそれぞれ呼ぶ `build_schemas(target_file)` を公開しています。
- **層流応力モデルの説明文** — `_laminar_models.py`: `MODEL_DOCS` のみ。
- **LES delta モデルの説明文** — `_delta_models.py`: LES の `delta` セレクタ用の `MODEL_DOCS` のみ。
- **`transportProperties` の粘度モデル** — `_transport.py` と `transport_properties.py`、`physical_properties.py`。Foundation は v10 で `constant/transportProperties` を `constant/physicalProperties` に改名し、非ニュートン流体モデルを運動量輸送のツリーへ移したため、`physicalProperties` が読むのは `nu` だけです。2 つのファイルは同じ表ではありません。
- **入れ子の一般化ニュートン粘度モデル** — `_generalised_newtonian.py` と `turbulence_properties_viscosity.py`、`momentum_transport_viscosity.py`: 層流の `generalizedNewtonian` 辞書内の `viscosityModel` セレクタで、乱流モジュールと同じ 2 つのファイルが対象です。

**ファイル名ごとに薄いモジュール 1 つ。** Foundation は OpenFOAM 8 で `constant/turbulenceProperties` を `constant/momentumTransport` に改名したため、ファクトは共有の `_*.py` モジュールに 1 度だけ置き、各ファイル名には約 25 行のモジュールが `TARGET_FILE` を宣言して `build_schemas` を呼びます。共有モジュールは import されるだけで登録されません。`TARGET_FILE` を持たないので `SchemaRegistry` は読み飛ばします。**対を `TARGET_FILES` の 1 モジュールに統合しないでください。** `_build_file_key_schemas` は複数ファイルを挙げたモジュールのテーブルを各ファイルへ**同一のまま**マージするため、OpenCFD 専用のキー（`decayControl`、`GEKOCoeffs` 全体）が `constant/momentumTransport` の中で解決してしまいます — OpenCFD のどのリリースも読まないファイルです。共有しているのはファクトだけで、バージョンタグ・注記・既定値一覧はすべて対象ファイルに依存します。文字どおりの統合を安全にするには、レジストリにキー単位の対象フィルタが必要です（`docs/foamlore-schema-spec.md` を参照）。

**境界を越える散文。** `_turbulence_coeffs` は `MODEL_DOCS`（`モデル名 → (説明, 注記)`。モデル自身のヘッダにある要約と、引用している論文）も公開しており、`turbulence_structure.py` がこれを import して `RAS`/`LES` モデルセレクタの選択肢を組み立てます。手書きと生成の境界を意図的に跨いでおり、向きが重要です。選択肢の*リスト*とその `supported_in` タグは辞書についての構造的な事実で手書きモジュールが所有し、各名前に対する散文は抽出されたものです。

laminar セレクタは `_laminar_models.MODEL_DOCS`（`docs/foamlore-schema-spec.md` の項目 12）から、LES の delta セレクタは `_delta_models.MODEL_DOCS` から、同じ仕組みで供給されます。laminar のテーブルを別モジュールにしてあるのは、散文だけを持ち（`SCHEMAS` も `TARGET_FILE` も無い）、foamlore がこの系統について係数キーを一切出力しないからです。テストは、laminar のすべての名前が存在すること、そして散文テーブル同士が互いに素であることを要求します。`_model()` の統合参照が、どちらのモジュールを後に書いたかに左右されないようにするためです。

手書きのまま残るのは、どのヘッダにも書かれていない事柄、つまり各名前の `supported_in` の範囲と、`generalizedNewtonian`/`generalisedNewtonian` がフォークによる改名でどちらも相手の綴りに対する互換宣言を持たないという但し書きで、後者は `_model()` が抽出された注記を置き換えるのではなく*追記*します。同じ境界はもう 1 段深く、各層流モデル自身の係数辞書（`MaxwellCoeffs`・`GiesekusCoeffs`・`PTTCoeffs`・`lambdaThixotropicCoeffs`）にも及びます。foamlore が意図的に出力しない半分なので手書きであり、実際のケースが使う 3 通りの綴り（OpenCFD の `<Model>Coeffs`、Foundation の素の `<Model>`、両フォークがフォールバックするフラット形式）のいずれでも解決します。

**選択肢リストの出所。** リストは**実行時の選択テーブル**、つまり `makeRASModel`・`makeLESModel`・`makeLaminarModel` に渡される名前を 19 チェックアウト全体で走査したもので、ディレクトリ一覧では**ありません**。`.../turbulenceModels/LES/` を読んだことが、かつて 4 つの DES モデルを Foundation 専用と誤らせました。OpenCFD はそれらを隣の `DES/` ディレクトリから登録しているためです。選択テーブルに無い名前はソースツリーに何があろうと構築できず、それこそが選択肢リストの答えるべき問いです。これがないとモデルの説明は `<Model>Coeffs` — 既定値を上書きするケースにしか存在しないキー — 経由でしか到達できません。散文の import は `TARGET_FILE` を宣言しないモジュールの単純な import なので、`schemas/builtin.py` の読み込み順は関係しません。セレクタのキー自体はこれとは異なり、生成側では意図的に出力していません（生成モジュールは `turbulence_structure` の*後*に読み込まれるため、出力すると衝突ではなく暗黙の上書きになります）。

**入れ子の `viscosityModel` セレクタ。** `constant/transportProperties` の同名セレクタ（`_transport.py`）と同じ選択肢の*値*を使いますが、この 2 つは異なるソースディレクトリ下で独立に実装された C++ クラスです。最初は `MODEL_DOCS` と同じ安全な再利用に見えたため、推測せずソースで確認した事実です。実際には安全ではありません。OpenCFD の入れ子の `BirdCarreau` は `nuInf`/`k`/`n`/`a` を読みます（`nu0` は無く、これを持つ `transportProperties` の `BirdCarreau` とは異なります）。Foundation の入れ子の `BirdCarreau` は `nuInf`/`k`/`tauStar`/`n`/`a` を読みます。`HerschelBulkley` と `powerLaw` も、Foundation の入れ子クラスが OpenCFD には無い `k` を追加している点で同様に食い違い、`Casson` と `CrossPowerLaw` は両フォークで同一です。したがって共有の 6 つの選択肢*名*は正しい値で（両フォークの実行時登録に対して検証済み）、各選択肢自身の係数も解決します。クラスごとに正しく分けたのが、`_generalised_newtonian.py` の上に立つ `turbulence_properties_viscosity.py` と `momentum_transport_viscosity.py` で、`_turbulence_coeffs.py` と同じ、実測・引用検証された厳密さで生成されています（`docs/foamlore-schema-spec.md` の項目 13）。`transport_properties.py` のスキーマを再利用していれば、6 クラスのうち 3 つで誤った係数集合を報告していたはずです。

**ベンダリングは両側から守られており、2 つのガードは別々の問いを立てます。** foamlore 側の `facts/tests` は（兄弟ディレクトリの FoDE チェックアウトを既定で見ます）自身の `fode-schemas/` をこの作業ツリーと比較します。FoDE 側の `tests/schemas/test_vendored_modules.py` は逆にこのツリーを `../foamlore/fode-schemas/` と比較し、さらに各ベンダリング済みモジュールが **git に入っていること**を検査します。これはどちらの側からも行えなかった検査です。`schemas/_laminar_models.py` は一度、`turbulence_structure.py` が import しているにもかかわらず、ベンダリング済み・バイト一致・未追跡の状態にあり、すべての検査が緑のまま clone すれば `ImportError` になるツリーを通していました。ベンダリングはコピーで、コピーは未追跡ファイルを残します。`revendor.sh` が報告に使う `git diff --stat` は未追跡パスを一覧しないため、新しく届いたモジュールは `git add` してください。モジュール一覧は名前を並べるのではなく `GENERATED by foamlore` バナーから導出するので、新しい系統が追加された時点で自動的に対象になります。無条件に走るのは git の検査だけで、比較は foamlore チェックアウトが無ければスキップされ、探索先は `FOAMLORE_ROOT` で上書きできます（反対側の `FODE_ROOT` と同じ約束です）。

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

`load_schema_config()` は保存されたファイルをそのまま返し、`SchemaRegistry._effective_config` が `union(組み込みデフォルト, 保存値) - disabled_modules` を計算します。以前は保存済みリストが唯一の正でした。そのため後のリリースで `schemas/builtin.py` にモジュールを追加しても、**Manage Schema Modules…** を一度でも開いたことのあるユーザーには永久に届きませんでした。設定はその日のリストに固定されてしまうからです。現在は、ユーザーが明示的に削除したモジュール（`set_schema_modules` が `disabled_modules` に記録）だけが除外されます。`disabled_modules` が存在する前に書かれた設定には意図の記録がないため、当時削除したモジュールは一度だけ再表示されます。これは安全側の選択です。余分なスキーマは目に見えてクリック 1 回で削除できますが、欠けたスキーマは目に見えません。

`reload()` は `schema_config.json` をディスクから再読み込みしてテーブルを再構築します。`apply_and_reload()` はディスクに触れずに現在のインメモリ設定からテーブルを再構築します（同一セッション内で **Settings > Manage Schema Modules…** が変更を適用した後に使用）。

## 差分アルゴリズム

`foam/diff.py` は 2 つの `FoamNode` ツリーを比較し、比較パネルの色付けに使うアノテーションマップを生成します。

**このセクションに関わるモジュール。**

- `foam/diff.py` — `diff_trees(a, b)` と `diff_trees_reverse(b, a)` — キー名で 2 つの `FoamNode` ツリーを比較し `dict[FoamNode, DiffEntry]` を返す。
- `ui/mixins/_diff_ops.py` — Mixin: サイドバイサイド比較、差分の計算・クリア。`_reset_diff_for_case_dir` は `_load_case_dir` 後にアクティブな比較を調整（ケース切り替え時はクリア、同一ディレクトリの再読み込み時は再アーム）。参照ファイルの解析失敗はステータスバーで報告（`_recompute_diff` ではファイル単位、事前計算スキャンの最後にはスキップ件数のサマリ）。

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
    "block_list",
})
```

子ノードは `node.name` で照合します。無名ノード（`name` が空）はスキップします。`field_value_block` については `_diff_field_value_block` が `node.value` の `field_name` でアイテムを照合します（[`field_value_block` の子ノードが `value` に格納される](#field_value_block-の子ノードが-value-に格納される)と同じレイアウト）。`action_list` については `_diff_action_list` が `action_entry` の子ノードを**インデックス順（位置）** で照合し、各エントリの名前付きサブエントリをキーで比較します。`action_entry` ノード自体は無名（`name=""`）のため名前で照合できません。`block_list` は、名前ではなく**位置**で対応付ける唯一の構造型です。子の `block_entry` は匿名なので、`_diff_block_list` はブロック 0 同士、ブロック 1 同士…を比較します。そのため、5 ブロックのうち 2 つが違う `blockMeshDict` は `≠1` ではなく `≠2` と表示されます。それ以外の位置ベースのリスト項目（`vertices` など）と匿名ノード（`#include`、`$macro`）には注釈が付きません。

等値は `_equal(a, b)` で判定します: `a.node_type == b.node_type and a.value == b.value` のとき `True`。

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

**C++ ヘッダーの除外。** `#codeStream` の本体には C++ ソースを取り込む本物の `#include` 行が含まれ、これらがファイル一覧に混入してはいけません。両方の入口に 2 つの規則を適用します。トークン全体が山括弧のもの（`^<.*>$`。`<constant>/caseSettings` は `>` で*終わらない*ため対象外）と、`.H/.h/.C/.cc/.cpp/.hpp/.hxx` の拡張子です。v2512 チュートリアルに対して実測したところ、これで過不足なく機能します。当該コーパスの誤検出（`createTime.H`、`argList.H`、`fvCFD.H`、`setRootCase.H` など）はすべて `.H` で終わり、辞書のインクルードで終わるものは 1 つもありません。とはいえ証明ではなくヒューリスティックです。`#{ … #}` の深さ追跡なら厳密ですが、安価な行スキャンに留めるべき処理の中で本物の字句解析が必要になります。認識されない対象は単に解決されないだけで無害なため、2026-11-14 の見直しで「更新候補」から外しました。

v2512 チュートリアル全体では 1081 件中 1072 件のディレクティブが解決します。残る 9 件は `Allrun` が生成するファイル（`blockMeshDict.caseBlocks`、`constant/ignitionPoint`）か、`0.orig/` をコピーして初めて存在する `0/` 配下のファイルで、未実行のケースでは「見つからない」が正しい報告です。

**スキャンは 1 段階のみで、再帰的ではありません。** インクルードされたファイル自身は、そのインクルードについてスキャンしません。この制限は*ファイル一覧*側のものです — 次に述べる展開は深さ上限の範囲で再帰的です。

**このセクションに関わるモジュール。**

- `foam/include_resolver.py` — `parse_include_directive()` と `resolve_include()`: インクルード対応のうち Qt 非依存のテキストからパスへの変換部分。上で説明。
- `foam/include_expand.py` — `expand_includes()` が 3-D ビューア向けの読み取り専用のマージ済みコピーを作り、`clear_expand_cache()` がそのパースのメモを破棄する。[3-D ビューア向けのインクルード展開](#3-d-ビューア向けのインクルード展開)を参照。
- `services/include_scan.py` — インクルード対応のディスク側: `foam_etc_dirs()`・`scan_includes()`/`included_files()`・`copy_destination_for()`。上で説明。

### 3-D ビューア向けのインクルード展開

インクルードされたファイルを一覧に出せば開いて編集はできますが、それを取り込んでいる辞書を*描画*するには足りません。寸法を 1 つのファイルにまとめたケース — `blockMeshDict` と `topoSetDict` の先頭に `#include "settings-region"` を置き、`scale`・`x0`・`xMax` などをそこだけに定義する — は何も表示されません。`var_resolver.build_var_map` は `root.children` しか走査せず、抽出関数の入口はどれもその単一ルートしか受け取らないため、他ファイルの定義が入る余地がないからです。結果として `parse_vertices` は解決できない座標三つ組をすべて捨て、`scale` も黙って 1.0 にフォールバックします。

`foam/include_expand.py` の `expand_includes(root, source_file=…, case_dir=…, etc_dirs=…, read_text=…) -> ExpandedTree` がこれを解消します。解決可能なインクルードの `directive_entry` を、指し示すファイルのエントリで**記述順に**置き換えます — OpenFOAM はテキストとして挿入するため、後の定義が先の定義を隠し、順序が意味を持ちます。インクルード先自身の `FoamFile` ヘッダーは除去します。`boundary ( … )` の中に差し込まれた場合、偽のパッチとして読まれてしまうためです。

**マージ後のツリーは読み取り専用であり、これは覚えておく規則ではなく構造上の性質です。** `ui/mixins/_model_ops.py` は `_update_viewer_panels` を、元のルートを使い続ける boundary 側と、展開を呼ぶ唯一の場所である `_update_block_mesh_viewer` に分割しています。したがってツリービュー・エディタ・ライター・Detail ペイン・保存経路はマージ後のツリーを一切見ず、どう編集しても別ファイルのエントリが書き込まれることはありません。ここから派生する 2 つの性質も重要です。

- **元のツリーは決して変更しません** — 展開はコピーオンライトで、ルートから差し込み位置までの経路だけを作り直し、配下にインクルードを持たない部分木は共有します。インクルードの無いファイルは*ルートオブジェクトそのもの*が返るため、通常のケースでは一切の確保が起きません。
- **マージ後のツリー内の親ポインタは意味を持ちません。** 差し込む各エントリは浅いコピーにしますが（パースのメモは毎回同じノードオブジェクトを返すため、親を付け替えてはいけません）、その孫はキャッシュ側のツリーを指したままです。これを読むものは存在しません — 上方向に辿る抽出関数は 1 つもありません。共有が安全なのはこの事実によるので、上方向に辿るコードを足す際は必ず確認してください。

検査で確認済みの点として、`BlockMeshPanel` はマージ後のルートを `self._root` に保持しますが読むだけです — 頂点テーブルの編集は `vertices_changed(row, xyz)` を通り、`MainWindow` が `state.current_root` に適用します。またマージ後のツリーは元の `vertices` ノードを*共有*するため、`_vertices_have_variables()` は従来どおり `$` を検出し、読み取り専用／**⚙ Variable-based** モードはそのまま働きます。

**`#includeFunc` は意図的に展開しません。** その対象は既にファイル一覧に解決されて単体で描画されており（`controlDict` に `#includeFunc sample` を持つケースは `system/sample` からサンプリング線を得ます）、ここでも差し込むと同じジオメトリを二重に描くことになります。

**失敗は何事でもありません。** 解決できない・読めない・パースできない・循環している・深すぎるインクルードは、その `directive_entry` をその場に残し、テキストを `ExpandedTree.unresolved` に記録します。ビューはエラーにならず未展開のツリーにフォールバックします。対象の無い `#sinclude` は OpenFOAM として正当なので、そもそも報告しません。循環ガードは分岐ごとの*実*パス集合なので、シンボリックリンクの別名も一致します。

**インクルード先の編集でビューが更新されます。** `settings-region` はビューアの辞書ではないため `_update_block_mesh_viewer` の名前テーブルには一致せず、何もしなければ寸法を変えても 3-D ビューは構築時の値を表示し続けます。`AppState.viewer_include_sources` がビューア辞書のパスごとに直前の展開で消費したファイル集合を保持し、`_refresh_include_dependents` が編集されたパスを含む辞書を再描画します。再実行するのは 3-D 側だけです — boundary テーブルはユーザーが実際に見ているファイルに紐づくためです。未保存のエディタバッファがディスク上のファイルより優先されるので（`read_text`）、保存前の編集にもビューが追随します。

**キャッシュ。** 抽出はツリー編集のたびに走るため、インクルード先は一度だけパースして `(mtime, size)` でメモ化します（スキャン側のメモと同じ方式）。`clear_expand_cache()` はケース切り替え時とクローズ時に `clear_scan_cache()` と並べて呼びます。バッファ由来のテキストはメモを経由しません — 小さなファイル 1 つで、しかも dirty の間だけだからです。

**一覧への反映。** `services/case_loader.list_case_files` はあえて変更していません。これはケースの許可リストであり、`services/case_copier.copy_visible_files`（ケースの複製時に `/usr/lib/openfoam/…` をコピーしてはいけない）と Add-files ダイアログの `loaded_set` が依存しています。インクルードはその後に `_case_file_paths`（`ui/mixins/_file_ops.py`）が追加し、`_load_case_dir` と `_reload_file_list` の両方がこれを呼びます。既に一覧にある対象は通常の見た目のままで、スキャンが*追加した*行だけが `_INCLUDED_ROLE` と `↳` マーカーを持ちます。重複排除は解決後の実パス（シンボリックリンクの別名も一致）で行い、*表示*パスはインクルードの綴りのままです。`.gz` に解決した場合は `resolved` と報告しつつ一覧からは除外します（`foam/utils.py` の `read_foam_file` が展開できないため）。

`model/file_list_model.py` の `_group_name` は 1 箇所だけ変更しました。`except ValueError`（ケースディレクトリ配下でないパス）の分岐が新しい `INCLUDED_GROUP` センチネル（`"<included>"`、順序 2000 で `ROOT_GROUP` より下）を返します。ケース*内*のインクルードは `relative_to` に成功して `constant`/`system`/`0/heater` などの本来のグループへ自動的に収まります — グループ分けの規則はこれだけです。`case_dir is None` の経路のために従来の `p.parent.name` フォールバックは残しています。

**読み取り専用の契約。** ケース外のインクルードは表示のみで書き込みません。編集すれば全ケースが共有するファイルを変えてしまうためです。同じ集合には、実際の場所がケースの外にある一覧上のファイル（リンク、リンクされたディレクトリの下のファイル）もすべて入り、書き込みのハンドラはディスク上でもう一度確かめます。[書き込みはケースの中に留める](#書き込みはケースの中に留める) を参照してください。述語は `_is_read_only(path)`（`ui/mixins/_model_ops.py`）1 つだけで、一覧読み込みのたびに `_case_file_paths` が再構築する `state.read_only_files` を参照します。ゲートは 10 箇所です。`_mark_dirty`/`_mark_path_dirty`（**実質的な錠前**。dirty にならないことで `*` マーカー・Save All・未保存確認がまとめて成立しなくなります）、`save_file`、`save_all_files`、`EditorPanel.set_read_only`、`FoamTreeModel.flags`（`ItemIsEditable` を与えないことでインライン編集*と*値の貼り付けの両方が無効化されます）、`DetailPanel._populate_normal`、ツリーのコンテキストメニューの変更系項目、`apply_text_to_tree`、そして `_create_backup`/`_on_delete_file_requested`/`_on_duplicate_file_requested`（いずれも当該ファイルかその隣に書き込みます）、そして `ui/mixins/_boundary_ops.py` の境界のハンドラ（保存できないバッファを変えてしまうため）。`ui/mixins/_diff_ops.py` は変更不要です — `_recompute_diff` と `_precompute_diff_step` は既に `relative_to(case_path)` を `try/except ValueError` で囲んでおり、ケース外ファイルは自動的にスキップされます。この既存のガードが今や本質的な役割を担っています。

**ケースにコピー**（`_on_copy_into_case_requested`、`ui/mixins/_file_mgmt_ops.py`）が逃げ道で、読み取り専用の行にのみ表示されます。コピー先は `include_scan.copy_destination_for` が決めます。`includeFunc`/`includeEtc` は `system/<name>` に平坦化し、相対パスを持つ素の `#include` はその相対パスを維持するので、ディレクティブを一切編集せずにコピー先へ再解決されます。包含チェックは事前に正規化します — `Path.relative_to` は純粋に字句的なので、そうしないと `<case>/../escaped` が通ってしまいます。処理後は `_reload_file_list()` を呼びます。`_load_case_dir` では未保存バッファがすべて失われるためです。

**ツリー側の導線。** `directive_entry` の行はコンテキストメニューに **Open Included File** を持ち、Key/Type 列のダブルクリックにも反応します（Value 列はディレクティブが値編集可能なのでインライン編集のままです）。どちらも `_open_included_target` に繋がります。解決結果の注記は `FoamTreeModel.set_include_notes` 経由でツールチップと Detail パネルの注記行に届きます。これは `_load_tree` の直後にキャッシュ済みのスキャン結果から与えられるため、モデルがツールチップ描画のためにディスクへ触ることはありません。注記はディレクティブのソーステキストそのものをキーにするので、`IncludeHit` は再構成ではなく生の一致行を保持しています。

## ケースとファイル

FoDE がケースとその中のファイルを見つけ、一覧にし、開き、整理する仕組みです。どのファイルをケースの一覧に出すかは `services/case_loader.py` が決めます。既定の対象リスト（`TARGET_FILES`・`REGION_SYSTEM_FILES`・`REGION_CONSTANT_FILES`・`PHASE_FILE_BASES`・`VARIANT_FILE_BASES`）と、改名された辞書は両方の綴りを一覧に出すという規則は、同モジュールの docstring と `tests/services/test_case_loader.py` にあるため、ここでは繰り返しません。

**このセクションに関わるモジュール。**

- `model/case_tree_model.py` — `CaseTreeModel`（`QAbstractItemModel`）: ルート配下のディレクトリを保持し、ケースには ◆ の記号を付けて*降りていかない*。`QFileSystemModel` をあえて使っていない理由は後述の「ケースナビゲーション」参照。翻訳対象の文言は持たず、ツールチップのフォーマッタは注入される。
- `services/backup_files.py` — `find_backup_files(case_dir)`: ケース配下の `<name>.bak_YYYYMMDD_HHMMSS` ファイルすべてについて [(`abs_path`, `rel_path`, `size_bytes`)] を返す。`ui/dialogs/clean_backups_dialog.py` の削除チェックリストに使われ、`ui/mixins/_file_mgmt_ops.py` から呼び出される。
- `services/case_fs_ops.py` — ケースディレクトリに対する Qt 非依存の移動・リネーム・コピー・削除・新規フォルダ作成と、その手前にある安全確認ロジック: `check_*()` は Refusal *コード*を返し、`perform_*()` が実処理を行う。`perform_delete` は削除処理を注入で受け取る作りで、実体は Qt の `QFile.moveToTrash()`。
- `services/case_paths.py` — FoDE がケースに書き込むすべての操作に使う、ただ一つの包含判定: 操作ごとの `editable`/`writable`/`creatable`/`removable`/`removable_tree` と、Duplicate Case / Save As 用の `copy_destination_problem`。ディスク上で解決して判定します（[書き込みはケースの中に留める](#書き込みはケースの中に留める)を参照）。
- `services/case_loader.py` — `VARIANT_FILE_BASES` と `_list_variant_files` により `system/<viewerDict>*` を自動で一覧に載せるため、`topoSetDict-slices` と `topoSetDict-background` を持つケースでも手動の Add files は不要。それ以外の一覧済み辞書については `system/` と `constant/` で `_list_suffixed_variants` が同じことを、より厳しい条件で行います（[サフィックス付きの派生ファイル](#サフィックス付きの派生ファイル)を参照）。`detect_poly_mesh()` も含む -- `constant/polyMesh/owner` の `FoamFile` note フィールドから `PolyMeshInfo(n_points, n_cells, n_faces, stale)` を生成。
- `services/case_scan.py` — ケースナビゲーター向けの Qt 非依存ディレクトリ一覧: `list_subdirectories()` -> `DirEntry(path, name, is_case, is_symlink, readable, has_subdirs)`。ディレクトリのみを対象とし隠しエントリは除外、OSError に対して安全。`case_summary()` は行のツールチップ用に `case_loader` のタイムディレクトリ・`polyMesh` 探索をラップする。
- `ui/case_navigation.py` — `CaseNavigator`（`QObject`）: Cases タブと Case Browser ウィンドウの背後にある共有コントローラ -- 1 つの `CaseTreeModel`、1 つの現在位置、両ビューが発するすべてのシグナルを持つ。下位層の上に立つ `tr()` 利用層でもある: `refusal_message()` が `services/case_fs_ops` の Refusal コードを文へ変換し、`describe_entry()` が行のツールチップを組み立てる。
- `ui/mixins/_case_nav_ops.py` — Mixin: Case Browser / Cases タブのハンドラ — `CaseNavigator` のシグナルはすべてここに届く。`_close_case()` も含む。`_case_ops.py` から分離（下記「ケースナビゲーション」を参照）。
- `ui/dialogs/_case_dest_dialog.py` — `_CaseDestDialogBase`（`QDialog`）: `DuplicateCaseDialog` と `SaveAsNewCaseDialog` が共有するソース/宛先（親+名前）/プレビュー/コピーモード UI の基底クラス。サブクラスは自身のコピーモードラジオグループを構築し `_finish_layout` を呼ぶ。
- `ui/dialogs/case_browser_dialog.py` — `CaseBrowserDialog`: **非モーダル**（`log_summary_dialog`・`find_examples_dialog`・`case_check_dialog`・`allrun_steps_dialog` と同様）の 2 ペイン構成のケースブラウザ — フォルダツリーとディレクトリ一覧を並べ、Cases タブが使うのと*同じ* `CaseNavigator`・`CaseTreeModel` の上で動くため両者がずれることはない。状態も操作ロジックも持たず、すべてのボタンは `navigator.request_*()` を呼ぶ。
- `ui/dialogs/save_as_new_case_dialog.py` — `SaveAsNewCaseDialog`（`_CaseDestDialogBase`）: 名前サフィックスは "`_new`"、デフォルトで「Copy app-visible files only」が選択済み、未保存の編集についての斜体注記ラベルを追加。
- `ui/panels/case_nav_panel.py` — `CaseNavPanel`: `main_splitter` インデックス 0 でファイル一覧の隣に並ぶ「Cases」タブ（どちらも `MainWindow.left_tabs` の中）。ケースディレクトリを 1 階層ずつ辿るブラウザで、ケースをダブルクリックすると降りていくのではなく*開く* — ケースの中身を扱うのはファイル一覧の役目だから。

### 書き込みはケースの中に留める

ケースは他人から受け取ることがあり、シンボリックリンク（別の場所のファイルを指す `system/fvSolution`、リンクされたディレクトリ）や、ケースの外へ出る `#include "../../x"` を含むことがあります。`Path.relative_to` のような文字列の比較ではどちらも見えません。`<case>/system/../../x` は `<case>/` で始まるからです。そこで FoDE がケースに書き込むときは必ず `services/case_paths.py` を通します。ここではパスをディスク上で解決し（`os.path.realpath(strict=True)`）、解決済みのケースディレクトリとパスの要素ごとに比べます。解決できないパスは拒否します。ケース外のファイルを**読む**ことは引き続き行います。ユーザー自身のデータを表示することは危険ではないからです。

**操作ごとに一つの規則**を使います。「中にある」の意味が操作ごとに違うためです。

| 操作 | 判定 | その後 |
|---|---|---|
| Save、Save Case、バックグラウンド実行の停止での `controlDict` の書き換え | `editable`（実際の場所が中にある通常ファイル）。`writable` はディスク上で消されたファイルの作り直しも認める | 書き込む |
| New File、Backup、Duplicate File、Copy into Case、Add Function Object | `creatable`: その名前に何もない（壊れたリンクも不可）、存在する最も近い祖先が中のディレクトリ、`..` を含まない | `write_foam_file(..., exclusive=True)` / モード `"x"` |
| Delete File、Clean Backups | `removable`: それを**含む**ディレクトリが中にある | `os.unlink`。リンクを消し、リンク先は消さない |
| Delete Directory、Duplicate Directory のコピー元 | `removable_tree`: ルートより下の本物のディレクトリ（リンクではない） | `rmtree` / `copytree(symlinks=True)` |
| Delete processor\* Directories | チェックの段階ですべての `processor*` に `removable_tree`（問題 `outside`。実際のパスを示す）、さらに各対象を消す直前にもう一度 | `rmtree` — それ自体がリンクのパスは拒否しますが、*親*にあるリンクはたどるため、リンクされた `processor0` の下の `processor0/<time>` にはこの判定が必要です |
| Duplicate Case、Save As New Case | 上書き確認の**前に**、そして確認の後にもう一度 `copy_destination_problem`: コピー元そのもの、その中、それを含む場所、リンクのいずれでもない。解決済みパスで比べ、解決しても一致しない書き方についてはデバイスと inode でも比べる | コピーし、その後の未保存バッファの書き込みで両端を再確認 |

**二段構え。** `_case_file_paths` は、`editable` を満たさない一覧上のパスすべて（とケース外の include 先すべて）を `state.read_only_files` に入れ、UI はこれを読みます（斜体の行、ロックされたエディタ、**Copy into case...** のみ）。この集合はファイル一覧を読み込んだ時点のものなので、書き込み処理はそれぞれ書く直前にもう一度確かめます（`ui/mixins/_file_mgmt_ops.py` の `_edit_refused`、`_create_refused`、`save_all_files` の `writable`）。強制しているのは二段目で、一段目はユーザーに見せるためのものです。新しい書き込み経路には、読み取り専用集合を見るだけでなく、その操作の判定が必要です。

**コピー。** 表示ファイルのみのコピーは、実際の場所が外にあるもの（ケースの設定ファイルを含む）を飛ばし、ダイアログが一覧表示する `CopyReport` を返します。全ファイルのコピーは `copytree(symlinks=True)` を使います。リンクはリンクのまま残り、リンク先の中身は新しいケースに入らず、新しいケースを開いたときに改めて判定されます。`_write_dirty_buffers_to` は、バッファをコピー元に対して、さらにコピー後のコピー先に対して確かめます。コピーされたリンクがバッファの書き込みを受けてはならないからです。

**Save As は、未保存の編集がすべて新しいケースに届いたときだけ新しいケースを開きます。** ケースを開くとすべてのバッファが消えるので、拒否された、または書き込みに失敗した編集はどちらのケースにも残らなくなります。その場合は元のケースを未保存のまま開いておき、メッセージで新しいケースの場所を示します。一覧にある `#include` のパスは `..` を含むことがあります（`system/../constant/x`）。新しいケースでの位置を求めるために文字列として畳みますが、畳んだ名前がディスク上で同じファイルである場合に限って受け付けます。`..` の前にリンクがあれば同じファイルにはなりません。

**文字列だけでなく同一性も。** `realpath` は与えられた書き方を保つので、大文字と小文字を区別しないファイルシステム（macOS、Windows）では、大文字小文字だけが違う 2 つのコピー先が異なる文字列に解決され、同じディレクトリを指します。`_identity_overlap` は、コピー先とその祖先を、コピー元とその祖先と `os.path.samefile` で比べます。テストは、別名と、それを解決しない `real_path` でそうしたファイルシステムの代わりをしています。大文字と小文字を区別しないファイルシステム上では実行していません。

**確認ダイアログの後に、もう一度判定する。** モーダルの確認はいくらでも長く開いたままにできます。Save（ディスク上で変更されたときの質問）、ケースの上書き、Duplicate Directory、Copy into Case のリンク置き換えは、確認から戻ったときに判定を繰り返します。残るのは、下に書いた判定と書き込みの間の一瞬だけです。

**ルートを固定する。** FoDE はケースを開いたときのパスを保持し、書き込みのたびに解決します。そのため、そのパスが別のディレクトリを指すようになると（フォルダーの名前が変えられ同じ名前に新しいものが置かれた、リンクの向け先が変えられた）、バッファが古いほうのファイルを保持したまま、すべての判定が新しいほうに対して通ってしまいます。`_load_case_dir` は `pin_case_root` を呼び、パスの解決先とそのディレクトリのデバイスと inode を記録します。`case_paths.py` のすべての判定は `_root` を通してルートを得ており、`case_root_changed` になると `_root` は None を返します。`_load_case_dir` はすべてのバッファを消すので、そこで固定すればバッファと固定先は同じケースになります。新しいフォルダーを受け入れる手段は Reload Case です。開いているケースは一度に 1 つなので、固定はモジュールレベルの値 1 つで、ほかのディレクトリに対する判定（Save As のコピー先）はこれに縛られません。ケースを開いたときに特定できなかったルートは、そのように固定されて同じく拒否するので、後から現れたパスに固定なしで書き込むことはありません。`CaseFilesConfig.save`/`delete_config_file` は自分で `case_root_changed` を確かめ、False を返します。ケースの再読み込みで終わる操作（Add files、Reset File List）は、先に `_case_folder_replaced` で止まります。内部の再読み込みは新しいフォルダーを固定してバッファを消してしまい、それをしてよいのは Open と Reload Case だけだからです。開いているケースに対して `_load_case_dir` を呼ぶ新しいハンドラーには、このガードが必要です。

**1 つのファイルには 1 回の書き込み。** 一覧の 2 つの名前がディスク上で同じファイルであることがあります。ケース内の別のファイルを指すケース内のリンクや、2 つのファイルが別々の書き方で取り込む 1 つの include です。include スキャンは実ファイルごとに 1 行だけを一覧に出し（最初に見つかった書き方）、`conflicting_writes` がその後ろの備えになります。`file_identity`（デバイスと inode）でまとめるので、大文字と小文字を区別しないファイルシステムでの大文字小文字の違いやハードリンクも 1 つのファイルとして数えます。include スキャンの重複判定のキーも同じです。Save Case と Save As は、同じ実ファイルを共有し内容が異なる 2 つの未保存バッファのどちらも書かず、両方を報告します。順に書くと、後のほうが黙って勝っていました。Save As はこれを 2 回行います。コピー元に対してと、バッファを 1 つも書く前に予定したコピー先に対してです。コピー元の 2 つのファイルが新しいケースでは 1 つのファイルになることがあるためです。

**リンクの置き換え**（それ自体がリンクである行での Copy into Case）は、質問で示したリンク先をコピーし、質問から戻ったときにリンクがそこを指していなければ中止します。コピーをリンクの隣にランダムな排他的な名前で書き、`os.replace` でリンクの上に置きます。読み取りや書き込みに失敗してもリンクはそのまま残ります。以前は先にリンクを削除していました。

**設定ファイルの書き込み**（`app_config/json_io.atomic_write_text`）は、一時ファイルをランダムな名前で排他的に作ります。以前は固定の `<name>.tmp` を使っており、ケースがそこにシンボリックリンクを置いておくと、次の設定保存でリンク先が上書きされました。`os.replace` はディレクトリエントリを入れ替えるので、最終的な名前にあるリンクは置き換えられ、リンク先に書き込まれることはありません。既存ファイルはモードを保ち（`lstat` で読む）、新しいファイルは `new_mode` から umask を引いたモードになります。ユーザーごとの `app_config.json` は `0o600` です。

**境界の操作**が変えるのはバッファであってファイルではなく、読み取り専用ファイルは未保存の印が付きません。そのためガードがないと、リンクされた `0/U` への編集はパネルには現れるのに、黙って保存されないままでした。`ui/mixins/_boundary_ops.py` の単一ファイルのハンドラは `_read_only_refused` で拒否し、名前の変更・全ファイルからの削除・全ファイルへの追加は読み取り専用ファイルを対象から外して、ステータス行に名前を示します。**Export Shapes as STL** はユーザーが選んだフォルダーに、ケースの辞書から取った名前で書き込むため、すでにシンボリックリンクになっている名前は飛ばします。

**保証をひとことで。** FoDE が判定した時点のパスについて、FoDE がケースのために行う書き込み・作成・削除は、開いたフォルダーの中の、ユーザーに示したファイルに届き、未保存のバッファを別のバッファで置き換えることはありません。**保証の範囲外**として文書化しているもの: 判定と書き込みの間の一瞬に変えられたエントリ（判定は確認ダイアログのたびに繰り返しますが、書き込みの間じゅう保持するわけではありません）、ケースのファイルから外のファイルへのハードリンク、ターミナルで実行するコマンド（Tools > Run …、Allrun、バックグラウンド実行のラッパーとその `log.*` ファイル）。これらはどのシェルとも同じくリンクをたどります。Plot Results は独自の出力規則（`services/plot_output.py`）を持ちます。テスト: `tests/services/test_case_paths.py` と `tests/ui/test_case_containment.py`。

### サフィックス付きの派生ファイル

チュートリアルは辞書の別案を、サフィックスを付けてその横に置きます: `decomposeParDict.4/.8/.16`（プロセッサ数ごとに 1 つ）、`refineMeshDict.tier6` や `extrudeMeshDict.1`（`-dict` で実行）、`controlDict.orig` や `fvSchemes.template`（スクリプトがコピーして使う）、`dynamicMeshDict.sixDoF`（別の設定）。OpenFOAM がこれらを読むのは、コマンドが名前で指定したときか、スクリプトが本来のファイルに上書きコピーしたときだけですが、どれも同じ種類の完全な辞書です。そこで FoDE は淡色で一覧に載せ、そのことを伝えるツールチップを付け、元の辞書のスキーマを与えます。

一覧に載せる規則は 2 つです。4 つのビューア用辞書は、ヘッダの有無にかかわらず接頭辞一致のまま（`VARIANT_FILE_BASES`、`_list_variant_files`）です。`blockMeshDict.m4` や `topoSetDict-slices` こそビューアの存在理由だからです。`system/` と `constant/` のそれ以外の名前は `foam/variants.variant_base`（`_list_suffixed_variants`）を通り、2 つの条件を満たす必要があります:

- **一覧済みの名前の後に区切りがあること** — `.`、`-`、`_` または数字。単純な接頭辞一致では `gravitationalProperties` を `g` の派生、`sampleDict` を `sample` の派生とみなしてしまいます。初期の接頭辞だけの試みでは余分な行が 398 行表示され、その多くがこうした誤一致でした。
- **ヘッダが一致すること** — ファイルの `FoamFile` の `object` が元の名前（`decomposeParDict.4` → `object decomposeParDict`）か、ファイル自身の名前（`topoSetDict.2`、`createBafflesDict.baffles`）であること。別の辞書を名乗るコピペのヘッダは除外します（`setAlphaFieldDict.liquid` は `setFieldsDict` を名乗っており、載せると setFields のオーバーレイに回されてしまいます）。ヘッダのないファイルも `#include` の断片として除外します。自分の名前を名乗っていても、兄弟ファイルが `#include` しているものは断片です: foamyHexMesh の `meshDict.geometry` は `foamyHexMeshDict` に取り込まれており、cfMesh の `meshDict` の派生として載せると、include スキャンが付ける `↳ included from` の印も失われます（そのスキャンは一覧済みのパスを飛ばすため）。

ローカルの 13 チュートリアルツリーすべて（v2212–v2606、Foundation 7–12 と dev、4,855 ケース）で計測: 309 ケースで 595 行増え、93% のケースは変化なし、コールドな一覧作成で 1 ケースあたり約 0.4 ms。隠れたまま残るのは意図した除外です — コピペのヘッダ 45 件（旧名 `extrudeProperties` を名乗ったままの `extrudeMeshDict.1`、`setAlphaFieldDict.*` の組）と、ヘッダのない断片・取り込まれる断片。同じ変更で `chemistryProperties` と `combustionProperties` を `PHASE_FILE_BASES` に加えました: その相ごとの `.gas`/`.vapour` ファイルは派生ではなく相ファイルです。

ヘッダと兄弟の include の読み取りは `foam/variants.py` が各ファイル自身の `(mtime_ns, size)` でメモ化します — 兄弟のメモは、その場での編集では動かないディレクトリの mtime ではなく、全兄弟の stat を鍵にします。`clear_variant_cache()` はケース切り替え時に `clear_scan_cache()` と並んで実行されます。`schemas/registry.SchemaRegistry._schema_file_name` は、自身のスキーマのファイル名を元の名前として同じ `variant_base` を使うので、`controlDict.orig` は controlDict の表から答え、断片の `meshDict.geometry` はどの表からも答えません。ファイル一覧が行を淡色にするために尋ねるのは `services/case_loader.listed_variant_base`（`_VARIANT_ROLE`）です。

### ケースナビゲーション

*1 つの*ケースについてのすべてはファイル一覧の仕事です。ディスク上のケース群についてのすべて — 開く・比較するケースを見つける、完了した実行結果をアーカイブフォルダへ移動する、リネーム・コピー・削除する — はケースナビゲーターの仕事であり、そのためにファイルマネージャへ FoDE を離れる必要はありません。

**2 つのビュー、1 つのコントローラ。** `CaseNavigator`（`ui/case_navigation.py`）が単一の `CaseTreeModel`・現在位置・すべてのシグナルを保持します。`CaseNavPanel`（**Cases** タブ。`MainWindow.left_tabs` 内でファイル一覧と並ぶ `main_splitter` インデックス 0）と `CaseBrowserDialog`（非モーダルな 2 ペインウィンドウ）はどちらもその上のビューにすぎず、互いの存在を知りません。ウィジェットは `navigator.request_*()` を呼び、`MainWindow._connect_signals` が各シグナルを 1 度だけ `ui/mixins/_case_nav_ops.py` のハンドラへ接続します。これによりタブとブラウザがずれることはありません — 両者は同じ位置にある同じモデルであり、操作後のリフレッシュはモデル 1 箇所で 1 回だけ起きます。

**ケースの間を辿るのであって、ケースの中へは入らない。** `is_openfoam_case` が受理するディレクトリにはマークが付き、*葉*として扱われます: `hasChildren()` はそれに対して `False` を返し、ダブルクリックすると展開ではなくケースを開き、単体のファイルは一切一覧に出ません。`is_openfoam_case` の判定はゆるく（`system/` か `constant/` のどちらかを持つディレクトリなら該当）、誤検出はサブツリーを隠してしまいます — その逃げ道はパスごとの **Show Subfolders** コンテキストアクション（`set_descend_override`）であり、アプリが開けて当然のケースにマークが付かなくなるような厳格な規則にはしていません。

**`QFileSystemModel` を使わない理由。** このビューが必要とする 4 つの性質のうち 3 つは、そのクラスの契約を拡張するのではなく矛盾させます: ケースの中へ降りてはならない（`QFileSystemModel` はどのみち中身を読み込んでしまい、プロキシは転送される `rowsInserted` と矛盾せずにソースより少ない行数を報告することはできません）、行にケースバッジが必要、そして並び順は独自のものにしたい、の 3 点です。`QFileSystemModel` が買えるのはファイルシステムを忠実に映すことですが、これは*ケース*ブラウザであり、そのノード集合は意図的にファイルシステムそのものではありません。忠実であることが仕事のモデルを、3 つの点で意図的に嘘をつくモデルへ改造するより、小さく素直な `QAbstractItemModel` を書くほうがコードは少なく済み、しかも同期的なので、ビューもイベントループも無しでテストできます。

**ケースのマーカーはアイコンではなくグリフです。** `DisplayRole` は `◆ <name>` を返します。`ui/icons.py` の `ICON_NAMES` はディスク上のファイルと双方向にアサートされているため、アイコンを 1 つ増やすのは実際にコストがかかります。ファイル一覧も既にこの方式でマークしており（シンボリックリンクは `⇢`、インクルードは `↳`）、グリフは選択されても消えませんが `ForegroundRole` の色は消えてしまいます。開いているケースを `FontRole` の太字でマークしているのも同じ理由からです — `FontRole` は選択中の行にもそのまま適用されます。

**`ui/` より下に翻訳対象の文言を置かない。** `tests/test_i18n.py` は `ui/` しか走査しないため、`model/` や `services/` にある `tr()` の文字列リテラルは `i18n/ja.py` と照合されることがなく、気づかれないまま未翻訳で出荷されてしまいます。そのため `services/case_fs_ops.py` は `Refusal` *コード*を返し、`ui/case_navigation.py` の `refusal_message()` がそれを文へ変換します。同様に `CaseTreeModel` も自前でツールチップを組み立てず、注入された `describe` 呼び出し可能オブジェクトを使います。

#### 開いているケースに対する規則

> パスをキーとするアプリケーション状態を、その場で書き換えることは決してない。破棄したうえで `_load_case_dir()` を通じて再構築する。

ソースが `state.current_case_dir` を含む、またはそれと等しい操作は、ユーザーが同じダイアログの中で開いているケースを片付けたあとにのみ許可され（`_settle_open_case_for`）、その後は次の順に進みます: 未保存の編集を片付ける → 解放する → ファイルシステム操作を行う → `_load_case_dir(new)` で入り直す、削除の場合は `_close_case()` を呼ぶ。開いているケースの**祖先**に対する操作は端的に拒否されます — ユーザーがそれを意図している可能性はまずなく、名指ししていないケースを黙って閉じることはデータ損失を伴う予期しない事態だからです。

移動を追いかける実装にするなら、`current_case_dir`・`current_file`・`file_buffers`・`file_dirty`・`read_only_files`・`parsed_roots`・`case_files_config`、diff 状態の両半分、そして各 `UndoSnapshot` が持つ 2 つのパスキー辞書を正しく書き換える必要があり、さらにウォッチャーのパス・ターミナルの作業ディレクトリ・BlockMesh パネル・キャッシュ済みのログダイアログも対象になります。`_load_case_dir` はこれらすべてを既に行っており、ケースを開くあらゆる経路が通る単一の合流点です。書き換え漏れは*沈黙して*起きます — `list_case_files` は存在しないディレクトリに対して `[]` を返すため、古いケースディレクトリはエラーなしにファイル一覧を空にしてしまいます。これは考えられる中で最悪の結果であり、部分的なキー書き換えが陥る既定の結末でもあります。

`_close_case()` は `_load_case_dir` の逆にあたり、ウィンドウをケースを開いていない状態にする唯一の経路です。

重要な順序が 2 つあります。`_stop_foam_monitor()` は削除の*前*に実行されます。そうしないと gnuplot が削除済みの inode へ書き込み続け、一時スクリプトの後始末がテアダウンと競合してしまいます。また `.foam-editor-files.json` は移動に際して何の手当ても要りません — パスをケース相対で保存しており、ディレクトリの中身として一緒に移動するためです。

#### 消滅したケースディレクトリのガード

`_reload_file_list`（`ui/mixins/_file_ops.py`）は、再一覧表示する前に `state.current_case_dir` が今もディレクトリとして存在するかを確認し、存在しない場合は再読み込みせずステータスバーに報告します。

そうする必要がある理由は、`list_case_files` が存在しないディレクトリに対して `[]` を返すからです — その中のあらゆる分岐が `is_file()`/`is_dir()`/`glob` でガードされているため、何も例外を送出しません — そして `load_files([])` がパネルを空にしてしまいます。この失敗は完全に沈黙しており、ユーザーの目にはケースが持っていたファイルを全部失ったかのように映ります。一覧とバッファをそのままにしておくことで、未保存の作業は引き続き **Save as New Case…** で救い出せます。

`_on_case_dir_changed_on_disk` が発火の原因になった `path` 引数を無視して、それを再読み込みしようとしない理由もここにあります。ウォッチャーの 2 つの挙動がこの引数を信用できないものにしています — Qt は監視中のディレクトリが*リネーム*された場合、その inode を黙って追跡し続けながら**旧**パスで報告してきます（`watcher.directories()` は、もう存在しない文字列を返し続けます）。加えてウォッチャーはケースディレクトリとその `constant/` サブディレクトリの両方を監視しているため、1 回の `cp -r` が両方から発火します。`current_case_dir` を読み直してそれが存在するかを確認すれば、この 2 つのケースに 1 回のテストで対応できます。

この不具合は Case Browser より前から存在していましたが、それをワンクリックの距離まで近づけたのが Case Browser です — FoDE の中からケースを削除すれば `_close_case()` を通るので問題ありませんが、同じディレクトリの変化がターミナルから届くとそうはなりません。

#### 削除はデスクトップのゴミ箱へ

`shutil.rmtree` でも `send2trash` でもなく `QFile.moveToTrash()`（`ui/mixins/_case_ops.py::_trash_directory`）を使います。PySide6 6.11.1 で確認済み: 空でないディレクトリツリーを扱える、ゴミ箱ディレクトリを持たないマウントには freedesktop 仕様の `.Trash-<uid>/` を作成する、シンボリックリンクはリンク先を残したままゴミ箱へ送る、権限エラー時は読める `errorString()` を伴って `False` を返す、をそれぞれ確認しています。`requirements.txt` は `PySide6>=6.6` の 1 行だけであり、新しいランタイム依存を増やすことは、`QtCore` が既に提供しているものを得るためだけに行数を倍にすることになっていたはずです。

`False` が返った場合のフォールバックは、**Delete Permanently** を提示する*2 段階目*の、明示的な文言による確認です。黙って完全削除されることはありません。下限は `>=6.6` のままで、実測したのは 6.11.1 のみである点に注意してください — ディレクトリのサポートは Qt 自身のドキュメントでも曖昧な部分であるため、要件のバージョンを引き上げるのではなく `tests/ui/test_case_browser_state.py` がその挙動を固定しています。

#### 拒否にダイアログは出さない

拒否された操作は `STATUS_WARNING` としてステータスバーに報告されます（`_refuse_case_nav`）。拒否はユーザーに判断を求めているものではないため、モーダルを出す価値はありません — モーダルという予算は、実際に進められる操作のために取っておきます。テストはこれを直接アサートしています — `QMessageBox` をモックでパッチし、一度も呼ばれていないことを確認します。

#### 永続化

最後に閲覧していた場所は `WindowState` のフィールドではなく `app_config.json` の `case_browser_dir` キーです。これはレイアウトではなく `default_case_dir` と同じ並びの好み設定です。`WindowState` を使うのは 2 重の意味で誤りだったはずです — `session_key()` によって*フィーチャーセットごと*にキー分けされるため `--variant no-terminal` では別のディレクトリを記憶してしまいますし、セッション復元がオンのときしか書き込まれませんが、ブラウザはそれに関わらず場所を覚えているべきだからです。開始位置の連鎖は `case_browser_dir` → `default_case_dir` → 開いているケースの親ディレクトリ → `Path.home()`（`CaseNavigator.initial_location`）です。

### 追加ディレクトリ

`case_files_config.py` は、ケースごとの追加ディレクトリ一覧を `list[DirEntry]` として保存します。`DirEntry = tuple[str, bool]` は `(rel_path, recursive)` を表します。このフラグにより、ディレクトリをフラットスキャン（`Path.iterdir()`）するか再帰スキャン（`Path.rglob("*")`）するかが決まります。

- `add_dir(rel_path, recursive=False)` は新規エントリを追加するか、パスが既に存在する場合はフラグをインプレースで更新します。
- `remove_dir(rel_path)` はパスで絞り込んでエントリを除去します。
- JSON は `[{"path": "...", "recursive": true/false}]` 形式で保存されます。プレーン文字列を格納した旧 JSON は後方互換のため非再帰として読み込まれます。

`case_loader.py` の `list_case_files` は `extra_dirs: list[tuple[str, bool]] | None` を受け取ります。フラットエントリは `sorted(d.iterdir(), key=...)` で、再帰エントリは `sorted(d.rglob("*"), key=lambda p: (str(p.parent), p.name.lower()))` で処理され、ディレクトリ→ファイル名の順に並びます。`TARGET_FILES` と共有する重複排除セットにより、同一パスが 2 回現れることはありません。

`FIELD_DIRS` のスキャン（`0/`、`0.orig/`）はまず直下のファイルを収集し、次に存在するサブディレクトリを 1 階層だけ下ります。これにより `chtMultiRegionFoam` ケースでよく見られる `0/heater/T` や `0/bottomWater/p` のようなリージョンごとのフィールドファイルが拾われます。`_group_name` はこれらのパスに対してすでに `"0/heater"` を返すため、ファイル一覧では自動的に専用のグループヘッダーの下に表示されます。バウンダリパネルの `_available_field_dirs` はこの検出をミラーし、Directory セレクタに `"0/heater"` などを表示します。`_is_in_dir` は複数階層のディレクトリ名を正しく照合するために `Path.is_relative_to` を使用します。

`manage_extra_files_dialog.py` では **Toggle Recursive** ボタンで選択中のディレクトリエントリの再帰フラグを切り替えられます。生パスは各アイテムの `Qt.UserRole` に格納され、再帰が有効な場合は表示テキストに `[recursive]` が付加されます。`result_dirs` プロパティは最終的な `list[DirEntry]` を返します。`_file_mgmt_ops.py` はこの値を使ってステータスバーの集計（追加・削除・フラグ変更の件数）を計算します。

### ケースルートのスクリプト

`list_case_files` はケースルート直下も `ROOT_SCRIPT_GLOB`（`All*`）で glob するため、`Allrun`、`Allrun.pre`、`Allclean` などが自動的に一覧へ追加されます — これらは Tools メニューが実行するスクリプトであり、一覧に含めることで `copy_visible_files` が複製ケースにも引き継ぎます（`shutil.copy2` が実行権限を保持）。それ以外のルート直下のファイル（ログ、`*.foam`、結果）は従来どおり表示されません。`model/file_list_model.py` はルート直下のファイルを `ROOT_GROUP`（`"."`）キーでグループ化して最後にソートし、`file_list_panel.py` はそのヘッダーを「case root」と表示します（`group_display_name` 経由。ヘッダーのコンテキストメニューや Add files ダイアログのラベルにも使用）。`[+]` マーカーは付けません（ルートにはほぼ常に未表示のログが存在し、マーカーが常時点灯してしまうため）。ヘッダーには他のグループと同じ New file / Add files コンテキストメニューがあり — pathlib が `"."` を正規化するためどちらのハンドラもそのまま動作します —、`list_directory_files` はドットファイルを除外するため、Add ダイアログに `.foam-editor-files.json` が現れることはありません。

スクリプトは辞書ではなくシェルファイルなので、テキスト専用の処理経路を通ります。`is_script_text` / `is_script_path`（`foam/utils.py`）が `#!` シバンを検出し、`is_log_filename` は同じ経路を `log.*` 実行ログ（ユーザーの追加ディレクトリ経由で一覧に入り得る）にも拡張します。`load_selected_file` と `save_file` はどちらの場合も解析をスキップし（ツリーには `_clear_current_file` と同様に空のルートが読み込まれます）、`apply_text_to_tree` はステータスメッセージを出して拒否し、diff の両経路（`_recompute_diff`、`_precompute_diff_step`）もスキップするため、無意味なツリー diff は表示されません。`log.*` の行はさらに `file_list_panel.py` の `_TEXT_ONLY_ROLE` によりグレーで薄く描画されます（色の優先順位: dirty > diff > text-only > extra）。保存は通常の `Path.write_text` で既存ファイルをそのまま書き換えるため、実行権限は保持されます。

エディタはスクリプトをシェルコードとしてハイライトします。`EditorPanel.set_text` がシバンを検出して `CodeEditor.set_shell_mode` を呼び、`FoamHighlighter`（`ui/widgets/_foam_highlighter.py`）を `"shell"` モードに切り替えます — `#` コメント、引用符付き文字列、`$変数`、OpenFOAM の RunFunctions（`_SHELL_KEYWORD_RE`）、さらに通常の `_build_value_kw_rules()` キーワードチャンクも適用されるため、ユーティリティ・ソルバー名も色分けされます。シェルモードでは `/* */` ブロックコメントの状態機械はバイパスされます。

`list_case_files` の追加ディレクトリスキャンは隠しエントリ（`.` で始まるパス要素）を常にスキップするため、ケースルート（`"."`）を追加ディレクトリとして登録してもアプリ自身の `.foam-editor-files.json` がアプリ内で編集可能になることはありません。

### 同じ辞書が複数あるケース

1 つのケースが同じ辞書を既定でない名前で複数持つことがあります。`topoSetDict-slices` と `topoSetDict-background` が並ぶ形や、チュートリアルで使われる `topoSetDict.1` / `.2` / `.3` の形です。そして `topoSet -dict <名前>` がそれぞれを順に実行します。これを 3-D ビューで扱うには 2 つの別々の作業が必要で、2 つめは見落としやすいものです。

**ファイルを識別する。** `ui/viewer_dicts.py` の `viewer_dict_kind(path, root)` はまずファイル名を試し、次にそのファイルの `FoamFile` ヘッダの `object` エントリを見ます。これは「その辞書が何であるか」に対する OpenFOAM 自身の答えであり、ファイル名が何であろうと変わりません。両フォークのチュートリアルツリーで計測したところ、ビューアの辞書らしい名前でありながら完全一致はしない 138 ファイルのうち、118 が基底の辞書名を `object` に持ち、さらに 12 がバリアント名（`object topoSetDict.1`）を持っていました。後者は区切り文字でガードした前方一致で拾えます。

残る 4 つが、これをファイル名の前方一致にしていない理由です。`blockMeshDict.resolvedBlocks` とその同類は `#include` される*フラグメント*であり、辞書に包まれていない裸の `hex (…)` の並びです。これをブロックメッシュの抽出に回すと、本物のシーンが空のシーンに置き換わってしまいます。これらに `FoamFile` ヘッダが無いのは、まさに辞書ではないからです。したがってヘッダを読むことで、描画すべきファイルを見つけることと、描画すべきでないファイルを外すことが、1 つの判定で同時に達成されます。

サンプリングは名前でもヘッダでも判定できません。関数オブジェクトのファイルはどんな名前でもよく（OpenCFD v2606 のチュートリアルだけでも `sampling`、`cuttingPlane`、`sampleLines`、`samplingDebug`、`sampleU` などがあり、Foundation には `functions` があります）、ほとんどは `FoamFile` ヘッダを持ちません。そこで最後に中身で判定します — `_defines_sampling`: 最上位、最上位の辞書、または `functions` の中に、`sets`、`surfaces`、probes 系の `type` があること。見るのはこの範囲とサンプリングの型だけなので、snappyHexMeshDict の `geometry` の中の `type searchableBox` が該当することはありません。v2606 と Foundation-12 のチュートリアルの `system/` にある 5,102 ファイルで、従来の名前の一覧に加えて 66 ファイルが該当し、いずれもサンプリングの関数オブジェクトを含んでいました（damBreak の `system/sampling` もその 1 つ）。名前やヘッダですでに判定されていたファイルは変わりません。

**見つけたものをマージする。** 識別だけでは足りません。最後に渡されたファイルだけからオーバーレイを作り直すと、2 つめの `topoSetDict` が 1 つめを消してしまうためです。そこで各オーバーレイが `dict[path, Data]`（`_topo_by_file` など。既存の `_sampling_by_file` に倣ったもの）を保持し、`BlockMeshPanel._merge_by_file` を通して和集合を作り直します。キーはベース名ではなくフルパスなので、追加ディレクトリに 2 つめの `topoSetDict` があっても機能します。何も生成しなかったファイルは空エントリとして残すのではなくストアから削除されるため、ある辞書を空にするとその行だけが消え、他はそのまま残ります。

行に `[ファイル名]` のサフィックスが付くのは、**そのオーバーレイに複数のファイルが寄与しているときだけ**です（`_ShapeOverlayMenu._attribution`。寄与したファイル数を知っている唯一の場所です）。ほとんどのケースは `topoSetDict` を 1 つしか持たず、そこで全行に名前を付けるのは情報ではなくノイズになります。

**自動判定では決められない場合。** ファイルの右クリックメニューに **Show in 3-D view as** サブメニューがあります。選択肢は「自動判定」、4 つの辞書のいずれか、または「サンプリング」です。これはヘッダでは決められないケースのためにあります。名前を変えたサンプリング辞書は関数オブジェクトのエントリ 1 つであり、`FoamFile` ヘッダがそもそも無いため、読むものがありません。ヘッダの記述が単に間違っているファイルにも使えます。そうした場合、そのファイルが何であるかは利用者には分かっていて、プログラムには分かりません。

この上書き指定は 2 つの判定のどちらよりも優先されます。未知のキーは振り分けられずに無視されるため、`.foam-editor-files.json` を手で編集して存在しないオーバーレイ名を書いても効きません。保存先はそのファイルの `viewer_kinds` マップで、ケース単位かつ追加ファイル一覧と同じくケース相対です。そのため Case Browser でケースディレクトリを移動しても一緒に付いていきます。この選択はセッションについての事実ではなく、そのケースのファイルについての事実だからです。

変更や解除は、まず `BlockMeshPanel.forget_file(path)` を通ります。再描画だけでは後片付けができません。そのファイルが以前に寄与していたオーバーレイは、いま書き込まれている側とは別であり、「自動判定」に戻した場合はそもそも何も振り分けられないため、古い行を消すものが存在しないからです。

マージされたビューが主張し*ない*ことが 1 つあります。`topoSet` のアクションは逐次実行であり、辞書が `action invert` で終わることもあります。オーバーレイは読み込まれた全ファイルの全アクションについて、その元になるジオメトリを同時に描きます。それらを実行した結果として得られるセルセットの絵ではありません。これは `topoSetDict` が 1 つのときも同じで、2 ファイルが並ぶと誤読しやすくなるだけです。

### ツールメニュー

Tools メニューは `ui/mixins/_menu_bar_ops.py` が構築し、ハンドラは `_tools_ops.py`（メッシュツール・ソルバ・`decomposePar`/`reconstructPar`・Allrun スクリプト・ParaView・ログサマリの実行）、`_processor_ops.py`（`processor*` の削除）、`_background_run_ops.py`（FoDE より長く続く実行）、`_function_object_ops.py`（関数オブジェクトの追加）、`_case_check_ops.py`（Check Case）、`_allrun_ops.py`（Allrun Steps、Create Allrun from Logs）、`_plot_ops.py`（Plot Results）、`_foam_monitor_ops.py` にあります。Qt を必要としないロジックは `services/` にあります。全体を貫く規則が 1 つあります。ターミナルへコマンドを送るアクションは、まず `_refuse_while_running` を呼びます。ターミナルが使用中だとコマンドが待ち行列に入るか、xterm ターミナルでは `mpirun` に入力として飲み込まれてしまうためです。

#### Run ダイアログの仕組み

「Run *」アクションはすべて、`services/tool_options.TOOL_SPECS` の `ToolSpec` から構築した `RunToolDialog` を開きます。ダイアログは、厳選オプション（両フォークに共通するフラグをチェックボックスやフィールドで。ファイルオプションにはケース相対パスを挿入する Browse ボタン付き）、それ以外のフラグ用の自由入力欄、実際のコマンドラインのライブプレビューから成ります。`build_command` は `shlex` でシェルクォートし、`2>&1 | tee log.<tool>` を付加します。ログサマリ機能と Allrun の事前チェックはこのファイル名に依存しています。オプション値はセッション中ツールごとに `state.run_tool_options` に記憶されます。メッシュツールは数値の結果ディレクトリがあると事前警告を出し、アクションはケースが開かれていてターミナルパネルがあるときだけ使えます。`RunSolverDialog` と `RunPostProcessDialog` は `_build_extra_sections`・`_resolved_spec`・`_run_prefix`・`_parallel_np` のフックでダイアログを拡張します。

#### postProcess とソルバ

関数の実行方法は `services/post_process.py` が決めます。`needs_solver` は関数の**型**で判断します（`system/<name>` ファイル自身の型、なければその `#includeEtc` テンプレートの型、なければ名前。前方一致なので `forcesIncompressible` も該当します）。ソルバの乱流・輸送モデルを使う関数（`yPlus`・`wallShearStress`・`forces`・`forceCoeffs`）はソルバ経由で実行する必要があります。単独で実行すると終了コード 0 で何も計算せず、ログには「Unable to find turbulence model in the database」とだけ出ます（v2606 の pitzDaily で確認）。`-func` を付けない実行（`controlDict` の全関数）もソルバが必要です。素の `postProcess` ではフィールドが一切読み込まれず、各サンプリング関数が「Cannot find registered field」をログに出して何も書き出さないためです。関数を 1 つ指定すれば（`-func probes`）、どちらの方法でも自身のフィールドが読み込まれます。`invocation` は、単独、`<application> -postProcess`（OpenCFD、Foundation 10 まで）、`foamPostProcess -solver <module>`（Foundation 11 以降）のいずれかを返します。ログは `build_command` の `log_name` により `log.<tool>` に出力され、ソルバのログには混ざりません。Add Function Object の「今すぐ実行」オプションも同じ規則を使います。

#### バックグラウンド実行

ターミナルでの実行は FoDE を閉じると終わってしまうため、Run Solver と Run Allrun Script は切り離した実行を開始できます。`services/background_run.py` は次のように組み立てます。

- `background_command()` は `setsid -f` で実行を開始します。新しいセッションなのでハングアップが届かず、ターミナルシェルの子でもないので、FoDE を閉じても確認は出ません。ログは `< /dev/null` を付けて直接書き込みます。`nohup` だけでは、ターミナルを閉じると `tee` が殺され、ソルバが SIGPIPE で死ぬため不十分です。
- 小さな `sh` が自身の `$$`（すでに終了した `setsid` を指してしまう `$!` ではなく）を隠しファイル `.fode-background-run` に書き、終了時に空にします。何も削除はしません。ターミナルは `tail -F --pid` でログを追い、`services/process_tree.FOLLOWERS` により単独の `tail` は実行中のジョブとは数えません。`TerminalPanel.run_command` は、タイプする前にこの `tail` へ SIGTERM を送ります。シェルは `tail` が去った後でバッファ済みのコマンドを読むためです。
- `active_run()` は記録された pid の `/proc` の cwd をケースと照合するので、古い pid や再利用された pid は実行とみなされません。記録される pid はラッパーの `sh` で、実行全体（ラッパー、`mpirun`、すべてのソルバ）を含むプロセスグループの先頭です。そのためケース内に残るグループのメンバーも実行とみなします。素の `kill <pid>` はラッパーだけを終わらせてソルバを孤児にしますが、これは 2 つ目の実行として拒否され続けなければなりません。実行を止めるのは `kill -- -<pid>` で、すべてのメッセージとユーザーガイドがこの形を示します。kill の後に後始末は不要で、残った `.fode-background-run` は古いものとして扱われます。
- **Stop Background Run** は OpenFOAM 自身の `stopAt writeNow` です。`request_stop` は、inotify で監視するソルバが握る inode を保つため `controlDict` を**その場で**書き換え、元の値と実行・要求の時刻を `.fode-stopAt-restore` に記録します。実行が終わると `finish_stop` が元に戻し、`StopReport` を返します。最後に書き出された時刻は、新しい時刻ディレクトリではなく、ソルバログの最後の `Time =` 行（Foundation では `s` 接尾辞付き）から取ります。再開された実行の前任者が、より後の時刻ディレクトリを残している場合があるためです。`clean` はログが `End` で終わっているかどうかです。`controlDict` に未保存の編集がある場合や `runTimeModifiable` が off の場合は、ソルバが要求を見ないため停止を拒否します。
- `MainWindow._poll_background_run` が `_background_run_timer` とケース読み込み時に実行を追跡し、`_update_background_badge` がツールバーのバッジとウィンドウタイトルの接尾辞を設定します。`closeEvent` は、閉じるのをキャンセルできる 2 つの質問の後で `_remind_background_runs` を呼びます。OK のみのリマインダ（閉じても実行には影響しないので質問にはしない）で、「Don't remind me again」チェックボックスは設定キー `remind_background_runs` に保存されます。

バックグラウンド実行には Linux（util-linux の `setsid`）が必要です。ログアウト時にユーザーのプロセスを終了させる設定のシステム（systemd の `KillUserProcesses`。Ubuntu の既定は無効）では、ログアウトで終了することがあります。

#### processor* ディレクトリの削除

**Delete processor\* Directories…** は、`processor*/` にあるすべてがケースルートにも存在し、ケースで他に作業しているものがないことを `services/solver_run.check_processor_deletion` が示した後でのみ削除します。これを厳格にしているのは、`reconstructPar` の正常終了があまり何も保証しないからです。`-latestTime` や `-fields` の実行も成功し、それでもデータがどこにも残らないことがあります。

- **存在確認。** すべての時刻ディレクトリとその中のすべてのファイル（フィールド、`uniform/`、`lagrangian/`）、`constant/polyMesh/sets/` の集合（`reconstructPar` の no-sets オプションでスキップされる）、そしてメッシュです。ケースルートには総セル数が同じメッシュが必要で、`snappyHexMesh -parallel` で作ったメッシュがまだ `reconstructParMesh` を通っていない状況を検出します。
- **健全性。** ルートのファイルは存在するだけでなく完全でなければならず、`services/field_integrity.py` はサイズを信用せず各ファイルの両端を読みます。再構築されたファイルは processor 側の部分の和にはならないためです。書き込み途中で kill された `reconstructPar` は、閉じの `// *** //` 行を残しません（OpenFOAM が最後に書くので、どこで切れても欠けます）。`FoamFile` ヘッダはそのファイルの名前を指していなければならず、`internalField` の要素数はメッシュと一致しなければなりません（vol フィールドはセル数、surface フィールドは内部面数、point フィールドは点数。`<t>/polyMesh` とリージョンのメッシュも辿ります）。これにより、`reconstructPar -newTimes` がスキップした、完全だが古いファイルを検出します。ルートのファイルは processor 側の写しが満たす条件のみを課されるため、閉じの行なしで書く OpenFOAM のファイルが誤検出されることはなく、`.gz` と平文の名前は同一視されます（`writeCompression on` では `decomposePar` が `0/U` から `processor*/0/U.gz` を書きます）。
- **圧縮ファイル。** `.gz` の閉じの行は全体を展開しないと読めないため、大きな `.gz` は、確認ダイアログの既定でチェック済みの「圧縮ファイルを最後まで読む」オプションが worker で `verify_compressed` を走らせない限り、先頭のみを読みます。
- **活動状況。** `case_activity_problem` は、ケースで他のプロセスが作業している間（cwd または `-case`。FoDE 自身のツリーは除外。アイドルなシェル・ページャ・エディタ・ParaView は数えない）は拒否し、削除の直前に worker で再度実行されます。コレーテッドデータ（`processorsN`）は FoDE が中を読めないため拒否します。

確認ダイアログは `ui/dialogs/processor_delete_dialog.py` の `ProcessorDeleteDialog` で、`QMessageBox` ではチェックボックスを 1 つしか置けないため `QDialog` にしています。以前は `QMessageBox` で、親なしで `setCheckBox` に渡したチェックボックスが GC により二重解放されました（再現した SIGBUS）。PySide6 の `setCheckBox` は所有権を移さず、ウィジェットを引き取る setter はどれも同じ `Shiboken.ownedByPython` の確認に値します。keep-latest モード（既定でオン）は、シリアルの `decomposePar` なしで並列実行を続けられるよう、各 processor の最新時刻と `constant/` を残します。専用の `keep_latest` フィールドなので「残すものがない」が「すべて削除」を意味することはなく、全削除ではデータを失う場合（メッシュが `processor*/` にしかない）はハンドラで強制的にオンになり、ケースルートの方が新しい時刻を持つ場合はオフで始まります。実際に削除されるものだけが検査されます。削除自体は永続的で、`ui/processor_deletion.py` のワーカースレッド上で、**Stop** 付きのモーダル進捗ダイアログの背後で実行されます（10 GB のケースでウィンドウが固まったため）。現在の時刻ディレクトリの後で停止するのは常に安全です。最初の削除の前にすべて検証済みだからです。

#### Allrun のステップ

**Tools > Allrun Steps…** は、ケース自身の `Allrun` をステップとして表示し、それぞれをログで判定して、1 つずつ実行させます。汎用のメッシュ → 計算 → 後処理の「ワークフロー表示」を置き換えたものです（ほとんどのケースはその手順ではなく、いくつかのステップでは「完了」をディスクから読めません）: ケースのスクリプト*こそ*がその手順であり、ステップがいつ完了かは OpenFOAM がすでに定めています。

Qt 非依存の `services/allrun.py` がスクリプトを `Step` の行に読み込みます。`runApplication`/`runParallel` の呼び出しがそれぞれステップ、それ以外のコマンド（`restore0Dir`、`cp`、`foamDictionary` など）は状態を持たない行で、シェルの配管（`echo`、`printf`、`[ … ]`、case のラベル、関数定義）は表示しません。呼び出しの先頭のオプションは両フォークの `RunFunctions` と同じに読みます: `-s`（サフィックス。OpenCFD と同様に先頭のドットを除く）、`-o`/`-a`（決して飛ばされない）、OpenCFD の `-p`/`-d`（ログの接頭辞とディレクトリ）と `-decomposeParDict`、`-n`/`-np`。ログは `<dir><prefix|log.><app><suffix>` です。

`$(getApplication)` は `controlDict` の `application`（未保存ならエディタのバッファ）から解決し、それを代入した変数も同様です。リテラルの代入は記憶し、それ以外は名前を忘れ、オプションを持つ変数（`decompDict="-decomposeParDict …"`）はオプションとして飛ばします。環境変数の接頭辞（`USE_ARC=true runApplication …`）は取り除き、バックスラッシュによる継続行はつなぎ、行はトップレベルの `;`/`&&`/`||` で分けます。`./Allrun.pre`、`./Allmesh` などは深さ 3 までたどります（`./Allrun` 自身はたどらない）。

別のディレクトリで実行されるステップ — `cd sub` の後（`cd ..` まで）、または 1 行でも複数行でも `( … )` のサブシェルの中 — は別のケースのものなので表示しません（`NOTE_SUBDIRECTORY`）。ループと条件分岐は `NOTE_BRANCHES` を立て、ブロック内のステップは `conditional` です。

`step_state` はログの末尾 16 KB だけを読みます: エラー（`FOAM FATAL (IO) ERROR`、`sigFpe`、`sigSegv`）があれば `FAILED`、`End` の行（ランク接頭辞の有無を問わず）があれば `DONE`、どちらもなければ `INCOMPLETE`、ログがなければ `NOT_RUN`。`step_states` は、ログがまだプロセスに書き込み用に開かれているファイルのひとつなら、`INCOMPLETE` のステップを `RUNNING` にします — `services/process_tree.files_written_in` が、cwd がケースであるプロセスについて `/proc/<pid>/fd` と `fdinfo` のアクセスモードから読みます: `runApplication` やバックグラウンド実行ではソルバー自身、Tools メニューのコマンドでは `tee` が書き込み手です。`tail -f` は読むだけなので数えません。`/proc` がない環境では `None` を渡し、`StepStatus.watched` は false のままなので、ツールチップは「停止した」と言い切らず「実行中か停止」のままにします。

`step_states` は初心者に最も必要な疑いを加えます: 前のステップが失敗または未完了のとき — Allrun は失敗しても先へ進むため、壊れた setFields が書かなかった場で damBreak の interFoam が完了と報告する。実際の実行で確認しました — や、前のステップのログが自分のものより新しいとき（そのステップが後で再実行された）、`DONE` のステップは*疑わしい*とします。条件付きのステップはどちらの判定にも含めません。

`step_command` は `RunFunctions` を読み込んだうえでステップ自身の行を送り、ログがあれば飛ばされないよう `-o` を加えます。`run_from_command` は選択行から末尾までのすべてのコマンドを `&&` でつないで送り（失敗すれば止まる）、ログのある各ステップに `-o` を付けます。分岐を持つスクリプトでは行が一直線に実行されないため、これは出しません（`None`）。`ui/mixins/_allrun_ops.py` は送る前に確認します — 正確なコマンド、上書きするログ、範囲にソルバーのステップを含むときの Check Case のエラー、未保存のファイルがあるときの「すべて保存して実行」 — ターミナルが使用中なら拒否します。`ui/dialogs/allrun_steps_dialog.py` は非モーダルで、表示中は 2 秒ごとに状態を読み直し（実行中のステップはログをその場で書き換え、ほかに気づくものがない）、選択行の説明を一覧の下に表示し（`ui/allrun_text.py`）、ステップのログを View Log Summary で開きます（`LogSummaryDialog.show_log`）。失敗はそこでログの助言が説明します。

**Allrun と Allrun-parallel。** `SCRIPT_NAMES` は `("Allrun", "Allrun-parallel")` です。Allrun-parallel はチュートリアルにおける Allrun の並列版です（v2606 の 61 ケース。うち 57 は逐次の Allrun と並び、33 は `./Allrun.pre` を共有）。`read_allrun(…, script=)` はどちらも読みます。互いの中へはたどりませんが、`./Allrun.pre` へは引き続きたどります。両方があるケースではステップのウィンドウに Script の選択欄が出て（`set_plan(scripts=…)`、`script_changed`）、`_refresh_allrun_steps` は、ケースにそのスクリプトがある間は 2 秒ごとの更新でも表示中のスクリプトを保ちます。Run Allrun Script は両方があるときだけどちらを実行するかを尋ね（`_tools_ops._choose_allrun_script`）、バックグラウンド実行は `log.<スクリプト名>` に書きます。

実測: v2606（494 件、直線的 359、2001 ステップ、アプリケーションを特定できないもの 5）と Foundation 12（213、178、893、8）のすべてのチュートリアルの Allrun が読め、`tests/services/test_allrun_corpus.py` に固定しています。damBreak、`extrudeMesh/polyline`（`-s` のサフィックス、環境変数の接頭辞）、`IO/systemCall`（`runParallel`）の実際の v2606 の Allrun は予測どおりのログをちょうど書き、すべてのステップが完了と読めました。`setFieldsDict` を壊した damBreak では setFields が `FAILED` と読め、修正後に `run_from_command` の文字列を bash で実行すると setFields と interFoam が完了に戻りました。

#### ログから Allrun を作成

**Tools > Create Allrun from Logs…** は、`Allrun` も `Allclean` もないケースにそれらを書きます — [Allrun のステップ](#allrun-のステップ)の相方で、これがあればユーザー自身のケースでもステップ表示が使えます。ケースに `Allrun` がないとき、Allrun Steps のウィンドウは同じ操作をボタンとして出します。既存の `Allrun` は決して置き換えず、既存の `Allclean` は残します（`write_script` はモード `x` で開きます）。

Qt 非依存の `services/allrun_create.py` がステップを提案します。**まずログから**: OpenFOAM は両フォークとも、すべてのログに同じヘッダーを書きます（`argList.C`、v2606 と Foundation-12 のソースで確認） — `Exec`（argv を空白でつないだもので引用符はないため、`-fields (U p)` のような括弧付きの値は括弧が釣り合うまでつなぎ直して引用し直す）、`Date`/`Time`（`Nov 06 2026` / `10:59:14`。両方とも `clock::date`/`clockTime`）、`nProcs`。`-parallel` と `-case <dir>` は除きます。`nProcs > 1` なら `runParallel` にし、`-np N` は N が `system/decomposeParDict` の `numberOfSubdomains` と違うときだけ付けます（両フォークの `runParallel` が `-np` を受け付けます）。`log.<app>.<suffix>` は `-s <suffix>` になります。

順序は開始時刻で、同時刻（秒単位なので、surfaceFeatureExtract と snappyHexMesh はよく同じ秒に始まる）はログの mtime、つまり終了時刻で決めます。FoDE 自身の Run Solver は以前のログを `log.<app>.partN` として残します: 同じコマンドの別のログがある part ログはそのステップの以前の実行（`SKIP_EARLIER_RUN`）で、ほかにない part ログが複数あればサフィックスなしの 1 つにします。ヘッダーのないログはアプリケーションのものではありません（`SKIP_NO_HEADER`）。失敗したログはチェックを外し（`MARK_FAILED`）、読むだけのツール（`checkMesh`、`foamListTimes` など）も同様です（`MARK_READ_ONLY`）。後の並列実行より古い `reconstructPar` は最後の並列実行の後へ移します（`MARK_MOVED`） — これを作るもとにした実際の `mixerVesselAMI` のコピーは、実行の途中で再構築し、領域分割し直して実行を続けたものでした。

**次に辞書から**、ケースに明らかに必要なのにログを残さなかったステップを提案します（`MARK_NO_LOG`、辞書の名前付き）: `blockMeshDict` → blockMesh。`snappyHexMeshDict` → surfaceFeatureExtract（あるいは Foundation の surfaceFeatures。どちらの辞書があるかによる）と `snappyHexMesh -overwrite`。`topoSetDict` → topoSet（`MARK_GUESSED`: snappyHexMesh の前か後かは分からない）。`setFieldsDict` → setFields。controlDict の `application` → ソルバー。並列（`decomposePar -force` の後）にするのは、`decomposeParDict` が 2 つ以上の領域を指定し、*かつ* `processor*` ディレクトリがあるときだけです — decomposeParDict だけならほとんどのチュートリアルにあり、何の証拠にもなりません。並列実行の後には `reconstructPar` も加えます（v2606 の `Allrun-parallel` 61 本のうち 41 本がそれで終わる）。一覧に並列実行があるときだけ合わせます。提案したステップは、チュートリアルの順序で前に来るステップのうち最後のものの後に入れます。`decomposePar` のログがない並列実行にはそれを加えます。ログがまったくなければ一覧全体がそうした提案で（`NOTE_FROM_DICTIONARIES`）、スクリプトはそのことを各行ではなく先頭で 1 回だけ述べます。

**0.orig**: あれば、メッシュ用ツールでない最初のステップの前に復元の行を加えます — チュートリアルと同じくメッシュ生成の後で、snappyHexMesh や createBaffles がパッチを `0/` に書き込まないように — OpenCFD では `restore0Dir`、それ以外では `rm -rf 0 && cp -r 0.orig 0` として（Foundation 12 には `restore0Dir` も `cleanCase0` もありません。フォークは `case_check.installation_info` によります）。`NOTE_RESTORES_ZERO` は、編集は `0.orig/` で行うよう警告します。`0.orig/` がなく、`0/` とそれを書き換えるステップがあれば `NOTE_NO_ZERO_ORIG` です。

**不注意なスクリプトがデータを失うのは Allclean です。** `cleanCase` は両フォークとも `constant/polyMesh` を削除するため、チェックの入ったステップのどれもメッシュを作らないとき（`makes_mesh`: blockMesh、extrudeMesh、foamyHexMesh、cfMesh のツールなど）、Allclean はメッシュを残し、代わりに `foamListTimes -rm` と `rm -rf processor* postProcessing dynamicCode log.*` を使います。そうでなければ `cleanCase0`（`0.orig/` のある OpenCFD）、`cleanCase` + `rm -rf 0`（それ以外で `0.orig/` あり）、または `cleanCase` です。Foundation の `cleanCase` は、ケース内のすべての `*.orig` ファイルの片割れも削除します（手で作った `controlDict.orig` があると `controlDict` が消える）。そのため Foundation ではその片割れを一覧にします（`NOTE_ORIG_FILES`）。

**並列版への分割。** 「Allrun-parallel も作成」はチュートリアルと同じ形でワークフローを書きます（上の実測を参照）。`render_split` はチェックの入った行を、最初にチェックの入ったソルバーの行（`solver_row`。controlDict の `application` を `Proposal.solver` として保持）で切ります。それより前の行が `Allrun.pre` です。`Allrun` は `./Allrun.pre` とソルバー以降の行で、`runParallel` の行は逐次に直します（`_serial`）。`Allrun-parallel` は `./Allrun.pre`、すべての decomposePar の行（一覧のどこにあっても先頭）、`runParallel` としてのソルバー（プロセス数はログか `numberOfSubdomains` から）、それ以降の行です。decomposePar と reconstructPar の行（`_PARALLEL_ONLY`）は `Allrun` にも `Allrun.pre` にも入りません。ソルバーより前に何もなければ `Allrun.pre` も `./Allrun.pre` の行も作りません。`can_split` はソルバーの行と 2 つ以上のサブドメイン（または並列の行）があるときに選択肢を出し、`ran_in_parallel` なら最初からチェックを入れます。チェックを入れると、一覧に欠けている分だけ `parallel_rows`（`SOURCE_ADDED`、`MARK_PARALLEL_ONLY`）をソルバーの行の前後に入れ、外すとそれらだけを取り除きます。チェックの入ったソルバーの行がなければダイアログがそう伝え、Create は押せません。この分割は、1 つの Allrun の中でソルバーを `runParallel` に替える「並列で実行」のチェックボックス案に代わるものです。どちらを選んでも、初心者にとって逐次のスクリプトは動き続けます。v2606 の cavity（9 プロセス）と damBreak（4）のスクリプトを消した複製で確認済み: 生成した `Allrun`、`Allclean`、`Allrun-parallel` をこの順に実行し、すべてのログが `End` で終わり、`reconstructPar` が最後の時刻を書き戻しました。

**入力したコマンド。** Add Command… は行を `user_row` に渡します（`SOURCE_USER`、`MARK_USER`）。OpenFOAM のアプリケーション — ケースのソルバー、固定の `_KNOWN_APPS`、または FoDE に読み込まれた環境があれば `$FOAM_APPBIN`/`$FOAM_USER_APPBIN` にあるファイル — は `runApplication <app> <引数>`（そう入力すれば `runParallel`）になり、Allrun Steps が追えるログを書きます。それ以外と、独自のオプション付きの `runApplication` は入力したとおりに残します（`OTHER` の行）。Remove はそうした行だけを取り除きます。

`ui/dialogs/create_allrun_dialog.py` はモーダルです: 行のチェックリスト（ドラッグか「上へ」「下へ」で並べ替え。各項目は `UserRole` に `Proposed` を持つので、行を加えたり取り除いたりできます）、選択行の出どころと印を下に（`ui/allrun_create_text.py`）、スクリプトのライブプレビュー（Allrun.pre、Allrun、Allrun-parallel、Allclean のタブ。分割しない間は分割用のタブを隠す）、注記、「Allclean も作成する」と「Allrun-parallel も作成」のチェックボックス — 後者は、ケースにすでに `Allrun.pre` か `Allrun-parallel` があれば選べません（`existing=`）。`scripts()` は書く順にファイルを並べます。`_allrun_ops._write_new_scripts` がそれらを実行可能として書きます。Allrun が存在しないスクリプトを呼ぶことのないよう Allrun.pre を先に書き、書けないファイルがあればそこで止めます。その後、ファイル一覧を読み直し、Allrun を開き、ステップ表示を更新します。

実際の v2606 の実行で確認しました: damBreak、`extrudeMesh/polyline`、`IO/systemCall`（並列）、`snappyHexMesh/flange` の Allrun を実行し、削除してからログで再び提案させると、同じ `runApplication`/`runParallel` のステップになりました（ログを残さない `cp`/`mkdir` だけが欠ける）。Allrun なしで配布される cavity と pitzDaily には辞書からの骨組みができました。生成した Allclean に続けて生成した Allrun を実行すると、6 つすべてで問題なく終わり、すべてのログが `End` で終わりました。`tests/services/test_allrun_create.py` は、書いた Allrun を `allrun.read_allrun` で読み戻すと同じログになること、両スクリプトの `sh -n` を確かめます。

#### ログの助言

**View Log Summary** は、認識できるエラーがログにあると、タブの上に「何が起きたか」の欄を表示します。Qt 非依存の `services/log_advice.py` が `--> FOAM FATAL (IO) ERROR` の各ブロック（`FOAM exiting`/`aborting` まで。並列計算の `[N] ` というランクの接頭辞は取り除き、全ランクが同じエラーを繰り返すので異なるエラーごとに 1 件）と、浮動小数点例外のスタックトレースの `Foam::sigFpe::sigHandler` 行を見つけ、表と照合します。返すのは値付きの `Advice` のコードと、開くファイルと行です。`ui/log_advice_text.py` がそれぞれのタイトルと説明を作り、`LogSummaryDialog` が `QTextBrowser` に表示します。その `open:N` リンクは `open_requested(path, line)` を発し、`MainWindow._open_file_at_line`（`_file_ops.py`。Check Case と共用）が処理します。

表の各パターンは、わざと壊したチュートリアルのコピーでインストール済みの v2606 が実際に書いたログから取り、Foundation-12 のソースでそのフォークの文言を確かめたものです:

| コード | OpenCFD v2606 | Foundation 12 |
|---|---|---|
| `missing_patch_entry` | `Cannot find patchField entry for P` | 同じ |
| `unknown_name` | `Unknown patchField type X` / `Unknown RAS model type X` / `Unknown symmetric matrix solver type X` / `Unknown discretisation type X` | `Unknown patchField type X for patch …` / `Unknown RASModel type X` / `Unknown discretisation scheme X` |
| `constraint_mismatch` | `inconsistent patch and patchField types for patch type A and patchField type B`、`patch type 'A' not constraint type 'B'` | 同じ |
| `missing_entry` | `Entry 'K' not found in dictionary "D"` | `keyword K is undefined in dictionary D` |
| `no_reference_cell` | `Unable to set reference cell for field p` | 同じ |
| `missing_file` | `cannot find file "PATH"` | 同じ |
| `no_mesh` | `Cannot find file "points" in directory "polyMesh"` | 同じ |
| `decomposition_divisions` | `Wrong number of domain divisions in geomDecomp` | `Wrong number of processor divisions in geometric` |
| `processor_count` | `specifies N processors but job was started with M ranks` | `… with M processors.`、`number of processor directories = N is not equal to the number of processors = M` |
| `syntax_error` | `Unexpected EOF while reading dictionary entry`、`Found { but expected }` など | — |
| `max_iterations` | `Maximum number of iterations exceeded`（熱物性でエネルギーから T を求める処理） | 同じ |
| `floating_point` | スタックトレースの `Foam::sigFpe::sigHandler` | 同じ |

大事な細部:

- **ファイルの参照。** OpenCFD は `file: 0/U/boundaryField at line 25 to 36.`（ケース相対）、Foundation は `file: /abs/0/U/boundaryField from line 25 to line 36.` と出力し、どちらもファイル名の後ろに辞書のスコープを付けます。そこで `_resolve` は、ログ自身のディレクトリを基準に、存在するファイルが残るまで末尾から要素を落とします。ケースの外を指す参照は開く対象にしません。
- **綴りを誤った名前**には、ログ自身が出力する「Valid … types」の一覧から最も近い名前を示します（`difflib`、カットオフ 0.75、大文字小文字を無視した一致を優先）。そのため、提案は常にこのインストールが受け付ける名前です: `noSlp`→`noSlip`、`lineer`→`linear`、`PCGG`→`PCG`、`kEpsilonn`→`kEpsilon`。
- **実はファイルに書かれている「項目なし」**は、典型的な `;` 抜けです: セミコロンのない `endTime 0.5` が次の行を飲み込み、OpenFOAM は `deltaT` が見つからないと報告します。助言はファイルを確かめ、キーが書かれていればそう伝えてその行を開き、なければ OpenFOAM 自身が示した行を開きます。
- **浮動小数点例外**では、異常終了の直前のクーラン数を引用します。1 を超えていれば `deltaT`/`adjustTimeStep` についての助言となり `controlDict` の `deltaT` を開きます。そうでなければよくある原因を挙げます。
- **認識できないエラーには助言を出しません。** その文面は要約にあり、誤った推測が本当のメッセージの前に立つことになるためです。

`tests/fixtures/logs/v2606/` は本物のログを保持し（ケースのパスは `{CASE}` に置換し、ホストと日付の行は削除）、`tests/services/test_log_advice.py` がそれぞれを試し、Foundation の形はそのソースから組み立てます。パターンを追加するには: チュートリアルのコピーで起こしてログをそこに保存し、コードと、`log_advice_text.py` の文と `i18n/ja.py` の項目を加え、もう一方のフォークの文言をそのソースで探します。

#### Check Case

**Tools > Check Case…** は、初回実行の失敗の大半を占める少数の不一致を静的に見つけます。チェック本体は Qt 非依存の `services/case_check.py` にあり、文ではなく `Finding` のコードを返します。文面は `ui/case_check_text.py` が作ります（i18n のスキャンは `ui/` しか見ないため）。`ui/dialogs/case_check_dialog.py` が非モーダルで一覧表示し、`ui/mixins/_case_check_ops.py` がサービス側では知り得ないもの — 未保存のバッファ（`_current_text(path, fallback=False)`。バッファのないファイルはサービス自身がディスクから読み、`.gz` も扱います）、`#includeEtc` の探索パス、インストール（`installation_info` がその `etc/bashrc` からフォークとバージョンを読みます）— を渡し、指摘のファイルを該当行で開き、Run Solver の警告に最大 4 件を加えます（`stop_at_left` と `processor_count` は Run Solver が自分の言葉で既に警告するので除きます）。

境界のチェックは両フォークの `GeometricBoundaryField::readField` をなぞります（OpenCFD v2606 と Foundation 12 は同じ読み方です）: パッチ名そのものの項目、次にそのグループ名の項目（辞書の逆順）、次に項目のない `empty` パッチ（自動で補われます — 両フォーク）、最後に正規表現キー（引用符付き、全体一致）。グループは boundary ファイルが列挙するものにパッチ自身のタイプを加えたものです: polyPatch.C は拘束タイプを、wallPolyPatch.C は `wall` を加えます。チェックは素の `patch` 以外の*あらゆる*タイプを加えます。余分なグループはカバー判定を通す方向にしか働かず、フォーク独自の拘束タイプ（Foundation 8/9 の `cyclicRepeatAMI`）はここでは知りようがないためです。`#includeEtc "caseDicts/setConstraintTypes"` が拘束パッチをカバーするのも同じ仕組みです — そのキーはグループ名です。解決できるインストールが見つからないときは、両フォークのキーの和集合で代用します。タイプ一致のチェックはより狭く、`empty`/`symmetryPlane`/`symmetry`/`wedge` のパッチに既知の非拘束の場タイプが与えられた場合と、それらの場タイプが `wall`/`patch` に与えられた場合だけを見ます。一覧にないタイプ、`patchType` による上書き、point 場（`pointPatchFieldNew` が黙って拘束タイプに置き換えます）は判定しません。

**迷ったら何も言わない。** 以下の規則はどれも、実際のチュートリアルでの誤検出から生まれたものです:

- メッシュ生成前は、ほかに何もメッシュを作り変えない場合に限り `blockMeshDict` からパッチを読みます — `system/` に `snappyHexMeshDict`、`createPatchDict`、`extrudeToRegionMeshDict`、`changeDictionaryDict` などがなく、`Allrun`/`Allrun.pre`/`Allmesh` のコメントでない行にそれらのユーティリティ（や `polyMesh`、`foamDictionary`、`m4`）がなく、古い `patches` 構文でなく、空でない `mergePatchPairs` がなく（Foundation の condenser では結合されたパッチが消えます）、どの名前も素の単語であること。blockMesh の `defaultFaces` パッチは、外側の面が余っていて、かつその名前のパッチが宣言されていないときだけ加えます（TJunction は `defaultFaces { type wall; faces (); }` を宣言しています）。
- 解決できない `#include`/`#includeEtc`、`$macro` の展開、コンパイルできない正規表現を含む場は、スキップしたことを報告して飛ばします。バイナリ形式の場も同様です。`cellDisplacement`/`cellMotionU` も飛ばします: 移動ソルバーはこれらを独自のパッチタイプで `READ_IF_PRESENT` として作り、overset の heatTransferFluxConservation1D チュートリアルは不完全なものを同梱したまま動くためです。
- どのパッチにも一致しない項目は、パッチの抜けと並ぶときだけ綴り間違いの候補として報告します。単独では OpenFOAM が無視するので、チェックも無視します。
- `no_start_dir` は `0.orig/` があるときだけ（chemFoam は `0/` を読まず、メッシュのデモには存在しません）。`already_at_end` は結果から続ける場合（開始時刻 > 0）だけです: 0 から始まる `endTime 0` のケースはユーティリティのデモです。`stopAt nextWrite` は最初の書き出しまでは走るので、数えるのは `writeNow`/`noWriteNow` だけです。計算の 10 倍を超える `writeInterval` は意図的な「書き出さない」設定（IO/systemCall、pitzDaily_fused）とみなし、計算と等しい `deltaT` は普通の 1 ステップです。
- 辞書のチェックは `SOLVER_DICTIONARIES` にあるソルバーだけを対象とし、`constant/` がないかファイルを 1 つも含まないとき（メッシュのデモ）や、`<name>.template` のような兄弟ファイルがスクリプトによる生成を示すとき（NACA4412）は黙ります。Foundation は旧名をフォールバックとして読み（`physicalProperties.C`、`momentumTransportModel.C`）、OpenCFD は新しい名前をどちらも読まないため、新しい名前は OpenCFD と、その名前を導入する前の Foundation（`momentumTransport` は 8、`physicalProperties` は 10）でエラーになります。

検証は関数オブジェクトのときと同じ方法です: 各指摘を v2606 の cavity のコピーで起こし、実際の `icoFoam`/`decomposePar` を走らせてエラー文を確かめました（writeInterval や deltaT が終了時刻を越えると何も書かずに終了コード 0 で終わり、`endTime` に達していると即座に `End` を出します）。`tests/services/test_case_check.py` にはそれぞれのケースがあります。誤検出の防波堤は `tests/services/test_case_check_corpus.py` です: v2606 と Foundation-12 のツリーのすべてのチュートリアルを `restore0Dir` 後の状態として見て、レビュー済みの 5 件 — 意図的な `stopAt writeNow` の設定 4 件と、本物の潜在バグ 1 件（v2606 の interIsoFoam/standingWave は `n (2 1 2)` で 1 分割を求めており、`decomposePar` は停止します）— 以外に何も出してはなりません。ローカルの 13 ツリーすべて（v2212–v2606、Foundation 7–12 と dev）でも一度計測して同じ結果を得ました。また、メッシュが blockMeshDict だけで決まる v2606 の 199 チュートリアルで実際の `blockMesh` を走らせても、追加の指摘はなく、推定したパッチは書き出された `boundary` と 198 件で一致しました（残る 1 件は `empty` パッチを見落としていましたが、これは指摘を生みません）。

チェックを追加するには: `case_check.py` にコード（と `FINDING_CODES`）、`case_check_text.py` にその文と `i18n/ja.py` の項目、サービスのテストに指摘を起こすケース、そしてコーパスでの実行です — 壊していないチュートリアルでの新しい指摘は、それが正しい理由をレビュアーが確かめられるまでは誤検出です。

#### Plot Results

**Tools > Plot Results…** は、ケースのテキスト出力 — 関数オブジェクトが `postProcessing/` の下に書くものと、ソルバーログの残差 — をプロットします。ウィンドウ、保存した画像、エクスポートしたスクリプトが食い違わないよう、層を分けています:

- `services/plot_data/`（Qt 非依存）がデータを見つけて読みます。`_discover.find_sources()` は `postProcessing/` を 4 階層まで走査して時刻ディレクトリを持つディレクトリを探し（なのでリージョンのサブディレクトリも扱えます）、ファイルを `Source` にまとめます。関数オブジェクトが追記していく **series** は、リスタートでできた区間 — 新しい `<startTime>/` ディレクトリや、既存ファイルの横に OpenCFD が作る `force_<time>.dat`（`writeFile::newFileAtTime`。Foundation 7 の `logFiles` も同じ）— を開始時刻順につなぎ、重なった区間は後の区間で置き換えます。**profile** は時刻ごとに 1 ファイルのサンプリングセット（`.xy`/`.csv`/`.raw`）です。**residuals** は `log.*` で、名前ではなく内容（先頭 256 KB に `Initial residual` と `Time =` のステップがあること）で判断します。`log.fluentMeshToFoam` はソルバーではなく、`log.foamRun` はソルバーだからです。`Source.key` はケースからの相対パスから時刻ディレクトリを除いたもので、「Plot This Column in Every Case」はこれでケース間を対応づけます。形状の出力（`.vtp`、`.vtk` など）は拡張子で、その他のファイルは先頭 4 KB を見て除外します。表は `(mtime_ns, size)` でキャッシュします。
- `services/plot_data/_reader.py` は 1 ファイルを解析し、**自己完結**しています（標準ライブラリのみ、プロジェクト内の import なし）。エクスポートする Python スクリプトがそのソースをそのまま埋め込むためで、`tests/services/test_plot_data.py` がその写しを `-I` で import して、この状態を保ちます。同じ理由で、凍結ビルドはこれをデータとして同梱します（`foam-dictionary-editor.spec`）。
- `services/plot_spec.py` はプロットが何を示すかです。`PlotSpec`（系列 — それぞれのサンプル時刻、X の列、ラベル、スタイルを含む —、軸、タイトル、グリッド、凡例とその位置、文字の大きさ、画像サイズ、コマ数/秒）は JSON にできるデータで、`resolve()` が各系列を読み込み、NaN の点を落とし（そのステップで解かれなかった残差や、リスタート区間にない列。NaN があると線がそこで切れます）、両方の出力が読む凡例のラベルと軸タイトルを確定させます。
- `services/plot_render.draw()` は resolve 済みの spec を `matplotlib.figure.Figure` に描きます（pyplot を使わないのでグローバルな状態を持ちません）。`services/plot_script.py` は同じ spec を書き出します。matplotlib のスクリプトはプロットの呼び出しが `draw()` と 1 対 1 で対応し、gnuplot のスクリプトには `.dat` のスナップショットが付きます。`tests/services/test_plot_script.py` はエクスポートしたスクリプトを実行し、その figure を `draw()` のものと要素ごと（線、ラベル、スケール、範囲、目盛り、凡例の文字と位置、サイズ）に比べます。片方だけを変えると、もう片方が追いつくまでテストが失敗します。凡例の位置は両方が呼ぶ `plot_spec.legend_kwargs()` を通ります。ウィンドウでドラッグした凡例は `legend_loc = "custom"` と `legend_at`（凡例の左下隅の位置を軸に対する割合で表したもの。ダイアログはマウスを離したときの凡例の範囲から読みます）として保存され、これは matplotlib のタプル形式の `loc` の意味そのものです。gnuplot には `set key at graph x, graph y left bottom` を書き出します。
- `services/plot_animation.py` はサンプリングラインを出力時刻ごとに進め（コマ、固定した範囲、時刻表示）、GIF/MP4/PNG のコマを書き出します。`services/plot_export.py` はデータやプロット中の線を見出し付きの CSV と `.source.txt` に書き出します。`services/plot_output.py` はそのどれもがどこに書いてよいかの規則で、アトミックに書き込みます。
- `ui/dialogs/plot_results_dialog.py` はウィジェットから spec を組み立てるだけで、プロットのロジックは持ちません。横に `line_settings_dialog.py`（線 1 本の設定）と `data_file_viewer.py`（データファイルの読み取り専用表示）があります。このダイアログはモジュールレベルで matplotlib を import するので、`ui/mixins/_plot_ops.py` が import の前に matplotlib の有無を確かめます。

**ファイル形式**は、OpenCFD v2512/v2606 の実際の出力と、Foundation のビルドがないため Foundation 7/dev のソースから調べました。表を書く関数オブジェクトはすべて `writeFile` の流儀（`writeCommented`/`writeTabbed`: `#` のコメント行が並び、データ直前の 1 行が列名）に従います。リーダーはヘッダーではなく**最初のデータ行の形**を基準にします。最上位のセルは数値、単語、括弧のグループのいずれかで、数値 1 つにつき 1 列に平らにします。ヘッダーは、そのトークン数がセル数と一致するとき（各セルを展開: 3 成分ベクトルは `_x/_y/_z`、6 と 9 はテンソル成分、Foundation の入れ子 `forces(pressure viscous)` と `((p) (v))` は `forces_pressure_x`…）か、平らにした幅と一致するときに使います。OpenCFD のビンごとの翼ファイルは 1 つのヘッダー名で 10 列を指すので `Cd(per bin) [i]` と番号を振り、プローブの列は `probe<N>` にします。単語はプロットしません（solverInfo のソルバー名や `N/A`）が、x が繰り返す中で値の変わる単語の列 — パッチごとに 1 行の `wallShearStress`、フィールドごとに 1 行の `fieldMinMax` — は、単語ごとの列の組に組み替えます。真偽値では組み替えません。ファイルの途中で繰り返されるヘッダー（メッシュのトポロジー変更で書き直される。`surfaceFieldValue` で確認）は他のコメントと同じく読み飛ばし、幅の違う行は誤読せず数えるだけにします。サンプリングセット: Foundation 10 以降の raw ライターは `#` のヘッダーを書き（`setWriter::writeTableHeader`）、区間を空行で区切ります。OpenCFD と古い Foundation はヘッダーを書かず、フィールド名をファイル名に入れます（`<set>_<f1>_<f2>.xy`。スカラーがベクトルより先）。これを列数と突き合わせて解読します。`_` で分かれた部分をつなぎ直すすべての方法（`p_rgh`）と、両方の軸の幅（1 列。セットの `axis` に応じて x、y、z、線に沿った距離のいずれかで、ファイルからはわからないため `position` と名付けます。または `x y z`）を試し、よく知られたスカラー（`p`、`k`、`alpha.*`）をベクトルとみなさない分け方を優先します。解読できない名前は `col N` になります。残差は、各ステップの各フィールドについて最初の `Initial residual` を使います。PIMPLE の外側補正や PISO の圧力補正で同じ行が繰り返されるためです。

**ビューは保存する画像のプレビューです。** `_PreviewArea` がキャンバスを持ち、**Image size** の縦横比で、収まる限り大きく、`Dark` の余白（デスクトップのテーマでは `Mid` はほぼ白です）の中央に置きます。その前に figure の dpi を、その結果の 1 インチあたりのピクセル数にします。matplotlib の Qt の `resizeEvent` は figure のインチを「ウィジェットのピクセル ÷ figure の dpi」にするので、こうするとインチがリサイズ後も保たれ、ポイントで指定した文字がファイルと同じ割合を占めます。`_original_dpi` もいっしょに設定します（論理値。`figure.dpi` はそれにデバイスピクセル比を掛けたもの）。ウィンドウを別の比の画面に移すと、matplotlib はこの値から計算し直すためです。**Fit to window** はキャンバスを 100 dpi で領域いっぱいに戻します。一致は近いものの厳密ではありません。文字は描く解像度で測られ、グリフの幅は整数ピクセルに丸められ、`tight_layout` もそれに従うためです。`test_the_view_previews_the_saved_image` は軸と凡例を figure の 0.015 以内（Fit to window では約 0.09 ずれます）、目盛りとインチを厳密に比べます。

**文字の大きさ**は `PlotSpec.title_size`/`label_size`/`tick_size`/`legend_size`（ポイント。None は matplotlib の既定）で、`_FontSizeSpin` で入力し、その Default（0）は `plot_render.default_font_sizes()`（`font.size` に対する相対値なので rcParams から読みます）の値を表示し、1 pt からではなくその値から増減します。rcParams ではなく明示的な `fontsize=` 引数と `tick_params(labelsize=)` として適用します。エクスポートしたスクリプトで、読む人が編集する呼び出しの中に見えるようにするためです。凡例の大きさは `legend_kwargs` が持ちます。gnuplot には、タイトル、ラベル、`set tics`、`set key` に `font ',<大きさ>'` を書きます。

**線ごとの設定と保存したプロット。** `Series` は `x_column`（空なら最初の列）とスタイル（`color`、`linestyle`、`marker`、`linewidth`。空なら matplotlib の既定）も持ちます。`style_kwargs()` がこれを `Axes.plot` の引数にし、`draw()` とエクスポートしたスクリプトの両方が使います。スクリプトの `SERIES` の各項目は `x_column` と `style` を持ちます。gnuplot には最も近い `lc`/`dt`/`lw`/`pt` と `lines`/`points`/`linespoints` を書きます。Save Settings… は `spec_to_json(spec)`（`{"format": "fode-plot", "version": 1, "plot": …}`、ケースのパスは絶対パス）を書き、Load Settings… は `spec_from_json` で読みます。外枠より内側は `from_dict` と同じく寛容です（不正な色やスタイルは既定に戻ります）。`PlotResultsDialog.apply_spec` はチェック中のものを置き換え、ウィンドウにないケースを加え、見つからなかった線は例外にせず返します。

**時刻とアニメーション。** サンプリングラインの時刻は、Line Settings で線ごとに選ぶ `Series.time` です（空なら最新）。データごとの時刻はありません。Time のスライダーはすべてのサンプリングラインをいっしょに動かします。位置 0 は通常のプロットで、それ以外は `plot_animation` のコマです（下のモジュールの項を参照）。`PlotResultsDialog.shown_spec()` は表示しているプロット（コマのときは、固定した軸、固定した色、時刻表示を含むそのコマ）で、すべての出力はこれから作ります。Save/Copy Image、両方のスクリプト（時刻表示を受け取ります）、Export Data です。Save Settings は設定したとおりのプロット `spec()` を保存します。`data_set_time()`（コマの時刻、なければ線が選んだ時刻、なければ最新）を Open File、Save as CSV、ツールチップが使います。

**自動更新**は、`auto_refresh()` を呼ぶ 2 秒の `QTimer` です。チェックした列のあるケースを `find_sources` で走査し直し（新しい出力時刻やリスタートの区間でデータのパスが変わります）、5 回に 1 回はすべてのケースを走査し（新しいデータがあれば `reload(keep_view=True)` でツリーを作り直します）、チェックした列のファイルの状態を調べ、変化があったときだけ描き直します（`replot(keep_view=True)`）。`keep_view` は軸の範囲を FoDE が最後に描いたときの `_drawn_limits` と比べ、ユーザーのズームやパンを描き直した後に戻します。ウィンドウが隠れているか最小化されているとき、マウスのボタンが押されているとき（凡例のドラッグやズームの最中）は何もせず、プロット中のファイルが 50 MB を超えると 10 秒ごとに遅くします。`load_source` は変わったファイルを丸ごと読み直すためで、追記された部分だけを読むのは、実際のケースで必要になったときの次の段階です。リーダーの `_read_text` は改行で終わらない最後の行を捨てますが、それは 10 秒以内に変更されたファイルの場合だけです。ソルバーは 1 行ずつ追記するので、読み込みが行の途中に当たることがある（`1.2345` の `1.2`）一方、書き終えて手で保存した CSV は最後の改行がなくてもその行を保ちます。実行中の simpleFoam で確認しました。描き直し 1 回に 40–100 ms、何も新しくない確認は数 ms、終始 1 時間ステップにつきプローブ 1 行でした。

まだしないこと: 大きなファイルの追記部分だけを読むこと、バイナリや VTK の出力の読み込み（これは ParaView の役目です）。

#### Tools メニューの背後のモジュール

- `services/background_run.py` — Qt 非依存: バックグラウンド実行と Stop Background Run の背後にある `background_command()`・`active_run()`・`request_stop()`・`finish_stop()`。[バックグラウンド実行](#バックグラウンド実行)を参照。
- `services/allrun.py` — Qt 非依存: `read_allrun()`、`step_state()`/`step_states()`、`step_command()`/`run_from_command()` — Allrun をログで判定したステップとして扱います。[Allrun のステップ](#allrun-のステップ)を参照。
- `services/allrun_create.py` — Qt 非依存: `read_log_header()`、`propose()`、`render_allrun()`/`render_split()`/`render_allclean()`、`user_row()`、`write_script()` — ケースのログから Allrun（必要なら Allrun.pre と Allrun-parallel も）と Allclean を作ります。[ログから Allrun を作成](#ログから-allrun-を作成)を参照。
- `services/case_check.py` — Qt 非依存: `check_case()` — Tools > Check Case… の事前チェック。`Finding`/`Skip` のコードを返し、文面は `ui/case_check_text.py` が作ります。[Check Case](#check-case) を参照。
- `services/domain_bounds.py` — Qt 非依存: `domain_bounds()` — `blockMeshDict` からケースの範囲を求める（include、$変数、`#eval`、scale を解決し、未保存のバッファを優先。`polyMesh/points` は読まない）。`snappyHexMeshDict` があれば `snappyHexMesh` の背景ボックスとして示す。`function_templates.suggest_values()` に使う。
- `services/field_integrity.py` — Qt 非依存: OpenFOAM の出力ファイル 1 つが完全か。`inspect_file()` が両端 — 終端の `// *** //` 行、`FoamFile` ヘッダの `object`/`class`、`internalField` の個数 — を、`read_mesh_sizes()` が owner の note を読む。`.gz` は full=True のときだけ先頭より先を読む。
- `services/function_templates.py` — Qt 非依存: OpenFOAM の関数オブジェクトのテンプレート（ユーザーのインストールの `etc/caseDicts/postProcessing`）の読み取りと入力 — `list_templates()`、`parse_template()`（各項目の種類を Foundation の `<placeholder>` またはキーと例の値から判断。`type/libs` は表示しない。C++ コードを含むテンプレートは入力欄にしない）、`render()`（編集した項目だけを書き換え、コメントや `#includeEtc` はバイト単位でそのまま）、`controlDict` の functions 用の `add_include_func()/function_names()`、選択肢用の `case_field_names()/case_patch_names()`。
- `services/foam_monitor.py` — `patched_foam_monitor()`: インストール済み `foamMonitor` スクリプトを chmod-755 の一時ファイルへコピーし、gnuplot の reread 非推奨化に対応する修正を適用する（`reread` を `load ARG0` に置き換え、`ARG0` が設定されるよう gnuplot を `-e "load '$GPFILE'"` で起動する。同じ修正はローカルの未追跡ファイル `foamMonitor_gnuplot_reread_fix.patch` にもあり、`.gitignore` の `*.patch` で除外されている）。`ui/mixins/_foam_monitor_ops.py` はこの一時ファイルを起動する。
- `services/example_search.py` — `discover_installations()/search_examples()`: OpenFOAM インストールを検出（`app_config/foam_env` による環境変数読み取り → 既知のパス）し、その `tutorials/` + `etc/caseDicts/` をキーワード走査して `SearchHit`（一致行、囲むチュートリアルケースのルート）を返す。
- `services/plot_data/` — Qt 非依存: Plot Results のデータ — `find_sources()`、`load_source()`、自己完結したリーダー `_reader.py`（`read_table()`、`stitch()`、`read_log_residuals()`）。[Plot Results](#plot-results) を参照。
- `services/plot_spec.py` — Qt 非依存: `PlotSpec`/`Series`/`Axis` と `resolve()` — プロットが何を示すか、読み込みとラベル付け。
- `services/plot_render.py` — `draw()` — resolve 済みの spec を matplotlib の `Figure` に描く（pyplot なし）。ASCII 以外のラベルには CJK フォントで補います。
- `services/plot_script.py` — Qt 非依存: `python_script()`（リーダーを埋め込み、`draw()` と対応）、`gnuplot_script()`/`gnuplot_data()`。
- `services/log_advice.py` — Qt 非依存: `advise()` — View Log Summary の助言。FATAL ERROR のブロックと `sigFpe` のトレースを、開くファイルと行付きの `Advice` のコードに対応づけます。文面は `ui/log_advice_text.py`。[ログの助言](#ログの助言)を参照。
- `services/log_summary/` — パッケージ: `parse_log()/format_summary()` が `blockMesh/snappyHexMesh/topoSet` およびソルバーの実行ログ（`log.*` の標準出力。`FoamNode` 辞書ツリーではない。ソルバーは名前ではなくタイムループの形で検出）を短い `LogSummary` レポートに要約。
- `services/log_summary/__init__.py` — `LogSummary/LogWarning/PhaseSummary` を再エクスポート。`parse_log()` はユーティリティ名/形状で分岐し、`format_summary()` がレポートを整形。
- `services/log_summary/_types.py` — `LogSummary/LogWarning/PhaseSummary` データクラス + すべての文法が共有するヘッダー・FOAM `Warning/FATAL` ERROR の汎用パース。
- `services/post_process.py` — Qt 非依存: 既存の結果への関数オブジェクトの実行 — `post_process_tool()`（インストールの `applications/` から `postProcess` か Foundation 11 以降の `foamPostProcess` を判断）、`needs_solver()`（関数の型で判断: `system/<name>` 自身の型、取り込むテンプレートの型、または名前）、`invocation()`（そのまま、`<application>` `-postProcess`、`foamPostProcess` `-solver` `<module>`）。
- `services/process_tree.py` — Qt 非依存、Linux の `/proc`: `child_processes(pid)` と `running_command_names(shell_pid, job_control=…)` — Terminal タブのシェルがまだ実行中のもの。閉じる・モード切替時の警告に使う。`processes_in_directory(dir, exclude_tree_of=…)` — FoDE 以外でケース内で動作しているもの（cwd、または OpenFOAM の `-case` 引数）。Delete `processor*` 用。`files_written_in(dir)` — ケースで動作しているプロセスが書き込み用に開いているケースのファイル（`fdinfo` のアクセスモード）。未完了の Allrun ステップを Running にする。FOLLOWERS（tail）は実行中に数えず、`follower_pids()` がそれを示して、Terminal タブがコマンドを送る前に止められるようにする。
- `services/solver_run.py` — Run Solver と Run decomposePar の背後にある Qt 非依存の読み取り（`controlDict`、`decomposeParDict`、`processor*` の状態、名前とサフィックスの検証）と、`processor*` ディレクトリ削除の安全確認（`check_processor_deletion`、`verify_compressed()`、`case_activity_problem()`）。[processor* ディレクトリの削除](#processor-ディレクトリの削除)を参照。
- `services/tool_options.py` — Tools メニュー「Run *」オプションダイアログ用の `ToolSpec/ToolOption` 仕様（`TOOL_SPECS`、`SOLVER_SPEC`）+ `build_args()/build_command()`。常に `log.<`ツール名> へ tee し、必要なら mpirun `-np` N … `-parallel` で包む。background=True のときは `| tee` の代わりに `services/background_run.py` の切り離した形を組み立てる。
- `ui/processor_deletion.py` — `run_deletion_with_progress()`: 確認済みの `processor*` 削除を、停止ボタン付きのアプリケーションモーダルな `QProgressDialog` の裏でワーカースレッド実行。同じスレッドでまずケース内のプロセスを確認し直し、指定があれば圧縮されたルートのファイルをすべて最後まで読む。どちらかで問題が見つかれば何も削除しない。
- `ui/mixins/_background_run_ops.py` — Mixin: FoDE を閉じても続く実行 — Run `Solver/Allrun` のバックグラウンド実行チェックボックス、Stop Background Run、ポーリング、ツールバーのバッジ、停止レポート、終了時のリマインダー（Qt に依存しない部分は `services/background_run.py`）。`_tools_ops.py` から分割。
- `ui/mixins/_function_object_ops.py` — Mixin: Tools > Add Function Object… — インストールのテンプレートを探し、`FunctionObjectDialog` を表示し、`system/<name>` と `#includeFunc` `<name>` を書く（`controlDict` に未保存の編集があれば拒否）。新しいファイルを一覧に加えて開く。
- `ui/mixins/_allrun_ops.py` — Mixin: Tools > Allrun Steps… — 未保存のバッファを渡して計画を読み、ステップや「ここから実行」を確認のうえターミナルに送り（ソルバーのステップの前に Check Case）、ログを View Log Summary で開きます。`_allrun_steps_dialog` はほかの非モーダルなウィンドウと同様に保持します。Tools > Create Allrun from Logs… も担当します: 提案し、`CreateAllrunDialog` を表示し、スクリプトを書きます（`_write_new_scripts`）。`Allrun` があれば断ります。
- `ui/mixins/_case_check_ops.py` — Mixin: Tools > Check Case… — 未保存のバッファとインストールを渡して `services/case_check` を実行し、`CaseCheckDialog` を表示（`self._case_check_dialog` として保持。表示中にケースが切り替わると再実行し、ケースを閉じると隠す）、指摘のファイルを `_file_ops._open_file_at_line`（View Log Summary の助言と共用）で該当行に開き、Run Solver の警告用に最大 4 件を文にします。[Check Case](#check-case) を参照。
- `ui/mixins/_processor_ops.py` — Mixin: Tools > Delete `processor*` Directories… — 確認ダイアログ、問題の説明、削除しなかった場合の報告。健全性チェックは Qt に依存しない（`services/solver_run.py`、`services/field_integrity.py`）、削除は `ui/processor_deletion.py` のワーカーで実行。`_tools_ops.py` から分割。
- `ui/mixins/_tools_ops.py` — Mixin: ターミナルで何かを実行する Tools メニューのアクション。[Run ダイアログの仕組み](#run-ダイアログの仕組み)と [postProcess とソルバ](#postprocess-とソルバ)を参照。
  - `blockMesh`・`snappyHexMesh`・`topoSet`・`setFields`・`checkMesh` は `_run_tool_with_options` 経由で、ツールごとに 1 つの `RunToolDialog` を使って実行します。プレフライト警告はダイアログ内にあります。時間ディレクトリの結果には `_rerun_over_results_warning`、`setFields` には、`0/` を直接書き換えるため再実行が重ねて適用されることから、デフォルトでチェックされた「先に `0/` を `0.orig/` から復元する」プレフィックスチェックボックスがあります。`checkMesh` は読み取り専用なので警告はありません。最後に使ったオプションの値は `state.run_tool_options` に記憶されます。
  - `decomposePar` は `processor*` ディレクトリがあれば `-force` をチェック済みにします。ソルバー（`_on_run_solver_clicked`）は、編集可能な `ExecutableChoice` を `services/solver_run.read_solver_info` で `controlDict` から事前入力した `RunSolverDialog` を開きます（メモリ上のテキストを読むので未保存の編集も反映されます）。`numberOfSubdomains` による並列チェックボックスと、未保存ファイルがあれば「先にすべて保存」チェックボックスもあります。ソルバー名は記憶せず、オプションだけを記憶します。
  - `Allrun` と `Allclean` はケースのスクリプトを実行し、クリーンのアクションは `foamCleanTutorials` を実行します。`runApplication` はログ済みのステップをスキップするため、`log.*` があると Allrun は「クリーンしてから実行」を提案します。
  - ParaView、ログ要約（非モーダルの `LogSummaryDialog`、`self._log_summary_dialog` で参照を保持）、OpenFOAM の例の検索（非モーダルの `FindExamplesDialog`、`self._find_examples_dialog` で参照を保持）もここから始まります。例のダイアログの `compare_requested` は `_diff_ops._start_comparison_with` に、`duplicate_requested` はホームディレクトリをフォールバックのコピー先として `_case_ops._duplicate_case_from` に接続されます。
- `ui/dialogs/find_examples_dialog.py` — `FindExamplesDialog`: 非モーダルのキーワード検索。インストールの `tutorials/` + `etc/caseDicts/` を対象（`services/example_search.py` をバックグラウンド `QThread`、`_SearchThread(_worker_thread._CancellableWorkerThread)` で実行)、シンタックスハイライト付きプレビュー、コピー、「このケースと比較」（`compare_requested` を発行）、「このケースを複製…」（`duplicate_requested` を発行）。インストール選択は共有ウィジェット `widgets/installation_selector.InstallationSelector`。
- `ui/dialogs/foam_monitor_dialog.py` — `FoamMonitorDialog`: ファイル選択 + `foamMonitor` オプション（対数スケール、グリッド、リフレッシュ間隔、アイドルタイムアウト、追加フラグ）。
- `ui/dialogs/function_object_dialog.py` — `FunctionObjectDialog`: 検索付きのテンプレート一覧、選んだテンプレートから作る入力欄（名前の選択、点、数値、制御の選択肢）、書き出すファイルのプレビュー、Add を止める問題とメッシュにないパッチの警告。
- `ui/dialogs/allrun_steps_dialog.py` — `AllrunStepsDialog`: ステップ（状態、ステップ、ログ）の非モーダルな一覧。選択行の説明を下に表示し、Run This Step / Run From Here / Open Log を備えます。表示中は 2 秒ごとに状態を読み直します。`run_requested(index, onwards)`、`log_requested(path)`。Allrun がなければ Create Allrun from Logs… のボタン（`create_requested`）。Allrun と Allrun-parallel があれば Script の選択欄（`script_changed`）。
- `ui/dialogs/create_allrun_dialog.py` — `CreateAllrunDialog`: 提案したステップのモーダルなチェックリスト（チェック、ドラッグ、「上へ」「下へ」）、選択行の出どころを下に、Allrun/Allclean のライブプレビュー、注記、「Allclean も作成する」。`allrun_text()`/`allclean_text()`。
- `ui/dialogs/case_check_dialog.py` — `CaseCheckDialog`: Check Case の指摘を非モーダルで一覧表示（重要度、ファイル:行、問題）。選択中の指摘の全文を下に、スキップしたチェックを注記として表示。`recheck_requested` と `open_requested(path, line)` を発し、チェックのロジックは持ちません。
- `ui/allrun_text.py` — `services/allrun` の状態・疑い・注記の文言（`state_label`、`state_tooltip`、`note_text`）。
- `ui/allrun_create_text.py` — `services/allrun_create` の行の印・含めなかったログ・注記の文言（`mark_label`、`row_detail`、`skip_text`、`note_text`）。
- `ui/case_check_text.py` — `services/case_check` のコードに対応する文（`finding_message`、`skip_message`、`severity_label`、`finding_location`）。すべてのコードに文があることを `tests/ui/test_case_check_ui.py` が確かめます。
- `ui/log_advice_text.py` — `services/log_advice` のコードに対応するタイトルと説明（`advice_title`、`advice_text`）。
- `ui/dialogs/log_summary_dialog.py` — `LogSummaryDialog`（「何が起きたか」の助言欄付き。そのリンクは `open_requested(path, line)` を発します）: 非モーダル（`find_examples_dialog` と同様。他のモーダルダイアログとは異なる）のファイル選択 + `Summary/Raw` Log タブ、`services/log_summary/` を利用。
- `ui/mixins/_plot_ops.py` — Mixin: Tools > Plot Results… — matplotlib の有無を確かめ、`PlotResultsDialog` を表示します（`self._plot_results_dialog` として保持。`_load_case_dir` が新しく開いたケースを追加します）。
- `ui/dialogs/plot_results_dialog.py` — `PlotResultsDialog`: 非モーダル。チェックするケース・データ・列、プロットの設定、Copy Image / Save Image / Export Script / Export Data。`PlotSpec` を組み立てるだけで、プロットのロジックは持ちません。データの右クリックメニューで、読み込んだファイル（`source_files()`: リスタートの各区間、または選んだサンプル時刻のファイル）を開けます。
- `services/plot_animation.py` — Plot Results のアニメーション。`frame_times` はサンプリング（profile）の線の出力時刻の和集合を数値順に並べたもの（2 つの実行が時刻を共有することはまれで、共通部分では何も残らないことが多いため）。`frame_spec` は各サンプリングラインをコマの時刻までで最新の時刻に置き（最初の時刻より前は描かない）、すべての線がそろったときの位置の `C<n>` に色を固定して線が欠けても色の順がずれないようにし、`fixed_ranges`（ユーザーが空にした Min/Max ごとに、全コマのデータに matplotlib の 5 % の余白を付けたもの）を適用して軸を動かさないようにします。`draw(…, stamp=)` はコマの時刻を軸の右上の角の上に書きます。ウィンドウの `shown_spec()` は表示しているプロット（コマのときはそのコマ）で、すべての出力はこれから作ります（Save/Copy Image、`python_script(…, stamp)` と `gnuplot_script(…, stamp)` — `set label` と、gnuplot が知らない `C<n>` の色を tab10 の16進に変換 —、Export Data）。Save Settings は `spec()` を保存します。`data_set_time()`（コマの時刻、なければ Line Settings で線が選んだ時刻、なければ最新）を Open File、Save as CSV、ツールチップが使います。データごとの時刻はもうありません。サンプリングラインの時刻は Line Settings で設定する `Series.time` です。`AnimationWriter` は RGBA のコマを書き出し先の横の一時ファイル/フォルダーに集め、`finish` で名前を変えて置きます（GIF は Pillow でパレット画像として、MP4 は `ffmpeg` のパイプで偶数の大きさに埋めて、PNG は `<名前>_frames/` に。既存のフォルダーには書きません）。結果には一時ファイルの非公開の権限ではなく通常の権限を与え、`abort` はすべてを消します。
- `services/plot_export.py` — データを見出し付きの表にします。`table_csv`（見出しは 1 行、`#` 行なし — コメント行は表計算ソフトでは不要な 1 行目になります — 欠けた値は空、数値は `repr` で書いて正確に読み戻せ、整数値は `.0` なし）、クリップボード用の `table_tsv`（表計算ソフトは貼り付け時に CSV の引用符を解釈しません）、`<名前>.source.txt` 用の `source_note`（つないだ順のファイル、サンプル時刻、`Table.naming` — 見出しがファイル自身のものか、名前から推定したか、ログのフィールドか、番号か）、`free_csv_path`（CSV *か*説明ファイルのどちらかがある名前は飛ばします）、Export Data… 用の `plotted_table`/`plotted_note`（1 つのデータの線はその x 列を共有し、そうでなければ線ごとに `<凡例の項目>: <列>` を見出しにした x/y の組を持ち、短いほうを空で埋めます。補間はしません）、`is_our_note`（説明ファイルの 1 行目は `NOTE_MARKER`。置き換える CSV のために FoDE が書いた説明ファイルはいっしょに置き換え、それ以外は確認します。保存ダイアログは CSV の名前しか確かめていないためです）。
- `services/plot_output.py` — Plot Results が書き込んでよい場所: `refusal(path, protected)` は、OpenFOAM が持つケースのディレクトリ（`system`、`constant`、`postProcessing`、時刻、`processor*` など）の中、ケース最上位の既存のログ・`All*`・隠しファイル・`.foam`、プロット中のファイル、のいずれかならコードを返します（シンボリックリンクは両端で判定）。確認ではなく拒否にしているのは、「上書きしますか?」がユーザーが読まずに押してしまう箱だからで、gnuplot のエクスポートは `.dat` の名前をスクリプトから決めるため、forces のファイルの横に `force.gp` を置くと `force.dat` を置き換えてしまうところでした。`write_atomically` は同じフォルダーの一時ファイルに書いて `os.replace` し、置き換えたファイルのモードを保ちます。
- `ui/dialogs/line_settings_dialog.py` — `LineSettingsDialog`: チェックした列の Line Settings…。凡例の文字、X の列、色、線種、マーカー、線幅。既定の状態は空の値として書くので、保存したプロットは自動の凡例や matplotlib の色の順に従い続け、固定されません。線種を「なし」にしてマーカーもない線には、何も描かれなくならないようマーカーを付けます。
- `ui/dialogs/data_file_viewer.py` — `DataFileViewer`: それらのファイルの 1 つを非モーダル・読み取り専用で表示し、Reload と Show in Folder を備えます。メインのエディタを使わないのは、エディタが開いているケースに属し、ファイルを辞書として解析してしまうためで、Plot Results は複数のケースを扱います。`read_for_view()` は 16 MB を超えるファイルを最初の 200 行（列名）と最後の 4 MB（最新の値）で表示し、gzip も展開して読みます。
- `ui/dialogs/processor_delete_dialog.py` — `ProcessorDeleteDialog`: Delete `processor*` の確認ダイアログ。選択肢が 2 つ（最新の時刻を残す、圧縮ファイルを最後まで読む）あり、`QMessageBox` には 1 つ分しか場所がないため `QDialog`。
- `ui/dialogs/run_tool_dialog.py` — `RunToolDialog`: `services/tool_options.TOOL_SPECS` から構築される Tools メニュー「Run *」の汎用オプションダイアログ — 主要フラグのウィジェット、自由記述の追加オプション、ライブコマンドプレビュー、任意のプレフライト警告とシェルプレフィックスチェックボックス。サブクラス用フック `_build_extra_sections/_resolved_spec/_run_prefix/_parallel_np`。
- `ui/dialogs/run_post_process_dialog.py` — `RunPostProcessDialog(RunToolDialog)`: 編集可能な関数一覧（`controlDict` の `#includeFunc` 名、続いてテンプレートの単発のもの）、手で変えるまで関数に追従する「ソルバーを通して実行」、並列。ログは `log.<tool>` でソルバーのログには書かない。
- `ui/dialogs/run_solver_dialog.py` — `RunSolverDialog(RunToolDialog)` + `ExecutableChoice`: 編集可能なソルバー欄、先にすべて保存・mpirun `-parallel` のチェックボックス、既存 `log.<`ソルバー名> を残すか上書きするかの選択（不正または既存名と重なるサフィックスでは Run を無効化）。
- `ui/dialogs/_worker_thread.py` — `_CancellableWorkerThread`（`QThread`）: `find_examples_dialog` の `_SearchThread` と `generate_keywords_dialog` の `_GeneratorThread` が共有する `progress/finished_err` シグナルと `cancel()` フラグ。各サブクラスは自身の `finished_ok` シグナルと `run()` を追加する。

## メインウィンドウの挙動

メインウィンドウの各パネルが互いに、またディスク上のテキストと整合を保つ仕組みです。ツリーとエディタの同期、ダーティ状態の追跡、Undo/Redo、そして同じツリーを読む 3-D ビューアを扱います。

### ツリーとエディタの同期

ツリーノードを選択すると、対応するソース行がテキストエディタで琥珀色の背景でハイライトされ、オプションでその行にスクロールします。仕組みは以下の通りです。

**パーサ側** — `FoamNode` には 1 ベースの行番号フィールドが 2 つあります。`source_line`（ソース内のエントリの先頭行）と `source_end_line`（末尾行）です。パーサは `_finalize_node` および `_parse_dictionary_entry` 内で `_token_line(token_index)` を使ってこれらを設定します。`_token_line` は、パーサ構築時に一度だけ計算した各行の開始オフセットのリスト（`_line_starts`）を二分探索して行番号を求めます。ノードごとにファイル先頭から改行を数えると、パースがファイルサイズに対して 2 乗の時間になってしまうためです。

**UI 側** — `CodeEditor` は `_span_start_line` / `_span_end_line` を保持します。`set_span_highlight(start, end)` でこの範囲を保存し `highlight_current_line` をトリガーします。`highlight_current_line` は `setExtraSelections` で琥珀色のスパン（背景）と青い現在行ハイライト（前面）を重ねて描画します。`EditorPanel` は `jump_to_node(start, end, scroll=True)`（ハイライト＋オプショナルスクロール）と `clear_node_highlight()` を公開します。

**状態ガード** — `state.source_lines_valid` は `_load_tree` 呼び出し後（ファイル読み込みまたは Apply Text to Tree）に `True` になり、ユーザーがエディタテキストを編集した瞬間（`_on_user_text_changed`）に `False` になります。`on_tree_selection` はこのフラグが `False` の場合にジャンプとハイライトをスキップし、古い行番号への誤ジャンプを防ぎます。`_update_sync_checkbox` はこの有効/古いの状態をチェックボックスのラベル・スタイル・ツールチップに反映します。

**エディタ → ツリー方向** — `_sync_tree_to_editor_line` は現在のエディタカーソル行を読み取り、`_find_deepest(root, line)` を呼び出して `source_line ≤ line ≤ source_end_line` を満たす最も内側のノードを探します。結果が見つかればツリーをそのノードまでスクロールして選択します。一致したノードがプロキシモデルでフィルタリングされている場合は、表示中の最も近い祖先まで遡ります。このメソッドは Editor ツールバーの **Find in Tree** ボタンと `Ctrl+Shift+T` ショートカットで呼び出されます。

### バウンダリパネルとエディタのナビゲーション

Boundary パネルのセルをクリックするとそのパッチがテキストエディタ上で選択され、パネルはテーブルをクリップボードへコピーすることもできます。クリックすると `patch_selected(path, patch_name)` シグナルが発行され、`_BoundaryOpsMixin` の `_on_patch_selected` が処理します。ツリーのナビゲーション（`source_line` を使用）と異なり、バウンダリのナビゲーションはテキスト検索を使います。これは `write_root()` がバウンダリ編集後にテキストを再生成するため、ソース行番号がすぐに古くなるからです。

`EditorPanel.jump_to_text(text)` はドキュメント先頭から `QTextDocument.find(text, 0, FindWholeWords)` を呼び出します。一致が見つかった場合、マッチしたブロック番号に対して `set_span_highlight(line, line)` と `goto_line(line)` を呼び出します。`boundaryField` 内のパッチ名はファイル内で一意のため、最初のヒットが常に正しい位置です。

クリックしたセルのファイルが `state.current_file` と異なる場合、`_on_patch_selected` はまず `load_selected_file(path)` を呼び出して（`state.current_file` を設定）、続いて `file_list_panel.select_file(path)` でファイルリストのハイライトを同期します。その結果発行される `file_selected` シグナルによって再入する `load_selected_file` は、`state.current_file` が既に設定済みのため no-op になります。

Boundary パネルツールバーの **Auto-scroll editor** チェックボックスは `_on_cell_clicked` 内での `patch_selected` 発行を制御します。オフの場合、シングルクリックはエディタに影響しません。

**Markdown / CSV としてコピー。** `BoundaryViewPanel._table_data()` は現在の `QTableWidget` の状態から `(col_headers, row_headers, rows)` を取り出すため、3 つのコピーアクションはいずれも現在の転置状態に対応します。形式は 3 つあります。

- **Markdown**（`_copy_as_markdown()`）: GitHub Flavored Markdown のパイプテーブル。セルテキスト内の `\n` は `<br>` に変換されます。
- **CSV、1 行 1 レコード**（`_copy_as_csv()`）: `_csv_text(flatten=True)` が RFC 4180 準拠の CSV を書き、複数行セルの各行を `_CSV_LINE_JOIN`（`"; "`）で連結して、テーブルの 1 行が常に 1 レコードになるようにします。既定にしているのは、束縛条件が RFC 4180 としての妥当性ではなく受け取り側アプリケーションの*貼り付け*経路だからです。アプリケーションは貼り付けられたテキストを、引用符を解釈する前に改行で行に分割する（Excel は貼り付け時に引用符を一切解釈しない）ため、フィールド内の改行はどう書かれていても余分な行になります。
- **CSV、複数行**（`_copy_as_csv_multiline()`）: `_csv_text(flatten=False)` が引用符付きフィールド内の改行をそのまま保持します。LibreOffice Calc の貼り付けダイアログのように引用符付きフィールドを解釈するインポーターではセル内の実際の改行として表示されるため残してあり、両方を満たす単一の出力は存在しません。

どちらの CSV 経路も、レコードの区切りに `csv.writer` 既定の CRLF ではなく `_CSV_LINE_TERMINATOR`（`"\n"`）を使います。クリップボードが運ぶのはファイルではなくテキストで、レコード区切りはプラットフォーム側の管轄です。仮想マシンのクリップボードブリッジが Windows へ渡す際に改行コードを変換するため、こちらで書いた CRLF は `\r\r\n` となり、Excel では行と行のあいだに空行が入ります。

### ダーティ状態の追跡

`MainWindow` は 2 つの並行したダーティ状態変数を維持します。

- `state.text_dirty: bool` — 現在開いているファイルのインメモリエディタ内容がディスク上のものと異なるかどうか。`_mark_dirty()` で設定され、`save_file()`、Apply Text to Tree、Reload from Disk でクリアされます。
- `state.file_dirty: dict[str, bool]` — 現在のセッションで読み込まれたすべてのファイルのファイルごとのダーティ状態。ファイルを切り替えても未保存の編集が失われないよう、ファイルスイッチをまたいで保持されます。

`_mark_dirty()`（`ui/mixins/_model_ops.py`）は両方の値を `True` に設定し、ウィンドウタイトルに `*` サフィックスを追加し、`file_list_panel.mark_dirty()` を呼び出してファイルリストにインジケーターを表示します。これは `_after_model_edit()`（`write_root()` 経由でテキストを再生成するツリー編集後）と `_on_user_text_changed()`（エディタへの人間によるキー入力時）から呼び出されます。

`_after_model_edit()` 自体は 2 つの経路で呼ばれます。1 つは明示的な呼び出しで、Detail パネルの「Apply」ハンドラとツリー CRUD 操作（`_tree_crud_ops.py`）が `FoamTreeModel.setData()` / `insert_node()` / `remove_node()` を呼び出した直後に行われます。もう 1 つは `_load_tree()` 経由で、これは `FoamTreeModel.dataChanged` を `_on_tree_data_changed()`（`ui/mixins/_model_ops.py`）に接続し、`Qt.EditRole` を伴う発行だけにフィルタします。この signal 接続が、Tree パネルのインラインセルエディタで直接行われた編集を捕捉する仕組みです — Qt のアイテムデリゲートはビューから直接 `setData()` を呼び出すため、そのパスには明示的な `_after_model_edit()` 呼び出しがどこにもありません。この `dataChanged` フックがなければ、インラインでのツリー編集はノードを変更するだけで、エディタテキストの再生成もファイルのダーティマークも行われません。`Qt.EditRole` フィルタは差分ハイライトの再描画（`set_diff()` / `clear_diff()`、`BackgroundRole` のみで `dataChanged` を発行）を除外します。

`_save_current_buffer()`（`ui/mixins/_model_ops.py`）はファイルスイッチ前に `editor_panel.get_text()` を `state.file_buffers[state.current_file]` へフラッシュし、`state.text_dirty` を `state.file_dirty[state.current_file]` に書き戻します。これにより、スイッチをまたいでも未保存の編集がインメモリで保持されます。

`_mark_path_dirty(path)` は現在開いているファイルに関係なく特定のパスをダーティとしてマークします。複数のフィールドファイルにわたって境界パッチをリネームするような操作で使用されます。

**圧縮ファイル。** `foam/utils.read_foam_file` は gzip ファイルを透過的に展開します。名前ではなくマジックバイトで判定するので、名前が合っていないファイルも正しく読めます。平文ファイルに対して `read_text` が行うのと同じ改行の変換も行い、壊れたアーカイブは `OSError` を送出します（呼び出し側はすべて処理済み）。対になる書き込みが `write_foam_file` です: 名前が `.gz` で終わるとき（OpenFOAM 自身の規則）か `compress=` で指示したときは gzip で、それ以外は平文の `write_text` で書くので、平文ファイルの扱いは何も変わりません。バッファを書くすべての経路がこれを通ります: `save_file`、`save_all_files`、Save as New Case、そして `_file_mgmt_ops.py` の New File、Duplicate（保存先の名前で判定）、Create Backup。Create Backup は*元の*ファイルから `compress=` を渡すので、`U.gz.bak_…` を元の名前に戻せば本物の `U.gz` になります。以前は `0/U.gz`（`writeCompression on`）が latin-1 で解釈した圧縮バイト列として開かれ、習慣的な Ctrl+S 一回で — `save_file` は編集の有無にかかわらず書きます — それが UTF-8 に再符号化され、ファイルが壊れていました。`is_large_non_foam_file` は圧縮ファイルの展開後の先頭を調べ、`services/include_scan.included_files` は、読めないとして飛ばしていた `.gz` のインクルード先を一覧に載せるようになりました。エンドツーエンドで確認済み: cavity の `0/U` と `0/p` を編集を加えて `write_foam_file` で `.gz` として書き、v2606 の `icoFoam` が `End` まで走って結果に編集が反映されました。

**FoDE の外で変更されたファイル。** `_case_dir_watcher` が見るのはディレクトリのエントリの増減だけで、その場で書き換えられたファイルは見えないため、バッファは古くなり得ます。FoDE はファイルを監視せず、代わりに書き込みを守ります。`state.disk_stamps` は `services/disk_stamp.DiskStamp`（`(st_mtime_ns, st_size)` とテキストの SHA-1）を保持し、`_record_disk_stamp` が、バッファをディスクから読んだとき（`load_selected_file`、および `_cache_parsed_root`。境界の編集や差分表示は、未オープンのファイルをこれで読んでから構文木からバッファを書きます）と書いたとき（`save_file`、`save_all_files`）に記録します。`_purge_file_caches` とケースの切り替え・クローズで捨てます。書き込みの前に `_changed_outside` が `changed_since` に尋ねます: まず stat の組を、異なるときだけテキストを比べるので、`touch` や同一内容での書き直しは変更とみなさず、消えたファイルは `DELETED` です。そのうえで `save_file` は確認し（`_confirm_overwrite`）、`save_all_files` は該当ファイルすべてについて一度だけ尋ねます（`_ask_overwrite_many`: それでも保存 / ほかだけ保存 / キャンセル）。FoDE がディスクから読んだことのないバッファにはスタンプがなく、確認なしで保存します。**Reload File from Disk**（`reload_file_from_disk`。Case メニューの `F5` とファイル一覧の行メニュー）は、未保存の編集があれば確認し、Undo のチェックポイントを取り、キャッシュを捨ててから `load_selected_file` でファイルを開き直します — 初回オープンと同じ経路なので、エディタ・ツリー・3-D ビューがそろって更新されます。さらに `_refresh_include_dependents` とファイル一覧の再読み込みで、それを `#include` するファイルも描き直します。FoDE 自身の直接の書き込み（Stop Background Run の `stopAt`、Add Function Object の `#includeFunc`）は、もともと `_reload_clean_file_from_disk` を通り、クリーンなバッファとそのスタンプを更新します。*ダーティ*なバッファの上に書いた場合は、次の保存で黙って上書きされる代わりに、このガードが捕まえるようになりました。自動の再読み込み（バッファごとの `QFileSystemWatcher.fileChanged` とウィンドウのアクティブ化時のチェック）は引き続き見送りです: コードは数倍（アトミックな書き込みと改名で外れたパスの再登録、Undo との相互作用）になるうえ、再読み込みはツリーの展開状態をリセットし、ユーザーがウィンドウに戻った瞬間にダイアログを出しかねません。

**このセクションに関わるモジュール。**

- `services/disk_stamp.py` — Qt 非依存: 保存時のガードの背後にある `take_stamp()`/`changed_since()`。上記を参照。
- `ui/app_state.py` — `AppState` データクラス: 共有可変フィールドすべて（`current_case_dir`、`current_file`、`current_root`、`current_model`、`file_buffers`、`file_dirty`、`text_dirty`、`source_lines_valid`、`syncing`、`case_files_config`、`parsed_roots`、`diff`、`foam_monitor`、`run_tool_options`、`undo`、`bm_side_by_side`）。
  - `diff` は `DiffState` サブデータクラス（`case_dir`、`parsed_roots`）。
  - `foam_monitor` は `FoamMonitorState` サブデータクラス（`proc`、`script_tmp`、`last_file`、`last_options`）。
  - `undo` は `UndoState` サブデータクラス（ファイルごとの `UndoSnapshot` スタックと `op_active`/`restoring` ガード）。
  - `MainWindow.__init__` が `self.state = AppState()` を生成し、すべての Mixin が `self.state.<field>` として共有状態にアクセス。

### ツリーのコピー・ペーストショートカット

`_setup_tree_copy_paste()`（`ui/mixins/_tree_crud_ops.py`）は `Qt.WidgetShortcut` スコープを使って Ctrl+C と Ctrl+V の `QShortcut` インスタンスを `tree` ウィジェットに直接アタッチします。

```python
copy_sc = QShortcut(QKeySequence.Copy, self.tree)
copy_sc.setContext(Qt.WidgetShortcut)

paste_sc = QShortcut(QKeySequence.Paste, self.tree)
paste_sc.setContext(Qt.WidgetShortcut)
```

`Qt.WidgetShortcut` は `self.tree` がキーボードフォーカスを持つ場合のみ発火するため、テキストエディタでの Ctrl+C は影響を受けません。ツリーセルがインライン編集モードの場合も発火しません。その状態では Qt がセルエディタ自身の選択コピー機能に Ctrl+C をルーティングします。

同じ 2 つのアクションはコンテキストメニューにも表示されます（**Copy Value** / **Paste Value**）。選択したノード型が値の編集をサポートしない場合、ペーストはメニューで無効化され静かに拒否されます。

### ブロックの選択と CRUD

`blockMeshDict` の `blocks ( … )` は、無名の `block_entry` 行からなる `block_list` としてツリーに届きます。これらの行が*位置指定*であることから 2 つの帰結があり、どちらも設計の要になっています。

- 行の `block N` というキーは保存されているのではなく `index.row()` から合成されます（`model/tree_model.py` の `_display_key`）。行を挿入・削除すれば、それ以降のキーは自動的に振り直されます。
- 同じ番号を `BlockMeshRenderer._render_blocks` が各ブロックの重心に描画します。どちらも `data.hex_blocks` の解析順から来ているためです。**ツリーの行番号はビューアのブロック番号そのもの**であり、間に変換は不要です。

#### `#include` があるときのブロック番号

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

**このセクションに関わるモジュール。**

- `ui/mixins/_tree_crud_ops.py` — Mixin: ツリーエントリの CRUD（コピー・ペースト、追加、複製、コメントアウト、削除、復元）と `_apply_comparison_value`。

### ツリー編集の Undo/Redo

`ui/mixins/_undo_ops.py` はスナップショット方式のツリー編集 Undo/Redo を実装しています。ツリーの変更はすべて `write_root()` による完全な再シリアライズで終わるため、変更前の状態はシリアライズ済み*テキスト*としてチェックポイントされます。操作が触れるすべてのファイルの `{path: text}` とダーティフラグを、1 つの `UndoSnapshot`（`ui/app_state.py`）として保持します。Undo はスナップショットを再パースし、`_load_tree()` でツリーを再読み込みします。ツリーの展開・選択状態は保持されません。履歴は**単一のグローバルタイムライン**（`UndoState.undo_stack` / `redo_stack`）で、ファイルごとではありません。Ctrl+Z はどのファイルを表示中かに関わらず最後のツリー操作を取り消し（`_restore_undo_snapshot` は、カレントファイルがスナップショットに含まれない場合、対象ファイルへ表示を切り替えます）、新規編集は Redo ブランチをクリアします。複数のフィールドファイルにまたがる境界操作は全ファイルを 1 つのスナップショットに格納するため、1 回の Undo で触れたすべてのファイルが復元されます。スタックは件数上限（`_UNDO_DEPTH` = 50）と総バイト数上限（`_UNDO_MAX_BYTES`）で制限され、ケース切り替え時にクリアされます。

チェックポイントは `_after_model_edit()` への到達経路と対応する 2 つの経路でスタックに積まれます:

- **`FoamTreeModel.about_to_change`** — `setData()` の先頭で、編集が検証される*前*に emit されるため、スナップショットを push せず `pending` として退避するだけです。`_on_tree_data_changed`（`setData` 成功時のみ発火）が `_commit_pending_undo` を呼び、pending を push して Redo をクリアします — 結果の状態が同一なら（値が変わらない編集）破棄します。拒否された編集は `dataChanged` を emit しないため、退避したスナップショットは静かに破棄され、スタックは変化しません。これがインラインデリゲート、Paste Value、Detail パネルの Apply ハンドラをカバーします。
- **明示的な `_checkpoint_for_undo(paths)` 呼び出し** — ノードを直接変更するすべての操作の先頭行（`_tree_crud_ops.py` の CRUD、`_tree_sync_ops.py` の `apply_text_to_tree` / `_on_blockmesh_vertices_changed`、`_boundary_ops.py` の全境界操作）。呼び出し側が実際の変更を保証するため即座に commit します。次のイベントループティックでリセットされる `UndoState.op_active` が、その操作が内部で行う `setData` からの余分な `about_to_change` 退避を抑制します。

カレントファイルのスナップショットテキストは常にエディタテキストです: 同期している間は読み込んだファイルとバイト単位で一致し（完全に Undo し終えたファイルはディスクと比較してクリーンになる）、ユーザーが未適用のフリーテキストを入力している場合は画面に表示されている内容そのもの — いずれも Undo が復元できるべき状態です。スナップショットが「クリーン」を主張するファイルは、ダーティフラグを下ろす前にディスクと照合されます（変更と Undo の間に保存が行われた可能性があるため）。

コピー・ペーストと同様、Ctrl+Z / Ctrl+Shift+Z のショートカットはツリーに `Qt.WidgetShortcut` スコープで割り当てられているため、下部のテキストエディタは自身のネイティブ Undo を保ちます。両アクションはツリーのコンテキストメニューにも表示されます（**Undo Tree Edit** / **Redo Tree Edit**）。

**このセクションに関わるモジュール。**

- `ui/mixins/_undo_ops.py` — Mixin: スナップショット方式のツリー編集 `Undo/Redo`（ツリーにスコープされた Ctrl+Z / Ctrl+Shift+Z。シリアライズ済みテキストのスナップショットからなる単一のグローバルタイムライン）。

### 3-D ビューアのオーバーレイ

BlockMesh 3-D パネルは `blockMeshDict` を描画し、他の *viewer dictionary* のジオメトリを重ねて表示します。対象は `topoSetDict`、`snappyHexMeshDict`、`setFieldsDict`、そしてサンプリング（プローブ、サンプル線、平面）を定義するファイルで、`controlDict` の `functions {}` 内でも単独の辞書でも構いません。処理は 4 段階です。

1. **ディスパッチ。** `ui/viewer_dicts.py` の `viewer_dict_kind(path, root)` が、ファイル名、次に `FoamFile` の `object` エントリ、（サンプリングは）最後に内容によって、ファイルがどのオーバーレイを供給するかを答えます。[同じ辞書が複数あるケース](#同じ辞書が複数あるケース)を参照してください。`_model_ops._prime_viewer` は、ケース読み込み時とファイルリストの再読み込みのたびに、オーバーレイを供給する `system/`・`constant/` のファイルを、開かずにすべて送り込みます。
2. **抽出。** `foam/block_mesh_extractor.py`・`topo_set_extractor.py`・`set_fields_extractor.py`・`snappy_hex_mesh_extractor.py`・`sampling_extractor.py` が `FoamNode` ツリーを素のデータクラスに変換し、各形状クラスは `foam/shapes.SourceShape` を継承します。ジオメトリのリゾルバ（box・sphere・cylinder・cone・平面）は `foam/tree_utils.py` で、`$var`/`#eval{}` の値は `foam/var_resolver.py` で共有されます。`blockMeshDict` では、`_update_block_mesh_viewer` がまず `foam/include_expand.expand_includes` を実行し、インクルード先で定義された変数を解決します。[3-D ビューア向けのインクルード展開](#3-d-ビューア向けのインクルード展開)を参照してください。
3. **描画。** `ui/panels/block_mesh_panel.py` は Qt 層で、VTK アクタの設定はすべて `RenderSettings` データクラスを介して `block_mesh_renderer.BlockMeshRenderer` に委譲します。形状のジオメトリは Qt 非依存の `shape_mesh.make_shape_mesh` が、常にクリップ前の完全な形状から作ります。レンダラはその後、ブロックメッシュの境界ボックスを各軸 10% 拡げた範囲で表示専用のクリップを行い（形状メッシュは中空の面なので `_clip_capped` が各切断面を塞ぎ、平面ディスクのように体積のない形状は `clip_box` が扱います）、ラベルには ASCII のみで「(clipped)」や「(outside block mesh)」を付けます（[テキストを描画するのは Qt ではなく VTK](#テキストを描画するのは-qt-ではなく-vtk) を参照）。
4. **メニュー。** 各ソースに切り替え可能なメニュー（`topoSet ▾`・`snappyHexMesh ▾`・`setFields ▾`・`sample ▾`・`STL ▾`）があり、すべて `_ShapeOverlayMenu` で作られ、形状ごとのチェックボックス、Show all / Hide all、描画できないエントリ用の「Non-geometric sources (N)」サブメニューを持ちます。`STL ▾` メニューは STL/OBJ の参照オーバーレイ（`block_mesh_renderer.LoadedSurface`）を一覧にし、`ExportStlDialog` を開く **Export Shapes as STL…** を提供します。サンプリング形状はエクスポートから除外されます。

**Save Image。** `ui/panels/_view_image_export.py` は描画されたシーンを `plotter.screenshot(path)` で書き出します。プロッタのネイティブ子ウィンドウでは `QWidget.grab()` が黒を返すため、使いません。`writable_image_path` は pyvista が拒否する拡張子を補正します（pyvista 自身の `SUPPORTED_FORMATS` の判定は大文字小文字を区別するので、`.JPG` は小文字化され、`.txt` には `.png` が付きます）。どちらの補正もファイルダイアログが衝突を確認した名前を変えるため、追加の上書き確認が出ます。ダイアログのフィルタは形式ごとではなく `_IMAGE_SUFFIXES` から導出した 1 つの統合フィルタです。GNOME では Qt がネイティブの GTK チューザに委譲し、GTK は名前フィルタを表示用フィルタとして扱って名前を書き換えないため、形式ごとのエントリでは JPEG を選んでも `.png` の名前のままで PNG が書かれてしまいます。受け付ける形式は、Qt の gtk3 ヘルパがネイティブフィルタのラベルに `(` より前のテキストを使い、パターン部分を捨てるため、フィルタの*名前*の `(` の前に書いてあります。`save_image_action` は View メニューが同じ `QAction` を追加するため公開されており、pyvista がない場合は `None` です。

**ビューアが起動できないとき。** `BlockMeshPanel.init_plotter` は、`QtInteractor(self)` の構築中に再入されることがあります。pyvistaqt 0.13 はインタラクタを `QOpenGLWidget` の上に作り、画面に出ているウィンドウに最初のこのウィジェットが加わると、Qt はそのウィンドウのネイティブサーフェスを作り直します（raster → OpenGL。ウィンドウ ID が変わります）。ウィンドウはいったん隠れて再表示されるので、コンストラクタの中で `showEvent` が走り、`_plotter` がまだ `None` なので `init_plotter` がもう一度呼ばれます。入れ子の `QtInteractor` は `SystemError: … QOpenGLWidget.__init__ … returned NULL without setting an exception` で失敗しました。これは表示中のウィンドウで 3D ビューが *同期的に* 初めて表示されたときだけ起きます。つまりイベントループ開始前にセッション復元が保存済みの BlockMesh タブを選んだときで、例外は `QTabWidget.setCurrentIndex` を抜けて伝わり、FoDE は開きませんでした。起動時の `QTimer.singleShot(0, init_plotter)` はタブが隠れている間に作るので `showEvent` は来ません。Linux（xcb）と Windows で再現。pyvistaqt 0.11 は普通の `QWidget` なので作り直しは起きません。`_plotter_starting` により入れ子の呼び出しはすぐ戻ります。それ以外の `QtInteractor` の例外は捕まえて理由をパネルに表示します（`_plotter_failed` で再試行しない）。ビューアはオプションであり、アプリを道連れにしてはいけないからです。

#### ビューアの背後のモジュール

- `foam/block_mesh_extractor.py` — `blockMeshDict` の `FoamNode` ツリーから頂点・ブロック・境界を抽出。`_HEX_FACE_VERTICES` + `_expand_compact_faces` がコンパクト (`blockIdx`, `faceIdx`) 境界エントリを 4 頂点リストに展開。`_compute_default_faces` は、どのパッチにも割り当てられていない外部ブロック面（`blockMesh` の暗黙の `defaultFaces` — 擬似 2D ケースが boundary に列挙しない面）を `BlockMeshData.default_faces` に収集。`parse_vertices()` はパブリック API。変数解決は `var_resolver` に委譲。
- `foam/var_resolver.py` — 共有の変数解決ロジック: `build_var_map(root, skip_keys)` が任意の深さの $変数（`-$xMax` のような否定マクロ word ノードを含む）と `#eval{}` チェーンを反復的に解決。`substitute_vars()` と `eval_foam_expr()` は両エクストラクタが使うパブリックヘルパー。`eval_foam_expr()` は文字クラスの正規表現ではなく AST 走査（`_EVAL_NODES`）で `#eval` の*文法*を、固定の名前表（`_EVAL_NAMES`: `round`/`floor`/`ceil`/`sqrt`/`min`/`max`/`mag`/`pow`/`abs`、三角関数一式、`exp`/`log`/`log10`、`degToRad`/`radToDeg`、pi）で許可する。これにより `round($x/$y)` を通しつつ、属性アクセスや添字を構造的に拒否できる。
- `foam/shapes.py` — `SourceShape`: すべてのエクストラクタ形状クラス（`TopoShape`、`SnappyShape`、`SetFieldsShape`、`SamplingShape`）が共有する `label/kind/geometry` の基底データクラス — 表示名 + ジオメトリ/ソースのキーワード + 解析済みジオメトリ dict。`BlockMesh` パネル/レンダラーと Export-STL コードが利用する。各サブクラスは独自の追加フィールド（action、`category/level/mode`、`source_file`）のみを宣言する。
- `foam/topo_set_extractor.py` — `topoSetDict` の `action_entry` ノードから描画可能なジオメトリ（box〈`min/max`・複数ボックス boxes 形式を含む〉、rotated box、sphere〈origin エイリアスと `innerRadius` を含む〉、cylinder、cone、点セット〈`nearestTo*/insidePoints/nearPoint`〉、`planeToFaceZone` の平面）を抽出。
  - `raw_list` / マクロ形式のジオメトリ値内の `$var` と `#eval` を `var_resolver` 経由で解決し、`TopoSetData(shapes=[TopoShape(...)])` を返す。
  - `TopoShape` は `shapes.SourceShape` のサブクラス（追加フィールド: action）。
  - ソースごとのジオメトリ分岐は `resolve_source_geometry()` / `is_non_geometric_source()` として公開され、`set_fields_extractor.py` と共有される。
- `foam/set_fields_extractor.py` — `setFieldsDict` の regions ( … ) リスト（`region_block` → `region_entry` ノード。エントリの「名前」がソースタイプ — `boxToCell`、`sphereToCell` など — で、`source` 子ノードは持たない）から描画可能な領域ジオメトリを抽出。`topo_set_extractor.resolve_source_geometry()` を再利用し、各シェイプに `fieldValues` の要約（例: "`alpha.water=1`"）をラベル付けして `SetFieldsData(shapes=[SetFieldsShape(...)])` を返す。`SetFieldsShape` は `shapes.SourceShape` のサブクラス（追加フィールドなし）。
- `foam/sampling_extractor.py` — 描画可能なサンプリングジオメトリ — probes の `probeLocations`（点マーカー）、sets タイプのサンプル線（`start/end`）、surfaces タイプの `plane/cuttingPlane` 円盤 — を `controlDict` の functions {} ブロックまたはスタンドアロンのサンプリング辞書（`system/sample`・probes・surfaces・`singleGraph`。`.org` 系のトップレベル `start/end` スタイルを含む）から抽出。
  - 入れ子のメンバーリストは 2 つの書式とも構造化パーサーノード: 辞書形式 sets {`}/surfaces` {} と、従来の丸括弧リスト形式 sets ( name {…} )（`named_dict_list`）。
  - 平面解決は `tree_utils.resolve_plane_geometry` を再利用。
  - `SamplingData(shapes=[SamplingShape(...)])` を返す。
  - `SamplingShape` は `shapes.SourceShape` のサブクラス（追加フィールド: `source_file`）。
- `foam/snappy_hex_mesh_extractor.py` — `snappyHexMeshDict` の geometry {} プリミティブ（box、sphere〈ベクトル radius によるだ円体を含む〉、cylinder、cone、`constant/triSurface/` から解決される `triSurfaceMesh/distributedTriSurfaceMesh/closedTriSurfaceMesh`（最後のものは両フォークで `triSurfaceMesh` のサブクラスであり、同じエントリを読む）〈`.gz` サイドカーへの透過的な解決を含む〉、box ベースの collection メンバー）を抽出。
  - 各タイプは両フォークの綴りを受け付ける（`searchableBox/box`、`searchableSphere/sphere`、`searchableCylinder/cylinder`、`searchableCone/cone`、`searchableSurfaceCollection/collection` — `_GEOMETRY_TYPE_ALIASES`）。
  - shape の kind には辞書が実際に使った綴りがそのまま残る。
  - `castellatedMeshControls.refinementSurfaces/refinementRegions`（正規表現パターンのサーフェス名を含む）と照合し `surface/region/geometry` に分類。
  - キープポイントは `castellatedMeshControls` 直下のみで、`insidePoints`（リスト）→ `insidePoint` → `locationInMesh` の順（Foundation 自身の優先順位に合わせたもの）に加えて OpenCFD の `locationsInMesh` のペアリストを抽出する。
  - この「直下のみ」という限定が、OpenCFD が `refinementSurfaces` の中で同じ `insidePoint(s)` という綴りを使うサーフェスごとの `cellZone` セレクタと区別する決め手になっている。
  - これらを抽出し、`SnappyHexMeshData(shapes=[SnappyShape(...)])` を返す。
  - `SnappyShape` は `shapes.SourceShape` のサブクラス（追加フィールド: `category/level/mode`）。
- `foam/tree_utils.py` — `topo_set` / `snappy_hex_mesh` / `set_fields` の各エクストラクタが共有する汎用 `FoamNode` ヘルパー: `find_child`、`find_child_any`、`child_vector/child_scalar`（最初に存在するキーを採用し、解決できなくても次のキーは試さない）、`resolve_scalar`、`resolve_vector`、`resolve_point_list`、`expand_evals`、および `box/sphere/cylinder/cone` の共有ジオメトリリゾルバ（`resolve_box_geometry` は `min/max`、`box (min) (max)` ペア、複数ボックス `boxes` の各形式をオプトインフラグで扱う）。
- `ui/viewer_dicts.py` — `viewer_dict_kind(path, root)`: そのファイルがどの 3-D オーバーレイに対応するか（該当なしは None）。まずファイル名、次に `FoamFile` の `object` ヘッダを見るため、既定名でない `topoSetDict-slices` や `topoSetDict.1` もビューアに届く。ファイル名の前方一致にはしていない — `blockMeshDict.resolvedBlocks` などは `#include` されるフラグメントであり、振り分けてはならないため。`_model_ops`（振り分け）と `_panel_ops`（サイドバイサイドボタン）で共有。
- `ui/dialogs/export_stl_dialog.py` — `ExportStlDialog`: 読み込み済みの `topoSetDict`・`snappyHexMeshDict`・`setFieldsDict` のシェイプをチェックリスト表示するモーダルダイアログ。チェックした各シェイプを `shape_mesh.make_shape_mesh` 経由でそれぞれ個別の `.stl` として書き出す。
- `ui/panels/_shape_overlay_menu.py` — 形状ごとのチェック可能なオーバーレイメニュー（`_ShapeOverlayMenu`、`_StaysOpenMenu` と共有ヘルパー）。`block_mesh_panel.py` から分離。パネルを一切参照せず、渡された shape のみに依存。
- `ui/panels/_view_image_export.py` — Save Image ダイアログと画像書き出し。`block_mesh_panel.py` から分離。親ウィジェット・プロッタ・初期パスだけを必要とするため、コントローラではなく関数として切り出している（STL オーバーレイ側はパネルの状態を持つ機構なのでそのまま残してある）。
- `ui/panels/block_mesh_panel.py` — `blockMeshDict` 用 3D ビューア（`pyVista/VTK`、遅延初期化）。
  - `topoSetDict`（`topoSet` ▾ メニュー）、`snappyHexMeshDict`（`snappyHexMesh` ▾ メニュー）、`setFieldsDict` の領域（`setFields` ▾ メニュー）、サンプリング定義（sample ▾ メニュー。`controlDict` の functions {} とスタンドアロンの `system/sample` 系辞書の合算を `_sampling_by_file` に元ファイル名ごとに保持）のジオメトリもそれぞれシェイプ単位の表示切替・Show `all/Hide` all アクション・描画不能エントリ用の「Non-geometric sources (N)」サブメニュー付きで重ねて表示する。
  - アクター構築は `block_mesh_renderer.BlockMeshRenderer` に委譲。
  - STL ▾ メニューには読み込み済み `STL/OBJ` サーフェス用の同じファイル別の行（`block_mesh_renderer.LoadedSurface`。1 ファイル 1 色、Unload サブメニュー付き）があり、「Export Shapes as STL…」は `dialogs/export_stl_dialog.ExportStlDialog` を開く。
  - Save Image… ボタンは描画されたシーンそのものを `plotter.screenshot()` で書き出す（このネイティブ子ウィンドウに対して `QWidget.grab()` は黒画像を返すため）。
  - その `QAction` は `MainWindow` が View メニューにも追加する。
- `ui/panels/block_mesh_renderer.py` — `BlockMeshRenderer`: `RenderSettings` データクラス経由の `blockMeshDict/topoSetDict/snappyHexMeshDict/setFieldsDict` ジオメトリ用 VTK レンダリングパイプライン。
  - 色テーブル（`_PATCH_COLORS`、`_ACTION_COLORS`、`_SNAPPY_CATEGORY_COLORS`、`_SET_FIELDS_REGION_COLOR`、`_SURFACE_COLORS`）と `_opacity()`（テーマ依存の alpha 倍率）は `ui.theme` に依存するためこちらに残る。
  - シェイプごとの描画メソッドは Qt に依存しないジオメトリ生成/クリッピング/ラベル付けを `shape_mesh.make_shape_mesh()/_clip_to_bounds()/_mark_label()` 経由で呼び出す。
  - `_render_boundary_faces` は `BlockMeshData.default_faces` も薄い "empty" グレーで描画する。
  - pyvista のガードを通過した後にのみインポートされる。
- `ui/panels/shape_mesh.py` — `block_mesh_renderer.py` から切り出した Qt に依存しないジオメトリ生成（Qt import なし、self なし）。
  - `make_shape_mesh()` はジオメトリ辞書のキー（box、boxes、centre+radius〈リスト radius によるだ円体と `innerRadius` による中空球を含む〉、p1+p2+radius、origin+i+j+k、`stl_path`、`planePoint+planeNormal`〈`plane_size` で寸法指定される円板〉。points は None を返しマーカーとして別途描画）で分岐し、全オーバーレイソースおよび `dialogs/export_stl_dialog.py` で共有される。
  - オーバーレイシェイプは `_clip_to_bounds` により、ブロックメッシュの AABB を各軸 10% 拡大した範囲へ（表示上のみ）クリップされる — ラベルには `_mark_label` 経由で「(clipped)」/「(outside block mesh)」マークが付き（ASCII のみ: VTK のラベルフォントは絵文字記号のグリフをまったく描画しない）、シーンを包み込むシェイプは AABB の重なりボックスにフォールバックする。
  - `read_surface_mesh()` は gzip 圧縮された `.stl/.obj` を透過的に展開する。
  - `block_mesh_renderer.py` と同様 pyvista は無条件にインポートされ、ガードされるのは pyvistaqt のみ。

### レイアウトとパネル

メインウィンドウのパネルがどう組み合わさるかを説明します。2 つのターミナルモードと、それぞれが BlockMesh タブに与える影響、View メニューのアクション、方位軸、サイドバイサイドモードとプレビューモードです。

**ターミナルのモード。** `TerminalPanel` は、QtWebEngine が使えれば `XtermTerminalWidget`（`QWebEngineView` 内の xterm.js v6 と PTY。完全な VT100/xterm エミュレーションと対話プログラム）を、使えなければ `SimpleTerminalWidget`（永続的なシェル — Linux/macOS では `bash`、Windows では `cmd.exe` — を動かす `QProcess`。ANSI エスケープは除去）を既定にします。xterm の間は BlockMesh タブが隠れ、**View > BlockMesh 3-D Panel** は上記の GPU の理由で無効になります。Simple モードへ切り替えるとタブが表示され、項目が再び有効になります。実行中のジョブがあるターミナルを閉じる前に確認する処理は、シェルの子プロセスを `/proc` から読むため Linux で動作し、それ以外では何も出しません。

**View メニューのアクション** — `_build_menu_bar` 内の `_blockmesh_action`（`QAction`、チェック式）は、ターミナルモードとは独立して BlockMesh タブを表示・非表示にする第 2 の手段です。xterm が有効な場合はアクションが無効化され、テキストが `"BlockMesh 3-D Panel  (unavailable: xterm active)"` に変わって理由をホバーなしで表示します。`_on_terminal_mode_changed` がアクションの有効状態とラベルをターミナルモードと同期させ、`_on_toggle_blockmesh_panel` がユーザーのクリック時に実際のタブ追加・削除を処理します。

**Axes ウィジェット** — `add_axes()` は `vtkOrientationMarkerWidget` を生成します。このウィジェットはアクター（`plotter.clear()` で消去される）ではないため、`clear()` をまたいで持続します。そのため `init_plotter()` で一度だけ呼び出します。`_render()` では毎フレーム再追加するのではなく `show_axes()` / `hide_axes()` でトグルします。

#### サイドバイサイドモード

`⊞` トグルボタン（`_bm_side_by_side_btn`）が `QTabWidget` のコーナーウィジェットとして追加されます。有効化すると `_on_toggle_bm_side_by_side` が `block_mesh_panel` を `upper_tabs`（`QTabWidget`）から `_tree_bm_splitter`（`right_upper_splitter` をラップし Tree タブのコンテンツとなる `QSplitter(Qt.Horizontal)`）へ再ペアレント化します。リペアレント前にまず Tree タブへ切り替えてスプリッターを可視状態にし、`setSizes([1,1])` と `init_plotter()` は `QTimer.singleShot(0, ...)` で次のイベントループティックまで遅延させます。サイドバイサイドモードを切ると `block_mesh_panel` は通常タブとして `upper_tabs` に戻されます。`_update_bm_side_by_side_btn`（`ui/mixins/_panel_ops.py`）は、現在のファイル名が `blockMeshDict`・`topoSetDict`・`snappyHexMeshDict`・`setFieldsDict`、またはサンプリング名（`SAMPLING_DICT_NAMES`: `controlDict`・`sample`・`probes`・`surfaces`・`singleGraph`）のいずれか（いずれも同じ 3D ビューに描画される — `block_mesh_extractor.py`、`topo_set_extractor.py`、`snappy_hex_mesh_extractor.py`、`set_fields_extractor.py`、`sampling_extractor.py` を参照）で、BlockMesh タブ自体が有効、かつ xterm が非アクティブなときにボタンを有効化します。それ以外はボタンを無効化し、サイドバイサイドモードが有効であれば強制的に解除します。

#### 比較パネルの表示制御

`comparison_panel` は起動時に `right_upper_splitter` へ追加されますが直後に非表示（`comparison_panel.hide()`）になります。`QSplitter` は非表示の子ウィジェットを無視するため、ハンドルや隙間は表示されません。`_on_side_by_side_toggled(True)` では `setSizes` 前に `comparison_panel.show()` を呼び、`_on_side_by_side_toggled(False)` と `_clear_diff` では `comparison_panel.hide()` を呼びます。

#### プレビューモード

`BlockMeshPanel` は `update_block_mesh()` 呼び出しごとに設定される 2 つのフラグを持ちます: `_has_variables`（`vertices` の raw_list 値に `$` 文字が含まれる場合 True）と `_preview_mode`（デフォルト False、**Preview** ボタンでトグル）。`_has_variables` が True の場合、Vertices グループボックス内のテーブル上部に `_vtx_info_bar`（琥珀色の **⚙ Variable-based** チップ + **Preview** トグルボタン）が表示され、X/Y/Z セルは読み取り専用になります（`rw_flags = ro_flags`）。`_preview_mode` が True の場合はセルが編集可能になり、`_on_cell_changed` は `vertices_changed` を emit する代わりに `_render()` を直接呼び出してツリーとファイルを変更しません。`_on_refresh()` はプレビューモード中に `self._root` から再抽出してから `_render()` を呼び出し、頂点データのリセットとプレビュー終了を同時に行います。

### セッションの復元

FoDE は前回の続きから開きます。復元するのは、ウィンドウのジオメトリ、スプリッタ、タブ、開いているケースとファイル、ツリーの選択、3-D のトグルとカメラ、最小化されているペインです。ユーザーに見える挙動はユーザーガイドの「Session restore」にあります。担当するモジュールは 2 つで、意図的に分けてあります。

`ui/window_state.py` がモデルです。`WindowState` と `BlockMeshViewState` のデータクラス、そして `capture_window_state(window)` と `apply_window_state(window, state, settle=…)` を持ちます。レイアウトのうち「結果」ではなく「選択」にあたる部分だけを保持し、ウィンドウが再導出するもの（選択の祖先を超えるツリーの展開、スクロール位置、エディタのカーソルと折りたたみの状態）は含めません。状態は JSON にできるので、プロセスをまたいで残ります。サイズは `saveState()` と `saveGeometry()` の blob（base64）で運び、手で書ける代替として `splitter_sizes` があります。`minimized_panes` は `ui/pane_minimize.py` の `PANE_*` 名を、そのペインを復元するサイズに対応づけます。スプリッタの blob には折りたたまれた後のジオメトリしか残らず、何から折りたたんだかが分からないためです。`_apply_minimized_panes` はスプリッタの blob の後に走り、最小化した後で記憶していたサイズを書き込みます。最小化は折りたたむ前のサイズを記録するので、先に書くと上書きされてしまうからです。`apply_block_mesh_view` が別になっているのは、描画のたびに `reset_camera()` で終わるため、固定したカメラはシーンが落ち着いた後でもう一度適用する必要があるからです。`settle` は、Qt が後のイベントループの周回でしか終えない手順のための、呼び出し側のフックです。3-D 側は `BlockMeshPanel.view_state()` と `apply_view_state()` が担います。

`ui/session_restore.py` は実行間をつなぐ配線で、モデルは持ちません。`save_session(window)` は `MainWindow.closeEvent` からパネルを破棄する前に呼ばれ（シャットダウン済みの BlockMesh パネルにはカメラがありません）、`AppConfigManager` の自動保存なしの規則に従うため、`closeEvent` 自身の `cfg.save()` が書き込みます。`restore_session(app, window)` は `main.py` から `window.show()` の後、先行 VTK 初期化のブロックの前に呼ばれます。そのブロックの xterm チェックは、復元が選んだモードを見る必要があるためです。レイアウトは `AppConfigManager.session_key()` のもとに機能の組み合わせごとに保存されます。キーは `--variant` の名前（保存されず、素の起動では存在しません）ではなく `terminal` と `blockmesh` のフラグから導くので、バリアント同士が上書きし合うことはありません。カメラは 2 回適用します。1 回は直ちに、もう 1 回はタイマーで。ケースの読み込みが引き起こす描画は呼び出しが返った後に届き、どれも `reset_camera()` で終わるためです。`--no-restore` はその 1 回の実行だけ復元を飛ばし、保存済みのセッションには触れません。

**strict と lenient の読み込み。** `WindowState` の 2 つの利用者はエラー処理が正反対で、`from_dict` と `apply_window_state` の `strict` フラグはそのためにあります。スクリーンショットの spec（[スクリーンショットの撮影](#スクリーンショットの撮影)を参照）は strict を求めます。未知のフィールド、存在しないタブ、古くなったツリー行は、そう伝えるべき不具合だからです。保存されたセッションは lenient を求めます。保存されたレイアウトは、アプリの起動を止めるのではなく、今の既定値へ縮退しなければなりません。lenient の読み込みは `load_saved_state()` を通り、lenient の適用は、飛ばしたものを例外にせずメモとして返します。`session_restore` はそのメモをダイアログではなくステータスバーに出します。モーダルは起動時の挨拶にふさわしくないためです。ディスクから読んだものに strict 経路を流用してはいけません。寛容さは `from_dict` だけでなく 7 か所に分かれています（未知のフィールド、不正な値、存在しないケースディレクトリやファイル、開くと確認が出る大きな非辞書ファイル、未知のタブやスプリッタ、未知のペイン、解決できないツリー行）。

## UI の規約

UI 全体に適用される規則です。文字列・色・フォントサイズの出どころと、それらの多くの背景にあるハードウェア・プラットフォーム上の制約（GPU、表示スケーリング）を扱います。

### 国際化（i18n）

`ui/` 内のユーザー向け文字列は、以下の2つの意図的な例外を除いてすべて `i18n/__init__.py` の `tr()` でラップされています。英語の文字列がそのままキーとして機能し、翻訳が存在しない場合は英語にフォールバックします。この状態を維持する回帰防止テストが `tests/ui/test_translatable_strings.py` です — `ui/**/*.py` を AST で走査し、文字列リテラル（または補間されない固定テキストを持つ f-string）が `tr()` を経由せず Qt の表示シンクへ到達した場合に失敗します。シンクの一覧、`_LOCAL_SINKS`/`_ALLOWED` の除外テーブル、一回限りのケース向けの `# i18n: skip` コメントについては、そのテストのモジュール docstring を参照してください。

**実行時の流れ**
1. `main.py` がウィンドウ作成前に `set_language(get_app_config().get_language())` を呼び出します。
2. 各ウィジェットのコンストラクタが `tr("some string")` をインスタンス化時に呼び出すため、選択言語が起動時に UI 全体へ適用されます。
3. 言語変更はアプリ再起動後に反映されます（ライブ再翻訳なし）。

手順1は `ui.main_window`（およびそれが import するすべて）が既に読み込まれた**後**に実行されます — `main.py` では `from ui.main_window import MainWindow` が `set_language(...)` より上にあります。そのため、モジュールレベルの文字列定数を*定義時*に `tr()` でラップすると、ユーザーがどの言語を選んでも永遠に英語のまま固定されてしまいます。`ui/panels/block_mesh_panel.py` の `_MOUSE_HINT`/`_MOUSE_HINT_TOOLTIP` がまさにこの理由でプレーンな英語定数のままになっている例です — `tr()` は定義箇所ではなく、実際に*使用される*箇所（ウィンドウが実際に構築されるときにのみ実行される `__init__` の中）で適用します。

**2つの例外: VTK が描画するテキスト**

`ui/panels/block_mesh_renderer.py` と `ui/panels/shape_mesh.py` は `tr()` 対応の対象から恒久的に除外されています。これらの文字列は最終的に VTK 自身の組み込みラベルフォントで描画されます（下の「テキストを描画するのは Qt ではなく VTK」参照）。このフォントはグリフを持たない文字に対して**何も描画しません** — 日本語ラベルは誤訳として表示されるのではなく、まったく表示されなくなります。`tests/ui/test_shape_mesh.py` と `tests/ui/test_block_mesh_renderer_colors.py` は既に両モジュールが ASCII のみであることを AST でアサートしているため、これらを翻訳することは単に無意味であるだけでなく、既存のテストによって積極的に禁止されています。`test_translatable_strings.py` 自体の走査対象からも、同じ理由でこの2ファイルを除外しています。

**補間には `.format()` を使用し、f-string は使わない**

`tr()` は `TRANSLATIONS` の中を文字列の完全一致で検索するため、`tr()` に渡すテキストはどの呼び出しでも同一でなければなりません。f-string は*描画後の*値をそのままルックアップキーへ焼き込んでしまうため、`tr(f"Line: {n}")` は `i18n/ja.py` のどのエントリとも一致し得ません。代わりに翻訳した*後で*補間してください: `tr("Line: {n}").format(n=n)` とし、`"Line: {n}"` を `tr()` 呼び出し側と `i18n/ja.py` の両方でリテラルキーとして使います。`ui/panels/file_list_panel.py` の `tr("included from {origin}").format(origin=origin)` がこの方式の元祖です。

**`▾` のドロップダウンマーカーはキーの外に置く**

`ui/panels/block_mesh_panel.py` のドロップダウンボタン（`topoSet ▾`、`STL ▾` など）は、翻訳キーの中にこの記号を織り込む（`tr("topoSet ▾")`）のではなく、`_menu_button()` 自身の中で、翻訳済みのラベルへ `" ▾"` を後から付加しています。このマーカーは装飾であって文章ではありません — `"topoSet ▾"` と `"snappyHexMesh ▾"` を無関係な2つの文字列として翻訳すると、末尾の記号だけが違う（しかもどの言語でも変わらない）ほぼ重複のキーが7つできてしまいます。呼び出し側は `tr("topoSet")` を渡すだけで、記号は `_menu_button` が後から付加します。

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

### テーマと配色

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

**アイコンの色付け。** `ui/icons.py` の `icon(name) -> QIcon` は `ui/assets/icons/` 以下の手描き SVG を読み込み、有効なテーマに合わせて色を付けます。すべての SVG は黒（`fill="#000"`/`stroke="#000"`）で作成されており、`currentColor` はどこにも使っていません — Qt の SVG Tiny 1.2 レンダラには CSS カスケードがないため、ブラウザとは違って `currentColor` はそもそも解決されないからです。したがって色付けは SVG のソース自体には一切触れません: グリフを透明な `QImage` に描画し、`QPainter.CompositionMode_SourceIn` で画像全体をティントカラーで塗りつぶしたうえで、グリフ自身の alpha の外側をすべて消し去ります。これは文字列置換ではなくアルファマスクです — アイコン内部に「間違えうる16進文字列」が存在しないため、「黒いアイコンがダークモードで見えなくなる」という事態は、10 個目のアイコンを追加する誰かが覚えておくべきルールではなく、構造的に起こり得ないことになります。

ティントカラー自体は `theme.icon_tint()` が返します — `QApplication.palette().color(QPalette.ColorRole.ButtonText)` を呼び出しのたびにライブで読むだけです。これは意図的に `ThemeColors` のフィールドには**していません**: `system` モードでは `apply_theme` がデスクトップ自身のパレットをそのまま残すため、ボタンテキストがほぼ黒でもほぼ白でもないデスクトップテーマに対しては、`_LIGHT`/`_DARK` に固定した16進値はたまたま正しいだけということになってしまいます。パレットをそのまま読むことだけが、3 つのモードすべてで正しい唯一の情報源であり、これによって `ui/theme.py` が `QPalette` に触れる唯一のモジュールという位置づけも保たれます — `ui/icons.py` は `QPalette` を一切 import しません。

`icon()` の `size`/`tint` 引数は既定で `fonts.icon_pixel_size()`/`theme.icon_tint()` を使い、どちらも呼び出し時に解決されます。import 時には解決しません — これは `ui/theme.py` と `ui/fonts.py` がすでに従っているのと同じルールです。デスクトップフォントも有効なテーマも、このモジュールが最初に import された後に確定するからです。背後にあるモジュールレベルの `(name, size, tint)` キャッシュは、そのルールが警告している「import 時キャッシュ」には当たりません: フォントとテーマはキャッシュキーへの**入力**であるため、テーマの切り替えやフォントの変更が起きればキャッシュは単に外れて再描画されるだけです — 古いエントリが残り続けることはなく、そもそも到達不能になります。失敗するパターン — SVG ファイルが存在しない、`PySide6.QtSvg` の import に失敗する、`QSvgRenderer.isValid()` が false を返す — はすべて例外を送出せず null の `QIcon` を返します。壊れたアイコンアセットがアプリの起動を止めることは決してあってはならないからで、null のアイコンはただ何も描画しないだけです。

`tests/ui/test_icons.py` は `ICON_NAMES` とアセットディレクトリの対応を両方向で検証し（ファイルのない名前とファイルはあるが名前のないもの、どちらも失敗させます）、すべてのアイコンが null でなく空でないピクセルとしてレンダリングされることを確認し、そして — 文字列置換版のバグへの回帰を実際に捕捉する検査として — アイコンの**不透明**ピクセル（透明な背景が平均を薄めないよう alpha でマスクします）の平均輝度が、`apply_theme(app, "dark")` の下では高く、`apply_theme(app, "light")` の下では低いことを確認します。

**選択行の可読性。** Qt は選択の塗りをデスクトップから（Windows 11 ではアクセントカラー）、選択行の文字色をシステムパレットから別々に取り、両者が一緒に読めるかは誰も確認しません。その結果、ツリーとファイルリストで彩度の高い青の選択の上にほぼ黒の文字が載っていました。FoDE は 3 つのテーマモードすべてで `readable_selection_pair` が組を再計算します。塗りの上で十分に読めるなら白文字、本当に明るい塗り（黄色やパステルのアクセント）なら暗い文字、それ以外は塗りを色相を保ったまま少し暗くして白文字が読めるようにします。ツリー、ファイルリスト、境界テーブル、比較パネルに適用されます。

**このセクションに関わるモジュール。**

- `ui/icons.py` — `icon(name)` → `QIcon`: `ui/assets/icons/` の SVG を、その時点の `ButtonText` 色でアルファマスク経由で着色。
- `ui/theme.py` — テーマモード（`system/light/dark`）、Qt がデスクトップから継承する `Highlight/HighlightedText` の組を修復する `readable_selection_pair()` のコントラスト規則、および `colors()` 経由で解決されるすべての UI 意味色を保持する `ThemeColors` テーブル。

### フォントサイズと表示スケーリング

仕組みは 2 つあり、どちらも「文字が小さすぎる」という形で現れるため混同されがちです。

#### サイズはアプリケーションフォントから決まる

`ui/fonts.py` は等幅フォントのサイズをすべて `QApplication.font()` から導出します。UI 側でポイント数を直接指定している箇所はありません。このモジュールを追加する前は 3 か所が指定していました — エディタ 10 pt、シンプルターミナル 10 pt、xterm.js のページ 13 CSS px — その結果、デスクトップのフォントが 11 pt の環境では、本文が置かれている 2 つのペインがウィンドウ内でもっとも小さい文字になり、しかもユーザーがデスクトップのフォントサイズを上げても変化しませんでした。

- `ui_point_size()` はアプリケーションフォントに*設定された*サイズを読み、ピクセル指定のフォント（そう指定するプラットフォームテーマがあり、その場合ポイントサイズは `-1` を返します）のときにだけ `QFontInfo` にフォールバックします。この順序には意味があります。`QFontInfo` は fontconfig が実際に*マッチさせた*フォントのサイズを、ピクセル単位に量子化して返すため（96 dpi の 13 pt は 12.75 pt として返ります）、ユーザーが選んだサイズを問い合わせのたびに丸めるのは、この層の仕事ではありません。
- `monospace_font()` はファミリ一覧とそのサイズを組み合わせたもの、`css_pixel_size()` は xterm.js ページ用に CSS ピクセル（固定の 96/72）へ変換したものです。後者は `ui/xterm_terminal.html` の `<!--XTERM_FONT_SIZE-->` プレースホルダ（既存の CSS/JS 用と同じ方式）経由で渡されます。Qt 6 では論理 DPI が 96 に固定され、スケーリングはデバイスピクセル比が担います。WebEngine は CSS ピクセルにも同じ比率を適用するため、両者の比は一定に保たれます。

- `icon_pixel_size()` も同じ考え方で `ui/icons.py` のツールバー/メニューアイコンのサイズを決めます: `css_pixel_size()` の `ICON_TO_TEXT_RATIO`（1.30）倍を、`ICON_MIN_PIXEL_SIZE`（12）を下限として使います。9 pt の既定値ではこれが 16 px になります — 慣習的な小アイコンのサイズですが、16 を直接指定しているわけではないため、デスクトップフォントを上げれば隣のテキストと同じようにアイコンも大きくなります。`ui_point_size()` を直接使わず `css_pixel_size()` を経由しているのも意図的です: アイコンは xterm.js のフォントと同様、ポイントではなくピクセルで測るものだからです。
- `small_point_size()` / `small_font()` は補助的なテキスト — BlockMesh パネルのマウス操作ヒント行と「⚙ Variable-based」バッジ、About ダイアログのバージョン・ライセンス・謝辞の各行 — を、アプリケーションフォントに対する比率（`SMALL_TEXT_RATIO`。下限として `SMALL_TEXT_MIN_POINT_SIZE` を設け、もともと小さいデスクトップフォントに引きずられて読めなくならないようにしています）で扱います。
- `heading_point_size()` / `heading_font()` は 1 段大きいサイズ（`HEADING_TEXT_RATIO`）で、About ダイアログのアプリ名の行が使います。併用する太字はスタイルシートに残しています。ウェイトはサイズではなくスタイルだからです。
- `button_pixel_width(text)` はポイントサイズではなく*幅*を答えます。最小幅を固定していたボタンのための入り口です — BlockMesh パネルの `+X`〜`Iso` カメラビューボタン、diff バーの `Clear`、ファイル一覧の `⟳` リフレッシュボタン、そして 2 つのペイン隅のグリフ（`▁`/`▔`、`⊞`）。隣にある Label size スピンボックスにヘルパーは不要です: `QSpinBox.sizeHint()` は `CT_SpinBox` を通じてスタイルに問い合わせており、その値には上下ボタンの分がすでに含まれているため、自分自身のヒントを下限にできます。アプリケーションフォントでのテキスト自体の幅を測り、そこに `_button_chrome_pixels()`（`PM_ButtonMargin`/`PM_DefaultFrameWidth` を*アクティブな*スタイルから呼び出し時に読み取ったもので、決め打ちではありません）を足します。`QPushButton.sizeHint()` を再利用しないのは、それがスタイルの定めるボタンの全体最小幅（Fusion で 80px、Qt の Windows スタイルで 75px。どちらもフォントによらず一定）に支配されており、これらのあえてコンパクトに保たれた行の狙いを台無しにしてしまうからです。`BUTTON_CHROME_MIN_PIXELS`（14。Fusion 自身の値）は、スタイルが報告する値の下限であると同時に、`QApplication` が存在しないときの答えそのものでもあります。

この 2 つで、固定されていた 8 か所のピクセル指定（11, 11, 16, 12, 12, 12, 13, 13）を置き換えました。2 つの免責事項ボックスにはヘルパーを使わず、`font-size: 13px` を単に削除しています。免責事項は周囲の本文と同じ読みやすさであるべきで、それはまさにアプリケーションフォントそのものだからです。

ここから導かれる原則があります。**サイズはフォントで、スタイルはスタイルシートで指定する。** スタイルシートの `font-size` はウィジェット自身のフォントを上書きするため、その上で `setFont` を呼んでも効きません。色・パディング・イタリックだけを指定したスタイルシートなら、サイズには手を触れません。`tests/ui/test_block_mesh_panel_fonts.py` と `tests/ui/test_dialog_fonts.py` が両方を固定しており、後者にはどちらのダイアログのラベルもサイズを再び固定していないことを確認する検査も含まれています。

幅についても対になる原則があります。**`setFixedWidth` は起点ではなく上限である。** 最小幅だけでなく最大幅も固定してしまうため、1 つのフォント・1 つのプラットフォームスタイルに対して測った数値が、他のあらゆる環境で硬い天井になってしまいます — BlockMesh パネルの Label size スピンボックスに数字がまったく表示されなくなったのは、まさにこれが原因でした。52px という幅は、Fusion スタイルの 16 pt の時点で、Qt 自身の `minimumSizeHint()` によってすでに超えられています。上記のすべての固定幅は今では`setFixedWidth(max(<元の数値>, <スタイルとフォントが必要とする幅>))` になっています — ボタンでは `button_pixel_width(<自分自身のテキスト>)`、スピンボックスでは `sizeHint().width()` です。元の数値はコンパクトな場合の下限として残るだけで、より広い場合の上限としては働きません。

インポート時のキャッシュは行いません。アプリケーションフォントは最初のウィジェットが作られる前にプラットフォームテーマが確定させるためで、`ui/theme.py` が構築時に `colors()` を読むのと同じ理由です。

**エディタのズーム**（`CodeEditor.set_zoom_steps`）は、絶対サイズではなくアプリケーションフォントからのポイント単位の差分として保持されます。そのため、デスクトップのフォントが異なるマシンでも保存されたズームが意味を保ち、`WindowState.editor_zoom` として永続化しても安全です。クランプは呼び出し側ではなくセッター側で行うので、キーを押しっぱなしにしても、画面に反映されなかった段階が溜まることはありません。`Ctrl+ホイール` には明示的な `wheelEvent` が必要です。`QPlainTextEdit` は実装を持っていますが、読み取り専用のときにしか働きません。

#### 折り返しラベルが申告する高さ

関連する落とし穴で、About / Resources ダイアログでテキストが切れていた原因でもあります。折り返し表示の `QLabel` の `sizeHint()` は、実際に与えられる幅ではなく Qt が推定した幅で測られます。幅固定のダイアログではこの推定は常に楽観的で、About ダイアログの謝辞ラベルは実際の幅 458 px では 176 px 必要なのに 102 px と申告していました。レイアウトは小さい方の値を割り当て、残りの行は描画されませんでした。11 pt という一般的なデスクトップフォントでも発生し、フォントが大きいほど悪化します。

`ui/label_fit.py` の `fit_wrapped_labels(root)` は、各折り返しラベルの*最小*高さを `heightForWidth(width())` まで引き上げます。呼び出し方について重要な点が 3 つあります。

- **最初のレイアウト完了後に**、`showEvent` から呼ぶこと。それ以前にラベルは自分の幅を知らず、既定の幅から求めた最小高さを固定してしまうと、以後ずっと誤った値のままになります。
- **リサイズの前に `layout().activate()`** を呼ぶこと。新しい最小高さがレイアウトを遡って伝わってから、ダイアログ自身のサイズヒントを読む必要があります。
- **`adjustSize()` ではなく `resize(width(), sizeHint().height())`** を使うこと。前者はウィンドウを画面高さの 2/3 にクランプするため、小さいディスプレイではまさにそこでテキストがまた切れてしまいます。

修正手段として*効かない*ものにも触れておきます。`QSizePolicy.setHeightForWidth` を有効にすることです。これらのラベルでは `hasHeightForWidth()` はすでに true であり、レイアウトは height-for-width を無視しているのではなく、それと矛盾する `sizeHint` を渡されているだけです。

`tests/ui/test_dialog_label_fit.py` が 9 / 11 / 16 pt の 3 通りで両ダイアログを構築し、どの折り返しラベルにも必要な高さ未満が割り当てられていないことを検証します。

##### 繰り返しフィットする: Detail ペイン。

`ui/panels/detail_panel.py` でも同じ「最終行が切れる」バグが起きていました（スキーマに選択肢があるキーを選んだときの `_choice_hint_label`）。ただしこちらは `showEvent` で一度だけ処理すれば済むダイアログではありません。ツリーの選択が変わるたびに再描画され、`right_upper` スプリッタをドラッグするたびに幅も変わります。それも再描画とは無関係にです。一度だけフィットする方式では、直前に処理したときの幅から得た最小値がそのまま残ってしまいます。

`ui/label_fit.py` 自体には手を入れていません。これは意図的です。`fit_wrapped_labels` は最小値を*引き上げる*だけで、それは一度だけフィットするダイアログには正しい振る舞いです — すでに十分な余白を与えられたラベルはそのまま余白を保ちます。About / Resources ダイアログは一度表示されたら縮む必要がないため、最小値を下げ直す機能は不要どころか害になります。Detail ペインが必要としているのは逆の振る舞いです。広いスプリッタ幅のときに引き上げた最小値は、後で幅が狭くなったときまで残ってはいけません。残ってしまうと、もう広い余白を必要としないラベルの下に隙間が空いたままになります。そのためこの振る舞いは共通ヘルパー側ではなく、ペイン自身の `_refit_labels()` に置かれています。`fit_wrapped_labels` を呼ぶ前に、折り返し表示のすべてのラベルの最小高さを一旦ゼロへ戻すので、呼び出しのたびに直前の幅を引きずらず、まっさらな状態から計算し直せます。

`_refit_labels()` は 3 箇所から呼ばれます。`_populate_normal`/`_populate_field_value` の末尾（`_stack.setCurrentIndex` の**後**であって前ではありません — `QStackedWidget` はページがカレントになって初めて実際のジオメトリを割り当てるため、先にフィットしてしまうと直前のページの古い幅を測ることになり、最初の選択では 0 になってしまいます）、そしてスプリッタドラッグのケースを `showEvent` だけではカバーできないために追加した `resizeEvent` オーバーライドです。

`fit_wrapped_labels` の呼び出しを 2 回の `layout().activate()` で挟んでいるのは、ダイアログ側の 2 段階（`activate()` してから測る）と同じ理由からですが、こちらは 2 倍に増えています。測定**前**の 1 回目の activate が必要なのは、この populate で初めて表示されたラベル（それまで隠れていたスキーマの注記など）がまだ古い幅 — 一度も表示されたことがなければ 0 — を持ったままで、`fit_wrapped_labels` は `width()` が `<= 0` のラベルを黙ってスキップしてしまうためです。2 回目の activate は、`fit_wrapped_labels` が設定したばかりの最小値を反映させるためのもので、ダイアログ側のフィット後 1 回の activate と同じ役割です。

最後の `self._stack.resize(...)`（スタック自身の `sizeHint().height()` へ）は、ダイアログには不要なひと手間です。`activate()` はページの*現在の*矩形の中でしか空間を再配分しないため、ページがより多くの高さを必要とするようになっても、それだけではスクロールエリアが把握している範囲の外側に余分な高さが取り残されたままになります。ここで明示的にリサイズを起こすことで、その分がすぐにスクロール可能になります。

`tests/ui/test_detail_panel_fit.py` は、通常ページの折り返しラベルが複数行を必要とするほど狭い幅で、3 通りのフォントサイズでペインを構築し、スクロールエリアのスクロールバー範囲が `_choice_hint_label` の下端に届くことを確認します（`sizeHint()` では不可 — 本リポジトリの「Qt ペインのはみ出しを測る」の教訓のとおり、実際に画面で切れたかどうかに関わらず同じ（誤った）値を返してしまいます）。別のテストケースでは、広い幅で populate してから狭めることで、populate 時のフィットではなく `resizeEvent` 自身の再フィットを検証します。

#### Qt のスケール係数と、設定に再起動が必要な理由

Qt はスケール係数を `QApplication` の構築時に確定し、その後に変更する手段を提供していません。そのため **Settings > UI Scale** は、プロセス内から環境変数 `QT_SCALE_FACTOR` を書き込む形になっています（`main._apply_ui_scale`。`parse_known_args` と `QApplication` の間で呼ばれ、モジュール冒頭の `QTWEBENGINE_CHROMIUM_FLAGS` と同じ「Qt が起動する前に設定する」手法です）。値は `ui_scale` キー（パーセント。`AppConfigManager.get_ui_scale`/`set_ui_scale`、他と同じく自動保存なし）として永続化され、設定時と読み込み時の両方で `MIN_UI_SCALE`/`MAX_UI_SCALE` にクランプされます。手で 5000 と書かれた設定ファイルは、それを直すための設定画面にたどり着けないウィンドウを開いてしまうためです。

設定ファイル由来の値は `setdefault` で入れるため、既存の `QT_SCALE_FACTOR` が優先されます。環境変数はユーザーが今使っているマシンに合わせて設定されたものだからです。`--ui-scale` は代入で上書きします。明示的に渡すというのはそういう意味だからです。

この設定が必要なのは、Qt の高 DPI 対応がセッションから伝えられる情報以上のことはできないためです。X11 ではスケール係数は `Xft.dpi` だけから決まるので、`GDK_SCALE` で拡大しているデスクトップや、フラクショナルスケーリングされた XWayland セッションでは、隣の GTK アプリケーションが正しく表示されていても Qt は 1 倍のままになります。ユーザー向けの説明は USER_GUIDE_ja.md の「文字サイズと表示スケーリング」にあり、`QT_FONT_DPI` と `QT_SCALE_FACTOR_ROUNDING_POLICY` という逃げ道も含めて記載しています。

**このセクションに関わるモジュール。**

- `ui/fonts.py` — UI が描くすべてのフォントサイズ。`QApplication.font()` から導出。

### GPU / OpenGL に関する注意

Linux 上では、次の 2 つのサブシステムが GPU に同時アクセスします。

- **VTK / pyVista**（`block_mesh_panel.py`）— `QtInteractor` 経由で OpenGL を使用し 3D レンダリングを行います。`features.blockmesh=true` のときのみ存在します。
- **Qt WebEngine**（`_xterm_widget.py`、`XtermTerminalWidget`）— 独自の GPU プロセスを持ちます。`features.terminal=true` のときのみ存在します。

これら 2 つは同一 GPU コンテキストに安全に共存できません。`main.py` で次の回避策を適用しています。

1. `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --disable-vulkan --log-level=2` を設定し、WebEngine を SwiftShader（CPU ソフトウェアレンダリング）で強制起動することで GPU を VTK 専用に開放します。`--log-level=2` は `--disable-gpu` の副作用として表示される "GPUInfo not initialized on GpuInfoUpdate" という Chromium の警告を抑制します。
2. 起動時に `block_mesh_panel` が `None` でなく、かつターミナルが存在しないかシンプルモードの場合は、`QTimer.singleShot(0, block_mesh_panel.init_plotter)` で VTK を先行初期化し、ユーザー操作より前に OpenGL コンテキストを確保します。

ターミナルモードの切替（`TerminalPanel.mode_changed` シグナル）では、xterm 起動前に VTK をシャットダウンし、シンプルモードへ戻る際に 300 ms の遅延後に VTK を再初期化します。このシグナルは `terminal` と `blockmesh` の両方が有効なときのみ接続されます。

#### テキストを描画するのは Qt ではなく VTK

3D シーン自身のテキスト（形状名バッジ、頂点番号とブロック番号、範囲表示、方位軸の文字、グリッドの目盛りラベル）は VTK の組み込みラベルフォントで描画され、Qt が使うデスクトップのフォントスタックとは別物です。このフォントはグリフを持たない文字に対して**何も描画しません** — 代替の四角い枠さえ描きません — そのため Qt のメニューでは正しく見える記号が、3D ラベルの中では幅だけを占めて消えることがあります。2026-07-30 まで 2 か所が実際にそうなっていました: `_CLIP_MARK_SUFFIX`（現在は `ui/panels/shape_mesh.py`）の `✂`/`⚠` と、**Dimensions** の範囲表示（`block_mesh_renderer.py`）で各軸の 2 つの数値を区切っていた `→` で、後者は画面上では `X  0   3  (3 m)` になっていました。角括弧も同様に不可で、丸括弧として描画されます。`shape_mesh.py` と `block_mesh_renderer.py` 内のすべての文字列は ASCII に限定してください。`tests/ui/test_shape_mesh.py` と `tests/ui/test_block_mesh_renderer_colors.py` がそれぞれ自分のモジュールの AST を走査して（docstring を除き）まさにこれを検査します。範囲表示はインラインの f-string だったため、定数ごとの検査では見逃されていたからです。ただしこのテストが捕捉できるのは「描画できない文字」であって「見た目が不適切な文字」ではないため、新しく追加したシーン表示は画面で確認してください — グリフの欠落は `assert` では検出できません。なお `block_mesh_panel.py` の `▾`・`·`・`📍`・`…` は対象外です。これらは Qt のウィジェットテキストです。

### ツールバーとメニューの構造

トップのアクションバーは、中央ウィジェット内のレイアウトではなく `addToolBar` で追加した本物の `QToolBar` です。そのため `QToolButton` はホバーされるまでフラットに描かれ、それぞれが枠付きの矩形として描かれることがありません（以前のフラットボタンの列は、**Tree** / **Boundary** / **BlockMesh** の上に 2 本目のタブバーがあるように見えていました）。Editor タブの検索行も同じ扱いの本物のツールバーです。`createPopupMenu()` は `None` を返すようオーバーライドしています。Qt 組み込みのツールバーの右クリックメニューは「`action_toolbar` を隠す」しか出さず、戻す手段がないためです。

`MainWindow._build_shared_actions()` が、ツールバーと **Case** メニューの両方が追加する `QAction`（**Open Case…**・**Save File**・**Save Case**・**Reload Case**）を作ります。コマンドごとにオブジェクトは 1 つなので、ラベル・ツールチップ・ショートカット・有効状態がずれることはありません。ツールバーが同じコマンドをメニューは **Save Case** と呼ぶのに **Save All Files** と表示していた問題の修正です。

メニューの置き場所は、アクションが何に作用するかで決めています。**Manage Extra Files & Directories…** と **Reset File List** は **Case** メニューに、**Reset Window Size** はペイン切り替えと並べて **View** にあります。いずれも開いている 1 つのケースか 1 つのウィンドウに作用し、アプリケーション全体の設定ではないためです。**Settings** にはアプリケーション全体の設定を残しています。**Tools** メニューでは区切り線で、メッシュ／フィールド用ユーティリティ、並列実行系（**Run decomposePar…** から **Delete processor\* Directories…**）、そして **Run Allrun Script**（ユーティリティ単位の操作ではなくワークフロー全体）と **Open Mesh in ParaView…**（実行ではなくビューア）を分けています。情報を表示するだけの Help メニューの項目には省略記号を付けていません。

### キーワードスキャナ

`app_config/keyword_generator.py` は、シンタックスハイライタが色付けするリスト `app_config/foam_keywords.json` を再生成します（gitignore 対象。追跡されている基準ファイル `foam_keywords.default.json` より優先されます）。`generate(project_dir=…)` はインストールのルートを引数から、省略時は `foam_env.foam_env_dirs` 経由で source 済みの環境から取ります。読み取るのは、インストールの `etc/caseDicts/` テンプレート、`src/` ヘッダの `TypeName(...)`/`ClassName(...)` マクロ・`addNamedTo*` の登録・実行時選択テーブルの名前、そして `src/` と `applications/` のソースにある辞書読み取り呼び出し（`lookup("…")`・`get<…>("…")`・`readEntry("…")` など）です。最後のものが、`application` や `writePrecision` のような自由形式のキーを拾います。JSON には出所（`source`・`version`・`generated`・`note`）が記録され、`json_io.atomic_write_text` でアトミックに書かれます。`tools/generate_foam_keywords.py`（`--dir`）と **Settings > Generate OpenFOAM Keywords…**（`ui/dialogs/generate_keywords_dialog.py`。バックグラウンドの `QThread` で進捗と Cancel 付きで実行し、`InstallationSelector` を Find Examples ダイアログと共有）から呼ばれます。

### ウィジェットと補助モジュール

複数のパネルやダイアログが共有する、小さな再利用部品です。

- `ui/pane_minimize.py` — `PaneMinimizer`: `QSplitter` の 1 ペインをワンクリックで畳む/戻す。ハンドルのダブルクリック用イベントフィルタも含む。方式は 2 つ: `sizes`（0 まで畳む — ファイル一覧・Detail ペイン）と `strip`（ウィジェットの最大サイズを固定して細い帯を残す — `Editor/Terminal` 行。この splitter は `setCollapsible(False)` を設定しており、その下では `setSizes` が `QTabWidget` の `minimumSizeHint` までしかクランプされず畳めない。残る帯はタブバーなので、タブと同期ボタンは操作可能なまま）。畳む直前のサイズ列全体を記憶するため、開閉のたびに 1 px ずつ失われることがない。外部から（復元セッションなど）サイズを設定するとこの記憶は破棄される。
- `ui/menu_builder.py` — `MenuBuilder` と `exec_menu`: コンテキストメニューを (`QMenu`, {`QAction`: ハンドラ}) として表し、ブロッキングする `QMenu.exec()` を 1 行に閉じ込めて、どの行がどのシグナルを出すかをそれなしでテストできるようにする — ファイル一覧・Cases タブ・ツリーのメニューで使用。
- `ui/widgets/_checkable_list.py` — `checked_items()` と `set_all_check_states()`: `clean_backups_dialog.py` と `manage_extra_files_dialog.py` が使うチェック可能 `QListWidget` パターン向けの共有の Select All / Deselect All と「N selected」ヘルパー。
- `ui/widgets/flow_layout.py` — `FlowLayout`（`QLayout`）: 折り返し式ツールバーレイアウト — 最小幅は最も幅の広い 1 項目分。`BlockMesh` パネルのツールバーで使用。
- `ui/widgets/installation_selector.py` — `InstallationSelector`（`QWidget`）: `services/example_search.discover_installations()` と永続化 `openfoam_dir` キーに基づくコンボ + Browse… 行。`installations_available/error` シグナル。`find_examples_dialog` と `generate_keywords_dialog` で共用。
- `ui/widgets/_foam_highlighter.py` — `FoamHighlighter`（`QSyntaxHighlighter`）: OpenFOAM トークンの色付け。`app_config/foam_keywords.json`（ユーザー生成）、無ければ `app_config/foam_keywords.default.json`（同梱ベースライン）を 1,000 キーワード単位の `QRegularExpression` チャンクで読み込む。数値ルール（`_NUMBER_RE`）とすべてのキーワードルールは前後判定（lookaround）で守られており、識別子に付いた数字（"wall0"）やドット付き名前のキーワード接頭辞（"`y0.1`" の "y0"）が部分的に色付けされることはない。

## ドキュメント用ツール

`docs/` のスクリーンショットとデモ動画は手作業ではなくスクリプトで作るため、インターフェースが変わったときに再生成できます。どちらも保存した `WindowState` から始まり、開発者の設定には決して触れないよう配慮しています。

### スクリーンショットの撮影

`docs/SCREENSHOTS.md` のギャラリーは、`tools/screenshot_specs.json` のショット一覧をもとに `tools/capture_screenshots.py` が撮影します。手作業で撮った画像は古くなるためです。メインウィンドウのショットは 2026 年 5 月から 2026-07-30 まで撮り直されず、その時点では Tools メニュー・キーフィルタ入力欄・case root と included files のグループが写っていませんでした。1 つの spec に対して `--theme` を変えて 2 回実行すれば、色以外がまったく同一の light/dark ペアが得られます。

```bash
DISPLAY=:1 python3 tools/capture_screenshots.py --all                    # ギャラリー全体、両テーマ
DISPLAY=:1 python3 tools/capture_screenshots.py main-window-tree-editor --theme dark --out /tmp/shots
python3 tools/capture_screenshots.py --list                              # spec が定義しているショット
DISPLAY=:1 python3 tools/capture_screenshots.py <shot> --interactive     # 手で調整し、その状態を JSON で出力
```

**キャプチャが設定を変更することはありません。** `_sandbox_app_config()` は `MainWindow` の構築前に `app_config.json` を使い捨てファイルへコピーし、設定シングルトンをそのコピーへ向けます。空ファイルではなくコピーにしているのは意図的です。キャプチャは実際の設定を*読み*ます — `terminal`/`blockmesh` のフィーチャーフラグはどのパネルが存在するか自体を決めます — ため、空から始めると撮影される内容が変わってしまいます。ウィンドウを閉じないこと（下記）で `window_size` を書く唯一の経路である `closeEvent` は既に塞がれていますが、サンドボックスはそれを経由しない保存経路もカバーします。ケースの複製、ケースライブラリの編集、テーマ・言語・UI スケール・シンタックスハイライトの変更はいずれも単独で `cfg.save()` を呼び、`--interactive` はそのどれにも手が届く状態でウィンドウを開いたままにします。`tools/demo_driver.py` の `seed_app_config` は収録に対して同じことをしています。

**実際の X ディスプレイに加えて、ImageMagick の `import` コマンドも必須です**（`apt install imagemagick` / `brew install imagemagick` — システムパッケージであり、`requirements-dev.txt` では固定できません）。オフスクリーン Qt では VTK が abort するため、ヘッドレスモードはありません。`--out` のデフォルトは `docs/images/` なので、最初の実行は別のディレクトリに向けてください。

**撮影は Qt ではなく ImageMagick 経由で行います。** `QWidget.grab()` は BlockMesh パネルのネイティブ子ウィンドウを黒く返す（前節の GPU の注意と同じ原因）ため、`import -frame -window <winId()>` でウィンドウを撮影します。`-frame` は既存のギャラリー画像と同じくタイトルバーと枠を含みます。GNOME では Mutter の見えない影・リサイズ用の余白（左右 14 px、上 12 px）も含まれ、`import` にはアルファがないため、その余白は真っ黒になります。`strip_shadow_margin` がこれを切り落とします。1 ピクセルの黒い枠を足してから塗りつぶしで透明にし、trim するので、ウィンドウ上端の角丸の外側も透明になります。そのため 1200×800 のウィンドウは 1200×837、つまりタイトルバーを含むフレームそのものになります。`capture_dialog.py` も同じ `capture_window` を通るため、ダイアログにも同じ処理がかかります。ウィンドウ ID は `QWidget.winId()` から得るので、ウィンドウマネージャへの問い合わせやタイトル一致は不要です。ただし `import` は*画面*を読むため、ウィンドウは (0, 0) に移動して前面に出します。重なっているウィンドウがあればそれが写ります。

**`app_config.json` には何も書き戻しません。** テーマは保存済み設定ではなく `--theme` から来ます（通常起動でも `main.py` の `--theme` が同じ働きをします）。言語は英語に固定し、ウィンドウは決して閉じません。ウィンドウサイズを保存するのは `MainWindow.closeEvent` なので、これを呼ばないことが撮影でユーザー設定を変えないための要点です。

**ショット × テーマごとに 1 プロセス。** スクリプトは自分自身を再実行（`--_worker`）するため、前のショットの状態を引き継ぐことがありません。各ワーカーは `os._exit` で終了します。VTK は `shutdown()` を正しく呼んでもインタプリタ終了時に abort することがあり、成功した撮影が失敗として報告されてしまうためです。

#### spec が固定するもの・固定しないもの

ショットの `state` は `WindowState`（`ui/window_state.py`）です。フィールド一覧は同モジュールの docstring を参照してください。 spec の読み込みと適用は **strict** 経路を通ります。この方針は維持してください: 未知のフィールド、存在しないタブラベル、spec の知らないうちに改名されたツリー行は spec 側の不具合であり、間違ったウィンドウを黙って撮影するくらいなら失敗したほうがましです。隣にある lenient な経路はセッションの復元のものであり、誤って使ってしまいやすい点に注意してください。詳しくは[セッションの復元](#セッションの復元)を参照してください。spec の `defaults` はすべてのショットの下敷きになります。`case_dir` にはリポジトリルートを表す `{repo}` と、撮影マシンの OpenFOAM 実行ディレクトリを表す `{cases}`（`--cases-dir` または `$FODE_CASES_DIR`）を使えます。ギャラリーが使うチュートリアルケースはリポジトリ外にあるためです。

固定するのは「選択」だけです。選択行の祖先を超えるツリー展開、スクロール位置、エディタのカーソルと折りたたみ状態、詳細パネルの内容は、開いているファイルと選択行から導かれます。そのため spec は選択のみを固定し、残りは追従させます（それで足りるショットを選んでいます）。`tree_expand` だけが例外で、選択せずに開いておきたい行のためにあります。

spec で間違えやすい点が 2 つあります。

- **`preload_files`** — 3-D ビューアは読み込んだ辞書のジオメトリを蓄積するため、`snappyHexMeshDict` のオーバーレイがブロックメッシュの中に描かれるのは `blockMeshDict` も開いた場合だけです。3-D のショットはすべてこれをプリロードします。
- **`block_mesh_visible`** — ターミナルを xterm から切り替えると **View > BlockMesh 3-D Panel** のメニュー項目は有効化されますがチェックは付かないため、タブは自動では戻りません。3-D パネルが必要なショットは明示的に指定します。

#### 比較モード

ショットは `state` と並べて `compare_with` キーを持つことができ、比較モードの参照ケースを指定します。これは意図的に `WindowState` のフィールドにしていません。あのデータクラスは `ui/session_restore.py` と共有されているため、そこにフィールドを足すと保存済みセッションが復元する内容が変わってしまい、それはスクリーンショットの都合ではなく製品としての判断になるからです。加えて、比較モードは `WindowState` が保持する「選択」ではなく「結果」の側です — 比較を開始すると side-by-side が強制的にオンになります。そこでツールは `MainWindow._start_comparison_with` を呼びます。**Case > Compare with Case…** と Find Examples ダイアログが使うのと同じ入口なので、ショットには実際の動作がそのまま写ります。

`apply_window_state` の内部ではなく後で呼ぶことから、2 つの帰結があります。ファイルごとの差分数はゼロタイマーで事前計算されるため、ファイル一覧のマーカーが現れるまでにイベントループを 1 回まわす必要があります。また比較を開始すると参照ペインの非表示が解除され、Qt がスプリッタの領域を配分し直すため、固定したいサイズは後からもう一度、スプリッタだけを適用し直します。

**比較ショットは 2 つのケースをどちらも `$HOME` の外に置く必要があり**、そのため `{repo}` ではなく絶対パスを書いています。差分バーが参照ケースのフルパスを画像に出力するのに対し、このリポジトリはホームディレクトリ配下にあるためです。ルールも理由も `capture_dialog.py` のログ要約用ケースと同じです:

```bash
mkdir -p /tmp/OpenFOAM/run && cp -r tutorials/cavity/cavity tutorials/cavity/cavityGrade /tmp/OpenFOAM/run/
```

サイズは `QSplitter.saveState()` / `QWidget.saveGeometry()` の blob（JSON では base64）として持ち運びます。ピクセル値の一覧と違い、これは正確に往復し Qt のバージョンをまたいでも有効です。ただし blob は手で書けないため、`splitter_sizes`（`setSizes` に渡す素のピクセル幅）が記述用の形式です。これは選んだときの `window_size` と同じ精度しか持たないため、両者は必ずセットで固定します。

カメラは `plotter.camera_position`（`(position, focal point, view up)`）で、3 つの 3-tuple として往復します。`BlockMeshRenderer.render` の最後が `reset_camera()` であるため、最後の描画の*あとに*適用する必要があります。`apply_block_mesh_view` が単独で呼べるのはこのためで、ツールは settle 待ち後にもう一度呼びます（ターミナルモード切り替え後に遅延実行される VTK の再初期化がその待ち時間の中で走ります）。

#### ダイアログ

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

Plot Results のショット（`plot-results`、`data-file-viewer`）と動画 16 は、プローブとサンプリングラインを加えた pitzDaily を k-epsilon と k-omega SST で実行した 2 つの結果を読みます。`tools/stage_plot_cases.sh` が `/tmp/OpenFOAM/run/plot` に 10 秒ほどで作ります（`--plot-cases` で別の場所を指せます）。データファイルのウィンドウはファイルのフルパスを表示するため、これも `$HOME` の下には置きません。

```bash
tools/stage_plot_cases.sh            # [OPENFOAM_DIR] [DEST]。既定は v2606、/tmp/OpenFOAM/run/plot
```

同じルールは今後追加するショットにも適用されます。コミット前に画像へ `/home/<name>` が写っていないか確認してください。`find_foam_example.png` はこのルールより前の画像ですが、たまたま条件を満たしています。ユーザー名が `user` のマシンで撮影されており、写っているパスもインストール先の `/usr/lib/openfoam/openfoam2606/...` だけであるためです。

各ショットは `build` と対になる `requires` を持ちます。`requires` は「このマシンにショットが読むものが揃っているか」に答え、足りないものを名指しして例外を送出します。これを `build` から分離しているため、`QApplication` なしにその判定ができ、結果としてテストで検証できます。2 つのショットは撮影マシン側が用意するもの（実行済みケース、OpenFOAM インストール）を読みますが、`run-tool` は同梱の `tutorials/damBreak` を読みます。このショットが見せたい「`0/` を復元する」前置きは、`0.orig/` を持つケースでしか現れないためです。つまりこのショットの入力はチェックアウトに同梱されています。

`run-tool` ショットは、`ui/mixins/_tools_ops.py` が渡すのと同じ警告文と前置き文字列を `RunToolDialog` に渡します。import ではなくコピーしているのは、それらがミックスイン内のインラインなリテラルであり、参照するには `MainWindow` を立ち上げる必要があるためです。テストスイートがそれらの文字列が当該ファイルに今も存在することを検証するので、アプリが決して表示しないダイアログをギャラリーが見せてしまうことはありません。

構築時点では内容が揃わないダイアログには `prepare` フックがあります。`show()` の後に呼ばれ、イベントループを回すための `pump(ms)` が渡されます。これが必要になったのが `find-examples` です: 検索が `QThread` で走るため、ショットはクエリを入力し、検索を開始し、結果ツリーが埋まるのを待ち（上限付き — キャプチャがハングしてはいけません）、続いて結果を 1 つ選択してプレビューを表示させます。このフックは `FindExamplesDialog` のプライベートなウィジェットを直接触ります。製品側のダイアログにキャプチャ専用のアクセサを足さないための引き換えです。参照している名前は `tests/tools/test_capture_dialog.py` で固定しているため、リネームは X ディスプレイを要するキャプチャ実行の途中ではなく、テストスイートで失敗します。

`capture_screenshots.py` と同様、このツールもショットごとに自身を再実行します（`--_worker`）。あちらの理由は「どのショットも直前のショットの状態を引き継がないこと」ですが、こちらにはより強い理由もあります。`QApplication` はシングルトンであり、同一プロセス内で 2 つ目のショットが QApplication を持つことはできません。

#### 対象外

`tools-menu.png` も、spec の `open_menu` フィールドを通じた `capture_screenshots.py` のショットです。開いたメニューはポップアップ、つまりメインウィンドウのフレームの外にある独立した override-redirect ウィンドウなので、`import -frame -window` では写りません。そこでメニューのショットは、クリックと同じ方法でメニューを開き（`QMenuBar.setActiveAction`、入力操作は使わない）、*画面全体* を取得して、Qt の `frameGeometry()`（ウィンドウマネージャのフレーム範囲）が示すウィンドウのフレームで切り抜きます。`xwininfo -frame` ではないのは、GNOME ではクライアント領域しか報告せず、タイトルバーが欠けたためです。これは、影の余白を切り落とした後の他のショットと同じ輪郭です。v1.19.0 までは手作業で撮影していました。この方法は以前に一度使われましたが、そのスクリプトは保存されていなかったため、今回ツールに組み込みました。

spec は `light` で撮影し、`system` は使いません。system テーマのウィンドウは撮影マシンのデスクトップパレットを継承するため、他の環境で再現できない唯一の要素になります。ギャラリーの light 画像は 2026-07-30 まで `system` モードで手作業撮影されていました。現在の画像で選択行の塗りがデスクトップのアクセントカラーではなく FoDE 自身の青になり、ウィジェットがデスクトップのスタイルではなく Fusion になっているのはこのためです。

**このセクションに関わるモジュール。**

- `ui/window_state.py` — `WindowState` / `BlockMeshViewState` データクラスと `capture_window_state()` / `apply_window_state()`。レイアウトのうち「結果」ではなく「選択」である部分（ジオメトリ、スプリッタ、タブ、開いているファイル、ツリー選択、3-D のトグルとカメラ、および `minimized_panes` — どのペインが最小化されているかと各ペインの復帰サイズ。スプリッタの blob では表せない半分）を扱う。JSON 化できるため、状態をプロセス間で受け渡せる。strict / lenient の使い分け（`from_dict` と `apply_window_state` の `strict` フラグ、`load_saved_state`）は、2 つの利用側の要求が逆であることに由来する: スクリーンショット spec は失敗を大きく報せるべきで、復元されるセッションは静かに劣化すべき。
- `ui/session_restore.py` — `window_state.py` の上に載る「実行間の配線」。`save_session()` は `MainWindow.closeEvent` から（パネル破棄前、自動保存はしない）、`restore_session()` は `main.py` の `show()` 後から呼ばれる。レイアウトは `AppConfigManager.session_key()` ごとに保存し、ケース読み込み時の描画が `reset_camera()` で終わるため 3-D カメラはタイマーで再適用、スキップした部分はステータスバーに表示。

### デモ動画の収録

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

**収録のたびにケースは新しくコピーされます。** シーンは `case_source` と `workdir` を指定し、ウィンドウを開く前に無条件でコピーされます。前回の収録の残骸（すでに生成されたメッシュ、すでに設定された `0/`）から始まった収録は、台本と違うものを記録します。また `blockMesh` を実行するシーンは、そうしなければリポジトリの `tutorials/` を汚します。`terminal_prelude` は収録開始前のステージング時に OpenFOAM 環境を Terminal タブに読み込ませます。シェルの設定作業を見せることはデモではないからです。`clean` はその対になるもので、ステージングがコピーするものではなく*ステップ*が作るものを対象にします。ケースを複製するシーンは `case_source` にも `copy_also` にも書かれていないディレクトリを作るので、前回の収録のものが残っていると次のステップが「上書きしますか？」のダイアログになってしまいます。`prepare_case` はリポジトリ内のパスの削除を拒否します。`case_prepare` は、同梱のケースにはない開始状態のためのものです。コピーの後、ウィンドウを開く前に、コピーしたケースで `bash` によりシェルコマンドを実行し、失敗したところで収録を止めます。動画 13 はこれで同梱の `Allrun` を削除し、4 つのツールをそれぞれのログに書き出して実行します。`terminal_prelude` と違い、画面に何か出る前に終わるので、どのステップもその所要時間に左右されません。

**`app_config.json` も収録ごとに新しくなります。** `seed_app_config` が workdir にスクラッチの設定ファイルを書き、`MainWindow` を組み立てる前にシングルトンをそちらへ向けます。理由は 2 つあり、2 つめがすべてのシーンで実行する理由です。収録が収録者の設定を*書いて*はいけません。「複製したケースを開きますか？」に Yes と答えると、その途中で新しい既定ケースディレクトリが保存されます。ウィンドウを閉じないだけでは防げません。そして収録が設定を*読んで*もいけません。機能フラグ、既定のケースディレクトリ、ケースライブラリはすべてこのファイル由来なので、そうしなければある機械で撮った動画が別の機械では違う場所を開くことになります。

`case_library` はその上に乗ります。指定したディレクトリが、ケースライブラリの唯一の項目になります。同時に `$FOAM_TUTORIALS` にも代入します。`get_case_library_dirs` はこの変数を登録済みリストの先頭に足すので、項目が 2 つあるとファイル選択の前に「どちらのライブラリを見るか」を訊くダイアログが出てしまい、その中身は収録シェル次第になるからです。同じディレクトリを指させれば 2 つは 1 つに畳まれます。変数を消すのではなくこの向きにしているのは、`paraFoam` が OpenFOAM 環境の残りを必要とするためです。

**ネストされたディスプレイには 2 つの代償があり、いずれもドライバ側で処理しています。** 閉じたメニューはピクセルを画面に残し、自力で再描画しないものの上に居座ります。3D ビューは VTK が描き直すので影響を受けず、結果としてエディタの上にメニュー型の穴が残り、そこに何かが描かれるまで消えません。`repaint()` でも `xrefresh` でも動かせませんが、1 ピクセルのリサイズなら消えます。内容だけでなく全ウィジェットのジオメトリを無効化するからです。ポップアップを閉じたステップの後にこれを実行しています。もう 1 つ、収録では Qt 自身のファイルダイアログを強制します（`AA_DontUseNativeDialogs`）。デスクトップのポータル製ファイル選択ダイアログは別プロセスなのでウィジェットに一切手が届かず、キーボードショートカットもデスクトップごとに異なります。さらにホームディレクトリを開いた状態で上部にユーザのアカウント名を表示するため、公開する動画には映せません。

**ネイティブダイアログを切ったのは、その半分にすぎませんでした。** Qt 自身のファイル選択ダイアログもサイドバーに **Home** のショートカットを出すため、収録中にダイアログを開くとやはり収録ユーザのアカウント名がフレームに写り込んでいました — 同じ規則が別のウィジェットで破られていたわけです。名前がどこまで見えるかは収録マシンに保存された `sidebarWidth` に依存するので、あるテイクでは 5 文字に切れ、別の 2 本では全体が写っていました。深刻さがローカルの設定値で決まる不具合です。`_isolate_qt_settings` が `XDG_CONFIG_HOME` を `<workdir>/config` に向け、続いて `_seed_file_dialog_sidebar` が使い捨ての `QFileDialog` を 1 つ作り、サイドバーをそのテイクのスクラッチルートに設定して破棄します。Qt はこのウィジェット状態を全部まとめて復元し、手書きの conf は無視するため、実際のダイアログから書かせる必要があります。以降そのプロセスで開かれる*すべての*ダイアログがこれを引き継ぎ、アプリが実際に使っている静的な `getExistingDirectory`/`getOpenFileName` 呼び出しも含まれます。これが、12 か所の呼び出し側をそれぞれ変更するのではなく収録側だけの修正で済む理由です。実ユーザからネイティブの選択ダイアログを奪うべき呼び出し側は 1 つもありません。

このリダイレクトは、狙っていなかった別の問題も直します。従来テイクは収録ユーザ本人の `~/.config/QtProject.conf` を読み*書き*しており、自身の `history`/`lastVisited` を残していました。`seed_app_config` は `app_config.json` をサンドボックス化しますが、Qt の設定はまったく別の場所にあるため、「テイクは収録ユーザの設定を書き換えてはならない」は半分しか実現できていませんでした。

**ParaView には専用のプロファイルを与えます。リダイレクトを維持しているのはそのためです。** ParaView は子プロセスとして起動されるため `XDG_CONFIG_HOME` を継承し、収録ユーザ本人ではなくテイクのスクラッチディレクトリから設定を読みます。本人のプロファイルに任せると 2 つの問題が起きます。1 つは、そのプロファイルが保存したジオメトリでウィンドウが開くこと（この環境では 1390×749 で、ネストされたディスプレイより広いため、毎テイクでカラーレジェンドが右端で切れていました）。もう 1 つは、`Apply` ボタンの位置が Pipeline Browser の高さに従って動き、その高さもそこに保存されていることです。実際このマシンだけで、2 回のテイクの間に `Apply` は 80px 移動しました。`point` ステップは外れようがないので、テイクは最後まで完走し、ナレーションが「キャビティがそこにあります」と言うそばで空のレンダービューを記録します。代わりに `_seed_paraview_profile` が `tools/demo_paraview_profile/` をコピーします。再生成は `tools/make_paraview_demo_profile.sh` で行い、ParaView のバージョンが変わったときに必要です — 設定ファイル名にバージョンが入っており、別のビルドはそれを無視するからです。プロファイルが無くても致命的ではありません: ParaView の Getting Started スプラッシュが記録されるだけで、レビューで気づくべき事柄です。

**`$HOME` は引き続きそのままにします。** リダイレクトすると `services/case_fs_ops.py` の保護パスから `Path.home()` が抜け落ちます。ケースブラウザがまさに通るコードパスです。

**ジオメトリはプロファイルに保存させず、収録時に `fit_window` ステップで強制します。** 素の X サーバ上では ParaView は終了時にジオメトリを書き出しません（プロファイル作成中に確認済み）。再生成で失われる値は、無いよりたちが悪いのです。このステップはウィンドウの出現を待ち、リサイズし、*サイズが実際に適用されたかを確認して再試行します*。ParaView は自前のジオメトリを適用する前にウィンドウを生成するため、その隙間に入ったリサイズは黙って取り消されるからです。

**動画の主題の手前にあるダイアログ。**テイクの入れ子のディスプレイにはウィンドウマネージャがないため、ダイアログはメインウィンドウの中央に開き、脇へ動かす手段がありません。そのため Add Function Object の即時プレビューが描かれる 3D ビューが隠れていました。`place` ステップは開いているダイアログのジオメトリを Qt から設定し（`"rect": [x, y, w, h]`）、その後、表示中のすべてのウィジェットに再描画を求めます。ウィンドウ単位の再描画だけでは、エディタのビューポートにダイアログの古いボタンが残像として残ったためです。`item` ターゲットは、開いているダイアログのツリーやリストの行をテキストで選びます（完全一致、なければ一意な部分一致。カテゴリと中の項目が同じ名前の場合 — Add Function Object の `probes`/`probes` — は子のない行が優先）。これらの行はインストールから読み込んだデータだからです。また `type` は改行を Return として送ります。`xdotool type` は改行を落とし、プローブの点のリストが 1 行につながってしまいました。FoDE の入力欄はそれを拒否したため、テイクはダイアログが開いたまま終わっていました。スペックの試験で UI のリテラルと照合するのは、コロンで終わる `field` ラベルだけです。Add Function Object は行のラベルにテンプレートのキーを使うためです。

**ParaView の座標は収録済みのフレームから測ってください。手で起動した ParaView から測ってはいけません。** この環境で手動起動した ParaView はツールバー項目が 1 つ多く、32px 右にずれており、それだけで Last Frame のクリックが Loop に変わりました。しかもテイクは完走し、見た目も一応それらしく、ただ時刻が進まないだけです。このシーンで間違っていた 3 つの座標のうち 2 つは、スタンドアロンのプローブを信用したことが原因でした。

**収録はハングしません。** ステップが送出した例外はすべて収録を終了させます。メッセージとともに、そのとき画面に何が表示されていたかのスクリーンショットも残ります。メニュー項目の改名でターゲットを見失った状態は、外から見るとこう見えます。それ以外の理由で止まった収録はウォッチドッグが終了させます。止まった収録はディスプレイを占有したまま何も報告しないからです。

細かい点が 2 つ、いずれも痛い目を見て分かったものです。`xdotool mousemove --sync` は、ポインタが**現在いる位置**への移動では決して発生しないモーションイベントを待ち、数秒間ブロックします。イージングによって、ゆっくり動く区間の複数ティックが同じピクセルに丸められるため、移動しない移動はスキップしなければなりません。もう 1 つ、ステップのマウスボタンは `button` ではなく `with` です。`button` はすでにターゲット（クリックするプッシュボタンの名前）だからです。

スクリーンショットツールがユーザの設定を汚さないために行っていることは、すべてそのまま当てはまります。テーマは保存された設定ではなく spec から取り、言語は英語に固定し、ウィンドウを閉じないので `closeEvent` が `app_config.json` を書くこともなく、VTK の後始末がクリーンな `shutdown()` の後でも abort しうるためプロセスは `os._exit` で終わります。

**入れ子のディスプレイでは、非モーダルのウィンドウは決してアクティブになりません。** アクティブにするウィンドウマネージャがないためです。そのため、モーダルダイアログかアクティブなウィンドウを探す `button`/`field`/`item` は、Plot Results の後ろにあるメインウィンドウを探してしまいます。代わりにステップは `"in"` でウィンドウを指定します。`widget` と同じく `MainWindow` からの属性パスで、数字はリストの添字です（`_plot_results_dialog._viewers.0` は最初のデータファイルのウィンドウ）。動画 16 で、さらに 3 つの指定方法を加えました。`item` に `"check": true` を付けると、行の文字ではなく（文字のクリックは選択するだけです）チェックボックスをクリックします。`item` をリスト（`["pitzDaily-kEpsilon", "probes/U"]`）で与えると、祖先をたどってツリーの行を指定でき、どのケースの下にも同じ文字の行がある場合に使います。`"legend"`（プロットウィンドウのパス）は matplotlib の凡例の中心で、matplotlib の左下基準のデバイスピクセルから変換したもので、`drag` でつかむためのものです。アクティブにならないことは Qt のツールチップも隠していました。Qt はアクティブなウィンドウでしかツールチップを表示しないためです。`PlotResultsDialog` は `WA_AlwaysShowToolTips` を設定しています。このウィンドウはふだんアクティブなメインウィンドウの横に置かれるので、ユーザーにとってもこれが正しい動作です。

**収録は、撮影者のデスクトップではなく専用の Xvfb で行えます。** `Xvfb :91 -screen 0 1280x800x24 &` を起動し、`DISPLAY=:91 … --on-this-display` とします。そのディスプレイには他に何もないので、実際の入力が誤って入り込む先がなく、デスクトップには何も表示されません。動画 16 はこの方法で収録しました。

**1 つだけ、FoDE 以外のアプリケーションを操作するシーンがあります。** `cavity-full-workflow` は ParaView で終わります。ParaView は意味的には何も解決できないので、そのクリックは `point` ステップ、つまりリハーサルのスクリーンショットから読み取ったピクセル座標です。収録が既知のサイズでウィンドウマネージャのないディスプレイ上で行われ、ParaView が毎回原点に 1280×800 で開くからこそ成立しています。

**ただし、すべてがディスプレイ側で固定されるわけではありません。そこが落とし穴です。** `Apply` ボタンの *y* 座標は ParaView の Pipeline Browser の高さに従い、その高さは収録ユーザ自身の ParaView プロファイルに保存されています。したがってウィンドウサイズとは無関係に、プロファイルが変わるたびにずれます。症状は無言です: `point` ステップは外れようがなく、その座標にあるものをただクリックするので、テイクは最後まで完走し、ナレーションが「キャビティがそこにあります」と言い続けたまま空のレンダービューが記録されます。撮り直しを信用する前にリハーサルのフレームから Apply を測り直し、終了コードではなく *ParaView のフレームそのもの* を確認してください。

関連して、このネストされたディスプレイ上の ParaView は、最後のフレームを取得した後の終了処理中に `QOpenGLContext::makeCurrent` で `SIGSEGV` を出して落ちることがあります。端末にはいかにも不穏に出ますが収録自体には無害で、撮り直すのではなくそういうものだと認識しておくべき挙動です。このシーンはさらに、OpenFOAM を source したシェル（`PATH` 上に `paraFoam` が無いと、`_on_open_paraview_clicked` は何も読み込んでいない素の `paraview` にフォールバックします）と `LIBGL_ALWAYS_SOFTWARE=1` を必要とします。どちらも [docs/DEMO_SCRIPTS_ja.md](docs/DEMO_SCRIPTS_ja.md) の「収録」節で扱っています。

## テストカバレッジ一覧

ディレクトリごとにテストファイル 1 行の一覧です。テストファイルの追加・削除時はここも更新してください — 以前サイレントにドリフトしたのはまさにこの部分です。各項目は 1〜2 文にとどめます。理由づけはテストの docstring にあるため、ここでは繰り返しません。

**`tests/`（トップレベル）**
- `test_config_isolation.py` — autouse の `temp_config` フィクスチャが、どのテストにもリポジトリの `app_config.json` を触らせないこと。設定シングルトンと `$FODE_CONFIG` が使い捨てファイルを指し、保存もそこに書かれます。
- `test_docs.py` — マニュアルの機械的な整合性: すべての節が目次にあること、すべての `#アンカー` リンクが解決すること、`_ja` ミラーが同じ見出しを保つこと、すべてのテストファイルがこの注記に載っていること、README の動画の本数が `docs/DEMO_SCRIPTS.md` と一致すること、空行が続かないこと。
- `test_i18n.py` — `i18n/ja.py` の `TRANSLATIONS` に重複キーがないこと、`ui/` 配下のすべての `tr()` 呼び出しが `ja.py` に項目を持つか実測済みの縮小専用の未翻訳許可リストにあること、そして許可リストに古い項目がないこと。
- `test_lint.py` — ruff と mypy をテストとして実行し、テスト衛生の 2 つのガードも含みます。[Lint と型チェック](#lint-と型チェック)を参照。
- `test_main_ui_scale.py` — `main._apply_ui_scale`: UI Scale 設定が `QApplication` の生成前に `QT_SCALE_FACTOR` として書かれること。設定ファイルの値は環境変数に譲り、`--ui-scale` はそれを上書きし、100% は何も設定しません。
- `test_main_windows_terminal.py` — `main._default_windows_to_no_terminal`: Windows で素の起動ではターミナルを入れないこと（以前はケースを開くたびに cmd.exe へ Unix 流の引用で `cd` を送っていた）、明示した `--variant` による機能設定は尊重されること、ほかのプラットフォームは変わらないこと。
- `test_version.py` — `_version.get_version()` の整形: リリースのコミット上、タグより先、未コミット変更あり、ハッシュのみ、git がない場合のフォールバック、そして別バージョンのタグ（タグを取得しないクローンの古いタグや、同じコミット上の別のタグ）ではハッシュだけを付けて `__version__` を表示すること。

**`tests/foam/`**
- `test_block_mesh_extractor.py` — `extract_block_mesh_data` の出力: 境界面の抽出（パッチの間に置かれた `#include` によって `outlet` が名前と面を失っていたリグレッションを含む）、`#include` を含む `blocks` リストおよび先読みが `raw_list` に落としたリストからの hex 抽出、`default_faces`（境界が全面を占有 → 空、未割り当ての外部面の収集、任意の頂点回転での占有判定、ブロック間で共有される内部面の除外）など。
- `test_boundary_patch.py` — `find_rename_targets()`: `blockMeshDict` 内の `boundary_entry` ノードおよび `boundaryField` ブロック内のパッチ `dictionary` ノードの検出、無関係な辞書への誤検出なし、空入力のエッジケース。
- `test_diff.py` — `diff_trees`/`diff_trees_reverse`: 同一ツリー、値の変更、片方のみに存在するキー、ネストした辞書、匿名ノードのスキップ、`field_value_block` エントリ、両関数の対称性。
- `test_gzip_files.py` — gzip での `read_foam_file`/`write_foam_file`: 名前ではなく内容で展開すること、CRLF が通常のファイルと同じに読めること、壊れたアーカイブが `OSError` を出すこと、名前または `compress=` で圧縮して書くこと、大きな圧縮辞書をログと取り違えないこと。
- `test_lexer.py` — `foam.lexer.OpenFoamLexer` の `//` 挙動: 引用符付き文字列内の二重スラッシュはコメントにならないこと、空白の後の二重スラッシュは直前の word を飲み込まずに `LINE_COMMENT` を開始すること、単独行の `//` は先頭トークンからコメントとして扱われること。加えて `${…}` 形式の波括弧付きマクロ参照: 参照全体が 1 つの WORD になること（スコープパス付き、および入れ子の波括弧が釣り合うこと）、その後続トークンが影響を受けないことなど。
- `test_parser_block_mesh_dict.py` — `boundary_block`/`boundary_entry` の構造的パース（パッチ数・名前・型・面）、ライタの round-trip。パッチ名と波括弧の間、および `vertices` 内のインライン `//`・`/* */` コメントがノード型を壊さないこと。
- `test_parser_control_dict.py` — `controlDict` のパース: FoamFile ヘッダー、int/scalar/word の値、`#directives`、`functions` サブ辞書、パース失敗時に空の root へフォールバックすること。
- `test_parser_fv_schemes.py` — `fvSchemes` のパース: compound 値、`ddtSchemes`/`divSchemes`/`interpolationSchemes`/`snGradSchemes` ブロック、すべてのトップレベルブロックの存在、round-trip 書き込み、辞書を閉じる余分な `;`（`divSchemes { … };`）が解析エラーとして数えられずに独立したノードになること。
- `test_parser_fv_solution.py` — `fvSolution` のパース: マクロおよび正規表現パターンのソルバーキー、`PIMPLE` ブロック、ソルバーの `tolerance`/`smoother` エントリ、round-trip 書き込み。
- `test_parser_block_list.py` — `blockMeshDict` の `blocks ( … );` の展開: `hex` のみのリストが匿名・1 行の `block_list`/`block_entry` として解析されること、先読みにより空リスト・単純なマクロ単語リスト・ディレクティブのみのリスト・`hex` 以外の先頭形状（`hex2D`、`prism`）が通常の `raw_list` パスに留まることなど。
- `test_parser_named_dict_list.py` — 省略可能な名前付き辞書リスト構文: `sets`/`surfaces` の名前付き辞書の丸括弧リストが `named_dict_list`/`named_dict_entry` として解析されること（トップレベルとファンクションオブジェクト辞書内の入れ子の両方）、先読みにより単純な単語/文字列リスト（`sets (setA setB);`）や空リストが通常の値パスに留まること、未変更時のラウンドトリップがバイト単位で一致すること、エントリ変更時に兄弟エントリの名前が保持されること。
- `test_parser_region_properties.py` — 無関係な 2 つの辞書が同じ `regions` というキーを使っている問題: `setFieldsDict` の名前付き辞書はこれまでどおり `region_block`/`region_entry` として解析され、`constant/regionProperties` の 名前と単語リストの組は、以前のような名前のない `unknown_raw_entry` ノード 2 つ ではなく `raw_list` に落ちること。いずれも解析エラーがなく、バイト単位の ラウンドトリップが一致することを確認します。
- `test_parser_set_fields_dict.py` — `setFieldsDict` のパース: `defaultFieldValues`/`regions` のフィールド値エントリ（ベクトル値を含む）、`box_pair` のパース、編集後の round-trip 書き込み。
- `test_parser_topo_set_dict.py` — `action_list`/`action_entry` の構造的パース: ノード型、エントリ数、名前付き子ノードの値、`box_pair` 座標、ソースなしエントリ、round-trip 書き込み、`_diff_action_list` による位置ベースの差分検出。
- `test_snappy_hex_mesh_extractor.py` — `extract_snappy_hex_mesh_data`: `geometry` の box/sphere（スカラーおよびベクトル/だ円体 radius）/cylinder/cone の抽出、`name` による上書き解決（`geom.stl { name geom; }`）など。
- `test_source_lines.py` — すべてのノード型に対する `source_line` および `source_end_line` の設定。
- `test_topo_set_extractor.py` — `extract_topo_set_data`: box・sphere・cylinder の 3 種類すべてに対するプレーンな型付き値、ベクトルとスカラーでの `$var` 解決、`raw_list` 内の `#eval{...}`、連鎖した変数/eval 解決、解決不能な変数のスキップ、すべての face/point ソースバリアント。
- `test_include_resolver.py` — `parse_include_directive`/`resolve_include`: 5 つのディレクティブ種別、オプション扱い（`#sinclude`/`#includeIfPresent`）の判定、末尾 `;`・コメント・引用符の除去、`#includeFunc mag(U)` のベース名への還元、拡張子とトークン全体の山括弧による C++ ヘッダー除外（`<constant>/…` は意図的に残ること）など。
- `test_sampling_extractor.py` — `extract_sampling_data`: `functions {}` ブロック内の probes、辞書形式 `sets {}` の line/cloud メンバーと、丸括弧リスト形式（`functions {}` ブロック内とファイルルートの sampleDict スタイルの両方）、`plane`/`cuttingPlane`/`patch` サーフェスメンバー、トップレベルの `singleGraph` スタイル `start`/`end`、スタンドアロンの `sample`/`probes` ファイルなど。
- `test_set_fields_extractor.py` — `extract_set_fields_data`: box/sphere/cylinder 領域の抽出（エントリ名がソースタイプ）、`fieldValues` のラベル要約（スカラー値とベクトル値）、ジオメトリを持たないソースの分類（`zoneToCell`）、`$var` の解決、解決不能なジオメトリックソースのケース。
- `test_topo_set_shapes_tutorial.py` — 同梱の `tutorials/topoSetShapes` ケースに対する `extract_topo_set_data`: すべてのジオメトリソースが抽出され、すべての形状がドメイン内に収まっていること。
- `test_sampling_shapes_tutorial.py` — `tutorials/samplingShapes` と `extract_sampling_data` について同じことを行うテスト: `controlDict` の `functions {}` ブロックから読み取る probes と、その隣に置いたサンプリングでない function object が完全に無視されること、メンバーリストの 2 通りの記法（`sets { … }` と `surfaces ( … );`）、始点・終点ではなく点列を持つ cloud、平面の 2 通りの記法など。
- `test_tree_utils.py` — `tree_utils` の各リゾルバの直接契約テスト（エクストラクタのテストは間接的にしか通らない）: `find_child`/`find_child_any` のエイリアス優先順、`expand_evals`、`resolve_scalar`（scalar/int/macro/`${…}`/`#eval`）、`resolve_vector` の要素数・数値ガード、`resolve_point_list`、オプトインフラグ付きの sphere/cylinder/cone リゾルバなど。
- `test_utils.py` — `is_large_non_foam_file`: 小さいファイルはヘッダーの有無にかかわらずフラグが立たないこと、最初の 512 バイト内に `FoamFile` トークンを含む大きいファイルはフラグが立たないこと、含まない大きいファイルはフラグが立つこと、存在しないファイルは `(False, 0)` を返すこと、コメントの後にヘッダーがある場合も正しく検出されること。
- `test_value_parse.py` — `parse_parenthesized_numbers`/`parse_text_for_node_type`/`set_node_value` を Qt なしで直接検証: int の受理・拒否と浮動小数点風文字列での scalar への昇格、scalar の受理・拒否、vector/int_list/scalar_list/box_pair の受理・拒否、raw_list の括弧除去、bool の大文字小文字を区別しない受理・拒否、word/string/macro/compound のそのまま通過など。
- `test_include_expand.py` — `expand_includes`: トップレベルの差し込みと記述順（後の定義が先の定義を隠すこと）、インクルード先の `FoamFile` ヘッダーの除去、元のツリーが変更されないこと、インクルードの無いファイルが*ルートオブジェクトそのもの*を返すこと、辞書の内側のインクルード、再帰的展開と深さ上限、解決できないインクルードがその場に残り報告される一方で `#sinclude` は報告されないこと、自己参照と相互参照の循環が断ち切られること、`#includeFunc` が対象外であることなど。
- `test_var_resolver.py` — `build_var_map`、`substitute_vars`、`eval_foam_expr`: スカラー/整数のシード、マクロチェーン、`#eval` 式、否定マクロ word ノード、解決不能な変数が値を持たないままになること、`skip_keys` による除外など。
- `test_variants.py` — `foam/variants.py`: `variant_base` が区切りと一致する `FoamFile` の `object` を要すること（最長の基本名が優先、兄弟ファイルに include される断片は除外）、ヘッダのメモがファイル自身の stat に従うこと。
- `test_writer_roundtrip.py` — `write_root`/`write_node` 全般: 未変更ノードが `raw_text` で再現されること、変更された word/int/scalar/vector ノードが再生成されること、directive/unknown_raw/macro エントリが保持されること、ネストした辞書、空行の連続がそのまま保持されること、`field_value_block`/`region_block` の round-trip（リージョン内のフィールド値編集を含む）など。
- `_parser_helpers.py` — テストではなく、`test_parser_*.py` の文法テストが共用する `find_child`。65 回呼ばれるため、フィクスチャにするとそのすべてのテストに引数が増えるので、モジュールにしています。

**`tests/model/`**
- `test_bool_nonuniform.py` — bool/nonuniform_list のパースと round-trip、`FoamTreeModel` の bool 編集（大文字小文字を区別しない、拒否シグナル）、`nonuniform_list` の表示・編集不可、不正エントリに対するパーサエラー収集。
- `test_boundary_model.py` — `extract_boundary()` と `BoundaryModel`: 読み込み、フィールド更新、ディレクトリごとの境界セット、`_is_in_dir` の多階層照合、モデルのクリア。
- `test_case_tree_model.py` — `CaseTreeModel`: `canFetchMore`/`fetchMore` による遅延読み込み、ディレクトリのみを対象にした大文字小文字を区別しない順序、ケースへ降りていかない規則とその双方向の抜け道である `set_descend_override`、`CASE_MARKER` の表示プレフィックス・`ENTRY_ROLE`・開いているケースを追跡する `FontRole` の太字・注入されたツールチップとデフォルトツールチップの切り替えなど。
- `test_file_list_model.py` — `FileListModel`: 読み込み、ソート済みグループ、アイテムごとのダーティ状態・差分状態、追加ファイルの扱い、クリア。
- `test_tree_model.py` — `set_diff(reverse=True)`: `"only_here"` を `"only_in_ref"` にリマップし `"changed"` は変更しないこと、淡緑色の `BackgroundRole` を返すこと、`"only in reference case"` をツールチップに含むこと。`FoamNode` は `__hash__ = object.__hash__` を持ち、差分マップのキーとして使用可能です。

**`tests/ui/`**
- `test_app_state.py` — `ui/app_state.py` の `AppState` の既定値: `diff` が `DiffState` であること、スカラーのフィールドが空で始まること、可変フィールドが書き換え可能であること、そして 2 つのインスタンスが `parsed_roots` を共有しないこと — クラス属性にしてしまうと起きる誤りです。
- `test_apply_comparison_value.py` — `_apply_comparison_value`（「Use this value」）: ネストしたエントリの取り込み時に不足している親辞書を作成すること（例: `functions {}` を持たないケースへの `functions/forces1/rhoInf` の適用）、名前のない `#includeFunc` ディレクティブを既存ブロックを上書きせず内容で照合して末尾に追加すること、同一のディレクティブは複製せずスキップすること、名前付きの値の通常の上書きパスなど。
- `test_block_mesh_panel_fonts.py` — パネルの補助ラベル 2 つ（ヒント行と `⚙ Variable-based` バッジ）が 9・11・16 pt でデスクトップのフォントサイズに追従すること。どちらも以前はスタイルシートに `font-size: 11px` を直接書いていたため、デスクトップのフォントをどれだけ大きくしても 11 px のままだった — 下記「フォントサイズと表示スケーリング」を参照。
- `test_block_mesh_panel_load_stl.py` — `STL ▾` メニューの読み込み済みサーフェス: 1 回の `getOpenFileNames` での複数ファイル選択、読み込めないファイルがあっても読める分は読み込まれること（失敗分をまとめた警告 1 回）、ダイアログのキャンセルが何もしないこと。さらにファイル別の行について: ファイルごとに 1 行・パレットから 1 色（最初は `lightgray`）、個別の非表示とアンロードの違い、アンロード後や同一パスの再読み込み後（重複行ではなく既存行の再読み込み）も各行のチェック状態が保たれることなど。
- `test_block_mesh_panel_sampling_select.py` — `sample ▾` の形状別表示メニュー: controlDict の `functions {}` ブロックからのメニュー生成（行には元ファイル名のタグ付き）、個別/マスタートグル、ジオメトリを持たないエントリのグレーアウト表示、複数ファイルの合算（controlDict + system/sample）とファイル単位の再読み込み置換、ベース名が同じ 2 つの辞書が別ディレクトリにあっても分離されること（`_sampling_by_file` はフルパスをキーとし、表示はベース名）など。
- `test_block_mesh_panel_save_image.py` — **Save Image…** アクション: 初期状態は無効（プロッタは最初の `showEvent` で遅延生成されるため、まだ取り込む対象がない）で、`shutdown()` で再び無効化されること。ツールバーのボタンと View メニューの項目が2 つではなく 1 つの `QAction` であること。
- `test_block_mesh_panel_set_fields_select.py` — `setFields ▾` の形状別表示メニュー: 同梱の damBreak チュートリアルの `setFieldsDict` からのメニュー生成（行は `fieldValues` の要約でラベル付け）、個別/マスタートグル、ジオメトリを持たないソースのグレーアウト表示、STL エクスポートへの包含、再読み込み時のクリア。
- `test_block_mesh_panel_snappy_select.py` — `snappyHexMesh ▾` の形状別表示メニュー: メニューの生成、個別/マスタートグル、surface/region/geometry カテゴリカラーの凡例、ジオメトリを持たないソースのグレーアウト表示、`locationInMesh`/`locationsInMesh` キープポイントのトグル。
- `test_block_mesh_panel_start_failure.py` — コンストラクタから `init_plotter` に再入する代役の `QtInteractor`（pyvistaqt 0.13 のウィンドウ作り直し）でもインタラクタは 1 つで入れ子の 2 つ目はできないこと、例外を出す代役ではパネルに理由が出て、Save Image は無効のまま、再試行しないこと。
- `test_block_mesh_panel_topo_select.py` — `topoSet ▾` の形状別表示メニュー: メニューの生成、個別/マスタートグル、Show all/Hide all、アクションカラーの凡例、ジオメトリを持たないソースをまとめた「Non-geometric sources (N)」サブメニュー、点/平面シェイプの STL エクスポートからの除外。
- `test_boundary_view_cell_label.py` — 境界表のセルの文字列: `nonuniform List` は個数で要約し、その他の長い値は `…` で切ること。
- `test_file_list_variants.py` — サフィックス付きの派生ファイルの行が淡色で、名前で指定されたときだけ読まれる旨のツールチップ付きで表示されること。
- `test_gzip_files_ui.py` — アプリ内の圧縮された場: テキストとして開いてパースでき、Ctrl+S・Save Case・Create Backup が gzip のまま保つこと。変更していない圧縮ファイルをディスク上で変更されたと報告しないこと。
- `test_outside_changes.py` — FoDE の外で変更されたファイル: Save File と Save Case が変更・削除されたファイルを上書きする前に確認すること、パースから作ったバッファも守られること、Reload File from Disk（`F5`、Case メニュー）が外部の版を読み込むこと、ケース切り替えでスタンプを捨てること。
- `test_shape_mesh.py` — `ui/panels/shape_mesh.py` の Qt に依存しないジオメトリ: `make_shape_mesh` によるジオメトリ生成: 真のコーンとフラスタム（円錐台）、中空の円環、`rotatedBoxToCell`、球（スカラー radius およびベクトル radius によるだ円体）など。
- `test_block_mesh_renderer_colors.py` — Qt に依存しないジオメトリが `shape_mesh.py` へ分離された後に `block_mesh_renderer.py` に残った部分: `_ACTION_COLORS` の `subtract`/`delete` の別名扱いと `remove` を意図的に含めないこと、および同じ AST 走査による ASCII チェックを `block_mesh_renderer.py` 自体に適用したもの — このフォントは Dimensions の範囲表示の `→` を何も描画しなかったため。
- `test_translatable_strings.py` — `ui/**/*.py`（`block_mesh_renderer.py`/`shape_mesh.py` を除く。理由は下の「国際化（i18n）」参照）を AST で走査し、決められた Qt 表示シンク（`QLabel`/`QPushButton`/…/`setText`/`setToolTip`/…/`QMessageBox.warning`/`QInputDialog.getText` など）へ到達する文字列リテラルがすべて `tr()` を経由していることを検査します。f-string も対象でなど。
- `test_block_mesh_selected_block.py` — ツリー → 3D のブロックハイライト: 初期状態ではどのブロックもハイライトされないこと、`set_selected_block` が `RenderSettings.selected_block` に届くこと、解除、別メッシュ読み込みでの破棄。`_highlight_selected_block` が `block_entry` 行の番号を転送し、それ以外の行では解除すること。
- `test_bm_side_by_side_multi_dict.py` — `⊞` サイドバイサイドコーナーボタン（`_update_bm_side_by_side_btn`）: `blockMeshDict`・`topoSetDict`・`snappyHexMeshDict`・`controlDict`（サンプリングオーバーレイ）では有効化され、無関係な辞書（例: `fvSchemes`）では無効化されることを検証。ツリー/BlockMesh スプリッターの両ペインが折りたたみ不可であることと、パネルが 150 px の最小幅を保つことも検証。
- `test_flow_layout.py` — `FlowLayout`（ui/widgets/flow_layout.py）: 最小幅が最も幅の広い 1 項目分に等しいこと、狭めたときの `heightForWidth` による折り返し、折り返し後の項目の順序と位置、`takeAt` の管理を検証。
- `test_case_containment.py` — 書き込みがケースの中に留まることを、実際のウィンドウを通して確かめます。リンクされたファイル、リンクされたディレクトリの下のファイル、外へ出る include は読み取り専用。Save と Save Case は書き込み時にも拒否し（一覧の読み込み後にリンクが変えられた場合を含む）、未保存のまま残すこと。New File、Backup、Delete、Clean Backups、ディレクトリの削除・複製、Copy into Case が `outside/` に手を付けないこと。Duplicate Case と Save As がどちらのコピーモードでも外の中身をコピーせず、リンク越しにバッファを書かないこと。重なるコピー先は何も削除する前に拒否されること。Save As は編集を持ち越せなかったとき元のケースを開いたままにし、`..` を含む include を持ち越し、リンクの後の `..` は畳まないこと。確認ダイアログの後に繰り返す判定（Save、ケースの上書き、Duplicate Directory）。リンクの置き換えに失敗してもリンクが残り、一時ファイルが残らないこと、質問の間に向け先を変えられたリンクは置き換えないこと。同じファイルである 2 つの未保存バッファを Save Case も Save As も書かないこと。ケースフォルダーがディスク上で置き換えられたとき、ケースを再読み込みするまで Save、Save Case、New File が何も書かず理由を示し、Reset File List と Add files が新しいフォルダーに触れず再読み込みもしないこと。新しいケースで 1 つのファイルになる 2 つのバッファを Save As が止めること。
- `test_case_ops.py` — ケース全体を開く・再読み込みする・複製する・名前を付けて保存する操作（カバレッジ 16% → 66%）。まず破壊的な側から。
- `test_file_mgmt_ops.py` — `ui/mixins/_file_mgmt_ops.py` 全体（カバレッジ 28% → 80%）。まずバックアップ、ファイル削除、ディレクトリ削除、すなわちディスクから対象を取り除く操作。
- `test_boundary_ops.py` — `ui/mixins/_boundary_ops.py` の複数ファイルにまたがる操作。1 クリックで複数のフィールドファイルに書き込むもの（全ファイルからの削除、全ファイルへの追加、テーブルのコンテキストメニューから呼ばれる単一ファイルの編集・作成・貼り付け・削除）を対象とする。
- `test_boundary_view_copy.py` — `BoundaryViewPanel._table_data()` と Copy Table: Markdown 出力と 2 つの CSV アクション（連結版・複数行版）。
- `test_case_switch_clears_block_mesh_panel.py` — 別のケースに切り替えたとき、`_load_case_dir()` が `BlockMeshPanel` の状態を（`_topo_shapes`/`_snappy_shapes` の一覧だけでなく）`clear()` 経由で完全にリセットすること: シェイプ別メニューアクション、`non_geometric` 一覧、`locationInMesh`/`locationsInMesh` マーカー、`Export Shapes as STL…` アクションの有効/無効状態がすべてクリアされること。
- `test_code_editor.py` — `CodeEditor` の折りたたみマップ計算、折りたたみ/展開のトグル、`FoamFile { … }` ヘッダーとファイル先頭のコメントバナーの自動折りたたみ。
- `test_code_editor_zoom.py` — `ui/widgets/code_editor.py` のズーム部分: `Ctrl` `+`/`-`/`0` と `Ctrl+wheel`、ズーム量をアプリケーションフォントからのポイント差分として保持するモデル（保存したズームが別マシンの異なるフォント設定でも同じ意味を保つため）、および `ZOOM_MAX_POINT_SIZE` による上限。
- `test_comparison_tree_panel.py` — `ComparisonTreePanel`: `load` でヘッダーラベルを設定しプロキシを更新して FoamFile ノードを折りたたみ Type 列の表示を再適用すること、`clear` でモデルとヘッダーをリセットすること、`set_type_column_visible` で Type 列の表示を切り替え `load` をまたいで状態が維持されること、`use_value_requested` シグナルが接続可能なこと。
- `test_detail_panel_fit.py` — Detail ペイン自身の折り返しラベル切れ修正（下記「フォントサイズと表示スケーリング」の「繰り返しフィットする: Detail ペイン」を参照）: `_choice_hint_label` が 3 通りのフォントサイズでスクロールエリアの到達可能範囲の下端に届くこと、通常ページのすべての折り返しラベルが必要な高さを得ていること、populate 後に幅を狭めても追従すること（populate 時のフィットだけでなく `resizeEvent` 自身の再フィットを検証）。
- `test_dialog_fonts.py` — About ダイアログと Resources ダイアログのラベルが 9・11・16 pt でデスクトップのフォントサイズに追従すること。うち 6 つは以前 `font-size` をピクセル値（16, 12, 12, 12, 13, 13）で固定しており、デスクトップのフォント設定を完全に無視していた — 上記 `test_block_mesh_panel_fonts.py` と同じ不具合。
- `test_current_text.py` — `_current_text` の優先順位（開いているファイルはエディタ、次にバッファ、パースキャッシュ、ディスク。`fallback=False` ではバッファで止まること、開いているファイルを別表記のパスで指しても一致すること）と `_dirty_paths`（読み取り専用を除外し、開いているファイルは `text_dirty` で数えること）。
- `test_dialog_label_fit.py` — `ui/label_fit.py` の検証: 両ダイアログを 9・11・16 pt で構築し、折り返しラベルがどれも必要な高さより小さく割り当てられないことを検証する。どちらも幅固定で折り返しラベルが詰まっており、折り返し `QLabel` の `sizeHint` は実際に与えられる幅ではなく Qt が推測した幅で測られる。
- `test_diff_state_reset_on_case_change.py` — `_reset_diff_for_case_dir` の回帰テスト: 別のケースを開くとアクティブな比較（差分状態・バー・パネル・解析キャッシュ）がクリアされること、同じケースの再読み込みでは維持されること、比較が無いときは何もしないこと。
- `test_drag_drop_open_case.py` — `MainWindow` のドラッグ＆ドロップによるケースオープン: `dragEnterEvent`、`dropEvent`、すべての子ウィジェットを有効なドロップ先にする `eventFilter`。
- `test_duplicate_case.py` — ケース複製: 「全ファイル」モードと「アプリ表示ファイルのみ」モードでコピーされる内容、コピー先の作成、ケースに登録された追加ファイルもコピーされること。
- `test_editor_panel.py` — `EditorPanel` の `user_text_changed` の抑制: プログラム的なパス（`set_text()`、`reload_highlighting()` — `QSyntaxHighlighter.rehighlight()` は書式しか変わらなくても `textChanged` を発火させ、以前は Generate OpenFOAM Keywords の後にファイルが編集済みになっていた）では発火せず、ドキュメントへの直接編集では発火すること。
- `test_export_stl_action_state.py` — `STL ▾` メニューの「Export Shapes as STL…」アクション（`_export_stl_act`）: 初期状態は無効、`update_topo_set`/`update_snappy_hex_mesh` で描画可能なシェイプを読み込むと有効化、`clear()` や空の辞書の再読み込み後は再び無効化されること。
- `test_export_stl_dialog.py` — `ExportStlDialog`: topoSet と snappyHexMesh を合わせたシェイプの行数とラベル付け、渡された可視状態セットが初期チェック状態に反映されること、Select All/Deselect All、チェックした各シェイプが 1 つの `.stl` として書き出され `pyvista.read()` でラウンドトリップ確認できること、ラベル衝突時のファイル名重複排除、縮退ジオメトリを例外を投げずにスキップすること、`_safe_filename` のサニタイズ処理。
- `test_case_browser_dialog.py` — `CaseBrowserDialog`: 非モーダルなウィンドウモダリティ、2 つのペインが 1 つのモデルを共有すること、ツリークリックによるナビゲーションとリストのダブルクリック（ケースは開き、フォルダは降りる）、選択項目の種類ごとのアクション行の有効/無効、同じナビゲーターに対するもう 1 つのビューが追従すること。
- `test_case_browser_state.py` — 結合まわりの規則: 開いているケースの祖先に対する操作はモーダルを一切出さずに拒否されること、開いているケースをリネームすると新しいパスで再読み込みされウォッチャーも付け替えられること、削除するとケースを閉じてパスをキーとする状態がクリアされること、foamMonitor が削除より*前*に停止されること、`.foam-editor-files.json` はパスがケース相対のため移動後も残ること、`_close_case()` が自身の持つ各フィールドをクリアすること。
- `test_allrun_ui.py` — Allrun Steps: すべての状態・疑い・注記の文言、ウィンドウの行・選択・ボタン・シグナル、メインウィンドウがステップを（`-o` 付きで）送ること、ソルバーのステップの確認に出る Check Case のエラー、Open Log、ケースに追従するメニュー項目。
- `test_allrun_create_ui.py` — Create Allrun from Logs: すべての印・含めなかったログ・注記の文言、チェックと順序に追従するダイアログのプレビュー（とメッシュを残す Allclean）、既存の Allclean の尊重、何もチェックがないときに無効になる Create、ステップ表示のボタン、メインウィンドウがスクリプトを書いて開くこと、Allrun を決して置き換えないこと、ケースに追従するメニュー項目。Allrun-parallel のチェックボックス（行の追加と削除、タブ、並列実行の後はチェック済み、スクリプトがあれば選べない、チェックの入ったソルバーがなければ Create は押せない）、Add Command… と Remove、メインウィンドウが 4 つのスクリプトを書くこと、更新されても保たれるステップのウィンドウの Script 選択、両方のスクリプトがあるときだけ尋ねる Run Allrun Script。
- `test_case_check_ui.py` — Check Case: すべての指摘・スキップのコードに文があること、ダイアログの一覧・詳細行・`open_requested`、ケースに追従するメニュー項目、未保存の編集が数えられること、指摘からファイルを該当行で開くこと、Run Solver が指摘を（上限付きで）表示すること。
- `test_case_nav_panel.py` — `CaseNavPanel`: ルートの付け替えとパスラベル、ダブルクリックで降りずにケースを開くこと、ナビゲーターの各シグナルとそのペイロードごとのテスト、記憶された場所とそのフォールバック連鎖、長い名前が水平スクロールバーを伸ばすのではなく省略されること。
- `test_file_list_panel.py` — `_build_context_menu` 経由で構築したコンテキストメニュー（ファイル行の各アクションが対応するシグナルを出すこと、追加ファイルのみの Remove、Show in 3-D view as のチェック状態、読み取り専用行は Copy into case のみ、ヘッダーの New/Add、0/ ↔ 0.orig の複製・削除の条件、ケースがなければメニューなし）。差分フィルター: `set_diff_filter_enabled` でチェックボックスの表示・非表示・チェック解除など。
- `test_find_examples_dialog.py` — `FindExamplesDialog`: 非モーダルなウィンドウモダリティ、インストールコンボの初期化（`discover_installations` を偽インストールにモンキーパッチ）、スレッド検索後の Tutorials/caseDicts グループ化結果、チュートリアル一致と caseDicts 一致でのプレビュー表示と比較/複製ボタンの有効/無効、クリップボードへのコピー、チュートリアルケースルートを渡す `compare_requested`/`duplicate_requested` の発行など。
- `test_function_object_dialog.py` — 偽のインストールでの `FunctionObjectDialog`: 選ぶ前は追加できないこと。例があらかじめ入り、使用中の名前は空いている名前に置き換わり、変更しなければプレビューがテンプレートと一致すること。
- `test_run_post_process.py` — Tools > Run postProcess…: 既定ですべての関数。ケースの関数が先に並ぶこと。
- `test_include_expansion_viewer.py` — 展開済みツリーを 3-D ビューアへ渡す MainWindow 側の結線。`BlockMeshPanel` の記録用スタブを使う（`main_window` フィクスチャは blockmesh を無効化しており、検証対象は VTK の挙動ではなくパネルに渡されるツリーそのもの）。
- `test_included_files.py` — `MainWindow` における `#include` 対応のエンドツーエンド。`tmp_path` 上に偽の OpenFOAM `etc` ツリーを作るため実インストールに依存しない: ケース外のインクルードが `<included>` グループに入り、ケース内のものは本来のグループに入ること、既に一覧にある対象にマークが付かないことなど。
- `test_foam_highlighter.py` — `FoamHighlighter`: コメント、文字列、`#directives`、`$macro` 参照、予約キーワード、数値（`wall0`/`inlet-1` のような識別子内の数字を色付けしない lookaround ガードを含む）、同じガードを共有するキーワードルール（`y0.1` や `off.1`、シェルの `config.fi` のようなドット付き識別子が分割されない）など。
- `test_keyboard_shortcuts_dialog.py` — **Help > Keyboard Shortcuts** が実態と一致し、かつ画面に収まり続けることの検証。この一覧は手書きの表なので、ウィンドウが実際に登録しているショートカットとずれても何も止めるものがなかった — `Ctrl+S` はメニュー項目もこの一覧の記載も無いまま数リリース登録され続けていた。
- `test_log_advice_ui.py` — すべての助言コードにタイトルと説明があること、その分岐、ダイアログの欄と `open:N` リンク、メインウィンドウがリンク先のファイルを該当行で開くこと。
- `test_plot_results_ui.py` — Plot Results: データの一覧、チェックで列がプロットされること、残差で対数軸になること、ケースの比較（「すべてのケース」、ケースを外す）、Line Settings で選ぶ線のサンプル時刻（Open File もそれに従うこと）、設定がプロットに届くこと、Use Current View、画像サイズでのコピー、保存とエクスポートがファイルを書くこと、補正した名前で上書き前に確認すること、Reload、自動更新（変化があったときだけ描き直し、オフや非表示では動かず、ズームを保ち、新しい時刻やデータを拾うこと）、凡例の位置（選んだ位置と、ドラッグした位置にそのまま描き直されること）、データのツールチップと Open File / Show in Folder（ファイルごとに 1 つのウィンドウ、リスタートの区間ごとのメニュー項目）、Time の行がコマをプレビューし（軸の固定、時刻表示）、すべての出力 — 画像、スクリプト、Export Data、Open File — が表示中のコマに従うことPlay が最後で止まること、Save Animation が時刻ごとに 1 コマを書くこと、ビューが保存する画像と同じ配置になること（と Fit to window）、文字の大きさがプロットに届き、本当の既定値から増減すること、Line Settings…（チェックした列にだけ表示。凡例、色、マーカーのみ、線幅が線に届くこと）、設定を保存して新しいウィンドウにそのまま読み込めること、なくなったケースの報告、メニューの配線と matplotlib がないときのメッセージ。
- `test_data_file_viewer.py` — Plot Results のデータファイル表示ウィンドウ: 小さいファイルは全体、大きいファイルは先頭と行単位の末尾、gzip の展開、一部だけ表示しているときの注記、Reload、読めないファイル。
- `test_log_summary_dialog.py` — `LogSummaryDialog`: 非モーダルなウィンドウモダリティ、ケースディレクトリ内で最も新しく更新された `log.*` ファイルをデフォルト選択してその要約を表示すること、ファイルフィールド変更時の再パース、空のケースディレクトリでのフォールバックメッセージ。
- `test_main_window_save_refresh.py` — `test_main_window_split.py` の構造チェックのみとは異なる、初めての振る舞いレベルの `MainWindow` テスト: 保存せずに編集しても `constant/polyMesh` メッシュインジケーターが変化しないこと、`save_file()`/`save_all_files()` のどちらも即座にファイル一覧を更新してなど。
- `test_main_window_split.py` — Mixin 構造: 各 Mixin が正しいメソッドを保有すること（`_BoundaryOpsMixin` の `_on_patch_selected`、`_TreeCrudOpsMixin` の `_apply_comparison_value`、`_FoamMonitorOpsMixin` の foamMonitor 関連メソッドを含む）、Mixin 間の重複がないこと、`MainWindow` がすべての Mixin を継承していること。
- `test_manage_extra_files_dialog.py` — `ManageExtraFilesDialog`: 登録済みの追加ファイル・ディレクトリの表示と削除操作。
- `test_reset_all_settings.py` — **Reset All Settings** の後に `app_config.json` がどうなるかを検証します。ファイルを削除するだけでは処理の半分でしかありません。
- `test_run_tool_dialog.py` — `RunToolDialog`: 初期状態のライブプレビューが `get_command()` と一致すること、チェックボックス/値編集によるコマンド更新、`last_values` の復元と `get_values()` の新しいダイアログへのラウンドトリップ、解析不能な追加オプションでの実行ボタン無効化、プレフィックスチェックボックスによるシェルプレフィックスの付加、Browse によるケース相対パスの挿入（ケース外は絶対パス）。
- `test_stays_open_menu.py` — ツールバーのドロップダウンメニュー（`Vertices ▾`、`Blocks ▾`、`Scale ▾`、`topoSet ▾`、`snappyHexMesh ▾`）がチェック可能項目のクリックでは開いたままになり、チェック不可のアクションでは通常どおり閉じること。
- `test_terminal_panel.py` — `SimpleTerminalWidget` と `TerminalPanel`: 初期状態、作業ディレクトリの切替、クリーンアップ、コマンド履歴、タブラベル、`run_command()`（シェル準備前のキューイングを含む）。あわせて実行中コマンドの保護: Simple ターミナルと xterm の PTY バックエンドそれぞれで実際の `sleep` が報告されること、何も実行していなければ確認を出さないこと、確認がコマンド名を示し既定が No であることなど。Windows ではケースのパスをシェルに打ち込まず、そのディレクトリでシェルを起動し直すこと、終了したシェルは何も打ち込まずにケースで再起動すること。
- `test_xterm_download.py` — `download_xterm_files`/`xterm_files_valid`: ダウンロードはすべてのファイルが固定した SHA-256 と一致したときだけ導入されること、改ざんや失敗したダウンロードは何も導入せず正常な導入済みファイルを残すこと、ダウンロード後に変更されたファイルは有効と見なされないこと。ネットワークは使わず、取得処理を差し替えます。
- `test_theme.py` — `ui/theme.py` の配色テーブルをデータとして検証します: コントラスト計算、選択行の前景・背景ペアに関する慣習ルール（Windows のアクセントカラー `#0078d4` を明示的に指定したリグレッションテストを含む。黒と白のうちコントラストが高い方を選ぶ実装だと、この不具合を再現してしまうため）、どのアクセントカラーでも判読不能なペアが生じないことを網羅的に確認するテスト、両テーブルのすべての前景色がそのテーマの `Base` に対して 3:1 を下回らないことなど。
- `test_fonts.py` — `ui/fonts.py` の検証: エディタと 2 つのターミナルがアプリケーションフォントから導出する等幅フォントサイズ。`ui_point_size` が `QFontInfo` にフォールバックするのはプラットフォームフォントがピクセル指定の場合だけであること（`QFontInfo` は整数ピクセルに量子化するため、96 dpi の 13 pt は 12.75 として返ってくる）、および xterm ページ用に `css_pixel_size` が 96/72 固定で変換することを含む。
- `test_icons.py` — `ui/icons.py`: `ICON_NAMES` とアセットディレクトリの対応を両方向で検証すること、宣言されたすべての名前が非 null かつ空でないピクセルのアイコンを返すこと、未知の名前は例外ではなく null のアイコンに落ちること、すべての SVG アセットがパース可能で SPDX ヘッダーを持つこと、`icon_pixel_size()` がアプリケーションフォントに追従して大きくなることなど。
- `test_tools_ops_mesh_actions.py` — Tools メニューの「Run *」アクションと Run Allrun/Run Allclean/Clean Case: blockMesh/snappyHexMesh/topoSet/setFields/checkMesh の（実物の、exec をパッチした）`RunToolDialog` を受理した後に偽のターミナルパネルへ送信される正確なコマンド文字列、キャンセル時に何も送信されないこと、時間ディレクトリが存在する場合にダイアログへ渡される再実行警告テキストなど。
- `test_tree_block_crud.py` — `block_entry` 行に対する追加/複製/削除: `_new_sibling_for` が生成する `block_entry` のデフォルト値が実際のブロックとして再解析されること（辞書が親の場合は `word` エントリ）、`_delete_label` がブロックを位置で呼ぶこと、ブロックの削除・追加後に書き出されるファイル（兄弟はそのまま、リストは自分の行で閉じる、残りのブロックは位置で振り直される）、および MainWindow を通した削除 → エディタテキスト → Ctrl+Z の一連の往復。
- `test_tree_context_menu.py` — `_build_tree_context_menu` 経由のツリー右クリックメニュー: 通常エントリでの兄弟操作、`block_entry` では CRUD 可・Comment Out 不可、境界エントリでの Rename Boundary、解決できない `#include` では Open Included File が無効、読み取り専用ファイルでは Copy Value 以外すべて無効、各行が対応する操作を呼ぶこと。
- `test_tree_color_lexer_dispatch.py` — `unknown_raw_entry` の琥珀色表示、パーサの括弧ブロック用ディスパッチテーブル（`_FIELD_VALUE_KEYS`・`_NAMED_BLOCK_PARAMS`・`_OPTIONAL_NAMED_BLOCK_PARAMS`）と、どのキーが同じハンドラを共有するか。
- `test_tree_copy_paste.py` — ツリーの Copy/Paste Value: コピーした値の round-trip、異なる型のノード間でのペースト、サポート対象外のノード型を拒否するガード。
- `test_tree_undo_redo.py` — スナップショット方式のツリー Undo/Redo: インライン編集の Undo が値・エディタテキスト・クリーンなダーティフラグを復元すること（Redo で再適用）、複数ステップの Undo、新しい編集による Redo ブランチのクリア、拒否された編集の迷子スナップショットのスキップ、削除/エントリ追加の往復、1 つの CRUD 操作がちょうど 1 つのスナップショットを生むこと（シグナルによる二重チェックポイントなし）、複数ファイルのスナップショットが全ファイルを復元すること、ケース再読み込みでのスタッククリアなど。
- `test_update_viewer_panels.py` — `MainWindow._update_viewer_panels`: ファイル名から 3D ビューアへのディスパッチを、オーバーレイを駆動する各辞書についてパラメータ化して検証し、無関係な辞書では何もディスパッチされないこと、そして Apply Text to Tree が snappyHexMesh オーバーレイを更新することを確認します。最後の 1 つがこのヘルパーの存在理由です: ディスパッチは読み込み・保存・ツリー編集の各パスにコピー&ペーストされておりなど。
- `test_tree_inline_edit_dirty.py` — Tree パネルのインラインセル編集がファイルをダーティにしエディタテキストを再生成すること、拒否された編集はファイルをクリーンなままにすること。
- `test_view_log_summary_action.py` — `_on_view_log_summary_clicked`: ダイアログを閉じた後の再表示（閉じても破棄はされず非表示になるだけなので、キャッシュ済みインスタンスは再度 raise するのではなく show し直す必要がある）、ケースディレクトリ未設定時の no-op、ケース切り替えへの追従（`_load_case_dir` が次のメニュークリックを待たず、開いたままのダイアログへ `set_case_dir()` で即座に新しいディレクトリを反映する）。
- `test_window_state.py` — `ui/window_state.py` とそこへ渡すスクリーンショット spec: 全フィールドの JSON ラウンドトリップ、未知キーと不正なカメラ値の拒否、デフォルトのマージ（`side_by_side` が必要とする、`False` が `True` のデフォルトを上書きする挙動を含む）、名前によるキーパス指定と匿名エントリの行番号指定、実際の `MainWindow` からのキャプチャなど。
- `test_pane_minimize.py` — `ui/pane_minimize.py` と、それが接続された 3 つのペイン: 畳む/戻すの往復、2 回続けて畳んでも復帰サイズを忘れないこと、`strip` 方式がウィジェットの最大サイズを固定し*かつ解除*すること、空いた領域が他ペインへ比例配分されること、View メニュー項目とペインが互いに無限ループせずに同期すること、下段がタブバーの高さで止まり（タブとコーナーウィジェットが残る）こと、ハンドルのダブルクリック（最小化できるペインが隣にないハンドルでは何も起きないことを含む）など。
- `test_tree_text_sync_bar.py` — **Apply Text to Tree** / **Reload from Tree** の配置: タブページの内部ではなく下段タブバーのコーナーにあること（内部だとタブ切り替えで消え、3D オーバーレイを更新するのは `apply_text_to_tree` である）、上部アクションバーからは消えていること、実際のメソッドに接続されていること（ウィンドウ構築*前*にクラス側でパッチするため、テストが張り直した接続ではなく本物の配線を検証する）、そして Case メニューにも並びなど。
- `test_action_toolbar.py` — 上部アクションツールバー: `addToolBar` で配置される実体としての `QToolBar` であり `centralWidget()` の子ではないこと、アイコンサイズが `icon_pixel_size()` に追従すること、`createPopupMenu()` が `None` を返すこと（Qt 標準の「このツールバーを隠す」メニューには元に戻す手段がないため）、ツールバーへ移動した後も現在ケース/現在ファイルのラベルが更新され続けることなど。
- `test_session_restore.py` — `ui/session_restore.py`: 終了時に正しいキーでレイアウトが保存されること、設定オフでは何も保存しないこと、適用対象がないときに restore が正直に報告すること、壊れた blob（改名されたフィールド、形の変わったフィールド、切り詰められたカメラ、移動したケース、別言語のタブラベル）で例外を出さないこと、そして実際の `MainWindow` から別の `MainWindow` へケース・開いているファイル・選択ツリー行が往復すること。
- `test_multi_dict_overlays.py` — 1 つのオーバーレイに複数のファイルが入る場合（`topoSetDict-slices` と `topoSetDict-background`）: 最後に読んだものが前のものを置き換えるのではなく両方が描かれること、複数のファイルが寄与するときだけ行にファイル名が付くこと、別ファイルの編集後も形状ごとの表示切替が保たれること。
- `test_supported_in_caveat.py` — 測定が止まったところで終わる `supported_in` の範囲に対する Detail パネルの注記。すべての範囲が測定済みになったため `OPEN_ENDED_SERIES` は空で、現在この注記が付くラベルはありません。
- `test_viewer_dicts.py` — `ui/viewer_dicts.viewer_dict_kind`: まず既定の名前、次に手で名付けた派生（`topoSetDict-slices`、`topoSetDict.1`）に対する `FoamFile` の `object` ヘッダ。`blockMeshDict.resolvedBlocks` のようなヘッダのない `#include` 断片はどのオーバーレイにも送らないこと。
- `test_viewer_priming.py` — `MainWindow._prime_viewer`（3D パネルは記録用の代役）: ケースを開くと blockMeshDict、topoSetDict、サンプリングファイル、controlDict がどれも開かずに描画されること（バッファなし、編集済みなし、現在のファイルなし）。controlDict の `#sinclude` で取り込まれるファイルは単独では描画されず、取り込みをやめると描画されること。
- `test_viewer_kind_override.py` — **Show in 3-D view as** による上書き: 自動判定より優先されること、手で編集した設定の未知のキーは無視されること、選択が `.foam-editor-files.json` にケース相対で保存されること、Automatic に戻すとその行がすぐ消えること、ケース外のファイルは拒否されること。
- `test_tools_busy_terminal.py` — ターミナルが使用中のとき、ターミナル系の操作（各 Run ツール、Run Solver、Allrun、Allclean、Clean Case、Restore 0/）がすべて拒否され何も送らないこと。Run reconstructPar…（`processor*` がなければ拒否、警告に未再構築の時刻、既定で `-newTimes`、実行中は拒否）。

**`tests/services/`**
- `test_backup.py` — バックアップファイルの命名（`.bak_<タイムスタンプ>`）と内容（ファイルが開いている場合はインメモリバッファ、それ以外はディスク上の内容をキャプチャ）。
- `test_case_scan.py` — `case_scan`: ケース判定（`system/` または `constant/`、およびケースでないものの判定）、既定で隠しエントリを除外したディレクトリのみの一覧、大文字小文字を区別しない順序、`has_subdirs`、シンボリックリンクされたディレクトリ、読み取り不可な子でも `readable=False` として一覧に残ること、存在しないディレクトリで例外ではなく `[]` を返すこと、実ケースに対する `case_summary`、`ancestors_to` の連鎖。
- `test_allrun.py` — `allrun`: チュートリアルの形、すべてのオプションと変数の形、継続行、配管、分岐、別ディレクトリ（cd とサブシェル）、Allrun.pre、未保存のバッファ。各状態、長いログとランク接頭辞付きのログ、2 種類の疑い。`-o` 付きのコマンドと「ここから実行」。
- `test_allrun_corpus.py` — v2606 と Foundation-12 のすべてのチュートリアルの Allrun が読めること（計測値を固定）。damBreak のステップとログ。
- `test_allrun_create.py` — `allrun_create`: ヘッダー（除くオプション、括弧のつなぎ直し、フルパス）、開始時刻と終了時刻による順序、`runParallel` と `-np`、サフィックスと FoDE の part ログ、失敗と読むだけの行のチェック外し、reconstructPar の移動、ログの一覧へ合流する辞書からの提案と骨組み（並列は processor ディレクトリがあるときだけ）、フォークごとの復元の行、メッシュを残す場合を含む Allclean の形、引用、`sh -n`、ファイルを決して置き換えないこと、書いた Allrun が同じログとして読み戻せること。並列実行の後だけの reconstructPar、cavity 型とログのある並列ケースの分割（各スクリプトに `sh -n`）、チェックの入ったソルバーやサブドメインがなければ分割しないこと、ソルバーより前に何もなければ Allrun.pre を作らないこと、入力したコマンド。
- `test_case_check.py` — `case_check`: 各指摘を起こすケースと、起こしてはならないケース — 正規表現・グループ・`setConstraintTypes` によるカバー、項目のない `empty` パッチ、たどる／飛ばす include、point 場、`patchType`、メッシュ生成前の `blockMeshDict` からの推定とそれを止める条件、マルチリージョン、controlDict と decomposeParDict のしきい値、フォークを考慮した辞書の規則。
- `test_case_check_corpus.py` — 誤検出の防波堤: v2606 と Foundation-12 のすべてのチュートリアルが `restore0Dir` 後にレビュー済みの指摘しか出さないこと。ツリーがなければスキップ。
- `test_case_paths.py` — `services/case_paths.py` の操作ごとの判定: シンボリックリンクされたファイルとディレクトリ、`..`、リンク経由で開いたケース、ループと存在しないパス。どんな書き方でもコピー先の重なりを検出し、文字列が異なる場合は同一性で検出すること。`conflicting_writes`。include の行が実ファイルごとに 1 つであること。固定されたルート（置き換えられたフォルダーと向け先を変えられたリンクはすべての判定を拒否し、開き直すと固定し直し、ほかのディレクトリには影響せず、特定できないフォルダーは拒否し、ケースの設定は書き込みも削除もされない）。1 つのファイルの 2 つの名前に対する `file_identity`。include スキャンの読み取り専用集合。`copy_visible_files` が外のエントリ（ケースの設定ファイルを含む）を飛ばして報告すること。設定の一時ファイル書き込み（仕込まれた `.tmp` リンク、最終名にあるリンク、既存と新規のモード、後始末）。壊れたリンクに対する排他的作成。リンクされた `controlDict` をバックグラウンド停止が拒むこと。
- `test_case_copier.py` — `copy_visible_files`: 可視ファイルがレイアウトを保ってコピーされること、非表示エントリ（ルートの `log.*`、時刻ディレクトリ、未登録ファイル）はスキップされること、登録済み追加ファイルと `.foam-editor-files.json` 自体が引き継がれること、設定ファイルなしでも動作すること、ネストしたコピー先の作成、細工した設定の `../` や絶対パスの項目がコピー先の外に何も書かないこと。
- `test_disk_stamp.py` — `services/disk_stamp.py`: 別のプログラムによる書き換えは同じサイズでも変更、touch や同一内容の書き直しは変更ではない、削除は変更、存在しないファイルにはスタンプがないこと。
- `test_include_scan.py` — `scan_includes`/`included_files`/`copy_destination_for`/`foam_etc_dirs`: パーサーが保存するのと同じ生ディレクティブテキストを hit が持つこと（ツールチップ検索のキー）、`#codeStream` の C++ ヘッダーのスキップ、非再帰性、サイズ・ログ・スクリプトのガード、mtime メモが未変更ファイルを読み直さず変更時には読み直すこと、ケース内／外の振り分け、既に一覧にあるファイルに対するシンボリックリンク考慮の重複排除など。
- `test_case_files_config.py` — `TestCaseFilesConfigDirs`: `DirEntry` の追加・削除・インプレース更新、プレーン文字列 JSON の後方互換ロード、設定リセット。`TestEntriesOutsideTheCase`: 絶対パス、`..`、Windows のドライブ指定の項目は読み込み時に捨てられ（次の保存からも消え）、`add_file`/`add_dir` も拒むこと。点を含むだけの名前は通ること。
- `test_case_fs_ops.py` — 安全確認の中核を、主にその拒否を通じて検証する: ソース自身のサブツリーへの移動・コピー（直接の場合とシンボリックリンク経由の場合の両方 — これにより `normpath` ではなく `resolve()` が使われていることが証明される）、既存の宛先の*中へ*移動しないこと、新しい名前へのパストラバーサルとセパレータ、保護対象パス、シンボリックリンクをリンクとして削除しリンク先はそのまま残ること、コピーがシンボリックリンクを辿らないこと、ケースに限ったリネームの例外、注入された削除処理の順序とエラー伝播など。
- `test_case_loader.py` — `detect_time_dirs` と `TestExtraDirs`: フラット・再帰スキャン、存在しないディレクトリの許容、重複排除。
- `test_example_search.py` — `example_search`: インストールルート／素の tutorials ディレクトリ／非インストールディレクトリに対する `installation_from_dir`、環境変数マッピングの注入・`extra_roots` の優先・重複排除を含む `discover_installations`、`stop` 境界付きで祖先を遡る `case_root_for`など。
- `test_log_advice.py` — `log_advice`: 本物の v2606 のログ（`tests/fixtures/logs/v2606/`）それぞれが、正しいコード・値・ファイル・行に対応すること。セミコロン抜けで飲み込まれた項目、0.orig からの復元、クーラン数による分岐、並列のランク接頭辞と重複除去、認識できないエラーを扱わないこと、ソースから組み立てた Foundation の文言。
- `test_log_summary.py` — `parse_log`/`format_summary`: `blockMesh` の Mesh Information/Patches 抽出と致命的エラー検出、`snappyHexMesh` の `Wrote mesh in` マーカーによるフェーズ分割・カテゴリごとの細分化反復回数・最終的なパッチ別レイヤーテーブル・件数付きの警告重複排除、`topoSet` のマルチソースセットの集約（`Read set` チェックポイントは新規セットではなく同一セットの継続として扱われること）など。
- `test_tool_options.py` — `tool_options`: 期待される `TOOL_SPECS` の集合とデフォルトコマンド（snappyHexMesh のデフォルトでオンの `-overwrite`）、`build_args` の bool/value/file の仕様順処理、空値の省略、追加テキストの shlex 分割（閉じていない引用符 → `ValueError`）、古い未知フラグの無視など。
- `test_solver_run.py` — リンクされた `processor*`（またはその中のリンクされた時刻ディレクトリ）を、チェックと削除そのものの両方が拒否して手を付けないこと。`solver_run`: controlDict の `application`（通常・引用符付き・欠落・解析不能）、foamRun の `solver` モジュール（foamRun のときのみ）、foamMultiRun の `regionSolvers`、`numberOfSubdomains`（0 以下や `$var` は不明扱い）、ソルバー名の検証（シェルのメタ文字・パス・先頭の `-` を拒否）など。
- `test_plot_animation.py` — コマが出力時刻の数値順の和集合であること。コマが各線を最新の時刻で持ち、まだない線を除くこと。色の固定。固定した範囲が全コマを覆い、設定した Min を保つこと。GIF、PNG、（ffmpeg があれば）MP4 の書き出しがすべてのコマを通常の権限で置くこと。取り消した保存が何も残さず、既存のコマのフォルダーを置き換えないこと。
- `test_plot_data.py` — `plot_data`: 調べたすべての形式（OpenCFD と Foundation の forces、probes、solverInfo、途中で繰り返されるヘッダー、パッチごとの組み替え、ビンごとの列、ヘッダーのないサンプリングセットとあるもの、CSV、gzip）、リスタートの連結、ログの残差、探索とキャッシュ、書きかけの最後の行を書き込み中のファイルからだけ捨てること、リーダーが FoDE のものを何も import しないこと。
- `test_plot_script.py` — `plot_spec`/`plot_render`/`plot_script`: エクスポートした Python スクリプトを実行し、その figure を `draw()` のものと要素ごとに比べること、単独で実行して PNG を保存すること、リーダーがそのまま埋め込まれること、ラベル、見つからない系列、CJK フォント、寛容な spec の往復、スタイル、文字の大きさ、選んだ X の列（figure の比較でも）、設定ファイルの外枠、gnuplot がインストールされていれば（線のスタイルを含む）gnuplot でのエクスポートの実行。
- `test_plot_export.py` — Save as CSV の表: 見出しは 1 行、正確な数値、空の欠損、引用符付きの見出し、タブ区切りのコピー。使われている CSV や説明ファイルを避ける名前。見出しのないセットが解読した見出し付きで書き出され、説明ファイルに推定と書かれること。リスタートのファイルが順に並ぶこと。自分の説明ファイルの判別。Export Data… の表が、1 つのデータ内では x を共有し、ケースをまたぐと線ごとの組を保つこと。
- `test_plot_output.py` — Plot Results の書き込みの規則: ケース自身のディレクトリ（時刻、`0.orig`、processor、`postProcessing` を含む）には書かないこと、最上位のログ・スクリプト・`.foam` を置き換えないこと、プロット中のファイルはどこにあっても守ること、シンボリックリンクは指す先で判定すること、アトミックな書き込みが失敗時に元のファイルを残すこと、エクスポートしたスクリプトの `savefig` が `.dat` の名前を書き込む前に拒むこと。
- `test_post_process.py` — `post_process`: インストールからのツール判断。Add Function Object が提示するコマンド `post_process_command`（OpenCFD と Foundation 11 以降、結果がなければ空、最新の時刻が processor にしかなければ `mpirun … -parallel`）。
- `test_process_tree.py` — 偽の `/proc` に対する `child_processes`/`running_command_names`（空白や括弧を含む `comm`、孫プロセスは報告しないこと、`tee` は名前から除くが実行中として数えること、`job_control` ではシェル自身の補助プロセスを無視し、独自のプロセスグループを持つジョブは報告すること、`/proc` がなければ何も報告しないこと）、実際のプロセスに対する `files_written_in`（書き込み用に開いたログは数え、読むだけのものは数えない。`/proc` がなければ None）となど。
- `test_background_run.py` — `background_run`: コマンドの形（前置きが先、`tee` なし、`< /dev/null`、引数の引用は一度だけ）。`build_command(background=True)`。
- `_processor_cases.py` — テストではなく、分割ケースの組み立て用ヘルパー。decomposePar・並列計算・reconstructPar がディスクに残す配置をなぞる（実際の v2606 cavity の計算で確認済み）。`test_solver_run.py` と `tests/ui/test_tools_busy_terminal.py` が共用。 `_sound_case`/`_field_text`/`_write` も提供: 実際の OpenFOAM ファイル（ヘッダ、個数付きの `internalField`、`boundaryField`、終端行）でできたケースを組み立てる。`writeCompression on` が残す形で圧縮することもできる。
- `test_field_integrity.py` — `field_integrity`: 完全な ASCII のフィールドと、ペイロードに中括弧やセミコロンを含むバイナリのフィールド。30/60/95% の位置や `boundaryField` の中で切れたファイルには終端行がないこと。
- `test_domain_bounds.py` — `domain_bounds`: `#include` した変数を解決した拡大縮小後の範囲、snappy の背景ボックスの指摘、エディタのテキストの優先、blockMesh がなければ推測しないこと。`suggest_values`: 中心のプローブ、壁から内側に寄せた最も長い方向の線、最も薄い方向に垂直な面、法線を保って移す OpenCFD の切断面の行、forces は変更しないこと、領域がなければ何もしないこと。
- `test_function_templates.py` — `function_templates`: OpenCFD 形式の例（1 点だけのリストを点ではなく点のリストとして読む）と Foundation 形式のプレースホルダー（種類、必須、コメントをヒントに、名前から分からないプレースホルダーはキーの意味を使う）、type/libs を表示しないこと、同じ行の項目は扱わないこと、コードを含むテンプレートは入力欄にしないこと。変更しなければバイト単位で一致すること、点のリストの編集はその項目だけを書き換えることなど。
- `test_variant_corpus.py` — ローカルの v2606 チュートリアルでのサフィックス付きの派生ファイル（なければスキップ）: mixerVessel と分割数の系列の派生ファイルが表示され、誤一致が除外されること。

**`tests/app_config/`**
- `test_app_config.py` — `AppConfigManager`: ウィンドウサイズ、デフォルトケースディレクトリ、Case Library ディレクトリ（`$WM_PROJECT_DIR/tutorials` フォールバックを含む）、`save()`/`reset()` のセマンティクス、`app_config.json` が存在しない場合のフォールバック、設定の組み合わせ、JSON 構造、フィーチャーフラグの扱い（`set_feature`/`set_features`）。
- `test_foam_env.py` — `foam_env_dirs`: 明示的な `FOAM_*` 変数が `WM_PROJECT_DIR` フォールバックより優先されること、サブディレクトリ単位のフォールバックはディレクトリが存在する場合のみ働くこと、無効・空白の変数は未設定扱いになること、バージョンの解決。
- `test_json_io.py` — `load_json` の欠落・破損・正常 JSON の扱い、`save_json` のラウンドトリップと親ディレクトリ作成、`atomic_write_text` が成功時に一時ファイルを残さないこと、最終リネームやシリアライズが失敗しても元ファイルが無傷のまま（一時ファイルも掃除される）こと。
- `test_keyword_generator.py` — `keyword_generator`: `*.C`/`*.H` から辞書読み取り呼び出し（`lookup`/`get<…>`/`readEntry`/`found` など）を収集する `scan_src_lookup_keywords()`（キーワードでない形式は除外）、フィクスチャのインストールツリーに対する `generate(project_dir=…)` — 環境変数は無視、`version` はディレクトリ名由来、ペイロードの来歴メタデータ、何も収集できない場合の `RuntimeError`。
- `test_config_failure_reporting.py` — 設定ファイルを読めない・書けない・削除できないときにユーザーに伝える内容: 失敗は出力されるのではなく記録されて `take_warnings()` で取り出されること、解析できないファイルは終了時に既定値で上書きされるのではなく `.json.bad` に退避されること。

**`tests/schemas/`**
- `test_schemas.py` — `ChoiceItem`/`KeySchema`、`schema_config.json` の読み込み・保存・リセット・削除、`SchemaRegistry` のプレーン/親修飾/祖父母修飾ルックアップ、他の名前空間の内側でフラットフォールバックを抑止する閉じた名前空間ルール（2 モデル構成の合成モジュールによる検証と、実在する `snappyHexMeshDict` の名前空間で過剰抑止が起きないことの確認）、`snappyHexMeshDict` スキーマモジュール、設定済みモジュール一覧。
- `test_schema_coverage.py` — モジュールが丸ごと機能停止したことを検出できたはずのテスト。`tests/fixtures/schemas/` にある実際の辞書（v2606 のチュートリアルから無改変でコピーしたもの。スキーマに合わせて手を加えていない点が重要）をパースし、`DetailPanel` とまったく同じ方法（`node.name`、`node.parent.name`、`node.parent.parent.name`）で走査して、辞書ごとのカバレッジ下限を検証します。
- `test_turbulence_schemas.py` — foamlore が生成した `turbulence_properties`/`momentum_transport` モジュール: `TARGET_FILE` と `SCHEMAS` の形状（値はすべて `KeySchema`、選択肢はすべて `ChoiceItem`）、`schemas/builtin.py` のモジュール一覧に両方が既定で登録されていることなど。
- `test_default_and_required.py` — 「このキーを省略するとどうなるか」への 2 つの答えである `KeySchema.default` / `.required`: Detail パネルは 1 行で表示するため、既定値があることと既定値がないことを同時に主張するスキーマがないこと。あわせて、その行が各場合をどう表示するか（既定値は `required` より優先、どちらもなければ何も表示しない）。
- `test_variant_schema.py` — サフィックス付きの派生ファイルが基本の辞書のスキーマで答え、食い違うヘッダや include される断片は何も得ないこと。
- `test_vendored_modules.py` — `GENERATED by foamlore` のバナーを持つすべてのモジュールが存在し、**git で追跡されており**、`../foamlore/fode-schemas/` とバイト単位で一致すること（foamlore のチェックアウトがなければ比較はスキップ）。git のチェックがあるのは、`_laminar_models.py` がかつて正しくベンダリングされたまま追跡されていなかったためです。

**`tests/tools/`**
- `test_capture_dialog.py` — `tools/capture_dialog.py` のショット一覧を素のデータとして検証するテストで、`test_window_state.py` のスクリーンショット spec 検査に対応するものです: 名前がキーと一致すること、同じファイルへ書き込むショットが 2 つないこと、すべてのショットが両言語のギャラリーページから参照されていて画像も存在すること、`requires()` がトレースバックではなく不足しているものを名指しすること。ショットは入力の出どころ（撮影マシンかリポジトリか）で分類されなど。
- `test_demo_driver_isolation.py` — テイクが収録環境に手を出さないことの確認: `XDG_CONFIG_HOME` がテイクのスクラッチディレクトリへ向き `$HOME` は触られないこと、同梱の ParaView プロファイルが存在して Getting Started スプラッシュを抑止し ParaView が見つける場所へコピーされること、そして — QSettings は 最初の構築時にパスをキャッシュするためサブプロセスで — ファイルダイアログに Home のショートカットが出ずなど。
- `test_demo_specs.py` — `tools/demo_specs.json` のシーンを素のデータとして検証します。この中で最も費用対効果が高い検査です。
- `test_reader_paths.py` — バージョンタグ・オラクルの FoDE 側である `tools/fode-reader-paths.json`: 現在のレジストリに対して最新であること（タグが変わった瞬間に `keys` が古くなるため）、foamlore と取り決めた形であること、読み取り箇所のパスが実際の OpenFOAM ツリーに存在すること（`lnInclude` は除外）、実行時に組み立てられるキーと構造的なキーが黙って落とされずにフラグ付きで残ること。

## 更新候補

将来のリリースに向けたメモ（現時点では未計画）。2026-11-14 の見直しで重要度と手間をもとに 3 段階に分けました。各段階の中は、おおむね取りかかる順です。

### 次に行う

- **単独の `meshQualityDict` のスキーマ** — `schemas/snappy_hex_mesh_dict/_mesh_quality.py` は `snappyHexMeshDict` の中の写しについて全キーをすでに記述しています。`system/meshQualityDict` にも応答させるには `TARGET_FILES` タプルを足すだけです（修飾キーが、トップレベルに置かれたファイルでも解決されることの確認を添えて）。

- **`block_mesh_extractor.py` のレガシーな生テキスト境界ブロックフォールバック（~164〜250 行目）を削除する。** 到達可能性は推測ではなく実測済みです: v2512 tutorials の `blockMeshDict` 489 件のうち、到達したのはちょうど 1 件（`compressible/rhoPimpleFoam/laminar/helmholtzResonance`）で、しかもそこでの出力は*誤っていました* — 正規表現の走査が先頭の `#include` をパッチ名として読み、次のパッチの面を割り当てて `outlet` を失っていました。このトリガーはパーサ側で修正済み（`boundary ( … )` 内のディレクティブは `directive_entry` の子ノードになる）で、フォールバックはコーパス全体で 0 ヒットです。3-D ビューアが黙って誤る境界リストより、目に見えて落とす境界リストのほうがよいので、テストのない受け皿を残さず削除します。

### 価値はあるが設計が要る

- **ケースのフォークとリリースを判定して活用する**（旧「インクルード解決におけるバージョン対応の `etc` 選択」を統合）。入力は 2 つそろいました: 辞書の先頭バナー（`Version: v2606` / `www.openfoam.com`）と、Check Case が用意した、インストールの `etc/bashrc` からフォークとバージョンを読む `services/case_check.installation_info` です。`docs/OPENFOAM_VERSIONS.md` にはリリース間で何が変わるかを記録しています。使い道を効果の大きい順に: `#includeEtc` を最新ではなくケースに合うインストールに対して解決する（今の `include_scan.foam_etc_dirs()` は対象を知り得ないため、古いリリース向けに書かれたケースでも、ユーザーがインストールを選ばない限り最新の `etc` が黙って使われます）。Detail ペインで、ケース自身のリリースを含まない `supported_in` をグレーアウトし、ユーザーが文字列を突き合わせなくて済むようにする。そして FoDE が OpenFOAM を読み込まずに起動されたとき、Check Case のフォーク対応の辞書チェックに推定値を与える。バナーがない・古い場合の代替は、ケースごとに記憶した選択です。

- **初心者が触れるキーへの注記**（`nNonOrthogonalCorrectors`、緩和係数、`nOuterCorrectors`、`maxCo`）: 典型的な値と変えるべき場合を、スキーマの説明に加えます。少しずつ、出典を示せるものからだけ行います。誤った助言は何もないより悪いためです。 プロジェクトとしてではなく、継続的な作業として扱うのがよいでしょう — リリースごとに数個のキーを、それぞれ出典付きで。

- **`#{ … #}` を 1 つの不透明なレキサトークンにする** — 下の[パーサに残る 4 つの失敗パターン](#保留)の最大のもの: v2606 のチュートリアル 27 ファイルで 153 件のエラー。主に `blockMeshDict`（13）と `controlDict`（11）で、`code #{ … #};` の中の C++ が辞書テキストとしてトークン化され、被害がファイル末尾まで波及するためです。ブロックを 1 つのトークンとして出すレキサの状態は追加的な変更で、ラウンドトリップのコーパスで安全に確かめられます。これだけを単独で行い、ディレクティブの統一レジストリ（下の保留）は、ほかに必要になったときに続ければ十分です。

- **`foam/parser.py` の 4 つの括弧ブロック振り分けテーブルの統合** — `_NAMED_BLOCK_PARAMS`、`_ANONYMOUS_BLOCK_PARAMS`、`_OPTIONAL_NAMED_BLOCK_PARAMS`、`_POSITIONAL_BLOCK_PARAMS` はそれぞれ `(...)` で区切られたブロックに対する異なる先読み/振り分け経路を担っている。個別に参照される 4 つの辞書ではなく、先読みフラグ付きのエントリ名をキーとする 1 つのテーブルにまとめられる可能性がある。 名前付きの `actions ( heater {{ … }} )`（6 ファイルで 10 件のエラー。下の失敗パターンの表を参照）と一緒に行います。同じ「名前は任意」の先読みであり、単独で対応すると 5 本目の経路が増えるためです。

- **ファイル一覧におけるインクルードの再帰的解決** — ビューア側は**完了済み**。`foam/include_expand.py` が 3-D 抽出用のマージ済みツリーを作る際、深さ上限の範囲で再帰的にインクルードを辿る（「3-D ビューア向けのインクルード展開」を参照）。残るのは一覧側で、`services/include_scan.py` は今も `list_case_files` が返したファイルから 1 段階だけインクルードを辿る。訪問済み集合を持つ深さ制限付きの再帰が素直な拡張形であり、これは机上の話ではない。`compressible/rhoPimpleFoam/RAS/annularThermalMixer` では `constant/caseSettings` 自身がインクルード対象であるため、その中の `#include "<constant>/boundaryConditions"` は辿られず、`constant/boundaryConditions` は一覧に出ない（代わりに `constant` ヘッダーに `[+]` が付く）。`etc/caseDicts/*.cfg` も相互にインクルードし合う。

- **残りの未カバーの辞書のスキーマモジュール** — 一覧している 105 個の名前のうち、モジュールがあるのは 9 個です（フォークで改名された辞書は綴りごとに数えます）。`docs/SCHEMA_CANDIDATES.md` が残りを実測の出現頻度とキー数で順位付けし、FoDE で手書きするものと foamlore で生成するものに理由付きで分けています。`meshQualityDict` はほぼ無償なので上の「次に行う」に入れました。

- **ログの助言を本物の Foundation のログで確かめる** — `services/log_advice.py` の Foundation 向けパターンは、Foundation のバイナリがインストールされていなかったため、Foundation-12 のソースとしか照合していません。OpenFOAM-12 を一度ビルドし、cavity のコピーを同じように壊せば、`tests/services/test_log_advice.py` で組み立てている文字列を `tests/fixtures/logs/v2606/` と並ぶ本物のログに置き換えられます。大部分は計算機の時間です。

- **Check Case のソルバー → 辞書の表を広げる** — `services/case_check.SOLVER_DICTIONARIES` は非圧縮性のソルバー群しか扱いません。作ったときと同じ方法で広げます: 各ソルバーのチュートリアルが必ず持つ辞書を計測し、欠けると実際のソルバーが失敗することを確かめ、コーパスの防波堤（`tests/services/test_case_check_corpus.py`）を静かなまま保ちます。

- **リージョンのサブディレクトリ** — サフィックス付きの派生ファイル（`_list_suffixed_variants`）と Check Case のメッシュ生成前の境界チェックは、`system/` と `constant/` だけを見て、`system/<region>/` と `constant/<region>/` は見ません。優先度は低め: マルチリージョンのケースが初心者の最初の一件になることはまれです。

### 保留

必要になったときに見直します。

- **3D のピッキング → ツリー** — ツリー → 3D の方向は実装済み（前述の「ブロックの選択と CRUD」を参照）。逆方向、つまりビューア上でブロックをクリックして該当ツリー行を選択する機能は、本コードベースで初の VTK ピッキング利用になる。 オフスクリーンでの試験が難しいので、ユーザーからの要望を待ちます。

- **その他の位置指定リストに対する CRUD** — 追加/複製/削除は `block_entry` 行では有効になったが、`region_entry`、`boundary_entry`、`action_entry` は引き続き親が `dictionary` であることを条件としている（`ui/mixins/_tree_crud_ops.py`）。この 3 つは*名前付き*であり、新規追加エントリの名前を与える手段（プロンプト、またはプレースホルダに対するインライン編集）がそれぞれ必要になるため、ブロックと一緒には対応していない。 最もよくある用途は、境界の編集ダイアログがすでに満たしています。

- **比較モードでのサイドバイサイドの参照*テキスト*エディタ** — 比較モードは現在、参照ケースを読み取り専用の*ツリー*として表示している。参照ファイルのテキストを読み取り専用エディタとしてメインの Editor タブの横に表示できれば、キーや値を自由にコピー＆ペーストできる（現状、例のケースについては非モーダルな Find OpenFOAM Examples のプレビュー + 「選択範囲をコピー」で代用できるが、任意の参照ケースには使えない）。比較モードの更新の一環として再検討する。

- **`schemas/turbulence_structure.py` にファイル別のバージョンタグを与える**（保留: 影響するのは古い `turbulenceProperties` を持つ Foundation 8 以降の利用者だけで、修正は実際の作業量がある）。 誤ったファイルに出る問題のほうは*完了しました*。`KeySchema.only_in_files` と当該モジュール内の導出により、そのキーを支持するどのリリースも読まない辞書には現れなくなりました。残っているのはタグ自体です。
  - *問題。* このモジュールは `TARGET_FILES = ("turbulenceProperties", "momentumTransport")` を宣言しているため、`_build_file_key_schemas` が同一のテーブルを両ファイルへマージします。これは `docs/foamlore-schema-spec.md` の項目 2 が記録している落とし穴そのものであり、*生成側*の乱流モジュールが共有の `_turbulence_coeffs.py` の上に薄いファイル別モジュールとして分割されている理由でもあります。手書きモジュールには同じ処置が施されないままでした。
  - *実測した影響。* バージョンタグのオラクルによるファイル別の範囲は、`constant/turbulenceProperties` について `Foundation v7` と OpenCFD、`constant/momentumTransport` について `Foundation v8-v14` ですが、ここのキーはすべて `BOTH` を持ちます。108 キーが該当し、完了したオラクルの測定（`docs/foamlore-schema-spec.md` 項目 11）による数字です。つまり Foundation v12 の利用者が古い `constant/turbulenceProperties` を開くと、そのキーが v12 で使えると表示されます。v12 は代わりに `momentumTransport` を読み、このファイルを読みません。
  - *修正方針。* モジュールの分割でも 108 件の手作業による再タグ付けでもありません。ラベルをリリースの*集合*に変え、`_turbulence_coeffs.build_schemas` が `_TARGET_CHECKOUTS` から既に行っているのと同じ方式でファイルごとに導出する必要があります。ラベルからラベルへの手書き対応表も検討しましたが却下しました。275 箇所のタグにわたって交差を手で符号化することになり、次のリリースで陳腐化するからです。

- **ディレクティブの統一レジストリ** — `foam/lexer.py` は今も全 `#word` を 1 種類の `DIRECTIVE` トークンに潰しており、`foam/include_resolver.py` がコードベース初のディレクティブ別知識になっている。`#remove`、`#calc`、`#codeStream`、`#eval` とインクルード系を 1 つのテーブルにまとめれば、レキサーの一律トークンとテキストを読み直す 1 モジュールという現在の分裂を解消できる。

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

- **`shape_mesh.make_shape_mesh` のジオメトリ振り分けの型付け**(Qt に依存しないジオメトリが `ui/panels/shape_mesh.py` へ分離された際に `block_mesh_renderer._make_shape_mesh` から移動)— 現状は呼び出し側で dict のキー（`box`、`boxes`、`centre`+`radius`、`p1`+`p2`+`radius`、`origin`+`i`+`j`+`k`、`stl_path`、`planePoint`+`planeNormal` など）に対して duck-typing で振り分けており、両方のリファクタで意図的にそのままにした。型付きのジオメトリ共用体（例: 種類ごとの dataclass）があれば、実行時のキーの有無に頼らず mypy で振り分けをチェックできる。

- **Undo の堅牢化** — Undo/Redo とサンプリング機能のコードレビューで挙がった項目（いずれも「確定」ではなく「可能性あり」と判断）。Undo に次に手を入れる変更に合わせて取り込みます:
  - **`UndoState.op_active` のリセットタイミングが脆い**（`ui/mixins/_undo_ops.py`）— 二重チェックポイント防止ガードを `QTimer.singleShot(0, ...)` でクリアしているが、これはネストしたイベントループ（`QMessageBox`/`QDialog.exec`）内で発火する。現状、`_checkpoint_for_undo` とその変更の間にダイアログを開く呼び出し箇所はないため潜在的だが、将来そのような操作があるとモデルの `about_to_change` が変更途中の 2 つ目のスナップショットを積み（1 回の編集に 2 回の Undo が必要になる）。ガードを同期的な操作スコープに限定（例: コンテキストマネージャ）すればタイミング依存を除去できる。
  - **変更パスが Undo チェックポイントを取ることを強制する仕組みがない**（`ui/mixins/_tree_crud_ops.py`・`_tree_sync_ops.py`・`_boundary_ops.py`）— Undo のカバレッジは手動で配置した約 18 個の `_checkpoint_for_undo` 呼び出しと、`setData` 経由編集の `about_to_change` シグナルに依存している。将来、明示的な呼び出しを忘れた直接変更パスは静かに Undo 不可になる（後の Ctrl+Z がそれを飛び越す）。変更後の 1 箇所のチョークポイントで直前のシリアライズ済みテキストを差分比較するか、カバレッジテストを設ければ堅牢になる。

2026-11-14 の見直しで削除した項目（新しい理由なしに戻さないため記録します）: *セル数/グレーディングの `block_entry` 子ノード化*（使う機能がない。3-D パネルがブロックごとのセル数を表示するようになったら戻す）、*インクルードスキャンの `#codeStream` 本体認識*（C++ ヘッダーのヒューリスティックはコーパスで過不足なく、失敗しても無害）、*`_restored_dirty` がディスクを再読み込みしている*（誤動作する入力が知られておらず、すでに設計上のメモに格下げ済み）。

## 謝辞

- [PyInstaller](https://pyinstaller.org/) — スタンドアロン実行ファイルのビルドに使用。
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — `blockMeshDict` の 3D ビューア（BSD-3-Clause、オプション）。
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — テストフレームワーク。

[OpenFOAM Foundation](https://openfoam.org/) および [OpenCFD / ESI Group](https://www.openfoam.com/) をはじめ、OpenFOAM をフリーのオープンソース CFD ソフトウェアとして開発・維持してきたすべての貢献者の方々に深く感謝いたします。
