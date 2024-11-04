from typing import Dict
from pydantic import BaseModel
import jsons

_config = None

class Configuration(BaseModel):
    folders: Dict[str, str] = {}

def get_config() -> Configuration:
    global _config
    if _config == None:
        try:
            _config = jsons.read_json("config.json", Configuration)
        except:
            _config = Configuration()
    return _config

def write_config(config: Configuration):
    jsons.write_json("config.json", config)