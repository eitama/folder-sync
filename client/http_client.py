import asyncio
import os
import urllib.parse
import httpx
import urllib
from models.config import Client
from models.data import Folder
from models.file_ops import Delete

client = httpx.AsyncClient(timeout=120)
files_endpoint = 'files'

MAX_CONCURRENT_UPLOADS = 10
semaphore = asyncio.Semaphore(MAX_CONCURRENT_UPLOADS)

async def upload_file(relative_path: str, local_full_path: str, target_url: str):
    # Wait to acquire the semaphore
    async with semaphore:
        with open(local_full_path, 'rb') as f:
            files = {'file': (relative_path, f, 'application/octet-stream')}
            try:
                response = await client.post(target_url, files=files)
                print(f"{relative_path} uploaded with status {response.status_code}")
            except httpx.HTTPStatusError as e:
                print(f"Failed to upload {relative_path}: {e}")

async def upload_all_files(base_path: str, files_to_copy: set[str], target_address: str, name: str):
    # Create upload tasks for each file path
    target_url = build_base_url(target_address=target_address, path=f"files/{name}/upload")
    tasks = [
        upload_file(relative_path, os.path.join(base_path, relative_path), target_url)
        for relative_path in files_to_copy
    ]
    # Wait for all uploads to complete
    await asyncio.gather(*tasks)

async def delete_all_files(base_path: str, old_files_to_delete: set[str], target_address: str, name: str):
    target_url = build_base_url(target_address=target_address, path=f"files/{name}/delete")
    delete_body = Delete(files_to_delete=list(old_files_to_delete))
    try:
        response = await client.post(target_url, json=delete_body.model_dump())
    except httpx.HTTPStatusError as e:
        print(f"Failed to delete files: {e}")

async def get_target_files_state(target_address: str, name: str) -> Folder:
    url = build_base_url(target_address=target_address, path=f"files/{name}")
    r = await client.get(url)
    r.raise_for_status()
    return Folder.model_validate(r.json())

def build_base_url(target_address: str, path: str):
    return urllib.parse.urljoin(f"http://{target_address}/", path)
