#!/bin/bash

# TARS デプロイスクリプト
# Google Cloud Run へのデプロイを簡略化

# 色付けのための定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TARS デプロイスクリプト${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# プロジェクトIDの確認
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}エラー: Google Cloud プロジェクトが設定されていません${NC}"
    echo "以下のコマンドを実行してプロジェクトを設定してください:"
    echo "  gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}✓ プロジェクトID: $PROJECT_ID${NC}"
echo ""

# デプロイ確認（課金対策）
echo -e "${BLUE}📊 デプロイコスト情報:${NC}"
echo "  • Cloud Build: 月120分まで無料（超過後 $0.003/分）"
echo "  • Cloud Run: 月2M リクエスト・36万GB秒まで無料"
echo "  • Artifact Registry: ストレージ 0.5GB まで無料"
echo ""
echo -e "${BLUE}💡 コスト削減のヒント:${NC}"
echo "  • 古いイメージは自動削除されません（手動削除推奨）"
echo "  • ローカルテストには: uvicorn backend.main:app --reload"
echo ""
read -p "このままデプロイを続けますか？ (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}デプロイをキャンセルしました${NC}"
    exit 0
fi
echo ""

# 必要なAPIの有効化
echo -e "${BLUE}必要なAPIを有効化しています...${NC}"
gcloud services enable \
    aiplatform.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ API有効化完了${NC}"
else
    echo -e "${RED}✗ API有効化に失敗しました${NC}"
    exit 1
fi
echo ""

# Cloud Runへデプロイ
echo -e "${BLUE}Cloud Runへデプロイしています...${NC}"
echo "  リージョン: asia-northeast1"
echo "  メモリ: 1Gi"
echo ""

gcloud run deploy tars \
    --source . \
    --region asia-northeast1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --platform managed \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=asia-northeast1"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  デプロイ成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # URLを取得して表示
    SERVICE_URL=$(gcloud run services describe tars --region asia-northeast1 --format 'value(status.url)')
    echo -e "${BLUE}アプリケーションURL:${NC}"
    echo -e "${GREEN}$SERVICE_URL${NC}"
    echo ""
    echo "ブラウザで上記URLを開いてTARSを使用できます。"
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  デプロイ失敗${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
