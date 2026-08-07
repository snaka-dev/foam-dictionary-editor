# Foam Dictionary Editor (FoDE)

FoDE — Foam Dictionary Editor（読み方: "フォーディー"）

Python と PySide6 で作られた、OpenFOAM 辞書ファイル向け GUI エディタです。

🎬 **YouTube のデモ動画** — 短い紹介動画が 8 本あります。ショットごとの台本とあわせて [docs/DEMO_SCRIPTS_ja.md](docs/DEMO_SCRIPTS_ja.md) に一覧があります。まずは [編集し、見て、実行する](https://youtu.be/kGxfNhAe6xo)（約 74 秒）から。[ワークフロー全体](https://youtu.be/0FZPb92luw8)（約 3 分 38 秒）を通しで見ることもできます。

> 📄 **[*SoftwareX*](https://doi.org/10.1016/j.softx.2026.102852)**（Elsevier）に掲載されました — 「[引用](#引用)」を参照してください。

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

**オプション — BlockMesh 3D ビューア**（Linux/macOS）: `blockMeshDict` のインタラクティブな 3D ジオメトリパネルを有効にするには `pyvista` と `pyvistaqt` をインストールしてください（`topoSetDict`・`snappyHexMeshDict`・`setFieldsDict` を開いている場合、それらのジオメトリも重ねて表示されます）:

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

各見出しは [USER_GUIDE_ja.md](USER_GUIDE_ja.md) の詳細ドキュメントへのリンクになっています。

**[ファイル管理](USER_GUIDE_ja.md#ファイル一覧の挙動)**
- 代表的な辞書ファイル（`controlDict`、`fvSchemes`、`fvSolution`、`blockMeshDict`、`snappyHexMeshDict` など）と `0/`・`0.orig/` 配下の全ファイル、ケースルートの `All*` スクリプト（`Allrun`、`Allclean` など — プレーンテキストとして編集可能）を自動表示。マルチリージョンケース構造も自動検出
- 追加のファイルやディレクトリ（フラット/再帰スキャン）をファイル一覧に登録可能 — カスタムフィールドディレクトリ、再起動タイムステップ、深い階層のサブディレクトリなどに便利
- [`#include` ディレクティブを追跡](USER_GUIDE_ja.md#インクルードされたファイル)して取り込み先のファイルを一覧表示。ケース内のインクルードは本来のディレクトリグループに入り、OpenFOAM インストール先に解決するもの（`#includeEtc`、`#includeFunc`）は別グループにまとめて読み取り専用で開く。**Copy into case...** で編集可能なローカルコピーを作成できる
- ファイルパネルからファイルの作成・複製・バックアップ・削除が可能。ケースはいつでもディスクから再読み込みできる
- アプリ外部（Terminal パネルなど）での変更を検知してファイル一覧を自動更新。`constant/polyMesh` インジケーターがセル数を表示し、メッシュ生成後に `blockMeshDict` が変更されると「stale」と表示
- 現在の状態を新しいケースとして保存したり、既存ケースを複製したりできる

**[ツリーとテキストの編集](USER_GUIDE_ja.md#ツリーとテキストの編集フロー)**
- 構造化ツリービューと生テキストエディタを双方向に同期
- OpenFOAM シンタックスハイライト（オン/オフ切替可。キーワードリストは自分のインストールから再生成可能）とコード折りたたみ
- 右クリックメニューでエントリの追加・複製・コメントアウト・削除が可能
- `blockMeshDict` の `blocks ( … );` は `block 0`、`block 1`、… として 1 ブロック 1 行に展開され、BlockMesh 3D ビューアが描画する番号と一致。各行を個別に編集・追加・複製・削除でき、行を選択するとそのブロックが 3D ビューでアウトライン表示される

**[境界条件ビュー](USER_GUIDE_ja.md#境界条件ビュー)**
- 全フィールド変数の境界条件を一つのテーブルで一覧 — フィールドファイルを切り替える必要なし
- テーブル上でパッチエントリを直接編集・作成・削除・コピー・ペースト。パッチの追加・削除・リネームは全フィールドファイルに対して一括で実行可能
- セルをクリックするとエディタのパッチエントリへジャンプ。テーブル全体を Markdown / CSV としてコピー可能

**[スキーマヘルプ](USER_GUIDE_ja.md#詳細ペイン)**
- 主要な設定項目（`controlDict`、`fvSchemes`、`fvSolution`、`blockMeshDict`、`snappyHexMeshDict`）の説明と有効な選択肢を組み込み表示
- `turbulenceProperties`/`momentumTransport` の乱流モデル: 29 モデルそれぞれが何であるかを、OpenFOAM 自身のヘッダから引用した説明と定義論文つきで表示。各係数のソース既定値もフォーク・バージョン別に表示
- 独自のスキーマモジュール（Python ファイル）で拡張可能

**[BlockMesh 3D ビューア](USER_GUIDE_ja.md#blockmesh-パネル)** *(pyvista / pyvistaqt が必要)*
- `blockMeshDict` のジオメトリ（頂点、ブロック、パッチ種別で色分けされた境界面）をインタラクティブに 3D プレビュー。`$variable` や `#eval` 参照も自動解決
- `topoSetDict` のアクションジオメトリ、`snappyHexMeshDict` の `geometry {}` 形状（surface / region / geometry のみ に分類）、`setFieldsDict` の領域（`fieldValues` をラベル表示）をオーバーレイ表示。形状ごとに表示切替可能。ブロックメッシュより大きい形状はビュー内でクリップされ「(clipped)」マークが付く
- 3D ビュー横の頂点テーブルで座標を編集すると即座に反映。変数ベースの頂点はプレビューモードでファイルを変更せずに試せる
- STL/OBJ のオーバーレイ読み込み（複数同時に読み込み可能。`STL ▾` メニューでファイルごとに行と色が割り当てられる）と、topoSet/snappyHexMesh/setFields 形状の STL エクスポート
- **⊞** サイドバイサイドモードで、`blockMeshDict`・`topoSetDict`・`snappyHexMeshDict`・`setFieldsDict` の編集中にツリーの隣に 3D ビューを表示

**[統合ターミナル](USER_GUIDE_ja.md#ターミナルタブ)**
- フル PTY xterm.js ターミナル（Linux/macOS）と QProcess ベースのシンプルターミナルを実行中に切替可能。ケースを開くと自動的にそのディレクトリへ移動
- `no-terminal` バリアントでは完全に省略（Windows 向け）

**[ツールメニュー](USER_GUIDE_ja.md#foammonitor-ランチャー)**
- `blockMesh`・`snappyHexMesh`・`topoSet`・`setFields`・`checkMesh` をワンクリックでターミナル実行（出力は `log.*` に保存）。`0/` を `0.orig` から復元することも可能
- ケースの `Allrun`/`Allclean` スクリプトを実行、または `foamCleanTutorials` でケースを初期状態にクリーン
- ソルバー実行中に `foamMonitor` を起動して gnuplot で残差をプロット
- 生成されたメッシュを ParaView で表示
- 数千行の生ログをスクロールする代わりに `log.*` ファイルの要約レポートを表示
- OpenFOAM の使用例検索: インストールの `tutorials/` ケースと `etc/caseDicts/` テンプレートからキーワードの実際の使用例を検索し、プレビューからそのまま比較ビューへ読み込んだり、チュートリアルケースを複製して自分のケースの出発点にしたりできる

**[ケース比較](USER_GUIDE_ja.md#ケース比較)**
- 開いているケースを任意の参照ケースと比較: ツリーの色分け差分オーバーレイ、ファイル一覧の `≠N` マーカー、差分ありファイルのみの絞り込みフィルター
- サイドバイサイドの参照ツリーで右クリック **Use this value** により個々の設定を取り込み

**[外観](USER_GUIDE_ja.md#外観と配色)**
- **Settings > Appearance** — **Follow System**（既定）、**Light**、**Dark** から配色テーマを選択（再起動で反映）。エディタのシンタックスハイライト、差分行の配色、BlockMesh 3D ビューアのシーンを含む UI 全体に適用され、暗い画面の中で 3D ビューだけが白いままになることはありません

**UI 言語**
- **Settings > Language** — English と 日本語 を切り替えられます（再起動で反映）。`i18n/` に翻訳ファイルを1つ追加するだけで新しい言語を追加できます

**[参照リンク](USER_GUIDE_ja.md#resources-ダイアログ)**
- **Help > Resources...** — OpenFOAM 公式ドキュメントへのリンクと、個人用の **My Links** リスト

## 全リファレンス

すべてのパネル・メニュー・操作手順の詳細については [USER_GUIDE_ja.md](USER_GUIDE_ja.md) を参照してください。
プロジェクト構成・開発環境のセットアップ・テストについては [DEVELOPER_ja.md](DEVELOPER_ja.md) を参照してください。
アプリの注釈付きスクリーンショットについては [docs/SCREENSHOTS_ja.md](docs/SCREENSHOTS_ja.md) を参照してください。

## サンプルケース

リポジトリルートの `tutorials/` ディレクトリには、すぐに開ける OpenFOAM ケースが収録されています。

| ディレクトリ | ソルバー | 用途 |
|---|---|---|
| `tutorials/cavity/cavity/` | `icoFoam` | 単一リージョンのエンドツーエンドワークフロー解説 |
| `tutorials/cavity/cavityGrade/` | `icoFoam` | 非一様グレーディング（`simpleGrading`） |
| `tutorials/cavity/cavityClipped/` | `icoFoam` | クリップ形状・`mapFieldsDict` |
| `tutorials/snappyMultiRegionHeater/` | `chtMultiRegionFoam` | 境界条件ビューとリージョンファイル一覧のマルチリージョンケース |
| `tutorials/damBreak/` | `interFoam` | 二相流・`setFieldsDict` と `0.orig/` のテスト |
| `tutorials/pitzDaily/` | `simpleFoam` | RAS の定番ケース。同梱ケースで唯一の乱流ケースであり、乱流モデルのヘルプを実際に確認できる場所 |
| `tutorials/oneBlocks/` | `icoFoam` | 3-D 単一ブロック・`blockMeshDict` 編集と 3-D メッシュビューア |
| `tutorials/oneBlocks-vars/` | `icoFoam` | `oneBlocks` の変数置換・コンパクト面記法バリアント |
| `tutorials/nineBlocks/` | `icoFoam` | 3×3 マルチブロック・正規表現パッチ |
| `tutorials/nineBlocks-vars/` | `icoFoam` | `nineBlocks` の変数置換・コンパクト面記法バリアント |
| `tutorials/topoSetShapes/` | `icoFoam` | 3D ビューアがオーバーレイできる `topoSetDict` のジオメトリソースを、1 つの 3×3×3 ブロックに網羅 |
| `tutorials/samplingShapes/` | `icoFoam` | 同じことをサンプリングオーバーレイについて行ったケース: プローブ点・線・点群・平面の 2 通りの記法 |

`cavity/` 各ケース・`snappyMultiRegionHeater`・`damBreak`・`pitzDaily` は OpenFOAM v2512 標準チュートリアルセットから取得しています。`oneBlocks*` および `nineBlocks*` は FoDE テスト用に cavity をベースにしたカスタム `blockMeshDict` ケースです。

**ライセンス:** これらのケースファイルは **GPL-3.0** でライセンスされています（FoDE ソースコードの AGPL-3.0 とは別です）。詳細は `tutorials/README.md` を参照してください。

## 引用

引用は必須ではありませんが、FoDE が研究の役に立った場合は、以下を引用いただけると開発の励みになります:

> Shinji Nakagawa,
> Foam Dictionary Editor: A GUI-based open-source tool for OpenFOAM case configuration,
> *SoftwareX*, Volume 35, 2026, 102852, ISSN 2352-7110,
> [https://doi.org/10.1016/j.softx.2026.102852](https://doi.org/10.1016/j.softx.2026.102852)
> ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2352711026003444))

## ライセンス

Copyright (C) 2025-2026 Shinji NAKAGAWA。[GNU Affero General Public License v3.0 以降](LICENSE)（AGPL-3.0-or-later）で配布されます。

本リポジトリには OpenFOAM 由来の素材が含まれており、それらは上記ライセンスの対象外です。同梱のチュートリアルケース、抽出したキーワード一覧、生成された乱流スキーマモジュール中の引用ドキュメントが該当します。これらは GPL-3.0-or-later であり、権利者は複数です（OpenFOAM Foundation、OpenCFD Ltd、Upstream CFD GmbH、Keysight Technologies）。ファイルごとの表示は [THIRD-PARTY.md](THIRD-PARTY.md) にあります（手で管理するのではなくソースから生成しています）。

## 免責事項

This offering is not approved or endorsed by OpenCFD Limited, producer and distributor of the OpenFOAM software via [www.openfoam.com](http://www.openfoam.com/), and owner of the OPENFOAM® and OpenCFD® trade marks.

## 謝辞

- [PySide6 (Qt for Python)](https://doc.qt.io/qtforpython/) — GUI フレームワーク（LGPL v3）
- [pyVista](https://pyvista.org/) / [VTK](https://vtk.org/) — `blockMeshDict`、`topoSetDict`、`snappyHexMeshDict` ジオメトリの 3D ビューア（BSD-3-Clause、オプション）
- [xterm.js](https://xtermjs.org/) — ターミナルパネルで使用するターミナルエミュレータ（MIT）。初回起動時に jsDelivr から自動ダウンロードされ `ui/xterm/` にキャッシュされます
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — テストフレームワーク（開発時のみ）

[OpenFOAM Foundation](https://openfoam.org/) および [OpenCFD / ESI Group](https://www.openfoam.com/) をはじめ、OpenFOAM をフリーのオープンソース CFD ソフトウェアとして開発・維持してきたすべての貢献者の方々に深く感謝いたします。
