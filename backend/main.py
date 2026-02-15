"""
TARS - World Model Experiment
FastAPI Backend with Vertex AI Gemini Integration for Physics-based Task Learning
"""

import asyncio
import os

import vertexai
import world_model
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.api_core import exceptions as api_exceptions
from pydantic import BaseModel, Field
from task import LEVELS
from vertexai.generative_models import GenerativeModel

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="TARS - World Model API", version="2.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")

try:
    vertexai.init(project=PROJECT_ID, location="us-central1")
    model = GenerativeModel("gemini-2.0-flash-exp")
    print(f"✅ Vertex AI initialized: {PROJECT_ID}")
except Exception as e:
    print(f"⚠️  Vertex AI initialization failed: {e}")
    print("ℹ️  Mock responses will be used for AI analysis.")
    model = None

# World Model Memory Stream (Episode-based Memory)
episode_memory = world_model.MemoryStream()
print(f"📚 Memory system initialized: {len(episode_memory.episodes)} memories loaded")


# ==================== Pydantic Models ====================


class WorldModelRequest(BaseModel):
    """World Model行動決定リクエスト"""

    level_key: str = Field(description="レベルキー (tutorial, friction, obstacle, barrier)")
    state: dict = Field(description="現在のシミュレーション状態")
    step: int = Field(description="現在のステップ数")
    previous_actions: list[str] = Field(default=[], description="これまでの行動履歴")


class WorldModelDecisionResponse(BaseModel):
    """World Model行動決定レスポンス"""

    reasoning: str = Field(description="物理的推論と戦略")
    action: dict = Field(description="選択された行動")
    success: bool = Field(default=True, description="処理の成功/失敗")
    error: str = Field(default="", description="エラーメッセージ")


# ==================== Endpoints ====================


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
        "episode_count": len(episode_memory.episodes),
    }


@app.post("/api/world-model/decide", response_model=WorldModelDecisionResponse)
async def world_model_decide(request: WorldModelRequest):
    """
    World Model: 物理シミュレーション状態を分析し、次の行動を決定

    Args:
        request: レベル情報、状態、ステップ数、行動履歴

    Returns:
        WorldModelDecisionResponse with reasoning and action
    """
    try:
        level = LEVELS.get(request.level_key)
        if not level:
            raise HTTPException(status_code=400, detail=f"Invalid level key: {request.level_key}")

        if not model:
            # Fallback to mock response if Vertex AI not available
            print("⚠️  Using default project ID, returning mock response")
            return WorldModelDecisionResponse(
                reasoning="モックレスポンス: Vertex AIが未設定です",
                action={
                    "type": "push",
                    "forceX": 50,
                    "forceY": 0,
                    "duration": 200,
                    "reason": "右に押す（デフォルト動作）",
                },
            )

        # Call world model to analyze and decide with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await world_model.analyze_and_decide(
                    level=level,
                    level_key=request.level_key,
                    state=request.state,
                    step=request.step,
                    previous_actions=request.previous_actions,
                    gemini_model=model,
                    memory_stream=episode_memory,
                )

                return WorldModelDecisionResponse(
                    reasoning=response.reasoning,
                    action=response.action.model_dump(by_alias=True),
                )
            except api_exceptions.ResourceExhausted:
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                    print(
                        f"⏳ Quota exceeded, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Quota exceeded after {max_retries} attempts")
                    raise

    except Exception as e:
        print(f"❌ World Model decision error: {e}")
        import traceback

        traceback.print_exc()

        return WorldModelDecisionResponse(
            reasoning=f"エラーが発生しました: {str(e)}",
            action={
                "type": "push",
                "forceX": 0,
                "forceY": 0,
                "duration": 100,
                "reason": "エラーのため待機",
            },
            success=False,
            error=str(e),
        )


@app.post("/api/world-model/episode-complete")
async def episode_complete(request: dict):
    """
    エピソード完了時に呼ばれるエンドポイント
    エピソードの結果をメモリに追加
    """
    try:
        level = LEVELS.get(request["level_key"])
        if not level:
            raise HTTPException(
                status_code=400, detail=f"Invalid level key: {request['level_key']}"
            )

        state = request["state"]
        actions_taken = request.get("actions_taken", [])

        # ゴールまでの最終距離を計算
        box_pos = state["box"]["position"]
        goal_pos = state["goal"]["position"]
        dx = goal_pos["x"] - box_pos["x"]
        dy = goal_pos["y"] - box_pos["y"]
        final_distance = (dx**2 + dy**2) ** 0.5

        # メモリに追加
        episode = episode_memory.add_episode(
            level_key=request["level_key"],
            level_name=level.name,
            success=state.get("isSuccess", False),
            steps=state.get("step", 0),
            elapsed_time=state.get("elapsedTime", 0),
            reward=request.get("reward", 0),
            actions_taken=actions_taken,
            final_distance=final_distance,
        )

        # リフレクションを取得
        reflection = episode_memory.get_reflection(request["level_key"])

        return {
            "success": True,
            "episode_id": episode.episode_id,
            "summary": episode.summary,
            "key_insight": episode.key_insight,
            "reflection": reflection.model_dump() if reflection else None,
            "stats": episode_memory.get_stats(),
        }

    except Exception as e:
        print(f"❌ Episode complete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/world-model/memory")
async def get_world_model_memory(level_key: str = None):
    """World Modelのメモリストリームを取得"""
    if level_key:
        return {
            "level_key": level_key,
            "reflection": (
                episode_memory.get_reflection(level_key).model_dump()
                if episode_memory.get_reflection(level_key)
                else None
            ),
            "recent_episodes": [
                ep.model_dump() for ep in episode_memory.get_recent_episodes(level_key, limit=5)
            ],
        }
    else:
        return {
            "stats": episode_memory.get_stats(),
            "all_episodes": [ep.model_dump() for ep in episode_memory.episodes[-10:]],
            "reflections": {
                key: refl.model_dump() for key, refl in episode_memory.reflections.items()
            },
        }


# Mount static files
app.mount("/dist", StaticFiles(directory="../frontend/dist"), name="dist")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
