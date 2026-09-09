# foamlore ジェネレータへの依頼アーカイブ

姉妹リポジトリ foamlore に対して FoDE が依頼した変更と、foamlore がそれに対して測定した結果の、確定した記録です。foamlore は [DEVELOPER_ja.md](../DEVELOPER_ja.md) の「生成モジュール(foamlore からのベンダリング)」で説明しているスキーマモジュールを生成し、FoDE に取り込んでいます。**本書の変更は FoDE 側では一切実施していません**。foamlore は独自のリモートを持つ別リポジトリであり、生成ファイルを FoDE 側で手編集してはいけないためです。

**新しい依頼は本書には書きません。** foamlore の `HANDOFF.md` に書いてください。あちらは未解決の項目だけを載せ、解決したら消していきます。解決した項目の記述はその後こちらへ移ります。2 つは寿命が正反対だからです — 未解決の依頼は短く揺れ動き、確定した記録は長く不変です。そして本書は `RELEASE_NOTES.md` と `DEVELOPER.md` から参照されているため、項目番号を動かせません。分けておくことは、固まりきっていない依頼が「記録として引用されるファイル」に入り込むのを防ぐことでもあります。

## 対応状況(2026-09-05)

foamlore 側が、同リポジトリの `fode-schemas/SPEC_RESPONSE_ja.md`
(および `_ja` でない対) で項目ごとに回答しています。あちらは本書の各項目のもう半分です — 本書が依頼を、あちらが測定結果を担うので、2 つは併せて読むことを想定しています。

| 項目 | 状況 |
|---|---|
| 1. 3 モデルの上限を解消 | **完了** — 3 モデル → 29(RAS 16、LES/DES 13) |
| 2. `TARGET_FILES` と重複モジュール廃止 | **完了。ただし統合ではない**(下記) |
| 3. 来歴フィールドの出力 | **測定の結果、出力すべきものなし**(下記) |
| 4. バージョンタグを広げる | **完了** — ラベル付け替えではなく全リリース走査による |
| 5. 構造キーには手を出さない | 同意。機械的に検査されるようになった |
| 6. v2112 のチェックアウトを追加 | **対応済み**(2026-08-07 提起、2026-08-12 完了) — 下記 |
| 7. 熱物性ファミリ:妥当性を決めるのはどのテーブルか | **回答済み**(2026-08-13 に foamlore が提起、2026-08-14 に回答) — (a)、フィールド 2 つ、モジュール 3 つ — 下記 |
| 8. OpenFOAM 14 | **対応済み**(2026-08-13 提起・同日完了) — 定数 4 つ、テスト 1 箇所、判断 1 件 — 下記 |
| 9. `FOUNDATION_SERIES` が v7-v13 のまま | **対応済み**(2026-08-13 提起、2026-08-14 完了) — 残り 21 件を実測。うち 11 件は元々 Foundation のキーではなかった — 下記 |
| 10. 改名走査が FoDE の辞書の大半を見ていない | **対応済み**(2026-08-13 提起、2026-08-14 に foamlore の `86a5bb4` と `2b314b8` で完了) — 依頼 3 件すべて着地 — 下記 |
| 11. `BOTH` タグは、狭いタグのようには検証されてこなかった | **2026-09-08 実測・取り込み完了** — 7 辞書・19 リリース・公表可能な範囲 340 件。5 辞書が完全に一致し、誤ったタグ 9 件を撤回。うち 2 件は実行の拒否または中断を引き起こすものだった。乱流 2 ファイルのファイル別タグは更新候補へ繰り延べ(下記) |
| 12. 層流応力モデルが未実測、`phaseSystemModels` が未取得 | **対応済み**(2026-09-03 提起、2026-09-04 に foamlore が完了。提案されていた追加対応は 2026-09-05 に実施) — 依頼 2 件とも回答済みで、7 つの層流説明文は `_laminar_models.MODEL_DOCS` 由来になりました — 下記 |
| 13. 入れ子の generalizedNewtonian/generalisedNewtonian 粘性モデル | **foamlore 側では実測済み**(先方の SPEC_RESPONSE.md 項目 12、2026-08-15) — 配線方式は FoDE が 2026-09-04 に決定、残るは再生成のみ — 下記 |

項目 2 を仕様どおりに実施しなかった理由は、先方ではなく**こちら側**にある。
`schemas/registry.py::_build_file_key_schemas` は `TARGET_FILES` の各要素に
対して `table.update(schemas)` を行うだけで、キー単位のフィルタがない。
つまり両方のファイル名を挙げた 1 つのモジュールは、各ファイルへ**同一の**
テーブルを与える。すると OpenCFD 専用の `decayControl` や `GEKOCoeffs` 全体が
`constant/momentumTransport` の中で解決してしまう。このファイルは OpenCFD の
どのリリースも読まず、Foundation も v8 以降しか読まない。現状はそこで正しく
`None` を返している。

foamlore は統合ではなく本体の分離で重複を解消した。生成された
`schemas/_turbulence_coeffs.py` が係数のファクトを 1 度だけ保持して
`build_schemas(target_file)` を提供し、ファイルごとのモジュールは
それぞれ約 25 行になっている。共有しているのはファクトだけである。
バージョンタグ・注記・既定値一覧はすべて対象ファイルに依存し、それこそが
1 つのマージ済みテーブルが両方のファイルにとって正しくなり得ない理由である。
`schemas/builtin.py` は変更していない — 共有モジュールは import されるだけで
登録されず、`TARGET_FILE` も宣言しない。

**文字どおりの単一モジュール形式を望むなら、前提条件はこちら側にある。**
`_build_file_key_schemas` にキー単位の対象フィルタを入れることである。
その是非は別途検討する価値があるが、現時点で必要としているものはない。

上限の解消は、把握しておくべき変更も 1 つ強いた。134 個の異なる係数名のうち
28 個が複数のモデルに読まれる(`Cmu` は 9 モデル。ほかに `C1`・`C2`・`C3`・
`sigmak`・`sigmaEps`・`kappa`・`Ck`・`betaStar`)。ジェネレータの従来の規則は
所有モデルがちょうど 1 つの名前にしか素のキーを出力しなかったので、
モデルを増やすと**最も一般的な係数について素の表記が黙って消える**ところ
だった。`OPEN_NAMESPACES` が支えている表記である。これらの名前には、
所有する全モデルを列挙し各既定値を提示する統合エントリを 1 つ出力する。
`<model>Coeffs` 辞書の中ではそのモデル自身のエントリが優先される。

項目 3 はジェネレータの担当範囲では空だと判明しました。両方の宣言形式を
18 リリース全体から引用検証付きで走査した結果、乱流モデルサブツリーには
改名宣言が 7 件あり、そのどれも `<Model>Coeffs` の係数ではありませんでした。
6 件は本書の項目 5 が `turbulence_structure.py` の担当と定めた
`RASModel`/`LESModel`/`laminarModel` → `model` のセレクタで、7 件目は
`relaxation` → `qrRelaxation`、`thermalBaffle1D` の境界条件キーです。
したがってジェネレータは来歴フィールドを出力せず、さらにセレクタを
**出力しないことが要件**になります。`schemas/builtin.py` は
`turbulence_structure` の後に読み込むため、出力すると衝突ではなく
FoDE 側のエントリを上書きしてしまうからです。

項目 3 に記した「古いツリーにしか残っていない対がある」という懸念は
裏付けられました。`relaxation` → `qrRelaxation` は v2106 と v2112 で宣言され、
v2206 以降には存在しません。

項目 4 では、手作業監査がサンプルから飛ばしていたリリースに由来する誤りが
2 点訂正されました。SpalartAllmaras の `ft2` 項の登場は v2306 ではなく
**v2212** であり、`sigmaNut` の既定値も v2212 で `scalar(2)/scalar(3)` から
`0.66666` に変わっていました。FoDE 側の対応は、`schemas/_base.py` への
`FOUNDATION_V8_V13`・`OPENCFD_V2212_V2606` の追加と、旧来の狭いタグを
固定していた `tests/schemas/test_turbulence_schemas.py` の 3 つの
アサーションの更新です。

## すでに正しい点

生成された内容は正確です。全係数を `.C` コンストラクタと照合し直しました。`kOmegaSST` の `a1`=0.31、`alphaK1`=0.85、`beta1`=0.075、`betaStar`=0.09 をはじめ、kEpsilon と SpalartAllmaras まで確認しましたが、名前・値ともに誤りは 1 件もありませんでした。`momentum_transport.py` は Foundation のコンストラクタに存在しない OpenCFD 限定係数（`decayControl`、`kInf`、`omegaInf`、`ReyFactor`、`ReyStar`、`twoLayerTreatment`、`ck`、`ft2`、`Ct3`、`Ct4`）を正しく**除外**しています。単純なコピーであればこれらが残っていたはずです。パイプラインは機械的なソース抽出であり、バナーに記されたコミットハッシュも実在します。

以下の指摘はすべて正確さではなく**カバー範囲**に関するものです。

## 1. 3 モデルの上限を解消する

`facts/tools/` にはモデルごとに手書きの抽出スクリプトがあります（`extract_kEpsilon.py`、`extract_kOmegaSST.py`、`extract_SpalartAllmaras.py`）。カバーが 3 モデルで止まっているのはこの設計が理由です。モデルを 1 つ増やすたびにスクリプトが 1 本必要になります。

OpenCFD v2606 は RAS モデル 14 種と LES モデル 7 種を同梱し、Foundation はさらに RAS 側に `kOmega2006` と `v2f`、LES 側に `SpalartAllmaras*DES` 系を加えます。つまり RAS は約 16 種中 3 種、LES は**ゼロ**という状態です。

依頼: `facts/tools/foam_extract.py` をテーブル駆動の抽出器に一般化し、スクリプトを書くのではなくソースパスを列挙するだけでモデルを追加できるようにしてください。認識すべき宣言はモデル間で共通です。

- `dimensioned<scalar>::getOrAddToDict("name", coeffDict(), default)`
- `Switch::getOrAddToDict("name", coeffDict(), default)`
- 直接コンストラクタ形式 `Cmu_("Cmu", coeffDict(), 0.09)`

パスがフォークで異なる点に注意してください。OpenCFD は `src/TurbulenceModels/turbulenceModels/{RAS,LES}/`、Foundation は `src/MomentumTransportModels/momentumTransportModels/{RAS,LES}/` です。

読み取りではなく**計算**で決まる係数は除外し続ける必要があります。現在の抽出器は `SpalartAllmaras` の `Cw1`（`Cw1_(Cb1_/sqr(kappa_)+(1+Cb2_)/sigmaNut_)`）を正しく除外できており、この挙動は書き直し後も維持してください。

## 2. `TARGET_FILES` を出力し、重複モジュールを解消する

`momentum_transport.py` の 57 キーは `turbulence_properties.py` の 77 キーの真部分集合であり、約 900 行が重複しています。この重複が存在した唯一の理由は、FoDE のレジストリが単一の `TARGET_FILE` でスキーマを保持していたことと、Foundation が OpenFOAM 8 で `constant/turbulenceProperties` を `constant/momentumTransport` に改名したことでした。

FoDE は `TARGET_FILES` タプルを受け付け、ファイルごとに複数モジュールのテーブルをマージするようになりました。したがってジェネレータは**単一**のモジュールを出力できます。

```python
TARGET_FILES = ("turbulenceProperties", "momentumTransport")
```

現在 2 ファイルを分けている情報は、各キーの `supported_in` にフォーク情報として持たせてください。移行までは現行の 2 モジュールがそのまま動作します。

## 3. 新しい来歴フィールドを出力する

`KeySchema` と `ChoiceItem` に省略可能なフィールドが 4 つ追加されました（DEVELOPER.md「キーが何であるかの記録」を参照）。

```python
status: KeyStatus = "valid"      # "valid" | "renamed" | "ineffective"
use_instead: str = ""            # 後継キー、または実際に読まれるキー
renamed_from: tuple[str, ...] = ()
deprecated_since: str = ""
```

すべて既定値付きなので現在の出力はそのまま有効です。これらがジェネレータに関係するのは、両フォークがリネームを機械可読な形で宣言しており、抽出器がすでにそのソースを走査しているためです。

- OpenCFD: `getCompat("newName", {{"oldName", apiVersion}})`
- Foundation: `lookupBackwardsCompatible<T>({"newName", "oldName"})`

この 2 系統をチェックアウト全体から走査すると、フォーク別バージョン範囲付きで約 100 組の旧称→新称が得られます。その中には API 2006 での `RASModel`/`LESModel` → `model` も含まれ、これはまさにこのジェネレータの守備範囲です。これらを `status="renamed"` のエントリとして出力すれば、詳細ペインが旧称を「不明なキー」として放置せず説明できるようになります。

補足: 互換エントリが後に削除されたため、古いツリーにしか残っていない組があります。`minMedianAxisAngle` は OpenCFD では v2206 まで宣言され v2212 以降には存在しませんが、Foundation では現在も受け付けられます。最新チェックアウトだけを読むジェネレータはこれらを取りこぼすため、走査は全チェックアウトを対象とし、範囲を記録してください。

## 4. バージョンタグを広げる、あるいは「検証記録」であると明示する

これは現時点でユーザーの目に見える問題である。Foundation v10 を使っているユーザーが `constant/momentumTransport` の `beta1` を選ぶと、詳細ペインには **「Foundation v13」** と表示され、「あなたの環境では使えない」と読めてしまう。同じ指摘が `snappyHexMeshDict` の `snap` に対して報告され、FoDE 側では手元にあるすべてのリリースで全キーを実測することで修正した。

生成されたタグは**何を確認したか**については正確である（`sources/` にある 4 つのチェックアウト）。しかし詳細ペインはそれをサポート範囲として提示する。Foundation 7/8/9/10/11/12/dev と OpenCFD v2106/v2206/v2306/v2412/v2506/v2512/v2606 に対する実測結果は次のとおり。

| エントリ | 現在のタグ | 実際に存在するのは |
|---|---|---|
| `momentum_transport.py` の全 111 件 | `Foundation v13` | **Foundation v8 〜 dev**（v7 に `MomentumTransportModels` は無く、OpenFOAM 8 での改名と整合する） |
| `beta1`、`Cmu`、`sigmaEps`、`decayControl` ほか（111 件） | `OpenCFD v2512, v2606` | **OpenCFD v2106 〜 v2606** |
| `ft2` | `OpenCFD v2512, v2606` | **v2306 〜 v2606** |
| `ReyFactor`、`ReyStar`、`twoLayerTreatment` | `OpenCFD v2512, v2606` | v2512 〜 v2606 — 現状のままで正しい |

すでに正確であり、広げてはいけないタグが 1 つある。`turbulence_properties.py` は Foundation のサポートを **v7 のみ**としているが、これは正しい。Foundation は OpenFOAM 8 でこのファイルを `momentumTransport` に改名したため、`constant/turbulenceProperties` を読む最後の Foundation リリースが実際に v7 だからである。

修正方法は 2 つあり、どちらでもよい。

1. **チェックアウトを増やす。** `fetch_sources.sh` は 4 つを取得しているが、Foundation 7〜13 と OpenCFD v2106〜v2606 を一式取得すれば、ジェネレータが実際の範囲を出力できる。FoDE 側は snappy の監査でこれを手作業で行い、上の表を得た。
2. **チェックアウト一覧ではなく範囲ラベルを出力する。** FoDE の `schemas/_base.py` はまさにこのために `FOUNDATION_SERIES`（`"Foundation v7-v13"`）と `OPENCFD_SERIES`（`"OpenCFD v2106-v2606"`）をエクスポートしている。特定リリースに紐付かないエントリは、たまたま手元にあったリリース名を並べるのではなく、その旨を示すべきである。安価だが (1) ほど精密ではない。

いずれを選ぶにせよ、重要なのは「このキーはリリース X で追加された」と「リリース X はたまたま我々が調べた場所である」の区別である。`supported_in` に入れてよいのは前者だけで、後者はすでにソースコミットを記録しているバナーの役割である。

## 5. 構造キーには手を出さない

`simulationType`、`RAS`/`LES`/`laminar`、`model` セレクタ、`turbulence`、`printCoeffs`、`delta` と delta 係数辞書は、手書きの `schemas/turbulence_structure.py` がカバーするようになりました。これらはモデルのコンストラクタから導出できるものではないため、ジェネレータの対象外としてください。レジストリが両モジュールを 1 つのテーブルにマージするので、両者の間に隙間は生じません。

## 6. v2112 のチェックアウトを追加する(2026-08-07)

チェックアウト一式から OpenCFD のリリースが 1 つ欠けています。`sources/` にあるのは v2106、v2206、v2212、v2306、v2312、v2406、v2412、v2506、v2512、v2606 の 10 個で、v2106〜v2606 の範囲にある 11 リリースのうち 10 個です。OpenCFD は年 2 回、`yymm` の `mm` が 06 か 12 でリリースするため、**v2112** が v2106 と v2206 の間に入るべきところ、欠けています。

これは表記上の些細な問題ではありません。項目 4 は全リリースを走査することで対応されており、`collapse()` は「そのキーが見つかったチェックアウトの集合」から範囲定数と明示リストのどちらを使うかを決めます。したがって v2106 と v2206 に存在するが v2112 を測定していないキーは、明示ペアの `"OpenCFD v2106, OpenCFD v2206"` として描画されます。利用者はこれを「v2112 では飛んでいる」と読みますが、その根拠はどこにもありません。`_turbulence_coeffs.py` はすでにこのペアを出力しています。

依頼: `fetch_sources.sh` とジェネレータの `CHECKOUTS` テーブルに `opencfd-v2112` を追加し、再導出してください。ストアはチェックアウト 1 つ分だけ増え、範囲は OpenCFD 11 リリース + Foundation 7〜13 の合計 18 になります。

FoDE 側は同じ変更で対応済みです。`schemas/_base.py` が `OPENCFD_V2112` をエクスポートし、この隙間をまたいで列挙していた唯一の手書きタグ(`schemas/snappy_hex_mesh_dict/_add_layers.py` の `addLayersControls.minMedianAxisAngle`)がこれを含むようになりました。ただしこのエントリは測定ではなく推論です。v2112 はこの範囲で唯一ローカルにソースツリーがないリリースであり、当該の互換エントリは前後のリリースには存在します。チェックアウトを備えたジェネレータであれば、この推論を実測に置き換えられます。

## 7. 熱物性ファミリ:妥当性を決めるのはどのテーブルか(2026-08-13)

この項目だけは向きが逆です。項目 1〜6 は foamlore への依頼ですが、これは probe(調査用の取得)を経て foamlore **から**提起されたものであり、冒頭の問いに答えるべきなのは **FoDE 側**です。しかもジェネレータの出力形を決める前に答える必要があります。[SCHEMA_CANDIDATES_ja.md](SCHEMA_CANDIDATES_ja.md) は `constant/physicalProperties` / `transportProperties` + `thermophysicalProperties` を「生成すべき辞書」の筆頭に挙げています(Foundation 12 のチュートリアルで 165 ファイル、OpenCFD v2606 で 491 ファイル)。foamlore は規模を測るため、`src/thermophysicalModels` と `src/transportModels` を 1 つのチェックアウト(`opencfd-v2606`、コミット `481094f`)に sparse-fetch しました。以下はすべてそのツリーからの実測です。

**問い:1 つの組み合わせは 3 つのテーブルへ同時に登録され、妥当性はソルバがどれを引くかで決まる。** `src/thermophysicalModels/basic/fluidThermo/makeThermo.H` の `makeThermoPhysicsThermos` は、各組み合わせを `basicThermo`、`fluidThermo`、**および**個別の基底 thermo の 3 つに対する `addThermoPhysicsThermo` へ展開します。v2606 では、132 回の `makeThermos` 呼び出しのうち個別基底が `psiThermo` のものが 26、`rhoThermo` のものが 106 です。したがって `rhoThermo` にしか登録されていない組み合わせは、`psiThermo` を構築するソルバでは実行時エラーになります — 綴り自体は他のチュートリアルに現れる実在のものであってもです。Detail ペインに見えているのは辞書だけです。

取り得る形は 3 つあり、ジェネレータはどれでも出力できます。いま決める必要があるのは、これがストアのキーを「組み合わせ」にするか「(組み合わせ, テーブル)」の対にするかを決めてしまうからです。これは後から変更できる描画上の詳細ではなく、再導出を伴います。

- **(a) テーブルも出力し、絞り込みは FoDE 側で行う。** 各組み合わせに、登録先の RTS テーブルを持たせます。表示の判断は FoDE が行い、必要になれば後から `controlDict` の `application` で絞り込めます。foamlore はこれを推奨します。ソースが実際に述べていることをそのまま記録する唯一の形であり、絞り込みの判断をソルバの文脈があるこちら側に残せるためです。
- **(b) 和集合を無条件に出力する。** 最も単純ですが、まずい方向に誤ります。ソルバが拒否する組み合わせを「妥当」と利用者に伝えてしまいます。
- **(c) テーブルごとに選択肢リストを出す。** 誠実ではありますが、ソルバ→テーブルの対応表をまるごとスキーマ側へ押し込むことになります。その対応は熱物性ツリーの中にはありません。

**2 つめの問い:`KeySchema` に `default` フィールドがない。** 乱流モデルでは問題になりませんでした。すべての係数に既定値があり、ジェネレータはそれを `description` に書き込んでいるからです。粘性モデルはそうではありません。`CrossPowerLaw.C:71-78` は `nu0`、`nuInf`、`m`、`n` をフォールバックなしの必須エントリとして読みます。つまり生成されるエントリは「必須、既定値なし」を散文で述べることになります。それで良いでしょうか。それとも `_base.py` に `required: bool`(あるいは `default: str`)を追加し、Detail ペインで区別して描画したいでしょうか。foamlore としては散文で構いません。フィールドの追加はこちら側では安価で、しかもこのファミリに限らずすべての辞書で効きます。

**3 つめの問い:項目 2 の結論に倣い、`TARGET_FILE` モジュールを 3 つにするか。** このファイルはフォークで改名されています。Foundation は v10 で `transportProperties` と `thermophysicalProperties` を `physicalProperties` に統合し、OpenCFD は 2 つのままです([OPENFOAM_VERSIONS_ja.md](OPENFOAM_VERSIONS_ja.md))。項目 2 を決着させたのと同じ理屈で、ここも「1 つのモジュール + `TARGET_FILES`」ではなく「共有の生成本体 + ファイルごとの薄いモジュール 3 つ」が適切です。さもなければ Foundation 専用のキーが、OpenCFD では別の意味で読まれるファイルの中で解決してしまいます。ジェネレータを書く前に確認しておく費用はゼロですが、書いた後に気づけば再導出になります。

### probe で決着した点(再度の議論は不要)

**費用の壁は SCHEMA_CANDIDATES.md が想定するより遥かに低い。** 同ページは「全チェックアウトに新しいサブツリーを取得すること」を検討材料として重く見ています。実際には、既存の blobless チェックアウトに両サブツリーを追加するのに 1.5 秒、サイズは 11 MB から 18 MB になりました。18 個すべてでもおよそ 130 MB と数分です。高くつくのは取得ではなく、2 つめの抽出器のほうです。

**スロットは 7 つまたは 4 つであり、7 つだけではない。** `basicThermo.C:52-68` は `componentHeader7`(`type`/`mixture`/`transport`/`thermo`/`equationOfState`/`specie`/`energy`)と `componentHeader4`(`type`/`mixture`/`properties`/`energy`)を定義し、`basicThermo.C:126` で辞書に `properties` があるかどうかにより選択します。液体物性の経路は短いほうを使います。スキーマは両方の形を記述する必要があり、Detail ペインは利用者がどちらにいるかを知る必要があります。

**妥当性は、列挙可能なテーブルへの完全一致での所属判定である。** `makeThermoName`(`basicThermo.C:135-156`)はスロットを `type<mixture<transport<thermo<eqnOfState<specie>>,energy>>>` の形に連結し、その文字列を引きます。このファミリを手書きではなく生成すべき最大の根拠がこれです。答えは機械的に決まり、しかも利用者が暗算できるものではありません。

**列挙は現実的で、typedef の間接参照も完全に解決する。** 1 チェックアウトに、8 種類の綴りで計 277 個のマクロ呼び出しがあります。

| マクロ | 個数 | 引数の形 |
|---|---:|---|
| `makeThermos` | 132 | 7 スロットの組をそのまま |
| `makeReactionThermos` | 52 | 9 引数 |
| `makeThermoPhysicsReactionThermos` | 50 | thermo-physics の typedef |
| `makeThermoPhysicsReactionThermo` | 20 | thermo-physics の typedef |
| `makeSolidThermo` ほか | 23 | 8 引数 |

132 個の `makeThermos` 呼び出しからは 132 通りの組み合わせが直接得られます。反応系 thermo の 70 個は代わりに `constGasHThermoPhysics` のような束を渡しますが、出現する 20 個の相異なるトークンはすべて `thermoPhysicsTypes.H` の 24 個の typedef で解決し、**未解決はゼロ**でした。これらの typedef は入れ子のテンプレートであり、foamlore の既存の `<>` を考慮する引数分割器がすでに扱えます。

### 分割の提案

1 つではなく 2 つの作業項目とします。輸送側 — `src/transportModels/incompressible/viscosityModels`、`optionalSubDict(typeName + "Coeffs")` 経由で読む 9 モデル — は foamlore のモデルレジストリへの通常の追加に近く、上記 3 つの問いのうち `default` の件以外には依存しません。`thermoType` 側は文字どおり新しい抽出器(マクロ展開 + typedef 解決)であり、その出力形は 1 つめの問いの答えに依存します。foamlore は輸送側から着手する意向で、熱物性側は本書の回答を待ちます。

このファミリが着地する際には、同じ変更の中で `tests/schemas/test_schema_coverage.py` に辞書ごとの下限を追加する必要があります。

### FoDE 側の回答(2026-08-14)

問われた順に 3 件すべてに答えます。ジェネレータの着手を妨げるものはもうありません。

**Q1 — 出力形は (a)、テーブルを出力する。** foamlore 自身の推奨どおりであり、その理由は述べておく価値があります。(a) は**方針変更に耐える唯一のストアキー**だからです。キーは `(組み合わせ, テーブル)` の対になるので、FoDE が後から `controlDict` の `application` → ソルバ → 基底 thermo という絞り込みを作る場合でも、(a) なら再導出は不要です。(b) と (c) はどちらも再導出を要します。(b) は本リポジトリが一貫して避けてきた向きに誤ります — ソルバが拒否するものを妥当だと言ってしまう。ここでのタグ付けの規律(`FOUNDATION_SERIES` の検証記録という扱い、`processorAgglomerator`、`turbOnFinalIterOnly` のフォーク非対称な扱い)はすべて「控えめに言う方が安いほうの誤り」という原則に立っています。(c) はソルバ→テーブルの対応をスキーマに持ち込みますが、その対応は熱物性ツリーの中にありません。これは本書が項目 2 の統合テーブルに対して述べたのと同じ反論です。ソースが持たない事実をジェネレータが発明すべきではありません。

形を推測させないために、制約を 2 つ。

- **テーブル集合は `supported_in` ではなく `note` として出力してください。** あのフィールドは「どのリリースか」を意味し、`_supported_in_text`・`_qualified_supported_in`・`tests/schemas/test_schema_coverage.py` の `test_long_standing_keys_are_not_tagged_to_one_release` はいずれも要素を `Foundation`／`OpenCFD` の接頭辞で解釈します。テーブル名を入れるとリリース名として読まれ、そのように描画されます。
- **7 スロットか 4 スロットかの切り分けはこちら側の問題です。** `componentHeader7` と `componentHeader4` は同一モジュール内の 2 つのキー集合になり、辞書に `properties` エントリがあるかどうかで区別します。これは `schemas/registry.py` の親キーの問題なので、出力形には何の制約も課しません。

**Q2 — `KeySchema` に `default: str` と `required: bool` の両方を追加する。** 本変更で実施済みです。どちらもデフォルト値を持つため現在の出力はそのまま有効です — 項目 3 が来歴フィールドに用いたのと同じ論法です。両者は排他で、`tests/schemas/test_default_and_required.py` がそれを強制します。Detail パネルでは**「省略した場合」**という 1 行を共有します。1 つの問いへの 2 つの答えだからです。`ChoiceItem` には付けません。既定値はキーに属し、その値の 1 つに属するものではありません。

`default` については prose でも許容できましたが、`required` は違います。こちらは機械可読なので、将来の「ケースに OpenFOAM が必要とするキーが欠けている」検査の裏付けになり得ます。`description` の一文では決して支えられません。そして `CrossPowerLaw.C:71-78` が必要としているのはまさにこれです。

**事実が二重の綴りにならないよう、依頼が 2 件。** 次回の再導出で `default=` を出力し、**同じ変更で `description` から既定値を落としてください**。それまで生成モジュールは prose の既定値とフィールドの空値を保つので、ここでは `default=""` を「未記録」の意と定義し、「既定値が存在しない」とは決して読みません。そうしないと生成された係数がすべて必須扱いになります。除外事項として、複数モデルが読む係数名 28 件(`Cmu` は 9 モデル、ほかに `C1`・`C2`・`C3`・`sigmak`・`sigmaEps`・`kappa`・`Ck`・`betaStar`)は各所有モデルの値を提示する統合フラットエントリを持ちますが、スカラーの `default: str` では「kEpsilon では 0.09、RNGkEpsilon では別の値」を表現できません。これらは `default` を空のままにし、現在どおり `ChoiceItem` の一覧で値を提示してください。再導出の後に気づくより、今言っておく方が安上がりです。

**Q3 — 共有の生成本体 1 つの上に、ファイル別の薄いモジュール 3 つ。** 確定です。理由は項目 2 のときより鋭いものです。Foundation の `constant/physicalProperties`(v10 以降)は粘性側と `thermoType` 側の**和集合**であるのに対し、OpenCFD は `constant/transportProperties`(粘性のみ)と `constant/thermophysicalProperties`(`thermoType` のみ)に分けたままです。したがって統合テーブル 1 つは**両方向に同時に誤ります** — OpenCFD の `transportProperties` の中で `thermoType` が解決してしまい(このファイルはそれを読みません)、かつ OpenCFD の `thermophysicalProperties` の中で粘性キーが解決してしまいます(こちらもそれを読みません)。項目 2 の失敗様式は一方向でしたが、これは対称です。

機構上の理由は変わらず、こちら側にあります。`schemas/registry.py::_build_file_key_schemas` は依然として対象ファイルごとに `table.update(schemas)` を行うだけで、キー単位のフィルタがありません。文字どおりの単一モジュール形の前提条件は今もこちらのキー単位フィルタであり、今もそれを必要とするものはありません。

具体形: 生成された `schemas/_thermophysical.py` が `build_schemas(target_file)` を公開し、加えて `schemas/physical_properties.py`・`schemas/thermophysical_properties.py`・`schemas/transport_properties.py` が各 25 行程度。`schemas/builtin.py` はこの 3 つを登録し、共有本体は import されるだけで登録されず、`TARGET_FILE` も宣言しません。`_turbulence_coeffs.py` とまったく同じ形です。`services/case_loader.py` は既に 3 つのファイル名すべてを列挙しているので、そちらでの作業はありません。

**カバレッジ下限について: 追加します。ただし今ではありません。** `tests/schemas/test_schema_coverage.py` は下限をフィクスチャ名でキーし、フィクスチャが何かにパースされたことを表明するため、フィクスチャが存在しないうちに下限の項目を足すと即座に失敗します。下限はモジュールと同じ変更で、実際のチュートリアルケースから採った 3 つのフィクスチャ(Foundation の `physicalProperties` 1 つ、OpenCFD の対 1 組)とともに、**0.70** から始めます。手書きのコアファイルが持つ 0.85〜0.90 ではなく、もう 1 つの生成辞書である `turbulenceProperties` に合わせた値です。

**輸送側は今すぐ着手できます。** 依存していたのは `default` の件だけで、本変更がそれに答えているため、`thermoType` の抽出器も本書のこれ以上の回答も待つ必要はありません。

## 8. OpenFOAM 14 は測定済み。残るは定数 4 つと判断 1 件(2026-08-13)

項目 7 と同じく、これも向きが逆です。測定は foamlore 側で完了しており、残る作業は **FoDE 側**にあります。2026-08-13 に対応済みで、変更内容は本項目の末尾に記録しています。

Foundation は 2026-07-14 に OpenFOAM 14 をリリースしました。foamlore はこれを 19 番目のチェックアウトとして追加し(`foundation-14` = `OpenFOAM-dev` のタグ `version-14`、コミット `c046c72`。`OpenFOAM-14` の動く master ではなく凍結タグ)、再導出を済ませています。記録は `facts/VERIFICATION.md` の「2026-08-13 — OpenFOAM 14 renamed the accessor and moved no value」、判断の理由は `fode-schemas/SPEC_RESPONSE_ja.md` の項目 8 にあります。

**このリリースは値を一切動かしません。** `foundation-13` との比較で、(モデル, 係数)の組 350 件のうち相違 0 件、追加 0 件、削除 0 件、モデル集合も同一、読むファイルも `constant/momentumTransport` のままです。既存のストア 441 件はバイト単位で同一に再生成され、追加は 23 件のみでした。

改名されたのは係数辞書のアクセサ、`this->coeffDict()` → `this->typeDict(type)` です。これを foamlore 内部の些事として処理せずここに書くのは、**引くキーが一緒に変わった**からです。`coeffDict()` は `RASDict().optionalSubDict(type() + "Coeffs")` でしたが、`typeDict(type)` は `RASDict().optionalTypeDict(type)` です。つまり **v14 が読むのは `kEpsilonCoeffs` ではなく `kEpsilon`** であり、これは従来のどのリリースも受け付けなかった辞書の綴りです。v14 自身のヘッダもそれを裏づけていて、22 個のモデルヘッダが記載例を `kEpsilonCoeffs { … }` から `kEpsilon { … }` へ書き換えています。`<model>Coeffs` をキーにした `<parent>.<key>` テーブルは、この新しい綴りを捉えられません。

**測定済み(2026-08-13。本項目を最初に書いた後に実施)。** foamlore が `src/OpenFOAM/db/dictionary` を全 19 チェックアウトの 3 つめの sparse サブツリーとして追加し、`optionalTypeDict`(foundation-14 `c046c72` の `dictionary.C:920-940`)を読みました。次の順に 3 つの綴りを解決します。

| 順 | 綴り | 受け付けるリリース |
|---|---|---|
| 1 | `RAS { kEpsilon { … } }` | **v14 のみ** |
| 2 | `RAS { kEpsilonCoeffs { … } }` | v7〜v14 |
| 3 | フラットな `RAS { Cmu 0.09; }` | v7〜v14 |

**v14 は v13 の厳密な上位集合であり、こちら側で壊れるものはありません。** 素の型名の綴りが増えただけで、`Coeffs` の綴りは削られていません。`<model>Coeffs` をキーにした `<parent>.<key>` テーブルは従来どおりのものを解決し続けます。v13 の `optionalSubDict`(`dictionary.C:926-941`)には連鎖自体が無く、1 回引いて無ければ外側の辞書を返すだけでした。`::optionalTypeDict` は foundation 7〜13 と opencfd の全リリースに存在しません。

これにより `<parent>.<key>` の作業は「修復」から「任意の上積み」に格下げされます。`<model>Coeffs` と並べて `<model>` を追加すれば v14 利用者の役に立ち、何も壊しませんが、今日時点で誤っている既存キーはありません。両方の引用は foamlore 側でキャッシュ済み・引用検証済みです(`get_fact model=dictionary`)。

### FoDE 側で必要な作業

1. **`schemas/_base.py` に定数 4 つ。** 新規 1 つ、改名 3 つです。既存の Foundation の区間はいずれも 1 リリース分伸びます。v13 にあった係数は v14 にもすべてあるため、区間は連続したままです。

   ```python
   FOUNDATION_V14      = "Foundation v14"    # 新規
   FOUNDATION_V8_V13   -> FOUNDATION_V8_V14  = "Foundation v8-v14"
   FOUNDATION_V9_V13   -> FOUNDATION_V9_V14  = "Foundation v9-v14"
   FOUNDATION_V10_V13  -> FOUNDATION_V10_V14 = "Foundation v10-v14"
   ```

   ここで追加ではなく改名にできるのは、foamlore 側で確認済みだからです。`_V13` の区間定数 3 つを参照しているのは生成された `_turbulence_coeffs.py` **だけ**で、手書きのスキーマエントリは 1 つも使っていません。

2. **モジュール 2 つを再ベンダリング**します。foamlore の `fode-schemas/` から `_turbulence_coeffs.py` と `momentum_transport.py` を取り込んでください。`turbulence_properties.py` は**変更されていません** — 対象ファイルを選ぶ条件が `n == "7"`、すなわち OpenFOAM 8 での改名という恒久的な境界であるため、Foundation タグは項目 4 の依頼どおり `FOUNDATION_V7` のままであり、広がりようがありません。

3. **テストのアサーション 1 箇所。** 項目 4 のときと同じ形です。`tests/schemas/test_turbulence_schemas.py:138` が `schema.supported_in == (FOUNDATION_V8_V13,)` をタプル完全一致で固定しています。完全一致のまま、測定値に合わせて更新してください。

4. **`docs/OPENFOAM_VERSIONS.md`(+ `_ja`)** — フォークと改名の表が Foundation 13 で止まっています。v14 はこのページが追跡している辞書に関しては何も改名していないので、必要なのは行の追加であって書き直しではありません。

### 判断が 1 件、こちら側に残されている

`FOUNDATION_SERIES` は今も `"Foundation v7-v13"` のままです。これを `v7-v14` に広げると `BOTH` も広がり、`BOTH` は `control_dict.py`・`fv_schemes.py`・`fv_solution.py`・`block_mesh_dict.py`・`turbulence_structure.py` にまたがるおよそ 256 件の手書きエントリに付いています。foamlore が測定しているのは乱流モデルだけであり、`controlDict` や `fvSchemes` のキーについて v14 の主張を代わりに裏づけることはできません。そのためラベルを広げずに、黙って処理するのではなく明示的に申し送ってきました。

`v7-v13` のままにすれば Detail ペインでカバレッジを過小に述べることになり、広げれば約 256 件のキーについて未検証のことを主張することになります。生成モジュールは `FOUNDATION_SERIES` を import していないので、どちらを選んでも再生成は問題なく通り、上記 1〜3 とは独立に決められます。

なお `tests/schemas/test_schema_coverage.py:224` は v7 から存在するキーについて `FOUNDATION_SERIES in foundation` を検査していますが、これは定数の**同一性**を見ており文字列の内容は見ていないので、どちらを選んでも影響を受けません。

### FoDE 側で対応した内容(2026-08-13)

`schemas/_base.py` に `FOUNDATION_V14` を追加し、Foundation の区間定数 3 つを `FOUNDATION_V8_V14`・`FOUNDATION_V9_V14`・`FOUNDATION_V10_V14` へ改名しました。`_turbulence_coeffs.py`・`momentum_transport.py`・生成ファイルの `THIRD-PARTY.md` を再ベンダリングしています(`turbulence_properties.py` はバイト単位で同一だったため手を触れていません)。`tests/schemas/test_turbulence_schemas.py` で固定しているアサーション 1 箇所も改名に追随させ、タプル完全一致のままです。上記の点 4、すなわち `OPENFOAM_VERSIONS.md` の表は、コミット `30c48f8`・`3dfa186`・`05eec50` ですでに対応済みでした。

本項目が挙げていなかった唯一のファイルであり、かつ実際に乖離していたのが `THIRD-PARTY.md` です。これは foamlore の `gen_attribution.py` が生成するファイルで、v14 のヘッダが持つ著作権表示年を FoDE 側が反映できていませんでした(`2011–2024` → `2011–2026`、チェックアウト 18 → 19、ファイル別 14 行への追記)。両リポジトリのどちらにもこれを検査する仕組みがありません — foamlore の `test_vendored_copy_matches` は `fode-schemas/*.py` のみをパラメータ化しています — ので、このパラメータ化を広げてもらうよう foamlore に依頼する価値があります。ライセンス表示のファイルは、黙って乖離させてよい種類のものではありません。

**判断は決着しました。`FOUNDATION_SERIES` は `"Foundation v7-v13"` のままとします。** このラベルが付くおよそ 256 件の手書きエントリは、Foundation 7〜13 と、`version-14` タグより前の `dev` ツリーに対して測定したものです。`controlDict` や `fvSchemes` のキーを 14 に対して測定した実績はありません。カバレッジを過小に述べる方が誤りとして安価です — 1 リリース短いラベルは「欠落」ですが、1 リリース長いラベルは「虚偽の主張」だからです。項目 9 として引き継ぎます。

## 9. `FOUNDATION_SERIES` が v7-v13 のまま(2026-08-13)

項目 8 の末尾に記録した判断から発生した項目で、foamlore 側ではなくこちら側で閉じるべきものです。FoDE が他のあらゆる箇所で対応しているリリースに対し、このラベルだけが 1 つ手前で止まっています。

Foundation 14 を使っている利用者から見ると、`BOTH` が付いたキー — `writeControl`、`ddtSchemes.default`、`solvers.solver`、`scale`、共有ライブラリ `finiteVolume`/`lduMatrix` の面すべて — は詳細ペインで `Foundation v7-v13, OpenCFD v2106-v2606` と表示されます。つまり「いま使っているリリースでは利用できない」と読めるということです。これは項目 6 が潰そうとした「タグが狭すぎる」問題そのものであり、1 リリース後ろにずれて再発しています。

`FOUNDATION_SERIES` を広げると `BOTH` も広がり、その付与箇所は 360 件です。

| モジュール | `BOTH` の付与箇所 |
|---|---|
| `control_dict.py` | 88 |
| `fv_schemes.py` | 81 |
| `snappy_hex_mesh_dict/*` | 115 |
| `turbulence_structure.py` | 29 |
| `fv_solution.py` | 25 |
| `block_mesh_dict.py` | 22 |

**どちらを選んでもテストは気づきません。** `tests/schemas/test_schema_coverage.py:224` が検査しているのは `FOUNDATION_SERIES in foundation`、すなわち定数の**同一性**であって文字列の内容ではないため、広げる前も後も通ります。ここではテストが緑であることは根拠になりません。次にこの箇所を見る人は、それを根拠と取り違えないようにしてください。

広げる際に同時に直すべき箇所が 2 つあります。

- `schemas/snappy_hex_mesh_dict/_structure.py:230,234` は `radius1`/`radius2` を `(FOUNDATION_V12, FOUNDATION_V13, OPENCFD_SERIES)` と、区間ではなく明示的な列挙でタグ付けしています。`FOUNDATION_V14` が存在するようになった今、これは「v14 も確認したうえで `searchableCone` は無かった」と読めますが、それを測定した事実はありません。項目 8 の変更では意図的に手を触れていません。正しい直し方は付け替えではなく実測です。
- `schemas/snappy_hex_mesh_dict/_add_layers.py:150-155` のコメントは、Foundation の「v7 から dev まで」全リリースが互換エントリを宣言している、と述べています。この `dev` ツリーは `version-14` タグより前のものなので、ラベルを広げると `minMedianAxisAngle` の主張がコメントの裏づける範囲を超えて静かに延びてしまいます。

### 測定に入る前に、ラベルが何を主張しているのかを確定させた

`schemas/_base.py` にはこのラベルの読み方が 2 つあり、互いに逆を向いていました。総称ラベルのコメントは「**個別リリースに紐づくのではなく**フォーク全体で共有されるエントリ向け」と述べており、これはフォーク全体への主張なので v14 は無償で仲間入りします。一方 `BOTH` のコメントは「**実測した全リリース**にわたって」対応と述べており、こちらは検証の主張なので v14 はまだそれを獲得していません。

これは好みではなく履歴で決着しました。`FOUNDATION_SERIES` を導入したコミット `15720b5` は、全スキーマを「バージョン横断の事実については Foundation 7-13 / OpenCFD v2106-v2606 に対して」監査したと述べ、チュートリアルに対するファイル別カバレッジを前後で測定して記録しています。**この区間は監査によって獲得されたものであり、したがって検証の記録です。** 「総称」が免除するのは個別リリース名を挙げることであって、実測されることではありません。`_base.py` の両方のコメントと DEVELOPER.md に、その旨を明記しました。

これにより安易な逃げ道は塞がれます。項目 9 はラベルの付け替えでは閉じられず、実測でしか閉じられません。

### 手元の証拠がどこまで届いているか

foamlore の `foundation-14` チェックアウトはもはや乱流モデル専用ではありません。項目 7 と項目 8 のために `src/finiteVolume/finiteVolume` と `src/OpenFOAM/db/dictionary` がスパースセットに加わっています。そのため 6 モジュールのうち 2 つは、新たな取得なしで測定できます。

- **`fvSolution` のリーダーのディレクトリは `foundation-13` と `foundation-14` でバイト単位で同一です。** これで `fv_solution.py` の 25 件が押さえられます。
- **`fvSchemes` のリーダーはリファクタリングされましたが、キーは 1 つも失われていません。** `read(const dictionary&)` は `readDict()` になり、渡された辞書ではなく `*this` を読むようになりましたが、`ddtSchemes`・`d2dt2Schemes`・`interpolationSchemes`・`divSchemes`・`gradSchemes`・`snGradSchemes`・`laplacianSchemes`・`fluxRequired` はいずれも読まれ続けています。
- **ただし v14 は 1 つ削除しています。** `select <name>;` をサブ辞書へ解決していた `fvSchemes::dict()` が `.C` からも `.H` からも消えました。FoDE は `select` キーを持ったことがないので誤りは生じていませんが、この走査が形式的な確認ではなく実質のある作業であることの証拠です。1 つのリリースで、誰も確認していなかった辞書ファミリにおいて、1 件が静かに削除されていました。

### 実測(2026-08-13): 確認 246 件、削除 1 件、未測定 60 件

最初の走査で届いたのは 307 件中 34 件だけでした。関係するリーダーがスパースチェックアウトにほとんど含まれていなかったためです。`foundation-13` と `foundation-14` はシャローではなく**部分クローン**(`blob:none`)なので、`git sparse-checkout add` は追加したパスの blob だけを取得します。`src/OpenFOAM/db/Time`・`src/OpenFOAM/matrices`・`src/finiteVolume`・`src/mesh/blockMesh`・`src/mesh/snappyHexMesh` で 1.7 秒・1.5 MB、`tutorials` で 6 秒・31 MB でした。差分方式である以上、両方のチェックアウトを同一に拡張しなければ何も測れません。

| モジュール | まだ読まれている | 削除された | 対象外 | チュートリアルにあり |
|---|---:|---:|---:|---:|
| `control_dict.py` | 38 | 0 | 28 | 52 |
| `fv_schemes.py` | 11 | 0 | 4 | 11 |
| `fv_solution.py` | 40 | 1 | 8 | 37 |
| `block_mesh_dict.py` | 15 | 0 | 6 | 18 |
| `turbulence_structure.py` | 17 | 0 | 39 | 16 |
| `snappy_hex_mesh_dict/*` | 65 | 0 | 35 | 87 |
| **合計** | **186** | **1** | **120** | **221** |

チュートリアルへの出現をそれ自体で証拠と数えると — そのリリースが当該キーを使うケースを実際に同梱しているということです — **確認 246 件、削除 1 件、未測定 60 件**になります。チュートリアル走査はソース走査の劣った代替ではなく、別種の証人です。ソースは「リーダーが存在する」ことを、チュートリアルは「出荷されたケースがそれを使っている」ことを示します。ソース走査では届かなかった 60 件を拾い上げました。これはコミット `15720b5` が最初の監査で用いた証拠でもあります。

**foamlore の `sources/` は gitignore された再生成可能な作業データ**(`/sources/*`、追跡されているのは `.gitkeep` のみ)なので、拡張しても何もコミットされません。ただし `facts/tools/fetch_sources.sh` がこれらのサブツリーを持つまでは再現可能な状態ではありません。そこが foamlore への依頼であり、走査そのものは FoDE 側にあります。

#### 走査が見つけたもの、そしてそれが判断を決着させる理由

1 件が **REMOVED** として返り、これは誤検出ではありません。`processorAgglomerator` は `foundation-13` の `GAMGAgglomeration.C` が読んでおり(`controlDict.found` / `.lookup`)、`foundation-14` には存在しません。v14 は `isDict`/`subDict` で選択する `processorAgglomeration { … }` サブ辞書に置き換えており、**互換ルックアップがありません**。したがって旧来の綴りは黙って無視されます。OpenCFD v2606 は今も読みます。FoDE はこのキーを `BOTH` でタグ付けしていました。**実測せずに `FOUNDATION_SERIES` を v7-v14 へ広げていたら、このタグは虚偽の主張になっていました。** 本項目を開く価値があったかという問いへの、これが具体的な答えです。

v14 の周辺コードを目視で読んだところ、走査では拾えない変更がもう 1 件見つかりました。`minCellsPerProcessor` と `nCellsInCoarsestLevel` が `lookupOrDefaultBackwardsCompatible<label>` の組になっています。つまり **Foundation 14 は `nCellsInCoarsestLevel` を `minCellsPerProcessor` へ改名し**、旧名も引き続き受け付けます。走査が沈黙したのは正しい挙動です。旧名は互換リストの中で v14 にも文字列として現れるため、「削除された」と報告すれば誤りだったからです。自動差分は消失を見つけますが、両方の綴りが残る改名は見つけません。

どちらも `schemas/fv_solution.py` で対応しました。いずれも変わったのは Foundation 側だけで、OpenCFD v2606 は両方の綴りを現行として読むため、どちらも `status="renamed"` にはしていません。そうすると OpenCFD 利用者に、自分のフォークが読まないキーを書くよう促してしまうからです。`processorAgglomerator` は `BOTH` のまま `deprecated_since` と注記を追加し、`minCellsPerProcessor` と `processorAgglomeration` は `renamed_from` を持つ新規の `FOUNDATION_V14` エントリとしました。

#### この注記が扱う範囲と、扱わない範囲

`schemas/_base.py` の `OPEN_ENDED_SERIES` により、詳細ペインは `FOUNDATION_SERIES` に「(これより新しいリリースは未検証)」を添えて表示します。これで v14 利用者が v13 までの区間を「自分には使えない」と読むことはなくなります。`tests/ui/test_supported_in_caveat.py` がこれを保護しており、ラベルを広げたのに集合を空にし忘れて注記が虚偽になるケースも検出します。

これは意図的に**ラベル単位であって、キー単位ではありません**。上記で実測した 246 件も注記付きで表示されます。`FOUNDATION_SERIES` は共有された 1 つの文字列であり、`supported_in` はキーごとの測定時期を記録しないからです。現時点ではこれが正しい割り切りです — 過大にではなく過小に述べる側に倒れます — そして本項目が閉じてラベルが広がれば、注記ごと消えます。

### 最初の走査(内容は上に更新済み。方法の記録として残す)

走査は `tools/scan_foundation14_keys.py` が行います。設計上これは**差分**走査です。チェックアウトがスパースであるため、「新しいツリーに無い」だけでは、キーが消えたのか、単にリーダーがチェックアウトされていないのかを区別できません。`foundation-13` と `foundation-14` を同一の方法で比較すればこの曖昧さは消えますが、その代わり報告できるのは古い側のツリーがすでに見えているキーに限られます。一致判定は意図的に緩めにしてあります(キー名が `.C`/`.H` 中でダブルクォート文字列として現れるか)。誤って「まだ読まれている」と判定してもよく見るべき対象を過小に見積もるだけですが、誤って「削除された」と判定すれば目視で気づけるからです。

`FOUNDATION_SERIES` が付いた手書きの `KeySchema` エントリ 307 件(ワイルドカード `<parent>.*` の行は除外)に対する結果です。

| モジュール | まだ読まれている | 削除された | 対象外 |
|---|---:|---:|---:|
| `control_dict.py` | 5 | 0 | 61 |
| `fv_schemes.py` | 9 | 0 | 6 |
| `fv_solution.py` | 1 | 0 | 48 |
| `block_mesh_dict.py` | 1 | 0 | 20 |
| `turbulence_structure.py` | 17 | 0 | 39 |
| `snappy_hex_mesh_dict/*` | 1 | 0 | 99 |
| **合計** | **34** | **0** | **273** |

**到達範囲はモジュール単位で数えた場合よりはるかに狭く、本項目の以前の見積もりは誤りでした。** `src/finiteVolume/finiteVolume` がチェックアウトにあっても `fv_schemes.py` のキーすべてが押さえられるわけではなく、`fvSchemes.C` 自身が読む 9 件だけです。スキーム*名*(`Gauss`・`linear`・`limited` など)は `src/finiteVolume/interpolation` などで宣言されています。スパースセットにある `fvSolution/` はヘッダ `fvSolution.H` 1 つだけで `.C` がありません。`solvers`/`relaxationFactors`/`PIMPLE` のキーはすべて `src/OpenFOAM/matrices/lduMatrix` と `src/finiteVolume/cfdTools` から読まれますが、どちらもチェックアウトされていません。素の `grep` で抜き取り検証済みです。`ddtSchemes` と `simulationType` は両ツリーに存在し、`writeControl` と `solver` はどちらにも存在しません。

したがって正直な現在地は、**34 件を実測して削除 0 件** — 弱いながらも実在する肯定的証拠 — と、未測定 273 件です。`FOUNDATION_SERIES` を広げる根拠としては足りません。

完了させるには `src/OpenFOAM/db/Time`・`src/OpenFOAM/matrices/lduMatrix`・`src/finiteVolume/cfdTools`・`src/mesh/blockMesh`・`src/mesh/snappyHexMesh` を `foundation-13` と `foundation-14` の**両方**のチェックアウトへ追加する必要があります。両方なのは、走査が差分方式であり、片側だけ揃っていても何も測れないからです。手順としては `git sparse-checkout add` ですが、ローカルミラーに `version-14` タグが無いため、上流からの取得が発生します。チェックアウトの定義表は foamlore の `facts/tools/fetch_sources.sh` にあるので、その半分は先方への依頼になります。走査そのものは本スクリプトであり、FoDE 側に置きます。

### 実測に基づく決着(2026-08-13): ラベルを拡大した

上記の「未測定 60 件」という数字自体が誤りであり、その訂正によって最も安価な直し方が変わりました。**そのうち 37 件は未確認なのではなく、構造上見えないものです。** モデルの係数辞書 — `kEpsilonCoeffs`・`kOmegaSSTCoeffs`・`SmagorinskyCoeffs`、および LES の delta 系 `…Coeffs` — は、どちらのツリーでも OpenFOAM ソース中に文字列リテラルとして現れません。実行時に `typeName + "Coeffs"` として組み立てられるからです(`dictionary.C:882/906/929`)。サブツリーをいくら追加しても、リテラル走査でこれらが見えるようになることはありません。そしてこれらは既に測定済みでもあります。項目 8 における foamlore の `optionalTypeDict` の読解が、まさにその測定です。

残りは **確認 283 件、削除 1 件、真に未測定 約 21 件** となります。測定済みの 283 件を付け替えるのは大きな編集ですが、未測定の 21 件を付け替えるのは小さな編集であり、しかも詳細ペインの注記がキー単位で正確になるという効果が無償で付いてきます。したがって次のようにしました。

- `FOUNDATION_SERIES` を `"Foundation v7-v14"` に変更。
- `FOUNDATION_V7_V13` を新設し、走査が到達できなかった約 21 件が保持します — `control_dict` 9 件(`fileHandler`、`functions` とその共通メンバ、`maxDi`)、`fv_schemes` 2 件(overset)、`fv_solution` 3 件(`nAlphaCorr`・`nAlphaSubCycles`・`finalOnLastPimpleIterOnly`)、`block_mesh_dict` 2 件、`snappy_hex_mesh_dict` 4 件、および `printCoeffs`。
- `OPEN_ENDED_SERIES` は `FOUNDATION_V7_V13` のみを保持し、ペインで注記が付くのはこれらのキーだけになります。
- `processorAgglomerator` は**先に**付け替えました。これは意図的です。`BOTH` を保持したまま `FOUNDATION_SERIES` を広げれば、存在しないと実証した唯一のリリースにまで、このキーの主張が伸びてしまうからです。現在は閉じた区間と `deprecated_since` を持ちます。これが「実測して存在しなかった」と「まだ確認していない」を区別します。

`tests/ui/test_supported_in_caveat.py` がこの区別を両側から保護しており、v14 を名乗るラベルが `OPEN_ENDED_SERIES` に残されたままになるケースも検出します。

**この項目を閉じる残りの条件:** 約 21 件の実測です。これらのリーダーは `src/` ではなくソルバのアプリケーション側にあるため、両方のチェックアウトに `applications/` を追加する必要があります。同じ `sparse-checkout add` を、ディレクトリ 1 つ分広げるだけです。

対応ではなく記録にとどめる留意点が 1 つあります。`fv_schemes` の overset 系 2 件は、そもそも Foundation 対応としてタグ付けされている点が疑わしいことです。overset は OpenCFD の機能です。スパースなツリーからは走査で決着させられず、また v14 が持ち込んだ問題ではなく従前からのタグ付けの問題なので、疑いだけで変更せずここに記しています。

### 実測による決着(2026-08-14)

`foundation-13` と `foundation-14` を、`src`・`applications`・`etc` の全体という同一の sparse セットへ拡張し(それぞれ 107 MB と 246 MB、`sparse-checkout add` 1 回)、21 件を実測しました。**ラベルのさらなる拡大は不要でした。必要だったのはキーの訂正です。** 結果は 3 通りに分かれました。

| 帰結 | 件数 | キー |
|---|---:|---|
| Foundation が v14 で読む → `BOTH` | 9 | `fileHandler`、`functions`、`functions.executeInterval`、`nAlphaSubCycles`、`nAlphaCorr`、`boundary.separationVector`、`minFaceFlatness`、`geometry.planeType`、`singleRegionName` |
| **そもそも Foundation のキーではない** → `(OPENCFD_SERIES,)` | 6 | `functions.writeToFile`、`functions.useUserTime`、`finalOnLastPimpleIterOnly`、`oversetInterpolation`、`oversetInterpolationSuppressed`、`mergeType` |
| Foundation が読んでいたが読まなくなった → 閉じた範囲 + `deprecated_since` | 5 | `maxDi`(v13)、`functions.regionType`(v13)、`functions.timeEnd`(v12)、`functions.formatOptions`(v8)、`minTriangleTwist`(v10) |
| 既に決着済み | 1 | `processorAgglomerator`(v14) |

同じ作業で 2 件を追加で訂正しました。いずれも 21 件の側からではなく、範囲を広げた走査が偶然通りかかって見つけたものです。`functions.timeStart` は `FOUNDATION_SERIES` を持っていましたが実際は Foundation v7〜v11(双子の `timeEnd` と同じく v12 で削除)。そして `geometry.radius1`/`radius2` は 11 件目の誤タグであり、本書全体の中で「リテラルには裏付けの読解が要る」ことを最も明快に示す例です(下記)。`schemas/_base.py` に閉じた範囲用の `FOUNDATION_V7_V9`・`FOUNDATION_V7_V11`・`FOUNDATION_V7_V12` を追加しました。

**`OPEN_ENDED_SERIES` は空になりました。** これが本項目の決着状態です。`FOUNDATION_V7_V13` は `processorAgglomerator` ただ 1 件が担う形で残り、意味が反転しました。「まだ見ていない」ではなく「実測した結果 13 で閉じた」です。Detail パネルはどこにも注記を付けません。付ける対象がもう存在しないからです。

#### 本書が誤っていた 4 点(その場で訂正)

- **リーダの所在が本項目の記述と違いました。** 上の「リーダは `src/` ではなくソルバアプリケーション側にある」は半分しか当たっていませんでした。実際には `src/OpenFOAM/global`・`src/OpenFOAM/meshes`・`src/functionObjects/field`・`src/twoPhaseModels/VoF`・`src/meshCheck` と `applications/` に分散していました。`applications/` だけを取得していたら大半は未測定のままでした。
- **21 件の内訳を数え違えていました。** 上の列挙は `fv_solution` を 3 件とし「加えて `printCoeffs`」としていますが、コード上は `fv_solution` が 4 件(4 件目は `processorAgglomerator`。モジュールの短縮名ではなくタプルを直書きしている)であり、`printCoeffs` が持つのは `BOTH` で、狭いラベルではありません。
- **overset に関する留保は正しく、かつ規模がまるで足りませんでした。** 疑わしい Foundation タグとして 2 件を挙げていましたが、実測では **11 件**です。overset の 2 カテゴリとその `.*` ワイルドカード 2 行、`mergeType`、`minTriangleTwist`、`finalOnLastPimpleIterOnly`、`writeToFile`、`useUserTime`、`geometry.radius1`/`radius2`。いずれも Foundation 利用者に対し、自分のフォークが読まないキーを「使える」と伝えていました。
- **`searchableCone` は Foundation に入ったことがありません。** `radius1`/`radius2` のタグは「v12 で Foundation に入った」としていましたが、Foundation の `src/meshTools/searchableSurfaces/` にあるのは `box closedTriSurface collection cylinder disk extrudedCircle plane plate sphere triSurface withGaps` で、**cone はありません**。v7〜v14 の全リリースでそうです。v12 の根拠とされたリテラル `"radius1"` は、無関係な topoSet／zone ソースである `truncatedConeToCell` のものでした。リテラルは一致していた。所有者が違っただけです。

#### 危うく誤るところだった 1 件と、ABSENT を必ず目視するようにした理由

`executeInterval` は OpenCFD 専用へ再タグされる寸前でした。Foundation のソースにリテラルとしては**一切**現れません。`timeControl.C:93` が `prefix_ + "Interval"` として名前を組み立てるからです。しかも Foundation は `etc/caseDicts/functions/mesh/checkMesh` でこのキーを出荷しています。37 件の `<Model>Coeffs` を隠していたのと同じ盲点が、今度は手書きキーで起きたわけです。走査が `tutorials` と並んで `etc/caseDicts` を読むようにし、3 つめの判定を `NOT COVERED` から **`ABSENT`** に改名して明示的な警告を添えたのはこのためです。

同じ範疇にあり、現状のままで正しいキーが 3 件あります。`advectionDiffusionCoeffs`(`+ "Coeffs"`)、`pRefCell`(`field.name() + "RefCell"`、`findRefCell.C:43`)、そして両フォークともリーダを持たず既に `status="ineffective"` である `minFlatness` です。

**決着条件は満たされました。** すべてのキーが、STILL READ であるか、`deprecated_since` を伴う REMOVED であるか、Foundation ラベルから外れたか、実行時組み立ての根拠を明示した ABSENT のいずれかです。走査に残る ABSENT 42 件は、`<Model>Coeffs` 38 件と上記 4 件です。

### foamlore への依頼 2 件

**1. 広げた範囲を `fetch_sources.sh` に載せてください。** 現状は `RENAME_SUBTREES` を持ちますが `src`・`applications`・`etc` は持たないため、`foundation-13`/`foundation-14` を新規に取得してもこの走査を再現できません。改名調査について項目 10 の依頼 1 が解消したのと同じ「偶然にしか再現できない」状態です。完全ツリーで実測したコストは、`src` + `applications` が 1 チェックアウトあたり約 83 MB、`etc` がさらに 4.5 MB です。

**`etc` は端数ではなく本質的です。** Foundation ツリー全体で `executeInterval` が現れる唯一の場所であり、これを外すと上記の誤った再タグがそのまま再発します。

**2. 改名調査に 1 組の取りこぼしがあり、その理由は項目 10 の再来です。** `functions.regionType` の年代を特定する過程で、Foundation 12 の `src/functionObjects/field/fieldValues/surfaceFieldValue/surfaceFieldValue.C:668` と `:698` に `dict.lookupBackwardsCompatible({"select", "regionType"})` が見つかりました。まさに `scan_renames.py` が収集するために存在する宣言の系統です。しかしこれは `facts/derived/renames.json` に**入っていません**。同ファイルの 21 組は 9 つの辞書をカバーしていますが、`src/functionObjects` は `fetch_sources.sh` にも `scan_renames.py` の `DICTIONARY_OF_PATH` にも無く、調査から見えないためです。

これは項目 10 の指摘がサブツリー 1 つ分外側で再現したものです。調査は依然として「たまたまチェックアウトされているもの」だけを報告しており、FoDE がスキーマを持つ辞書である `controlDict` の `functions` ブロックがその外にあります。`src/functionObjects` を取得範囲とパス対応表の両方に追加し、再導出してください。この組は件数以上の価値があります。Foundation は `regionType` を `select` の後方互換の綴りとしてのみ読み、v13 以降はどちらも読みません。一方 OpenCFD は `regionType` を現行名として読みます。[OPENFOAM_VERSIONS.md](OPENFOAM_VERSIONS_ja.md) の「ファイル内での改名」節が既に警告しているフォーク間不一致の形であり、しかも「Foundation が**両方の**綴りを捨てた」という、同ページにまだ例のない第 3 の変種です。

FoDE 側はこの読解に基づいて既にタグ付けを済ませているので、再導出待ちで止まるものはありません。調査が得るのはこの組自体と、19 チェックアウト分のそのサブツリーが宣言している他のすべてです。

## 10. 改名走査が FoDE の辞書の大半を見ていない(2026-08-13)

これは副産物です。項目 9 のために Foundation の各チェックアウトへ `src/OpenFOAM/db/Time`・`src/OpenFOAM/matrices`・`src/finiteVolume`・`src/mesh/blockMesh`・`src/mesh/snappyHexMesh` を手作業で追加しました。`scan_renames.py` は `sources/*/`、すなわちチェックアウトされているものを読みます。したがってこれまでは乱流モデルのサブツリーしか見ていませんでした。

`foundation-14` において `src/MomentumTransportModels` の外にある `lookupBackwardsCompatible` 宣言を数え、機構を*定義*しているだけの `dictionary.C`/`.H`/`dictionaryTemplates.C` を除くと、FoDE が扱う辞書の中に実際の呼び出し箇所が 5 件あります。

| ファイル | 辞書 |
|---|---|
| `db/Time/TimeIO.C` | `controlDict` |
| `cfdTools/…/pimpleNoLoopControl.C`(×2) | `fvSolution` |
| `lduMatrix/…/GAMGAgglomeration.C` | `fvSolution` |
| `mesh/snappyHexMesh/…/medialAxisMeshMover.C` | `snappyHexMeshDict` |
| `finiteVolume/pointMesh/pointMeshMover.C` | — |

**うち 1 件はすでに FoDE の不具合であり、しかも v14 の問題ではありません。** `pimpleNoLoopControl.C` は `{"transportCorrectionFinal", "turbOnFinalIterOnly"}` を宣言しています。FoDE は `turbOnFinalIterOnly` を `BOTH` タグの通常の有効キーとして持ち、`transportCorrectionFinal` はまったく持っていませんでした。つまり歴史的な綴りを現行として提示し、その後継名を示せない状態でした。Foundation の 8 チェックアウト全部に対してリリースごとに実測したところ、**この改名は Foundation 11** であり、後方互換は v14 まで維持されています。3 リリースにわたって誤っていたことになり、それが表面化したのは無関係な理由でサブツリーを取得したからにすぎません。同じファイルの `{"simpleRho", "SIMPLErho"}` の組はさらに古く、v7 以降のすべての Foundation リリースが `simpleRho` を読みますが、FoDE はどちらの綴りも持っていませんでした。

どちらも FoDE 側で修正済みです(`schemas/fv_solution.py`、および新しい `FOUNDATION_V11_V14`)。フォーク非対称として扱っています — OpenCFD v2606 は `turbOnFinalIterOnly` と `SIMPLErho` を*現行*の名前として読み、Foundation 側の綴りをどちらも持たないため、いずれも `status="renamed"` にはしていません。

### 依頼 3 件

1. **取得範囲を広げてください。** 上記 5 つのサブツリーを、Foundation の全チェックアウトについて `fetch_sources.sh` に追加してください(ローカルでは手作業で追加済みなので、上記の測定はこれが入るまで偶然にしか再現できません)。コストは小さく、チェックアウトは部分クローン(`blob:none`)なので `git sparse-checkout add` は追加分の blob しか取得しません。1 チェックアウトあたり 1.7 秒・1.5 MB、`tutorials` を加えてもさらに 6 秒・31 MB です。

2. **広げた範囲で改名を再導出してください。** 上記 5 件は 1 リリースが示すものにすぎません。Foundation 8 件と OpenCFD 11 件のチェックアウトからはさらに出てくるはずで、それぞれが FoDE 側の `renamed_from`/`use_instead`/`deprecated_since` と、foamlore がスプライスする `OPENFOAM_VERSIONS.md` の「ファイル内での改名」節に反映されます。なお現在その節にはこれらのどれも記録されていません。

3. **`THIRD-PARTY.md` を保護してください。** これは `gen_attribution.py` が生成し FoDE へ取り込まれるファイルですが、`test_vendored_copy_matches` は `fode-schemas/*.py` のみをパラメータ化しているため、乖離しても誰も気づきません。実際 v14 の作業で見つかった時点で 32 行ずれていました(`2011–2024` と `2011–2026`、チェックアウト 18 と 19、ファイル別の著作権行 14 件)。ライセンス表示の記録であり、黙って乖離させてよい種類のファイルとしては最悪の部類です。

### foamlore 側で完了(2026-08-14)

3 件すべてが着地しました。コミットは `86a5bb4`(「辞書のリーダも取得し、帰属ファイルを保護する」)と `2b314b8`(「改名の全数調査を乱流サブツリーの外へ広げる」)です。

1. **取得範囲が広がりました。** `facts/tools/fetch_sources.sh` に `RENAME_SUBTREES` の一覧 — `src/OpenFOAM/db/Time`、`src/OpenFOAM/matrices`、`src/finiteVolume`、`src/mesh/blockMesh`、`src/mesh/snappyHexMesh` — が入り、`src/OpenFOAM/db/dictionary` と並んで全チェックアウトに適用されます。上記の測定は偶然ではなく再現可能になりました。

2. **その範囲で改名が再導出されました。** `facts/derived/renames.json` は**改名対 21 件、未解決 0 件**を保持し、`render_renames.py` を通じて `fode-docs/renames_table.md` に描画され、コミット `1ca5680` により本リポジトリの [OPENFOAM_VERSIONS.md](OPENFOAM_VERSIONS_ja.md) の生成領域 `renames-table` にスプライスされています。上記の呼び出し箇所 5 件はすべて表に入りました — `writeFrequency` → `writeInterval`、`SIMPLErho` → `simpleRho`、`turbOnFinalIterOnly` → `transportCorrectionFinal`、`nCellsInCoarsestLevel` → `minCellsPerProcessor`、`minMedianAxisAngle` → `minMedialAxisAngle` — さらに、上表の `pointMeshMover.C` の行が当時は辞書名を挙げられなかった `motionSolver` → `pointMeshMover` も入っています。**依頼 2 の末尾「なお現在その節にはこれらのどれも記録されていません」はもはや成り立たず、ここで撤回します。**

3. **`THIRD-PARTY.md` が保護されました。** `test_vendored_copy_matches` を広げる形ではありません — あれは `fode-schemas/*.py` をパラメータ化しており、帰属ファイルはそのディレクトリにも `.py` にも該当しないためです。代わりに専用の対となるテスト `test_vendored_attribution_matches()` が `facts/tests/test_generated_schemas.py` に追加され、foamlore 側の写しと FoDE 側の写しをバイト単位で比較します。現時点で両者は一致しています。

### FoDE 側が負うもの

現時点では、`tools/scan_foundation14_keys.py` をチェックアウトの状態に追随させること以外にありません。このスクリプトは foamlore がより適切に答えられる問いに対する間に合わせです。リテラルを読むため実行時に組み立てられるキーには盲目で、消失は見つけられても両方の綴りが残る改名は見つけられません。`nCellsInCoarsestLevel` → `minCellsPerProcessor` がこれをすり抜け、目視で読む必要があったのはそのためです。

実行時組み立てへの盲目さは、もはや `<Model>Coeffs` の一群だけの例ではありません。項目 9 の締めの測定で、手書きキーにも実例が見つかりました。`executeInterval` は `prefix_ + "Interval"` として組み立てられ(`src/OpenFOAM/db/functionObjects/timeControl/timeControl.C:93`)、どの Foundation ツリーにもリテラルとしては現れませんが、Foundation は `etc/caseDicts/functions/mesh/checkMesh` でこのキーを出荷しています。リテラル走査だけなら「そもそも Foundation のキーではない」と結論していたはずです。項目 9 を参照してください。

**そして本項目自身の指摘が、サブツリー 1 つ分外側で再現しました。** 上の依頼 3 件は、調査が乱流サブツリーしか見ていなかったことから提起されたものです。今では 5 つ多く見えるようになりました。それでもなお `src/functionObjects` は見えておらず、そこでは Foundation 12 が `lookupBackwardsCompatible({"select", "regionType"})` を宣言しています(`surfaceFieldValue.C:668,698`)。この組は再導出後の `renames.json` にも入っていません。依頼としては項目 9 の 2 件目に記載したのでここでは繰り返しませんが、教訓は本項目のものです。**取得範囲を一度広げても調査は完了せず、境界が動くだけです。** FoDE がスキーマを増やすたびにサブツリー候補が増え、調査が完全と言えるのは実際にチェックアウトされている集合に対してだけです。だから注視すべきは走査ではなく取得範囲の方です。

## 11. `BOTH` タグは、狭いタグのようには検証されてこなかった(2026-08-14 提起、2026-09-05 再計画)

報告ではなく項目 9 の結果から開いた項目です。項目 9 が実測した 21 キーのうち
**11 件が、実際には読んでいないフォークを名乗っていました**。この失敗の仕方に、
あのキー群に固有の要素は何もありません。たまたま吟味を促すラベルの下にあっただけです。
`FOUNDATION_V7_V13` は「未検証」を意味するために存在したので、いずれ誰かが検証しました。
`BOTH` は**2 つ**のフォークを主張し、しかも疑いを一切表明しません。

### 対象の実際の規模

2026-09-05 に、モジュールの本文ではなくレジストリから実測した値です。

| モジュール | `BOTH` キー | (うちワイルドカード) | `BOTH` **選択肢** |
|---|---:|---:|---:|
| `snappy_hex_mesh_dict/*` | 120 | 7 | 97 |
| `turbulence_structure.py` | 108 | 39 | 107 |
| `control_dict.py` | 66 | 3 | 142 |
| `fv_solution.py` | 66 | 5 | 145 |
| `fv_schemes.py` | 29 | 10 | 110 |
| `block_mesh_dict.py` | 22 | 1 | 28 |
| **合計** | **411** | **65** | **629** |

2026-08-14 の記録に対する訂正が 2 点あります。キー数は約 360 ではなく 411 です。
そして**選択肢の値が数えられていませんでした**。さらに 629 件あり、しかも軽い対象では
ありません。実際に出荷された不具合 2 件はいずれも選択肢の値でした。Foundation 14 から
消えた `processorAgglomerator` のメソッド名と、`generalizedNewtonian` のフォーク改名です。
実際の対象面はおよそ 1,040 箇所です。

スキーマ層全体の規模で見ると比率が分かります。手書きエントリはすべて `supported_in` を
持ちます。キー 467・選択肢 663 の計 1,130 件で、そのうち**1,040 件、92% が未検証の
`BOTH`** です。生成モジュール側はキー 964・選択肢 807 を持ち、いずれも 19 リリースに
わたって実測済みです。詳細ペインは両者を同一に描画するため、利用者には実測値と推測の
区別がつきません。

### 項目 9 の手法は転用できない

この項目は当初「手順は文書化されており、走査ツールは既に `BOTH` を見ている」と
記録されていました。2026-09-05 に実際に試したところ、そうではないことが分かりました。
理由は機能の不足ではなく構造的なものです。

**ツリー全体の文字列走査では判別できません。** OpenCFD の `src` からは 30,351 個の
相異なる文字列リテラルが得られます。`block_mesh_dict` の検査可能な `BOTH` キー 20 件に
対して実行すると、**両フォークとも ABSENT は 0 件**でした。一般的な名前(`type`・
`name`・`faces`・`scale`・`geometry`)は、この規模のプールなら誰が読むかに関係なく
何かに一致します。これは項目 9 の `radius1`/`truncatedConeToCell` の失敗が規模を得た
ものです。項目 9 で手法が機能したのは、あれが同一フォークの 2 チェックアウト間の
**差分**であり、共通の偽陽性率が相殺されたからです。`BOTH` は絶対的な問いを立てるので
相殺されません。

**読み手にスコープを絞ると判別力は戻り、代わりに 2 つの新しい誤りが入ります。**
`src/mesh/blockMesh` に絞るとプールは 362 リテラル、雑音は 84 分の 1 になり、
`inGroups` は blockMesh の読み手に対して正しく ABSENT へ転じます。しかし:

- `inGroups` は `blockMeshDict` の正当なエントリのままです。下流の `polyPatch` が
  処理しています。単一の読み手への限定は*狭すぎる*ことがあります。
- `mergePatchPairs` は **`src/` ではなく `applications/` で読まれます**。OpenCFD では
  `applications/utilities/mesh/generation/blockMesh/blockMesh.C` が唯一の出現箇所です。
  `src/mesh/blockMesh` だけを挙げた対応表は、現役のキーをそのフォークが読んでいないと
  報告してしまいます。

  *(本節の初稿は、`mergePatchPairs` がどちらのフォークの `.C`/`.H` にも現れないと
  主張していました。これは誤りで、切り詰められた grep の出力と、その後の誤った
  ディレクトリに限定した grep が原因です。2026-09-05 訂正。このキーは文字列走査の
  盲点ではなく対応表の落とし穴であり、この設計で実際に危ういのはどちらかを示す点で、
  むしろ強い警告です。)*

文字列走査の真の盲点は別にあり、全体索引で確認しました。`executeInterval` と
`executeControl` は `prefix_ + "Interval"` で組み立てられ、リテラルとしては現れません。
`turbulenceProperties` の `BOTH` キー 63 件のうち 41 件を占める `<Model>Coeffs` 群は
`typeName + "Coeffs"` です。`minFlatness` はどちらのフォークも読んでおらず、これは
OpenCFD へ #3592 として報告済みの上流の不具合です。`radius1`(誤った読み手に一致)と
併せて、**走査結果だけで再タグ付けしない**ことがここでは注意事項ではなく設計上の
制約である理由です。

### 証拠は、この項目が想定した場所になかった(2026-09-05 解決)

| | Foundation | OpenCFD(発見時) |
|---|---|---|
| foamlore の `sources/` | 完全。`src` + `applications` + `etc`、チェックアウトあたり 8.5〜9.3k の `.C`/`.H` | **`src` の 50 サブディレクトリ中 13 個のみ。`applications/` も `etc/` も無し** — 約 3.5k ファイル |
| ディスク上の他の場所 | `openfoam-sources/OpenFOAM-{7..12,dev}` | `/usr/lib/openfoam/openfoam{2212..2606}` が約 21k ファイル、加えて `OpenFOAM-v{2106,2206}` |

Foundation は項目 9・10 の作業中に拡張されましたが、OpenCFD は一度も拡張されていません
でした。これらのチェックアウトに対して**内容**の走査を行えば、有効な OpenCFD キーが
数百件 absent と判定され、フォークが剥がされていたはずです。ソースツリーに関する注意書きが
警告しているとおりの失敗です。

**これが無効化しなかったもの。** 本節の最初の版は、狭いチェックアウトのせいで foamlore の
改名走査と辞書ファイル数の集計も不健全であり、拡張はその修復だと主張していました。
どちらの主張も誤りで、2026-09-05 に foamlore から訂正がありました。

- これらのチェックアウトは**部分クローン**(`filter=blob:none`)であり、パスは常に
  すべて列挙されていました。欠けていたのは blob の*内容*だけです。`opencfd-v2606` は
  26,137 パス(うち 11,608 が `tutorials/` 配下)を列挙しており、ディスク上に実体化して
  いたのはそれよりはるかに少ない数でした。
- `scan_dictionary_files.py` は固定したコミットに対する `git ls-tree` を読んでおり、
  作業ツリーは読みません。決定性のための意図的な設計です。集計は一貫して健全でした。
- 改名走査は**不健全だったのではなく、範囲が限定されていた**だけです。
  `scan_renames.scope_of()` は `CENSUS_SUBTREES ∩ そのチェックアウトが持つもの`であり、
  生のスパース集合ではなく*宣言された*一覧です。どちらのフォークが物理的に広いかに
  関係なく同じ幅で走査するための設計です。その範囲内での「OpenCFD はこれを宣言していない」
  は健全であり、範囲外については何の判定も下していません。

したがって幅の非対称は実在しましたが、影響は限定的でした。妨げていたのはツリー全体の
**内容**走査だけで、それは後述のオラクルがまさに必要とするものです。本項目の前提条件で
あって、公開済みの何かの修復ではありません。

**同日に解決。** 19 チェックアウトすべてが `src applications etc tutorials` を取得する
ようになりました。`opencfd-v2606` は `src` サブディレクトリが 13 から 50 になり、
1 つも持っていなかった 3 つのトップレベルツリーを獲得し、`sources/` は 2.0 GB から
4.9 GB になりました。`tutorials` は本項目が依頼した範囲を超えて追加されています。
第 1 段階の出荷辞書走査がこれを必要とするのに、当初の依頼は `src` + `applications` +
`etc` としか書いておらず、自分の次の段階に対して記述が不足していたためです。
その後 `regen_check.sh` は 6 つの成果物レイヤすべてでバイト単位一致し、134 テストが
通りました。これ自体が、公開済みのものが狭い幅に依存していなかったことの証拠です。

### 決定: `supported_in` は検証するのではなく生成する

3 つの選択肢を比較した上で、2026-09-05 に決定しました。

スキーマ生成を**すべて** foamlore へ移す案は退けました。`executeInterval` と 41 件の
`<Model>Coeffs` が示すとおり、コンストラクタを読む生成器はすべてのキーを見られません。キー単位の判断
(`renamed_from`・`status`・`use_instead`)は利用者に何を伝えるかの決定であり、
foamlore は項目 3 で既にこれを引き受けないと述べています。ファミリごとの 2 つめの
抽出器が高くつくことは `docs/SCHEMA_CANDIDATES_ja.md` が述べているとおりです。そして
FoDE は姉妹リポジトリなしにスキーマを追加できなくなります。

代わりに、分担は保ったまま**境界を移す**案を採りました。現在の境界は*ファミリ*単位で、
乱流は生成・その他は手書きです。これは原理的な境界ではなく、扱いやすかった境界でした。
本来は**主張の種類**で分けるべきです。

| 主張 | 担当 |
|---|---|
| `supported_in` — フォーク X のリリース Y はキー K を読むか | **foamlore** — 純粋な事実、判断を含まない |
| 選択肢の*一覧* — 実行時の選択テーブル | FoDE |
| `renamed_from` / `status` / `use_instead` | FoDE — 判断 |
| `required` / `default` の意味論 | FoDE |
| 説明・注記、FoDE 自身の UI に関する記述 | FoDE |
| 係数のファクト | foamlore(現状どおり) |

決め手となる論点はこれです。**この項目が必要とする計測器は、そのままバージョンタグの
オラクルです。** 読み手スコープの走査と出荷辞書の走査を両フォークに対して行う仕組みは、
どちらの道を選んでも作ることになります。一度きりの検証として走らせれば 1,040 箇所を
直せますが、手書きタグは古びるので OpenFOAM のリリースごとに再実行が必要です。生成器
として組み込めば、タグは構成上正しくなり、この項目はリリースが動いたときに落ちる
テストになります。第 1 段階の費用は同じで、5 か月後の第 5 段階がありません。

### 結果(2026-09-08)

実測は完了しました。7 辞書・19 リリース・354 の範囲のうち 340 件が公表可能です。
14 件の拒否にはすべて文章による理由が付き、いずれも*終端*です。7 件は `scope_limited` で、
読み手が `applications/modules` へ移り、こちら側は設計上ソルバを対象外としているためです。
残る 7 件は `no_evidence` で、FoDE 側の `runtime_assembled` または `known_unseen` が
「探すな」と正しく指示しているものです。

取り込みは 7 辞書中 5 つで完了しました。`blockMeshDict`・`fvSchemes`・`fvSolution`・
`controlDict`・`snappyHexMeshDict` は比較可能なキー**すべて**(189 件)で実測と一致します。
本プロジェクトのバージョン主張が、単に自己矛盾がないだけでなく検証済みと言えるのは初めてです。
乱流 2 ファイルに残る 108 件の相違は原因が 1 つで、DEVELOPER_ja.md の**更新候補**に
記録しています。1 つのモジュールが 1 つのテーブルで 2 つの辞書名を賄うため、ファイル別の
実測が正しく食い違う場所でもすべてのキーが `BOTH` を主張します。誤った*ファイル*に出る
half は修正済み(`KeySchema.only_in_files`)で、ファイル別の*タグ*は未修正です。

**両者の間で誤ったタグ 9 件を撤回しました。** いずれも FoDE 自身のテストでは見つかりません
でした。2 件は単なる誤情報ではなく実行を拒否または中断させるものであり、さらに OpenFOAM
本体の不具合 2 件を報告して v2612 へ取り込まれました。どちらもスキーマを読むだけでは
到達できないものです。

### 計画

**第 0 段階 — 証拠(foamlore)。2026-09-05 完了。** `opencfd-*` チェックアウトを
`src applications etc tutorials` へ拡張し、Foundation 側と揃えたうえで、第 1 段階の
出荷辞書走査のために `tutorials` を追加しました。何が解決され何がされなかったかは
上記の節を参照してください。

**第 1 段階 — オラクル(foamlore、FoDE が入力を提供)。** 単独では成立しないため、
証拠は 3 系統にします。

1. 読み手にスコープを絞った文字列走査。FoDE が供給する「辞書 → 読み手のパス」対応表で
   駆動します(約 15 項目。`blockMeshDict` → `src/mesh/blockMesh`、`snappyHexMeshDict`
   → `src/mesh/snappyHexMesh`、`controlDict` → `src/OpenFOAM/db/Time` +
   `src/functionObjects` など)。
2. 出荷辞書の走査。`tutorials/`・`etc/caseDicts/`・`applications/test/*/system/` を対象と
   し、どの名前でもソースが読まないキーに対する唯一の証拠になります。`SHIPPED_DIRS` は
   `tools/scan_foundation14_keys.py` に既にあります。
3. 両方を通り抜けたものの人手による読解。

判定はフォークごとに 3 値(`READ`・`SHIPPED-ONLY`・`UNSEEN`)とし、現在の 2 値では
ありません。

**第 2 段階 — 取り込み。小さいモジュールから。** `block_mesh_dict`(22)→
`fv_schemes`(29)→ `fv_solution` / `control_dict`(各 66)→ `snappy_hex_mesh_dict`
(120)→ `turbulence_structure`(108。うち 39 はワイルドカードで、多くは既に foamlore の
担当)。モジュールごとの初回は、既存の手書きタグを残したままオラクルと*差分*を取り、
置き換えないでください。対応表の 1 項目の誤りは辞書 1 つ分を一度に誤らせますが、
手書きタグの誤りは 1 キーずつだからです。各モジュールは単独で出荷できる修正になります。

**照合は 2 リリース、公表は 19 リリースから。** フォークごとに 1 リリースを固定して
測った判定集合は*相互照合*用の成果物です。2 つの独立した実装の間で食い違いが出たとき、
それがリリースの違いではなく測定の誤りを意味するからこそ、突き合わせに意味があります。
これは `supported_in` の供給源ではありません。2026-09-06 に `functions.mode` がそれを
証明しました。foundation-12 と opencfd-v2606 で測ると、きれいに OpenCFD 限定と読めます。
しかし Foundation は v7 と v8 で `fieldMinMax` を同梱しており、そこで
`lookupOrDefault<word>("mode", "magnitude")` を読んだうえで、v9 でこのモデルを落として
います。この判定を公表していれば、誤ったタグを別の誤ったタグへ置き換えたうえに、実測と
しての権威まで与えていたことになります。本項目が防ごうとしているのはまさにこの害です。
`tools/fode-reader-paths.json` はこの制約を、消費側の判断に委ねるのではなく
`verdicts_publishable_from: all_releases` として宣言しており、テストで固定しています。

**第 3 段階 — 選択肢 629 件。** キーが済んだあと、同じ計測器で。

**費用。** 計測器はおよそ 1 日。人手の読解は圧縮できず、キーと選択肢を合わせて
300〜400 箇所を人が読む見込みです。当初計画との違いは、この費用がリリースごとではなく
一度だけで済むことです。

## 12. 層流応力モデルが未実測、`phaseSystemModels` が未取得(2026-09-03 提起、2026-09-04 完了)

どちらの依頼も何かをブロックするものではありません。これらを提起したきっかけの修正は FoDE 側で
すでに着地しており、説明文は手書き、タグはローカルで実測済みです。2 件とも「ここで手作業で
実測した」状態と「ストアで一度導出される」状態との差を埋めるための依頼です。

### 経緯

「`RASModel` を改名すると RAS セレクタの選択肢が失われる」という報告が発端でした。実際には
失われておらず、`RAS.RASModel` と `RAS.model` は以前から 1 つのリストを共有し、テストでも固定されて
います。しかし確認の過程で、**同じ手書きリスト**に実在の不具合が 5 件見つかり、うち 4 件は
単純にタグが誤っていました。

| 不具合 | 表示 | 19 チェックアウトの実測 |
|---|---|---|
| `SpalartAllmarasDES`/`DDES`/`IDDES`、`kOmegaSSTDES` | Foundation 専用 | 両フォークの全リリース |
| `kOmegaSSTDDES`、`kOmegaSSTIDDES` | 選択肢に無い | OpenCFD の全リリース |
| `GEKO` | OpenCFD v2106-v2606 | v2606 のみ |
| `sigma` / `EBRSM` | OpenCFD v2106-v2606 | v2212 以降 / v2206 以降 |
| `kOmega2006` | Foundation v7-v14 | v9 以降 |
| `laminar` セレクタ | 4 択、すべて `BOTH` | 7 択、うち 5 つはフォークまたは範囲に固有 |

上 2 行の原因は転記ミスではなく**手法**の誤りなので、記録しておく価値があります。リストを
`.../turbulenceModels/LES/` のディレクトリ一覧から読んでいた一方、OpenCFD は DES モデルを隣の
`DES/` に置いています。現在は実行時の選択テーブル — `makeRASModel`・`makeLESModel`・
`makeLaminarModel` に渡される名前 — に切り替えました。そのテーブルに無い名前は、ツリーに何が
あろうと構築できないからです。

なお `kOmegaSSTDDES` と `kOmegaSSTIDDES` は既に `MODEL_DOCS` に入っていました。foamlore は導出済みで、
欠けていたのは手書きリストのほうだけです。そのため FoDE は `kOmegaSSTDDESCoeffs` を説明できる一方で
`kOmegaSSTDDES` は選ばせない、という状態になっていました。

### 依頼

**依頼 1 — 事実ストアを層流応力モデルへ広げる。** これは項目 5 の境界を一貫して適用するものです。
項目 5 は選択肢の*リストとタグ*を `turbulence_structure.py` に、*散文*を生成側に割り当てており、
`MODEL_DOCS` は RAS/LES の 29 モデルについてはそれを守っていますが、層流モデルは 0 件です。つまり
`laminar.model` は FoDE がすべての説明を手書きしている唯一のセレクタであり、これは項目 5 が
防ぐために存在する非対称そのものです。負荷は小さいはずです。

- 7 クラスは `laminar/` にあり、`fetch_sources.sh` が既に取得しているサブツリー内で `RAS/`・`LES/` と
  同階層です — 取得設定の変更は不要;
- いずれも抽出器が既に読んでいる Doxygen の `Description` ブロックを持ち、`Maxwell`・`Giesekus`・
  `PTT`・`lambdaThixotropic` は `MODEL_DOCS` の注記が既に引用しているのと同じ形の `Reference:`
  ブロックを持ちます;
- フォークで分かれる綴りは、チェックアウト集合が交わらない 2 つのモデル名にすぎず、`collapse()`
  が既に扱える形です。

回答を照合するための期待出力として、実測表を挙げます。

| モデル | Foundation | OpenCFD |
|---|---|---|
| `Stokes` | 7-14 | v2106-v2606 |
| `Maxwell` | 7-14 | v2106-v2606 |
| `generalizedNewtonian` | 7-8 | v2106-v2606 |
| `generalisedNewtonian` | 9-14 | — |
| `lambdaThixotropic` | 9-14 | — |
| `Giesekus` | 7-14 | — |
| `PTT` | 8-14 | — |

`tests/schemas/test_turbulence_schemas.py::TestSelectorChoiceLists::test_no_laminar_model_is_covered_by_foamlore`
が仕掛けです。これらの名前が `MODEL_DOCS` に無いことを表明しているため、この依頼が着地した瞬間に
失敗します。それが、手書きの説明文を上流ヘッダに置き換える合図になります。

**依頼 2 — OpenCFD チェックアウトからは `twoPhaseTransport` が見えない。** `fetch_sources.sh` は
Foundation 側には `src` + `applications` + `etc` 全体を与えていますが、OpenCFD 側は
`src/TurbulenceModels` と census サブツリーのみです。`src/phaseSystemModels` はどちらにも
入っていないため、`simulationType twoPhaseTransport` — FoDE がスキーマを持つ辞書のキーの*値*で、
両フォークの全リリースのチュートリアルが書いているもの — が `sources/` からは OpenCFD 全体に
わたって実測できません。今回は別途の完全な v2606 ツリーを読むことでのみ確認しました。項目 10 が
サブツリー 1 つ外側で再発した形です。依頼は OpenCFD 側への `src/phaseSystemModels` の追加です。

### 回答(2026-09-04)

依頼 2 件とも完了しました — `facts/store/laminar/`、78 ストア、4 つめのファミリー
（`facts/tools/laminar_models.py`）で、FoDE の期待表と正確に一致しました（手作業で測った 3 つの
範囲を含む: `lambdaThixotropic` は `FOUNDATION_V9_V14`、`sigmay` は `FOUNDATION_V11_V14`、
`residualAlpha` は `FOUNDATION_V12_V14` —「訂正の必要は何もありませんでした」）。
`src/phaseSystemModels` は `CENSUS_SUBTREES` に加わり、`twoPhaseTransport` の `BOTH` タグは
Foundation 側からの読み取りではなく OpenCFD 自身のツリーに対して確認済みです。

**`MODEL_DOCS` の適用は、この項目を閉じた時点では意図的に配線していませんでした**。
提案は **2026-09-05** に採用されました。見送った理由はそのまま有効で、だからこそ出荷した
形は狭いものになっています。`generate_fode_schemas.py` は与えられたモデルごとに散文と
`SCHEMAS` エントリの両方を出力しますが、層流モデルの `SCHEMAS` エントリは
`turbulence_structure.py` が既に手書きで持っているもの（`laminar.MaxwellCoeffs`、
`nuM`/`lambda`/`modes`、生成器が出力しない `required=True`、`modes` については生成器が出さない
散文つき）と衝突していたはずです。`builtin.py` は手書きモジュールを先に読み込むため、衝突は
生成器側が勝つ形で黙って解決してしまいます。

**代わりに出荷したもの** — 項目 5 の境界をそのまま適用した形です: 散文のみの生成モジュール
`schemas/_laminar_models.py` で、`MODEL_DOCS` 以外の文を 1 つも持ちません。`KeySchema` も
`SCHEMAS` も `TARGET_FILE` も無いので、レジストリがマージするものが存在せず、手書きキーを
上書きし得るものも存在しません。foamlore 側では、事実を実測した先のディレクトリで振り分けて
います（`facts/derived/laminar/` は散文専用）。したがって生成器の呼び出し方によって層流モデル
が係数を出力してしまうことはあり得ず、当該モジュールが `KeySchema` も `ChoiceItem` も名前に
含まないことをガードテストが表明しています。

FoDE 側では、`_LAMINAR_MODELS` の 5 つの素の `ChoiceItem` を RAS/LES セレクタと同じ
`_model(...)` 呼び出しに置き換え、`fallback` の説明文を削除しました。`_model()` には省略可能な
`note`/`deprecated_since` を追加し、2 つの generali[sz]edNewtonian エントリが FoDE 自身の
フォーク分岐の但し書きを保てるようにしています — これは上流の注記を置き換えるのではなく
*追記*します。フォーク 2 つの関係についての事実であり、どちらのヘッダにも書かれていないから
です。`supported_in` タグはすべて変更していません。あれは FoDE の実測であり、
`test_laminar_models_match_the_measured_table` はいまもモジュールとは独立に書かれた表と
突き合わせています。`test_no_laminar_model_is_covered_by_foamlore` は
`test_every_laminar_model_is_covered_by_foamlore` になりました — 同じ仕掛けを逆向きに読み、
加えて 2 つの散文テーブルが互いに素であることを表明します。さらに
`test_laminar_notes_cite_only_where_upstream_does` を追加し、7 つのうち `Reference:` 注記を
持つ 4 つ（`Maxwell`・`Giesekus`・`PTT`・`lambdaThixotropic`）と、持ってはならない 3 つ
（`Stokes` と generali[sz]edNewtonian の両綴り）を固定しました。ヘッダが論文を引用していない
クラスに対して論文を創作することはできません。

1 つだけ知っておく価値のある傷: `lambdaThixotropic` の Description は、生成モジュール全体で
唯一 Doxygen の数式マークアップが残っている引用文字列です — 「…the structural parameter
\f$ \lambda \f$:」と表示されます。foamlore の `demarkup()` は意図的に狭く作られており
（`\c` と verbatim フェンスのみ）、未対応のディレクティブは黙って壊されるのではなく目に見える
形で残ります。これを広げるのはこの配線の変更ではなくストア全体の再抽出になります。

抽出から得られた知見が 3 つ、`turbulence_structure.py` の層流エントリに再び触れる前に知って
おく価値があります — 詳細は foamlore の `fode-schemas/SPEC_RESPONSE.md` の「12 (yours)」節に
あります。

- **`modes` は Foundation 14 で構文上のカテゴリが変わります** — v13 まではリスト、v14 からは
  辞書 — そして v13 形式は v14 で黙って無視されるのではなく致命的エラーになります（項目 13 の
  出荷監査時点、2026-09-04 で、FoDE の `modes` の説明文に既に反映済みです）。
- **`nuM` は Foundation 14 でモードごとになります**: `modes` がある場合、各モードのサブ辞書が
  自身の `nuM` を持つ必要があり、トップレベルのフラットな `nuM` は*警告付きで無視*されます
  （エラーではありません）。
- **このファミリーのどのキーも `getOrDefault`/`lookupOrDefault` を使っていません** — 例外は
  `sigmay`(既定値 0、`found("sigmay")` で保護)、`residualAlpha`(既定値 `1e-6`)、`modes`
  自身のみです。他の層流キーが `default=` を持っていたら、それは誤りです。


## 13. 入れ子の generalizedNewtonian/generalisedNewtonian 粘性モデル — 実測済みだった。配線方式に FoDE 側が答えていなかった(2026-09-04 提起・同日訂正)

項目 12 の姉妹タスク — 層流応力モデル自身の係数辞書 — を仕上げる過程で見つかりました。
`laminar { model generalizedNewtonian; }`（または `generalisedNewtonian`）はさらに入れ子の
`viscosityModel` セレクタを読み、その 6 つの共有選択肢（`BirdCarreau`・`Casson`・
`CrossPowerLaw`・`HerschelBulkley`・`powerLaw`・`strainRateFunction`、加えて Foundation
専用の `Newtonian`）は現在 FoDE が正しく提示しています。問題はそれぞれの係数のほうです。

### この節が訂正する誤り

ある実装の過程で、この 6 クラスは `constant/transportProperties` が既に持つ同名の
`viscosityModel` セレクタ（`_transport.py`）と*同一*だと想定してしまいました — 名前も
系統も同じなのだから係数も同じはずで、既存スキーマを指せば済む、という考えです。この
想定はコミットメッセージ、コードコメント 3 箇所、RELEASE_NOTES の 2 項目にまで載った後、
レビューで見つかりました。

これは独立した 2 つの理由で誤りです。

1. **レジストリはファイル単位です。** `_transport.py` は
   `TARGET_FILES = ("transportProperties", "physicalProperties")` を宣言しており、
   そこに登録されたものは `constant/turbulenceProperties` や
   `constant/momentumTransport` からは、キー名が一致していようと決して届きません。
   つまりこの「再利用」はそもそも解決すらせず — 誤情報の漏洩ではなく単なる欠落ですが、
   「既に説明済み」という主張とも違います。
2. **たとえ解決したとしても、6 つのうち 3 つでは誤りです。** これらは異なるソース
   ディレクトリ下で独立に実装された C++ クラスであり、1 つのクラスを 2 つのファイルから
   読んでいるのではなく、6 つのうち 3 つは `transportProperties` の同名クラスと係数集合を
   共有していません — 残る 2 つは実は同一だったと、下で訂正します。

   | モデル | transportProperties(旧) | OpenCFD 入れ子 | Foundation 入れ子 |
   |---|---|---|---|
   | `BirdCarreau` | `nu0, nuInf, k, n, a` | `nuInf, k, n, a`（`nu0` 無し） | `nuInf, k, tauStar, n, a`（OpenCFD に無い 5 つめ） |
   | `HerschelBulkley` | — | `n, tau0` | `n, tau0, k`（Foundation は `k` を追加） |
   | `powerLaw` | — | `n, nuMin, nuMax` | `k, n, nuMin, nuMax`（Foundation は `k` を追加） |
   | `Casson` | — | `m, tau0, nuMin, nuMax` | `m, tau0, nuMin, nuMax` — **同一** |
   | `CrossPowerLaw` | — | `nuInf, m, n, tauStar` | `nuInf, m, tauStar, n` — **同一** |

   **訂正(2026-09-04):** この表はもともと、`HerschelBulkley` は `tau0` を `k` に
   置き換える、`Casson` は Foundation で `tau0` を落とす、と主張していましたが両方とも
   誤りでした。原因は手作業の grep（`grep -n "dimensionedScalar [a-zA-Z]*_;"`）で、
   その文字クラスが数字を含む識別子を暗黙に除外しており、`tau0_` を見落としていました。
   実際には Foundation の `HerschelBulkley` は共有される `n, tau0` に加えて `k` を
   *追加*しており、`Casson` は両フォークで同一です。ソースへ直接当たり直すのではなく、
   出荷済みのベンダリング済みスキーマ（もう一度 grep するのではなくレジストリへの照会）
   に対して再検証しました — foamlore 自身の抽出にこのバグはなく、この文書の根拠表に
   だけありました。`BirdCarreau`・`HerschelBulkley`・`powerLaw` はそれでも食い違って
   おり、それだけで元の「`transportProperties` を再利用する」という主張を誤りにするには
   十分です。そのスキーマを入れ子クラスに再利用していたら、両フォークの momentumTransport
   側入れ子クラスのどちらも実際には読んでいない `nu0` を、正当な `BirdCarreau` の係数
   として報告していたことになります —
   項目 12 自身の報告が `lambdaThixotropic`/`CrossPowerLaw` について捉えたのと同じ種類の
   不具合を、別の軸で。

共有名から推測せず、ソースを直接測定しました（`.H` のメンバ一覧と、各名前を coeffDict
から取り出す `.C` のコンストラクタ/`read()` 呼び出し）。現時点で確認したのは OpenCFD
v2606 と Foundation-14 のみです。食い違い自体は実在しますが、*正確な*リリース範囲
（Maxwell/Giesekus/PTT が Foundation v8 でマルチモード対応を得たときのように、実測範囲
内でこれらの係数の形が変わった箇所があるか）は 19 チェックアウト全体でまだ走査して
いません。

### 訂正: そもそも依頼する必要はなかった — foamlore 側では既に着地していた

上の各段落は事実ストアの拡張が必要だという前提で書きましたが、その前提自体が誤りです。
foamlore リポジトリの `facts/store/generalisedNewtonian/` には既に 119 個の派生 JSON が
あります — 6 つの共有クラス（`BirdCarreau`・`Casson`・`CrossPowerLaw`・`HerschelBulkley`・
`powerLaw`・`strainRateFunction`）× 最大 19 チェックアウト分で、`facts/tools/families.py`
にそれ自身の `Family` として登録済みです。`facts/tools/generate_transport_schemas.py`
にも生成器が既に用意されています。2 つの `Target` 行がコメントアウトされたまま
置かれています。

```python
# Target("momentumTransport", "momentum_transport_viscosity",
#        "generalisedNewtonian", tuple(f"foundation-{n}" for n in range(8, 15))),
# Target("turbulenceProperties", "turbulence_properties_viscosity",
#        "generalisedNewtonian", OPENCFD_ALL + ("foundation-7",)),
```

foamlore はこれを 2026-08-15 に、*先方の* `fode-schemas/SPEC_RESPONSE.md` 項目 12 で
既に提起していました（この文書の項目番号とは独立の採番で、たまたま一致しただけです）。
「回答待ちで何もブロックされていません。……どちらを選んでも表 1 行と再生成だけで済み、
再導出は不要です。」として、FoDE に 3 つの配線方式（上記のようなファイルごとの薄い
モジュールを追加する方式、`_build_file_key_schemas` にキー単位の対象フィルタを入れる
方式、乱流生成器の出力に畳み込む方式）を示し、選択を委ねていました。これは FoDE 自身の
レジストリに関する問いだからです。FoDE 側は誰も答えていませんでした — その結果、この
文書は foamlore が既に測定済みだった食い違い表を独自に再導出し、「未配線」を「未実測」と
取り違えることになりました。

**決定(2026-09-04): 最初の方式にします。** 既存の `turbulence_properties.py`/
`momentum_transport.py` パターンにそのまま倣う、ファイルごとの薄いモジュールを追加する
方式です — 最も安価で、foamlore 側も既にこの方式向けのモジュール名を用意していました。
実測されたキー集合は今のところ重なっていません（`nu0`・`nuInf`・`tauStar`・`k`・`m`・`n`・
`nuMin`・`nuMax`・`tau0`・`function` と、乱流係数側）。まだ起きてもいない衝突に備えて
重いキー単位フィルタを今作り込むのではなく、同じ `TARGET_FILE` に登録される他モジュールと
この 2 モジュールのキー集合が重ならないことをテストで固定します。実際に衝突が起きれば
生成チェックの時点で大きな音を立てて失敗するようにし、より重い修正はその時点でも選べる
ままにしておきます。

**foamlore 側に残る作業は、これだけです。** 上記の 2 つの `Target` 行のコメントを外して
再生成し、`momentum_transport_viscosity.py` / `turbulence_properties_viscosity.py` を
`turbulence_properties.py`/`momentum_transport.py` と同じ要領で FoDE の `schemas/` へ
ベンダリングしてください。`strainRateFunction` は固定の係数集合ではなく入れ子の
`Function1<scalar>` を読むため、この生成パスでは別扱いが必要かもしれません — ここでは
指摘のみ残し、解決はしていません。

### 出荷済み(2026-09-04): 「コメントを外して再生成」だけでは済まなかった内容

foamlore は文字どおりの依頼のままでは実行しませんでした。「2 つの `Target` 行の
コメントを外すだけ」を文字どおり実行していたら、3 通りの誤ったスキーマが出荷されて
いたはずで、いずれもベンダリング前に見つかりました。

1. **ファミリーごとに 1 つの共有モジュールにすべきで、全体で 1 つではない。**
   `_MODELS`/`_COEFFS` は素のモデル名でキー付けされており、両ファミリーを 1 つの
   モジュールに流し込むと係数が和集合になります。そのため `BirdCarreauCoeffs` は
   すべての対象ファイルで `nu0`(旧実装のみ)と `tauStar`(Foundation の入れ子のみ)
   の両方を抱えることになっていたはずです — まさにこの項目が説明している不具合が、
   生成側から到達していたということです。ファミリーごとに共有する
   `_generalised_newtonian.py` を設けて修正しました。ストアが既にこのファミリーを
   名前空間分けしていたのと同じ理由です。生成モジュールは今や 9 つで、6 つでは
   ありません。
2. **パーサのバグが 3 リリースで必須キーを落としていました。** Foundation 12 が
   `Function1<scalar>::New(...)` に次元引数を追加したため、位置ベースのパーサが
   誤読し、`strainRateFunction` の `function` キーが foundation-12/13/14 で黙って
   落ちていました。出荷していれば `supported_in=('Foundation v8-v11',)` となり、
   実際にはそのキーを必要とするリリースで「利用不可」と伝えていたはずです。修正
   済みで、レジストリ照会により `Foundation v8-v14` であることを確認しています。
3. **`container_of` が Foundation 14 のアクセサを知りませんでした。** そのため
   Foundation 14 の入れ子モデルはすべてコンテナが空として記録され、フラット書式
   にしか応答しないところでした。出力に到達しなかったのは、生成器がコンテナ名を
   対象チェックアウトのうち並び順で最後のものから採っており、たまたま OpenCFD の
   チェックアウトが最後に来ていたからにすぎません。

**そして FoDE 自身の「キー集合は今のところ重ならない」という決定も完全には正しく
ありませんでした。** 上の重複防止テストはこれを捕まえるためのものでしたが、衝突の
方が先に着地していました。`viscosityModel` そのものが衝突していたのです —
`turbulence_structure.py` が手書きしており、生成器は後から読み込まれるため、黙って
上書きしていたはずです。foamlore は FoDE の手書きエントリを上書きさせる代わりに、
生成器側でこの 1 キーだけ出力を止めました(`Target.emit_selector` /
`_transport.py` の `_SELECTOR_FILES`)。レジストリ照会で確認済みです。
`viscosityModel` は両方の対象ファイルで、今も手書きの 7 選択肢のエントリに解決
します。

実測された知見が 2 件、適用はされず報告のみに留まっていましたが、今回解決しました。

- **`Newtonian` のタグが 3 リリース分過大申告していました。** `FOUNDATION_SERIES`
  (v7-v14)とタグ付けされていましたが、入れ子の `Newtonian` クラスは foundation-10
  で初めて登録されます(foundation-7/8/9 のディレクトリ一覧で不在を確認済み)。
  `FOUNDATION_V10_V14` に修正しました。
- **`viscosityModel` の `supported_in=BOTH` は、Foundation の各バージョンが実際に
  どちらのファイルから読んでいるかを区別しません**(`turbulenceProperties` は v7 の
  みで、v8 以降は `momentumTransport`)。これはそのままにしています。この共有
  モジュール内の他のすべてのエントリが同じ粗さを持っているためです — `RAS.model`
  の選択肢も同じ粗いタグ付けです。このキーだけを狭めるのは修正ではなく不整合に
  なります。1 つのテーブルが両方のファイルに仕えるというこのモジュールのアーキ
  テクチャ上、そういうものだからです。

出荷内容を監査する過程でもう 1 つ修正しました。`modes` は Foundation 14 で構文上の
カテゴリが変わります(v13 まではリスト、v14 からは辞書)。旧形式は黙って無視される
のではなく、そこでは致命的エラーになります(`subOrEmptyDict` が、実際にはプリミ
ティブ(リスト)エントリであるものに対して `entry::dict()` を呼び出すため)。FoDE
の `modes` の説明文は今やそのことを述べています。以前はリスト形式しか説明して
いませんでした。

`turbulence_structure.py` の `viscosityModel` エントリは、6 つの選択肢名を示す
*だけでなく*、それぞれの係数も解決するようになりました — この手書きモジュールから
ではなく、姉妹にあたる生成済みの `turbulence_properties_viscosity.py` /
`momentum_transport_viscosity.py` からです。理由の全文は、その `KeySchema` の上の
コードコメントと `DEVELOPER.md` の対応する段落を参照してください。
