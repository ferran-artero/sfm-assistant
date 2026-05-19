from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Missatge escrit per l'usuari.",
        examples=["Vull anar d'Inca a Palma"],
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Identificador de la conversa. Si no arriba, el backend en crea un.",
    )


class ChatResponse(BaseModel):
    conversation_id: str
    response: str