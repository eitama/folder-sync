from typing import Dict, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

def uuid4str() -> str:
    return str(uuid4())

class TrackingFolder(BaseModel):
    name: str
    base_path: str
    uuid: str = Field(default_factory=uuid4str)

class Concurrency(BaseModel):
    max_workers: int = 4

class Client(BaseModel):
    dest_address: str = "127.0.0.1:8000"
    mac_address: Optional[str] = None

class Configuration(BaseModel):
    folders: Dict[str, TrackingFolder] = {"Example": TrackingFolder(name="Example", base_path="D:\\Example")} # name -> TrackingFolder
    concurrency: Concurrency = Concurrency()
    client: Client = Field(default_factory=Client)