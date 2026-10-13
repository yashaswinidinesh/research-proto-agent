"""
Research-to-Prototype orchestrator.
Chains 5 agents sequentially; pauses at human checkpoints.
"""
import asyncio, time, json
from abc import ABC, abstractmethod
from datetime import datetime
import httpx
from app.core.config import settings


class AgentOutput:
    def __init__(self, role, summary, evidence, structured, confidence, is_assumption=False):
        self.role = role
        self.summary = summary
        self.evidence = evidence       # [{text, source, location}]
        self.structured = structured   # role-specific JSON
        self.confidence = confidence
        self.is_assumption = is_assumption
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


class BaseAgent(ABC):
    def __init__(self, role: str):
        self.role = role
        self.model = settings.DEFAULT_MODEL
        self._client = httpx.AsyncClient(timeout=90)

    async def _call_llm(self, system: str, user: str, temperature: float = 0.1) -> str:
        if not settings.OPENAI_API_KEY:
            return await self._mock(user)
        resp = await self._client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                "temperature": temperature,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def _mock(self, prompt: str) -> str:
        await asyncio.sleep(0.4)
        return json.dumps({
            "summary": f"[MOCK] {self.role} analysis complete.",
            "confidence": 0.8,
            "findings": [],
            "note": "Set OPENAI_API_KEY for real analysis",
        })

    @abstractmethod
    async def run(self, ctx: dict) -> AgentOutput:
        pass


class ResearchOrchestrator:
    def __init__(self, job_id: str, agents: list, on_step=None):
        self.job_id = job_id
        self.agents = agents
        self.on_step = on_step
        self.ctx: dict = {}

    async def run(self, initial_ctx: dict) -> list[AgentOutput]:
        self.ctx = initial_ctx.copy()
        outputs = []
        total = len(self.agents)
        for i, agent in enumerate(self.agents):
            t0 = time.time()
            try:
                out = await agent.run(self.ctx)
            except Exception as e:
                out = AgentOutput(agent.role, f"Failed: {e}", [], {"error": str(e)}, 0.0)
            out.structured["_latency_ms"] = int((time.time() - t0) * 1000)
            out.structured["_progress_pct"] = round((i + 1) / total * 100, 1)
            outputs.append(out)
            self.ctx[agent.role] = out.to_dict()
            if self.on_step:
                await self.on_step(out)
        return outputs
