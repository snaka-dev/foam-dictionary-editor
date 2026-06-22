# Foam Dictionary Editor (FoDE)

FoDE — Foam Dictionary Editor（読み方: "フォーディー"）

Python と PySide6 で作られた、OpenFOAM 辞書ファイル向け GUI エディタです。

## FoDE とは？

FoDE は OpenFOAM ケースの辞書ファイルをグラフィカルに編集するツールです。構造化されたツリー表示とプレーンテキストエディタの両方で辞書を閲覧・編集・管理できます。OpenFOAM シミュレーションを行うエンジニアや研究者が、ケースファイルのセットアップや修正をより手軽に行えることを目指しています。

![メインウィンドウ — Tree と Editor タブ](docs/images/main-window-tree-editor.png)

## インストール

Python 3.10 以上が必要です。

```bash
git clone https://github.com/snaka-dev/foam-dictionary-editor
cd foam-dictionary-editor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # PySide6 (Qt for Python) をインストール
```

初回起動時にインターネット接続を推奨します — ターミナルエミュレータ xterm.js が `ui/xterm/` へ自動ダウンロードされます。接続がない場合は QProcess ベースのシンプルターミナルが使われます。インターネット接続のある状態でアプリを再起動すると再試行されます。手動で配置する場合は以下のファイルを `ui/xterm/` に置いてください:

| ファイル | URL |
|---|---|
| `xterm.js` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/lib/xterm.js` |
| `xterm.css` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/css/xterm.css` |
| `xterm-addon-fit.js` | `https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.11.0/lib/addon-fit.js` |

**オプション — BlockMesh 3D ビューア**（Linux/macOS）: `blockMeshDict` のインタラクティブな 3D ジオメトリパネルを有効にするには `pyvista` と `pyvistaqt` をインストールしてください:

```bash
pip install pyvista pyvistaqt
```

これらのパッケージがない場合、BlockMesh タブにインストールを促すメッセージが表示され、3D ビューアは無効になります。

## 基本的な使い方

1. **起動**

   ```bash
   python3 main.py                                   # 標準（ターミナル + BlockMesh）
   python3 main.py --variant no-terminal             # ターミナルなし（Windows 向け）
   python3 main.py --variant no-terminal-blockmesh   # ターミナルなし + BlockMesh 3D パネル
   ```

   選択したバリアントは終了時に `app_config.json` へ保存され、次回以降の起動時にも自動的に適用されます。

2. **ケースを開く** — いずれかを選択:
   - *自分のケース:* **Case > Open Case** → ケースディレクトリを選択
   - *ドラッグ＆ドロップ:* ファイルマネージャからケースディレクトリをウィンドウ上の任意の場所にドロップ
   - *チュートリアルから始める:* **Case > Duplicate from Case Library** → `$FOAM_TUTORIALS` を参照 → 作業ディレクトリへコピー
   - *同梱サンプルを使う:* リポジトリルートの `tutorials/` ディレクトリにあるケースを直接開く（「[サンプルケース](#サンプルケース)」参照）

3. **ファイルを選択** — 左パネルから対象ファイルを選ぶ（例: `system/controlDict`、`0/U`）

4. **編集** — ツリービューまたは下部のテキストエディタで値を編集する

5. **境界条件を確認・調整** — **Boundary** タブで全パッチと全フィールド変数の境界条件を一覧表示。セルをクリックするとそのファイルがエディタで開きパッチエントリにジャンプ。ダブルクリックで編集できる

6. **保存** — `Ctrl+S`（現在のファイル）または `Ctrl+Shift+S`（変更済みファイルをすべて保存）

7. *（オプション）* **ソルバーを実行** — **Terminal** タブから直接 `blockMesh`、`interFoam` などの OpenFOAM コマンドを実行できる。ターミナルはケースディレクトリで自動的に起動する

## 主な機能

**ファイル管理**
- 代表的な辞書ファイル（`controlDict`、`fvSchemes`、`fvSolution`、`blockMeshDict`、`snappyHexMeshDict` など）を自動表示
- マルチリージョンケース構造やフィールドディレクトリ（`0/`、`0.orig/`）を自動検出
- 任意のディレクトリをファイル一覧に追加可能。`0/` と同様にディレクトリ内のファイルを自動スキャン。フラット（直下ファイルのみ）または再帰スキャン（サブディレクトリを含む）を選択できます。カスタムフィールドディレクトリ（`initial/`）、再起動タイムステップ（`0.5/`）、深い階層のサブディレクトリ（`lagrangian/chemkin/`）などに対応
- ファイルパネルからファイルの追加・作成・複製・バックアップ・削除が可能
- トップバーの **Reload Case** ボタンまたは **Case > Reload Case** でケースをディスクから再読み込みし、すべてのメモリ上の編集内容を破棄（未保存ファイルがある場合は確認ダイアログを表示）
- `0` ヘッダーの右クリックメニューから `0/` ディレクトリをディスクごと削除（`0.orig` が存在する場合のみ表示）
- 現在のケースを新しいケースとして保存したり、既存ケースを複製したりできる

**ツリーとテキストの編集**
- 辞書エントリの閲覧・編集ができる構造化ツリービュー
- 生テキストエディタをいつでもフォールバックとして利用可能
- ツリーとテキストの双方向同期
- 右クリックメニューでエントリの追加・複製・コメントアウト・削除が可能

**境界条件ビュー**
- 全フィールド変数の境界条件を一つのテーブルで確認
- セルをクリックするとそのファイルをエディタで開きパッチエントリにジャンプ（**Auto-scroll editor** で切り替え可）
- テーブル上でパッチエントリを直接編集・作成・削除・コピー・ペースト
- 全フィールドファイルへのパッチ一括追加・削除

**スキーマヘルプ**
- 主要な設定項目（`controlDict`、`fvSchemes`、`fvSolution`、`blockMeshDict`、`snappyHexMeshDict`）の説明と有効な選択肢を組み込み表示
- 独自のスキーマモジュール（Python ファイル）で拡張可能

**BlockMesh 3D ビューア** *(pyvista / pyvistaqt が必要)*
- `blockMeshDict` のジオメトリをインタラクティブに 3D プレビュー（頂点、ブロックエッジ、境界面）
- 境界面をパッチ種別（wall、inlet、outlet、symmetry など）で色分け表示
- STL / OBJ ジオメトリファイルの読み込みとオーバーレイ表示
- 頂点、頂点ラベル、ブロックエッジ、ブロックラベル、境界面、軸、グリッド、寸法テキストの表示切替
- Color blocks: 各ヘックスブロックを定性的パレットの異なる色で表示。Solid blocks: 半透明のソリッドブロック面（opacity 0.25）を表示
- 頂点ラベルとブロックラベルで共用するラベルフォントサイズ調整スピンボックス
- 視点方向ボタン（+X/−X/+Y/−Y/+Z/−Z/Iso）でカメラ位置を素早く切り替え
- 3D ビュー下部のマウス操作ヒント（ドラッグ = 回転、Shift+ドラッグ = 平行移動、スクロール = ズーム）。詳細は **Help > Keyboard Shortcuts…** を参照
- 3D ビューと並んで表示される頂点テーブル（インデックス | X | Y | Z）。行をクリックすると頂点がハイライト表示され、座標セルをダブルクリックすると値を編集できます。変更は即座に FoamNode ツリーとテキストエディタに書き戻されます
- `blockmesh` フィーチャーが有効なときに **BlockMesh** タブとして表示（`no-terminal-blockmesh` バリアントでは常時表示、`standard` バリアントではシンプルターミナル使用時のみ表示）。**View > BlockMesh 3-D Panel** でも切り替え可能

**統合ターミナル**
- フル PTY xterm.js ターミナル（Linux/macOS で `QtWebEngineWidgets` が利用可能な場合）— `standard` バリアントのデフォルト
- QProcess ベースのシンプルターミナルも利用可能。有効にすると BlockMesh 3D パネルが表示される
- Terminal タブのチェックボックスで実行中に切り替え可能
- ケースを開くと自動的にそのディレクトリへ移動
- `no-terminal` および `no-terminal-blockmesh` バリアントでは完全に省略（Windows 向け）
- **foamMonitor ランチャー** — **Tools > foamMonitor…** から `foamMonitor` を起動し、残差や postProcessing データを gnuplot でプロット。**■ foamMonitor** を再度選択して停止

**ケース比較**
- **Case > Compare with Case...** — 参照ケースのディレクトリを選択し、現在のケースと比較できます
- アクションバー下の差分バーに参照パス、カラーレジェンド、**Side by side** トグルを表示します。**Clear** をクリックすると比較モードを終了できます
- **サイドバイサイド表示**: メインツリーの右に参照ケースのツリーパネルが開きます。そのエントリを右クリックして **Use this value** を選ぶと、値を現在のケースへ直接適用できます
- ツリーオーバーレイ — 現在のケース（左ペイン）: 薄黄色 = 値の変更、薄青 = 現在のファイルのみに存在するキー。参照ペイン（右）: 薄黄色 = 値の変更、薄緑 = 参照のみに存在するキー
- いずれかのペインのハイライト行をホバーすると、ツールチップに対応する値を表示します
- ファイル一覧のマーカー: 差分あり → `≠N`（アンバー）、差分なし（確認済み）→ `≠0`（グレー）、未訪問 → マーカーなし。50 件超は `≠50+` に丸めます。比較開始時に全ファイルのマーカーが即座に計算されます
- ファイル一覧の **Changed files only** チェックボックス: 差分のないファイルを非表示にします

**UI 言語**
- **Settings > Language** — English と 日本語 を切り替えられます。アプリケーションを再起動すると反映されます。
- `i18n/` に翻訳ファイルを1つ追加するだけで、新しい言語を追加できます。

**参照リンク**
- **Help > Resources...** から OpenFOAM 公式ドキュメントへのリンクを確認できます
- **My Links** タブで個人用参照リンクの追加・編集・並び替え・削除が可能。ダブルクリックでブラウザを開きます

## 全リファレンス

すべてのパネル・メニュー・操作手順の詳細については [USER_GUIDE_ja.md](USER_GUIDE_ja.md) を参照してください。
プロジェクト構成・開発環境のセットアップ・テストについては [DEVELOPER_ja.md](DEVELOPER_ja.md) を参照してください。

## サンプルケース

リポジトリルートの `tutorials/` ディレクトリには、OpenFOAM v2512 の標準チュートリアルセットから取得した OpenFOAM ケースが収録されています。

| ディレクトリ | ソルバー | 用途 |
|---|---|---|
| `tutorials/cavity/` | `icoFoam` | 単一リージョンのエンドツーエンドワークフロー解説 |
| `tutorials/snappyMultiRegionHeater/` | `chtMultiRegionFoam` | 境界条件ビューとリージョンファイル一覧のマルチリージョンケース |

**ライセンス:** これらのケースファイルは **GPL-3.0** でライセンスされています（FoDE ソースコードの AGPL-3.0 とは別です）。詳細は `tutorials/tutorials_README.md` を参照してください。

## ライセンス

Copyright (C) 2025-2026 Shinji NAKAGAWA。[GNU Affero General Public License v3.0 以降](LICENSE)（AGPL-3.0-or-later）で配布されます。

## 免責事項

This offering is not approved or endorsed by OpenCFD Limited, producer and distributor of the OpenFOAM software via [www.openfoam.com](http://www.openfoam.com/), and owner of the OPENFOAM® and OpenCFD® trade marks.

## 謝辞

- [PySide6 (Qt for Python)](https://doc.qt.io/qtforpython/) — GUI フレームワーク（LGPL v3）
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — `blockMeshDict` の 3D ビューア（BSD-3-Clause、オプション）
- [xterm.js](https://xtermjs.org/) — ターミナルパネルで使用するターミナルエミュレータ（MIT）。初回起動時に jsDelivr から自動ダウンロードされ `ui/xterm/` にキャッシュされます
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — テストフレームワーク（開発時のみ）

[OpenFOAM Foundation](https://openfoam.org/) および [OpenCFD / ESI Group](https://www.openfoam.com/) をはじめ、OpenFOAM をフリーのオープンソース CFD ソフトウェアとして開発・維持してきたすべての貢献者の方々に深く感謝いたします。
