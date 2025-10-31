#!/bin/bash

# =========================================
# WatchMe Vault API - 本番環境デプロイスクリプト
# =========================================
#
# このスクリプトは、EC2上でDockerコンテナを完全に
# 再起動し、最新のECRイメージを使用して
# WatchMe Vault APIを起動します。
#
# 使用方法:
#   ./run-prod.sh
#
# 前提条件:
#   - docker-compose.prod.ymlが同じディレクトリに存在
#   - .envファイルが同じディレクトリに存在
#   - ECRに最新イメージがプッシュ済み
#
# =========================================

set -e  # エラーで即座に終了

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# コンテナ名の定義
CONTAINER_NAME="watchme-vault-api"
ECR_REGISTRY="754724220380.dkr.ecr.ap-southeast-2.amazonaws.com"
ECR_REPOSITORY="watchme-api-vault"
AWS_REGION="ap-southeast-2"

echo -e "${GREEN}🚀 WatchMe Vault API - 本番デプロイ開始${NC}"
echo "========================================"
echo ""

# ステップ1: ECRにログイン
echo -e "${BLUE}🔑 Step 1: ECRにログイン中...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ ECRログイン成功${NC}"
else
    echo -e "${RED}❌ ECRログインに失敗しました${NC}"
    exit 1
fi
echo ""

# ステップ2: 最新イメージをECRから取得
echo -e "${BLUE}📥 Step 2: 最新イメージをECRから取得中...${NC}"
docker pull ${ECR_REGISTRY}/${ECR_REPOSITORY}:latest
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ イメージ取得成功${NC}"
else
    echo -e "${RED}❌ イメージ取得に失敗しました${NC}"
    exit 1
fi
echo ""

# ステップ3: 既存コンテナの完全削除（3層アプローチ）
echo -e "${BLUE}🗑️  Step 3: 既存コンテナを完全削除中...${NC}"

# 3-1. 実行中コンテナの検索と停止
echo "  📦 実行中コンテナの検索..."
RUNNING_CONTAINERS=$(docker ps -q --filter "name=${CONTAINER_NAME}")
if [ ! -z "$RUNNING_CONTAINERS" ]; then
    echo "  ⏸️  実行中コンテナを停止中..."
    docker stop $RUNNING_CONTAINERS
    echo -e "  ${GREEN}✅ コンテナを停止しました${NC}"
else
    echo "  ℹ️  実行中のコンテナは見つかりませんでした"
fi

# 3-2. 全コンテナの削除（停止済み含む）
echo "  📦 全コンテナの削除..."
ALL_CONTAINERS=$(docker ps -aq --filter "name=${CONTAINER_NAME}")
if [ ! -z "$ALL_CONTAINERS" ]; then
    echo "  🗑️  コンテナを削除中..."
    docker rm -f $ALL_CONTAINERS
    echo -e "  ${GREEN}✅ コンテナを削除しました${NC}"
else
    echo "  ℹ️  削除するコンテナは見つかりませんでした"
fi

# 3-3. docker-compose管理コンテナの削除
echo "  📦 docker-compose管理コンテナの削除..."
docker-compose -f docker-compose.prod.yml down || true
echo -e "${GREEN}✅ 既存コンテナの削除完了${NC}"
echo ""

# ステップ4: 新規コンテナの起動
echo -e "${BLUE}🚀 Step 4: 新規コンテナを起動中...${NC}"
docker-compose -f docker-compose.prod.yml up -d
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ コンテナ起動成功${NC}"
else
    echo -e "${RED}❌ コンテナ起動に失敗しました${NC}"
    exit 1
fi
echo ""

# ステップ5: コンテナ起動待機
echo -e "${BLUE}⏳ Step 5: コンテナの起動を待機中...${NC}"
sleep 5
echo -e "${GREEN}✅ 待機完了${NC}"
echo ""

# ステップ6: コンテナの状態確認
echo -e "${BLUE}📊 Step 6: コンテナの状態確認...${NC}"
CONTAINER_STATUS=$(docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}")
if [ ! -z "$CONTAINER_STATUS" ]; then
    echo "$CONTAINER_STATUS"
    echo -e "${GREEN}✅ コンテナは正常に稼働中です${NC}"
else
    echo -e "${RED}❌ コンテナが見つかりません${NC}"
    echo "ログを確認してください:"
    docker logs ${CONTAINER_NAME} --tail 50
    exit 1
fi
echo ""

# ステップ7: ヘルスチェック
echo -e "${BLUE}🏥 Step 7: ヘルスチェック実行中...${NC}"
echo "最大60秒間（12回 × 5秒）リトライします..."

for i in {1..12}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ヘルスチェック成功 (試行 $i/12)${NC}"
        echo ""

        # ヘルスチェックの詳細情報を表示
        echo "📊 ヘルスチェック詳細:"
        curl -s http://localhost:8000/health | python3 -m json.tool || echo "{}"
        echo ""

        # 最終結果
        echo "========================================"
        echo -e "${GREEN}🎉 デプロイが正常に完了しました！${NC}"
        echo "========================================"
        echo ""
        echo "📦 コンテナ名: ${CONTAINER_NAME}"
        echo "🌐 ローカルURL: http://localhost:8000"
        echo "🌐 本番URL: https://api.hey-watch.me/vault/"
        echo "📋 ログ確認: docker logs ${CONTAINER_NAME} -f"
        echo ""
        exit 0
    fi

    echo -e "${YELLOW}  試行 $i/12 失敗、5秒後に再試行...${NC}"
    sleep 5
done

# ヘルスチェック失敗時
echo -e "${RED}❌ ヘルスチェックに失敗しました${NC}"
echo ""
echo "デバッグ情報:"
echo "------------"
echo "コンテナログ（最新50行）:"
docker logs ${CONTAINER_NAME} --tail 50
echo ""
echo "コンテナステータス:"
docker ps -a --filter "name=${CONTAINER_NAME}"
echo ""
echo "トラブルシューティング:"
echo "1. docker logs ${CONTAINER_NAME} -f でログを確認"
echo "2. .envファイルの環境変数が正しく設定されているか確認"
echo "3. S3とSupabaseの認証情報が正しいか確認"

exit 1
