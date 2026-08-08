## Week 3

### Why SQLite?
SQLite requires no separate server process or installation, it stores all data in a single database file (`tasks.db`) and is included as part of Python's standard library. 
This makes it an ideal choice for a small project like this: it requires virtually no setup, is lightweight, and preserves data across application restarts. 
While SQLite is excellent for single-user or low-concurrency applications, larger systems with many simultaneous users or distributed, multi-server deployments are better served by a client-server database such as PostgreSQL.

##
### DB Browser screenshot
###
![DB Browser screenshot](Verification_screenshot_of_DB_Browser(Task4).png)


## W3-A3 Containerize your stack

## Run PostgreSQL

```bash
docker run --name taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5432:5432 -v taskdata:/var/lib/postgresql/data -d postgres:16
```

## Connect Database

```bash
python -m uvicorn app:app --reload
```

## Stage 2: Read from PostgreSQL

* Updated the API to read task data directly from the PostgreSQL database using parameterized `psycopg` queries.
* Implemented `GET /tasks` to return all tasks and `GET /tasks/{id}` to retrieve a single task by its ID.
* Preserved the existing API behavior by returning `404` with `{"error": "Task not found"}` for unknown task IDs.
* Verified that all task data is fetched from PostgreSQL instead of in-memory storage or SQLite.

### Start the application
```bash
python -m uvicorn app:app --reload
```
### Get all tasks
```bash
curl.exe -i http://localhost:8000/tasks
```
### Get a task by ID
```bash
curl.exe -i http://localhost:8000/tasks/1
```
### Verify a non-existent task returns 404
```bash
curl.exe -i http://localhost:8000/tasks/999
```

## Stage 3: Full CRUD with PostgreSQL

* Implemented full CRUD operations using PostgreSQL and parameterized `psycopg` queries.
* Added support for creating, updating, and deleting tasks while preserving input validation and appropriate HTTP status codes.
* Used `RETURNING` in `INSERT`, `UPDATE`, and `DELETE` queries to simplify responses and detect missing records.
* Verified the complete CRUD workflow with PostgreSQL, including `201`, `200`, `204`, and `404` responses.

### Create a task
```bash
curl.exe -i -X POST http://localhost:8000/tasks ^
-H "Content-Type: application/json" ^
-d "{\"title\":\"Finish Stage 3\",\"done\":false}"
```
### Get all tasks
```bash
curl.exe -i http://localhost:8000/tasks
```
### Update a task (replace `4` with the actual task ID)
```bash
curl.exe -i -X PUT http://localhost:8000/tasks/4 ^
-H "Content-Type: application/json" ^
-d "{\"title\":\"Finish Stage 3\",\"done\":true}"
```
### Delete a task
```bash
curl.exe -i -X DELETE http://localhost:8000/tasks/4
```
### Verify the task was deleted
```bash
curl.exe -i http://localhost:8000/tasks/4
```
### Verify the database directly (optional)
```bash
docker exec -it taskdb psql -U postgres -d tasks
```

Inside PostgreSQL:

```sql
SELECT * FROM tasks;
```

Exit:
```sql
\q
```

