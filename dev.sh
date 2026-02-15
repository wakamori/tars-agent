#!/bin/bash

# TARS ローカル開発用スクリプト
# uv を使った高速セットアップと起動

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TARS ローカル開発環境${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# uv がインストールされているか確認
if ! command -v uv &> /dev/null; then
    echo -e "${RED}エラー: uv がインストールされていません${NC}"
    echo "以下のコマンドでインストールしてください:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✓ uv が見つかりました${NC}"

# 依存関係をインストール
echo ""
echo -e "${BLUE}依存関係をインストールしています...${NC}"
uv sync --extra dev

echo -e "${GREEN}✓ 依存関係のインストール完了${NC}"
echo ""

# サーバー起動
echo -e "${BLUE}バックエンドサーバーを起動しています...${NC}"
echo "  URL: http://localhost:8080"
echo "  停止: Ctrl+C"
echo ""

cd backend && uv run uvicorn main:app --reload --port 8080
