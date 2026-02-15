# 開発効率向上の提案

## ✅ 実施済み

- [x] **uv**: 高速Pythonパッケージマネージャー
- [x] **ruff**: 高速Python linter + formatter
- [x] **TypeScript**: 型安全なフロントエンド開発
- [x] **esbuild**: 高速ビルド（4-19ms）
- [x] **ESLint**: TypeScriptコード品質チェック
- [x] **npm scripts**: ビルド・lint・型チェックの自動化
- [x] **Hot Reload with Browser Sync**: ファイル変更時に自動ビルド+ブラウザリロード
- [x] **Pre-commit Hooks (husky + lint-staged)**: git commit時に自動リント・フォーマット

## 🎯 推奨: すぐに導入可能

### 1. ~~**Hot Reload with Browser Sync**~~ ✅ 実装済み (優先度: 高)

**効果**: フロントエンドの変更が即座にブラウザに反映

**使用法:**

```bash
npm run dev    # 自動ビルド + ブラウザ自動リロード
```

---

### 2. ~~**Pre-commit Hooks**~~ ✅ 実装済み (優先度: 高)

**効果**: コミット前に自動でコード品質チェック、バグを事前防止

**動作**: `git commit` 実行時に自動で以下が実行されます

- TypeScript: ESLint自動修正 + 型チェック
- Python: ruff check --fix + ruff format

---

### 3. **Docker Compose for Local Dev** (優先度: 中)

**効果**: 1コマンドで開発環境全体を起動

**docker-compose.yml:**

```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./backend:/app/backend
      - ./frontend:/app/frontend
    environment:
      - PYTHONUNBUFFERED=1
    command: uv run uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
  
  frontend:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./frontend:/app/frontend
      - ./package.json:/app/package.json
      - ./package-lock.json:/app/package-lock.json
    command: sh -c "npm install && npm run watch"
```

**使用法:**

```bash
docker-compose up  # すべて起動
```

---

### 4. **VS Code Workspace Settings** (優先度: 中)

**効果**: チーム全体で一貫した開発環境

**.vscode/extensions.json を作成:**

```json
{
  "recommendations": [
    "ms-python.python",
    "charliermarsh.ruff",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode"
  ]
}
```

**.vscode/launch.json を作成:**

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["backend.main:app", "--reload", "--port", "8080"],
      "jinja": true
    }
  ]
}
```

---

## 🔮 将来的な検討

### 5. **GitHub Actions CI/CD** (優先度: 低)

**効果**: プルリクエスト時の自動テスト、自動デプロイ

**.github/workflows/ci.yml:**

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run ruff check backend/
      - run: npm install && npm run type-check && npm run lint
```

---

### 6. **Testing Setup** (優先度: 低)

**注意**: YAGNI原則に基づき、テストが本当に必要になるまで導入しない

**バックエンド:**

```bash
uv add --dev pytest pytest-asyncio httpx
```

**フロントエンド:**

```bash
npm install -D vitest @testing-library/dom
```

---

### 7. **Makefile for Task Runner** (優先度: 低)

**効果**: 複雑なコマンドを簡略化

**Makefile:**

```makefile
.PHONY: dev build lint test deploy

dev:
 ./dev.sh

build:
 npm run build
 uv run ruff format backend/

lint:
 uv run ruff check backend/
 npm run lint

test:
 uv run pytest
 npm test

deploy:
 ./deploy.sh
```

**使用法:**

```bash
make dev
make lint
make deploy
```

---

## 📊 推奨度マトリクス

| 提案 | 優先度 | 効果 | 工数 | すぐ導入すべき？ | ステータス |
| ---- | ------ | ---- | ---- | ---------------- | --------- |
| Hot Reload | 高 | ⭐⭐⭐⭐⭐ | 15分 | ✅ はい | ✅ 実装済み |
| Pre-commit Hooks | 高 | ⭐⭐⭐⭐⭐ | 15分 | ✅ はい | ✅ 実装済み |
| Docker Compose | 中 | ⭐⭐⭐ | 30分 | チーム開発なら | - |
| VS Code Settings | 中 | ⭐⭐⭐ | 10分 | チーム開発なら | - |
| GitHub Actions | 低 | ⭐⭐ | 1時間 | リリース後 | - |
| Testing | 低 | ⭐⭐ | 2時間+ | 本当に必要なら | - |
| Makefile | 低 | ⭐⭐ | 20分 | 好みによる | - |

---

## 🚀 実装済み機能の使い方

### Hot Reload

```bash
npm run dev    # 自動ビルド + ブラウザ自動リロード
```

### Pre-commit Hooks

```bash
git commit -m "your message"
# → 自動で ESLint + ruff が実行されます
```

---

## 次のステップ

必要に応じて以下を検討してください：

- **Docker Compose**: チーム開発が始まったら
- **VS Code Settings**: チームで設定を統一したいなら
- **GitHub Actions**: 継続的インテグレーションが必要なら
- **Testing**: テストが本当に必要になったら（YAGNI原則）
