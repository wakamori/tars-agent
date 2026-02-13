# TARS セットアップガイド

## 🚀 クイックスタート

### 1. Google Cloud プロジェクトの設定

```bash
# gcloud CLIにログイン
gcloud auth login

# プロジェクトを作成（まだない場合）
gcloud projects create YOUR_PROJECT_ID --name="TARS"

# プロジェクトを設定
gcloud config set project YOUR_PROJECT_ID

# 必要なAPIを有効化
gcloud services enable aiplatform.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 2. ローカルでテスト（オプション）

```bash
# バックエンドディレクトリに移動
cd backend

# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=asia-northeast1

# サーバーを起動
uvicorn main:app --reload --port 8080
```

ブラウザで `http://localhost:8080` を開いてテストしてください。

### 3. Google Cloud Run にデプロイ

#### 方法A: デプロイスクリプト使用（推奨）

```bash
# プロジェクトルートから実行
./deploy.sh
```

#### 方法B: 手動デプロイ

```bash
gcloud run deploy tars \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=asia-northeast1"
```

デプロイが完了すると、URLが表示されます。

## 🧪 動作確認

1. デプロイされたURLをブラウザで開く
2. 「▶ 開始」ボタンをクリックしてシミュレーションを開始
3. 作業員（青い円）とロボット（赤い四角）が動き出す
4. 「🧠 AI分析」ボタンをクリック
5. Gemini Vision APIが画像を分析し、危険を検知すると安全バリア（緑の長方形）が配置される

## 📊 機能概要

### フロントエンド (Matter.js)
- 2D物理演算シミュレーション
- 作業員とロボットの自動移動
- Canvas画像キャプチャ
- リアルタイムUI更新

### バックエンド (FastAPI)
- `/analyze` エンドポイント: Gemini Vision分析
- `/mock-analyze` エンドポイント: テスト用モックデータ
- `/health` エンドポイント: ヘルスチェック

### AI (Vertex AI)
- Gemini 2.0 Flash: 高速な画像認識
- 座標検出、リスク評価、介入提案
- JSON形式の構造化出力

## 🐛 トラブルシューティング

### エラー: "Vertex AI not initialized"

環境変数が設定されていません。

```bash
# ローカルの場合
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID

# Cloud Runの場合（再デプロイ時に設定）
--set-env-vars "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID"
```

### エラー: "API not enabled"

必要なAPIを有効化してください：

```bash
gcloud services enable aiplatform.googleapis.com
```

### デプロイが遅い

初回デプロイは5-10分かかることがあります。コンテナイメージのビルドに時間がかかります。

### AI分析が失敗する

1. `GOOGLE_CLOUD_PROJECT` が正しく設定されているか確認
2. Vertex AI APIが有効化されているか確認
3. `/mock-analyze` エンドポイントでテスト（モックデータを返す）

## 💰 コスト見積もり

### 無料枠での利用
- Cloud Run: 月200万リクエストまで無料
- Vertex AI Gemini: 月間無料クォータあり（詳細はGoogle Cloudコンソールで確認）

### 注意事項
- `--min-instances 0` に設定することで、使用していない時はコストゼロ
- デモ後は不要なサービスを削除することを推奨

## 📝 次のステップ

### Phase 2への拡張案
1. **プロンプト最適化**: 座標抽出精度の向上
2. **複数シナリオ**: 様々な危険パターンの追加
3. **統計ダッシュボード**: 時系列データの可視化
4. **WebSocket対応**: リアルタイムストリーミング分析
5. **モバイル対応**: レスポンシブデザイン

### ハッカソン提出用
1. デモ動画を録画（3分、3つのシナリオを見せる）
2. Zenn記事を執筆（課題、ソリューション、アーキテクチャ）
3. GitHubリポジトリを公開設定に
4. README.mdに使い方とデモURLを記載

## 📚 参考資料

- [Vertex AI Gemini Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Matter.js Documentation](https://brm.io/matter-js/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🎯 成功の定義

✅ Cloud Runにデプロイ成功
✅ Gemini Vision APIが画像を分析できる
✅ Matter.jsシミュレーションが動作
✅ 安全バリアが自動で配置される
✅ 3つの異なるシナリオで動作確認

---

質問があれば、GitHubのIssuesまたはDiscordで！
