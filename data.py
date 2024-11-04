from __future__ import annotations
import jsons
from typing import List, Dict
from pydantic import BaseModel

_data: Data = None

class File(BaseModel):
    dateModified: float
    md5: str = ""

class Folder(BaseModel):
    name: str
    base_path: str
    files: Dict[str, File] = {}

class Data(BaseModel):
    folders: Dict[str, Folder] = {}

def save_data():
    global _data
    jsons.write_json('data.json', _data)

def update_folder_data(folder: Folder):
    global _data
    _data.folders[folder.name] = folder
    save_data()

def get_data() -> Data:
    global _data
    if _data == None:
        try:
            _data = jsons.read_json('data.json', Data)
        except:
            _data = Data()
    return _data

def get_previous_folder_data(name: str, base_path: str) -> Folder:
    return get_data().folders.get(name) if name in get_data().folders.keys() else Folder(base_path=base_path, name=name, files={})