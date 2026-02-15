"""
TARS - World Model: LLM-driven Physics Reasoning

Gemini APIを使った空間知能システム
物理シミュレーションを観察し、次の行動を推論する
"""

import json
from datetime import datetime

from pydantic import BaseModel, Field
from task import Action, LevelConfig


class EpisodeMemory(BaseModel):
    """エピソード記憶（Generative Agents風）"""

    episode_id: int = Field(description="エピソードID")
    level_key: str = Field(description="レベル識別子")
    level_name: str = Field(description="レベル名")
    timestamp: str = Field(description="タイムスタンプ")
    success: bool = Field(description="成功/失敗")
    steps: int = Field(description="使用ステップ数")
    elapsed_time: float = Field(description="経過時間（秒）")
    reward: float = Field(description="獲得報酬")
    actions_taken: list[str] = Field(description="実行した行動リスト")
    final_distance: float = Field(description="最終的なゴールまでの距離")
    summary: str = Field(description="エピソードのサマリー")
    key_insight: str | None = Field(
        default=None, description="このエピソードから得られた重要な洞察"
    )


class Reflection(BaseModel):
    """リフレクション（複数エピソードからの学習）"""

    level_key: str = Field(description="レベル識別子")
    pattern: str = Field(description="発見したパターン")
    successful_strategy: str | None = Field(default=None, description="成功した戦略")
    failed_attempts: list[str] = Field(default_factory=list, description="失敗したアプローチ")
    improvement_hint: str = Field(description="改善のヒント")


class MemoryStream:
    """記憶ストリーム（Generative Agentsのメモリシステム）"""

    def __init__(self):
        self.episodes: list[EpisodeMemory] = []
        self.reflections: dict[str, Reflection] = {}  # level_key -> Reflection
        self.episode_counter = 0

    def add_episode(
        self,
        level_key: str,
        level_name: str,
        success: bool,
        steps: int,
        elapsed_time: float,
        reward: float,
        actions_taken: list[str],
        final_distance: float,
    ) -> EpisodeMemory:
        """新しいエピソードを記憶に追加"""

        self.episode_counter += 1

        summary = create_episode_summary(
            level_name=level_name,
            success=success,
            steps=steps,
            reward=reward,
            actions_taken=actions_taken,
        )

        # 重要な洞察を抽出
        key_insight = None
        if success:
            if steps < 10:
                key_insight = "最短ルートを発見！効率的なダ push戦略が有効"
            elif "barrier" in actions_taken:
                key_insight = "バリアを活用した誘導路が成功"
        else:
            if "画面外" in summary:
                key_insight = "力が強すぎて制御不能に→次回はより慎重に"
            elif "時間切れ" in summary:
                key_insight = "動作が遅すぎる→より強い力が必要"

        episode = EpisodeMemory(
            episode_id=self.episode_counter,
            level_key=level_key,
            level_name=level_name,
            timestamp=datetime.now().isoformat(),
            success=success,
            steps=steps,
            elapsed_time=elapsed_time,
            reward=reward,
            actions_taken=actions_taken,
            final_distance=final_distance,
            summary=summary,
            key_insight=key_insight,
        )

        self.episodes.append(episode)

        # リフレクションを更新
        self._update_reflection(level_key)

        return episode

    def _update_reflection(self, level_key: str):
        """このレベルに関するリフレクションを更新"""

        level_episodes = [e for e in self.episodes if e.level_key == level_key]

        if not level_episodes:
            return

        successes = [e for e in level_episodes if e.success]
        failures = [e for e in level_episodes if not e.success]

        # パターン発見
        pattern = f"{len(successes)}/{len(level_episodes)}回成功"

        # 成功戦略
        successful_strategy = None
        if successes:
            # 最も効率的な成功エピソードを特定
            best = min(successes, key=lambda e: e.steps)
            successful_strategy = (
                f"ステップ{best.steps}でクリア: {', '.join(best.actions_taken[:5])}"
            )

        # 失敗したアプローチ
        failed_attempts = []
        for failure in failures[-3:]:  # 最近の3回の失敗
            if failure.key_insight:
                failed_attempts.append(failure.key_insight)

        # 改善のヒント
        improvement_hint = "まだ試行錯誤中です"
        if len(level_episodes) >= 3:
            if successes:
                improvement_hint = f"成功パターン確立: {successful_strategy}"
            else:
                improvement_hint = "異なるアプローチを試してください"

        self.reflections[level_key] = Reflection(
            level_key=level_key,
            pattern=pattern,
            successful_strategy=successful_strategy,
            failed_attempts=failed_attempts,
            improvement_hint=improvement_hint,
        )

    def get_reflection(self, level_key: str) -> Reflection | None:
        """特定レベルのリフレクションを取得"""
        return self.reflections.get(level_key)

    def get_recent_episodes(self, level_key: str, limit: int = 5) -> list[EpisodeMemory]:
        """最近のエピソードを取得"""
        level_episodes = [e for e in self.episodes if e.level_key == level_key]
        return level_episodes[-limit:]

    def get_stats(self) -> dict:
        """統計情報を取得"""
        if not self.episodes:
            return {"total_episodes": 0}

        success_count = sum(1 for e in self.episodes if e.success)
        total_reward = sum(e.reward for e in self.episodes)

        return {
            "total_episodes": len(self.episodes),
            "success_rate": success_count / len(self.episodes) if self.episodes else 0,
            "total_reward": total_reward,
            "average_reward": total_reward / len(self.episodes) if self.episodes else 0,
        }


class WorldModelPrompt:
    """World Model用のプロンプトテンプレート"""

    SYSTEM_PROMPT = """あなたは物理法則を理解する空間知能AIです。

**タスク**: 倉庫内で荷物（青い箱）をゴール（金色の円）まで移動させる

**物理法則**:
- 重力: 下方向に常に働く (gravity.y = 1.0)
- 摩擦: 表面との摩擦で減速 (レベルにより異なる)
- 反発: 壁や障害物との衝突で跳ね返る (restitution = 0.3)
- 質量: 荷物の質量が大きいほど動きにくい (mass = 10kg)

**利用可能な行動**:
1. **push**: 荷物に力を加える
   - forceX, forceY: 力の方向と大きさ (推奨範囲: 50〜150)
   - duration: 力を加える時間（ミリ秒、100-500推奨）
   - 参考値: 50-80程度の力で荷物を動かし、100以上でより速く移動
   - 注意: 空気抵抗により速度は自然に減衰します。複数回押すことで加速できます

2. **barrier**: バリア（斜面）を配置して荷物を誘導
   - x, y: 配置位置
   - angle: 角度（度、0=水平、90=垂直）
   - レベルによって使用回数制限あり

3. **wait**: 何もせず観察（荷物が動いている時に有効）
   - duration: 待機時間（ミリ秒、500-2000推奨）

4. **observe**: 状況を詳しく観察（次の戦略を考える）
   - focus: 注目する要素（例: "velocity", "obstacles"）

**評価基準**:
- ゴール到達: +100点
- 効率性: 少ないステップでクリア（ボーナス最大+50）
- スムーズな動き: 急激な力を避ける (+20点)
- 新規戦略: 未知の解法を発見 (+30点)
- 失敗ペナルティ: 画面外に落下 (-50点)、時間切れ (-30点)

**重要な考慮事項**:
- 摩擦が低いレベルでは、荷物が滑りやすいので微調整が必要
- 壁がある場合は、迂回路を考える
- バリアを使える場合は、滑り台や誘導路を作ると効率的
- 過剰な力は逆効果（跳ね返りや制御不能）

あなたの目標は、物理法則を理解し、最も効率的な方法でゴールを達成することです。"""

    @staticmethod
    def create_observation_prompt(
        level: LevelConfig,
        state: dict,
        step: int,
        previous_actions: list[str],
        reflection: Reflection | None = None,
        recent_episodes: list[EpisodeMemory] = None,
    ) -> str:
        """観察データから推論プロンプトを生成"""

        box_pos = state["box"]["position"]
        box_vel = state["box"]["velocity"]
        goal_pos = state["goal"]["position"]
        goal_radius = state["goal"]["radius"]

        # 距離とベクトルを計算
        dx = goal_pos["x"] - box_pos["x"]
        dy = goal_pos["y"] - box_pos["y"]
        distance = (dx**2 + dy**2) ** 0.5

        # 速度の大きさ
        speed = (box_vel["x"] ** 2 + box_vel["y"] ** 2) ** 0.5

        prompt = f"""**現在の状況**:

**レベル**: {level.name}
- 説明: {level.description}
- 時間制限: {level.time_limit}秒
- 最大ステップ: {level.max_steps}
- 利用可能バリア: {level.available_barriers}個

**荷物の状態**:
- 位置: ({box_pos["x"]:.1f}, {box_pos["y"]:.1f})
- 速度: ({box_vel["x"]:.2f}, {box_vel["y"]:.2f}) - 速さ: {speed:.2f} px/s
- 質量: {level.box_mass}kg
- 摩擦係数: {level.friction}

**ゴールの状態**:
- 位置: ({goal_pos["x"]:.1f}, {goal_pos["y"]:.1f})
- 半径: {goal_radius}px
- 距離: {distance:.1f}px
- 方向: {"右" if dx > 0 else "左"} {abs(dx):.1f}px, {"下" if dy > 0 else "上"} {abs(dy):.1f}px

**進捗**:
- 現在のステップ: {step}/{level.max_steps}
- 経過時間: {state["elapsedTime"]:.1f}/{level.time_limit}秒
"""

        if level.obstacles:
            prompt += f"\n**障害物**: {len(level.obstacles)}個存在\n"
            for _i, obs in enumerate(level.obstacles):
                prompt += f"  - {obs['type']}: ({obs['x']}, {obs['y']}) サイズ{obs['width']}x{obs['height']}\n"

        if previous_actions:
            recent = previous_actions[-3:] if len(previous_actions) > 3 else previous_actions
            prompt += f"\n**直前の行動**: {', '.join(recent)}\n"

        # 記憶ストリームからの情報を追加（Generative Agents風）
        if reflection:
            prompt += "\n**📚 記憶からの洞察** (エピソード履歴):\n"
            prompt += f"- パターン: {reflection.pattern}\n"
            if reflection.successful_strategy:
                prompt += f"- ✅ 成功戦略: {reflection.successful_strategy}\n"
            if reflection.failed_attempts:
                prompt += "- ❌ 失敗から学ぶ:\n"
                for attempt in reflection.failed_attempts[-2:]:
                    prompt += f"  • {attempt}\n"
            prompt += f"- 💡 改善のヒント: {reflection.improvement_hint}\n"

        if recent_episodes:
            prompt += "\n**🧠 最近のエピソード** (最大3回):\n"
            for ep in recent_episodes[-3:]:
                result_emoji = "✅" if ep.success else "❌"
                prompt += f"- エピソード{ep.episode_id} {result_emoji}: ステップ{ep.steps}, 報酬{ep.reward:.0f}\n"
                if ep.key_insight:
                    prompt += f"  洞察: {ep.key_insight}\n"

        prompt += """
**質問**: 上記の物理状況を分析し、次に取るべき最適な行動を選択してください。

**回答形式** (必ずJSON形式で):
```json
{{
  "reasoning": "物理的推論と戦略の説明（日本語、2-3文）",
  "action": {{
    "type": "push" | "barrier" | "wait" | "observe",
    "forceX": 数値（pushの場合、例: 30.0）,
    "forceY": 数値（pushの場合、例: 10.0）,
    "duration": 数値（push/waitの場合、ミリ秒単位、例: 500）,
    "x": 数値（barrierの場合）,
    "y": 数値（barrierの場合）,
    "angle": 数値（barrierの場合、度、例: 45）,
    "focus": "文字列（observeの場合）",
    "reason": "行動の簡潔な理由（日本語、1文）"
  }}
}}
```

物理法則を考慮し、最も効率的な行動を選択してください。"""

        return prompt


class WorldModelResponse(BaseModel):
    """World Modelからの応答"""

    reasoning: str = Field(description="物理的推論と戦略")
    action: Action = Field(description="選択された行動")
    raw_response: str = Field(description="Geminiの生の応答")


async def analyze_and_decide(
    level: LevelConfig,
    level_key: str,
    state: dict,
    step: int,
    previous_actions: list[str],
    gemini_model,
    memory_stream: MemoryStream | None = None,
) -> WorldModelResponse:
    """
    物理シミュレーションの状態を分析し、次の行動を決定

    Args:
        level: レベル設定
        level_key: レベル識別子（例: 'tutorial'）
        state: 現在のシミュレーション状態
        step: 現在のステップ数
        previous_actions: これまでの行動履歴
        gemini_model: Gemini API モデルインスタンス
        memory_stream: エピソード記憶ストリーム

    Returns:
        WorldModelResponse: 推論結果と選択された行動
    """

    # 記憶から関連情報を取得
    reflection = None
    recent_episodes = []
    if memory_stream:
        reflection = memory_stream.get_reflection(level_key)
        recent_episodes = memory_stream.get_recent_episodes(level_key, limit=3)

    # プロンプトを生成
    system_prompt = WorldModelPrompt.SYSTEM_PROMPT
    observation_prompt = WorldModelPrompt.create_observation_prompt(
        level, state, step, previous_actions, reflection, recent_episodes
    )

    # Gemini APIに問い合わせ
    full_prompt = f"{system_prompt}\n\n{observation_prompt}"

    response = await gemini_model.generate_content_async(full_prompt)

    # レスポンスをパース
    response_text = response.text

    # JSONブロックを抽出（```json ... ``` 形式に対応）
    json_text = response_text
    if "```json" in response_text:
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        json_text = response_text[json_start:json_end].strip()
    elif "```" in response_text:
        json_start = response_text.find("```") + 3
        json_end = response_text.find("```", json_start)
        json_text = response_text[json_start:json_end].strip()

    try:
        parsed = json.loads(json_text)
        reasoning = parsed.get("reasoning", "")
        action_dict = parsed.get("action", {})

        # Actionモデルに変換
        action = Action(**action_dict)

        return WorldModelResponse(
            reasoning=reasoning,
            action=action,
            raw_response=response_text,
        )

    except (json.JSONDecodeError, Exception) as e:
        # パースに失敗した場合は安全な待機アクションを返す
        print(f"⚠️  Failed to parse Gemini response: {e}")
        print(f"Raw response: {response_text}")

        return WorldModelResponse(
            reasoning="応答のパースに失敗したため、観察を実行します",
            action=Action(
                type="observe",
                focus="state",
                reason="応答解析エラー",
            ),
            raw_response=response_text,
        )


def create_episode_summary(
    level_name: str,
    success: bool,
    steps: int,
    reward: float,
    actions_taken: list[str],
) -> str:
    """エピソード終了時のサマリーを生成（記憶システム用）"""

    result = "成功" if success else "失敗"

    summary = f"""倉庫番タスク完了 - {level_name}
結果: {result}
ステップ数: {steps}
獲得報酬: {reward:.1f}
実行した行動: {", ".join(actions_taken[:10])}{"..." if len(actions_taken) > 10 else ""}

"""

    if success:
        if steps < 10:
            summary += "非常に効率的な解法を発見しました。"
        elif steps < 20:
            summary += "適度なステップ数でクリアしました。"
        else:
            summary += "時間がかかりましたが、ゴールに到達しました。"
    else:
        summary += "失敗から学び、次回は改善が必要です。"

    return summary
