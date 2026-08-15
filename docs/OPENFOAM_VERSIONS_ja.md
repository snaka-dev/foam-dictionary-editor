# ケースファイルに影響する OpenFOAM バージョン間の違い

[English version](OPENFOAM_VERSIONS.md)

OpenFOAM のケースは、多くの人が期待するほどにはリリース間で可搬ではありません。ソルバ名が変わり、キーが改名され、そして最も意外なことに、**辞書ファイルそのものが改名されます**。OpenFOAM 7 のチュートリアルからコピーしてきた `constant/transportProperties` は、OpenFOAM 12 では単に読まれません。12 が探すのは `constant/physicalProperties` だからです。警告は出ません。ファイルはそこに置かれたまま、実行は既定値を使うか、ルックアップエラーで止まります。

このページは、FoDE が実測した改名を記録したものです。手元にあるケースが、いま動かそうとしている OpenFOAM と噛み合っているかを一目で判断できます。

## まず: これはどの OpenFOAM か

どちらのフォークも、辞書の先頭バナーに自分の素性を書き込んでいます。Editor タブで任意のファイルを開き、4 行目を読んでください。

```
|  \\    /   O peration     | Version:  v2606                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
```

- **`www.openfoam.com`** とバージョン `vYYMM` — **OpenCFD** フォーク（openfoam.com）。年 2 回リリース: `v2506`、`v2512`、`v2606`、…
- **`openfoam.org`** と数字のみのバージョン — **Foundation** フォーク（openfoam.org）。ほぼ年 1 回: `9`、`10`、`11`、`12`、…

この 2 つは 1 つのソフトの版違いではなく、別系統です。以下の改名はほぼすべて Foundation 側で起きているため、どのリリースかよりも**どちらのフォークか**のほうが重要です。

## Foundation の改名

各リリースが実際に `tutorials/` ツリーに同梱しているファイル数を数えたものです。`0` は、そのリリースのチュートリアルがその名前をまったく使っていないことを意味します。

<!-- BEGIN generated: foundation-table -->
| ファイル | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `constant/turbulenceProperties` | 167 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/momentumTransport` | 0 | 167 | 170 | 177 | 184 | 188 | 198 | 204 |
| `constant/transportProperties` | 110 | 111 | 112 | 0 | 0 | 0 | 0 | 0 |
| `constant/thermophysicalProperties` | 87 | 86 | 95 | 0 | 0 | 0 | 0 | 0 |
| `constant/physicalProperties` | 1 | 1 | 1 | 158 | 160 | 166 | 181 | 185 |
| `constant/fvOptions` | 23 | 22 | 0 | 0 | 0 | 0 | 0 | 0 |
| `system/fvOptions` | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/fvModels` | 0 | 0 | 42 | 46 | 66 | 72 | 82 | 91 |
| `system/fvConstraints` | 0 | 0 | 43 | 44 | 50 | 52 | 55 | 58 |
| `constant/thermophysicalTransport` | 0 | 2 | 7 | 7 | 7 | 7 | 8 | 11 |
| `constant/regionProperties` | 4 | 4 | 5 | 5 | 0 | 0 | 0 | 0 |
| `system/functions` | 0 | 0 | 0 | 0 | 0 | 115 | 128 | 136 |
| `constant/momentumTransfer` | 0 | 0 | 0 | 0 | 0 | 0 | 29 | 31 |
<!-- END generated: foundation-table -->

列を上から下に読むと、きれいな切り替わりが 4 つ見えます。

**OpenFOAM 8 — 乱流。** `constant/turbulenceProperties` が `constant/momentumTransport` になります。同じ 167 ファイルが 1 リリースで名前を変えただけです。中身の構造は保たれています（`simulationType`、`RAS`/`LES` ブロック、`model`、`turbulence`、`printCoeffs`）。分離された熱側のために `constant/thermophysicalTransport` が同時に現れます。

**OpenFOAM 9 — `fvOptions` が 2 つに分かれる。** 1 つだった `fvOptions` が `constant/fvModels`（生成・消滅項、つまり方程式に**加える**もの）と `system/fvConstraints`（値を**固定する**もの）になります。OpenFOAM 8 から持ち込んだ `fvOptions` はどちらとしても読まれません。しかも分割は意味的なものなので `mv` 一発の改名では済まず、エントリを 2 つの新ファイルに仕分ける必要があります。

**OpenFOAM 10 — transport と thermophysical が統合される。** `constant/transportProperties` と `constant/thermophysicalProperties` の両方が 1 つの `constant/physicalProperties` に置き換わります。ほぼすべてのケースが影響を受けるため、これが最も痛い変更です。2 つの名前で 207 ファイルあったものが、1 つの名前で 158 ファイルになりました。（それ以前の 1 件は実在しますが無関係です。`electrostaticFoam` は OpenFOAM 7 の時点で `physicalProperties` を持っています。）

**OpenFOAM 11 — `regionProperties` が消える。** マルチリージョンの設定方法が刷新され、このファイルはチュートリアルから姿を消します。

改名ではなく追加のものが 2 つあります。`system/functions` は **OpenFOAM 12** で登場し、従来 `controlDict` の中にあった function object のブロックの置き場所になりました。`constant/momentumTransfer` は **OpenFOAM 13** で登場し、多相流の運動量交換を扱います。

OpenFOAM 14 は辞書ファイルを新設も改名もしていません。ケースファイルに対する変更は 1 階層下、`constant/momentumTransport` の中で起きています（後述の副辞書の節を参照）。

相バリアントは基底名に追随します。OpenFOAM 10 より前に `thermophysicalProperties.air` と `thermophysicalProperties.water` があったケースは、10 以降では `physicalProperties.air` と `physicalProperties.water` になります。`momentumTransport.air` も同様です。

## OpenCFD 側: 何も動かない

同じ測定を OpenCFD のリリースに対して行った結果です。

<!-- BEGIN generated: opencfd-table -->
| ファイル | v2106 | v2112 | v2206 | v2212 | v2306 | v2312 | v2406 | v2412 | v2506 | v2512 | v2606 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `constant/turbulenceProperties` | 335 | 354 | 354 | 368 | 370 | 421 | 424 | 435 | 436 | 438 | 438 |
| `constant/transportProperties` | 245 | 264 | 246 | 256 | 259 | 312 | 315 | 331 | 332 | 333 | 333 |
| `constant/thermophysicalProperties` | 162 | 176 | 181 | 182 | 182 | 182 | 182 | 182 | 182 | 183 | 184 |
| `constant/fvOptions` | 39 | 41 | 39 | 42 | 42 | 42 | 42 | 43 | 43 | 43 | 43 |
| `system/fvOptions` | 13 | 15 | 16 | 16 | 16 | 41 | 41 | 43 | 43 | 44 | 45 |
| `constant/regionProperties` | 14 | 17 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 19 | 19 |
| `constant/momentumTransport` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/physicalProperties` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `constant/fvModels` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `system/fvConstraints` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
<!-- END generated: opencfd-table -->

5 年・11 リリースを通して、これらのファイル名は 1 つも変わっていません。数はおおむねチュートリアルの増加に従って増えますが、単調ではありません。v2112 と v2206 の間の再編成でケースが移動したため、何も改名されていないのに `transportProperties` は 264 から 246 へ減っています。これは両端だけでなく行全体を読むべき理由でもあります。改名は「同じリリースで一方の列がゼロになり、他方が現れる」形で出ますが、ここではどの行もそうなっていません。したがって:

- **OpenCFD のリリース間**でケースを移動しても、ファイル名で壊れることはほとんどありません。
- **フォークをまたぐ**移動、あるいは **Foundation の 8/9/10 をまたぐ**移動では、たいてい壊れます。

裏を返せば、ファイル名は信頼できるフォーク判定材料です。`constant/momentumTransport` を含むケースは Foundation 8 以降のケースであり、OpenCFD のどのリリースもそのファイルを読みません。

## フォーク間で名前が違うもの

改名ではなく、2 つのフォークが同じ役割に別の名前を選んだだけのものです。

| 役割 | Foundation | OpenCFD |
|---|---|---|
| 乱流モデル（v8 以降） | `constant/momentumTransport` | `constant/turbulenceProperties` |
| 輸送・熱物性（v10 以降） | `constant/physicalProperties` | `constant/transportProperties`、`constant/thermophysicalProperties` |
| ソースと拘束（v9 以降） | `constant/fvModels`、`system/fvConstraints` | `constant/fvOptions`、`system/fvOptions` |
| サーフェス特徴抽出 | `system/surfaceFeaturesDict` | `system/surfaceFeatureExtractDict` |

片方にしか存在しない辞書もあります。`system/optimisationDict` と `constant/adjointRASProperties`（随伴最適化）、`system/meshDict`（cfMesh）、finite area の 3 点（`faSchemes` / `faSolution` / `faMeshDefinition`）は OpenCFD 側。`system/createZonesDict`、`system/setWavesDict`、`constant/cloudProperties` は Foundation 側です。

## ファイルの中のキーの改名

キーも改名されます。しかもファイルよりはるかに頻繁です。両フォークのソースから互換宣言を走査すると、旧称→新称の組が約 100 得られます。FoDE はこれを文書ではなく **Detail ペイン**で示します。答えが、いま見ているキーごとに違うからです。

- **renamed**（改名）のキーは、後継の名前と、旧称が現行でなくなったリリースを示します。`convertToMeters` → `scale`（v1012）、`minMedianAxisAngle` → `minMedialAxisAngle`（v1712）。
- **ineffective**（無効）のキーは、公式チュートリアルには現れるがどのリリースも読まないもので、書いても何も起きません。典型例は `minFlatness` で、OpenFOAM 2.3.x 以来 `motorBike` に入っている一方、両フォークが読むのは `minFaceFlatness` です。

互換エントリは永続ではありません。OpenCFD は `minMedianAxisAngle` を v2206 まで受け付け、v2212 で削除しました。つまり古いインストールでは効く綴りが、新しいほうでは黙って無視されます。Foundation は今も両方を受け付けます。FoDE が把握している範囲では、Detail ペインがそのことを表示します。

**さらに、どちらの綴りが現行かでフォーク同士が食い違うことがあります。** そのため「新しい名前を選んでおけばよい」という指針は、それだけでは誤りになります。Foundation 11 は `turbOnFinalIterOnly` を `transportCorrectionFinal` へ改名し、以来どちらも受け付けています。一方 OpenCFD は `turbOnFinalIterOnly` を*現行*の名前として読み、もう一方の名前をそもそも持ったことがありません。`fvSolution` の `SIMPLErho` / `simpleRho` の組も同じ分かれ方をし、しかもさらに古く、v7 以降のすべての Foundation リリースが `simpleRho` を読みます。つまりどちらについても「現代的な綴り」は 1 つに定まりません。正しいのは動かしているフォーク次第であり、フォークをまたいでケースを持ち込むときは、そのまま保つのではなくキーを書き換える必要があります。

### 実測した組

下の表は約 100 の全部ではありません。foamlore が取得しているソースのサブツリー — FoDE がスキーマを持つ辞書の読み取り側と、それらのツリーがたまたま触れている範囲 — で宣言されている改名のすべてを、19 チェックアウト全体にわたって測ったものです。一度数えた値ではなく、ソースから再生成しています。ダッシュはそのフォークがその組を宣言していないことを示し、上で述べた食い違いはこれで一目で読めます。

範囲が示すのは*宣言*の所在であり、旧称が今も通るかどうかとは別です。Foundation 7 と 8 は `SIMPLErho` と `simpleRho` の両方を、互換のために残す旨のコメント付きで、素の lookup 2 回で読んでいます。受け付けてはいるが宣言はしていないため、表のその行は 9 から始まります。

<!-- BEGIN generated: renames-table -->
| 旧 → 新 | 読み取り元 | Foundation | OpenCFD |
|---|---|---|---|
| `centre` → `origin` | `0/<field> boundaryField entry` | — | v2106〜v2606 (api 1712) |
| `redirectType` → `name` | `0/<field> boundaryField entry` | — | v2106〜v2606 (api 1706) |
| `relaxation` → `qrRelaxation` | `0/<field> boundaryField entry` | — | v2106〜v2606 (api 1712) |
| `motionSolver` → `pointMeshMover` | `constant/dynamicMeshDict` | 14 | — |
| `LESModel` → `model` | `constant/momentumTransport` / `constant/turbulenceProperties` | 9〜14 | v2106〜v2606 (api -2006) |
| `RASModel` → `model` | `constant/momentumTransport` / `constant/turbulenceProperties` | 9〜14 | v2106〜v2606 (api -2006) |
| `laminarModel` → `model` | `constant/momentumTransport` / `constant/turbulenceProperties` | 9〜14 | v2106〜v2606 (api -2006) |
| `transportModel` → `viscosityModel` | `constant/physicalProperties` | 10〜13 † | — |
| `Es` → `es` | `constant/thermophysicalProperties` | 12〜14 | — |
| `Esref` → `esRef` | `constant/thermophysicalProperties` | 12〜14 | — |
| `Hf` → `hf` | `constant/thermophysicalProperties` | 12〜14 | — |
| `Hs` → `hs` | `constant/thermophysicalProperties` | 12〜14 | — |
| `Hsref` → `hsRef` | `constant/thermophysicalProperties` | 12〜14 | — |
| `K` → `kappa` | `constant/thermophysicalProperties` | 9〜14 | v2106〜v2606 (api 1612) |
| `Sf` → `sf` | `constant/thermophysicalProperties` | 12〜14 | — |
| `a` → `Av` | `constant/thermophysicalProperties` | 11〜14 | — |
| `chemistrySolver` → `solver` | `constant/thermophysicalProperties` | 9〜13 | v2106〜v2606 (api -1712) |
| `convergence` → `tolerance` | `constant/thermophysicalProperties` | — | v2106〜v2606 (api 1712) |
| `inertSpecie` → `defaultSpecie` | `constant/thermophysicalProperties` | 9〜14 | — |
| `mode` → `type` | `constant/thermophysicalProperties` | — | v2106〜v2606 (api 1812) |
| `convertToMeters` → `scale` | `system/blockMeshDict` | — | v2106〜v2606 (api 1012) |
| `writeFrequency` → `writeInterval` | `system/controlDict` | 12〜14 | — |
| `CofR` → `origin` | `system/controlDict functions entry` | 14 | — |
| `Prl` → `Pr` | `system/controlDict functions entry` | 9〜14 | — |
| `alphaD` → `alphal` | `system/controlDict functions entry` | 13〜14 | — |
| `alphaDt` → `alphat` | `system/controlDict functions entry` | 13〜14 | — |
| `calcCoeff` → `mode` | `system/controlDict functions entry` | — | v2106〜v2606 (api 1812) |
| `calcTotal` → `mode` | `system/controlDict functions entry` | — | v2106〜v2606 (api 1812) |
| `nCorr` → `nCorrectors` | `system/controlDict functions entry` | 13〜14 | — |
| `name` → `faceZone` | `system/controlDict functions entry` | 11〜12 | — |
| `name` → `field` | `system/controlDict functions entry` | 11〜14 | — |
| `name` → `patch` | `system/controlDict functions entry` | 11〜12 | — |
| `regionType` → `select` | `system/controlDict functions entry` | 11〜12 | — |
| `timeVsFile` → `fileVsTime` | `system/controlDict functions entry` | 11〜14 | — |
| `SIMPLErho` → `simpleRho` | `system/fvSolution` | 9〜14 | — |
| `nCellsInCoarsestLevel` → `minCellsPerProcessor` | `system/fvSolution` | 14 | — |
| `turbOnFinalIterOnly` → `transportCorrectionFinal` | `system/fvSolution` | 11〜14 | — |
| `minMedianAxisAngle` → `minMedialAxisAngle` | `system/snappyHexMeshDict` | 12〜14 | v2106〜v2206 (api 1712) |

† すべてのチェックアウトで取得しているとは限らないサブツリー内の宣言であり、範囲は「存在する範囲」ではなく「調べた範囲」を表す。
<!-- END generated: renames-table -->

## モデルの副辞書: OpenFOAM 14 で綴りが 1 つ増えた

ファイルが改名され、キーも改名されます。そして OpenFOAM 14 では、**乱流モデルが係数を読む副辞書**の名前が 1 つ増えました。

OpenFOAM 13 までは、モデルは `<model>Coeffs` を探し、無ければ外側のブロックから直接読んでいました。

```
RAS
{
    model           kEpsilon;
    kEpsilonCoeffs  { Cmu 0.09; }   // 最初に探される
    Cmu             0.09;           // 無ければ RAS 自身から読む
}
```

OpenFOAM 14 は、**素のモデル名**を最初に試し、次に従来の `Coeffs` 名、最後に外側のブロックを見ます。

```
RAS
{
    model     kEpsilon;
    kEpsilon  { Cmu 0.09; }         // 14 で新設。最初に試される
    kEpsilonCoeffs { Cmu 0.09; }    // 引き続き有効
    Cmu       0.09;                 // 引き続き有効
}
```

**手元にあるケースが動かなくなることはありません。** ここでの OpenFOAM 14 は厳密な上位集合であり、素の綴りを追加しただけで従来の 2 つはどちらも削っていません。8〜13 向けに書かれたケースは 14 でもそのまま動きます。

**壊れるのは逆方向で、しかも無言です。** OpenFOAM 14 上で `kEpsilon { … }` を使って書いたケースを 13 以前で走らせると、フォールバックに落ちます。副辞書として認識されないためブロックごと読み飛ばされ、**その中の係数はすべて黙って既定値になります**。エラーも警告も出ず、`Cmu` は 0.09、他もモデル内蔵の既定値のまま走ります。14 からケースを**過去方向**へ移すときは、ブロック名を `<model>Coeffs` に戻してください。

これは Foundation 側だけの話で、OpenCFD の各リリースは影響を受けません。v14 では自身のモデルヘッダも新しい形を記載するよう書き換えられています（14 個。例えば `kEpsilon.H` は 13 の `kEpsilonCoeffs { … }` に代えて `kEpsilon { … }` を示します）。

これはチュートリアルではなくソースからの実測です。v14 の `src/OpenFOAM/db/dictionary/dictionary.C` にある `dictionary::optionalTypeDict`（920〜940 行）が `typeName`、次に `typeName + "Coeffs"`、最後に外側の辞書を返します。OpenFOAM 13 の `optionalSubDict`（同ファイル 926〜941 行）にはこの連鎖がありません。`optionalTypeDict` は Foundation 7〜13 にも、OpenCFD のどのリリースにも存在しません。

## OpenFOAM 14 はキーを 1 つ落としてもいる。そちらは順方向で刺さる

上記の副辞書の変更は 8〜13 → 14 の方向では安全です。しかし v14 の変更にはそうでないものがもう 1 つあり、同じように静かに失敗するため見出しを分けます。並列 `GAMG` から `processorAgglomerator` が無くなりました。

13 までは、`fvSolution` はプロセッサ集約の方法を単語で指定していました。

```
solvers
{
    p
    {
        solver                 GAMG;
        processorAgglomerator  masterCoarsest;
    }
}
```

14 は代わりに副辞書を読み、方法はその中で指定します。

```
solvers
{
    p
    {
        solver  GAMG;
        processorAgglomeration
        {
            agglomerator  pair;
        }
    }
}
```

**ここには互換ルックアップがありません。** 13 は `controlDict.found("processorAgglomerator")` を尋ね、14 は `controlDict.isDict("processorAgglomeration")` を尋ねます。該当する辞書が無ければ集約器のポインタは null のままです。つまり既存のケースは誤読されるのではなく、旧来のキーがまったく読まれません。これまでプロセッサをまたいで集約していた並列計算が、単にそれをやめます。エラーも警告もなく、現れる症状は所要時間だけです。

方法の名前も同時に変わったので、書き換えは純粋に機械的な作業ではありません。`manual` と `none` は残りますが、**`masterCoarsest`・`eager`・`procFaces` は無くなり**、`all`・`sequential`・`pair` が新しく加わっています。

Foundation 限定であり、両ツリーの `GAMGAgglomeration.C` と `GAMGProcAgglomerations/` 以下の `TypeName` 登録から実測しました。OpenCFD v2606 は Foundation 13 と同じく、今も `processorAgglomerator` を単語として読みます。

## FoDE 側の対応

- **ファイル一覧は両方の綴りを提示します。** 上記の辞書はすべて、旧称と新称の両方が FoDE のファイル一覧に載っており、実際にケースに存在するほうだけが表示されます。設定は不要です。
- **キーのバージョン表示は推測ではなく実測です。** Detail ペインの *Supported in* は両フォークの全リリースを読んだ結果なので、「OpenCFD v2106-v2606」はそのすべてに存在するという意味であり、たまたま調べた 2 つに存在するという意味ではありません。
- **リリースをまたぐ比較はメニュー項目です。** **Case > Find OpenFOAM Examples** がインストール済みの `tutorials/` を検索し、ヒットしたケースを比較の参照側として開く（**Case > Compare with Case**）ことも、新しい編集可能なケースとして複製することもできます。**移行先**のインストールを指定して検索するのが、同種の現代的なケースがどう書かれているかを知る最短経路です。

## 検証できるように: 測定方法

上の数値はすべて、そのリリースの `tutorials/` ツリーで当該名を持つファイルの数を、ケース直下（`<case>/constant/<name>`）とリージョン 1 階層下（`<case>/constant/<region>/<name>`）について数えたものです。`physicalProperties.air` のような相バリアントは別に数えず、完全一致のファイル名のみを対象としています。

両フォークの**全リリース**を数えています。Foundation 7〜14 と、OpenCFD の v2106〜v2606 の全 11 リリースで、抜けはありません。しかも各リリースはコミットで固定してあるので、この表は信用するものではなく再現できるものです。

<!-- BEGIN generated: commit-table -->
| フォーク | リリース | コミット |
|---|---|---|
| Foundation | 7〜14 | `6334942`、`a86b07b`、`d87800e`、`89f925d`、`9cbf94f`、`0b487fc`、`17489db`、`c046c72` |
| OpenCFD | v2106〜v2606 | `c15bfde`、`14aeaf8`、`76d719d`、`6690815`、`a6e826b`、`1d8f0d5`、`630d60d`、`d394908`、`615aae6`、`87ed40d`、`481094f` |
<!-- END generated: commit-table -->

13 と 14 は `OpenFOAM-dev` のタグ `version-13` / `version-14` で、それ以外は各リリースのリポジトリです。計数は各コミットに対する `git ls-tree -r` から得ており、作業ツリーを介さないので、あとからチェックアウトしても数値がずれることはありません。

**この数値は旧版の表を置き換えるものです。** 旧版は OpenCFD を 7 リリースだけ抽出しており、また 13 と 14 のタグ付け以前に取得した `dev` 列を使っていました。ほとんどのセルの差は 0〜2 です。OpenCFD 側の変化が大きいのは、これまで一度も数えていなかった 4 リリースが加わったためです。**結論は何も変わっていません** — Foundation の切り替わりは同じ 4 つで、OpenCFD 側は依然として改名ゼロです。

これは**チュートリアルが何を使っているか**の測定であり、リリースが何を読むかの代理指標であって証明ではありません。良い代理指標ではあります（改名は、同じリリースで一方の名前がゼロになり他方が現れる形で現れます）。ただし個別のキーについての権威はソースコードであり、個別のケースについての権威は実際に走らせてみることです。上で述べた副辞書の変更をこれらの表に**入れていない**のは意図的です。ファイル名ではなくファイルの中で起きた変更であり、ファイル名の計数では見えないため、ソースから読み取っています。
