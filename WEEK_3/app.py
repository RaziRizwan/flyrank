from fastapi import FastAPI
from fastapi import Response
from fastapi import Body
from fastapi.responses import JSONResponse
from database import init_db
from database import (
    init_db,
    get_all_tasks,
    get_task_by_id,
    create_task,
    update_task,
    delete_task,
)

app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def home():
    return {"message": "Database connected successfully!"}

@app.get("/tasks")
def read_tasks():
    return get_all_tasks()


@app.get("/tasks/{task_id}")
def read_task(task_id: int):
    task = get_task_by_id(task_id)

    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"}
        )

    return task


# POST /tasks

@app.post("/tasks", status_code=201)
def add_task(task: dict = Body(...)):
    title = task.get("title", "").strip()

    if not title:
        return JSONResponse(
            status_code=400,
            content={"error": "Title is required"},
        )

    done = task.get("done", False)

    return create_task(title, done)


# PUT /tasks/{id}

@app.put("/tasks/{task_id}")
def edit_task(task_id: int, task: dict = Body(...)):
    title = task.get("title", "").strip()

    if not title:
        return JSONResponse(
            status_code=400,
            content={"error": "Title is required"},
        )

    updated = update_task(
        task_id,
        title,
        task.get("done", False),
    )

    if updated is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"},
        )

    return updated


# DELETE /tasks/{id}

@app.delete("/tasks/{task_id}", status_code=204)
def remove_task(task_id: int):
    deleted = delete_task(task_id)

    if not deleted:
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"},
        )

    return Response(status_code=204)

