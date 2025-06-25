# WatchMe Vault API

WatchMe プロジェクト用のファイル受け渡しAPIです。

音声データ（WAV）と各種解析結果（JSON）をユーザー・日付単位で管理し、iOSアプリ・Streamlit・Webダッシュボード間のデータ授受を安全に行います。

## ⚠️ 重要な制限事項

**このローカル環境は「コード編集専用」です。以下の点にご注意ください：**

- 🎯 **目的**: app.pyのコード編集とバージョン管理のみ
- 🚫 **動作保証なし**: ローカルで動作しなくても問題ありません
- 🔒 **本番優先**: 本番環境の動作に影響を与えない構成を維持します
- ⚡ **カスタマイズ禁止**: ローカル環境の過度なカスタマイズは避けてください

## プロジェクト構造

### サーバー環境（本番）
```
/home/ubuntu/
├── watchme_api/          # このGitHubリポジトリ
│   ├── app.py           # メインAPIサーバー
│   ├── requirements.txt # 依存関係
│   ├── README.md        # このファイル
│   └── LOCAL_DEV.md     # ローカル開発ガイド
└── data/
    └── data_accounts/   # 実際のデータストレージ
```

### ローカル開発環境（コード編集用）
```
vault/                   # 開発用コンテナ
├── watchme_api/         # GitHubリポジトリ（このフォルダ）
│   ├── app.py          # 編集対象のコード
│   ├── requirements.txt # 本番と同じ依存関係
│   ├── README.md       # このファイル
│   └── LOCAL_DEV.md    # ローカル開発ガイド
└── data/               # ローカル開発用データ（Git管理外）
    └── data_accounts/  # データ構造のミラー
```

## 本番環境での起動

サーバー上（本番環境）でのみ実行してください：

```bash
# GitHubからクローン（初回のみ）
git clone git@github.com:matsumotokaya/watchme-vault-api.git watchme_api
cd watchme_api

# 依存関係のインストール
pip install -r requirements.txt

# アプリケーション起動
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## ローカル開発環境での作業

⚠️ **ローカル環境は動作確認目的ではありません。コード編集のみに使用してください。**

### コード編集のワークフロー

```bash
# 1. 最新コードを取得
cd vault/watchme_api
git pull origin main

# 2. app.py を編集
# （お好みのエディタでapp.pyを編集）

# 3. 変更をコミット・プッシュ
git add .
git commit -m "修正内容の説明"
git push origin main
```

### ローカル動作テスト（任意・非推奨）

動作テストは本番環境で行うことを強く推奨しますが、必要な場合のみ：

```bash
cd vault/watchme_api
WATCHME_LOCAL_DEV=1 uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**注意**: ローカルでエラーが発生しても、本番環境では正常動作する可能性があります。

## 主要エンドポイント

### アップロード系
- `POST /upload` - WAV音声ファイルアップロード
- `POST /upload-transcription` - 文字起こしJSONアップロード
- `POST /upload-prompt` - ChatGPTプロンプトJSONアップロード
- `POST /upload/analysis/emotion-timeline` - 感情タイムラインJSONアップロード
- `POST /upload/analysis/sed-timeline` - SEDタイムラインJSONアップロード
- `POST /upload/analysis/sed-summary` - SEDサマリーJSONアップロード

### ダウンロード・表示系
- `GET /download` - 個別WAVファイルダウンロード
- `GET /download-file` - ファイルパス指定ダウンロード
- `GET /view-file` - JSONファイル内容表示
- `GET /status` - HTML形式のファイル一覧表示

### API系（Webダッシュボード用）
- `GET /api/users/{user_id}/logs/{date}/sed-summary` - SEDサマリー取得

## データ構造

### 本番環境
```
/home/ubuntu/data/data_accounts/
├── user_id/
│   └── YYYY-MM-DD/
│       ├── raw/              # WAV音声ファイル
│       ├── transcriptions/   # 文字起こしJSON
│       ├── prompt/           # プロンプトJSON
│       ├── emotion-timeline/ # 感情タイムライン
│       ├── sed/              # SEDタイムライン
│       └── sed-summary/      # SEDサマリー
```

### ローカル開発環境（WATCHME_LOCAL_DEV=1時）
```
vault/data/data_accounts/
├── user_id/
│   └── YYYY-MM-DD/
│       ├── raw/              # WAV音声ファイル
│       ├── transcriptions/   # 文字起こしJSON
│       ├── prompt/           # プロンプトJSON
│       ├── emotion-timeline/ # 感情タイムライン
│       ├── sed/              # SEDタイムライン
│       └── sed-summary/      # SEDサマリー
```

## 機能と特徴

### セキュリティ
- 本番環境優先の安全な環境分離
- 環境変数による明示的な開発モード切り替え
- ローカル開発データの Git 除外

### 安定性
- 適切なエラーハンドリングとログ出力
- ファイルサイズ制限（WAV: 100MB、JSON: 10MB）
- JSON形式の検証
- 日付形式の検証
- HTMLエスケープ処理
- 包括的な例外処理

### 利用者別用途

#### 🔹 iOS録音アプリ
- 音声ファイル（WAV）の送信：`POST /upload`

#### 🔹 Streamlitアプリ（音声解析・PoC）
- Whisper文字起こしJSONの送信：`POST /upload-transcription`
- ChatGPT用プロンプト送信：`POST /upload-prompt`
- SEDタイムライン/サマリーJSON送信：`POST /upload/analysis/sed-*`
- 各種JSONやWAVの表示・取得：`GET /view-file`, `GET /download-file`

#### 🔹 Web版ダッシュボード（React + Vite + Tailwind）
- 感情グラフの取得：`GET /api/users/{user_id}/logs/{date}/emotion-timeline`
- 行動グラフ（SEDサマリー）の取得：`GET /api/users/{user_id}/logs/{date}/sed-summary`

## 🚨 開発時の重要な注意事項

### 本番環境保護のためのルール

1. **コード変更は慎重に**: app.py の修正は本番環境で稼働中です
2. **requirements.txt**: 本番環境の依存関係のため、むやみに変更しないでください  
3. **テスト**: 重要な変更は本番環境でのテストを推奨します
4. **ローカル環境のカスタマイズ**: データ構造やパス設定の変更は禁止です

### 緊急時の対応

本番環境で問題が発生した場合：
1. 即座にGitで前のバージョンに戻す
2. サーバー上で `git pull` して修正を適用
3. ローカル環境での動作確認は補助的な目的のみ

### 推奨ワークフロー

```bash
# 開発時
cd vault/watchme_api
git pull            # 最新取得
# app.py編集
git add app.py
git commit -m "説明"
git push

# 本番反映（サーバー上で）
cd /home/ubuntu/watchme_api
git pull
# 必要に応じてサービス再起動
```

詳細は [LOCAL_DEV.md](LOCAL_DEV.md) を参照してください。