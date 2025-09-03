# WatchMe Vault API - Dockerデプロイメントガイド

最終更新: 2025年9月3日

## 🔄 重要な変更（2025年9月3日）

### systemd管理への完全移行
このAPIは**systemdサービスとして管理**されるようになりました。
- **自動起動**: サーバー再起動時に自動的に起動
- **統一管理**: 他のWatchMeサービスと同じ管理方式
- **本番用設定**: `docker-compose.prod.yml`を使用

## 概要

このドキュメントでは、WatchMe Vault APIをEC2上でDockerコンテナとして実行する手順を説明します。

**現在の環境:**
- サービス名: `watchme-vault-api.service`
- ポート: 8000（localhost only）
- 公開URL: `https://api.hey-watch.me` → `localhost:8000`
- サーバー: EC2 (Ubuntu) - 3.24.16.82
- リポジトリ: `git@github.com:matsumotokaya/watchme-api-whisper-prompt.git`
- 実行方式: **Docker (docker-compose.prod.yml) + systemd管理**

## 前提条件

- EC2インスタンスへのSSHアクセス
- Dockerがインストールされていること
- watchme-server-configsリポジトリがセットアップ済み
- 環境変数ファイル（.env）が設定されていること

## 🚀 標準デプロイ手順（2025年9月3日更新）

### ステップ1: systemdサービス設定の準備

**重要**: デプロイ前に`watchme-server-configs`リポジトリでsystemdサービス設定を確認・更新します。

```bash
# ローカルで作業
cd /Users/kaya.matsumoto/projects/watchme/watchme-server-configs

# systemdサービスファイルを確認
cat systemd/watchme-vault-api.service
```

**必須設定内容:**
```ini
[Unit]
Description=WatchMe Vault API Docker Container
After=docker.service watchme-infrastructure.service
Requires=docker.service watchme-infrastructure.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/watchme-vault-api-docker
TimeoutStartSec=0

# 既存コンテナを停止してから起動
ExecStartPre=-/usr/bin/docker-compose -f docker-compose.prod.yml down
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### ステップ2: サーバーへの接続と準備

```bash
# 1. サーバーへ接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# 2. 作業ディレクトリの確認（既存の場合）
cd /home/ubuntu/watchme-vault-api-docker

# または新規作成
mkdir -p /home/ubuntu/watchme-vault-api-docker
cd /home/ubuntu/watchme-vault-api-docker
```

### ステップ3: コードの取得・更新

```bash
# 初回の場合
git clone git@github.com:matsumotokaya/watchme-api-whisper-prompt.git .

# 更新の場合
git pull origin main
```

### ステップ4: 環境変数の設定

```bash
# .envファイルを作成（初回のみ）
cp .env.example .env
nano .env

# 必須環境変数：
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# S3_BUCKET_NAME=watchme-vault
# AWS_REGION=ap-southeast-2
# SUPABASE_URL=https://qvtlwotzuzbavrzqhyvt.supabase.co
# SUPABASE_KEY=your_supabase_key
```

### ステップ5: Docker設定の確認

**⚠️ 重要: 本番では必ず`docker-compose.prod.yml`を使用**

```bash
# docker-compose.prod.ymlの確認
cat docker-compose.prod.yml

# 以下を確認:
# 1. Dockerfile.prodを使用している
# 2. watchme-networkに接続している（external: true）
# 3. healthcheckが設定されている
# 4. restart: alwaysが設定されている
```

**必須要素の確認:**
```yaml
services:
  vault-api:
    build:
      context: .
      dockerfile: Dockerfile.prod  # 本番用Dockerfile
    networks:
      - watchme-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    restart: always

networks:
  watchme-network:
    external: true  # 既存ネットワークを使用
```

### ステップ6: systemd設定の反映

```bash
# watchme-server-configsを最新化
cd /home/ubuntu/watchme-server-configs
git pull origin main

# setup_server.shを実行
./setup_server.sh
```

### ステップ7: サービスの起動

```bash
# 手動起動のコンテナがある場合は停止
cd /home/ubuntu/watchme-vault-api-docker
docker-compose -f docker-compose.prod.yml down

# systemdサービスを有効化・起動
sudo systemctl enable watchme-vault-api.service
sudo systemctl start watchme-vault-api.service

# 状態確認
sudo systemctl status watchme-vault-api.service
```

### ステップ8: 動作確認

```bash
# systemdサービスの状態
sudo systemctl status watchme-vault-api.service | grep -E "Active|Loaded"
# → Active: active (running), Loaded: enabled

# Dockerコンテナの状態
docker ps | grep watchme-vault-api
# → Up X minutes (healthy)

# ヘルスチェック
curl http://localhost:8000/health
# → {"status":"healthy",...}

# ログ確認
docker logs watchme-vault-api --tail 50
sudo journalctl -u watchme-vault-api.service -n 50
```

## 📝 運用コマンド

### サービスの管理（systemd経由）

```bash
# サービス状態確認
sudo systemctl status watchme-vault-api.service

# サービス再起動
sudo systemctl restart watchme-vault-api.service

# サービス停止
sudo systemctl stop watchme-vault-api.service

# サービス開始
sudo systemctl start watchme-vault-api.service

# ログ確認
sudo journalctl -u watchme-vault-api.service -f
```

### Dockerコンテナの直接管理（トラブルシューティング時）

```bash
cd /home/ubuntu/watchme-vault-api-docker

# コンテナ状態確認
docker-compose -f docker-compose.prod.yml ps

# ログ確認
docker-compose -f docker-compose.prod.yml logs -f vault-api

# コンテナ再ビルド（コード更新後）
docker-compose -f docker-compose.prod.yml build --no-cache

# ヘルスチェック状態
docker inspect watchme-vault-api | jq '.[0].State.Health'
```

## 🔧 トラブルシューティング

### 問題: コンテナがunhealthy状態

**症状**: `docker ps`で`(unhealthy)`と表示される

**確認事項:**
1. Dockerfile.prodにcurlがインストールされているか
   ```dockerfile
   RUN apt-get update && apt-get install -y curl
   ```

2. ヘルスチェックエンドポイントが正しく動作しているか
   ```bash
   docker exec watchme-vault-api curl -f http://localhost:8000/health
   ```

3. 正しいDockerfileが使用されているか
   ```bash
   # docker-compose.prod.ymlを確認
   grep dockerfile docker-compose.prod.yml
   # → dockerfile: Dockerfile.prod
   ```

### 問題: サーバー再起動後にサービスが起動しない

**確認事項:**
1. systemdサービスが有効化されているか
   ```bash
   sudo systemctl is-enabled watchme-vault-api.service
   # → enabled
   ```

2. 依存関係が正しく設定されているか
   ```bash
   sudo systemctl list-dependencies watchme-vault-api.service
   ```

### 問題: ネットワーク接続エラー

**症状**: 他のコンテナから接続できない

**確認事項:**
1. watchme-networkに接続されているか
   ```bash
   docker network inspect watchme-network | grep watchme-vault-api
   ```

2. docker-compose.prod.ymlの設定
   ```yaml
   networks:
     watchme-network:
       external: true  # これが必須
   ```

## 📊 ヘルスチェック

### 内部ヘルスチェック
```bash
# コンテナ内から
docker exec watchme-vault-api curl http://localhost:8000/health
```

### 外部ヘルスチェック
```bash
# Nginx経由
curl https://api.hey-watch.me/health
```

### 自動監視（推奨）
```bash
# cronジョブ設定
crontab -e

# 5分ごとにヘルスチェック
*/5 * * * * curl -f http://localhost:8000/health || systemctl restart watchme-vault-api.service
```

## 🔄 更新手順

### コード更新時の標準手順

```bash
# 1. サーバーに接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# 2. 最新コードを取得
cd /home/ubuntu/watchme-vault-api-docker
git pull origin main

# 3. サービス再起動（systemd経由）
sudo systemctl restart watchme-vault-api.service

# 4. 状態確認
sudo systemctl status watchme-vault-api.service
docker ps | grep watchme-vault-api
```

### 設定変更時の手順

```bash
# 1. watchme-server-configsを更新
cd /home/ubuntu/watchme-server-configs
git pull origin main

# 2. setup_server.shを実行
./setup_server.sh

# 3. サービス再起動
sudo systemctl restart watchme-vault-api.service
```

## ⚠️ 重要な注意事項

### 本番環境での鉄則

1. **必ず`docker-compose.prod.yml`を使用**
   - 開発用の`docker-compose.yml`は使用しない
   - Dockerfile.prodには必要な依存関係（curl等）が含まれている

2. **systemd管理を徹底**
   - 手動での`docker-compose up`は避ける
   - 全ての操作はsystemd経由で行う

3. **ネットワーク設定の確認**
   - watchme-networkへの接続は必須
   - external: trueの設定を忘れない

4. **環境変数の保護**
   ```bash
   chmod 600 .env
   ```

## 📝 今回の教訓（2025年9月3日）

### 修正内容
1. **問題**: ヘルスチェックでcurlが見つからない
   - **原因**: 開発用Dockerfileが使用されていた
   - **解決**: docker-compose.prod.ymlに切り替え

2. **問題**: サーバー再起動時に自動起動しない
   - **原因**: 手動でdocker-composeを実行していた
   - **解決**: systemdサービスとして管理

3. **改善点**:
   - watchme-server-configsでの一元管理
   - 標準化されたデプロイプロセス
   - 明確なトラブルシューティングガイド

## バックアップとリカバリ

### 環境変数のバックアップ
```bash
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
```

### Dockerイメージのバックアップ
```bash
docker save watchme-vault-api-docker-vault-api:latest | gzip > vault-api-backup-$(date +%Y%m%d).tar.gz
```

### リカバリ手順
```bash
# イメージのリストア
docker load < vault-api-backup-20250903.tar.gz

# サービス再起動
sudo systemctl restart watchme-vault-api.service
```

## 問題発生時の連絡先

- 開発者: Kaya Matsumoto
- 最終更新: 2025年9月3日
- バージョン: 2.5.0（systemd管理対応版）
- 関連ドキュメント: `/home/ubuntu/watchme-server-configs/API_DEPLOYMENT_GUIDE.md`