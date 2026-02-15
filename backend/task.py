"""
Task Evaluation System for LLM-driven World Model Experiment

タスク評価システム：報酬計算、成功/失敗判定、メトリクス収集
"""

import math
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


class TaskOutcome(BaseModel):
    """タスク結果"""

    # 成功/失敗
    goal_reached: bool = False
    box_out_of_bounds: bool = False
    timeout: bool = False

    # 距離
    initial_distance: float
    final_distance: float
    distance_improvement: float

    # 効率性
    steps: int
    total_force: float = 0.0
    excessive_force: bool = False

    # 動き
    smooth_movement: bool = True
    path_length: float = 0.0

    # 戦略
    strategy_hash: str = ""
    is_novel_strategy: bool = False

    # 時間
    completion_time: float = 0.0


class EpisodeMetrics(BaseModel):
    """エピソード評価指標"""

    # 成功率
    success_rate: float = 0.0
    success_count: int = 0
    total_episodes: int = 0

    # 効率性
    avg_steps_to_goal: float = 0.0
    avg_force_magnitude: float = 0.0
    avg_completion_time: float = 0.0

    # 学習
    unique_strategies: int = 0
    strategy_diversity: float = 0.0

    # 創発性
    novel_actions: int = 0
    unexpected_solutions: int = 0

    # 品質
    smoothness_score: float = 0.0
    elegance_score: float = 0.0

    # 報酬
    total_reward: float = 0.0
    avg_reward: float = 0.0
    max_reward: float = 0.0


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
        time_limit=60.0,  # AI mode needs more time (2s per step * 20 steps = 40s minimum)
        max_steps=20,
    ),
    TaskLevel.FRICTION: LevelConfig(
        name="物理：摩擦係数",
        description="滑りやすい荷物をコントロール",
        box_position=Point(x=200, y=300),
        goal_position=Point(x=600, y=300),
        box_mass=10.0,
        friction=0.1,  # 非常に滑る
        time_limit=80.0,  # AI mode needs more time
        max_steps=30,
    ),
    TaskLevel.OBSTACLE: LevelConfig(
        name="障害：壁の回避",
        description="壁を避けてゴールへ",
        box_position=Point(x=200, y=300),
        goal_position=Point(x=600, y=300),
        box_mass=10.0,
        friction=0.5,
        time_limit=100.0,  # AI mode needs more time
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
        time_limit=120.0,  # AI mode needs more time
        max_steps=50,
        available_barriers=3,
        obstacles=[{"type": "pit", "x": 400, "y": 550, "width": 100, "height": 50}],
    ),
}


# ==================== Reward Calculator ====================


class RewardCalculator:
    """報酬計算器"""

    def __init__(self):
        self.past_strategies: set = set()

    def calculate(self, outcome: TaskOutcome, level: LevelConfig) -> float:
        """
        報酬を計算

        Args:
            outcome: タスク結果
            level: レベル設定

        Returns:
            報酬値
        """
        reward = 0.0

        # 【主要目標】ゴール到達
        if outcome.goal_reached:
            reward += 100

            # 効率性ボーナス
            time_bonus = max(0, 50 - outcome.steps * 2)
            reward += time_bonus

            # 優雅さボーナス
            if outcome.smooth_movement:
                reward += 20

        # 【進捗評価】距離の減少
        distance_improvement = outcome.initial_distance - outcome.final_distance
        reward += distance_improvement * 0.1  # 係数を0.5から0.1に調整

        # 【創発性ボーナス】新しい戦略
        if outcome.is_novel_strategy:
            reward += 30
            print(f"🎉 新戦略発見! Hash: {outcome.strategy_hash[:8]}")

        # 【ペナルティ】
        if outcome.box_out_of_bounds:
            reward -= 50

        if outcome.excessive_force:
            reward -= 10

        if outcome.timeout:
            reward -= 20

        return reward

    def register_strategy(self, strategy_hash: str):
        """戦略を登録"""
        self.past_strategies.add(strategy_hash)

    def is_novel_strategy(self, strategy_hash: str) -> bool:
        """新規戦略かどうか"""
        return strategy_hash not in self.past_strategies


# ==================== Task Evaluator ====================


class TaskEvaluator:
    """タスク評価器"""

    def __init__(self):
        self.reward_calculator = RewardCalculator()
        self.metrics = EpisodeMetrics()

    def evaluate_state(self, state: SimulationState, level: LevelConfig) -> tuple[bool, bool, str]:
        """
        現在の状態を評価

        Args:
            state: シミュレーション状態
            level: レベル設定

        Returns:
            (成功, 失敗, 理由)
        """
        # 成功判定
        if self.is_success(state.box.position, state.goal.position):
            return True, False, "ゴール到達"

        # 失敗判定
        if state.box.position.y > 600:
            return False, True, "画面外に落下"

        if state.step >= level.max_steps:
            return False, True, "制限ステップ超過"

        if state.box.position.x < -100 or state.box.position.x > 900:
            return False, True, "画面外（横方向）"

        if state.elapsed_time > level.time_limit:
            return False, True, "時間切れ"

        return False, False, "継続中"

    def is_success(self, box_pos: Point, goal_pos: Point) -> bool:
        """成功判定"""
        distance = self.euclidean_distance(box_pos, goal_pos)
        return distance < 30.0

    def evaluate_episode(
        self,
        initial_state: SimulationState,
        final_state: SimulationState,
        level: LevelConfig,
    ) -> tuple[TaskOutcome, float]:
        """
        エピソード全体を評価

        Args:
            initial_state: 初期状態
            final_state: 最終状態
            level: レベル設定

        Returns:
            (タスク結果, 報酬)
        """
        initial_dist = self.euclidean_distance(
            initial_state.box.position, initial_state.goal.position
        )
        final_dist = self.euclidean_distance(final_state.box.position, final_state.goal.position)

        # 行動シーケンスからハッシュを生成
        strategy_hash = self.compute_strategy_hash(final_state.actions_taken)

        # 力の合計を計算
        total_force = sum(
            math.sqrt((a.force_x or 0) ** 2 + (a.force_y or 0) ** 2)
            for a in final_state.actions_taken
            if a.type == ActionType.PUSH
        )

        # 動きの滑らかさを評価
        smooth_movement = self.evaluate_smoothness(final_state.actions_taken)

        # タスク結果を構築
        outcome = TaskOutcome(
            goal_reached=self.is_success(final_state.box.position, final_state.goal.position),
            box_out_of_bounds=(
                final_state.box.position.y > 600
                or final_state.box.position.x < -100
                or final_state.box.position.x > 900
            ),
            timeout=(final_state.elapsed_time > level.time_limit),
            initial_distance=initial_dist,
            final_distance=final_dist,
            distance_improvement=initial_dist - final_dist,
            steps=final_state.step,
            total_force=total_force,
            excessive_force=(total_force > 5.0),
            smooth_movement=smooth_movement,
            strategy_hash=strategy_hash,
            is_novel_strategy=self.reward_calculator.is_novel_strategy(strategy_hash),
            completion_time=final_state.elapsed_time,
        )

        # 報酬を計算
        reward = self.reward_calculator.calculate(outcome, level)

        # 新規戦略を登録
        if outcome.is_novel_strategy:
            self.reward_calculator.register_strategy(strategy_hash)

        # メトリクスを更新
        self.update_metrics(outcome, reward)

        return outcome, reward

    def compute_strategy_hash(self, actions: list[Action]) -> str:
        """行動シーケンスからハッシュを生成"""
        # 行動タイプのシーケンスをハッシュ化
        action_sequence = "".join([a.type.value[0] for a in actions])  # p, b, w, o

        # 力の方向パターンも考慮
        force_pattern = ""
        for a in actions:
            if a.type == ActionType.PUSH:
                if a.force_x and a.force_x > 0:
                    force_pattern += "R"  # Right
                elif a.force_x and a.force_x < 0:
                    force_pattern += "L"  # Left
                if a.force_y and a.force_y > 0:
                    force_pattern += "D"  # Down
                elif a.force_y and a.force_y < 0:
                    force_pattern += "U"  # Up

        combined = f"{action_sequence}:{force_pattern}"
        return str(hash(combined))

    def evaluate_smoothness(self, actions: list[Action]) -> bool:
        """動きの滑らかさを評価"""
        if len(actions) < 2:
            return True

        # 力の変化が急激でないか
        push_actions = [a for a in actions if a.type == ActionType.PUSH]
        if len(push_actions) < 2:
            return True

        max_force_change = 0.0
        for i in range(1, len(push_actions)):
            prev = push_actions[i - 1]
            curr = push_actions[i]

            prev_mag = math.sqrt((prev.force_x or 0) ** 2 + (prev.force_y or 0) ** 2)
            curr_mag = math.sqrt((curr.force_x or 0) ** 2 + (curr.force_y or 0) ** 2)

            force_change = abs(curr_mag - prev_mag)
            max_force_change = max(max_force_change, force_change)

        # 変化が0.1以下なら滑らか
        return max_force_change < 0.1

    def update_metrics(self, outcome: TaskOutcome, reward: float):
        """メトリクスを更新"""
        self.metrics.total_episodes += 1

        if outcome.goal_reached:
            self.metrics.success_count += 1

        self.metrics.success_rate = self.metrics.success_count / self.metrics.total_episodes

        # 平均値の更新（累積平均）
        n = self.metrics.total_episodes
        self.metrics.avg_steps_to_goal = (
            self.metrics.avg_steps_to_goal * (n - 1) + outcome.steps
        ) / n
        self.metrics.avg_force_magnitude = (
            self.metrics.avg_force_magnitude * (n - 1) + outcome.total_force
        ) / n
        self.metrics.avg_completion_time = (
            self.metrics.avg_completion_time * (n - 1) + outcome.completion_time
        ) / n

        # 報酬
        self.metrics.total_reward += reward
        self.metrics.avg_reward = self.metrics.total_reward / n
        self.metrics.max_reward = max(self.metrics.max_reward, reward)

        # 創発性
        if outcome.is_novel_strategy:
            self.metrics.novel_actions += 1
            self.metrics.unique_strategies = len(self.reward_calculator.past_strategies)

        # 品質
        if outcome.smooth_movement:
            self.metrics.smoothness_score = (self.metrics.smoothness_score * (n - 1) + 1.0) / n
        else:
            self.metrics.smoothness_score = (self.metrics.smoothness_score * (n - 1) + 0.0) / n

    def euclidean_distance(self, p1: Point, p2: Point) -> float:
        """ユークリッド距離"""
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

    def get_metrics(self) -> EpisodeMetrics:
        """現在のメトリクスを取得"""
        return self.metrics

    def reset_metrics(self):
        """メトリクスをリセット"""
        self.metrics = EpisodeMetrics()


# ==================== Helper Functions ====================


def get_level_config(level: TaskLevel) -> LevelConfig:
    """レベル設定を取得"""
    return LEVELS[level]


def create_initial_state(level: LevelConfig) -> SimulationState:
    """初期状態を作成"""
    return SimulationState(
        box=BoxState(
            position=level.box_position,
            velocity=Velocity(x=0, y=0),
            mass=level.box_mass,
            friction=level.friction,
            restitution=level.restitution,
        ),
        goal=GoalState(position=level.goal_position),
        barriers=[],
        step=0,
        elapsed_time=0.0,
        actions_taken=[],
    )
