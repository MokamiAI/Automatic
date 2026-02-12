from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Recommendation Engine",
    description="Bureau enrichment and product recommendation service",
    version="1.0.0"
)

app.include_router(router)
