## AI vs me

####

## My prompt

Create a REST API in Python powered by FastAPI, to manage a to-do list in memory (no database). There are integers of task `id`, strings of task `title`, and booleans of task `done` (default as `false`). Fill in with 3 sample tasks. Implement:

- `GET /` returning `{"name","version","endpoints"}`
When a person accesses the service with a GET request to `/health`, it returns a status=ok message.
The list is returned by `GET /tasks`.
- `GET /tasks/{id}` returning one task or a `404` with `{"error": "..."}` if not found
Timely return of the created task body as a result of the POST /tasks call, setting a default status of done to false and assigning a unique id, returning 201, and returning 400 with a JSON error if the title is not specified or is empty.
PUT /tasks/{id} (replaces `title` and/or `done` in the request body; returns the updated task or `404` / `400` as appropriate)
DELETE /tasks/{id} returning 204 (no body) or 404 if id is not found

Expose interactive Swagger docs at /docs.

####

## AI vs me findings

What the AI can do better and does frequently: cleaner separation of Pydantic models, or adds type hints/docstrings more consistently than a first-pass hand-written version.

What it sows and what it leaves: Errors are returned as default 422 whereas it was looking for the requested 400 and/or errors are wrapped in an object of the form "detail" instead of "error".

What the prompt never mentions and the AI implicitly assumes: if the body is empty, should the PUT delete the entry from the database? (Yes, it should!) 

Should ids be reused after a delete? No, they shouldn't!. 
Does the title get .strip() ped? (Yes, it should!)


####

## One Rematch

#### AI Prompt: Build a REST API with FastAPI

Create a REST API in **Python** using **FastAPI** to manage an **in-memory to-do list** (no database or file storage).

#### Requirements

- Store tasks in memory only.
- Each task must contain:
  - `id` (integer)
  - `title` (string)
  - `done` (boolean, default: `false`)
- Pre-populate the application with **3 sample tasks**.

## Endpoints

### `GET /`

Return JSON containing:

```json
{
  "name": "...",
  "version": "...",
  "endpoints": [...]
}
```

### `GET /health`

Return:

```json
{
  "status": "ok"
}
```

### `GET /tasks`

- Return the complete list of tasks.

### `GET /tasks/{id}`

- Return the matching task.
- If the task does not exist, return **404 Not Found** with:

```json
{
  "error": "Task not found"
}
```

### `POST /tasks`

Accept:

```json
{
  "title": "..."
}
```

Behavior:

- Automatically assign the next available unique integer `id`.
- Set `done` to `false`.
- Return **201 Created** with the created task.
- If `title` is missing, empty, or contains only whitespace, return **400 Bad Request** with:

```json
{
  "error": "..."
}
```

> **Important:** Do **not** use FastAPI's default **422 Unprocessable Entity** response for validation errors.

### `PUT /tasks/{id}`

- Allow updating `title` and/or `done`.
- Return the updated task.
- Return **404 Not Found** if the task does not exist.
- Return **400 Bad Request** for invalid input (e.g., an empty `title`).

### `DELETE /tasks/{id}`

- Delete the task.
- Return **204 No Content** with an empty response body.
- Return **404 Not Found** if the task does not exist.

## Additional Requirements

- Use **Pydantic models** where appropriate.
- Use **Python type hints** throughout the code.
- Keep all data **in memory only**.
- IDs must always increase and **must not be reused** after a task is deleted.
- Strip leading and trailing whitespace from `title` before validation.
- Return errors in the format:

```json
{
  "error": "..."
}
```

instead of FastAPI's default:

```json
{
  "detail": "..."
}
```

- Expose the automatically generated **Swagger UI** at **`/docs`**.
- Organize the code cleanly with separate models, route handlers, and comments.
- Provide the complete runnable source code in a single file named **`main.py`**.
- The application should be runnable using:

```bash
uvicorn main:app --reload
```