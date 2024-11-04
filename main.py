import uvicorn
from fastapi import FastAPI
from files import get_folder_data
from config import get_config
from data import get_previous_folder_data, update_folder_data

app = FastAPI()

@app.get("/files/{name}")
async def files(name: str):
    return get_folder_metadata(name)

def get_folder_metadata(name: str):
    base_path = get_config().folders.get(name)
    folder = get_previous_folder_data(name=name, base_path=base_path)
    fresh_folder_data = get_folder_data(folder=folder)
    update_folder_data(fresh_folder_data)
    return fresh_folder_data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)