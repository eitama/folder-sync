import os
from typing import Dict, Set
from models.config import Configuration
from models.data import Data, File, Folder
import hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed

from utils.data_connector import DataConnector

class FileHandler():
    def __init__(self, config_dc: DataConnector[Configuration], data_dc: DataConnector[Data]) -> None:
        self.num_workers = config_dc.get().concurrency.max_workers
        self.config_dc = config_dc
        self.data_dc = data_dc
    
    def consolidate_folder_data(self, folder: Folder) -> Folder:
        existing_files_from_disk = self.get_existing_files_metadata(folder.base_path)
        
        new_files_on_disk = set(existing_files_from_disk.keys()) - set(folder.files.keys())
        
        changed_files = {
            key for key in existing_files_from_disk.keys() & folder.files.keys()
            if existing_files_from_disk[key].dateModified != folder.files[key].dateModified
        }
        
        unchanged_files = {
            key for key in existing_files_from_disk.keys() & folder.files.keys()
            if existing_files_from_disk[key].dateModified == folder.files[key].dateModified
        }

        new_dict = {key: file for key, file in folder.files.items() if key in unchanged_files}

        changed_files.update(new_files_on_disk)
        processed_dict = self.process_files(folder.base_path, changed_files)
        new_dict.update(processed_dict)
        
        return Folder(name=folder.name, base_path=folder.base_path, files=new_dict)

    def process_files(self, base_path: str, file_paths: Set[str]) -> Dict[str, Dict]:
        result_dict = {}
        if not file_paths:
            return result_dict
        
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            future_to_path = {executor.submit(self.process_file, base_path, path): path for path in file_paths}
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                file = future.result()
                result_dict[path] = file
        
        return result_dict

    def process_file(self, base_path: str, file_path: str) -> File:
        last_modified = self.get_file_last_modified(os.path.join(base_path, file_path))
        md5 = self.get_file_md5(os.path.join(base_path, file_path))
        return File(dateModified=last_modified, md5=md5)

    def get_file_last_modified(self, file_path: str) -> float:
        return os.path.getmtime(file_path)

    def get_file_md5(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_md5.update(chunk)
        digest = hash_md5.hexdigest()
        print(f"MD5 for: {file_path} - {digest}")
        return digest

    def get_existing_files_metadata(self, parentPath: str) -> Dict[str, File]:
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
    
    def get_folder_metadata(self, name: str) -> Folder:
        if not name in self.config_dc.get().folders.keys():
            raise FileNotFoundError(f"{name} not configured in config.json")
        
        base_path = self.config_dc.get().folders.get(name).base_path
        folder = self.get_previous_folder_data(name=name, base_path=base_path)
        fresh_folder_data = self.consolidate_folder_data(folder=folder)
        self.update_folder_data(fresh_folder_data)
        return fresh_folder_data

    def get_previous_folder_data(self, name: str, base_path: str) -> Folder:
        return self.data_dc.get().folders.get(name) if name in self.data_dc.get().folders.keys() else Folder(base_path=base_path, name=name, files={})

    def update_folder_data(self, folder: Folder):
        data = self.data_dc.get()
        data.folders[folder.name] = folder
        self.data_dc.update_data(data)
