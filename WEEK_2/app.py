
# Task API - FlyRank W2 A1 (Python / FastAPI lane)
# Run with:  uvicorn app:app --reload --port 8000
# Docs at:   http://localhost:8000/docs


from typing import Optional
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Task API", version="1.0")

tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Write weekly report", "done": True},
    {"id": 3, "title": "Walk the dog", "done": False},
]
next_id = 4


def error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def find_task(task_id: int):
    return next((t for t in tasks if t["id"] == task_id), None)


class TaskCreate(BaseModel):
    title: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks(
    done: Optional[bool] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
):
    result = tasks
    if done is not None:
        result = [t for t in result if t["done"] == done]
    if search:
        needle = search.lower()
        result = [t for t in result if needle in t["title"].lower()]
    if offset:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]
    return result


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        return error(404, f"Task {task_id} not found")
    return task


@app.post("/tasks", status_code=201)
def create_task(payload: TaskCreate):
    global next_id
    if not payload.title or not payload.title.strip():
        return error(400, "title is required and cannot be empty")
    new_task = {"id": next_id, "title": payload.title.strip(), "done": False}
    tasks.append(new_task)
    next_id += 1
    return JSONResponse(status_code=201, content=new_task)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate):
    task = find_task(task_id)
    if task is None:
        return error(404, f"Task {task_id} not found")
    if payload.title is None and payload.done is None:
        return error(400, "request body must include at least 'title' or 'done'")
    if payload.title is not None and not payload.title.strip():
        return error(400, "title cannot be empty")
    if payload.title is not None:
        task["title"] = payload.title.strip()
    if payload.done is not None:
        task["done"] = payload.done
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        return error(404, f"Task {task_id} not found")
    tasks.remove(task)
    return Response(status_code=204)


@app.get("/stats")
def stats():
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    return {"total": total, "done": done_count, "open": total - done_count}


@app.post("/reset")
def reset_tasks():
    global tasks, next_id
    tasks = [
        {"id": 1, "title": "Buy milk", "done": False},
        {"id": 2, "title": "Write weekly report", "done": True},
        {"id": 3, "title": "Walk the dog", "done": False},
    ]
    next_id = 4
    return {"message": "Tasks reset to the 3 example tasks", "tasks": tasks}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
