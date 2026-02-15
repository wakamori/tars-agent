# TARS - 協働ロボット空間知能守護システム

<img src="https://img.shields.io/badge/Google_Cloud-4285F4?style=flat&logo=google-cloud&logoColor=white" alt="Google Cloud"/> <img src="https://img.shields.io/badge/Vertex_AI-4285F4?style=flat&logo=google&logoColor=white" alt="Vertex AI"/> <img src="https://img.shields.io/badge/Matter.js-Physics-green" alt="Matter.js"/>

## 概要

TARSは、**空間知能 (Spatial Intelligence)** を活用して、製造現場における人とロボットの協働作業の安全性を向上させるAIシステムです。

Matter.jsによる2D物理シミュレーション上で、Gemini Vision APIが作業環境をリアルタイム分析し、危険を予測して自動的に安全介入を行います。

## 解決する課題

協働ロボット市場は急成長中（年率30%）ですが、以下の課題が存在します：

- **労災リスク**: 人とロボットが同じ空間で作業する際の衝突・挟まれ事故
- **中小企業の導入障壁**: 高価な安全システムが必要で、投資回収が困難
- **予測的安全の欠如**: 既存システムは事故発生後に停止する「事後対応型」

## ソリューション

TARSは以下の技術で予測的安全を実現：

1. **空間認識AI**: Gemini Visionが作業員とロボットの位置・動きを分析
2. **物理シミュレーション**: Matter.jsで危険シナリオを予測
3. **自動介入**: 安全バリア配置、ロボット減速、警告表示を自動実行

## アーキテクチャ

```text
┌─────────────────────────────────────────┐
│  Cloud Run Service                      │
│                                         │
│  ┌─────────────┐    ┌──────────────┐  │
│  │  Frontend   │    │  FastAPI     │  │
│  │  Matter.js  │◄───┤  Backend     │  │
│  │  Physics    │    │  /analyze    │  │
│  └─────────────┘    └──────┬───────┘  │
│                             │           │
│                             ▼           │
│                    ┌──────────────────┐│
│                    │ Vertex AI Gemini ││
│                    │ Vision API       ││
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

1. ブラウザでアプリケーションを開く
2. シミュレーションを開始（作業員が工場フロアを移動）
3. AIが危険を検知すると自動的に安全バリアを配置
4. 「防いだ事故」カウンターで効果を確認

## デモシナリオ

1. **衝突回避**: ロボットアームの動作範囲に作業員が接近 → バリア配置
2. **挟まれ防止**: 可動部品と壁の間に作業員 → ロボット減速
3. **落下物危険**: 不安定な物体の下に作業員 → 警告＋退避誘導

## 機能

- ✅ **自律エージェント**: Generative Agents アーキテクチャによる自己問答・学習
- ✅ **記憶システム**: 重要度ベースの記憶管理とReflection
- ✅ **パターン発見**: 新規パターンの自動検出
- ✅ **物理シミュレーション**: Matter.jsによるリアルタイム衝突予測
- ✅ **型安全**: TypeScript + Pydanticで完全な型保証
- ✅ **コード品質**: ruff + ESLintで自動チェック

## ライセンス

MIT License
