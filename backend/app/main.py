from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ChatRequest, ChatResponse


app = FastAPI(
    title=settings.app_name,
    description="Backend de l'assistent intel·ligent en català per consultar trens de Mallorca.",
    version="0.1.0",
)


# Permet que el frontend pugui cridar el backend durant el desenvolupament.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "language": settings.response_language,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(uuid4())

    return ChatResponse(
        conversation_id=conversation_id,
        response=(
            "Hola! Encara estic en fase inicial, però aviat podré ajudar-te "
            "a consultar horaris de tren de Mallorca en català."
        ),
    )