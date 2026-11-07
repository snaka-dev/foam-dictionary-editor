# FoDE — スクリーンショットギャラリー

FoDE の各パネル・オーバーレイ・ダイアログを画面で紹介します。全機能リファレンスは [USER_GUIDE_ja.md](../USER_GUIDE_ja.md)、インストールとクイックスタートは [README_ja.md](../README_ja.md) を参照してください。

以下の **メインウィンドウ** と **BlockMesh 3D ビューア** の各画像は、`tools/screenshot_specs.json` に記述したウィンドウ状態から `tools/capture_screenshots.py` が撮影しています。そのため 1 コマンドで撮り直せ、ライト/ダークのペアはテーマ以外がまったく同一になります。詳細は [スクリーンショットの撮影](../DEVELOPER_ja.md#スクリーンショットの撮影) を参照してください。**ダイアログとメニュー** の各画像は別途撮影しています: 開いたメニューやダイアログはメインウィンドウのフレームの一部ではなく、独立した X ウィンドウであるためです。ダイアログは `tools/capture_dialog.py` が撮影し、Tools メニューは、メニューを開いて画面をウィンドウの範囲で切り抜く `capture_screenshots.py` のショットです。

## メインウィンドウ

![メインウィンドウ — Tree と Editor タブ](images/main-window-tree-editor.png)

ツリー表示とプレーンテキストエディタを並べて表示し、双方向に同期します。ツリーで値を編集するとエディタ側の該当行がハイライトされ、逆にテキストを編集してツリーへ適用することもできます。詳細は [現在のUI構成](../USER_GUIDE_ja.md#現在のui構成) を参照してください。

![メインウィンドウ — ダークテーマ](images/main-window-tree-editor-dark.png)

同じ画面を **Settings > Appearance** の **Dark** で表示したもの。テーマはウィンドウが描画するすべてに適用され、エディタのシンタックスハイライト、行番号のガター、選択行の背景色と文字色も含まれます。選択行の配色はデスクトップから継承するのではなく FoDE 自身が算出するため、どのアクセントカラーを設定していても選択行が読みづらくなることはありません。詳細は [外観と配色](../USER_GUIDE_ja.md#外観と配色) を参照してください。

![メインウィンドウ — Cases タブ](images/main-window-cases-tab.png)

ファイル一覧の隣にある **Cases** タブ。OpenFOAM インストールの `simpleFoam` チュートリアルを表示し、`pitzDaily` を開いた状態です。**◆** はそのディレクトリがケースであることを示し、開いているケースは太字になります — つまりこの一覧は「今どのケースにいるのか」の答えも兼ねます。`bump2D` と `turbulentFlatPlate` には ◆ が付かず、代わりに展開用の矢印が付いています。これらはケースそのものではなくケースを含むフォルダであり、他のフォルダと同様に中へ入れます。ケースをダブルクリックすると展開ではなく*開く*のがこの区別の要点です — ケースの中身を扱うのは **Files** タブの役目です。パスは末尾ではなく中央を省略するため、220 ピクセル幅のカラムでも先頭のドライブと現在のフォルダ名の両方が読めます。下端の **Browse…** でより本格的な [Case Browser](#case-browser) を開けます。「[ケースナビゲーター](../USER_GUIDE_ja.md#ケースナビゲーター)」を参照。

![メインウィンドウ — Boundary と Editor タブ](images/main-window-boundary-editor.png)

Boundary view タブ: すべてのフィールドファイルにまたがる境界パッチをテーブル（パッチ × フィールド）として一覧表示し、各フィールドファイルを個別に開くことなく境界条件全体を一目で確認・編集できます。各セルにはパッチの `type` が表示され、**Lines per cell** を増やすとその下のエントリ（`value uniform (10 0 0)` など）も表示されます。詳細は [境界条件ビュー](../USER_GUIDE_ja.md#境界条件ビュー) を参照してください。

![メインウィンドウ — 2 つのケースの比較](images/main-window-compare.png)

比較モード。`cavity` チュートリアルを開き、`cavityGrade` を参照側に設定した状態です。2 つのツリーが左右に並び、違いは自分で探すのではなくその場でマークされます。値が異なるエントリはハイライトされ、片側にしか存在しないエントリも同様です — この例の `grad(p)` は開いているケースにはあり、参照側にはありません。ファイル一覧にも同じ情報が 1 段上のレベルで表示されるため、ファイルを 1 つも開かないうちにケース全体を見渡せます。各ファイルには差分のあるエントリ数が付き、片側に存在しないファイルはグレー表示になります。比較しても内容は一切変更されません。**Clear** で比較を終了します。詳細は [ケース比較](../USER_GUIDE_ja.md#ケース比較) を参照してください。

## BlockMesh 3D ビューア

3D パネルは `blockMeshDict` のジオメトリを描画し、`topoSetDict`・`snappyHexMeshDict`・`setFieldsDict`・サンプリング辞書のジオメトリも重ねて表示します。ケースを開いた時点で描画され、編集にも追従します。詳細は [BlockMesh パネル](../USER_GUIDE_ja.md#blockmesh-パネル) を参照してください。

### topoSetDict オーバーレイ — topoSetShapes ケース

![topoSetDict オーバーレイ — topoSetShapes ケース](images/blockMesh3Dview-topoSet-topoSetShapes.png)

同梱の `tutorials/topoSetShapes` ケース。その `topoSetDict` は、オーバーレイが描画できるすべてのジオメトリソースを網羅しています: ボックス（通常形・`min`/`max` 形・複数ボックスの `boxes` 形）、回転したボックス、中実および中空の球、円柱と円錐のファミリー、点マーカー、`planeToFaceZone` の平面。いずれもブロックメッシュのワイヤーフレーム内に重ねて描画され、形状の中心に名前バッジが表示されます。各形状の色はそれを生成した action に対応しているため、`new`・`add`・`subtract` のセットを一目で区別できます。形状が入れ子になっている箇所ではバッジが重なります。またブロックメッシュの外側へはみ出す形状はクリップして描画され、バッジに `(clipped)` と表示されます（この例では `midPlane`）。エディタペインには `#eval` 式を使った `coneToCell` エントリが表示されています。詳細は [topoSetDict オーバーレイ](../USER_GUIDE_ja.md#toposetdict-オーバーレイ) を参照してください。

### topoSetDict オーバーレイ — floatingObject ケース

![topoSetDict オーバーレイ — floatingObject ケース](images/blockMesh3Dview-topoSet-floatingObject.png)

OpenFOAM の `floatingObject` チュートリアル。単位ブロック内に青色の `boxToCell` セルセット（`c0`）が描画されています。詳細は [topoSetDict オーバーレイ](../USER_GUIDE_ja.md#toposetdict-オーバーレイ) を参照してください。

### setFieldsDict オーバーレイ — damBreak ケース

![setFieldsDict オーバーレイ — damBreak ケース](images/blockMesh3Dview-setFields-damBreak.png)

同梱の `tutorials/damBreak` ケース。`setFieldsDict` の `regions` リストがブロックメッシュ上にオレンジ色で描画され、各リージョンにはそれが設定するフィールド値の要約がバッジとして表示されます。これにより `setFields` を実行する前に、初期の水柱をメッシュと照らし合わせて確認できます。この例のリージョンは準 2 次元ケースの奥行き全体をまたぐように記述されていてメッシュより大きくはみ出すため、メッシュに合わせてクリップして描画され、バッジには `(clipped)` と表示されます。辞書ファイル自体は変更されず、STL エクスポートではクリップ前の完全な形状が書き出されます。ツリーで `box` 行を選択すると、エディタがそれを定義している行までスクロールします。詳細は [setFieldsDict オーバーレイ](../USER_GUIDE_ja.md#setfieldsdict-オーバーレイ) と [オーバーレイのクリップ表示](../USER_GUIDE_ja.md#オーバーレイのクリップ表示) を参照してください。

### サンプリングオーバーレイ — samplingShapes ケース

![サンプリングオーバーレイ — samplingShapes ケース](images/blockMesh3Dview-sampling-samplingShapes.png)

同梱の `tutorials/samplingShapes` ケース。`topoSetShapes` のサンプリング版で、ビューアが描画できるサンプリングジオメトリのすべての種類を 1 つの 3×3×3 ブロック内に収めています。probes と cloud の定義は点マーカーとして、始点・終点を持つ sets はチューブとして、サンプリング平面は円板として描画されます。サンプリングは他のオーバーレイと違って専用の辞書ファイルを持たない点が特徴です — `controlDict` 内の function object としても、スタンドアロンの辞書としても書け、後者にはメンバーリストの記法が 2 通りあります。そこでこのケースでは定義を 3 か所すべてに分散させており、パネルはそれらをマージしたうえで、**sample ▾** メニューの各行に由来ファイルをタグ表示します。2 つの平面はいずれも `(clipped)` と表示されます: 平面は無限に広がるため、描画される円板は表示専用であり、常に表示先のメッシュに合わせて切り取られるからです。詳細は [サンプリングオーバーレイ](../USER_GUIDE_ja.md#サンプリングオーバーレイ) と [オーバーレイのクリップ表示](../USER_GUIDE_ja.md#オーバーレイのクリップ表示) を参照してください。

### snappyHexMeshDict オーバーレイ — motorBike ケース（サイドバイサイド）

![snappyHexMeshDict オーバーレイ — motorBike ケース](images/blockMesh3Dview-snappyHex-motorBike.png)

OpenFOAM の `motorBike` チュートリアルをサイドバイサイドモードで表示: ツリーと 3D ビューが並んで表示されます。motorBike の `triSurfaceMesh` ジオメトリに加えて、紫色の `refinementBox` リージョン（"inside" として分類）と `locationInMesh` マーカーが重ねて描画され、ツリーとエディタは `refinementRegions` エントリにフォーカスしています。詳細は [snappyHexMeshDict オーバーレイ](../USER_GUIDE_ja.md#snappyhexmeshdict-オーバーレイ) と [サイドバイサイドモード](../USER_GUIDE_ja.md#サイドバイサイドモード) を参照してください。

![snappyHexMeshDict オーバーレイ — motorBike ケース、ダークテーマ](images/blockMesh3Dview-snappyHex-motorBike-dark.png)

同じオーバーレイを同じカメラ位置からダークテーマで表示したもの — 同じ spec を 2 回撮影しているため、テーマ以外は何も違いません。3D シーンは固有のパレットを持たないため、配色は明示的に指定されています: シーンの背景、その上の範囲表示、グリッドの目盛り数値と軸タイトル、方位軸の X/Y/Z の文字、頂点番号とブロック番号はテーマに追従して切り替わります。一方、パッチやオーバーレイの色は切り替わりません — motorBike の表面は teal、`refinementBox` は紫のままです。これらは何を見ているかを識別するための色だからです。形状名バッジが両テーマで明るいラベルのままなのも同じ理由で、下にあるジオメトリがどの色であっても読めなければならないためです。詳細は [外観と配色](../USER_GUIDE_ja.md#外観と配色) を参照してください。

## ダイアログとメニュー

### Case Browser

![Case Browser dialog](images/case-browser-dialog.png)

OpenFOAM インストールの `simpleFoam` チュートリアルを表示している非モーダルな Case Browser。左にフォルダツリー、右に現在のフォルダの中身、下端に選択対象へ適用されるアクションが並びます。**◆** は OpenFOAM ケースであるディレクトリを示し、◆ が付いていない 2 行こそがこのビューの要点です。`bump2D` と `turbulentFlatPlate` はケースそのものではなくケースを含むフォルダなので、マーカーの代わりに展開用の矢印が付き、他のフォルダと同様に中へ入れます。一方でブラウザがしないのはケースの中へ入ることです — ケースの中身を扱うのは[ファイル一覧](../USER_GUIDE_ja.md#ファイル一覧の挙動)の役目だからです。ケースが選択されているため、ケース専用のアクション **Open Case**・**Compare**・**Duplicate…** が有効になっています。**Move…**・**Rename…**・**Delete…** は任意のフォルダに適用できます。「[Case Browser ウィンドウ](../USER_GUIDE_ja.md#case-browser-ウィンドウ)」を参照。

### Find OpenFOAM Examples

![Find OpenFOAM Examples ダイアログ](images/find_foam_example.png)

非モーダルの Find OpenFOAM Examples ダイアログ。インストールの `tutorials/` と `etc/caseDicts/` をキーワードで検索します（この例では `topoSetDict` で 200 件が一致）。ヒットは所属するケースごとにグループ化され、選択するとそのファイルがシンタックスハイライト付きでプレビューされます。下端のボタンは、検索結果を実際の作業につなげるためのものです: ファイルをコピーする、そのチュートリアルをケース比較の参照側として開く、あるいはケース全体を編集可能な新しいケースとして複製する。詳細は [Find OpenFOAM Examples](../USER_GUIDE_ja.md#find-openfoam-examples) を参照してください。

### メッシュ・場のツールを実行する

![Run setFields オプションダイアログ](images/run-tool-dialog.png)

Tools メニューの **Run …** アクションの背後にあるオプションダイアログ。ここでは同梱の `damBreak` ケースに対する `setFields` です。実行ファイルのフラグを覚えておくことを求める代わりに、各ツールについて厳選したフラグを入力欄として提示し、そこに含まれないものは **Extra options** に書きます。そして下端のボックスには、Terminal タブへ実際に送られるコマンドがそのまま表示され、設定を変えるたびに更新されます。組み立てられるコマンドは必ず最後に `log.<ツール名>` へ tee するため、その後 [View Log Summary](#view-log-summary) が読むログが残ります。ツールの落とし穴に先回りするのもこのダイアログの役割です: `setFields` は `0/` をその場で書き換えるため、再実行すると既に設定した値にさらに重ねてしまいます。そこで `0.orig/` から `0/` を復元する選択肢が既定でオンになっており、実際に実行される前置きコマンドとしてコマンド欄にも現れています。詳細は [Run setFields](../USER_GUIDE_ja.md#run-setfields) を参照してください。

### Add Function Object

![Add Function Object ダイアログ](images/add-function-object-dialog.png)

同梱の `damBreak` ケースで **Tools > Add Function Object…** を開き、プローブを選んだところです。左の一覧は FoDE 独自のものではなく、上部に表示されている OpenFOAM のインストールが同梱するテンプレートです。そのため、同じ関数でも 2 つのフォークで名前や形が異なっても、入力欄は常に実際に使う OpenFOAM と一致します。入力欄にはそのテンプレートが設定する項目だけが、種類に合った形で表示されます。フィールド名は **▾** でケースから選べ、点は 1 行に 1 つ `x y z` で入力します。ここでのプローブの位置は、このケースでは角にあたるテンプレートの例 `(0 0 0)` ではありません。FoDE が `blockMeshDict` から読んだメッシュの中心に置き、入力欄の下の注記にそう書かれています。**書き出すファイル** は `system/probes` に書かれる正確なテキストで、設定の部分までスクロールされ、入力に合わせて更新されます。ダイアログを開いている間、3D ビューはメッシュと重ねてプローブを描画します。[Add Function Object](../USER_GUIDE_ja.md#add-function-object) を参照してください。

### ソルバーを実行する

![Run Solver ダイアログ](images/run-solver-dialog.png)

同梱の `damBreak` ケースで **Tools > Run Solver…** を開いたところです。ソルバーは `controlDict` の `application` から読み取られ、変更もできます。**Run in parallel** は、ケースが実際に分割されているプロセッサ数を使うので、コマンドは `mpirun -np 4 … -parallel` になります。**Keep running after FoDE closes** を選ぶと、FoDE を閉じても止まらないように切り離して実行し、後から **Tools > Stop Background Run** で書き出し済みの時刻に止められます。どの Run ダイアログでも同じく、下部のコマンドがそのまま Terminal に送られます。詳細は [Run Solver](../USER_GUIDE_ja.md#run-solver) を参照してください。

### Run postProcess

![Run postProcess ダイアログ](images/run-post-process-dialog.png)

同梱の `pitzDaily` ケースで **Tools > Run postProcess…** を開き、`yPlus` を選んだところです。関数の一覧は、ケース自身の関数オブジェクト（ここでは `streamlines`）から始まり、続いて OpenFOAM がテンプレートから直接実行できるよく使うものが並びます。`yPlus` はソルバーの乱流モデルを必要とするため **ソルバーを通して実行** が自動でチェックされ、コマンドは `simpleFoam -postProcess` になっています。そのままの `postProcess` では、エラーなく終了しても何も計算されません。出力は `log.postProcess` に書かれ、ソルバー自身のログには書かれません。[Run postProcess](../USER_GUIDE_ja.md#run-postprocess) を参照してください。

### View Log Summary

![View Log Summary ダイアログ](images/log-summary-dialog.png)

非モーダルの View Log Summary ダイアログ。`pitzDaily` の実行が残した `log.simpleFoam` を読み込み、2,898 行のソルバー出力を画面に見えている内容まで凝縮しています: 実行がどこまで進んだか、収束したか、残差が最終的にどうなったか、正常に終了したか。ケース内で最後に書き込まれた `log.*` が自動的に選ばれ、**Browse…** で別のログを選べます。要約だけでは足りない場合のために、**Raw Log** タブに元のテキストがそのまま入っています。`blockMesh`・`snappyHexMesh`・`topoSet` のログはそれぞれ専用の文法で解析され、そのユーティリティにとって重要な情報 — メッシュ規模、リファインメントの各フェーズ、セットごとの個数 — を代わりに報告します。また繰り返し現れる警告は 1 件ずつ並べるのではなくまとめられます。非モーダルであるため、メインウィンドウの横に置いたまま編集を続けられます。詳細は [View Log Summary](../USER_GUIDE_ja.md#view-log-summary) を参照してください。

### Tools メニュー

![Tools メニュー](images/tools-menu.png)

Tools メニューは、FoDE が辞書の編集をやめて OpenFOAM 自身に処理を渡す場所です。各項目は対象ごとにグループ分けされており、ツールを実行する項目は先にオプションダイアログを開きます。いずれも開いているケース — この例では `pitzDaily` — に対して実行されます。詳細は [Tools メニュー](../USER_GUIDE_ja.md#tools-メニュー) を参照してください。
