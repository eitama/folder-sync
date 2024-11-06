import os
import threading
from nicegui import ui, run, app
from nicegui.elements.card import Card
from nicegui.elements.button import Button
from nicegui.elements.spinner import Spinner
from typing import Dict
import asyncio
from dataclasses import dataclass
from client.http_client import get_target_files_state, upload_all_files, delete_all_files
from client.storage import get_config_dc, get_data_dc
from models.config import TrackingFolder
from shared.files import FileHandler
from shared.systray import init_systray_icon

@dataclass
class FolderRow():
    cardRow: Card
    syncButton: Button
    deleteButton: Button
    spinner: Spinner

communication_queue = asyncio.Queue()
systray_init_done = False
dark = ui.dark_mode(True)
folder_rows: Dict[str, FolderRow] = {}
input_name = None
input_base_path = None
add_folder_button = None
conf_panel = ui.expansion('Configuration', icon='work').classes('w-full')
folders_panel = ui.expansion('Folders', icon='work').classes('w-full')
folders_panel.open()
timer = None

fh = FileHandler(get_config_dc(), get_data_dc())

def remove_folder(folder_to_delete: TrackingFolder):
    config = get_config_dc().get()
    folders = {k: v for k, v in config.folders.items() if v.uuid != folder_to_delete.uuid}
    folder_rows.get(folder_to_delete.uuid).cardRow.delete()
    folder_rows.pop(folder_to_delete.uuid)
    config.folders = folders
    get_config_dc().update_data(config)

async def add_saved_folders():
    config = get_config_dc().get()
    for _, folder in config.folders.items():
        await add_folder_row(folder)

async def add_folder(folder: TrackingFolder):
    config = get_config_dc().get()
    if not os.path.exists(folder.base_path):
        raise Exception(f"Folder: {folder.base_path} not found.")
    
    if folder.name in config.folders.keys():
        raise Exception(f"Folder: {folder.name} already being tracked.")
    
    input_name.value = ""
    input_base_path.value = ""
    config.folders[folder.name] = folder
    get_config_dc().update_data(config)
    await add_folder_row(folder)

async def sync_folder(folder: TrackingFolder):
    global folder_rows
    client = get_config_dc().get().client
    folder_rows[folder.uuid].syncButton.disable()
    folder_rows[folder.uuid].deleteButton.disable()
    folder_rows[folder.uuid].spinner.set_visibility(True)

    try:
        local_folder_state = await run.cpu_bound(fh.get_folder_metadata, folder.name)
        target_folder_state = await get_target_files_state(client.dest_address, folder.name)

        new_files_to_copy = set(local_folder_state.files.keys()) - set(target_folder_state.files.keys())
        old_files_to_delete = set(set(target_folder_state.files.keys() - local_folder_state.files.keys()))
        
        changed_files_to_copy = {
            key for key in local_folder_state.files.keys() & target_folder_state.files.keys()
            if local_folder_state.files[key].md5 != target_folder_state.files[key].md5
        }
        
        files_to_copy = new_files_to_copy.union(changed_files_to_copy)
        await upload_all_files(folder.base_path, files_to_copy, client.dest_address, folder.name)
        await delete_all_files(folder.base_path, old_files_to_delete, client.dest_address, folder.name)
    except:
        pass

    folder_rows[folder.uuid].syncButton.enable()
    folder_rows[folder.uuid].deleteButton.enable()
    folder_rows[folder.uuid].spinner.set_visibility(False)

async def add_folder_row(folder: TrackingFolder):
    global folder_rows
    with folders_panel:
        card = ui.card().props("square outline").style("width: 80%")
        with card:
            with ui.row().classes('items-center').style("width: 100%"):
                ui.label(folder.name).style("border: solid 1px; width: 150px; padding: 10px")
                ui.label(folder.base_path).style("border: solid 1px; width: 250px; padding: 10px")
                ui.space()
                spinner = ui.spinner()
                spinner.set_visibility(False)
                sync = ui.button("Sync", on_click=lambda: sync_folder(folder))
                delete = ui.button("Delete", on_click=lambda: remove_folder(folder))
                folder_rows[folder.uuid] = FolderRow(card, sync, delete, spinner)
        card.move(target_container=folders_panel)

async def input_changed():
    global input_name, input_base_path, add_folder_button
    print(f"{input_name.value}, {input_base_path.value}")
    if input_name.value and input_base_path.value:
        add_folder_button.enable()
    else:
        add_folder_button.disable()

def config_changed():
    global timer
    config = get_config_dc().get()
    config.client.dest_address = input_target_address.value
    if timer:
        timer.cancel()
        timer = None
    timer = ui.timer(callback=lambda: get_config_dc().update_data(config), once=True, interval=3.0)

with conf_panel:
    config = get_config_dc().get()
    input_target_address = ui.input("Target IP/Host", on_change=config_changed, value=config.client.dest_address)
    
with folders_panel:
    with ui.card().style("width: 80%"), ui.row().classes('items-center').style("width: 100%"):
        input_name = ui.input("Name ", on_change=input_changed)
        input_base_path = ui.input("Base Path ", on_change=input_changed)
        ui.space()
        add_folder_button = ui.button(text="Add Folder", on_click=lambda: add_folder(TrackingFolder(name=input_name.value, base_path=input_base_path.value)))
        add_folder_button.disable()

def handle_exit():
    app.shutdown()

async def handle_queue_messages():
    while True:
        try:
            event = await communication_queue.get()
            print(event)
            if event == "Exit":
               handle_exit()
        except asyncio.QueueEmpty:
            print("Sleeping")
            await asyncio.sleep(5)

def add_tray_icon():
    global systray_init_done
    if not systray_init_done:
        systray_init_done = True
        tray_thread = threading.Thread(target=init_systray_icon, args=(communication_queue,), daemon=True)
        tray_thread.start()

ui.timer(0.1, handle_queue_messages, once = True)
ui.timer(0.5, add_tray_icon, once = True)

if __name__ in {'__mp_main__', '__main__'}:
    asyncio.run(add_saved_folders())
    ui.run(show=False, reload=False)