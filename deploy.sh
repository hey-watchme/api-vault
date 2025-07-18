#!/bin/bash
# Vault API Dockerデプロイスクリプト

echo "=== WatchMe Vault API Docker Deployment ==="
echo ""

# 色の定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 現在のディレクトリ確認
CURRENT_DIR=$(pwd)
echo -e "${YELLOW}現在のディレクトリ: $CURRENT_DIR${NC}"

# Step 1: 既存のsystemdサービスを停止
echo ""
echo -e "${YELLOW}Step 1: 既存のsystemdサービスを停止${NC}"
if sudo systemctl is-active --quiet watchme-vault-api.service; then
    echo "watchme-vault-api.service を停止します..."
    sudo systemctl stop watchme-vault-api.service
    sudo systemctl disable watchme-vault-api.service
    echo -e "${GREEN}✅ サービスを停止しました${NC}"
else
    echo "watchme-vault-api.service は実行されていません"
fi

# Step 2: Dockerがインストールされているか確認
echo ""
echo -e "${YELLOW}Step 2: Docker環境の確認${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Dockerがインストールされていません${NC}"
    echo "Dockerをインストールしてください："
    echo "curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "sudo sh get-docker.sh"
    echo "sudo usermod -aG docker ubuntu"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Composeがインストールされていません${NC}"
    echo "Docker Composeをインストールしてください："
    echo "sudo apt-get update"
    echo "sudo apt-get install docker-compose-plugin"
    exit 1
fi

echo -e "${GREEN}✅ Docker環境が確認できました${NC}"
docker --version
docker compose version

# Step 3: 環境変数ファイルの確認
echo ""
echo -e "${YELLOW}Step 3: 環境変数の確認${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}❌ .envファイルが見つかりません${NC}"
    echo ".envファイルを作成してください。"
    echo "例："
    echo "cp .env.example .env"
    echo "nano .env  # 環境変数を設定"
    exit 1
fi
echo -e "${GREEN}✅ .envファイルが見つかりました${NC}"

# Step 4: 既存のコンテナを停止（存在する場合）
echo ""
echo -e "${YELLOW}Step 4: 既存のDockerコンテナを停止${NC}"
if [ "$(docker ps -aq -f name=watchme-vault-api)" ]; then
    echo "既存のコンテナを停止します..."
    docker compose down
    echo -e "${GREEN}✅ 既存のコンテナを停止しました${NC}"
else
    echo "既存のコンテナはありません"
fi

# Step 5: Dockerイメージをビルド
echo ""
echo -e "${YELLOW}Step 5: Dockerイメージをビルド${NC}"
docker compose build --no-cache
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dockerイメージのビルドが完了しました${NC}"
else
    echo -e "${RED}❌ Dockerイメージのビルドに失敗しました${NC}"
    exit 1
fi

# Step 6: コンテナを起動
echo ""
echo -e "${YELLOW}Step 6: Dockerコンテナを起動${NC}"
docker compose up -d
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dockerコンテナを起動しました${NC}"
else
    echo -e "${RED}❌ Dockerコンテナの起動に失敗しました${NC}"
    exit 1
fi

# Step 7: ヘルスチェック
echo ""
echo -e "${YELLOW}Step 7: ヘルスチェック${NC}"
echo "APIの起動を待機中..."
sleep 5

# ヘルスチェックを実行
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}✅ APIが正常に起動しました${NC}"
        echo ""
        echo "ヘルスチェック結果:"
        curl -s http://localhost:8000/health | python3 -m json.tool
        break
    else
        if [ $i -eq 10 ]; then
            echo -e "${RED}❌ APIの起動に失敗しました${NC}"
            echo "ログを確認してください："
            echo "docker compose logs vault-api"
            exit 1
        fi
        echo "再試行中... ($i/10)"
        sleep 3
    fi
done

# Step 8: 最終確認
echo ""
echo -e "${YELLOW}Step 8: デプロイ完了${NC}"
echo ""
echo "📋 デプロイサマリー:"
echo "  - コンテナ名: watchme-vault-api"
echo "  - ポート: 8000"
echo "  - ステータス: $(docker compose ps --format 'table {{.Status}}' | tail -n 1)"
echo ""
echo "🔧 便利なコマンド:"
echo "  - ログ確認: docker compose logs -f vault-api"
echo "  - 再起動: docker compose restart vault-api"
echo "  - 停止: docker compose down"
echo "  - ステータス確認: docker compose ps"
echo ""
echo -e "${GREEN}✅ デプロイが完了しました！${NC}"

# オプション: 古いディレクトリの削除確認
echo ""
echo -e "${YELLOW}オプション: 古いアプリケーションディレクトリの削除${NC}"
echo "既存の /home/ubuntu/watchme_api ディレクトリを削除しますか？"
echo "（Dockerが正常に動作していることを確認してから削除することをお勧めします）"
echo -n "削除しますか？ (y/N): "
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    if [ -d "/home/ubuntu/watchme_api" ]; then
        echo "バックアップを作成中..."
        sudo mv /home/ubuntu/watchme_api /home/ubuntu/watchme_api_backup_$(date +%Y%m%d_%H%M%S)
        echo -e "${GREEN}✅ 古いディレクトリをバックアップしました${NC}"
    fi
fi