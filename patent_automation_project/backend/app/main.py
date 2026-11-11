from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router

app = FastAPI(title=settings.app_name, version="0.1.0",
              description="Internal patent disclosure and prior-art discovery starter")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok"}
