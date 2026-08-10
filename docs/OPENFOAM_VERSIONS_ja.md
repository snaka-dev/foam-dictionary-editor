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

| ファイル | 7 | 8 | 9 | 10 | 11 | 12 | dev |
|---|---:|---:|---:|---:|---:|---:|---:|
| `constant/turbulenceProperties` | 166 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/momentumTransport` | 0 | 166 | 169 | 176 | 183 | 187 | 203 |
| `constant/transportProperties` | 110 | 111 | 112 | 0 | 0 | 0 | 0 |
| `constant/thermophysicalProperties` | 86 | 85 | 94 | 0 | 0 | 0 | 0 |
| `constant/physicalProperties` | 1 | 1 | 1 | 157 | 159 | 165 | 184 |
| `constant/fvOptions` | 23 | 22 | 0 | 0 | 0 | 0 | 0 |
| `system/fvOptions` | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| `constant/fvModels` | 0 | 0 | 42 | 46 | 66 | 72 | 91 |
| `system/fvConstraints` | 0 | 0 | 43 | 44 | 50 | 52 | 58 |
| `constant/thermophysicalTransport` | 0 | 2 | 6 | 6 | 6 | 6 | 10 |
| `constant/regionProperties` | 4 | 4 | 5 | 5 | 0 | 0 | 0 |
| `system/functions` | 0 | 0 | 0 | 0 | 0 | 115 | 137 |
| `constant/momentumTransfer` | 0 | 0 | 0 | 0 | 0 | 0 | 31 |

列を上から下に読むと、きれいな切り替わりが 4 つ見えます。

**OpenFOAM 8 — 乱流。** `constant/turbulenceProperties` が `constant/momentumTransport` になります。同じ 166 ファイルが 1 リリースで名前を変えただけです。中身の構造は保たれています（`simulationType`、`RAS`/`LES` ブロック、`model`、`turbulence`、`printCoeffs`）。分離された熱側のために `constant/thermophysicalTransport` が同時に現れます。

**OpenFOAM 9 — `fvOptions` が 2 つに分かれる。** 1 つだった `fvOptions` が `constant/fvModels`（生成・消滅項、つまり方程式に**加える**もの）と `system/fvConstraints`（値を**固定する**もの）になります。OpenFOAM 8 から持ち込んだ `fvOptions` はどちらとしても読まれません。しかも分割は意味的なものなので `mv` 一発の改名では済まず、エントリを 2 つの新ファイルに仕分ける必要があります。

**OpenFOAM 10 — transport と thermophysical が統合される。** `constant/transportProperties` と `constant/thermophysicalProperties` の両方が 1 つの `constant/physicalProperties` に置き換わります。ほぼすべてのケースが影響を受けるため、これが最も痛い変更です。2 つの名前で 196 ファイルあったものが、1 つの名前で 157 ファイルになりました。（それ以前の 1 件は実在しますが無関係です。`electrostaticFoam` は OpenFOAM 7 の時点で `physicalProperties` を持っています。）

**OpenFOAM 11 — `regionProperties` が消える。** マルチリージョンの設定方法が刷新され、このファイルはチュートリアルから姿を消します。

改名ではなく追加のものが 2 つあります。`system/functions` は **OpenFOAM 12** で登場し、従来 `controlDict` の中にあった function object のブロックの置き場所になりました。`constant/momentumTransfer` は **dev** で登場し、多相流の運動量交換を扱います。

相バリアントは基底名に追随します。OpenFOAM 10 より前に `thermophysicalProperties.air` と `thermophysicalProperties.water` があったケースは、10 以降では `physicalProperties.air` と `physicalProperties.water` になります。`momentumTransport.air` も同様です。

## OpenCFD 側: 何も動かない

同じ測定を OpenCFD のリリースに対して行った結果です。

| ファイル | v2106 | v2206 | v2212 | v2306 | v2412 | v2506 | v2606 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `constant/turbulenceProperties` | 318 | 348 | 363 | 364 | 429 | 430 | 432 |
| `constant/transportProperties` | 219 | 239 | 250 | 252 | 324 | 325 | 326 |
| `constant/thermophysicalProperties` | 148 | 162 | 163 | 163 | 163 | 163 | 165 |
| `constant/fvOptions` | 35 | 39 | 42 | 42 | 43 | 43 | 43 |
| `constant/momentumTransport` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `constant/physicalProperties` | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `system/fvConstraints` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

5 年間で、これらのファイル名は 1 つも変わっていません。数が増えているのはチュートリアル自体が増えているからです。したがって:

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

## FoDE 側の対応

- **ファイル一覧は両方の綴りを提示します。** 上記の辞書はすべて、旧称と新称の両方が FoDE のファイル一覧に載っており、実際にケースに存在するほうだけが表示されます。設定は不要です。
- **キーのバージョン表示は推測ではなく実測です。** Detail ペインの *Supported in* は両フォークの全リリースを読んだ結果なので、「OpenCFD v2106-v2606」はそのすべてに存在するという意味であり、たまたま調べた 2 つに存在するという意味ではありません。
- **リリースをまたぐ比較はメニュー項目です。** **Case > Find OpenFOAM Examples** がインストール済みの `tutorials/` を検索し、ヒットしたケースを比較の参照側として開く（**Case > Compare with Case**）ことも、新しい編集可能なケースとして複製することもできます。**移行先**のインストールを指定して検索するのが、同種の現代的なケースがどう書かれているかを知る最短経路です。

## 検証できるように: 測定方法

上の数値はすべて、そのリリースの `tutorials/` ツリーで当該名を持つファイルの数を、ケース直下とリージョン 1 階層下について `find` で数えたものです。使用したツリーは OpenFOAM-7〜12 と dev、および OpenCFD v2106、v2206、v2212、v2306、v2412、v2506、v2606 です。

これは**チュートリアルが何を使っているか**の測定であり、リリースが何を読むかの代理指標であって証明ではありません。良い代理指標ではあります（改名は、同じリリースで一方の名前がゼロになり他方が現れる形で現れます）。ただし個別のキーについての権威はソースコードであり、個別のケースについての権威は実際に走らせてみることです。
