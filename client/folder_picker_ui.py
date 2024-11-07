from utils.folder_selector import FolderSelector
from nicegui import ui
from nicegui.elements.list import List
from nicegui.events import ClickEventArguments
from typing import cast

fs_dialog = None
options = {}

def select_next(fs: FolderSelector, options_list: List, item: ClickEventArguments):
    next = options[item.sender]
    fs.move_to(next)
    update_list(fs, options_list)

def select_prev(fs: FolderSelector, options_list: List):
    fs.go_back()
    update_list(fs, options_list)

def update_list(fs: FolderSelector, options_list: List):
    options_list.clear()
    for option in fs.get_next_options():
        item = ui.item(option, on_click=lambda item: select_next(fs, options_list, item))
        options[item] = option
        item.move(options_list)

async def pick_folder():
    global fs_dialog, options
    fs: FolderSelector = FolderSelector()
    with ui.dialog() as dialog, ui.card().classes('w-full'):
        fs_dialog = dialog
        with ui.column().classes('w-full'):
            ui.label('Choose a folder')
            with ui.row().classes('w-full'):
                with ui.scroll_area().classes('w-full h-32 border'):
                    with ui.list().props('dense').classes('w-full') as options_list:
                        update_list(fs, options_list)
            with ui.row():
                ui.button('Back', on_click=lambda: select_prev(fs, options_list))
                ui.button('Cancel', on_click=lambda: dialog.submit(None))
                ui.button('Select', on_click=lambda: dialog.submit(fs.get_selected()))

    result = await dialog
    fs_dialog.close()
    fs_dialog.delete()
    fs_dialog = None
    fs = None
    options = {}
    return result