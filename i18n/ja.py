# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
LANGUAGE_NAME = "日本語"

TRANSLATIONS: dict[str, str] = {
    # ── window / app ──────────────────────────────────────────────────────────
    "foam dictionary editor": "foam ディクショナリエディタ",
    "Language": "言語",
    "Language Changed": "言語の変更",
    "The language will change after restarting the application.": "アプリケーションを再起動すると言語が変わります。",

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
    "Reset All Settings…": "すべての設定をリセット…",
    "View": "表示",
    "Show Type Column": "型列を表示",
    "BlockMesh 3-D Panel": "BlockMesh 3Dパネル",
    "BlockMesh 3-D Panel  (unavailable: xterm active)": "BlockMesh 3Dパネル（利用不可: xterm使用中）",
    "Help": "ヘルプ",
    "About Foam Dictionary Editor (FoDE)...": "Foam Dictionary Editor (FoDE) について...",
    "Keyboard Shortcuts...": "キーボードショートカット...",
    "Resources...": "リソース...",

    # ── top bar buttons / labels ──────────────────────────────────────────────
    "Save File": "ファイルを保存",
    "Save All Files": "すべてのファイルを保存",
    "Apply Text to Tree": "テキストをツリーに適用",
    "Reload from Tree": "ツリーから再読み込み",
    "Case:": "ケース:",
    "File:": "ファイル:",
    "Current case name": "現在のケース名",
    "Current file name": "現在のファイル名",
    "No case opened": "ケースが開かれていません",
    "No file loaded": "ファイルが読み込まれていません",

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
    "Clear": "クリア",
    "Select Reference Case Directory": "参照ケースディレクトリを選択",
    "Comparing with: <b>{name}</b>  ({directory})": "{name} と比較中  ({directory})",
    "Diff cleared.": "差分をクリアしました。",
    "Diff: {rel} not found in reference case.": "差分: {rel} が参照ケースに見つかりません。",
    "Diff: {n} difference{s} in {rel}.": "差分: {rel} に {n} 件{s}の差異。",

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
    "Cannot apply: '{path}' not found in current case": "適用できません: '{path}' が現在のケースに見つかりません",
    "Applied '{key}' from reference case": "参照ケースから '{key}' を適用しました",
    "Inserted '{key}' from reference case": "参照ケースから '{key}' を挿入しました",
    "Case reloaded: {path}": "ケースを再読み込みしました: {path}",
    "Duplicated to: {dest}": "複製しました: {dest}",
    "Saved as new case: {dest}": "新しいケースとして保存しました: {dest}",
    "Loaded: {path}": "読み込みました: {path}",
    "Parsed: {path} — {n} unrecognized {entries}": "解析しました: {path} — {n} 件の未認識{entries}",
    "Parsed successfully: {path}": "正常に解析しました: {path}",
    "Parse warning: {e}": "解析時の警告: {e}",
    "Saved: {path}": "保存しました: {path}",
    "Saved: {path} — {n} unrecognized {entries}": "保存しました: {path} — {n} 件の未認識{entries}",
    "Saved and parsed: {path}": "保存して解析しました: {path}",
    "Saved, but parse failed: {e}": "保存しましたが、解析に失敗しました: {e}",
    "Saved {n} file(s).": "{n} 件のファイルを保存しました。",
    "Added {n} file(s) to the file list.": "{n} 件のファイルをファイルリストに追加しました。",
    "File name must not be empty.": "ファイル名を入力してください。",
    "File name must not contain path separators.": "ファイル名にパス区切り文字を含めないでください。",
    "File already exists: {name}": "ファイルが既に存在します: {name}",
    "Created: {group}/{filename}": "作成しました: {group}/{filename}",
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
    "Reload Case": "ケースの再読み込み",
    "Destination Already Exists": "保存先が既に存在します",
    "Duplicate Error": "複製エラー",
    "Save As Error": "名前を付けて保存エラー",
    "Duplicate Complete": "複製完了",
    "Possibly Not an OpenFOAM Case": "OpenFOAMケースではない可能性があります",
    "Directory Saved": "ディレクトリを保存しました",
    "Reset Window Size": "ウィンドウサイズをリセット",
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
    "Reset File List": "ファイルリストをリセット",
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
    "No Case Open": "ケースが開かれていません",

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
    "Could not remove existing directory:\n{e}": "既存のディレクトリを削除できませんでした:\n{e}",
    "The selected directory does not contain 'system' or 'constant':\n\n{directory}\n\n"
    "This may not be a valid OpenFOAM case.\nOpen anyway?":
        "選択したディレクトリには 'system' または 'constant' が含まれていません:\n\n{directory}\n\n"
        "有効な OpenFOAM ケースでない可能性があります。\nそれでも開きますか？",
    "Delete '{node_name}'? This cannot be undone.": "'{node_name}' を削除しますか？この操作は元に戻せません。",
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

    # ── context-menu items ────────────────────────────────────────────────────
    "Copy Value\tCtrl+C": "値をコピー\tCtrl+C",
    "Paste Value\tCtrl+V": "値を貼り付け\tCtrl+V",
    "Add Entry After": "後にエントリを追加",
    "Add Child Entry": "子エントリを追加",
    "Duplicate": "複製",
    "Rename Boundary...": "境界をリネーム...",
    "Comment Out": "コメントアウト",
    "Restore from Comment": "コメントから復元",
    "Delete": "削除",
    "Edit": "編集",
    "Create Entry": "エントリを作成",
    "Delete Entry": "エントリを削除",
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
    "Auto-scroll editor": "エディタ自動スクロール",
    "When checked, clicking a cell opens its file in the editor\nand scrolls to that boundary entry.":
        "チェックすると、セルのクリックでエディタにファイルを開き、その境界エントリへスクロールします。",
    "Copy Table": "テーブルをコピー",
    "Directory:": "ディレクトリ:",
    "Lines per cell:": "セルあたりの行数:",
    "Number of lines to display per cell": "セルあたりの表示行数",
    "Delete BoundaryField  '{patch}'": "BoundaryField '{patch}' を削除",
    "Delete BoundaryField": "BoundaryField を削除",
    "Rename Boundary  '{patch}'...": "境界 '{patch}' をリネーム...",
    "Rename Boundary...": "境界名を変更...",
    "Add BoundaryField...": "BoundaryField を追加...",

    # ── file list panel ───────────────────────────────────────────────────────
    "Changed files only": "変更済みファイルのみ",
    "Manage extra files…": "追加ファイルを管理…",

    # ── dialogs ───────────────────────────────────────────────────────────────
    "About Foam Dictionary Editor (FoDE)": "Foam Dictionary Editor (FoDE) について",
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
    "BlockMesh 3-D viewer (mouse)": "BlockMesh 3Dビューア（マウス）",
    "Rotate": "回転",
    "Pan": "パン",
    "Zoom": "ズーム",
    "Reset camera": "カメラをリセット",
    "Fly to point": "ポイントへ移動",
    "Rename Boundary": "境界名を変更",
    'Rename "{name}" to:': '"{name}" を次の名前に変更:',
    "Apply to:": "適用先:",
    "Rename ({n} file{s})": "{n} 件{s}のファイルをリネーム",
    "No matching boundary entries found in loaded files.": "読み込まれたファイルに一致するバウンダリエントリが見つかりません。",
    "Save as New Case": "新しいケースとして保存",
    "Unsaved edits in the current session are written into the new case.\n"
    "The original case is not modified.":
        "現在のセッションの未保存の編集は新しいケースに書き込まれます。\n"
        "元のケースは変更されません。",
    "Reset Settings": "設定のリセット",
    "Reset Options": "リセットオプション",
    "Application Settings (app_config.json)": "アプリケーション設定 (app_config.json)",
    "Reset case directory, window size, and recent cases": "ケースディレクトリ、ウィンドウサイズ、最近のケースをリセット",
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
    "Edit": "編集",
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
    "File was saved as text, but tree refresh failed.\n\n{e}": "ファイルをテキストとして保存しましたが、ツリーの更新に失敗しました。\n\n{e}",
    "All files in '{group}' are already in the file list.":
        "'{group}' 内のすべてのファイルはすでにファイルリストにあります。",
    "Add files from '{group}'": "'{group}' からファイルを追加",

    # ── file dialog titles ────────────────────────────────────────────────────
    "Open OpenFOAM Case": "OpenFOAM ケースを開く",
    "Open OpenFOAM Case from Library": "ライブラリから OpenFOAM ケースを開く",
    "Select Source Case from Library": "ライブラリからソースケースを選択",
    "Select Default Case Directory": "デフォルトケースディレクトリを選択",
}
