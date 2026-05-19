---
title: "GPU貸出とクラウド連携でCoreWeaveが狙う供給網の再編理由"
source: "CoreWeave Blog"
source_url: "https://wf.coreweave.com/blog/coreweave-announces-new-capabilities-to-simplify-cross-cloud-ai"
source_type: "official_blog"
source_label: "一次情報"
is_primary_source: true
source_authority: 15.5
category: "インフラ"
category_slug: "infrastructure"
article_slug: "coreweave-cross-cloud-ai-capabilities"
published_at: "2026-05-19"
source_published_at: "Mon, 11 May 2026 20:30:50 GMT"
buzz_score: 61.0
image_url: "https://cdn.prod.website-files.com/62bc66d283fd9c34ffec780a/69e82fee493c984fe03163c8_Flex%20capacity%20Technical%20blog_META_1200x630.jpg"
description: "CoreWeaveとGoogle Cloudの専用線接続により、逼迫するGPU調達の選択肢を広げ、分散リソースを一体的に扱えるクロスクラウド環境を実現する狙いを解説。"
meta_description: "CoreWeaveとGoogle Cloudの専用線接続により、逼迫するGPU調達の選択肢を広げ、分散リソースを一体的に扱えるクロスクラウド環境を実現する狙いを解説。"
topics_json: ["amazon", "datacenter", "google", "gpu", "microsoft", "nvidia", "reasoning"]
companies_json: ["google", "microsoft", "nec", "nvidia"]
summaryPoints: ["単一クラウドのGPU逼迫を受け、特化型事業者とハイパースケーラーの接続が供給網の再編を促す局面である。", "ジョブ移送による学習アービトラージが実用化されれば、AI開発のコスト構造そのものが変化する可能性がある。", "日本企業にとって、地理的制約を緩和し海外GPUを柔軟に活用できる分岐点になり得る動きである。"]
---


CoreWeaveがGoogle Cloudとの接続サービス「CoreWeave Interconnect」を発表した。両社間の専用線でAIワークロードを統合し、分散したGPUリソースを一体的に扱えるようにする。AI開発者がクラウドをまたいで学習と推論を実行できる環境を提供し、供給逼迫が続くGPU調達の選択肢を広げる点で重要だ。発表には学習ジョブの移送を簡略化する「SUNK Anywhere」と、推論を分散配置する「LOTA Cross-Cloud」の2機能が含まれる。

## なぜクラウド間接続が課題だったのか
大規模なAI学習には数千基のGPUを同時に確保する必要がある。ところが単一クラウドでは需要が集中し、特にNVIDIA H100や次世代B200といった先端GPUの調達待ちが数カ月に及ぶケースが常態化している。CoreWeaveはNVIDIAから優先的にGPUを調達できる立場を生かし、自社データセンターの余剰リソースを他クラウドの顧客へ融通する仕組みを以前から模索していた。Google Cloud側もAIワークロードの獲得競争で差別化要素を必要としており、両社の利害が一致した形だ。従来のマルチクラウドはデータ転送の遅延やAPIの非互換に悩まされてきたが、今回の相互接続は専用線と共通スケジューラでその障害を取り除く設計になっている。

## 供給網に見るCoreWeaveの立ち位置
AIインフラの供給層は大別して、GPU製造のNVIDIA、クラウド基盤のAWS・Google Cloud・Microsoft Azure、そしてGPU特化型プロバイダのCoreWeaveやLambda Labsが並ぶ。CoreWeaveはNVIDIAとの強い調達パイプを背景に、約45,000基のH100相当を運用していると推定され、2024年末までにさらに拡張する計画を公表している。今回のInterconnectは、このGPU在庫をGoogle Cloudの顧客基盤に直結させる意味を持つ。Google Cloudの顧客はVertex AIなどのマネージドサービスからCoreWeaveのベアメタルGPUを呼び出せるようになり、オンプレミスに近い低遅延で学習パイプラインを組める。APIレベルではKubernetesベースのオーケストレーションが両環境を抽象化し、開発者がインフラの境界を意識せずにジョブを投入できる設計だ。

## クロスクラウドが変えるモデル開発と推論経済
SUNK Anywhereは、学習ジョブのチェックポイントを圧縮・転送し、中断した処理を別クラウドで再開する仕組みである。これにより、スポット価格の安いリソースを動的に渡り歩く「学習アービトラージ」が実用的になる。アナリスト予測では、大規模言語モデルの学習コストのうちGPU使用料が6割を占めるため、ジョブ移送で価格差を利用できれば総コストを15〜20％圧縮できる可能性がある。一方のLOTA Cross-Cloudは推論ワークロードを地理分散させる機能で、エンドユーザーに近いPOP（接続拠点）へモデルを配置し応答遅延を低減する。推論需要が急増するエッジAIやリアルタイム翻訳サービスでは、単一リージョンよりクロスクラウド構成の方がレイテンシを40ミリ秒以上短縮できるケースが報告されており、サービス品質に直結する。

## 日本企業への波及と調達多様化
国内のAIスタートアップや事業会社にとって、GPU調達の選択肢は実質的に国内データセンターを持つ事業者か米大手クラウドの東京リージョンに限られてきた。今回の接続が日本向けに展開されれば、CoreWeaveの米国拠点GPUをGoogle Cloud経由で利用できるようになり、調達の地理的制約が緩む。円安で海外GPUの調達コストが上昇している局面でも、スポット価格の安い時間帯を狙ったジョブ移送が実用的になれば、為替影響を一部吸収できる可能性がある。もっとも、日米間の専用線遅延やデータ主権の課題は残り、金融・医療分野での利用には追加のコンプライアンス対応が必要になるだろう。

## 今後の論点はマルチクラウド標準化競争
CoreWeaveとGoogle Cloudの相互接続は、GPU特化型事業者がハイパースケーラーと対等に接続する先例となる。今後はMicrosoft AzureやAWSが同様の相互接続をGPUプロバイダと結ぶかが焦点で、事実上の標準APIを巡る競争が加速する。NVIDIAが提供するGPU仮想化レイヤー「NVIDIA AI Enterprise」との整合性や、IBM・Oracleといった後発クラウドの動きも絡み、AIインフラの相互運用性が業界構造を左右する局面に入った。一つの指標として、クロスクラウド接続を利用するAIワークロードの割合が2025年に全体の12％を超えるかどうかが、投資家やプラットフォーマーの判断材料になる。
