from __future__ import annotations
import os
from utils.jsons import read_json, write_json
from pydantic import BaseModel
from typing import TypeVar, Type, Generic

T = TypeVar('T', bound=BaseModel)

class DataConnector(Generic[T]):
    def __init__(self, relative_file_path: str, cls: Type[T], default_data: T) -> None:
        self.cls = cls
        self._data: T = None
        self._data_mtime = float(0)
        self._data_path = relative_file_path
        if not os.path.exists(self._data_path):
            self.update_data(default_data)

    def update_data(self, data: T):
        write_json(self._data_path, data)
        self._data = data
        self._data_mtime = os.path.getmtime(self._data_path)

    def get(self) -> T:
        new_mtime = os.path.getmtime(self._data_path)
        if self._data == None or self._data_mtime != new_mtime:
            self._data = read_json(self._data_path, self.cls)
            self._data_mtime = new_mtime
        return self._data