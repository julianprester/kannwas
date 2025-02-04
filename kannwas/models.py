from typing import Optional
from pydantic import BaseModel

class Student(BaseModel):
    id: int
    sid: int
    name: str
    unikey: str
    email: str
    section: Optional[str]
    group: Optional[str]

class DiscussionEntry(BaseModel):
    id: int
    user_id: int
    type: str
    message: str
    created_at: str
    updated_at: str
