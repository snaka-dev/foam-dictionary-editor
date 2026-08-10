# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
LANGUAGE_NAME = "日本語"

TRANSLATIONS: dict[str, str] = {
    # ── window / app ──────────────────────────────────────────────────────────
    "foam dictionary editor": "foam ディクショナリエディタ",
    "Language": "言語",
    "Language Changed": "言語の変更",
    "The language will change after restarting the application.": "アプリケーションを再起動すると言語が変わります。",
    "Appearance": "外観",
    "Appearance Changed": "外観の変更",
    "Follow System": "システムに従う",
    "Light": "ライト",
    "Dark": "ダーク",
    "The theme will change after restarting the application.": "アプリケーションを再起動するとテーマが変わります。",
    "UI Scale": "UI の拡大率",
    "UI Scale Changed": "UI 拡大率の変更",
    "The interface scale will change after restarting the application.": "アプリケーションを再起動すると UI の拡大率が変わります。",

    # ── menus ─────────────────────────────────────────────────────────────────
    "Case": "ケース",
    "Open Case": "ケースを開く",
    "Open from Case Library...": "ケースライブラリから開く...",
    "Reload Case": "ケースを再読み込み",
    "Save Case": "ケースを保存",
    "Save as New Case...": "新しいケースとして保存...",
    "Duplicate Case...": "ケースを複製...",
    "Duplicate from Case Library...": "ケースライブラリから複製...",
    "Clean Backup Files...": "バックアップファイルを削除...",
    "Compare with Case...": "ケースと比較...",
    "Exit": "終了",
    "Settings": "設定",
    "Set Default Case Directory": "デフォルトケースディレクトリの設定",
    "Manage Case Library…": "ケースライブラリの管理…",
    "Manage Extra Files & Directories…": "追加ファイル＆ディレクトリの管理…",
    "Reset File List": "ファイルリストをリセット",
    "Manage Schema Modules": "スキーマモジュールの管理",
    "Reset Window Size": "ウィンドウサイズをリセット",
    "Restore Last Session on Startup": "起動時に前回のセッションを復元",
    "Reopen the window layout, case and files from the last time the "
    "application was closed. Unticking this keeps what is stored; use "
    "Forget Saved Session to discard it.":
        "前回アプリケーションを終了したときのウィンドウレイアウト・ケース・ファイルを復元します。"
        "チェックを外しても保存されている内容は残ります。破棄するには Forget Saved Session を使用してください。",
    "Forget Saved Session": "保存されたセッションを破棄",
    "Discard the stored window layouts, including those of the other "
    "variants. The next launch opens a default window.":
        "保存されているウィンドウレイアウトを、他のバリアントのものも含めて破棄します。"
        "次回起動時はデフォルトのウィンドウで開きます。",
    "Saved session discarded.": "保存されたセッションを破棄しました。",
    "Session restored, except: {details}": "セッションを復元しました（次を除く）: {details}",
    "Reset All Settings…": "すべての設定をリセット…",
    "View": "表示",
    "Show Type Column": "型列を表示",
    "BlockMesh 3-D Panel": "BlockMesh 3Dパネル",
    "BlockMesh 3-D Panel  (unavailable: xterm active)": "BlockMesh 3Dパネル（利用不可: xterm使用中）",
    "Tools": "ツール",
    "Launch foamMonitor to plot residuals or other data with gnuplot":
        "foamMonitor を起動し、残差などのデータを gnuplot でプロットします",
    "Restore 0/ from 0.orig": "0/ を 0.orig から復元",
    "Delete 0/ and replace it with a fresh copy of 0.orig/":
        "0/ を削除し、0.orig/ の新しいコピーで置き換えます",
    "Run blockMesh…": "blockMesh を実行…",
    "Choose options and run blockMesh in the terminal panel":
        "オプションを選択して blockMesh をターミナルパネルで実行します",
    "Run snappyHexMesh…": "snappyHexMesh を実行…",
    "Choose options and run snappyHexMesh in the terminal panel":
        "オプションを選択して snappyHexMesh をターミナルパネルで実行します",
    "Run topoSet…": "topoSet を実行…",
    "Choose options and run topoSet in the terminal panel":
        "オプションを選択して topoSet をターミナルパネルで実行します",
    "Run setFields…": "setFields を実行…",
    "Choose options and run setFields in the terminal panel — sets "
    "initial field regions in 0/ from system/setFieldsDict":
        "オプションを選択して setFields をターミナルパネルで実行します — "
        "system/setFieldsDict に従って 0/ の初期場の領域を設定します",
    "Run checkMesh…": "checkMesh を実行…",
    "Choose options and run checkMesh in the terminal panel to "
    "validate the mesh":
        "オプションを選択して checkMesh をターミナルパネルで実行し、"
        "メッシュを検証します",
    "Open Mesh in ParaView…": "メッシュを ParaView で開く…",
    "Open the case's generated mesh in ParaView (paraFoam)":
        "ケースの生成済みメッシュを ParaView (paraFoam) で開きます",
    "View Log Summary…": "ログ要約を表示…",
    "Show a condensed summary of a log.* file (blockMesh, snappyHexMesh, topoSet, setFields, checkMesh, ...)":
        "log.* ファイル (blockMesh, snappyHexMesh, topoSet, setFields, checkMesh, ...) の要約を表示します",
    "Help": "ヘルプ",
    "About Foam Dictionary Editor (FoDE)...": "Foam Dictionary Editor (FoDE) について...",
    "Keyboard Shortcuts...": "キーボードショートカット...",
    "Resources...": "リソース...",

    # ── top bar buttons / labels ──────────────────────────────────────────────
    "Save File": "ファイルを保存",
    "Save All Files": "すべてのファイルを保存",
    "Case:": "ケース:",
    "File:": "ファイル:",
    "Current case name": "現在のケース名",
    "Current file name": "現在のファイル名",
    "No case opened": "ケースが開かれていません",
    "No file loaded": "ファイルが読み込まれていません",

    # ── editor↔tree sync bar (bottom tab bar corner) ──────────────────────────
    "Apply Text to Tree": "テキストをツリーに適用",
    "Reload from Tree": "ツリーから再読み込み",
    "Re-parse the editor text and rebuild the tree above":
        "エディタのテキストを解析し直して上のツリーを再構築します",
    "Regenerate the editor text from the tree above":
        "上のツリーからエディタのテキストを生成し直します",
    "Minimize the editor pane to its tab bar": "エディタペインをタブバーまで最小化",
    "Restore the editor pane": "エディタペインを元に戻す",

    # ── View menu: pane minimize ──────────────────────────────────────────────
    "File List": "ファイル一覧",
    "Detail Pane": "詳細ペイン",
    "Editor / Terminal Pane": "Editor / Terminal ペイン",
    "Editor Pane": "Editor ペイン",
    "Panes (show / minimize)": "ペイン（表示 / 最小化）",
    "Minimize a pane": "ペインを最小化",

    # ── tree area ─────────────────────────────────────────────────────────────
    "Filter keys…": "キーをフィルタ…",
    "Auto-scroll editor": "エディタ自動スクロール",
    "Auto-scroll editor (stale)": "エディタ自動スクロール（古い情報）",
    "When checked, the editor scrolls to the selected tree entry.\n"
    "The span highlight is always shown regardless of this setting.":
        "チェックすると、選択したツリーエントリへエディタがスクロールします。\n"
        "スパンハイライトはこの設定に関係なく常に表示されます。",
    "Source lines are stale — the editor text has changed since the last parse.\n"
    "Apply Text to Tree to re-enable jump-to-line and span highlight.":
        "ソース行が古くなっています — 最後の解析以降にエディタのテキストが変更されました。\n"
        "「テキストをツリーに適用」を実行して行ジャンプとスパンハイライトを再有効にしてください。",

    # ── tab labels ────────────────────────────────────────────────────────────
    "Editor": "エディタ",
    "Tree": "ツリー",
    "Boundary": "境界",
    "BlockMesh": "BlockMesh",
    "Extra Files": "追加ファイル",
    "Extra Directories": "追加ディレクトリ",
    "My Links": "マイリンク",
    "OpenFOAM": "OpenFOAM",

    # ── diff bar ──────────────────────────────────────────────────────────────
    "Side by side": "並べて表示",
    "Show BlockMesh 3-D view alongside the tree (side-by-side)":
        "BlockMesh 3D ビューをツリーの横に並べて表示します",
    "Clear": "クリア",
    "Select Reference Case Directory": "参照ケースディレクトリを選択",
    "Comparing with: <b>{name}</b>  ({directory})": "{name} と比較中  ({directory})",
    "Diff cleared.": "差分をクリアしました。",
    "Diff: {rel} not found in reference case.": "差分: {rel} が参照ケースに見つかりません。",
    "Diff: {n} difference{s} in {rel}.": "差分: {rel} に {n} 件{s}の差異。",
    "Diff: could not parse {rel} in the reference case.":
        "差分: 参照ケースの {rel} を解析できませんでした。",
    "Diff: {n} reference file(s) could not be parsed and were skipped.":
        "差分: 参照ケースの {n} 個のファイルを解析できずスキップしました。",

    # ── status bar ────────────────────────────────────────────────────────────
    "Tree changes applied to text editor": "ツリーの変更をテキストエディタに適用しました",
    "No unsaved files.": "未保存のファイルはありません。",
    "File list reset to default.": "ファイルリストをデフォルトにリセットしました。",
    "No extra files configured for this case.": "このケースには追加ファイルが設定されていません。",
    "Paste failed: value format not accepted": "貼り付け失敗: 値の形式が受け付けられません",
    "Copied: {text}": "コピーしました: {text}",
    "Apply Text to Tree to enable editor-to-tree sync": "「テキストをツリーに適用」でエディタとツリーの同期を有効にしてください",
    "No tree entry found for line {line}": "行 {line} に対応するツリーエントリが見つかりません",
    "Entry is hidden by the current filter": "エントリが現在のフィルタで非表示になっています",
    "Apply Text to Tree to re-enable jump-to-line": "「テキストをツリーに適用」で行ジャンプを再有効にしてください",
    "No source location — entry was added or modified in the tree": "ソース位置なし — エントリはツリーで追加または変更されました",
    "Cannot apply: '{path}' is not a dictionary in the current case":
        "適用できません: '{path}' は現在のケースでは辞書ではありません",
    "'{key}' is already present in the current case": "'{key}' は現在のケースに既に存在します",
    "Applied '{key}' from reference case": "参照ケースから '{key}' を適用しました",
    "Inserted '{key}' from reference case": "参照ケースから '{key}' を挿入しました",
    "Case reloaded: {path}": "ケースを再読み込みしました: {path}",
    "Duplicated to: {dest}": "複製しました: {dest}",
    "Saved as new case: {dest}": "新しいケースとして保存しました: {dest}",
    "Loaded: {path}": "読み込みました: {path}",
    "Parsed: {path} — {n} unrecognized {entries}": "解析しました: {path} — {n} 件の未認識{entries}",
    "Parsed successfully: {path}": "正常に解析しました: {path}",
    "Parse warning: {e}": "解析時の警告: {e}",
    "Script file — text editing only: {path}": "スクリプトファイル — テキスト編集のみ: {path}",
    "Script file — tree editing unavailable": "スクリプトファイルのためツリー編集は利用できません",
    "Text file — no dictionary tree: {path}": "テキストファイル — 辞書ツリーはありません: {path}",
    "Text file — tree editing unavailable": "テキストファイルのためツリー編集は利用できません",
    "case root": "ケースルート",

    # ── included files (#include resolution) ──────────────────────────────────
    "included files": "インクルードファイル",
    "included from {origin}": "インクルード元: {origin}",
    "read-only": "読み取り専用",
    "read-only — outside the case directory": "読み取り専用 — ケースディレクトリの外",
    "Read-only file — outside the case directory: {name}": "読み取り専用ファイル — ケースディレクトリの外: {name}",
    "Read-only file — tree editing unavailable": "読み取り専用ファイルのためツリー編集は利用できません",
    "Open Included File": "インクルードファイルを開く",
    "resolves to {path}": "解決先: {path}",
    "Include not found: {target}": "インクルードが見つかりません: {target}",
    "Optional include not present: {target}": "省略可能なインクルードは存在しません: {target}",
    "No OpenFOAM installation found — #includeEtc/#includeFunc cannot be resolved.": "OpenFOAM のインストールが見つかりません — #includeEtc/#includeFunc は解決できません。",
    "Copy into case...": "ケースにコピー...",
    "Copy into Case": "ケースにコピー",
    "Copy {name} into the case as:": "{name} をケース内に次の名前でコピー:",
    "Copied into case: {name}": "ケースにコピーしました: {name}",
    "Destination must be inside the case directory.": "コピー先はケースディレクトリ内である必要があります。",
    "Copy Error": "コピーエラー",
    "Could not copy file:\n{e}": "ファイルをコピーできませんでした:\n{e}",

    "Saved: {path}": "保存しました: {path}",
    "Saved: {path} — {n} unrecognized {entries}": "保存しました: {path} — {n} 件の未認識{entries}",
    "Saved and parsed: {path}": "保存して解析しました: {path}",
    "Saved, but parse failed: {e}": "保存しましたが、解析に失敗しました: {e}",
    "Saved {n} file(s).": "{n} 件のファイルを保存しました。",
    "Added {n} file(s) to the file list.": "{n} 件のファイルをファイルリストに追加しました。",
    "File name must not be empty.": "ファイル名を入力してください。",
    "File name must not contain path separators.": "ファイル名にパス区切り文字を含めないでください。",
    "File already exists: {name}": "ファイルが既に存在します: {name}",
    "Created: {name}": "作成しました: {name}",
    "Backup created: {rel}{suffix}": "バックアップを作成しました: {rel}{suffix}",
    " (includes unsaved edits)": " (未保存の編集を含む)",
    "Removed from extra files: {name}": "追加ファイルから削除しました: {name}",
    "Added directory: {dir}/": "ディレクトリを追加しました: {dir}/",
    "Removed directory from file list: {dir}/": "ファイルリストからディレクトリを削除しました: {dir}/",
    "Deleted: {name}": "削除しました: {name}",
    "Duplicated: {src} → {dst}": "複製しました: {src} → {dst}",
    "Deleted {n} backup file(s).": "{n} 件のバックアップファイルを削除しました。",
    "Boundary updated: {file} / {patch}": "境界を更新しました: {file} / {patch}",
    "Created boundary: {field} / {patch}": "境界を作成しました: {field} / {patch}",
    "Pasted to {file} / {patch}": "{file} / {patch} に貼り付けました",
    "Deleted boundary: {file} / {patch}": "境界を削除しました: {file} / {patch}",
    "Renamed '{old}' → '{new}' in {n} file(s).": "'{old}' を '{new}' に {n} 件のファイルでリネームしました。",
    "Deleted BoundaryField '{patch}' from {n} file(s).": "'{patch}' を {n} 件のファイルから削除しました。",
    "Added BoundaryField '{patch}' to {n} file(s). Edit each cell to add boundary condition content.":
        "'{patch}' を {n} 件のファイルに追加しました。各セルを編集して境界条件の内容を追加してください。",

    # ── QMessageBox titles ────────────────────────────────────────────────────
    "Unsaved Changes": "未保存の変更",
    "No Case Open": "ケースが開かれていません",
    "Destination Already Exists": "保存先が既に存在します",
    "Duplicate Error": "複製エラー",
    "Save As Error": "名前を付けて保存エラー",
    "Duplicate Complete": "複製完了",
    "Possibly Not an OpenFOAM Case": "OpenFOAMケースではない可能性があります",
    "Directory Saved": "ディレクトリを保存しました",
    "Size Reset": "サイズをリセットしました",
    "Case Library Empty": "ケースライブラリが空です",
    "Select Library": "ライブラリを選択",
    "Error": "エラー",
    "Large Non-Dictionary File": "非ディクショナリファイル（大）",
    "'{name}' does not appear to be an OpenFOAM dictionary ({size} KB).\nThe tree view will not be available.\nLoading may take a while — the application will not respond during this time.\n\nOpen anyway?":
        "'{name}' はOpenFOAMのディクショナリではない可能性があります（{size} KB）。\nツリービューは利用できません。\n読み込みに時間がかかる場合があります — この間、アプリケーションは応答しなくなります。\n\n開きますか？",
    "Loading large file: {name} — please wait…":
        "大きいファイルを読み込み中: {name} — しばらくお待ちください…",
    "Parse Warning": "解析警告",
    "Saved with Parse Warning": "解析警告付きで保存",
    "Save Error": "保存エラー",
    "Save All - Partial Failure": "すべて保存 - 部分的な失敗",
    "New File": "新しいファイル",
    "Duplicate File": "ファイルを複製",
    "Backup Error": "バックアップエラー",
    "Create File Error": "ファイル作成エラー",
    "Delete File": "ファイルを削除",
    "Delete Error": "削除エラー",
    "Delete Errors": "複数の削除エラー",
    "Cannot Delete": "削除できません",
    "Delete Directory": "ディレクトリを削除",
    "Duplicate Directory": "ディレクトリを複製",
    "Delete Entry": "エントリを削除",
    "Restore Failed": "復元に失敗",
    "Edit Error": "編集エラー",
    "Boundary Not Found": "境界が見つかりません",
    "Parse Error": "解析エラー",
    "Paste Error": "貼り付けエラー",
    "Delete BoundaryField": "BoundaryField を削除",
    "Add BoundaryField": "BoundaryField を追加",
    "Confirm Reset": "リセットの確認",
    "No Selection": "選択なし",
    "Reset Complete": "リセット完了",
    "Invalid File": "無効なファイル",
    "Invalid Directory": "無効なディレクトリ",
    "Already Added": "既に追加済み",
    "Missing URL": "URLが入力されていません",
    "No 0.orig/ to restore": "復元元の 0.orig/ がありません",
    "Restore 0/ from 0.orig/?": "0/ を 0.orig/ から復元しますか?",
    "ParaView not found": "ParaView が見つかりません",

    # ── QMessageBox messages ──────────────────────────────────────────────────
    "Text editor has unsaved changes. Discard them?": "テキストエディタに未保存の変更があります。破棄しますか？",
    "Please open a case first.": "最初にケースを開いてください。",
    "Reloading will discard unsaved changes in {count} file(s).\n\nReload from disk?":
        "{count} 件のファイルの未保存の変更が破棄されます。\n\nディスクから再読み込みしますか？",
    "There are unsaved changes. Save all files before duplicating?":
        "未保存の変更があります。複製前にすべてのファイルを保存しますか？",
    "The following directory already exists:\n{dest}\n\nOverwrite?":
        "次のディレクトリが既に存在します:\n{dest}\n\n上書きしますか？",
    "Could not remove existing directory:\n{e}": "既存のディレクトリを削除できませんでした:\n{e}",
    "Failed to duplicate case:\n{e}": "ケースの複製に失敗しました:\n{e}",
    "Case duplicated to:\n{dest}\n\nOpen the duplicated case now?":
        "ケースを複製しました:\n{dest}\n\n今すぐ複製したケースを開きますか？",
    "Some edited files could not be written:\n{errors}": "一部の編集済みファイルを書き込めませんでした:\n{errors}",
    "No directories are registered in the Case Library.\n\n"
    "Add directories via Settings > Manage Case Library...":
        "ケースライブラリにディレクトリが登録されていません。\n\n"
        "設定 > ケースライブラリの管理... でディレクトリを追加してください。",
    "Choose a library to browse:": "参照するライブラリを選択してください:",
    "Default case directory set to:\n{directory}\n\n"
    "This directory will be used as the initial location when opening cases.":
        "デフォルトケースディレクトリを設定しました:\n{directory}\n\n"
        "このディレクトリはケースを開く際の初期場所として使用されます。",
    "Reset window size to default ({w}x{h})?": "ウィンドウサイズをデフォルト（{w}x{h}）にリセットしますか？",
    "Window size has been reset to default ({w}x{h}).": "ウィンドウサイズをデフォルト（{w}x{h}）にリセットしました。",
    "Text was loaded, but tree update failed.\n\n{e}\n\nYou can continue editing in the text editor.":
        "テキストを読み込みましたが、ツリーの更新に失敗しました。\n\n{e}\n\nテキストエディタでの編集は続けられます。",
    "File was saved as text, but tree refresh failed.\n\n{e}":
        "ファイルをテキストとして保存しましたが、ツリーの更新に失敗しました。\n\n{e}",
    "Failed to save the following files:\n{files}": "次のファイルの保存に失敗しました:\n{files}",
    "Remove all user-added files and directories from the file list for this case?\n"
    "The .foam-editor-files.json file will be deleted.":
        "このケースのファイルリストからユーザーが追加したファイルとディレクトリをすべて削除しますか？\n"
        ".foam-editor-files.json ファイルが削除されます。",
    "File name (will be created in {group}/):" : "ファイル名（{group}/ に作成されます）:",
    "New file name (in {dir}/):" : "新しいファイル名（{dir}/ 内）:",
    "Could not read file:\n{e}": "ファイルを読み込めませんでした:\n{e}",
    "Could not write backup:\n{e}": "バックアップを書き込めませんでした:\n{e}",
    "Backup && Delete": "バックアップして削除",
    "Delete": "削除",
    "This action cannot be undone.": "この操作は元に戻せません。",
    "This file has unsaved changes.\nThis action cannot be undone.":
        "このファイルには未保存の変更があります。\nこの操作は元に戻せません。",
    "{name} has unsaved changes.": "{name} に未保存の変更があります。",
    "How would you like to duplicate this file?": "このファイルをどのように複製しますか？",
    "Save and Duplicate": "保存して複製",
    "Duplicate with Unsaved Changes": "未保存の変更を含めて複製",
    "Could not write file:\n{e}": "ファイルを書き込めませんでした:\n{e}",
    "Duplicate '{src}/' to '{dst}/'?\n\nSource:      {src_path}\nDestination: {dst_path}":
        "'{src}/' を '{dst}/' に複製しますか？\n\nソース:      {src_path}\n保存先: {dst_path}",
    "Failed to duplicate directory:\n{e}": "ディレクトリの複製に失敗しました:\n{e}",
    "The '0.orig' directory does not exist.\n\nDeletion aborted to prevent data loss.":
        "'0.orig' ディレクトリが存在しません。\n\nデータ損失を防ぐため削除を中止しました。",
    "Delete the '{group}/' directory and all its contents?\n\n{path}\n\nThis cannot be undone.":
        "'{group}/' ディレクトリとその内容をすべて削除しますか？\n\n{path}\n\nこの操作は元に戻せません。",
    "Could not delete directory:\n{e}": "ディレクトリを削除できませんでした:\n{e}",
    "Could not delete file:\n{e}": "ファイルを削除できませんでした:\n{e}",
    "Some files could not be deleted:\n{errors}": "一部のファイルを削除できませんでした:\n{errors}",
    "Could not copy case files:\n{e}": "ケースファイルをコピーできませんでした:\n{e}",
    "The selected directory does not contain 'system' or 'constant':\n\n{directory}\n\n"
    "This may not be a valid OpenFOAM case.\nOpen anyway?":
        "選択したディレクトリには 'system' または 'constant' が含まれていません:\n\n{directory}\n\n"
        "有効な OpenFOAM ケースでない可能性があります。\nそれでも開きますか？",
    "Delete '{node_name}'?": "'{node_name}' を削除しますか？",
    "Undo Tree Edit\tCtrl+Z": "ツリー編集を元に戻す\tCtrl+Z",
    "Redo Tree Edit\tCtrl+Shift+Z": "ツリー編集をやり直す\tCtrl+Shift+Z",
    "Undo Tree Edit": "ツリー編集を元に戻す",
    "Redo Tree Edit": "ツリー編集をやり直す",
    "Nothing to undo": "元に戻す操作はありません",
    "Nothing to redo": "やり直す操作はありません",
    "Undid tree change": "ツリーの変更を元に戻しました",
    "Redid tree change": "ツリーの変更をやり直しました",
    "{msg} (+{n} more file(s))": "{msg}（他 {n} ファイル）",
    "Could not parse the uncommented text:\n\n{e}": "コメントを外したテキストを解析できませんでした:\n\n{e}",
    "No entries found after removing comment markers.": "コメント記号を除去した後にエントリが見つかりませんでした。",
    "Could not apply the value to the selected node.": "選択したノードに値を適用できませんでした。",
    "Field Type must not be empty.": "フィールドタイプを入力してください。",
    "Patch '{name}' not found in {file}.": "'{name}' が {file} に見つかりません。",
    "Could not parse patch content:\n{e}": "パッチの内容を解析できませんでした:\n{e}",
    "No boundaryField found in {field}.": "{field} に boundaryField が見つかりません。",
    "Could not parse copied content:\n{e}": "コピーしたコンテンツを解析できませんでした:\n{e}",
    "No boundaryField in {file}.": "{file} に boundaryField がありません。",
    "Delete '{patch}' from {n} file(s)?\n\n{files}": "'{patch}' を {n} 件のファイルから削除しますか？\n\n{files}",
    "An empty entry will be added to {n} field file(s).\n"
    "Edit each cell to add boundary condition content.\n\nProceed?":
        "{n} 件のフィールドファイルに空のエントリを追加します。\n"
        "各セルを編集して境界条件の内容を追加してください。\n\n続けますか？",
    "Select which settings to reset to default values.\nThis action cannot be undone.":
        "デフォルト値にリセットする設定を選択してください。\nこの操作は元に戻せません。",
    "Please select at least one option to reset.": "リセットするオプションを少なくとも1つ選択してください。",
    "Are you sure you want to reset:\n\n{items}\nThis action cannot be undone.":
        "次の設定をリセットしてもよろしいですか:\n\n{items}\nこの操作は元に戻せません。",
    "Please restart the application for all changes to take effect.":
        "すべての変更を反映させるには、アプリケーションを再起動してください。",
    "Please select a file to remove.": "削除するファイルを選択してください。",
    "Please select a directory to remove.": "削除するディレクトリを選択してください。",
    "Please select a directory inside the case folder.": "ケースフォルダ内のディレクトリを選択してください。",
    "'{rel}' is already in the directory list.": "'{rel}' は既にディレクトリリストに含まれています。",
    "Please enter a URL.": "URLを入力してください。",
    "No matching boundary entries found in loaded files.": "読み込まれたファイルに一致する境界エントリが見つかりません。",
    "New patch name:": "新しいパッチ名:",
    "Patch '{name}' already exists in the boundary view.": "パッチ '{name}' は境界ビューに既に存在します。",
    "Open": "開く",
    "This case has no 0.orig/ directory to restore 0/ from.":
        "このケースには 0/ の復元元となる 0.orig/ ディレクトリがありません。",
    "This will delete 0/ and replace it with a fresh copy of "
    "0.orig/, discarding any edits made directly to 0/. Continue?":
        "0/ を削除して 0.orig/ の新しいコピーで置き換え、0/ に直接加えた編集を"
        "破棄します。続行しますか?",
    "This case already has results in: {dirs}.":
        "このケースには既に結果があります: {dirs}",
    "Re-running blockMesh will regenerate the mesh and may "
    "invalidate those results.":
        "blockMesh を再実行するとメッシュが再生成され、これらの結果が無効になる"
        "可能性があります。",
    "Re-running snappyHexMesh will regenerate the mesh and may "
    "invalidate those results.":
        "snappyHexMesh を再実行するとメッシュが再生成され、これらの結果が無効になる"
        "可能性があります。",
    "Re-running topoSet will regenerate cell/face sets and may "
    "invalidate those results.":
        "topoSet を再実行するとセル/面セットが再生成され、これらの結果が無効になる"
        "可能性があります。",
    "Neither paraFoam nor paraview could be found on PATH.":
        "PATH 上に paraFoam も paraview も見つかりませんでした。",

    # ── context-menu items ────────────────────────────────────────────────────
    "Copy Value\tCtrl+C": "値をコピー\tCtrl+C",
    "Paste Value\tCtrl+V": "値を貼り付け\tCtrl+V",
    "Add Entry After": "後にエントリを追加",
    "Add Child Entry": "子エントリを追加",
    "Duplicate": "複製",
    "Comment Out": "コメントアウト",
    "Restore from Comment": "コメントから復元",
    "Edit": "編集",
    "Create Entry": "エントリを作成",
    "Copy": "コピー",
    "Paste": "貼り付け",
    "Rename Boundary...": "境界名を変更...",
    "Copy as Markdown": "Markdownとしてコピー",
    "Copy as CSV": "CSVとしてコピー",
    "Save File\tCtrl+S": "ファイルを保存\tCtrl+S",
    "Remove from extra files": "追加ファイルから削除",
    "Duplicate...": "複製...",
    "Create Backup": "バックアップを作成",
    "Delete file...": "ファイルを削除...",

    # ── detail panel ──────────────────────────────────────────────────────────
    "No item selected": "選択なし",
    "Apply Value": "値を適用",
    "Apply Field Value": "フィールド値を適用",
    "Key": "キー",
    "Type": "型",
    "Key Help": "キーのヘルプ",
    "Key Supported In": "対応バージョン",
    "Key Note": "キーのメモ",
    "Value": "値",
    "Choices": "選択肢",
    "Choice Help": "選択肢のヘルプ",
    "Choice Supported In": "選択肢の対応バージョン",
    "Choice Note": "選択肢のメモ",
    "Field Type": "フィールドタイプ",
    "Field Name": "フィールド名",
    "Select a suggested value or type a custom value.": "推奨値を選択するかカスタム値を入力してください。",

    # ── boundary view panel ───────────────────────────────────────────────────
    "Transpose": "転置",
    "Swap rows (fields) and columns (patches)": "行（フィールド）と列（パッチ）を入れ替え",
    "When checked, clicking a cell opens its file in the editor\nand scrolls to that boundary entry.":
        "チェックすると、セルのクリックでエディタにファイルを開き、その境界エントリへスクロールします。",
    "Copy Table": "テーブルをコピー",
    "Directory:": "ディレクトリ:",
    "Lines per cell:": "セルあたりの行数:",
    "Number of lines to display per cell": "セルあたりの表示行数",
    "Delete BoundaryField  '{patch}'": "BoundaryField '{patch}' を削除",
    "Rename Boundary  '{patch}'...": "境界名 '{patch}' を変更...",
    "Add BoundaryField...": "BoundaryField を追加...",

    # ── file list panel ───────────────────────────────────────────────────────
    "Changed files only": "変更済みファイルのみ",
    "Manage extra files…": "追加ファイルを管理…",

    # ── dialogs ───────────────────────────────────────────────────────────────
    "About Foam Dictionary Editor (FoDE)": "Foam Dictionary Editor (FoDE) について",
    "Version {v}": "バージョン {v}",
    "Close": "閉じる",
    "Cancel": "キャンセル",
    "OK": "OK",
    "Select All": "すべて選択",
    "Deselect All": "すべて選択解除",
    "Browse...": "参照...",
    "(incomplete)": "（未入力）",
    "Add Selected ({n})": "選択済みを追加 ({n})",
    "Add Directory...": "ディレクトリを追加...",
    "Add Directory to Case Library": "ケースライブラリにディレクトリを追加",
    "Remove Selected ({n})": "選択済みを削除 ({n})",
    "Delete Selected ({n})": "選択済みを削除 ({n})",
    "Manage Case Library": "ケースライブラリの管理",
    "Auto-detected (read-only)": "自動検出（読み取り専用）",
    "User-added directories": "ユーザー追加ディレクトリ",
    "$FOAM_TUTORIALS is not set or does not exist.": "$FOAM_TUTORIALS が設定されていないか存在しません。",
    "Clean Backup Files": "バックアップファイルを削除",
    "No backup files found in this case.": "このケースにバックアップファイルが見つかりません。",
    "{n} backup file(s) found in this case:": "このケースに {n} 件のバックアップファイルが見つかりました:",
    "Manage Extra Files & Directories": "追加ファイル＆ディレクトリの管理",
    "Extra files registered for this case:": "このケースに登録された追加ファイル:",
    "Directories scanned in full (all files loaded, like 0/).\n"
    "Check items and click Toggle Recursive to enable/disable recursive scan.":
        "完全スキャン対象のディレクトリ（0/ のようにすべてのファイルを読み込み）。\n"
        "チェックして再帰切替えをクリックして再帰スキャンを切り替えてください。",
    "Add Directory…": "ディレクトリを追加…",
    "Toggle Recursive": "再帰切替え",
    "Select Directory to Add": "追加するディレクトリを選択",
    "No case directory open": "ケースディレクトリが開かれていません",
    "Duplicate Case": "ケースを複製",
    "Source case:": "ソースケース:",
    "Save in:": "保存先:",
    "New case name:": "新しいケース名:",
    "Destination:": "保存先パス:",
    "Copy mode": "コピーモード",
    "Copy all files (full directory copy)": "すべてのファイルをコピー（ディレクトリ全体）",
    "Copy app-visible files only\n"
    "(system/controlDict, fvSchemes, fvSolution, …, constant/g, 0/, 0.orig/)":
        "アプリ表示ファイルのみコピー\n"
        "（system/controlDict, fvSchemes, fvSolution, …, constant/g, 0/, 0.orig/）",
    "Select Destination Directory": "保存先ディレクトリを選択",
    "Keyboard Shortcuts": "キーボードショートカット",
    # Help > Keyboard Shortcuts: section titles and row labels.
    "Application": "アプリケーション",
    "Find": "検索",
    "Find Next": "次を検索",
    "Find Previous": "前を検索",
    "Find in Tree": "ツリー内で検索",
    "Undo": "元に戻す",
    "Redo": "やり直す",
    "Cut": "切り取り",
    "Copy Value": "値をコピー",
    "Paste Value": "値を貼り付け",
    "Zoom In": "拡大",
    "Zoom Out": "縮小",
    "Reset Zoom": "拡大率をリセット",
    "Zoom (mouse)": "ズーム（マウス）",
    "BlockMesh 3-D viewer": "BlockMesh 3Dビューア",
    "Rotate": "回転",
    "Pan": "パン",
    "Zoom": "ズーム",
    "Reset camera": "カメラをリセット",
    "Isometric view": "等角投影ビュー",
    "Fly to point": "ポイントへ移動",
    "Wireframe / Surface": "ワイヤフレーム / サーフェス",
    "Point & line size": "点と線のサイズ",
    "Rename Boundary": "境界名を変更",
    'Rename "{name}" to:': '"{name}" を次の名前に変更:',
    "Apply to:": "適用先:",
    "Rename ({n} file{s})": "{n} 件{s}のファイルをリネーム",
    "Save as New Case": "新しいケースとして保存",
    "Unsaved edits in the current session are written into the new case.\n"
    "The original case is not modified.":
        "現在のセッションの未保存の編集は新しいケースに書き込まれます。\n"
        "元のケースは変更されません。",
    "Reset Settings": "設定のリセット",
    "Reset Options": "リセットオプション",
    "Application Settings (app_config.json)": "アプリケーション設定 (app_config.json)",
    "Reset the case directory, window size, saved session, theme, "
    "language, case library, and links":
        "ケースディレクトリ、ウィンドウサイズ、保存されたセッション、テーマ、"
        "言語、ケースライブラリ、リンクをリセット",
    "Schema Module Settings (schema_config.json)": "スキーマモジュール設定 (schema_config.json)",
    "Reset schema modules to default (controlDict, fvSchemes, fvSolution)":
        "スキーマモジュールをデフォルト（controlDict, fvSchemes, fvSolution）にリセット",
    "⚠️ Warning: This will delete the selected configuration files and restore default settings.":
        "⚠️ 警告: 選択した設定ファイルが削除され、デフォルト設定に戻ります。",
    "Reset Selected": "選択済みをリセット",
    "• Application Settings\n": "• アプリケーション設定\n",
    "• Schema Module Settings\n": "• スキーマモジュール設定\n",
    "✓ Application settings reset successfully\n  (window size restored to {w}x{h})":
        "✓ アプリケーション設定をリセットしました\n  （ウィンドウサイズを {w}x{h} に復元）",
    "  The window layout and size of this session are not saved.":
        "  このセッションのウィンドウレイアウトとサイズは保存されません。",
    "✗ Failed to reset app settings: {e}": "✗ アプリ設定のリセットに失敗しました: {e}",
    "✓ Schema module settings reset successfully": "✓ スキーマモジュール設定をリセットしました",
    "✗ Failed to reset schema settings: {e}": "✗ スキーマ設定のリセットに失敗しました: {e}",
    "\n\nPlease restart the application for all changes to take effect.":
        "\n\nすべての変更を反映させるには、アプリケーションを再起動してください。",
    "Schema Module Manager": "スキーマモジュールマネージャ",
    "Currently loaded schema modules:": "現在読み込まれているスキーマモジュール:",
    "Add Module from File": "ファイルからモジュールを追加",
    "Remove Selected": "選択済みを削除",
    "Save & Close": "保存して閉じる",
    "Select Schema Module File": "スキーマモジュールファイルを選択",
    "Resources": "リソース",
    "OpenFOAM has two main distributions maintained by separate organizations. "
    "This application is not affiliated with either.":
        "OpenFOAM には別々の組織が管理する2つの主要ディストリビューションがあります。\n"
        "このアプリケーションはどちらとも関係ありません。",
    "OpenCFD / ESI Group  (openfoam.com)": "OpenCFD / ESI Group  (openfoam.com)",
    "OpenFOAM Foundation  (openfoam.org)": "OpenFOAM Foundation  (openfoam.org)",
    "Double-click a link to open it in your browser.": "リンクをダブルクリックしてブラウザで開きます。",
    "Add": "追加",
    "Remove": "削除",
    "Move Up": "上へ移動",
    "Move Down": "下へ移動",
    "Label:": "ラベル:",
    "URL:": "URL:",
    "Link": "リンク",
    "Edit boundary: {field} / {patch}": "境界を編集: {field} / {patch}",
    "Variable:": "変数:",
    "Patch:": "パッチ:",
    "Content:": "内容:",
    "Type:": "型:",
    "⚠ This patch contains large or binary data.\n"
    "The full value cannot be displayed here.\n"
    "Use the Text Editor tab to edit the complete content.":
        "⚠ このパッチには大きなまたはバイナリデータが含まれています。\n"
        "ここでは完全な値を表示できません。\n"
        "テキストエディタタブで完全な内容を編集してください。",
    "Select files to add from '{group}':": "'{group}' から追加するファイルを選択してください:",
    "New file in '{group}'...": "'{group}' に新しいファイル...",
    "Add files from '{group}'...": "'{group}' からファイルを追加...",
    "Add '{d}' to file list": "'{d}' をファイルリストに追加",
    "Remove '{group}' from file list": "'{group}' をファイルリストから削除",
    "Duplicate '{src}' → '{dst}'...": "'{src}' → '{dst}' に複製...",
    "Delete '0' directory...": "'0' ディレクトリを削除...",
    "Extra": "追加",
    "Manage…": "管理…",
    "Parsed successfully and tree updated": "正常に解析してツリーを更新しました",
    "Parse failed: {e}": "解析に失敗しました: {e}",
    "Reloaded text from current tree": "現在のツリーからテキストを再読み込みしました",
    "Vertex coordinates updated": "頂点座標を更新しました",
    "All files in '{group}' are already in the file list.":
        "'{group}' 内のすべてのファイルはすでにファイルリストにあります。",
    "Add files from '{group}'": "'{group}' からファイルを追加",

    # ── file dialog titles ────────────────────────────────────────────────────
    "Open OpenFOAM Case": "OpenFOAM ケースを開く",
    "Open OpenFOAM Case from Library": "ライブラリから OpenFOAM ケースを開く",
    "Select Source Case from Library": "ライブラリからソースケースを選択",
    "Select Default Case Directory": "デフォルトケースディレクトリを選択",

    # ── generate keywords dialog ──────────────────────────────────────────────
    "Generate OpenFOAM Keywords…": "OpenFOAM キーワードを生成…",
    "Scans the selected OpenFOAM installation (etc/caseDicts/, src/ and\n"
    "applications/ sources) and writes app_config/foam_keywords.json,\n"
    "which overrides the bundled foam_keywords.default.json.":
        "選択した OpenFOAM インストール (etc/caseDicts/、src/ と applications/ の\n"
        "ソース) をスキャンし、app_config/foam_keywords.json に書き出します。\n"
        "このファイルは同梱の foam_keywords.default.json より優先されます。",
    "Installation:": "インストール:",
    "No OpenFOAM installation found — browse to one, or source "
    "your OpenFOAM environment and reopen this dialog.":
        "OpenFOAM のインストールが見つかりません — 参照ボタンで指定するか、"
        "OpenFOAM 環境を source してからダイアログを開き直してください。",
    "This file overrides the bundled foam_keywords.default.json.":
        "このファイルは同梱の foam_keywords.default.json より優先されます。",

    # ── find OpenFOAM examples dialog ─────────────────────────────────────────
    "Find OpenFOAM Examples…": "OpenFOAM の例を検索…",
    "Find OpenFOAM Examples": "OpenFOAM の例を検索",
    "Search example usages in the OpenFOAM tutorials and etc/caseDicts templates":
        "OpenFOAM のチュートリアルと etc/caseDicts テンプレートから使用例を検索します",
    "OpenFOAM installation:": "OpenFOAM インストール:",
    "No OpenFOAM installation found — browse to one to enable searching.":
        "OpenFOAM のインストールが見つかりません — 参照ボタンで指定すると検索できます。",
    "Keyword or setting, e.g. #includeFunc": "キーワードまたは設定 (例: #includeFunc)",
    "All files": "すべてのファイル",
    "Tutorials": "チュートリアル",
    "caseDicts templates": "caseDicts テンプレート",
    "Search": "検索",
    "File": "ファイル",
    "First match": "最初の一致",
    "Compare with this case": "このケースと比較",
    "Duplicate this case…": "このケースを複製…",
    "Copy File": "ファイルをコピー",
    "Copy Selection": "選択範囲をコピー",
    "Browse…": "参照…",
    "Select OpenFOAM Installation Directory": "OpenFOAM インストールディレクトリを選択",
    "Not an OpenFOAM directory (no tutorials/ or etc/caseDicts/).":
        "OpenFOAM のディレクトリではありません (tutorials/ も etc/caseDicts/ もありません)。",
    "Select an OpenFOAM installation first.": "先に OpenFOAM インストールを選択してください。",
    "Enter a search keyword.": "検索キーワードを入力してください。",
    "Select at least one source to search.": "検索対象を 1 つ以上選択してください。",
    "Searching…": "検索中…",
    "Cancelling…": "キャンセル中…",
    "{count} matching file(s) found.": "{count} 件のファイルが一致しました。",
    "No matches found.": "一致するものが見つかりませんでした。",
    "Search failed: {msg}": "検索に失敗しました: {msg}",
    "Could not read file: {msg}": "ファイルを読み込めませんでした: {msg}",
    "{path}  ({count} matching line(s))": "{path}  ({count} 行が一致)",
    "Selection copied.": "選択範囲をコピーしました。",
    "File contents copied.": "ファイルの内容をコピーしました。",
    "No case open": "ケースが開かれていません",
    "Open a case first, then compare it with the example case.":
        "先にケースを開いてから、例のケースと比較してください。",

    # ── run tool options dialog (Tools menu "Run *") ──────────────────────────
    "Run {tool}": "{tool} を実行",
    "Run": "実行",
    "Extra options:": "追加オプション:",
    "Additional options (e.g. -time 0.5)": "その他のオプション（例: -time 0.5）",
    "Command:": "コマンド:",
    "(invalid extra options — unbalanced quote?)":
        "（追加オプションが不正です — 引用符が閉じていない可能性があります）",
    "Select dictionary file": "ディクショナリファイルを選択",
    "Alternative dictionary": "代替ディクショナリ",
    "Mesh region (multi-region case)": "メッシュリージョン（マルチリージョンケース）",
    "Overwrite the existing mesh instead of writing a new time directory":
        "新しい時間ディレクトリを作らず既存のメッシュを上書き",
    "Run all geometry checks (including non-standard)":
        "すべての形状チェックを実行（非標準を含む）",
    "Run all topology checks (including non-standard)":
        "すべてのトポロジーチェックを実行（非標準を含む）",
    "Write faulty cells/faces as sets in this format":
        "問題のあるセル/面をこの形式のセットとして書き出し",
    "e.g. system/blockMeshDict.v2": "例: system/blockMeshDict.v2",
    "e.g. fluid": "例: fluid",
    "e.g. vtk": "例: vtk",

    # ── Allrun / Allclean / clean case (Tools menu) ───────────────────────────
    "Run Allrun Script": "Allrun スクリプトを実行",
    "Send './Allrun' to the terminal panel — runs the case's full "
    "workflow, including the solver":
        "'./Allrun' をターミナルパネルに送信します — ソルバーを含む"
        "ケースの全ワークフローを実行します",
    "Run Allclean Script": "Allclean スクリプトを実行",
    "Send './Allclean' to the terminal panel to clean the case":
        "'./Allclean' をターミナルパネルに送信してケースをクリーンします",
    "Clean Case (foamCleanTutorials)": "ケースをクリーン (foamCleanTutorials)",
    "Clean the case with foamCleanTutorials; runs ./Allclean "
    "when the case has one":
        "foamCleanTutorials でケースをクリーンします。ケースに ./Allclean が"
        "あればそれを実行します",
    "No Allrun script": "Allrun スクリプトがありません",
    "This case has no Allrun script to run.":
        "このケースには実行する Allrun スクリプトがありません。",
    "No Allclean script": "Allclean スクリプトがありません",
    "This case has no Allclean script to run.":
        "このケースには実行する Allclean スクリプトがありません。",
    "Case already run?": "ケースは実行済みですか?",
    "This case already has log files: {logs}.\n"
    "OpenFOAM's Allrun helpers skip any step whose log.* file "
    "exists, so those steps will not re-run.\n"
    "Clean the case first to re-run the whole workflow?":
        "このケースには既にログファイルがあります: {logs}\n"
        "OpenFOAM の Allrun ヘルパーは log.* ファイルが存在するステップを"
        "スキップするため、それらのステップは再実行されません。\n"
        "先にケースをクリーンして、ワークフロー全体を再実行しますか?",
    "Clean, then run": "クリーンしてから実行",
    "Run anyway": "そのまま実行",
    "setFields modifies the field files in 0/ in place, so re-running "
    "it on already-set fields compounds the values.":
        "setFields は 0/ の場ファイルを直接書き換えるため、設定済みの場に"
        "対して再実行すると値が重ねて適用されます。",
    "Restore 0/ from 0.orig/ first (start from clean initial fields)":
        "先に 0/ を 0.orig/ から復元する（クリーンな初期場から開始）",
    "This case has no 0.orig/ backup to restore from.":
        "このケースには復元元となる 0.orig/ バックアップがありません。",
    "Run Allrun script?": "Allrun スクリプトを実行しますか?",
    "This runs the case's full workflow, which may include a "
    "long-running solver. In Simple terminal mode a running "
    "job cannot be interrupted. Continue?":
        "ケースの全ワークフローを実行します。長時間かかるソルバーが含まれる"
        "場合があります。Simple ターミナルモードでは実行中のジョブを中断"
        "できません。続行しますか?",
    "Run Allclean script?": "Allclean スクリプトを実行しますか?",
    "This removes the generated mesh, time directories, log files "
    "and other results from the case. Continue?":
        "生成されたメッシュ、時刻ディレクトリ、ログファイルなどの結果を"
        "ケースから削除します。続行しますか?",
    "Clean case?": "ケースをクリーンしますか?",
    "This cleans the case with foamCleanTutorials, removing the "
    "generated mesh, time directories, processor*/ decompositions, "
    "postProcessing/ and log.* files.":
        "foamCleanTutorials でケースをクリーンし、生成されたメッシュ、"
        "時刻ディレクトリ、processor*/ 分割、postProcessing/、log.* ファイルを"
        "削除します。",
    "This case has its own Allclean script, which will be run instead.":
        "このケースには独自の Allclean スクリプトがあり、代わりにそれが実行されます。",
    "0/ will also be removed because 0.orig/ exists "
    "(use 'Restore 0/ from 0.orig' to recreate it).":
        "0.orig/ が存在するため 0/ も削除されます"
        "（'Restore 0/ from 0.orig' で再作成できます）。",
    "Continue?": "続行しますか?",
}
