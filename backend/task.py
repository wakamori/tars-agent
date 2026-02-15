"""
Task Configuration for World Model Experiment

レベル設定とデータモデル
"""

from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, Field

# ==================== Data Models ====================


class TaskLevel(StrEnum):
    """タスクレベル"""

    TUTORIAL = "tutorial"
    FRICTION = "friction"
    OBSTACLE = "obstacle"
    BARRIER = "barrier"


class ActionType(StrEnum):
    """行動タイプ"""

    PUSH = "push"
    BARRIER = "barrier"
    WAIT = "wait"
    OBSERVE = "observe"


class Point(BaseModel):
    """2D座標"""

    x: float
    y: float


class Velocity(BaseModel):
    """速度ベクトル"""

    x: float
    y: float


class BoxState(BaseModel):
    """荷物の状態"""

    position: Point
    velocity: Velocity
    mass: float
    friction: float
    restitution: float


class GoalState(BaseModel):
    """ゴールの状態"""

    position: Point
    radius: float = 30.0


class Action(BaseModel):
    """エージェントの行動"""

    type: ActionType
    force_x: float | None = Field(None, alias="forceX")
    force_y: float | None = Field(None, alias="forceY")
    duration: float | None = None
    x: float | None = None
    y: float | None = None
    angle: float | None = None
    reason: str | None = None
    focus: str | None = None

    class Config:
        populate_by_name = True  # Accept both snake_case and camelCase


class SimulationState(BaseModel):
    """シミュレーション状態"""

    box: BoxState
    goal: GoalState
    barriers: list[dict] = Field(default_factory=list)
    step: int = 0
    elapsed_time: float = 0.0
    actions_taken: list[Action] = Field(default_factory=list)


# ==================== Level Configuration ====================


@dataclass
class LevelConfig:
    """レベル設定"""

    name: str
    description: str
    box_position: Point
    goal_position: Point
    box_mass: float = 10.0
    friction: float = 0.5
    restitution: float = 0.3
    time_limit: float = 30.0
    max_steps: int = 50
    available_barriers: int = 0
    obstacles: list[dict] = field(default_factory=list)


# 事前定義レベル
LEVELS = {
    TaskLevel.TUTORIAL: LevelConfig(
        name="基礎：直線移動",
        description="荷物を右に押してゴールへ",
        box_position=Point(x=200, y=300),
        goal_position=Point(x=600, y=300),
        box_mass=10.0,
        friction=0.5,
        time_limit=60.0,
        max_steps=20,
    ),
    TaskLevel.FRICTION: LevelConfig(
        name="物理：摩擦係数",
        description="滑りやすい荷物をコントロール",
        box_position=Point(x=200, y=300),
        goal_position=Point(x=600, y=300),
        box_mass=10.0,
        friction=0.1,  # 非常に滑る
        time_limit=80.0,
        max_steps=30,
    ),
    TaskLevel.OBSTACLE: LevelConfig(
        name="障害：壁の回避",
        description="壁を避けてゴールへ",
        box_position=Point(x=200, y=300),
        goal_position=Point(x=600, y=300),
        box_mass=10.0,
        friction=0.5,
        time_limit=100.0,
        max_steps=40,
        obstacles=[{"type": "wall", "x": 400, "y": 200, "width": 20, "height": 400}],
    ),
    TaskLevel.BARRIER: LevelConfig(
        name="戦略：誘導路作成",
        description="バリアで滑り台を作り、安全にゴールへ",
        box_position=Point(x=200, y=100),  # 高い位置
        goal_position=Point(x=600, y=500),
        box_mass=10.0,
        friction=0.3,
        time_limit=120.0,
        max_steps=50,
        available_barriers=3,
        obstacles=[{"type": "pit", "x": 400, "y": 550, "width": 100, "height": 50}],
    ),
}
