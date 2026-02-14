"""
TARS - 協働ロボット空間知能守護システム
FastAPI Backend with Vertex AI Gemini Integration + Generative Agent Architecture
"""

import json
import os
from typing import List

import vertexai
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import memory system
from memory import REFLECTION_PROMPT_TEMPLATE, MemorySystem
from pydantic import BaseModel, Field
from vertexai.generative_models import GenerationConfig, GenerativeModel, Part


# Helper function to flatten Pydantic v2 schema for Vertex AI compatibility
def flatten_schema(schema: dict) -> dict:
    """
    Flatten Pydantic v2 JSON schema by inlining $defs.
    Vertex AI Schema doesn't support $defs field from JSON Schema 2020-12.
    """
    if "$defs" not in schema:
        return schema
    
    defs = schema.pop("$defs")
    
    def replace_refs(obj):
        if isinstance(obj, dict):
            # If this is a $ref, replace it with the actual definition
            if "$ref" in obj:
                ref_path = obj["$ref"]
                ref_name = ref_path.split("/")[-1]
                if ref_name in defs:
                    # Return a copy of the definition (recursively process it too)
                    return replace_refs(defs[ref_name].copy())
            # Recursively process all dict values
            return {k: replace_refs(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            # Recursively process list items
            return [replace_refs(item) for item in obj]
        return obj
    
    return replace_refs(schema)


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

# Initialize Memory System
memory_system = MemorySystem(memory_file="data/memory_stream.json")


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


# ============================================================================
# Pydantic Models for Autonomous Agent Response (Structured Output)
# ============================================================================

class AccidentScenario(BaseModel):
    """事故シナリオの詳細"""
    scenario: str = Field(description="事故シナリオの説明")
    probability: float = Field(ge=0.0, le=1.0, description="発生確率")
    severity: int = Field(ge=1, le=10, description="深刻度")
    reasoning: str = Field(description="なぜこのシナリオが起こりうるか")


class SelfInquiry(BaseModel):
    """エージェントの自己質問プロセス"""
    observations: List[str] = Field(description="環境の観察内容")
    memory_connections: List[str] = Field(description="過去の記憶との関連")
    accident_scenarios: List[AccidentScenario] = Field(description="想定される事故シナリオ")
    causal_analysis: str = Field(description="因果関係の分析")


class Entity(BaseModel):
    """検出されたエンティティ"""
    type: str = Field(description="エンティティのタイプ: worker, robot, obstacle, hazard")
    bbox: List[float] = Field(description="バウンディングボックス [x1, y1, x2, y2] 正規化座標")
    description: str = Field(description="エンティティの説明")
    risk_level: int = Field(ge=0, le=100, description="リスクレベル")
    movement: str = Field(description="移動状態: static, moving_slow, moving_fast")


class DiscoveredPattern(BaseModel):
    """発見された安全パターン"""
    pattern_name: str = Field(description="パターンの名前")
    description: str = Field(description="パターンの説明")
    indicators: List[str] = Field(description="検出指標")
    is_novel: bool = Field(description="新規発見かどうか")


class InterventionAction(BaseModel):
    """介入アクション"""
    type: str = Field(description="アクションタイプ: barrier, alert, slowdown, evacuation, monitoring")
    position: List[float] = Field(description="介入位置 [x, y]")
    reasoning: str = Field(description="なぜこの介入が最適か")
    expected_outcome: str = Field(description="期待される結果")


class InterventionDecision(BaseModel):
    """介入判断"""
    priority: int = Field(ge=1, le=10, description="優先度")
    primary_action: InterventionAction = Field(description="主要アクション")
    alternative_actions: List[InterventionAction] = Field(description="代替アクション")


class AgentResponse(BaseModel):
    """エージェントの完全な応答（Structured Output）"""
    self_inquiry: SelfInquiry = Field(description="自己質問プロセス")
    entities: List[Entity] = Field(description="検出されたエンティティ")
    discovered_patterns: List[DiscoveredPattern] = Field(description="発見されたパターン")
    intervention_decision: InterventionDecision = Field(description="介入判断")
    confidence: float = Field(ge=0.0, le=1.0, description="信頼度")
    learning_note: str = Field(description="この観察から学んだこと")


# ============================================================================
# Self-Ask Prompt Template for Autonomous Agent
# ============================================================================

AGENT_PROMPT_TEMPLATE = """あなたはTARS - 自律的な工場安全エージェントです。

{memory_context}

## 現在の環境
画像を確認し、以下の質問に自分で答えながら分析してください。

### 視覚情報の理解
- **作業員（worker）**: 青色の円形オブジェクト
- **協働ロボット（robot）**: 赤色または濃いピンク色の矩形オブジェクト  
- **障害物（obstacle）**: 灰色の静的オブジェクト
- **危険エリア（hazard）**: 色が異なる床面領域

### 自己質問プロセス（7つの質問に答えてください）

**Q1: この環境で何が起きているか？（観察）**
→ 作業員、ロボット、障害物の位置と動きを観察

**Q2: 過去の経験と比較して、似た状況はあったか？**
→ 記憶を振り返り、類似パターンを探す

**Q3: 現在の状況からどのような事故シナリオが考えられるか？（複数）**
→ 可能性のある危険シナリオを列挙

**Q4: 各シナリオの発生確率と深刻度は？**
→ 確率（0-1）と深刻度（1-10）を評価

**Q5: なぜそれが危険なのか？（因果関係）**
→ 物理的・論理的な因果関係を説明

**Q6: どう介入すべきか？優先順位は？**
→ 最適なアクションと代替案を考える

**Q7: この観察から何を学んだか？**
→ 次回に活かせる知見を抽出

### 最終判断
上記の自己質問の結果を踏まえ、以下のJSON構造で応答してください：

{{
  "self_inquiry": {{
    "observations": ["観察1", "観察2", ...],
    "memory_connections": ["過去の類似ケース1", ...],
    "accident_scenarios": [
      {{
        "scenario": "シナリオ説明",
        "probability": 0.0-1.0,
        "severity": 1-10,
        "reasoning": "なぜこのシナリオが起こりうるか"
      }}
    ],
    "causal_analysis": "因果関係の詳細な説明"
  }},
  "entities": [
    {{
      "type": "worker" | "robot" | "obstacle" | "hazard",
      "bbox": [x1, y1, x2, y2],
      "description": "何が見えるか",
      "risk_level": 0-100,
      "movement": "static" | "moving_slow" | "moving_fast"
    }}
  ],
  "discovered_patterns": [
    {{
      "pattern_name": "自分で命名した危険パターン",
      "description": "パターンの説明",
      "indicators": ["検出方法1", "検出方法2"],
      "is_novel": true
    }}
  ],
  "intervention_decision": {{
    "priority": 1-10,
    "primary_action": {{
      "type": "barrier" | "alert" | "slowdown" | "evacuation" | "monitoring",
      "position": [x, y],
      "reasoning": "なぜこの介入が最適か",
      "expected_outcome": "期待される結果"
    }},
    "alternative_actions": [
      {{"type": "...", "position": [...], "reasoning": "...", "expected_outcome": "..."}}
    ]
  }},
  "confidence": 0.0-1.0,
  "learning_note": "この観察から学んだこと（記憶に追加される）"
}}

## 重要な指針
1. **自律性**: 過去に見たことのない危険パターンを積極的に発見してください
2. **推論**: 「なぜ」を常に問い、論理的に説明してください
3. **記憶活用**: 過去の経験を参照し、学習を示してください
4. **創造性**: 固定概念にとらわれず、新しい安全介入を提案してください
5. **不確実性**: 確信が持てない場合は confidence を下げてください

座標系: 正規化座標 (0,0) = 左上、(1,1) = 右下
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
        "memory_stats": memory_system.get_stats()
    }


@app.post("/analyze", response_model=AgentResponse)
async def analyze_frame(file: UploadFile = File(...)):
    """
    Autonomous Agent Analysis with Gemini Vision + Memory System
    
    Args:
        file: Screenshot from Matter.js canvas (PNG/JPEG)
        
    Returns:
        AgentResponse with self-inquiry, entities, discovered patterns, and intervention plan
    """
    
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Vertex AI not initialized. Check GOOGLE_CLOUD_PROJECT env variable."
        )
    
    try:
        # Read image file
        image_bytes = await file.read()
        
        # Get memory context for prompt
        memory_context = memory_system.get_context(n_recent=3, n_important=2)
        
        # Create agent prompt with memory
        agent_prompt = AGENT_PROMPT_TEMPLATE.format(memory_context=memory_context)
        
        # Create image part
        image_part = Part.from_data(
            data=image_bytes,
            mime_type=file.content_type or "image/png"
        )
        
        print(f"🤖 Agent analyzing with {len(memory_system.memories)} memories...")
        
        # Call Gemini Vision with Structured Output
        # Use flattened schema to avoid $defs (not supported by Vertex AI Schema)
        flattened_schema = flatten_schema(AgentResponse.model_json_schema())
        
        response = model.generate_content(
            [image_part, agent_prompt],
            generation_config=GenerationConfig(
                temperature=0.3,  # Some creativity for autonomous discovery
                max_output_tokens=16384,
                response_mime_type="application/json",
                response_schema=flattened_schema
            )
        )
        
        # Check finish reason before accessing text
        if response.candidates:
            candidate = response.candidates[0]
            finish_reason_str = str(candidate.finish_reason)
            
            print(f"🔍 Finish reason: {finish_reason_str}")
            
            if "MAX_TOKENS" in finish_reason_str:
                print("⚠️  Response truncated due to MAX_TOKENS")
                # Return fallback response
                return _create_fallback_response(
                    "AI応答がトークン制限により切り詰められました"
                )
            elif "SAFETY" in finish_reason_str:
                print("⚠️  Response blocked by safety filters")
                return _create_fallback_response(
                    "AI応答が安全フィルタによりブロックされました"
                )
        
        # Parse response with structured output
        try:
            response_text = response.text.strip()
            print(f"📝 Response length: {len(response_text)} chars")
            
            # Parse JSON
            analysis_data = json.loads(response_text)
            agent_response = AgentResponse(**analysis_data)
            
        except (ValueError, AttributeError, json.JSONDecodeError) as e:
            print(f"⚠️  Parse error: {e}")
            print(f"Raw response: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
            return _create_fallback_response(f"AI応答の解析に失敗: {str(e)}")
        
        # Save to memory system
        observation_summary = " / ".join(agent_response.self_inquiry.observations[:2])
        action = agent_response.intervention_decision.primary_action
        outcome = f"Priority {agent_response.intervention_decision.priority} intervention"
        
        # Calculate importance based on priority and confidence
        importance = min(
            int(agent_response.intervention_decision.priority * agent_response.confidence),
            10
        )
        
        memory_system.add_memory(
            observation=observation_summary,
            action={
                "type": action.type,
                "position": action.position,
                "reasoning": action.reasoning
            },
            outcome=outcome,
            importance=importance,
            learning_note=agent_response.learning_note
        )
        
        print(f"✅ Analysis complete (confidence: {agent_response.confidence:.2f})")
        
        # Trigger reflection if needed
        if len(memory_system.memories) % 10 == 0:
            memory_system.generate_reflection(model, REFLECTION_PROMPT_TEMPLATE)
        
        return agent_response
        
    except Exception as e:
        import traceback
        error_detail = f"分析エラー: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=error_detail)


def _create_fallback_response(warning_message: str) -> AgentResponse:
    """Create a fallback response when AI analysis fails"""
    return AgentResponse(
        self_inquiry=SelfInquiry(
            observations=["エラーが発生しました"],
            memory_connections=[],
            accident_scenarios=[],
            causal_analysis=warning_message
        ),
        entities=[],
        discovered_patterns=[],
        intervention_decision=InterventionDecision(
            priority=5,
            primary_action=InterventionAction(
                type="monitoring",
                position=[0.5, 0.5],
                reasoning="エラーのため監視モードに移行",
                expected_outcome="状況を監視"
            ),
            alternative_actions=[]
        ),
        confidence=0.0,
        learning_note="エラーが発生しました"
    )


@app.get("/mock-analyze", response_model=AgentResponse)
async def mock_analyze_get():
    """
    Mock analysis endpoint for testing without Vertex AI (GET version)
    Returns dummy autonomous agent data for development
    """
    return AgentResponse(
        self_inquiry=SelfInquiry(
            observations=[
                "作業員（青い円）が画面左側を移動中",
                "ロボット（赤い矩形）が画面右側で高速移動",
                "作業員とロボットの距離が急速に縮まっている"
            ],
            memory_connections=[
                "過去に類似した接近パターンで衝突リスクが発生した"
            ],
            accident_scenarios=[
                AccidentScenario(
                    scenario="作業員とロボットの正面衝突",
                    probability=0.75,
                    severity=9,
                    reasoning="移動速度と方向から、2秒以内に衝突経路が交差する"
                ),
                AccidentScenario(
                    scenario="作業員の緊急回避による転倒",
                    probability=0.45,
                    severity=6,
                    reasoning="ロボットに気づいて急停止した場合の二次リスク"
                )
            ],
            causal_analysis="作業員の移動経路とロボットの動作範囲が重複しており、双方が相手の存在を認識していない可能性が高い"
        ),
        entities=[
            Entity(
                type="worker",
                bbox=[0.3, 0.5, 0.35, 0.6],
                description="青い円形オブジェクト、左から右へ移動中",
                risk_level=75,
                movement="moving_slow"
            ),
            Entity(
                type="robot",
                bbox=[0.6, 0.4, 0.7, 0.55],
                description="赤い矩形オブジェクト、高速で動作中",
                risk_level=85,
                movement="moving_fast"
            )
        ],
        discovered_patterns=[
            DiscoveredPattern(
                pattern_name="交差動線衝突リスク",
                description="移動中の作業員とロボットの進行方向が交差する危険パターン",
                indicators=[
                    "作業員とロボットの移動ベクトルが交差",
                    "相対速度が基準値を超過",
                    "視界外からの接近"
                ],
                is_novel=True
            )
        ],
        intervention_decision=InterventionDecision(
            priority=9,
            primary_action=InterventionAction(
                type="barrier",
                position=[0.45, 0.5],
                reasoning="作業員とロボットの間に緊急バリアを配置して衝突を物理的に防止する",
                expected_outcome="衝突を確実に防ぎ、作業員の安全を確保"
            ),
            alternative_actions=[
                InterventionAction(
                    type="alert",
                    position=[0.3, 0.5],
                    reasoning="作業員に視覚・音声警告を発する",
                    expected_outcome="作業員が自主的に回避行動を取る"
                ),
                InterventionAction(
                    type="slowdown",
                    position=[0.6, 0.4],
                    reasoning="ロボットの動作速度を50%に減速",
                    expected_outcome="衝突時の衝撃を軽減"
                )
            ]
        ),
        confidence=0.85,
        learning_note="交差動線パターンは過去のデータでも高リスク。バリア介入が最も効果的であることを確認"
    )


@app.post("/mock-analyze", response_model=AgentResponse)
async def mock_analyze(file: UploadFile = File(None)):
    """
    Mock analysis endpoint for testing without Vertex AI
    Returns dummy autonomous agent data for development
    """
    # File parameter is optional for mock
    return await mock_analyze_get()


@app.get("/memory")
async def get_memory_stream():
    """Get memory stream and reflections"""
    return {
        "memories": memory_system.retrieve_recent(10),
        "reflections": memory_system.reflections[-5:] if memory_system.reflections else [],
        "stats": memory_system.get_stats()
    }


@app.delete("/memory")
async def clear_memory():
    """Clear all memories (for debugging)"""
    memory_system.clear()
    return {"status": "Memory cleared"}


# Mount static files (CSS, JS)
app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
