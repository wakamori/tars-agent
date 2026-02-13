#!/bin/bash

# TARS イメージクリーンアップスクリプト
# 古いコンテナイメージを削除して Artifact Registry のストレージ課金を削減

# 色付けのための定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TARS イメージクリーンアップ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# プロジェクトIDの確認
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}エラー: Google Cloud プロジェクトが設定されていません${NC}"
    exit 1
fi

echo -e "${GREEN}✓ プロジェクトID: $PROJECT_ID${NC}"
echo ""

# Artifact Registry のロケーション
REGION="asia-northeast1"
REPOSITORY="cloud-run-source-deploy"

echo -e "${BLUE}🔍 古いイメージを検索中...${NC}"
echo ""

# イメージのリストを取得
IMAGES=$(gcloud artifacts docker images list \
    ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/tars \
    --format="value(package)" \
    --limit=20 2>/dev/null)

if [ -z "$IMAGES" ]; then
    echo -e "${YELLOW}古いイメージは見つかりませんでした${NC}"
    exit 0
fi

# イメージの詳細を表示
echo -e "${BLUE}以下のイメージが見つかりました:${NC}"
gcloud artifacts docker images list \
    ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/tars \
    --format="table(package, tags, create_time)" \
    --limit=20

echo ""
echo -e "${YELLOW}⚠️  最新のイメージ以外を削除します${NC}"
echo -e "${YELLOW}   ロールバックが必要な場合は、この操作を行わないでください${NC}"
echo ""
read -p "古いイメージを削除しますか？ (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}クリーンアップをキャンセルしました${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}🗑️  古いイメージを削除中...${NC}"

# 最新の3つを除いて削除
IMAGES_TO_DELETE=$(gcloud artifacts docker images list \
    ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/tars \
    --format="value(package)" \
    --sort-by="~CREATE_TIME" \
    --limit=100 | tail -n +4)

if [ -z "$IMAGES_TO_DELETE" ]; then
    echo -e "${GREEN}✓ 削除対象のイメージはありません（最新3つを保持）${NC}"
    exit 0
fi

DELETED_COUNT=0
for image in $IMAGES_TO_DELETE; do
    echo "  削除中: $image"
    gcloud artifacts docker images delete "$image" --quiet 2>/dev/null
    if [ $? -eq 0 ]; then
        ((DELETED_COUNT++))
    fi
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  クリーンアップ完了！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}削除したイメージ: ${DELETED_COUNT}個${NC}"
echo ""
echo -e "${BLUE}💡 定期的にこのスクリプトを実行してストレージコストを削減できます${NC}"
