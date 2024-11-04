import os
from typing import Dict
import config
from data import File, Folder
import hashlib

def get_folder_data(folder: Folder) -> Folder:
    if not folder.name in config.get_config().folders:
        raise FileNotFoundError(f"{folder.name} not configured in config.json")
    
    existing_files_from_disk = get_existing_files_metadata(folder.base_path)
    new_files_on_disk = set(existing_files_from_disk.keys()) - set(folder.files.keys())
    
    changed_files = {
        key for key in existing_files_from_disk.keys() & folder.files.keys()
        if existing_files_from_disk[key].dateModified != folder.files[key].dateModified
    }
    
    unchanged_files = {
        key for key in existing_files_from_disk.keys() & folder.files.keys()
        if existing_files_from_disk[key].dateModified == folder.files[key].dateModified
    }

    new_file_dict = {key: file for key, file in folder.files.items() if key in unchanged_files}
    for file_path in changed_files:
        last_modified = existing_files_from_disk.get(file_path).dateModified
        md5 = get_file_md5(os.path.join(folder.base_path, file_path))
        new_file_dict[file_path] = File(dateModified=last_modified, md5=md5)

    for file_path in new_files_on_disk:
        last_modified = get_file_last_modified(os.path.join(folder.base_path, file_path))
        md5 = get_file_md5(os.path.join(folder.base_path, file_path))
        new_file_dict[file_path] = File(dateModified=last_modified, md5=md5)
    
    return Folder(name=folder.name, base_path=folder.base_path, files=new_file_dict)

def get_file_last_modified(file_path: str) -> float:
    return os.path.getmtime(file_path)

def get_file_md5(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):  # 4KB chunks
            hash_md5.update(chunk)
    digest = hash_md5.hexdigest()
    print(f"MD5 for: {file_path} - {digest}")
    return digest

def get_existing_files_metadata(parentPath: str) -> Dict[str, File]:
    """Recursively get all files within parentPath with their modified timestamps.
    
    Args:
        parentPath (str): The path of the directory to scan.
        
    Returns:
        Dict[str, float]: A dictionary where the keys are relative file paths
                          and values are their last modified timestamps.
    """
    files_with_timestamps: Dict[str, File] = {}

    # Walk through directory tree
    for root, _, files in os.walk(parentPath):
        for file in files:
            # Full file path
            full_path = os.path.join(root, file)
            # Relative file path
            relative_path = os.path.relpath(full_path, parentPath)
            # Modified time
            modified_time = os.path.getmtime(full_path)
            # Store in dictionary
            files_with_timestamps[relative_path] = File(dateModified=modified_time)
    
    return files_with_timestamps