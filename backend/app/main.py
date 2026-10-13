from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.base import Base, engine
from app.api.v1.endpoints.jobs import router as jobs_router

@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Research-to-Prototype Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                  allow_methods=["*"], allow_headers=["*"])
app.include_router(jobs_router, prefix="/api/v1")

@app.get("/health")
async def health(): return {"status": "ok", "service": "research-proto-agent"}
