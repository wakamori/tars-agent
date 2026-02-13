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
    title="TARS API",
    description="協働ロボット空間知能守護システム",
    version="1.0.0"
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
SYSTEM_PROMPT = """あなたは工場の安全管理AIです。画像を分析し、作業員とロボットの安全リスクを評価してください。

画像内の以下の要素を検出してください：
- 作業員（青い円形 or 人型）
- 協働ロボット（赤い/オレンジの四角形）
- 障害物（灰色の静的オブジェクト）
- 危険エリア（床の色が異なる部分）

以下のJSON形式で応答してください：
{
  "entities": [
    {
      "type": "worker" | "robot" | "obstacle" | "hazard",
      "bbox": [x1, y1, x2, y2],
      "risk_level": 0-100,
      "movement": "static" | "moving_slow" | "moving_fast"
    }
  ],
  "warnings": ["危険な状況の説明"],
  "interventions": [
    {
      "type": "barrier" | "slowdown" | "alert",
      "position": [x, y],
      "reason": "介入の理由"
    }
  ],
  "confidence": 0.0-1.0
}

座標は画像の左上を(0,0)、右下を(1,1)とした正規化座標で表現してください。
risk_levelは衝突の危険度を0-100で評価してください（100が最も危険）。
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
        "project_id": PROJECT_ID
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
            detail="Vertex AI not initialized. Check GOOGLE_CLOUD_PROJECT env variable."
        )
    
    try:
        # Read image file
        image_bytes = await file.read()
        
        # Create prompt with image
        image_part = Part.from_data(
            data=image_bytes,
            mime_type=file.content_type or "image/png"
        )
        
        # Call Gemini Vision
        response = model.generate_content(
            [image_part, SYSTEM_PROMPT],
            generation_config=GenerationConfig(
                temperature=0.1,  # Low temperature for consistent output
                max_output_tokens=2048,
            )
        )
        
        # Parse response
        response_text = response.text.strip()
        
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
                confidence=0.0
            )
        
        # Validate and return
        return AnalysisResponse(**analysis_data)
        
    except Exception as e:
        import traceback
        error_detail = f"分析エラー: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


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
                movement="moving_slow"
            ),
            Entity(
                type="robot",
                bbox=[0.6, 0.4, 0.7, 0.55],
                risk_level=80,
                movement="moving_fast"
            )
        ],
        warnings=[
            "作業員がロボットの動作範囲に接近しています",
            "衝突の危険性: 高"
        ],
        interventions=[
            {
                "type": "barrier",
                "position": [0.45, 0.5],
                "reason": "作業員とロボットの間に安全バリアを配置"
            }
        ],
        confidence=0.85
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
                movement="moving_slow"
            ),
            Entity(
                type="robot",
                bbox=[0.6, 0.4, 0.7, 0.55],
                risk_level=80,
                movement="moving_fast"
            )
        ],
        warnings=[
            "作業員がロボットの動作範囲に接近しています",
            "衝突の危険性: 高"
        ],
        interventions=[
            {
                "type": "barrier",
                "position": [0.45, 0.5],
                "reason": "作業員とロボットの間に安全バリアを配置"
            }
        ],
        confidence=0.85
    )


# Mount static files (CSS, JS)
app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
