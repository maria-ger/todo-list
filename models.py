from pydantic import BaseModel
from pydantic_settings import BaseSettings
from datetime import datetime

class Settings(BaseSettings):
    DATABASE_URL: str = ""

class User(BaseModel):
    username: str
    password: str

class ToDo(BaseModel):
    user_id: int
    title: str
    description: str
    completed: bool = False
    created_at: datetime
    completed_at: datetime | None = None