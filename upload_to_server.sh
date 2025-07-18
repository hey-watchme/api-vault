#!/bin/bash
# EC2サーバーへのアップロードスクリプト

# 色の定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# サーバー情報
SERVER_USER="ubuntu"
SERVER_IP="3.24.16.82"
KEY_PATH="~/watchme-key.pem"
REMOTE_DIR="/home/ubuntu/watchme-vault-api-docker"

echo -e "${YELLOW}=== WatchMe Vault API - サーバーアップロード ===${NC}"
echo ""

# アップロードするファイルのリスト
FILES=(
    "app.py"
    "requirements.txt"
    "Dockerfile"
    "Dockerfile.prod"
    "docker-compose.yml"
    "docker-compose.prod.yml"
    ".dockerignore"
    "deploy.sh"
    "README.md"
    "DEPLOYMENT.md"
    ".env.example"
)

# Step 1: SSHキーの確認
echo -e "${YELLOW}Step 1: SSHキーの確認${NC}"
if [ ! -f ~/watchme-key.pem ]; then
    echo -e "${RED}❌ SSHキー（~/watchme-key.pem）が見つかりません${NC}"
    exit 1
fi
echo -e "${GREEN}✅ SSHキーを確認しました${NC}"

# Step 2: リモートディレクトリの作成
echo ""
echo -e "${YELLOW}Step 2: リモートディレクトリの作成${NC}"
ssh -i $KEY_PATH $SERVER_USER@$SERVER_IP "mkdir -p $REMOTE_DIR"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ リモートディレクトリを作成しました: $REMOTE_DIR${NC}"
else
    echo -e "${RED}❌ リモートディレクトリの作成に失敗しました${NC}"
    exit 1
fi

# Step 3: ファイルのアップロード
echo ""
echo -e "${YELLOW}Step 3: ファイルのアップロード${NC}"
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -n "アップロード中: $file ... "
        scp -i $KEY_PATH "$file" $SERVER_USER@$SERVER_IP:$REMOTE_DIR/
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅${NC}"
        else
            echo -e "${RED}❌ 失敗${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  $file が見つかりません（スキップ）${NC}"
    fi
done

# Step 4: .envファイルの準備
echo ""
echo -e "${YELLOW}Step 4: 環境変数ファイルの準備${NC}"
echo "サーバー上で.envファイルを作成します..."
ssh -i $KEY_PATH $SERVER_USER@$SERVER_IP << 'EOF'
cd /home/ubuntu/watchme-vault-api-docker
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env.exampleから.envを作成しました"
        echo "⚠️  .envファイルを編集して環境変数を設定してください："
        echo "   nano .env"
    else
        echo "⚠️  .env.exampleが見つかりません"
    fi
else
    echo "✅ .envファイルは既に存在します"
fi
EOF

# Step 5: 実行権限の付与
echo ""
echo -e "${YELLOW}Step 5: 実行権限の付与${NC}"
ssh -i $KEY_PATH $SERVER_USER@$SERVER_IP "cd $REMOTE_DIR && chmod +x deploy.sh"
echo -e "${GREEN}✅ deploy.shに実行権限を付与しました${NC}"

# Step 6: アップロード完了の確認
echo ""
echo -e "${YELLOW}Step 6: アップロード完了の確認${NC}"
echo "アップロードされたファイル:"
ssh -i $KEY_PATH $SERVER_USER@$SERVER_IP "cd $REMOTE_DIR && ls -la"

# 完了メッセージ
echo ""
echo -e "${GREEN}=== アップロード完了 ===${NC}"
echo ""
echo "次のステップ:"
echo "1. サーバーにSSH接続:"
echo "   ssh -i ~/watchme-key.pem ubuntu@3.24.16.82"
echo ""
echo "2. ディレクトリに移動:"
echo "   cd /home/ubuntu/watchme-vault-api-docker"
echo ""
echo "3. 環境変数を設定（初回のみ）:"
echo "   nano .env"
echo ""
echo "4. デプロイスクリプトを実行:"
echo "   ./deploy.sh"
echo ""
echo "または本番環境用のDocker Composeを使用:"
echo "   docker compose -f docker-compose.prod.yml up -d"