from sqlalchemy import String, Text, JSON, Float, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, new_uuid
import enum

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"

class Paper(Base, TimestampMixin):
    __tablename__ = "papers"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String, default="")
    authors: Mapped[str] = mapped_column(Text, default="")
    venue: Mapped[str] = mapped_column(String, default="")
    year: Mapped[int] = mapped_column(Integer, default=0)
    source_url: Mapped[str] = mapped_column(String, default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    storage_path: Mapped[str] = mapped_column(String, default="")
    jobs: Mapped[list["ResearchJob"]] = relationship(back_populates="paper")

class ResearchJob(Base, TimestampMixin):
    __tablename__ = "research_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    status: Mapped[str] = mapped_column(String, default=JobStatus.PENDING)
    current_agent: Mapped[str] = mapped_column(String, default="")
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    paper: Mapped["Paper"] = relationship(back_populates="jobs")
    steps: Mapped[list["AgentStep"]] = relationship(back_populates="job", order_by="AgentStep.created_at")
    methodology: Mapped["Methodology"] = relationship(back_populates="job", uselist=False)
    artifacts: Mapped[list["CodeArtifact"]] = relationship(back_populates="job")
    checkpoints: Mapped[list["HumanCheckpoint"]] = relationship(back_populates="job")
    report: Mapped["ReproducibilityReport"] = relationship(back_populates="job", uselist=False)

class AgentStep(Base, TimestampMixin):
    __tablename__ = "agent_steps"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id"))
    agent_role: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    output: Mapped[dict] = mapped_column(JSON, default={})
    evidence: Mapped[list] = mapped_column(JSON, default=[])
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    is_assumption: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    job: Mapped["ResearchJob"] = relationship(back_populates="steps")

class Methodology(Base, TimestampMixin):
    __tablename__ = "methodologies"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id"), unique=True)
    problem_statement: Mapped[str] = mapped_column(Text, default="")
    model_architecture: Mapped[str] = mapped_column(Text, default="")
    dataset: Mapped[str] = mapped_column(String, default="")
    hyperparameters: Mapped[list] = mapped_column(JSON, default=[])
    evaluation_metrics: Mapped[list] = mapped_column(JSON, default=[])
    ambiguities: Mapped[list] = mapped_column(JSON, default=[])
    assumptions: Mapped[list] = mapped_column(JSON, default=[])
    human_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    job: Mapped["ResearchJob"] = relationship(back_populates="methodology")

class CodeArtifact(Base, TimestampMixin):
    __tablename__ = "code_artifacts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id"))
    file_path: Mapped[str] = mapped_column(String)
    artifact_type: Mapped[str] = mapped_column(String)  # source|test|config|dockerfile|readme
    content: Mapped[str] = mapped_column(Text, default="")
    traceability: Mapped[list] = mapped_column(JSON, default=[])
    job: Mapped["ResearchJob"] = relationship(back_populates="artifacts")

class HumanCheckpoint(Base, TimestampMixin):
    __tablename__ = "human_checkpoints"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id"))
    checkpoint_type: Mapped[str] = mapped_column(String)  # methodology|execution|results
    description: Mapped[str] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSON, default={})
    status: Mapped[str] = mapped_column(String, default="pending")
    reviewer_note: Mapped[str] = mapped_column(Text, default="")
    job: Mapped["ResearchJob"] = relationship(back_populates="checkpoints")

class ReproducibilityReport(Base, TimestampMixin):
    __tablename__ = "reproducibility_reports"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id"), unique=True)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    comparisons: Mapped[list] = mapped_column(JSON, default=[])
    missing_details: Mapped[list] = mapped_column(JSON, default=[])
    recommendation: Mapped[str] = mapped_column(Text, default="")
    code_ran: Mapped[bool] = mapped_column(Boolean, default=False)
    tests_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    job: Mapped["ResearchJob"] = relationship(back_populates="report")
