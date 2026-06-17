import asyncpg
import asyncio
from dotenv import load_dotenv
from todo.models import Settings

load_dotenv()

settings = Settings()
DATABASE_URL = settings.DATABASE_URL

async def create_tables():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS todo (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            completed BOOL NOT NULL
        )
    ''')
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    await conn.execute('''
        ALTER TABLE todo ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
    ''')
    await conn.close()

asyncio.run(create_tables())
