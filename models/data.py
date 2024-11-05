from pydantic import BaseModel
from typing import Dict

class File(BaseModel):
    dateModified: float
    md5: str = ""

class Folder(BaseModel):
    name: str
    base_path: str
    files: Dict[str, File] = {}

class Data(BaseModel):
    folders: Dict[str, Folder] = {}