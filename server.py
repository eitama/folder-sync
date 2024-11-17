import os
import uvicorn
from fastapi import FastAPI, Response, UploadFile, File, Request
from models.file_ops import Delete
from server.exceptions import UnicornException
from server.storage import get_config_dc, get_data_dc
from shared.files import FileHandler

app = FastAPI()
fh = FileHandler(get_config_dc(), get_data_dc())

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    import traceback
    return Response(
        content=traceback.format_exc()
        )

@app.get("/files/{name}")
async def files(name: str):
    print(f"Get {name}")
    return fh.get_folder_metadata(name)

@app.post("/files/{name}/upload")
def upload(name: str, request: Request, file: UploadFile = File(...)):
    base_path = get_config_dc().get().folders[name].base_path
    print(f"Upload request for: {file.filename}")
    try:
        full_path = os.path.join(base_path, file.filename)
        dir_path = os.path.dirname(full_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with open(full_path, 'wb') as f:
            while contents := file.file.read(1024 * 1024):
                f.write(contents)
    except Exception:
        raise UnicornException(name=name)
    finally:
        file.file.close()
    return {"message": f"Successfully uploaded {file.filename}"}

@app.post("/files/{name}/delete")
def delete(name: str, request_body: Delete):
    base_path = get_config_dc().get().folders[name].base_path
    for file in request_body.files_to_delete:
        os.remove(os.path.join(base_path, file))
    return {"message": f"Successfully delete files."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)