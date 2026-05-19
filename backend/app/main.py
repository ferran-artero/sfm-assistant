from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ChatRequest, ChatResponse

from app.services.station_service import station_service
from app.services.train_service import train_service
from app.services.conversation_service import conversation_service
from app.services.intent_service import intent_service
from app.services.llm_service import llm_service
from app.services.response_service import response_service


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

@app.get("/debug/conversation/query")
def debug_conversation_query(
    conversation_id: str | None = None,
    origin_stop_id: str | None = None,
    destination_stop_id: str | None = None,
    query_type: str = "next_departure",
    date: str | None = None,
    time: str | None = None,
    time_window: str | None = None,
    departure_after: str | None = None,
    arrival_before: str | None = None,
    service_id: str | None = None,
):
    new_query = {
        "query_type": query_type,
        "origin_stop_id": origin_stop_id,
        "destination_stop_id": destination_stop_id,
        "date": date,
        "time": time,
        "time_window": time_window,
        "departure_after": departure_after,
        "arrival_before": arrival_before,
        "service_id": service_id,
    }

    return conversation_service.merge_with_pending_query(
        conversation_id=conversation_id,
        new_query=new_query,
    )


@app.get("/debug/conversation/{conversation_id}")
def debug_get_conversation(conversation_id: str):
    return conversation_service.get_public_context(conversation_id)


@app.delete("/debug/conversation/{conversation_id}")
def debug_reset_conversation(conversation_id: str):
    deleted = conversation_service.reset_conversation(conversation_id)

    return {
        "conversation_id": conversation_id,
        "deleted": deleted,
    }


@app.get("/debug/intent")
def debug_intent(message: str):
    return intent_service.analyze_message(message)


@app.get("/debug/llm")
def debug_llm():
    return llm_service.get_status()


@app.get("/debug/response/simple")
def debug_simple_response(intent: str):
    intent_result = {
        "intent": intent,
    }

    return response_service.build_simple_response(intent_result)


@app.get("/debug/response/trains")
def debug_train_response(
    origin: str,
    destination: str,
    after_time: str = "00:00",
    service_id: str | None = None,
    limit: int = 3,
):
    query = {
        "query_type": "next_departure",
        "origin_stop_id": origin,
        "destination_stop_id": destination,
        "time": after_time,
        "service_id": service_id,
    }

    results = train_service.search_next_departure(
        origin_stop_id=origin,
        destination_stop_id=destination,
        after_time=after_time,
        service_id=service_id,
        limit=limit,
    )

    response = response_service.build_train_results_response(
        query=query,
        results=results,
    )

    return {
        "query": query,
        "results": results,
        "response": response,
    }


@app.get("/debug/response/place-without-train")
def debug_place_without_train_response(place: str):
    validation = station_service.validate_station(place)

    if validation.get("status") != "known_place_without_train":
        return {
            "validation": validation,
            "response": {
                "response": "Aquest lloc no s'ha detectat com a poble conegut sense tren.",
                "source": "template",
            },
        }

    place_info = {
        "type": "place_without_train",
        "id": validation.get("place_id"),
        "display_name": validation.get("display_name"),
        "message": validation.get("message"),
    }

    response = response_service.build_known_place_without_train_response(
        places=[place_info],
    )

    return {
        "validation": validation,
        "response": response,
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