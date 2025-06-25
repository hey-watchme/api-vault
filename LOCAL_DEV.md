# ローカル開発環境セットアップ

## 重要な注意事項

**本番環境を保護するため、以下の設定を必ず守ってください：**

- 本番環境: `/home/ubuntu/data/data_accounts` (デフォルト)
- ローカル環境: `vault/data/data_accounts` (環境変数指定時のみ)

## ローカル開発環境のセットアップ

### 1. 環境変数の設定

ローカル開発時には以下の環境変数を設定：

```bash
export WATCHME_LOCAL_DEV=1
```

### 2. アプリケーション起動

```bash
# vaultディレクトリで作業
cd vault

# 依存関係インストール（初回のみ）
pip install -r requirements.txt

# ローカル開発モードで起動
WATCHME_LOCAL_DEV=1 uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 3. データディレクトリ構造

環境変数設定時、以下の構造でデータが保存されます：

```
vault/
├── app.py               # メインAPIサーバー
├── requirements.txt     # 開発用依存関係
├── data/               # ローカル開発用データ
│   └── data_accounts/
│       └── user123/
│           └── 2025-06-21/
│               ├── raw/              # WAV音声ファイル
│               ├── transcriptions/   # 文字起こしJSON
│               ├── prompt/           # ChatGPTプロンプトJSON
│               ├── emotion-timeline/ # 感情タイムライン
│               ├── sed/              # SEDタイムライン
│               └── sed-summary/      # SEDサマリー
├── .gitignore
├── LOCAL_DEV.md
└── README.md
```

## 本番環境への安全なデプロイ

- `data/` ディレクトリは `.gitignore` で除外済み
- 本番環境では環境変数設定なしで従来通り動作
- 本番環境のデータ構造は変更されません

## 動作確認

環境変数の設定確認：
```bash
echo $WATCHME_LOCAL_DEV
```

アプリケーション起動時のログで使用されるBASE_DIRを確認してください。