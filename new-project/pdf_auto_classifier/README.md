# PDF Auto Classifier

社内AI ツール - 監視フォルダ PDF 自動分類／リネーム・移動システム

## 概要

このシステムは、共有フォルダに保存されるPDFファイルを自動的に監視し、注文書（Purchase Order）を識別してリネーム・分類する自動化ツールです。

## 主な機能

- **フォルダ監視**: watchdogを使用してリアルタイムでPDFファイルを監視
- **PDF内容抽出**: pdfplumberとOCRを使用してテキストを抽出
- **注文書判定**: キーワードマッチングによる高精度な注文書判定
- **メタデータ抽出**: 日付、会社名、注文番号の自動抽出
- **自動リネーム**: `YYYYMMDD_会社名_注文番号.pdf` 形式でリネーム
- **ファイル移動**: 成功時は Orders フォルダ、失敗時は Error フォルダへ移動
- **ログ出力**: 詳細なログ出力と JSON 形式での記録
- **アラート通知**: Teams Webhook を使用したエラー通知

## システム構成

```
pdf_auto_classifier/
├── src/
│   ├── main.py              # メインアプリケーション
│   ├── pdf_processor.py     # PDF処理・内容抽出
│   ├── file_manager.py      # ファイル管理・移動
│   └── alert_manager.py     # アラート通知
├── config/
│   └── config.yaml          # 設定ファイル
├── tests/                   # テストコード
├── logs/                    # ログファイル
├── docker/                  # Docker関連
├── requirements.txt         # Python依存関係
├── Dockerfile              # Docker設定
└── docker-compose.yml      # Docker Compose設定
```

## 必要な環境

- Python 3.12+
- Docker & Docker Compose
- Tesseract OCR (日本語言語パック)
- 共有フォルダへのアクセス権限

## セットアップ

### 1. 設定ファイルの編集

`config/config.yaml` を編集し、以下を設定：

```yaml
folders:
  input: "/path/to/input"      # 監視フォルダ
  output: "/path/to/output"    # 出力フォルダ
  error: "/path/to/error"      # エラーフォルダ

alerts:
  teams_webhook_url: "https://your-teams-webhook-url"
```

### 2. Docker コンテナの起動

```bash
# ビルドと起動
docker-compose up -d

# ログの確認
docker-compose logs -f pdf-classifier
```

### 3. ローカル実行（開発用）

```bash
# 依存関係のインストール
pip install -r requirements.txt

# アプリケーションの実行
python src/main.py
```

## 設定項目

### 注文書判定

- `po_detection.keywords`: 判定に使用するキーワード
- `po_detection.confidence_threshold`: 判定の信頼度閾値

### メタデータ抽出

- `metadata_extraction.date_patterns`: 日付抽出の正規表現
- `metadata_extraction.order_number_patterns`: 注文番号抽出の正規表現
- `metadata_extraction.company_patterns`: 会社名抽出の正規表現

### 処理制限

- `processing.max_file_size_mb`: 最大ファイルサイズ（MB）
- `processing.max_pages`: 最大ページ数
- `processing.timeout_seconds`: 処理タイムアウト

## テスト

```bash
# 単体テストの実行
python -m pytest tests/ -v

# 特定のテストファイルの実行
python -m pytest tests/test_pdf_processor.py -v
```

## ログ

システムのログは以下の場所に保存されます：

- `logs/app.log`: アプリケーションログ
- `error/`: エラーファイルとエラーログ

## 監視・運用

### システムの状態確認

```bash
# コンテナの状態確認
docker-compose ps

# ログの確認
docker-compose logs pdf-classifier

# リアルタイムログ監視
docker-compose logs -f pdf-classifier
```

### パフォーマンス指標

- 処理時間: 1ファイルあたり平均5秒以下
- 判定精度: 98%以上
- 処理能力: 200件/時間

## トラブルシューティング

### よくある問題

1. **OCR が動作しない**
   - Tesseract がインストールされているか確認
   - 日本語言語パックがインストールされているか確認

2. **ファイルアクセスエラー**
   - 共有フォルダへのアクセス権限を確認
   - ファイルがロックされていないか確認

3. **メタデータ抽出が失敗する**
   - 正規表現パターンが適切か確認
   - PDFの形式が想定と異なる場合は設定を調整

### デバッグ

```bash
# デバッグモードでの実行
LOG_LEVEL=DEBUG docker-compose up

# 特定のファイルでのテスト
python -c "from src.pdf_processor import PDFProcessor; processor = PDFProcessor(config); print(processor.extract_text_from_pdf('test.pdf'))"
```

## セキュリティ

- ファイルI/Oは適切な権限で実行
- ログに個人情報は平文で出力しない
- 処理済みファイルは安全に移動

## ライセンス

社内利用のみ

## 更新履歴

- v1.0.0: 初回リリース
  - 基本機能の実装
  - Docker化
  - テスト追加