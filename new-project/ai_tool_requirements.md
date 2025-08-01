# 社内 AI ツール要件定義書  
### 監視フォルダ PDF 自動分類／リネーム・移動システム  
（版数 1.0 作成日 2025‑07‑11）

---

## 1. 目的・背景  
- **目的**  
  手作業で行っている 「PDF 注文書の確認 → リネーム → 所定フォルダへのドラッグ＆ドロップ」 を自動化し、月間 10 時間以上の工数削減とヒューマンエラーの撲滅を図る。  
- **背景**  
  * 共有サーバーの `\\filesvr\Incoming\` に各部署／取引先から PDF が随時出力される  
  * 購買部門では注文書を抽出し、命名規則 `YYYYMMDD_会社名_注文番号.pdf` で `\\filesvr\Orders\` へ移動する運用  
  * ファイル増加と担当者交代によりミスが顕在化

---

## 2. スコープ  
| 区分 | 内容 |
|------|------|
| **対象内** | PDF の購入注文書判定、メタデータ抽出、リネーム、フォルダ移動、ログ・アラート |
| **対象外** | 見積書・納品書の処理、ERP 連携、ファイル内容の変更、紙書類のスキャン |

---

## 3. 用語定義  
| 用語 | 定義 |
|------|------|
| **監視フォルダ** | PDF が出力される共有フォルダ (`\\filesvr\Incoming\`) |
| **出力フォルダ** | 処理済み注文書を格納するフォルダ (`\\filesvr\Orders\`) |
| **PO (Purchase Order)** | 当社が発行または受領する「注文書」 |
| **OCR** | 画像 PDF から文字を抽出する光学文字認識 |

---

## 4. 現状業務フロー（AS‑IS）  
1. PDF を視認  
2. 注文書か判断  
3. ファイルをリネーム  
4. `Orders` フォルダへ移動  
5. エクセル台帳へ転記  
→ **課題**: 判定ミス・重複ファイル・リネーム漏れ

---

## 5. 新業務フロー（TO‑BE 概要）  

```
PDF 出力
   │
   ▼ (自動)
File Watcher → Content Extractor → PO 判定 → メタデータ抽出 → リネーム → Orders へ移動
                                                  │
                                                  └→ ログ／アラート
```

---

## 6. 5W1H 仕様  

| 項目 | 要件 |
|------|-----|
| **Who** | 情シス部門がシステム運用、購買部門が利用・受益 |
| **What** | PO 判定し、`YYYYMMDD_会社名_注文番号.pdf` にリネームして移動 |
| **When** | PDF 生成後 30 秒以内に処理完了 |
| **Where** | 監視フォルダ＝`\\filesvr\Incoming\`<br>出力フォルダ＝`\\filesvr\Orders\` |
| **Why** | 手作業削減・ミス防止・監査証跡確保 |
| **How** | Python サービス（watchdog＋pdfplumber／OCR）を Docker コンテナで常駐 |

---

## 7. 機能要件  

| 番号 | 機能名 | 詳細要件 |
|------|--------|---------|
| F‑1 | フォルダ監視 | サブフォルダを含まず PDF の新規作成イベントを検知 |
| F‑2 | 内容抽出 | テキストレイヤ有無を判定し、<br>有：`pdfplumber` / 無：`pytesseract`＋`pdf2image` で OCR |
| F‑3 | PO 判定 | ①正規表現キーワード（注文書／PURCHASE ORDER 等）、<br>②タイトル行・ロゴ配置をルール化し命中率 ≧ 98 % |
| F‑4 | メタデータ抽出 | 注文番号・発注日・会社名を正規表現または表認識で取得 |
| F‑5 | リネーム処理 | `YYYYMMDD_会社名_注文番号.pdf`<br>重複時 `_v2`, `_v3` … と連番 |
| F‑6 | 移動処理 | 成功時 `\\filesvr\Orders\` へ移動、失敗時 `\\filesvr\Error\` へ |
| F‑7 | ログ出力 | ファイル名・判定結果・処理時間・例外を JSON/CSV で保存 |
| F‑8 | アラート通知 | 例外・エラー時に Teams Webhook へメッセージ |

---

## 8. 非機能要件  

| 区分 | 要件 |
|------|------|
| **性能** | 1 ファイル当たり平均処理時間 ≤ 5 秒、ピーク 200 件/時を捌ける |
| **可用性** | 稼働率 99.5 %／月、サービス停止時は自動再起動 |
| **拡張性** | 取引先レイアウト追加を設定ファイルで吸収（再デプロイ不要） |
| **セキュリティ** | ファイル I/O は AD 認証経由、ログに個人情報を平文出力しない |
| **保守性** | コード・設定を Git 管理、Docker イメージ化、3 行以内で環境再構築可能 |
| **監査** | 1 年間のログ保管、検索 UI でトレーサビリティ確保 |

---

## 9. システム構成  

| レイヤ | 構成要素 | 備考 |
|--------|----------|------|
| アプリ | Python 3.12 アプリ（watchdog, pdfplumber, pytesseract, loguru） | 仮想環境内 |
| コンテナ | Docker コンテナ | systemd で自動再起動 |
| サーバ | Windows Server 2022（ファイルサーバ共有上） | CPU 4 vCore, RAM 8 GB |
| ネットワーク | 社内 LAN | 帯域要件なし（PDF 数 MB 程度） |

---

## 10. インタフェース仕様  

| IF‑ID | 方向 | 相手 | 方式 | データ項目 |
|-------|------|------|------|-----------|
| IF‑1 | IN | ファイルサーバ (Incoming) | SMB | PDF バイナリ |
| IF‑2 | OUT | ファイルサーバ (Orders/Error) | SMB | リネーム後 PDF |
| IF‑3 | OUT | Teams | HTTPS Webhook | JSON (エラーメッセージ) |
| IF‑4 | OUT | ログストレージ | ファイル I/O | JSON/CSV ログ |

---

## 11. 制約条件・前提  

1. 監視対象 PDF は A4 以内・最大 5 ページ  
2. 注文番号は半角英数字 50 文字以内  
3. OCR 用 Tesseract は日本語言語パックを導入済み  
4. ファイルサーバ共有は 24 h 稼働し、十分な空き容量があること

---

## 12. テスト計画（抜粋）  

| テスト | 内容 | 合格基準 |
|--------|------|----------|
| 単体 | 各関数の入出力検証 | 期待値完全一致 |
| 結合 | F‑1〜F‑6 連携 | 100 件投入で成功率 100 % |
| 性能 | 200 件/時 × 1 時間 | 失敗 0、平均 5 秒以内 |
| 障害 | 共有フォルダ切断・復旧 | 自動再接続、処理継続 |
| UAT | 実データ 1 週間分 | 購買部門承認 |

---

## 13. 移行／リリース計画  

| 週次 | 作業 | 担当 |
|------|------|------|
| W1 | 要件定義レビュー・承認 | 情シス／購買 |
| W2‑3 | プロトタイプ実装 | 開発 |
| W4 | 社内 PoC & 改修 | 開発＋購買 |
| W5‑6 | 本番機構築・自動テスト | 情シス |
| W7 | UAT | 購買 |
| W8 | 本番リリース | 情シス |
| W9 | 運用安定化／振り返り | 全体 |

---

## 14. 受入基準  

1. テスト計画に記載の全ケースを合格  
2. UAT で購買部門の承認を取得  
3. 業務マニュアル・運用手順書を提出  
4. 本番稼働後 2 週間で重大障害 0 件

---

## 15. リスクと対策  

| リスク | 影響 | 対策 |
|--------|------|------|
| レイアウト追加 | 誤判定増加 | 判定ロジックを外部 YAML で設定化 |
| OCR 精度不足 | 注文番号誤抽出 | 90 % 未満は要確認フォルダへ振り分け |
| サーバ障害 | 処理停止 | 冗長構成は不要だがバックアップ手順を整備 |

---

## 16. 添付資料  
- 業務フロー図（PDF）  
- 命名規則一覧（Excel）  
- ログ項目定義書（Markdown）

---

*以上、要件定義書として承認をお願いいたします。  
書式ミスを見つけても怒りのドラッグ＆ドロップはご容赦を。* 😌
