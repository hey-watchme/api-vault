# WatchMe Vault API

WatchMe プロジェクト用のファイル受け渡しAPIです。

音声データ（WAV）と各種解析結果（JSON）をユーザー・日付単位で管理し、iOSアプリ・Streamlit・Webダッシュボード間のデータ授受を安全に行います。

## プロジェクト構造

```
vault/
├── watchme_api/          # FastAPIアプリケーション
│   ├── app.py           # メインAPIサーバー
│   └── requirements.txt # 依存関係
├── data/                # ローカル開発用データ（.gitignoreで除外）
│   └── data_accounts/   # 実際のデータ構造をミラー
├── .gitignore          # Git除外設定
├── LOCAL_DEV.md        # ローカル開発ガイド
└── README.md           # このファイル
```

## 本番環境での起動

サーバー上（本番環境）では従来通り：

```bash
cd watchme_api
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## ローカル開発環境での起動

⚠️ **重要**: 本番環境を保護するため、ローカル開発時は必ず環境変数を設定してください。

```bash
cd watchme_api

# 依存関係のインストール（初回のみ）
pip install -r requirements.txt

# ローカル開発モードで起動
WATCHME_LOCAL_DEV=1 uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

詳細は [LOCAL_DEV.md](LOCAL_DEV.md) を参照してください。

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

## 開発ガイド

- **本番環境への影響を避けるため**: 必ず [LOCAL_DEV.md](LOCAL_DEV.md) を確認してください
- **コード変更時**: app.py の修正は本番環境で稼働中のため慎重に行ってください
- **requirements.txt**: サーバーの全パッケージリストのため変更不要です