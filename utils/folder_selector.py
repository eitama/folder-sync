from typing import List
import os

class FolderSelector:
    def __init__(self):
        self.selections = []

    def go_back(self) -> None:
        self.selections.pop()

    def move_to(self, next_folder: str) -> None:
        self.selections.append(next_folder)

    def get_next_options(self) -> List[str]:
        if len(self.selections) == 0:
            return os.listdrives()
        else:
            return [f.name for f in os.scandir(os.path.join(*self.selections)) if f.is_dir()]
    
    def get_selected(self) -> str:
        return os.path.join(*self.selections)

