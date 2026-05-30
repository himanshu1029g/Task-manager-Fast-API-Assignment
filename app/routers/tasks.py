import json
import logging
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskUpdate, TaskResponse
from app.cache import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])

CACHE_TTL = 60  # seconds


def _serialize(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# ── GET ALL ───────────────────────────────────────────────────────────────────
@router.get("/", response_model=list[TaskResponse])
async def get_tasks(db: AsyncSession = Depends(get_db)):
    r = await get_redis()

    cached = await r.get("tasks:all")
    if cached:
        logger.info("cache | HIT tasks:all")
        return json.loads(cached)

    logger.info("cache | MISS tasks:all — querying DB")
    result = await db.execute(select(Task).order_by(Task.created_at.desc()))
    tasks = result.scalars().all()

    tasks_data = [TaskResponse.model_validate(t).model_dump() for t in tasks]
    await r.setex("tasks:all", CACHE_TTL, json.dumps(tasks_data, default=_serialize))

    return tasks


# ── GET ONE ───────────────────────────────────────────────────────────────────
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    r = await get_redis()

    cached = await r.get(f"task:{task_id}")
    if cached:
        logger.info("cache | HIT task:%s", task_id)
        return json.loads(cached)

    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task_data = TaskResponse.model_validate(task).model_dump()
    await r.setex(f"task:{task_id}", CACHE_TTL, json.dumps(task_data, default=_serialize))
    return task


# ── CREATE ────────────────────────────────────────────────────────────────────
@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)

    r = await get_redis()
    await r.delete("tasks:all")
    logger.info("tasks | created id=%s title=%r | list cache invalidated", task.id, task.title)

    return task


# ── UPDATE ────────────────────────────────────────────────────────────────────
@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)

    r = await get_redis()
    await r.delete("tasks:all", f"task:{task_id}")
    logger.info("tasks | updated id=%s fields=%s | cache invalidated", task_id, list(updates.keys()))

    return task


# ── DELETE ────────────────────────────────────────────────────────────────────
@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    await db.delete(task)
    await db.commit()

    r = await get_redis()
    await r.delete("tasks:all", f"task:{task_id}")
    logger.info("tasks | deleted id=%s | cache invalidated", task_id)
