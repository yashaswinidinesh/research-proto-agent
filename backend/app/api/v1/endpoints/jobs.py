"""
Research job endpoints — upload paper, run pipeline, stream events, get results.
"""
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.base import get_db, AsyncSessionLocal
from app.models.models import Paper, ResearchJob, AgentStep, Methodology, CodeArtifact, ReproducibilityReport, JobStatus
from app.services.agents import IngestionAgent, MethodologyAgent, PlanningAgent, CodeGenAgent, ReproducibilityAgent
from app.services.orchestrator import ResearchOrchestrator, AgentOutput

router = APIRouter(prefix="/jobs", tags=["jobs"])
_sse: dict[str, asyncio.Queue] = {}


async def _run_job(job_id: str, paper_text: str):
    async with AsyncSessionLocal() as db:
        job = await db.get(ResearchJob, job_id)
        if not job: return
        job.status = JobStatus.RUNNING
        await db.commit()

        q = _sse.setdefault(job_id, asyncio.Queue())

        async def on_step(out: AgentOutput):
            step = AgentStep(
                job_id=job_id, agent_role=out.role, status="completed",
                output=out.structured, evidence=out.evidence,
                confidence=out.confidence, is_assumption=out.is_assumption,
                latency_ms=out.structured.get("_latency_ms", 0),
            )
            db.add(step)

            # Persist methodology
            if out.role == "methodology":
                s = out.structured
                m = Methodology(
                    job_id=job_id,
                    problem_statement=s.get("training_procedure", ""),
                    model_architecture=s.get("model_architecture", ""),
                    dataset=s.get("dataset", ""),
                    hyperparameters=s.get("hyperparameters", []),
                    evaluation_metrics=s.get("evaluation_metrics", []),
                    ambiguities=s.get("ambiguities", []),
                    assumptions=[],
                )
                db.add(m)

            # Persist code artifacts
            if out.role == "code_gen":
                for f in out.structured.get("files", []):
                    db.add(CodeArtifact(
                        job_id=job_id, file_path=f.get("path", ""),
                        artifact_type=f.get("type", "source"),
                        content=f.get("content", ""),
                        traceability=f.get("traceability", []),
                    ))

            # Persist report
            if out.role == "reproducibility":
                s = out.structured
                db.add(ReproducibilityReport(
                    job_id=job_id,
                    overall_score=s.get("overall_reproducibility_score", 0),
                    comparisons=s.get("comparisons", []),
                    missing_details=s.get("missing_details", []),
                    recommendation=s.get("recommendation", ""),
                    code_ran=s.get("code_ran", False),
                    tests_passed=s.get("tests_passed", False),
                ))

            job.progress_pct = out.structured.get("_progress_pct", 0)
            job.current_agent = out.role
            await db.commit()
            await q.put(json.dumps({"step": out.role, "summary": out.summary,
                                    "confidence": out.confidence,
                                    "progress_pct": out.structured.get("_progress_pct", 0)}))

        try:
            agents = [IngestionAgent(), MethodologyAgent(), PlanningAgent(),
                      CodeGenAgent(), ReproducibilityAgent()]
            orch = ResearchOrchestrator(job_id, agents, on_step=on_step)
            await orch.run({"paper_text": paper_text})
            job.status = JobStatus.COMPLETED
            job.progress_pct = 100.0
        except Exception as e:
            job.status = JobStatus.FAILED
            job.current_agent = f"error: {e}"
        await db.commit()
        await q.put("__done__")


@router.post("", status_code=201)
async def create_job(
    background_tasks: BackgroundTasks,
    paper_text: str = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    text = ""
    if file:
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")[:40000]
    elif paper_text:
        text = paper_text[:40000]
    else:
        raise HTTPException(400, "Provide paper_text or upload a file")

    paper = Paper(raw_text=text)
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    job = ResearchJob(paper_id=paper.id)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_run_job, job.id, text)
    return {"job_id": job.id, "paper_id": paper.id, "status": job.status}


@router.get("")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResearchJob).order_by(ResearchJob.created_at.desc()).limit(50))
    jobs = result.scalars().all()
    return [{"id": j.id, "status": j.status, "progress_pct": j.progress_pct,
             "current_agent": j.current_agent, "created_at": j.created_at} for j in jobs]


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ResearchJob)
        .options(selectinload(ResearchJob.steps), selectinload(ResearchJob.artifacts),
                 selectinload(ResearchJob.methodology), selectinload(ResearchJob.report),
                 selectinload(ResearchJob.checkpoints))
        .where(ResearchJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job: raise HTTPException(404)
    return {
        "id": job.id, "status": job.status, "progress_pct": job.progress_pct,
        "current_agent": job.current_agent,
        "steps": [{"role": s.agent_role, "status": s.status, "output": s.output,
                   "confidence": s.confidence, "latency_ms": s.latency_ms} for s in job.steps],
        "artifacts": [{"id": a.id, "path": a.file_path, "type": a.artifact_type} for a in job.artifacts],
        "methodology": {
            "hyperparameters": job.methodology.hyperparameters if job.methodology else [],
            "ambiguities": job.methodology.ambiguities if job.methodology else [],
            "model_architecture": job.methodology.model_architecture if job.methodology else "",
        } if job.methodology else None,
        "report": {
            "overall_score": job.report.overall_score,
            "comparisons": job.report.comparisons,
            "recommendation": job.report.recommendation,
            "code_ran": job.report.code_ran,
            "tests_passed": job.report.tests_passed,
        } if job.report else None,
    }


@router.get("/{job_id}/stream")
async def stream_job(job_id: str):
    q = _sse.setdefault(job_id, asyncio.Queue())
    async def gen():
        while True:
            msg = await asyncio.wait_for(q.get(), timeout=120)
            if msg == "__done__":
                yield "data: {\"done\": true}\n\n"; break
            yield f"data: {msg}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/{job_id}/artifacts/{artifact_id}/download")
async def download_artifact(job_id: str, artifact_id: str, db: AsyncSession = Depends(get_db)):
    a = await db.get(CodeArtifact, artifact_id)
    if not a or a.job_id != job_id: raise HTTPException(404)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(a.content, media_type="text/plain",
                             headers={"Content-Disposition": f'attachment; filename="{a.file_path.split("/")[-1]}"'})
