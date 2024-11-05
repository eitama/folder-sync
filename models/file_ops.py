from typing import List
from pydantic import BaseModel

class Delete(BaseModel):
    files_to_delete: List[str]