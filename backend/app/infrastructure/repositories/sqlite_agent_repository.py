import json
from datetime import UTC, datetime
from typing import Optional

from app.domain.models.agent import Agent
from app.domain.models.memory import Memory
from app.domain.repositories.agent_repository import AgentRepository
from app.infrastructure.storage.sqlite import get_sqlite


class SQLiteAgentRepository(AgentRepository):
    async def save(self, agent: Agent) -> None:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                """
                INSERT INTO agents (
                    agent_id, model_name, temperature, max_tokens, memories_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    model_name=excluded.model_name,
                    temperature=excluded.temperature,
                    max_tokens=excluded.max_tokens,
                    memories_json=excluded.memories_json,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at
                """,
                (
                    agent.id,
                    agent.model_name,
                    agent.temperature,
                    agent.max_tokens,
                    json.dumps({k: v.model_dump(mode="json") for k, v in agent.memories.items()}),
                    agent.created_at.isoformat(),
                    agent.updated_at.isoformat(),
                ),
            )
            await conn.commit()

    async def find_by_id(self, agent_id: str) -> Optional[Agent]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM agents WHERE agent_id = ?",
                (agent_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            memories_raw = json.loads(row["memories_json"])
            memories = {name: Memory.model_validate(value) for name, value in memories_raw.items()}
            return Agent.model_validate(
                {
                    "id": row["agent_id"],
                    "model_name": row["model_name"],
                    "temperature": row["temperature"],
                    "max_tokens": row["max_tokens"],
                    "memories": memories,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )

    async def add_memory(self, agent_id: str, name: str, memory: Memory) -> None:
        await self.save_memory(agent_id, name, memory)

    async def get_memory(self, agent_id: str, name: str) -> Memory:
        agent = await self.find_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        return agent.memories.get(name, Memory(messages=[]))

    async def save_memory(self, agent_id: str, name: str, memory: Memory) -> None:
        agent = await self.find_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        agent.memories[name] = memory
        agent.updated_at = datetime.now(UTC)
        await self.save(agent)
