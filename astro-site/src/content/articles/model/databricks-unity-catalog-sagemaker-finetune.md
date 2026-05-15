---
title: "DatabricksとAWSが実現するLLM微調整の新基盤"
source: "AWS Machine Learning"
source_url: "https://aws.amazon.com/blogs/machine-learning/fine-tune-llm-with-databricks-unity-catalog-and-amazon-sagemaker-ai/"
category: "モデル"
category_slug: "model"
article_slug: "databricks-unity-catalog-sagemaker-finetune"
published_at: "2026-05-15"
buzz_score: 40.5
image_url: "https://d2908q01vomqb2.cloudfront.net/f1f836cb4ea6efb2a0b1b99f41ad8b103eff4b59/2026/05/13/ml-19973.png"
meta_description: "DatabricksとAWSは、Unity Catalogで管理するデータをSageMaker AIで安全に微調整する手法を確立した。EMR Serverlessを前処理に活用し、データの移動や権限継承の障壁を克服。一貫したリネージ追跡によ"
topics_json: ["amazon", "llm"]
companies_json: ["amazon", "databricks", "mistral"]
---


## ガバナンスを維持する分散処理の障壁
企業が大規模言語モデルを業務活用する際、最大の課題はデータの統制とセキュリティの両立である。Databricks の Unity Catalog で一元管理するデータを、Amazon SageMaker AI の持つ高性能な学習環境で微調整しようとすると、データの移動やアクセス権限の継承が大きな障壁となっていた。今回 Databricks と AWS が共同で示した手法は、Amazon EMR Serverless を前処理に活用し、この分断を克服する点に価値がある。

具体的には、Unity Catalog 上で厳格に管理された構造化・非構造化データに対し、SageMaker AI が安全にアクセスできる経路を確立した。この接続により、データの出所からモデル学習、そして成果物の登録に至るまで、一貫したリネージを断絶させずに追跡できる。金融や医療など、厳格なコンプライアンスが求められる業界にとって、監査証跡を残しつつ生成 AI の精度を高められる意義は大きい。

## 前処理に EMR Serverless を採用した理由
このワークフローの中核は、前処理エンジンとして Amazon EMR Serverless を採用した点にある。Unity Catalog 内の大規模データを SageMaker の学習ジョブに適した形式へ変換する際、サーバーレスアーキテクチャは動的な計算リソースの最適化を可能にする。従来の常時稼働クラスタと異なり、ペタバイト級のデータ処理でもアイドルリソースが発生せず、コスト効率と処理速度を両立する設計だ。

EMR Serverless は Apache Spark との親和性が高く、Unity Catalog 上の Delta Lake 形式データをネイティブに読み込める。これにより、認証情報を直接扱うことなく、一時クレデンシャルを用いた安全なデータアクセスが実現する。ガバナンスを司る Unity Catalog の権限設定が、データ移動後も完全に保持される点が、このアーキテクチャの核心である。

## Ministral-3-3B-Instruct 選定の意味
今回の実証で微調整対象に選ばれたのは、Mistral AI が開発した Ministral-3-3B-Instruct モデルだ。パラメータ数が約33億と比較的軽量でありながら、命令追従性能に優れるこのモデルは、エッジデバイスや特定業務への組み込みに適している。大規模基盤モデルに比べ、SageMaker AI 上での学習時間と推論コストを抑えつつ、専用データによるカスタマイズ効果を検証しやすい点が選定理由とみられる。

SageMaker AI の分散学習機能を用いて Ministral-3 を微調整し、生成されたモデルアーティファクトは再び Unity Catalog に登録される。一連の流れの中で、学習に用いたデータセットのバージョンからハイパーパラメータまで、すべての操作履歴が Databricks 側に自動記録される。日本企業が重視する内部統制の観点からも、この自動キャプチャ機能は汎用 AI サービスにはない強みとなる。

## 日本企業のデータ戦略にもたらす示唆
国内製造業や金融機関では、基幹系データをオンプレミスやプライベートクラウドに保持しつつ、AI 学習はパブリッククラウドのマネージドサービスで実行したいという需要が根強い。今回のリファレンスアーキテクチャは、データ主権を Unity Catalog で守りながら、SageMaker AI の計算資源を安全に呼び出すハイブリッド運用モデルを提示している。これは個人情報保護法や業界ガイドラインへの適合に苦慮する国内企業にとって、具体的な設計指針となり得る。

Databricks の調査によると、企業データの70%以上がいまだに AI 学習に活用されていない。この未活用データの壁を崩すには、部門や国をまたいだ統制と、俊敏な学習環境のバランスが欠かせない。Databricks と AWS が示した統合手法は、データを動かさずに価値だけを引き出す「コンピュート・トゥ・データ」の発想を、LLM 時代に再定義する布石と位置づけられる。両社はこのリファレンス実装を GitHub 上で公開し、企業の検証を促している。
