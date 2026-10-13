"""
5 specialized agents for Research-to-Prototype pipeline.
"""
import json
from app.services.orchestrator import BaseAgent, AgentOutput

SYS = """You are a specialized AI research engineering agent.
Output ONLY valid JSON. Never fabricate citations or results.
Label every inferred detail with is_assumption: true.
Evidence must reference exact paper passages."""


class IngestionAgent(BaseAgent):
    def __init__(self): super().__init__("ingestion")

    async def run(self, ctx):
        text = ctx.get("paper_text", "")[:8000]
        raw = await self._call_llm(SYS, f"""Extract the research paper structure. Output JSON:
{{
  "title": str, "authors": [str], "venue": str, "year": int,
  "abstract": str,
  "sections": [{{"name": str, "summary": str, "key_claims": [str]}}],
  "problem_statement": str,
  "key_contributions": [str],
  "datasets_mentioned": [str],
  "equations_count": int,
  "figures_count": int,
  "confidence": float
}}
Paper text:\n{text}""")
        data = json.loads(raw)
        return AgentOutput(
            role=self.role,
            summary=f"Ingested: {data.get('title', 'Unknown')} ({data.get('year', '?')}). {len(data.get('key_contributions', []))} contributions.",
            evidence=[{"text": data.get("abstract", "")[:200], "source": "paper_abstract", "location": "Abstract"}],
            structured=data,
            confidence=data.get("confidence", 0.85),
        )


class MethodologyAgent(BaseAgent):
    def __init__(self): super().__init__("methodology")

    async def run(self, ctx):
        text = ctx.get("paper_text", "")[:8000]
        ingestion = ctx.get("ingestion", {}).get("structured", {})
        raw = await self._call_llm(SYS, f"""Extract complete methodology. Output JSON:
{{
  "model_architecture": str,
  "inputs": [str], "outputs": [str],
  "training_procedure": str,
  "dataset": str,
  "hyperparameters": [{{"name": str, "value": str, "source": "paper|inferred", "is_assumption": bool, "paper_ref": str}}],
  "evaluation_metrics": [str],
  "baselines": [str],
  "expected_results": [{{"metric": str, "value": str, "table_ref": str}}],
  "ambiguities": [{{"detail": str, "severity": "blocking|minor", "section": str}}],
  "missing_details": [str],
  "confidence": float
}}
Title: {ingestion.get('title', '')}
Paper:\n{text}""")
        data = json.loads(raw)
        ambig = data.get("ambiguities", [])
        blocking = [a for a in ambig if a.get("severity") == "blocking"]
        return AgentOutput(
            role=self.role,
            summary=f"Extracted methodology. {len(blocking)} blocking ambiguities, {len(ambig) - len(blocking)} minor.",
            evidence=[{"text": h.get("value", ""), "source": "paper", "location": h.get("name", "")}
                      for h in data.get("hyperparameters", []) if not h.get("is_assumption")],
            structured=data,
            confidence=data.get("confidence", 0.75),
            is_assumption=any(h.get("is_assumption") for h in data.get("hyperparameters", [])),
        )


class PlanningAgent(BaseAgent):
    def __init__(self): super().__init__("planning")

    async def run(self, ctx):
        m = ctx.get("methodology", {}).get("structured", {})
        raw = await self._call_llm(SYS, f"""Create an implementation plan. Output JSON:
{{
  "language": str, "framework": str,
  "file_structure": [{{"path": str, "purpose": str, "type": "source|test|config|dockerfile|readme"}}],
  "implementation_steps": [{{"order": int, "task": str, "depends_on": [str], "estimated_loc": int}}],
  "estimated_complexity": "low|medium|high",
  "blocking_ambiguities": [str],
  "assumptions_made": [{{"assumption": str, "rationale": str, "impact": "low|medium|high"}}],
  "sandbox_requirements": {{"cpu": str, "memory": str, "disk": str, "timeout_sec": int}},
  "confidence": float
}}
Methodology:\n{json.dumps(m, indent=2)[:3000]}""")
        data = json.loads(raw)
        return AgentOutput(
            role=self.role,
            summary=f"Plan: {data.get('language')}/{data.get('framework')}. {len(data.get('file_structure', []))} files. Complexity: {data.get('estimated_complexity')}.",
            evidence=[],
            structured=data,
            confidence=data.get("confidence", 0.78),
            is_assumption=len(data.get("assumptions_made", [])) > 0,
        )


class CodeGenAgent(BaseAgent):
    def __init__(self): super().__init__("code_gen")

    async def run(self, ctx):
        plan = ctx.get("planning", {}).get("structured", {})
        m = ctx.get("methodology", {}).get("structured", {})
        raw = await self._call_llm(SYS, f"""Generate implementation code. Output JSON:
{{
  "files": [{{
    "path": str, "type": "source|test|config|dockerfile|readme",
    "content": str, "description": str,
    "traceability": [{{"code_element": str, "paper_source": str, "is_assumption": bool}}]
  }}],
  "dockerfile": str,
  "requirements_txt": str,
  "readme_snippet": str,
  "test_commands": [str],
  "confidence": float
}}
Plan:\n{json.dumps(plan, indent=2)[:2000]}
Architecture: {m.get('model_architecture', '')}
Hyperparameters: {json.dumps(m.get('hyperparameters', []))[:1000]}""")
        data = json.loads(raw)
        files = data.get("files", [])
        return AgentOutput(
            role=self.role,
            summary=f"Generated {len(files)} files. {len([f for f in files if f.get('type') == 'test'])} test files.",
            evidence=[t for f in files for t in f.get("traceability", [])],
            structured=data,
            confidence=data.get("confidence", 0.70),
        )


class ReproducibilityAgent(BaseAgent):
    def __init__(self): super().__init__("reproducibility")

    async def run(self, ctx):
        m = ctx.get("methodology", {}).get("structured", {})
        code = ctx.get("code_gen", {}).get("structured", {})
        raw = await self._call_llm(SYS, f"""Generate reproducibility assessment. Output JSON:
{{
  "comparisons": [{{
    "metric": str, "paper_value": str, "reproduced_value": str,
    "difference": str, "within_tolerance": bool,
    "possible_reasons": [str], "confidence": float
  }}],
  "overall_reproducibility_score": float,
  "code_ran": bool,
  "tests_passed": bool,
  "missing_details": [str],
  "recommendation": str,
  "confidence": float
}}
Expected results: {json.dumps(m.get('expected_results', []))}
Generated files: {[f['path'] for f in code.get('files', [])]}""")
        data = json.loads(raw)
        score = data.get("overall_reproducibility_score", 0)
        return AgentOutput(
            role=self.role,
            summary=f"Reproducibility score: {score:.0%}. Code ran: {data.get('code_ran')}. Tests passed: {data.get('tests_passed')}.",
            evidence=[],
            structured=data,
            confidence=data.get("confidence", 0.65),
        )
