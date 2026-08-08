import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    return psycopg.connect(DATABASE_URL)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN DEFAULT FALSE
                );
            """)

            cur.execute("SELECT COUNT(*) FROM tasks;")
            count = cur.fetchone()[0]

            if count == 0:
                cur.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    [
                        ("Learn FastAPI", False),
                        ("Connect PostgreSQL", False),
                        ("Finish Assignment", False),
                    ],
                )

        conn.commit()
        
def get_all_tasks():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, done
                FROM tasks
                ORDER BY id;
            """)
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "done": row[2]
        }
        for row in rows
    ]


def get_task_by_id(task_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, done
                FROM tasks
                WHERE id = %s;
                """,
                (task_id,)      # parameterized query
            )

            row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "title": row[1],
        "done": row[2]
    }
    

# create a task
def create_task(title: str, done: bool = False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tasks (title, done)
                VALUES (%s, %s)
                RETURNING id, title, done;
                """,
                (title, done),
            )

            row = cur.fetchone()
        conn.commit()

    return {
        "id": row[0],
        "title": row[1],
        "done": row[2],
    }


# Update a task
def update_task(task_id: int, title: str, done: bool):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET title = %s,
                    done = %s
                WHERE id = %s
                RETURNING id, title, done;
                """,
                (title, done, task_id),
            )

            row = cur.fetchone()

        conn.commit()

    if row is None:
        return None

    return {
        "id": row[0],
        "title": row[1],
        "done": row[2],
    }

# Delete a task
def delete_task(task_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM tasks
                WHERE id = %s
                RETURNING id;
                """,
                (task_id,),
            )

            row = cur.fetchone()

        conn.commit()

    return row is not None