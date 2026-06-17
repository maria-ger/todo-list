from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = ""

class User(BaseModel):
    username: str
    password: str

class ToDo(BaseModel):
    id: Optional[None] = None
    user_id: int
    title: str
    description: str
    completed: bool = False