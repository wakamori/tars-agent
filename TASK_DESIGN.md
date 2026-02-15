# タスク設計書：LLM駆動の倉庫番シミュレーション

## 🎯 タスク概要

### コンセプト
「物理法則を理解し、試行錯誤と記憶を通じて創発的な解決策を発見するAIエージェント」

### ゴール
荷物を指定されたゴール地点まで運ぶ

### 特徴
- **物理ベース**: 重さ・摩擦・弾性などの実世界の物理特性
- **世界モデル**: LLM (Gemini) が状況を理解し、物理法則を推論
- **記憶学習**: 成功/失敗パターンを記憶し、次回に活かす
- **創発性**: 予期しない解決策の自発的発見

---

## 📋 Phase 1: 最小プロトタイプ（MVP）

### 1.1 シミュレーション環境

```
┌───────────────────────────────────────────┐
│  800x600 キャンバス                        │
│                                           │
│  📦 Box (荷物)                             │
│     - 位置: (200, 300)                    │
│     - サイズ: 40x40px                     │
│     - 重さ: 可変                          │
│     - 摩擦係数: 可変                      │
│     - 色: #4169E1 (青)                    │
│                                           │
│  🎯 Goal (ゴール)                          │
│     - 位置: (600, 300)                    │
│     - サイズ: 60x60px                     │
│     - 色: #FFD700 (金)                    │
│                                           │
│  🧱 Ground (地面)                          │
│     - 位置: (0, 550)                      │
│     - サイズ: 800x50px                    │
│     - 静止オブジェクト                    │
│                                           │
└───────────────────────────────────────────┘
```

### 1.2 物理パラメータ

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| **重力** | { x: 0, y: 1.0 } | 下向きの重力 |
| **荷物の質量** | 10 | Matter.jsの密度で制御 |
| **摩擦係数** | 0.5 | 0=滑りやすい, 1=滑りにくい |
| **反発係数** | 0.3 | 0=弾まない, 1=完全弾性 |
| **空気抵抗** | 0.01 | 速度の減衰 |

### 1.3 エージェントの行動空間

```typescript
type Action = 
  | { type: 'push', forceX: number, forceY: number, duration: number }
  | { type: 'barrier', x: number, y: number, angle: number }
  | { type: 'wait', reason: string }
  | { type: 'observe', focus: string };

// 例
{ type: 'push', forceX: 0.05, forceY: 0, duration: 1000 }  // 右に押す
{ type: 'barrier', x: 400, y: 300, angle: 45 }             // 斜めバリア
{ type: 'wait', reason: '荷物の動きを観察' }                // 待機
{ type: 'observe', focus: '摩擦係数を推定' }                // 観察
```

### 1.4 観測空間

LLMが受け取る情報：

```typescript
interface Observation {
  // 視覚情報
  screenshot: string;  // Base64エンコード画像
  
  // 構造化情報
  entities: {
    box: { x: number, y: number, velocityX: number, velocityY: number },
    goal: { x: number, y: number },
    barriers: Array<{ x: number, y: number, angle: number }>
  };
  
  // 物理状態
  physics: {
    boxMass: number,
    friction: number,
    restitution: number
  };
  
  // 履歴
  actionHistory: Array<{ action: Action, outcome: string }>;
  
  // 記憶
  relevantMemories: Array<Memory>;
}
```

---

## 📊 評価システム

### 2.1 報酬関数

```python
def calculate_reward(outcome: TaskOutcome) -> float:
    reward = 0.0
    
    # 【主要目標】ゴール到達
    if outcome.goal_reached:
        reward += 100
        
        # 効率性ボーナス
        time_bonus = max(0, 50 - outcome.steps * 2)  # 早いほど高得点
        reward += time_bonus
        
        # 優雅さボーナス（滑らかな動き）
        if outcome.smooth_movement:
            reward += 20
    
    # 【進捗評価】距離の減少
    distance_improvement = outcome.initial_distance - outcome.final_distance
    reward += distance_improvement * 0.5  # 近づいたら加点
    
    # 【創発性ボーナス】新しい戦略
    if outcome.strategy_hash not in past_strategies:
        reward += 30
        print("🎉 新戦略発見!")
    
    # 【ペナルティ】
    if outcome.box_out_of_bounds:
        reward -= 50  # 画面外に落ちた
    
    if outcome.excessive_force:
        reward -= 10  # 力の無駄遣い
    
    if outcome.timeout:
        reward -= 20  # 時間切れ
    
    return reward
```

### 2.2 成功条件

```python
def is_success(box_pos: Point, goal_pos: Point) -> bool:
    """荷物がゴールに到達したか判定"""
    distance = euclidean_distance(box_pos, goal_pos)
    return distance < 30  # ゴールの半径内
```

### 2.3 失敗条件

```python
def is_failure(state: SimulationState) -> bool:
    """失敗判定"""
    if state.box.y > 600:  # 画面外に落下
        return True
    
    if state.steps > 50:   # 制限ステップ超過
        return True
    
    if state.box.x < -100 or state.box.x > 900:  # 横方向も外に出た
        return True
    
    return False
```

### 2.4 評価指標 (Metrics)

```python
class EpisodeMetrics:
    # 成功率
    success_rate: float  # ゴール到達率
    
    # 効率性
    avg_steps_to_goal: float      # 平均ステップ数
    avg_force_magnitude: float    # 平均力の大きさ
    
    # 学習
    unique_strategies: int         # 発見した戦略数
    strategy_diversity: float      # 戦略の多様性
    
    # 創発性
    novel_actions: int             # 新規行動パターン
    unexpected_solutions: int      # 予期しない解決策
    
    # 品質
    smoothness_score: float        # 動きの滑らかさ
    elegance_score: float          # 解の優雅さ
```

---

## 🧪 実験設定

### 3.1 レベル設計

#### Level 1: チュートリアル
```yaml
name: "基礎：直線移動"
box_position: [200, 300]
goal_position: [600, 300]
obstacles: []
box_mass: 10
friction: 0.5
time_limit: 30  # 秒
description: "荷物を右に押してゴールへ"
```

#### Level 2: 摩擦の理解
```yaml
name: "物理：摩擦係数"
box_position: [200, 300]
goal_position: [600, 300]
obstacles: []
box_mass: 10
friction: 0.1  # 非常に滑る
time_limit: 40
description: "滑りやすい荷物をコントロール"
```

#### Level 3: 障害物
```yaml
name: "障害：壁の回避"
box_position: [200, 300]
goal_position: [600, 300]
obstacles:
  - type: wall
    position: [400, 200]
    size: [20, 400]
box_mass: 10
friction: 0.5
time_limit: 50
description: "壁を避けてゴールへ"
```

#### Level 4: バリア活用
```yaml
name: "戦略：誘導路作成"
box_position: [200, 100]  # 高い位置
goal_position: [600, 500]
obstacles:
  - type: pit
    position: [400, 550]
    size: [100, 50]
available_barriers: 3
box_mass: 10
friction: 0.3
time_limit: 60
description: "バリアで滑り台を作り、安全にゴールへ"
```

### 3.2 実験プロトコル

```python
# 各レベルを5回実行
for level in levels:
    for episode in range(5):
        # 1. 環境リセット
        state = env.reset(level)
        
        # 2. エージェント実行
        done = False
        while not done:
            observation = env.get_observation()
            action = agent.decide(observation, memories)
            state, reward, done = env.step(action)
        
        # 3. 評価
        metrics = evaluate(state, level)
        
        # 4. 記憶保存
        if metrics.success or metrics.novel:
            memory.save(episode)
        
        # 5. 分析
        print(f"Episode {episode}: Reward={reward}, Steps={state.steps}")
```

---

## 🧠 LLM世界モデルの設計

### 4.1 プロンプト構造

```python
TASK_PROMPT_TEMPLATE = """
# タスク：荷物をゴールに運ぶ

## 現在の状況
{observation_summary}

## 物理法則
- 重力: 下向きに常に作用
- 摩擦: {friction} (0=滑る, 1=滑らない)
- 質量: {mass}kg (重いほど動かしにくい)
- 反発: {restitution} (壁に当たると少し跳ね返る)

## 利用可能な行動
1. push(force_x, force_y, duration): 荷物に力を加える
2. barrier(x, y, angle): バリアを設置してルートを作る
3. wait(reason): 一時停止して観察
4. observe(focus): 特定の要素を詳しく観察

## 過去の記憶（成功例）
{relevant_memories}

## 質問
1. 現在の荷物とゴールの位置関係をどう理解していますか？
2. 物理特性（摩擦={friction}, 質量={mass}）から、どんな戦略が有効ですか？
3. 過去の記憶から学べることはありますか？
4. 今まで試していない新しいアプローチはありますか？

## 行動選択
最適な行動を1つ選択し、JSON形式で出力してください：

{{
  "reasoning": "選択理由の詳細な説明",
  "action": {{
    "type": "push",
    "force_x": 0.05,
    "force_y": 0,
    "duration": 1000
  }},
  "prediction": "この行動の結果として何が起きるか",
  "confidence": 0.85
}}
"""
```

### 4.2 応答スキーマ

```python
class ActionDecision(BaseModel):
    reasoning: str = Field(description="選択理由")
    action: Action = Field(description="実行する行動")
    prediction: str = Field(description="結果予測")
    confidence: float = Field(ge=0, le=1, description="確信度")
    
    # 内部思考（観察可能）
    observations: List[str] = Field(description="現在の状況認識")
    physics_understanding: str = Field(description="物理法則の理解")
    strategy: str = Field(description="採用する戦略")
    alternatives: List[Action] = Field(description="代替案")
```

---

## 📈 期待される創発的行動

### 予想される発見パターン

1. **効率的経路**
   - 直線的な押し方（基本）
   - 斜め押しで回転を利用
   - 連続プッシュで勢いをつける

2. **物理特性の活用**
   - 摩擦が低い→小さい力で継続的に押す
   - 摩擦が高い→大きい力で一気に動かす
   - 重力を利用した転がし

3. **バリア戦略**
   - ガイドレール（左右に配置）
   - 滑り台（斜め配置）
   - ジャンプ台（跳ね上げ）

4. **予期しない創発**
   - バリアを複数組み合わせた複雑な誘導路
   - 意図的な壁バウンドの利用
   - 「押す」ではなく「転がす」戦略

---

## 🎮 ユーザーインターフェース

### 5.1 画面構成

```
┌─────────────────────────────────────────────────────────────┐
│  TARS - World Model Experiment                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                                                        │  │
│  │          [物理シミュレーション領域]                   │  │
│  │                                                        │  │
│  │    📦 Box                                 🎯 Goal     │  │
│  │                                                        │  │
│  │    🧱 Ground                                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  🧠 AI Thinking:                                      │  │
│  │  "荷物は滑りやすい(摩擦=0.1)。継続的に小さい力で    │  │
│  │   押すことで、オーバーシュートを防ぎます..."          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Episode: 5 | Steps: 12 | Reward: 87.5                      │
│  [▶️ Start] [⏸️ Pause] [🔄 Reset] [⏭️ Next Level]           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 インタラクション

- **自動モード**: AIが自律的に行動選択
- **ステップモード**: 1行動ごとに停止して観察
- **解説モード**: AIの思考プロセスを表示

---

## 📁 実装ファイル構成

```
tars-agent/
├── backend/
│   ├── task.py              # タスク定義・評価システム
│   ├── world_model.py       # LLM世界モデル
│   ├── reward.py            # 報酬関数
│   └── levels.py            # レベル設定
│
├── frontend/
│   ├── src/
│   │   ├── simulation.ts    # 物理シミュレーション（強化版）
│   │   ├── visualizer.ts    # 描画・アニメーション
│   │   └── agent.ts         # エージェント制御
│   └── index.html           # UI
│
└── TASK_DESIGN.md           # このファイル
```

---

## 🚀 Next Steps

### Phase 1 (現在)
- [x] タスク設計文書の作成
- [ ] 評価システムの実装 (backend/task.py)
- [ ] 物理シミュレーションの強化 (frontend)

### Phase 2
- [ ] LLM世界モデルの統合
- [ ] 記憶システムとの連携
- [ ] 基本レベルのテスト

### Phase 3
- [ ] 複雑なレベルの追加
- [ ] 創発行動の分析
- [ ] パフォーマンス最適化

---

**設計完了日**: 2026-02-15
**作成者**: TARS Development Team
