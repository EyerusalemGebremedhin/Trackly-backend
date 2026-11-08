from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Literal, List

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    history: List[ChatTurn] = Field(default_factory=list, max_length=20)
    memory: List[str] = Field(default_factory=list, max_length=8)


class ChatResponse(BaseModel):
    response: str
    model: str


@router.post("", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = ChatService(db).chat(current_user, data.message, data.context, data.history, data.memory)
    return result


from fastapi import UploadFile, File, Form
from tracker.services.groq_client import transcribe_audio


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        audio_bytes = await file.read()
        text = transcribe_audio(audio_bytes, file.filename or "audio.webm")
        return {"text": text}
    except Exception as e:
        print(f"TRANSCRIBE ERROR: {e!r}", flush=True)
        raise


class VisionChatRequest(BaseModel):
    message: str = ""
    image: str  # base64 data url


@router.post("/vision", response_model=ChatResponse)
def vision_chat(
    data: VisionChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from tracker.services.groq_client import call_groq_vision
    system_prompt = (
        "You are Trackly AI, the assistant inside Trackly. You CAN view and analyze images. "
        "Only describe or discuss an image if it relates to Trackly work (tasks, groups, plans, check-ins, performance, team progress). "
        "If the image is unrelated (food, personal photos, etc.), politely decline and say you can only help with Trackly-related things. "
"Trackly is a progress tracking platform for individuals and teams to set plans, track tasks, work in groups, do check-ins, and get insights. "
"Its real features are: personal dashboards, task boards and plans, groups/teams with members and roles, group goals and assignments, daily check-ins, alerts, insights/metrics, help requests, profile settings with avatar upload, and direct messages (DMs). "
        "Reply in short, plain conversational text. Do not use tables, headings, or heavy markdown. Keep answers under 100 words unless asked for more. "
        "If asked about something not in this list, say you're not sure rather than guessing. "
        "You never identify as 'Grow' or any other system - you are Trackly AI."
    )
    models = [
        "qwen/qwen3.8-27b",
        "meta-models/muse-spark-open",
    ]
    for m in models:
        try:
            response = call_groq_vision(system_prompt, data.message, data.image, model=m)
            return {"response": response, "model": m}
        except Exception as e:
            print(f"VISION ERROR ({m}): {e!r}", flush=True)
    return {"response": "I can only help with Trackly-related things like your tasks, groups, plans, and team progress.", "model": "none"}
