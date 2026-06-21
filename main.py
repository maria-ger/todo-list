from fastapi import FastAPI, Depends, Query, HTTPException
import asyncpg
from contextlib import asynccontextmanager
from databases import Database
from datetime import datetime, timezone
import pytz
from models import Settings, User, ToDo
from dotenv import load_dotenv

load_dotenv()

settings = Settings()

DATABASE_URL = settings.DATABASE_URL
db = Database(DATABASE_URL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(lifespan=lifespan)

@app.post("/register")
async def register(user: User):
    query = "INSERT INTO users (username, password) VALUES (:username, :password)"
    try:
        await db.execute(query, values=user.model_dump())
        return {"message": "User was registered successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User wasn't registered: {str(e)}")

@app.post("/todos")
async def create(todo: ToDo):
    query = '''
INSERT INTO todos (user_id, title, description, completed, created_at, completed_at) 
VALUES (:user_id, :title, :description, :completed, :created_at, :completed_at) RETURNING user_id, id
            '''
    try:
        row = await db.fetch_one(query, values=todo.model_dump())
        if row is None:
            raise HTTPException(status_code=404, detail="Not found")
        return {"id": row["id"], **todo.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task wasn't created: {str(e)}")

@app.get("/todos/")
async def read_tasks(limit: int = Query(10, ge=0, le=100), 
                     offset: int = Query(0, ge=0), 
                     sort_by: str = "id",
                     completed: bool | None = None, title_contains: str | None = None,
                     created_after: str | None = None, created_before: str | None = None):
    conditions = []
    params = {}
    query_parts = ['''
SELECT id, user_id, title, description, completed, created_at FROM todos
WHERE ''']
    if completed is not None:
        conditions.append('completed = :completed')
        params["completed"] = completed
    if title_contains is not None:
        conditions.append("title ILIKE '%' || :title_contains || '%'")
        params["title_contains"] = title_contains
    dt_after = None
    if created_after is not None:
        try:
            dt_after = datetime.fromisoformat(created_after)
            conditions.append('created_at > :dt_after')
            params["dt_after"] = dt_after
        except Exception:
            raise HTTPException(status_code=500, detail="Incorrect date format")
    dt_before = None
    if created_before is not None:
        try:
            dt_before = datetime.fromisoformat(created_before)
            conditions.append('created_at < :dt_before')
            params["dt_before"] = dt_before
        except Exception:
            raise HTTPException(status_code=500, detail="Incorrect date format")
    query_parts.append(' AND '.join(conditions))
    query_parts.append('''
ORDER BY :sort_by
LIMIT :limit
OFFSET :offset ''')
    query = ' '.join(query_parts)
    try: 
        rows = await db.fetch_all(query, {"sort_by": sort_by, "limit": limit, "offset": offset,
                                          **params})
        if rows:
            return rows
        raise HTTPException(status_code=404, detail="Tasks not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while getting tasks: {str(e)}")

@app.get("/todos/{id}")
async def read_task(id: int):
    query = '''
SELECT * FROM todos WHERE id = :id
                     '''
    try:
        row = await db.fetch_one(query, {"id": id})
        if row:
            return row
        raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while getting task: {str(e)}")

@app.get("/todos/analytics")
async def get_analytics(timezone: str = 'UTC'):
    if timezone not in pytz.all_timezones:
        raise HTTPException(status_code=400, detail="Invalid timezone")
    query = f'''
SET timezone = '{timezone}'
'''
    try:
        await db.execute(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    analytics = dict()
    query_tasks_cntr = '''
SELECT COUNT(id) AS num FROM todos
'''
    query_status = '''
SELECT completed, COUNT(completed) AS num FROM todos
GROUP BY completed
'''
    query_avg_time = '''
SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600) as avg_time
FROM todos 
WHERE completed = true
'''
    query_weekdays = '''
WITH weekdays (weekday, ind) AS
(SELECT TO_CHAR(created_at, 'Day'),
        CASE
            WHEN EXTRACT(DOW FROM created_at) != 0 THEN EXTRACT(DOW FROM created_at)
            ELSE 7
        END
 FROM todos)
SELECT weekday, COUNT(weekday) AS num
FROM weekdays
GROUP BY weekday, ind
ORDER BY ind
'''
    try:
        row1 = await db.fetch_one(query_tasks_cntr)
        if row1:
            analytics["total_number_of_tasks"] = row1["num"]
        
        rows2 = await db.fetch_all(query_status)
        if rows2:
            vals = dict()
            for row in rows2:
                vals[row["completed"]] = row["num"]
            analytics["completed_stats"] = vals
        row3 = await db.fetch_one(query_avg_time)
        if row3:
            analytics["avg_time_of_task_completion"] = row3["avg_time"]
        rows4 = await db.fetch_all(query_weekdays)
        if rows4:
            vals = dict()
            for row in rows4:
                vals[row["weekday"]] = row["num"]
            analytics["weekday_distribution"] = vals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return analytics

@app.put("/todos/{id}")
async def update(id: int, todo: ToDo):
    query = '''
        UPDATE todos SET user_id = :user_id, title = :title, description = :description, 
            completed = :completed, created_at = :created_at, completed_at = :completed_at
        WHERE id = :id
        RETURNING *      '''
    try:
        row = await db.fetch_one(query, {"id": id, **todo.model_dump()})
        if row:
            return row
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while updating task: {str(e)}")

@app.patch("/todos")
async def update_status(ids: str, completed: bool):
    list_ids = list(map(int, ids.split(',')))
    upd_cntr = 0
    for id in list_ids:
        query = '''
            UPDATE todos SET completed = :completed
            WHERE id = :id '''
        try:
            await db.execute(query, {"id": id, "completed": completed})
            upd_cntr += 1
        except Exception:
            pass
    return {"updated_count": upd_cntr}

@app.delete("/todos/{id}")
async def delete_todo(id: int):
    query = '''
DELETE FROM todos WHERE id = :id RETURNING user_id
                     '''
    try:
        row = await db.fetch_one(query, values={"id": id})
        if row:
            return {"message": f"Task from {row['user_id']} deleted successfully!"}
        raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while deleting task: {str(e)}")

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    query = '''
DELETE FROM users WHERE id = :user_id RETURNING user_id
                     '''
    try:
        row = await db.execute(query=query, values={"user_id": user_id})
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message":f"User {row['user_id']} deleted successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while deleting user: {str(e)}")
    
@app.get("/")
async def greet():
    return {"message": "Welcome to ToDo-list! Visit /docs for more information."}