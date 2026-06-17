from fastapi import FastAPI, Depends, HTTPException
from todo.database import get_db_connection
import asyncpg
from todo.models import User, ToDo


app = FastAPI()

@app.post("/register")
async def register(user: User, db: asyncpg.Connection = Depends(get_db_connection)):
    await db.execute("INSERT INTO users (username, password) VALUES ($1, $2)", user.username, user.password)
    return {"message": "User registered successfully!"}

@app.post("/todos")
async def create(todo: ToDo, db: asyncpg.Connection = Depends(get_db_connection)):
    row = await db.fetchrow('''
INSERT INTO todo (user_id, title, description, completed) VALUES ($1, $2, $3, $4) RETURNING user_id, id
                     ''', todo.user_id, todo.title, todo.description, todo.completed)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": row["id"], "title": todo.title, "description": todo.description, "completed": todo.completed}

@app.get("/todos/{id}")
async def read(id: int, db: asyncpg.Connection = Depends(get_db_connection)):
    row = await db.fetchrow('''
SELECT id, user_id, title, description, completed FROM todo WHERE id = $1
                     ''', id)
    if row:
        if not row["user_id"]:
            raise HTTPException(status_code=404, detail="User not found")
        return row
    raise HTTPException(status_code=404, detail="ID not found")

@app.put("/todos/{id}")
async def update(id: int, todo: ToDo, db: asyncpg.Connection = Depends(get_db_connection)):
    row = await db.execute('''
    UPDATE todo SET user_id = $5, title = $2, description = $3, completed = $4 WHERE id = $1
    RETURNING user_id      ''', id, todo.title, todo.description, todo.completed, todo.user_id)
    if row:
        return {"id": id, "title": todo.title, "description": todo.description, "completed": todo.completed}
    raise HTTPException(status_code=404, detail="User not found")

@app.delete("/todos/{id}")
async def delete_todo(id: int, db: asyncpg.Connection = Depends(get_db_connection)):
    row = await db.execute('''
DELETE FROM todo WHERE id = $1 RETURNING user_id
                     ''', id)
    if row:
        return {"message": "Task from {row['user_id']} deleted successfully!"}
    raise HTTPException(status_code=404, detail="User not found")

@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: asyncpg.Connection = Depends(get_db_connection)):
    await db.execute('''
DELETE FROM users WHERE id = $1
                     ''', user_id)
    return {"message": "User deleted successfully!"}