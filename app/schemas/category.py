from pydantic import BaseModel

class Create_Category_Request(BaseModel):
    name: str
