# WatchMe Vault API - Dockerデプロイメントガイド

## 概要

このドキュメントでは、WatchMe Vault APIをEC2上でDockerコンテナとして実行する手順を説明します。

**現在の環境:**
- サービス名: `watchme-vault-api.service`
- ポート: 8000
- 公開URL: `https://api.hey-watch.me` → `localhost:8000`
- サーバー: EC2 (Ubuntu)

## 前提条件

- EC2インスタンスへのSSHアクセス
- Dockerがインストールされていること
- 環境変数ファイル（.env）が設定されていること

## デプロイ手順

### 1. サーバーへ接続

```bash
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
```

### 2. アプリケーションディレクトリの準備

```bash
# 新しいディレクトリを作成（Dockerデプロイ用）
mkdir -p /home/ubuntu/watchme-vault-api-docker
cd /home/ubuntu/watchme-vault-api-docker

# GitHubからコードを取得
git clone git@github.com:matsumotokaya/watchme-vault-api.git .
```

### 3. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env
nano .env

# 以下の環境変数を設定：
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# S3_BUCKET_NAME=watchme-vault
# AWS_REGION=us-east-1
# SUPABASE_URL=https://qvtlwotzuzbavrzqhyvt.supabase.co
# SUPABASE_KEY=your_supabase_key
```

### 4. Dockerのインストール（未インストールの場合）

```bash
# Dockerのインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Docker Composeのインストール
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 一度ログアウトして再ログイン（dockerグループの反映）
exit
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
```

### 5. デプロイスクリプトの実行

```bash
cd /home/ubuntu/watchme-vault-api-docker
chmod +x deploy.sh
./deploy.sh
```

このスクリプトは以下を自動的に実行します：
- 既存のsystemdサービス（watchme-vault-api.service）の停止
- Dockerイメージのビルド
- コンテナの起動
- ヘルスチェック

### 6. 手動デプロイ（スクリプトを使わない場合）

```bash
# 既存のsystemdサービスを停止
sudo systemctl stop watchme-vault-api.service
sudo systemctl disable watchme-vault-api.service

# Dockerイメージをビルド
docker compose build

# コンテナを起動
docker compose up -d

# ログを確認
docker compose logs -f vault-api

# ヘルスチェック
curl http://localhost:8000/health
```

## 運用コマンド

### コンテナの管理

```bash
# ステータス確認
docker compose ps

# ログ確認（リアルタイム）
docker compose logs -f vault-api

# ログ確認（最新100行）
docker compose logs --tail 100 vault-api

# コンテナ再起動
docker compose restart vault-api

# コンテナ停止
docker compose down

# コンテナ起動
docker compose up -d
```

### 更新手順

```bash
# 最新コードを取得
git pull origin main

# コンテナを再ビルドして起動
docker compose down
docker compose build --no-cache
docker compose up -d
```

### トラブルシューティング

```bash
# コンテナの詳細情報
docker inspect watchme-vault-api

# コンテナ内でコマンド実行
docker exec -it watchme-vault-api /bin/bash

# 環境変数の確認
docker compose exec vault-api env | grep -E "AWS|SUPABASE|S3"

# ネットワークの確認
docker compose exec vault-api curl http://localhost:8000/health
```

## Nginxの設定確認

既存のNginx設定は変更不要です。`api.hey-watch.me`は引き続き`localhost:8000`に転送されます。

```nginx
# /etc/nginx/sites-available/api.hey-watch.me
server {
    server_name api.hey-watch.me;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## バックアップとロールバック

### バックアップ

```bash
# 環境変数のバックアップ
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Dockerイメージのバックアップ
docker save watchme-vault-api-docker-vault-api:latest | gzip > vault-api-backup-$(date +%Y%m%d).tar.gz
```

### ロールバック（systemdに戻す場合）

```bash
# Dockerコンテナを停止
docker compose down

# systemdサービスを再度有効化
cd /home/ubuntu/watchme_api
sudo systemctl enable watchme-vault-api.service
sudo systemctl start watchme-vault-api.service
```

## セキュリティ考慮事項

1. **.envファイルの権限**
   ```bash
   chmod 600 .env
   ```

2. **Dockerデーモンのセキュリティ**
   - rootless Dockerの使用を検討
   - 不要なポートは公開しない

3. **ログの管理**
   ```bash
   # ログローテーションの設定
   docker compose logs --tail 1000 > logs/vault-api-$(date +%Y%m%d).log
   ```

## パフォーマンスチューニング

### Docker Composeの設定調整

```yaml
# docker-compose.yml に追加可能な設定
services:
  vault-api:
    # リソース制限
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 複数ワーカーでの実行

Dockerfileを修正して複数ワーカーを使用：

```dockerfile
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## モニタリング

### Docker統計情報

```bash
# リアルタイムの統計情報
docker stats watchme-vault-api

# CPU/メモリ使用率の確認
docker compose exec vault-api ps aux
```

### ヘルスチェックの自動化

```bash
# cronジョブの設定例
*/5 * * * * curl -f http://localhost:8000/health || echo "Vault API is down" | mail -s "Alert: Vault API" admin@example.com
```

## 移行完了後のクリーンアップ

Dockerが安定して動作することを確認後：

```bash
# 古いディレクトリのバックアップ
sudo tar -czf watchme_api_backup_$(date +%Y%m%d).tar.gz /home/ubuntu/watchme_api

# バックアップ後に削除
sudo rm -rf /home/ubuntu/watchme_api

# systemdサービスファイルの削除
sudo rm /etc/systemd/system/watchme-vault-api.service
sudo systemctl daemon-reload
```

## 問題発生時の連絡先

- 開発者: Kaya Matsumoto
- デプロイ日: [デプロイ実行日を記入]
- バージョン: 2.0.0（S3移行版）