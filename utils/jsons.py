from typing import Any, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def read_json(file_path: str, cls: Type[T]) -> T:
    with open(file_path, 'r') as file:
        json_data = file.read()
        return cls.model_validate_json(json_data)

def write_json(file_path: str, object: T) -> None:
    with open(file_path, 'w') as file:
        file.write(object.model_dump_json(indent=4))