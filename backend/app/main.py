from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ChatRequest, ChatResponse

from app.services.station_service import station_service
from app.services.train_service import train_service


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


@app.get("/debug/station/{query}")
def debug_validate_station(query: str):
    return station_service.validate_station(query)


@app.get("/debug/trains/next")
def debug_next_departure(
    origin: str,
    destination: str,
    after_time: str = "00:00",
    service_id: str | None = None,
    limit: int = 3,
):
    return train_service.search_next_departure(
        origin_stop_id=origin,
        destination_stop_id=destination,
        after_time=after_time,
        service_id=service_id,
        limit=limit,
    )


@app.get("/debug/trains/window")
def debug_trains_in_window(
    origin: str,
    destination: str,
    start_time: str,
    end_time: str,
    service_id: str | None = None,
):
    return train_service.search_trains_in_window(
        origin_stop_id=origin,
        destination_stop_id=destination,
        start_time=start_time,
        end_time=end_time,
        service_id=service_id,
    )


@app.get("/debug/trains/arrival-before")
def debug_arrival_before(
    origin: str,
    destination: str,
    arrival_time: str,
    service_id: str | None = None,
    limit: int = 5,
):
    return train_service.search_arrival_before(
        origin_stop_id=origin,
        destination_stop_id=destination,
        arrival_time=arrival_time,
        service_id=service_id,
        limit=limit,
    )


@app.get("/debug/trains/departure-after")
def debug_departure_after(
    origin: str,
    destination: str,
    departure_time: str,
    service_id: str | None = None,
    limit: int = 5,
):
    return train_service.search_departure_after(
        origin_stop_id=origin,
        destination_stop_id=destination,
        departure_time=departure_time,
        service_id=service_id,
        limit=limit,
    )


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