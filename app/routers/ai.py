import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Task
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)


@router.get("/summary", summary="Gemini AI summary of current tasks")
async def get_ai_summary(db: AsyncSession = Depends(get_db)):
    """
    Fetches recent tasks and asks Gemini to summarise the workload
    and provide one actionable productivity recommendation.
    """
    result = await db.execute(
        select(Task).order_by(Task.created_at.desc()).limit(15)
    )
    tasks = result.scalars().all()

    if not tasks:
        return {
            "task_count": 0,
            "pending": 0,
            "completed": 0,
            "summary": "No tasks found. Add some tasks to receive an AI-powered summary!",
        }

    tasks_text = "\n".join([
        f"- {'[DONE]' if t.completed else '[PENDING]'} {t.title}"
        + (f": {t.description}" if t.description else "")
        for t in tasks
    ])

    prompt = (
        "You are a productivity assistant. Analyze these tasks and provide:\n"
        "1. A brief 2-sentence summary of the workload\n"
        "2. One specific actionable recommendation\n\n"
        f"Tasks:\n{tasks_text}\n\n"
        "Keep the response under 5 sentences. Be direct and practical."
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                GEMINI_URL,
                params={"key": settings.GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )

        if response.status_code != 200:
            logger.error(
                "gemini | API error status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            raise HTTPException(status_code=502, detail="AI service unavailable")

        data = response.json()
        summary = data["candidates"][0]["content"]["parts"][0]["text"]

    except httpx.TimeoutException:
        logger.warning("gemini | Request timed out")
        raise HTTPException(status_code=504, detail="AI request timed out")
    except (KeyError, IndexError) as exc:
        logger.error("gemini | Unexpected response structure: %s", exc)
        raise HTTPException(status_code=502, detail="Unexpected response from AI service")

    pending   = sum(1 for t in tasks if not t.completed)
    completed = len(tasks) - pending

    return {
        "task_count": len(tasks),
        "pending":    pending,
        "completed":  completed,
        "summary":    summary,
    }
