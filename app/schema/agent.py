from pydantic import BaseModel

class Invoke(BaseModel):
    task: str