"""
TARS - 協働ロボット空間知能守護システム
FastAPI Backend with Vertex AI Gemini Integration
"""

import json
import os
from typing import Any, Dict, List

import vertexai
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from vertexai.generative_models import GenerationConfig, GenerativeModel, Part

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-northeast1")
MODEL_NAME = "gemini-2.5-flash"  # Latest stable Gemini 2.5 Flash model

# Initialize Vertex AI
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = GenerativeModel(MODEL_NAME)
    print(f"✅ Vertex AI initialized: {PROJECT_ID} / {LOCATION}")
except Exception as e:
    print(f"⚠️  Vertex AI initialization failed: {e}")
    model = None


# FastAPI app
app = FastAPI(
    title="TARS API", description="協働ロボット空間知能守護システム", version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class Entity(BaseModel):
    type: str  # "worker", "robot", "obstacle", "hazard"
    bbox: List[float]  # [x1, y1, x2, y2] normalized 0-1
    risk_level: int  # 0-100
    movement: str  # "static", "moving_slow", "moving_fast"


class AnalysisResponse(BaseModel):
    entities: List[Entity]
    warnings: List[str]
    interventions: List[Dict[str, Any]]
    confidence: float


# System prompt for Gemini
SYSTEM_PROMPT = """あなたは工場の安全管理AIアシスタントです。
協働ロボットと作業員が同じ空間で作業する製造現場の画像を分析し、安全リスクを評価してください。

## 検出対象：
- **作業員（worker）**: 青色の円形オブジェクト。人間の作業者を表現しています。
- **協働ロボット（robot）**: 赤色または濃いピンク色の矩形オブジェクト。産業用ロボットアームを表現しています。
- **障害物（obstacle）**: 灰色の静的オブジェクト。機械、壁、設備などを表現します。
- **危険エリア（hazard）**: 床面の色が異なる領域。立入禁止エリアや危険ゾーンを表現します。

## 安全リスク評価基準：
1. **衝突リスク**: 作業員とロボットの距離が近い（画像の10%以内）
2. **挟まれリスク**: 作業員が障害物とロボットの間にいる
3. **動線交差**: 移動中の作業員とロボットの経路が交差する
4. **危険エリア侵入**: 作業員が危険エリアに接近・侵入している

## 応答形式：
以下のJSON形式で応答してください（マークダウンのコードブロックは不要です）：

{
  "entities": [
    {
      "type": "worker" | "robot" | "obstacle" | "hazard",
      "bbox": [x1, y1, x2, y2],
      "risk_level": 0-100,
      "movement": "static" | "moving_slow" | "moving_fast"
    }
  ],
  "warnings": ["具体的な危険状況の説明"],
  "interventions": [
    {
      "type": "barrier" | "slowdown" | "alert",
      "position": [x, y],
      "reason": "介入が必要な理由"
    }
  ],
  "confidence": 0.0-1.0
}

## 座標系の説明：
- bbox（バウンディングボックス）: [x1, y1, x2, y2] 形式
- position（介入位置）: [x, y] 形式
- すべての座標は正規化座標（0.0〜1.0）を使用
- 画像の左上が (0, 0)、右下が (1, 1)
- 例: 画像中央は [0.5, 0.5]

## risk_levelの評価基準：
- 0-30: 低リスク（十分な距離がある）
- 31-60: 中リスク（注意が必要）
- 61-85: 高リスク（介入を推奨）
- 86-100: 緊急（即座に介入が必要）

## interventionsの種類：
- **barrier**: 作業員とロボットの間に安全バリアを配置（緑色の壁として表示）
- **slowdown**: ロボットの動作速度を減速
- **alert**: 作業員に警告を表示

できるだけ具体的で実用的な安全介入を提案してください。
"""


@app.get("/")
async def root():
    """Serve frontend HTML"""
    return FileResponse("../frontend/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "vertex_ai": "connected" if model else "disconnected",
        "project_id": PROJECT_ID,
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_frame(file: UploadFile = File(...)):
    """
    Analyze factory floor image with Gemini Vision

    Args:
        file: Screenshot from Matter.js canvas (PNG/JPEG)

    Returns:
        Analysis with detected entities, warnings, and interventions
    """

    if not model:
        raise HTTPException(
            status_code=503,
            detail="Vertex AI not initialized. Check GOOGLE_CLOUD_PROJECT env variable.",
        )

    try:
        # Read image file
        image_bytes = await file.read()

        # Create prompt with image
        image_part = Part.from_data(
            data=image_bytes, mime_type=file.content_type or "image/png"
        )

        # Call Gemini Vision
        response = model.generate_content(
            [image_part, SYSTEM_PROMPT],
            generation_config=GenerationConfig(
                temperature=0.1,  # Low temperature for consistent output
                max_output_tokens=16384,  # Gemini 2.5 Flash supports up to 65,535
                response_mime_type="application/json",  # Force JSON response
            ),
        )

        # Check finish reason
        if response.candidates and response.candidates[0].finish_reason:
            finish_reason = str(response.candidates[0].finish_reason)
            if "MAX_TOKENS" in finish_reason or "SAFETY" in finish_reason:
                print(f"⚠️  Response incomplete: {finish_reason}")
                return AnalysisResponse(
                    entities=[],
                    warnings=[f"AI応答が不完全です: {finish_reason}"],
                    interventions=[],
                    confidence=0.0,
                )

        # Parse response
        try:
            response_text = response.text.strip()
        except (ValueError, AttributeError) as e:
            print(f"⚠️  Cannot extract text from response: {e}")
            print(f"Response: {response}")
            return AnalysisResponse(
                entities=[],
                warnings=["AI応答の取得に失敗しました"],
                interventions=[],
                confidence=0.0,
            )

        # Extract JSON from markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        # Parse JSON
        try:
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            # Fallback: return error with raw response for debugging
            print(f"JSON Parse Error: {e}")
            print(f"Raw response: {response_text}")

            return AnalysisResponse(
                entities=[],
                warnings=[f"AI応答の解析に失敗: {str(e)}"],
                interventions=[],
                confidence=0.0,
            )

        # Validate and return
        return AnalysisResponse(**analysis_data)

    except Exception as e:
        import traceback

        error_detail = f"分析エラー: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/mock-analyze")
async def mock_analyze_get():
    """
    Mock analysis endpoint for testing without Vertex AI (GET version)
    Returns dummy data for development
    """
    return AnalysisResponse(
        entities=[
            Entity(
                type="worker",
                bbox=[0.3, 0.5, 0.35, 0.6],
                risk_level=75,
                movement="moving_slow",
            ),
            Entity(
                type="robot",
                bbox=[0.6, 0.4, 0.7, 0.55],
                risk_level=80,
                movement="moving_fast",
            ),
        ],
        warnings=["作業員がロボットの動作範囲に接近しています", "衝突の危険性: 高"],
        interventions=[
            {
                "type": "barrier",
                "position": [0.45, 0.5],
                "reason": "作業員とロボットの間に安全バリアを配置",
            }
        ],
        confidence=0.85,
    )


@app.post("/mock-analyze", response_model=AnalysisResponse)
async def mock_analyze(file: UploadFile = File(None)):
    """
    Mock analysis endpoint for testing without Vertex AI
    Returns dummy data for development
    """
    # File parameter is optional for mock
    return AnalysisResponse(
        entities=[
            Entity(
                type="worker",
                bbox=[0.3, 0.5, 0.35, 0.6],
                risk_level=75,
                movement="moving_slow",
            ),
            Entity(
                type="robot",
                bbox=[0.6, 0.4, 0.7, 0.55],
                risk_level=80,
                movement="moving_fast",
            ),
        ],
        warnings=["作業員がロボットの動作範囲に接近しています", "衝突の危険性: 高"],
        interventions=[
            {
                "type": "barrier",
                "position": [0.45, 0.5],
                "reason": "作業員とロボットの間に安全バリアを配置",
            }
        ],
        confidence=0.85,
    )


# Mount static files (CSS, JS)
app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
