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

初回起動時にインターネット接続を推奨します — ターミナルエミュレータ xterm.js が `ui/xterm/` へ自動ダウンロードされます。接続がない場合はシンプルなフォールバックターミナルが使われます。インターネット接続のある状態でアプリを再起動すると再試行されます。手動で配置する場合は以下のファイルを `ui/xterm/` に置いてください:

| ファイル | URL |
|---|---|
| `xterm.js` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/lib/xterm.js` |
| `xterm.css` | `https://cdn.jsdelivr.net/npm/@xterm/xterm@6.0.0/css/xterm.css` |
| `xterm-addon-fit.js` | `https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.11.0/lib/addon-fit.js` |

## 基本的な使い方

1. **起動**

   ```bash
   python3 main.py
   ```

2. **ケースを開く** — いずれかを選択:
   - *自分のケース:* **Case > Open Case** → ケースディレクトリを選択
   - *チュートリアルから始める:* **Case > Duplicate from Case Library** → `$FOAM_TUTORIALS` を参照 → 作業ディレクトリへコピー

3. **ファイルを選択** — 左パネルから対象ファイルを選ぶ（例: `system/controlDict`、`0/U`）

4. **編集** — ツリービューまたは下部のテキストエディタで値を編集する

5. **境界条件を確認・調整** — **Boundary** タブで全パッチと全フィールド変数の境界条件を一覧表示。セルをダブルクリックして編集できる

6. **保存** — `Ctrl+S`（現在のファイル）または `Ctrl+Shift+S`（変更済みファイルをすべて保存）

7. *（オプション）* **ソルバーを実行** — **Terminal** タブから直接 `blockMesh`、`interFoam` などの OpenFOAM コマンドを実行できる。ターミナルはケースディレクトリで自動的に起動する

## 主な機能

**ファイル管理**
- 代表的な辞書ファイル（`controlDict`、`fvSchemes`、`fvSolution`、`blockMeshDict`、`snappyHexMeshDict` など）を自動表示
- マルチリージョンケース構造やフィールドディレクトリ（`0/`、`0.orig/`）を自動検出
- 任意のディレクトリをファイル一覧に追加可能。`0/` と同様にディレクトリ内のファイルを自動スキャン。カスタムフィールドディレクトリ（`initial/`）、再起動タイムステップ（`0.5/`）、深い階層のサブディレクトリ（`lagrangian/chemkin/`）などに対応
- ファイルパネルからファイルの追加・作成・複製・バックアップ・削除が可能
- 現在のケースを新しいケースとして保存したり、既存ケースを複製したりできる

**ツリーとテキストの編集**
- 辞書エントリの閲覧・編集ができる構造化ツリービュー
- 生テキストエディタをいつでもフォールバックとして利用可能
- ツリーとテキストの双方向同期
- 右クリックメニューでエントリの追加・複製・コメントアウト・削除が可能

**境界条件ビュー**
- 全フィールド変数の境界条件を一つのテーブルで確認
- テーブル上でパッチエントリを直接編集・作成・削除・コピー・ペースト
- 全フィールドファイルへのパッチ一括追加・削除

**スキーマヘルプ**
- 主要な設定項目（`controlDict`、`fvSchemes`、`fvSolution`、`blockMeshDict`、`snappyHexMeshDict`）の説明と有効な選択肢を組み込み表示
- 独自のスキーマモジュール（Python ファイル）で拡張可能

**統合ターミナル**
- フル PTY ターミナル（Linux/macOS で `QtWebEngineWidgets` が利用可能な場合）またはシンプルなフォールバック
- ケースを開くと自動的にそのディレクトリへ移動

**参照リンク**
- **Help > Resources...** から OpenFOAM 公式ドキュメントへのリンクを確認できます
- **My Links** タブで個人用参照リンクの追加・編集・並び替え・削除が可能。ダブルクリックでブラウザを開きます

## 全リファレンス

すべてのパネル・メニュー・操作手順の詳細については [USER_GUIDE_ja.md](USER_GUIDE_ja.md) を参照してください。
プロジェクト構成・開発環境のセットアップ・テストについては [DEVELOPER_ja.md](DEVELOPER_ja.md) を参照してください。

## ライセンス

Copyright (C) 2025-2026 Shinji NAKAGAWA。[GNU Affero General Public License v3.0 以降](LICENSE)（AGPL-3.0-or-later）で配布されます。

## 免責事項

This offering is not approved or endorsed by OpenCFD Limited, producer and distributor of the OpenFOAM software via [www.openfoam.com](http://www.openfoam.com/), and owner of the OPENFOAM® and OpenCFD® trade marks.

## 謝辞

- [PySide6 (Qt for Python)](https://doc.qt.io/qtforpython/) — GUI フレームワーク（LGPL v3）
- [xterm.js](https://xtermjs.org/) — ターミナルパネルで使用するターミナルエミュレータ（MIT）。初回起動時に jsDelivr から自動ダウンロードされ `ui/xterm/` にキャッシュされます
- [pytest](https://pytest.org/) / [pytest-qt](https://pytest-qt.readthedocs.io/) — テストフレームワーク（開発時のみ）
