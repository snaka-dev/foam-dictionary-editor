# スキーマ候補: 次にどの辞書を記述するか

[English version](SCHEMA_CANDIDATES.md)

FoDE の Detail ペインは、カーソル位置のキーが何を意味し、どんな値を取り、どのリリースに存在するかを、`schemas/` のスキーマモジュールから説明します。モジュールのない辞書ではペインは空になります。このページは、まだモジュールのない辞書を順位付けし、それぞれについて **FoDE で手書きすべきか**、**foamlore で生成すべきか**を示します。この選択は好みの問題ではなく、辞書の形から決まります。

書き方は DEVELOPER.md の「Schema system」を参照してください。着手前にテーブルキーの規約を読んでください。キーを `"<parent>.<key>"` ではなく `"<key>.<parent>"` と綴ったモジュールは、読み込まれ、素朴な単体テストも通り、どこからも到達されません。`fv_schemes.py` に実際に起きたことです。

## 現在のカバレッジ

モジュールがある辞書は 6 つです。`controlDict`、`fvSchemes`、`fvSolution`、`blockMeshDict`、`snappyHexMeshDict`、そして `turbulenceProperties` + `momentumTransport`（後の 2 つは foamlore のジェネレータ製）。FoDE のファイル一覧は 105 個の名前を提示するので、ユーザが開けるもののほとんどには背後にスキーマがありません。

## 順位付けの方法

候補ごとに 2 つの数値を、推定ではなく実測しています。

- **ケースがそれを持つ頻度** — `tutorials/` 内でその名前を持つファイル数を、Foundation 12 と OpenCFD v2606 で別々に数えたもの。一方のフォークでありふれた辞書が他方には存在しないことがあるためです。2 列の差が大きい理由は [OPENFOAM_VERSIONS_ja.md](OPENFOAM_VERSIONS_ja.md) を参照してください。
- **異なるキーの数** — チュートリアル中の全インスタンスに現れるキー名の概算です。こちらは労力側の指標で、誰かが調べて書く `KeySchema` エントリの数にあたります。

同点を分ける 3 つ目の要素は数値化していません。FoDE が別の理由ですでにそのファイルを理解しているかどうかです。`topoSetDict` と `setFieldsDict` は、3D ビューアが描画するために、ソース種別とジオメトリのキーワードがすでにコードとして列挙されています。

## Tier 1 — FoDE で手書きするもの

1 つのユーティリティが所有する有限のキー集合で、フォーク差がほとんどないもの。生成すべきものは何もありません。キーは紙の上で数え切れますし、エントリの価値はキーを説明する散文にあり、それはジェネレータが作るものではありません。

| 辞書 | OF12 | v2606 | キー数 | 備考 |
|---|---:|---:|---:|---|
| `system/decomposeParDict` | 106 | 362 | 25 | コア 4 つを除けば最も多い辞書。`method` は閉じた選択肢リスト（`scotch`、`hierarchical`、`simple`、`kahip`、`metis`、`none`）で、メソッドごとの係数ブロックも小さい |
| `system/setFieldsDict` | 64 | 134 | 30 | リージョンのソース種別は 3D ビューア用に `foam/set_fields_extractor.py` で列挙済み |
| `system/topoSetDict` | 34 | 137 | 53 | 同じく `foam/topo_set_extractor.py`。`source` の値一覧と各ソースのジオメトリキーはすでにコードとして書かれている |
| `constant/g` | 137 | 232 | 9 | 半日仕事で、ほぼ全ケースに存在する |
| `system/fvConstraints` | 52 | 0 | 25 | Foundation 専用。Tier 2 の `fvModels` と対だが、拘束側は短い閉じたリスト |
| `system/meshQualityDict` | 16 | 41 | 20 | **ほぼ無料**: `schemas/snappy_hex_mesh_dict/_mesh_quality.py` が `meshQualityControls` ブロック向けにまさにこれらのキーを記述済み。単独ファイルにも応答するよう `TARGET_FILES` タプルを足すだけ |
| `system/createPatchDict` | 6 | 48 | 14 | |
| `system/surfaceFeatureExtractDict` / `surfaceFeaturesDict` | 13 | 49 | 17 / 13 | 1 モジュールに `TARGET_FILES` で 2 つの名前 — OPENFOAM_VERSIONS_ja.md のフォーク対応表を参照 |
| `system/createBafflesDict` | 18 | 13 | 16 | |
| `system/extrudeMeshDict` | 14 | 17 | 36 | 出現頻度のわりにキーが多い。安いものを片付けてから |
| `system/refineMeshDict` | 3 | 10 | 20 | 埋め草 |
| `constant/regionProperties` | 0 | 19 | 8 | OpenCFD では現行。Foundation は v10 以降で同梱をやめた |
| `system/meshDict` | 0 | 22 | 8 | cfMesh、OpenCFD のみ |
| `system/faSchemes` / `faSolution` / `faMeshDefinition` | 0 | 17 | 14 / 36 / 9 | finite area、OpenCFD のみ。`faSchemes`/`faSolution` は `fv` 版と近いので既存モジュールが出発点になる（ただし丸写しのテンプレートではない） |
| サンプリング系（`sample`、`probes`、`surfaces`、`singleGraph`、`sampling`、`cuttingPlane`） | 少 | 少 | — | 件数は少ないが、FoDE が 3D ビューアでジオメトリを描画するため、ユーザは Detail ペインを開いた状態でこれらを見ている |

推奨順序: `meshQualityDict`（タプル 1 つ）→ `decomposeParDict` と `g`（高頻度・小規模）→ `topoSetDict` と `setFieldsDict`（エクストラクタが下調べ済み）→ 残りは余力に応じて。

## Tier 2 — foamlore で生成するもの

有効な値が実行時解決される C++ クラス階層にあり、その集合がフォークごとに異なりリリースごとに増え、有用な内容が係数名・既定値・OpenFOAM が併記している散文であるもの。これはまさに foamlore のジェネレータが作られた形です。19 リリースにわたる 29 の乱流モデルについて 12,501 行を生成しました。手書きする人はいません。

| 辞書 | OF12 | v2606 | 生成すべき理由 |
|---|---:|---:|---|
| `constant/physicalProperties` / `transportProperties` + `thermophysicalProperties` | 165 | 491 | ぶっちぎりの筆頭。`thermoType` は 7 スロットの実行時選択の組み合わせ（`type`/`mixture`/`transport`/`thermo`/`equationOfState`/`specie`/`energy`）で、ユーザが実際に間違えるのはその有効な組み合わせであり、それは `src/thermophysicalModels` からしか分からない |
| `constant/dynamicMeshDict` | 40 | 118 | 移動ソルバとトポロジ変更が RTS。しかも Foundation が v10 以降で仕組みを再編したため、手書きモジュールは 1 リリースで陳腐化する |
| `constant/fvOptions` / `fvModels` | 72 | 43 | 一方のフォークの `fvOptions` が他方の `fvModels` + `fvConstraints`（[OPENFOAM_VERSIONS_ja.md](OPENFOAM_VERSIONS_ja.md)）で、ソース種別ごとに独自のクラスと独自のキーを持つ |
| `constant/radiationProperties` | 8 | 72 | 輻射モデルと散乱・吸収のサブモデルがすべて RTS |
| `constant/combustionProperties`、`chemistryProperties` | 16、10 | 45、42 | 形は同じだが価値は下。ジェネレータがすでにそのツリーを走査している場合にのみ |

**コストのゲート。ただし見た目より低い。** foamlore の `facts/tools/fetch_sources.sh` は各チェックアウトについて、乱流サブツリー(`src/TurbulenceModels` / `src/MomentumTransportModels`)に加え `src/OpenFOAM/db/dictionary`・`src/OpenFOAM/db/Time`・`src/OpenFOAM/matrices`・`src/finiteVolume`・`src/mesh/blockMesh`・`src/mesh/snappyHexMesh` をスパースチェックアウトします。上記のどのファミリも、全チェックアウトに新しいサブツリーを取得し、そのためのレジストリを書くところから始まります。

取得そのものは安価で、天秤にかけるべき対象ではありません。チェックアウトは部分クローン(`blob:none`)なので、サブツリーの追加はその blob しか引きません。熱物性の 2 サブツリーを 1 チェックアウトに追加して 1.5 秒・7 MB、Foundation の 2 チェックアウトを `src` + `applications` + `etc` の全体へ広げて数分・約 210 MB でした。**高くつくのは 2 つめの抽出器の方です。** 熱物性ファミリなら一度書く価値がありますが、9 キーのファイルのために書く価値はありません。この制約を回避するために `schemas/` の生成モジュールを**手編集しないでください**。GENERATED バナーが入っており、テストがそれを検査しています。ジェネレータへの依頼は foamlore 側の仕様書に書きます。

## 意図的にスキーマを作らないもの

- **`system/changeDictionaryDict`**（v2606 で 55 ケース） — キーがユーザ自身のフィールド名・パッチ名なので、一般的に言えることがありません。
- **`system/functions`** と function object の設定ファイル — キー集合は OpenFOAM が同梱する全 function object の和集合であり、開いた集合です。個々の説明は `etc/caseDicts/postProcessing/` にあります。もし対応するなら、手書きテーブルではなくそれらのファイルのリーダという形になります。
- **辞書に見えるだけのファイル** — `constant/foam.inp` と `foam.dat` は Chemkin のデータであり、FoDE は意図的に一覧に載せていません。

## 着手前に

`tests/schemas/test_schema_coverage.py` を実行してください。実際のチュートリアルのフィクスチャを解析し、Detail ペインと同じ歩き方で走査して、辞書ごとのカバレッジ下限を強制します。存在してインポートもされているのにどこからも到達されないモジュールを捕まえるのがこのテストです。新しい辞書の下限も同じ変更の中で追加してください。下限は現在のカバレッジのすぐ下に置き、上げる方向にのみ動かします。
