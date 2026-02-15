"""
Task Evaluation System - Unit Tests
評価システムの動作確認
"""

import sys

sys.path.insert(0, "backend")

from task import (
    LEVELS,
    Action,
    ActionType,
    BoxState,
    GoalState,
    LevelConfig,
    Point,
    RewardCalculator,
    SimulationState,
    TaskEvaluator,
    TaskLevel,
    TaskOutcome,
    Velocity,
    create_initial_state,
    get_level_config,
)


def test_level_configs():
    """レベル設定のテスト"""
    print("\n=== レベル設定テスト ===")

    assert len(LEVELS) == 4, "レベル数は4つであるべき"

    for level_name, level in LEVELS.items():
        print(f"\n📋 {level.name}")
        print(f"   説明: {level.description}")
        print(f"   荷物位置: ({level.box_position.x}, {level.box_position.y})")
        print(f"   ゴール位置: ({level.goal_position.x}, {level.goal_position.y})")
        print(f"   質量: {level.box_mass}kg")
        print(f"   摩擦: {level.friction}")
        print(f"   制限時間: {level.time_limit}秒")
        print(f"   最大ステップ: {level.max_steps}")
        print(f"   バリア数: {level.available_barriers}")

    print("\n✅ レベル設定テスト成功")


def test_reward_calculator():
    """報酬計算のテスト"""
    print("\n=== 報酬計算テスト ===")

    calculator = RewardCalculator()
    level = get_level_config(TaskLevel.TUTORIAL)

    # テスト1: ゴール到達
    outcome1 = TaskOutcome(
        goal_reached=True,
        box_out_of_bounds=False,
        timeout=False,
        initial_distance=400.0,
        final_distance=10.0,
        distance_improvement=390.0,
        steps=10,
        total_force=2.0,
        smooth_movement=True,
        strategy_hash="test_strategy_1",
        is_novel_strategy=True,
    )

    reward1 = calculator.calculate(outcome1, level)
    print(f"\n✅ ゴール到達ケース:")
    print(f"   ステップ数: {outcome1.steps}")
    print(f"   滑らかな動き: {outcome1.smooth_movement}")
    print(f"   新規戦略: {outcome1.is_novel_strategy}")
    print(f"   → 報酬: {reward1}")
    assert reward1 > 100, "ゴール到達の報酬は100以上であるべき"

    # テスト2: 進捗のみ（ゴール未到達）
    outcome2 = TaskOutcome(
        goal_reached=False,
        box_out_of_bounds=False,
        timeout=False,
        initial_distance=400.0,
        final_distance=200.0,
        distance_improvement=200.0,
        steps=20,
        total_force=3.0,
        smooth_movement=False,
    )

    reward2 = calculator.calculate(outcome2, level)
    print(f"\n📊 進捗のみケース:")
    print(f"   距離改善: {outcome2.distance_improvement}")
    print(f"   → 報酬: {reward2}")
    assert 0 < reward2 < 50, "進捗のみの報酬は0から50の間であるべき（距離改善*0.1）"

    # テスト3: 失敗（画面外）
    outcome3 = TaskOutcome(
        goal_reached=False,
        box_out_of_bounds=True,
        timeout=False,
        initial_distance=400.0,
        final_distance=400.0,
        distance_improvement=0.0,
        steps=30,
        total_force=10.0,
        excessive_force=True,
    )

    reward3 = calculator.calculate(outcome3, level)
    print(f"\n❌ 失敗ケース:")
    print(f"   画面外に落下: {outcome3.box_out_of_bounds}")
    print(f"   過剰な力: {outcome3.excessive_force}")
    print(f"   → 報酬: {reward3}")
    assert reward3 < 0, "失敗の報酬は負であるべき"

    print("\n✅ 報酬計算テスト成功")


def test_task_evaluator():
    """タスク評価器のテスト"""
    print("\n=== タスク評価器テスト ===")

    evaluator = TaskEvaluator()
    level = get_level_config(TaskLevel.TUTORIAL)

    # 初期状態を作成
    initial_state = create_initial_state(level)
    print(f"\n📍 初期状態:")
    print(
        f"   荷物位置: ({initial_state.box.position.x}, {initial_state.box.position.y})"
    )
    print(
        f"   ゴール位置: ({initial_state.goal.position.x}, {initial_state.goal.position.y})"
    )

    # シミュレーション: 成功ケース
    final_state_success = SimulationState(
        box=BoxState(
            position=Point(x=600, y=300),  # ゴール近く
            velocity=Velocity(x=0, y=0),
            mass=level.box_mass,
            friction=level.friction,
            restitution=level.restitution,
        ),
        goal=GoalState(position=level.goal_position),
        step=15,
        elapsed_time=10.0,
        actions_taken=[
            Action(type=ActionType.PUSH, force_x=0.05, force_y=0),
            Action(type=ActionType.PUSH, force_x=0.05, force_y=0),
            Action(type=ActionType.WAIT, reason="観察"),
        ],
    )

    # 評価
    success, failure, reason = evaluator.evaluate_state(final_state_success, level)
    print(f"\n✅ 成功判定テスト:")
    print(f"   成功: {success}, 失敗: {failure}, 理由: {reason}")
    assert success and not failure, "ゴール近くなら成功であるべき"

    # エピソード評価
    outcome, reward = evaluator.evaluate_episode(
        initial_state, final_state_success, level
    )
    print(f"\n📊 エピソード評価:")
    print(f"   ゴール到達: {outcome.goal_reached}")
    print(f"   ステップ数: {outcome.steps}")
    print(f"   距離改善: {outcome.distance_improvement:.1f}")
    print(f"   報酬: {reward:.2f}")
    assert outcome.goal_reached, "成功エピソードではゴール到達フラグが立つべき"
    assert reward > 100, "成功時の報酬は100以上であるべき"

    # シミュレーション: 失敗ケース (画面外)
    final_state_failure = SimulationState(
        box=BoxState(
            position=Point(x=200, y=650),  # 画面外
            velocity=Velocity(x=0, y=5),
            mass=level.box_mass,
            friction=level.friction,
            restitution=level.restitution,
        ),
        goal=GoalState(position=level.goal_position),
        step=25,
        elapsed_time=15.0,
        actions_taken=[
            Action(type=ActionType.PUSH, force_x=0, force_y=0.1),
        ],
    )

    success, failure, reason = evaluator.evaluate_state(final_state_failure, level)
    print(f"\n❌ 失敗判定テスト:")
    print(f"   成功: {success}, 失敗: {failure}, 理由: {reason}")
    assert not success and failure, "画面外なら失敗であるべき"

    print("\n✅ タスク評価器テスト成功")


def test_strategy_hash():
    """戦略ハッシュのテスト"""
    print("\n=== 戦略ハッシュテスト ===")

    evaluator = TaskEvaluator()

    # 同じ行動シーケンス
    actions1 = [
        Action(type=ActionType.PUSH, force_x=0.05, force_y=0),
        Action(type=ActionType.PUSH, force_x=0.05, force_y=0),
        Action(type=ActionType.WAIT, reason="観察"),
    ]

    actions2 = [
        Action(type=ActionType.PUSH, force_x=0.05, force_y=0),
        Action(type=ActionType.PUSH, force_x=0.05, force_y=0),
        Action(type=ActionType.WAIT, reason="観察"),
    ]

    hash1 = evaluator.compute_strategy_hash(actions1)
    hash2 = evaluator.compute_strategy_hash(actions2)

    print(f"\n同じ戦略:")
    print(f"   Hash 1: {hash1}")
    print(f"   Hash 2: {hash2}")
    assert hash1 == hash2, "同じ行動シーケンスは同じハッシュであるべき"

    # 異なる行動シーケンス
    actions3 = [
        Action(type=ActionType.PUSH, force_x=-0.05, force_y=0),  # 左に押す
        Action(type=ActionType.BARRIER, x=400, y=300, angle=45),
    ]

    hash3 = evaluator.compute_strategy_hash(actions3)
    print(f"\n異なる戦略:")
    print(f"   Hash 3: {hash3}")
    assert hash1 != hash3, "異なる行動シーケンスは異なるハッシュであるべき"

    print("\n✅ 戦略ハッシュテスト成功")


def test_metrics():
    """メトリクス収集のテスト"""
    print("\n=== メトリクス収集テスト ===")

    evaluator = TaskEvaluator()
    level = get_level_config(TaskLevel.TUTORIAL)

    # 複数エピソードをシミュレート
    for i in range(5):
        initial_state = create_initial_state(level)

        # 成功: 3回, 失敗: 2回
        is_success = i < 3

        if is_success:
            final_state = SimulationState(
                box=BoxState(
                    position=Point(x=600, y=300),
                    velocity=Velocity(x=0, y=0),
                    mass=level.box_mass,
                    friction=level.friction,
                    restitution=level.restitution,
                ),
                goal=GoalState(position=level.goal_position),
                step=10 + i * 2,
                elapsed_time=8.0 + i,
                actions_taken=[Action(type=ActionType.PUSH, force_x=0.05, force_y=0)],
            )
        else:
            final_state = SimulationState(
                box=BoxState(
                    position=Point(x=300, y=400),
                    velocity=Velocity(x=0, y=0),
                    mass=level.box_mass,
                    friction=level.friction,
                    restitution=level.restitution,
                ),
                goal=GoalState(position=level.goal_position),
                step=30,
                elapsed_time=25.0,
                actions_taken=[Action(type=ActionType.PUSH, force_x=0, force_y=0.05)],
            )

        outcome, reward = evaluator.evaluate_episode(initial_state, final_state, level)

    metrics = evaluator.get_metrics()
    print(f"\n📊 メトリクス (5エピソード後):")
    print(f"   成功率: {metrics.success_rate:.2%}")
    print(f"   成功回数: {metrics.success_count} / {metrics.total_episodes}")
    print(f"   平均ステップ数: {metrics.avg_steps_to_goal:.1f}")
    print(f"   平均報酬: {metrics.avg_reward:.2f}")
    print(f"   最大報酬: {metrics.max_reward:.2f}")

    assert metrics.total_episodes == 5, "5エピソード記録されるべき"
    assert metrics.success_count == 3, "3回成功するべき"
    assert abs(metrics.success_rate - 0.6) < 0.01, "成功率は60%であるべき"

    print("\n✅ メトリクス収集テスト成功")


def run_all_tests():
    """全テストを実行"""
    print("\n" + "=" * 60)
    print("🧪 Task Evaluation System - 検証テスト")
    print("=" * 60)

    try:
        test_level_configs()
        test_reward_calculator()
        test_task_evaluator()
        test_strategy_hash()
        test_metrics()

        print("\n" + "=" * 60)
        print("✅ 全てのテストが成功しました！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ テスト失敗: {e}")
        raise
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
