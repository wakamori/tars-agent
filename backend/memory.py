"""
TARS Memory System
Persistent memory stream with reflection capabilities for autonomous agent learning
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class MemorySystem:
    """
    メモリシステム - Generative Agentsの記憶ストリームを実装

    Features:
    - JSON永続化（再現性担保）
    - 重要度ベースの検索
    - 10件ごとのReflection自動生成
    """

    def __init__(self, memory_file: str = "data/memory_stream.json"):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memories = self._load()
        self.reflections = []
        print(f"📚 Memory system initialized: {len(self.memories)} memories loaded")

    def _load(self) -> List[Dict]:
        """JSONファイルから記憶をロード"""
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text(encoding="utf-8"))
                return data.get("memories", [])
            except json.JSONDecodeError as e:
                print(f"⚠️  Memory file corrupted, starting fresh: {e}")
                return []
        return []

    def _save(self):
        """JSONファイルに保存（同期書き込み）"""
        data = {
            "memories": self.memories,
            "reflections": self.reflections,
            "last_updated": datetime.utcnow().isoformat(),
        }
        self.memory_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def add_memory(
        self,
        observation: str,
        action: Dict,
        outcome: str,
        importance: int,
        learning_note: Optional[str] = None,
    ) -> int:
        """
        新しい記憶を追加

        Args:
            observation: 観察内容
            action: 実行したアクション
            outcome: 結果
            importance: 重要度 (1-10)
            learning_note: 学習メモ

        Returns:
            memory_id: 追加された記憶のID
        """
        memory_id = len(self.memories)
        memory = {
            "id": memory_id,
            "timestamp": datetime.utcnow().isoformat(),
            "observation": observation,
            "action": action,
            "outcome": outcome,
            "importance": min(max(importance, 1), 10),  # 1-10にクリップ
            "learning_note": learning_note,
        }
        self.memories.append(memory)
        self._save()

        print(f"💾 Memory #{memory_id} saved (importance: {importance})")

        # 10件ごとにReflectionトリガー
        if len(self.memories) % 10 == 0 and len(self.memories) > 0:
            print(f"🔄 Reflection triggered at {len(self.memories)} memories")
            # Reflectionは後で実装（LLM呼び出しが必要）

        return memory_id

    def retrieve_recent(self, n: int = 5) -> List[Dict]:
        """直近N件の記憶を取得"""
        return self.memories[-n:] if len(self.memories) >= n else self.memories

    def retrieve_important(self, threshold: int = 7, limit: int = 5) -> List[Dict]:
        """重要度が高い記憶を取得"""
        important = [m for m in self.memories if m["importance"] >= threshold]
        return important[-limit:] if len(important) >= limit else important

    def get_context(self, n_recent: int = 3, n_important: int = 2) -> str:
        """
        プロンプトに注入する記憶コンテキストを生成

        Args:
            n_recent: 直近の記憶の件数
            n_important: 重要な記憶の件数

        Returns:
            フォーマットされた記憶コンテキスト
        """
        recent = self.retrieve_recent(n_recent)
        important = self.retrieve_important(limit=n_important)

        # 重複排除（IDベース）
        seen_ids = set()
        context_memories = []

        # 重要な記憶を優先
        for m in important + recent:
            if m["id"] not in seen_ids:
                context_memories.append(m)
                seen_ids.add(m["id"])

        if not context_memories:
            return "（まだ記憶がありません。これが最初の観察です）"

        context = "## 過去の記憶\n"
        for m in context_memories:
            # タイムスタンプを読みやすく
            try:
                dt = datetime.fromisoformat(m["timestamp"])
                time_str = dt.strftime("%H:%M:%S")
            except (ValueError, KeyError):
                time_str = m["timestamp"]

            importance_stars = "⭐" * min(m["importance"], 10)
            context += f"\n### 記憶 #{m['id']} [{time_str}] {importance_stars}\n"
            context += f"**観察**: {m['observation']}\n"
            context += f"**行動**: {m['action'].get('type', 'N/A')} at {m['action'].get('position', 'N/A')}\n"
            context += f"**結果**: {m['outcome']}\n"

            if m.get("learning_note"):
                context += f"**学び**: {m['learning_note']}\n"

        # Reflectionがあれば追加
        if self.reflections:
            context += "\n## 反省（高レベルな洞察）\n"
            for i, r in enumerate(self.reflections[-3:], 1):  # 最新3つ
                context += f"{i}. {r}\n"

        return context

    def generate_reflection(self, model, prompt_template: str) -> Optional[str]:
        """
        Reflectionを生成（LLM呼び出し）

        Args:
            model: Vertex AI GenerativeModel
            prompt_template: Reflectionプロンプトのテンプレート

        Returns:
            生成されたReflection
        """
        if not self.memories:
            return None

        # 最近の記憶を取得（過去10-20件）
        recent_memories = self.retrieve_recent(20)

        memory_summary = "\n".join(
            [
                f"- {m['observation']} → {m['action'].get('type')} → {m['outcome']}"
                for m in recent_memories
            ]
        )

        reflection_prompt = prompt_template.format(memory_summary=memory_summary)

        try:
            response = model.generate_content(
                reflection_prompt,
                generation_config={
                    "temperature": 0.7,  # 創造性を許容
                    "max_output_tokens": 2048,
                },
            )

            reflection_text = response.text.strip()
            self.reflections.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "content": reflection_text,
                    "based_on_memories": len(recent_memories),
                }
            )
            self._save()

            print(f"💡 Reflection generated: {reflection_text[:100]}...")
            return reflection_text

        except Exception as e:
            print(f"⚠️  Reflection generation failed: {e}")
            return None

    def get_stats(self) -> Dict:
        """記憶システムの統計情報を取得"""
        if not self.memories:
            return {
                "total_memories": 0,
                "avg_importance": 0,
                "reflections_count": len(self.reflections),
            }

        return {
            "total_memories": len(self.memories),
            "avg_importance": sum(m["importance"] for m in self.memories)
            / len(self.memories),
            "high_importance_count": len(
                [m for m in self.memories if m["importance"] >= 7]
            ),
            "reflections_count": len(self.reflections),
            "oldest_memory": self.memories[0]["timestamp"] if self.memories else None,
            "newest_memory": self.memories[-1]["timestamp"] if self.memories else None,
        }

    def clear(self):
        """すべての記憶をクリア（デバッグ用）"""
        self.memories = []
        self.reflections = []
        self._save()
        print("🗑️  All memories cleared")


# Reflection用のプロンプトテンプレート
REFLECTION_PROMPT_TEMPLATE = """
あなたはTARS - 自律的な工場安全エージェントです。
過去の観察と行動を振り返り、高レベルな洞察を3つ生成してください。

## 過去の記憶（最近の20件）
{memory_summary}

## タスク
上記の記憶から、以下のような高レベルな洞察を3つ生成してください：

1. パターンの発見（例：「作業員は午後になると移動速度が上がる傾向がある」）
2. 効果的な介入法（例：「バリア配置は挟まれリスクの回避に最も効果的」）
3. リスク要因の特定（例：「ロボットと障害物の間のスペースが狭いほど危険度が上がる」）

JSON形式で応答してください：
{{
  "reflections": [
    "洞察1",
    "洞察2",
    "洞察3"
  ]
}}
"""
