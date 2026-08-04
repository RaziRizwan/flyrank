from fastapi import FastAPI
from database import init_db
from database import init_db, get_all_tasks, get_task_by_id
from fastapi.responses import JSONResponse

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