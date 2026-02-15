# TARS - World Model Experiment

<img src="https://img.shields.io/badge/Google_Cloud-4285F4?style=flat&logo=google-cloud&logoColor=white" alt="Google Cloud"/> <img src="https://img.shields.io/badge/Vertex_AI-4285F4?style=flat&logo=google&logoColor=white" alt="Vertex AI"/> <img src="https://img.shields.io/badge/Matter.js-Physics-green" alt="Matter.js"/>

## 概要

TARSは、**物理シミュレーション上でLLMが世界モデルを構築し、物理法則を推論して行動決定を行う**実験システムです。

Matter.jsによる2D物理シミュレーション環境で、Gemini 2.0 Flashが倉庫番タスク（荷物をゴールまで移動）を解き、**Generative Agents**アーキテクチャで過去の経験から学習します。

## コンセプト

### World Model Learning

- **観察**: AIがシミュレーション状態（位置、速度、重力、摩擦）を観察
- **推論**: 物理法則を理解し、次の行動の結果を予測
- **行動**: push（力を加える）、barrier（斜面配置）、wait、observe
- **学習**: 成功/失敗のエピソードを記憶し、リフレクションで戦略を改善

### Generative Agents アーキテクチャ

1. **エピソード記憶**: 各試行の結果をサマリー化して保存
2. **リフレクション**: 複数エピソードから成功パターンと失敗を抽出
3. **記憶ストリーム**: 過去の経験をプロンプトに含めて意思決定を改善

## アーキテクチャ

```text
┌─────────────────────────────────────────┐
│  Cloud Run Service                      │
│                                         │
│  ┌─────────────┐    ┌──────────────┐  │
│  │  Frontend   │    │  FastAPI     │  │
│  │  Matter.js  │◄───┤  Backend     │  │
│  │  Simulation │    │  /api/       │  │
│  └─────────────┘    │  world-model/│  │
│                      └──────┬───────┘  │
│                             │           │
│                             ▼           │
│                    ┌──────────────────┐│
│                    │ Vertex AI Gemini ││
│                    │ 2.0 Flash        ││
│                    └──────────────────┘│
└─────────────────────────────────────────┘
```

## 技術スタック

### バックエンド

- **実行環境**: Google Cloud Run
- **AI**: Vertex AI (Gemini 2.0 Flash)
- **フレームワーク**: FastAPI
- **パッケージ管理**: uv
- **コード品質**: ruff (linter + formatter)

### フロントエンド

- **言語**: TypeScript
- **物理エンジン**: Matter.js
- **ビルドツール**: esbuild
- **コード品質**: ESLint + TypeScript Compiler

## セットアップ

### 前提条件

- Google Cloud プロジェクト
- gcloud CLI インストール済み
- Python 3.11+
- Node.js 20+ (フロントエンドビルド用)
- **uv** (高速Pythonパッケージマネージャー) - [インストール方法](https://github.com/astral-sh/uv)

```bash
# uv のインストール (推奨)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### ローカル開発

> **💡 開発モード**: Google Cloud認証なしでモックAI応答を使用して動作します。
> 実際のGemini AIを使用する場合は、[Google Cloud認証](#google-cloud-認証)を参照してください。

**クイックスタート（最も簡単）：**

```bash
# バックエンド
./dev.sh   # 依存関係のインストール + サーバー起動を自動実行

# フロントエンド (別ターミナル)
cd frontend
npm install        # 初回のみ
npm run dev        # 開発モード：自動ビルド + ブラウザ自動リロード
# または
npm run build      # TypeScriptをビルド
# または
npm run watch      # ファイル変更を監視して自動ビルド
```

> **✨ World Model Experiment**:
> AIが物理法則を学習する倉庫番タスクは
> <http://localhost:8080/> でアクセスできます

**手動での開発：**

```bash
# バックエンド
uv sync                                        # 依存関係をインストール
cd backend && uv run uvicorn main:app --reload --port 8080

# フロントエンド (別ターミナル)
npm install                                    # 初回のみ
npm run build                                  # ビルド

# ブラウザで http://localhost:8080 を開く
```

### 依存関係管理

**バックエンド (Python):**

- **pyproject.toml**: 依存関係の定義（バージョン範囲）
- **uv.lock**: 厳密なバージョン固定（再現可能なビルド用）

```bash
# pyproject.toml を編集してから
uv lock          # uv.lock を更新
uv sync          # インストール
```

**フロントエンド (TypeScript):**

- **package.json**: 依存関係の定義
- **package-lock.json**: バージョン固定

```bash
npm install matter-js        # 依存関係を追加
npm install -D @types/xxx    # 型定義を追加
```

### コード品質チェック

```bash
# バックエンド
uv run ruff check backend/       # Pythonリント
uv run ruff format backend/      # Pythonフォーマット

# フロントエンド
npm run type-check              # TypeScript型チェック
npm run lint                    # ESLint
npm run lint:fix                # ESLint自動修正
```

**Pre-commit Hooks（自動）:**

`git commit` 実行時に自動でリント・フォーマット処理が実行されます：

- TypeScript: ESLint自動修正 + 型チェック
- Python: ruff check --fix + ruff format

### Google Cloud 認証

**ローカル開発**: デフォルトではモックAI応答を使用します（認証不要）。

**実際のGemini AIを使用する場合**:

1. **Google Cloudプロジェクトを作成**
   - [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
   - Vertex AI APIを有効化

2. **認証情報を設定**

   ```bash
   # Application Default Credentialsを設定
   gcloud auth application-default login
   ```

3. **環境変数を設定（恒久的な設定）**

   `.env.example` をコピーして `.env` ファイルを作成：

   ```bash
   cp .env.example .env
   ```

   `.env` ファイルを編集してプロジェクトIDを設定：

   ```bash
   # .env
   GOOGLE_CLOUD_PROJECT=your-actual-project-id
   GOOGLE_CLOUD_LOCATION=asia-northeast1
   ```

   > **注意**: `.env` ファイルは `.gitignore` に含まれているため、GitHubにpushされません。

4. **サーバーを再起動**

   ```bash
   ./dev.sh
   ```

これで実際のGemini 2.5 Flash AIが使用されます。

### Google Cloud デプロイ

```bash
# デプロイスクリプト実行（推奨）
./deploy.sh

# または手動デプロイ
gcloud run deploy tars \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10
```

### コスト管理

#### 無料枠

- **Cloud Build**: 月120分まで無料
- **Cloud Run**: 月2Mリクエスト、36万GB秒まで無料
- **Artifact Registry**: 0.5GBまで無料

#### 課金対策

1. **デプロイ前確認**: `./deploy.sh` は確認プロンプトを表示
2. **ローカルテスト**: `uvicorn backend.main:app --reload` でローカル開発
3. **古いイメージ削除**: 定期的に `./cleanup-images.sh` を実行してストレージ課金削減

```bash
# 古いコンテナイメージを削除（最新3つを保持）
./cleanup-images.sh
```

## 使い方

1. **レベル選択**: tutorial（基礎）、friction（摩擦）、obstacle（壁回避）、barrier（誘導路）から選択
2. **AI開始**: 「AI開始」ボタンでGeminiが自動プレイ開始
3. **観察**: 右側パネルで以下を確認:
   - **観察**: AIが認識した状態（位置、速度、距離）
   - **記憶**: 過去のエピソード記憶
   - **学習**: リフレクション（成功パターン、失敗の教訓）
   - **計画**: 次の行動と推論プロセス
4. **学習プロセス**: 成功/失敗を繰り返しながら戦略を改善

## タスクレベル

1. **Tutorial**: 荷物を右に押してゴールへ（直線移動）
2. **Friction**: 滑りやすい荷物をコントロール
3. **Obstacle**: 壁を避けてゴールへ
4. **Barrier**: バリアで滑り台を作り、安全にゴールへ

## 機能

- ✅ **World Model**: LLMが物理法則を推論して行動決定
- ✅ **Generative Agents**: エピソード記憶＋リフレクションで継続学習
- ✅ **物理シミュレーション**: Matter.jsによる重力・摩擦・反発の再現
- ✅ **エピソード自動リトライ**: 成功/失敗後に自動的に次のエピソード開始
- ✅ **記憶ストリーム**: 過去の経験を活用した意思決定
- ✅ **型安全**: TypeScript + Pydanticで完全な型保証
- ✅ **コード品質**: ruff + ESLintで自動チェック

## ライセンス

MIT License
