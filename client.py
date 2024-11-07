import os
import threading
from nicegui import ui, run, app
from nicegui.elements.card import Card
from nicegui.elements.button import Button
from nicegui.elements.spinner import Spinner
from nicegui.elements.label import Label
from nicegui.elements.input import Input
from typing import Dict
import asyncio
from dataclasses import dataclass
from client.http_client import get_target_files_state, upload_all_files, delete_all_files, UploadResult, UploadResultEnum
from client.storage import get_config_dc, get_data_dc
from models.config import TrackingFolder
from shared.files import FileHandler
from shared.systray import init_systray_icon
from client.folder_picker_ui import pick_folder

@dataclass
class FolderRow():
    cardRow: Card
    syncButton: Button
    deleteButton: Button
    spinner: Spinner
    status_label: Label

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

async def track_upload_status(queue: asyncio.Queue[UploadResult], total: int, folder: TrackingFolder):
    if total == 0:
        return
    uploaded_count = 1
    while True:
        result = await queue.get()
        if result.result == UploadResultEnum.SUCCESS:
            # TODO: Implement
            pass
        else:
            # TODO: Implement
            pass
        
        uploaded_count += 1
        folder_rows[folder.uuid].status_label.set_text(f"Uploading {uploaded_count}/{total}")
        if uploaded_count > total:
            queue.task_done()
            return

async def sync_folder(folder: TrackingFolder):
    global folder_rows
    client = get_config_dc().get().client
    folder_rows[folder.uuid].syncButton.disable()
    folder_rows[folder.uuid].deleteButton.disable()
    folder_rows[folder.uuid].spinner.set_visibility(True)

    try:
        folder_rows[folder.uuid].status_label.set_text("Scanning...")
        local_folder_state_task = run.cpu_bound(fh.get_folder_metadata, folder.name)
        folder_rows[folder.uuid].status_label.set_text("Fetching remote state...")
        target_folder_state_task = get_target_files_state(client.dest_address, folder.name)
        local_folder_state, target_folder_state = await asyncio.gather(local_folder_state_task, target_folder_state_task)

        new_files_to_copy = set(local_folder_state.files.keys()) - set(target_folder_state.files.keys())
        old_files_to_delete = set(set(target_folder_state.files.keys() - local_folder_state.files.keys()))
        
        changed_files_to_copy = {
            key for key in local_folder_state.files.keys() & target_folder_state.files.keys()
            if local_folder_state.files[key].md5 != target_folder_state.files[key].md5
        }
        
        queue = asyncio.Queue[UploadResult]()
        files_to_copy = new_files_to_copy.union(changed_files_to_copy)
        folder_rows[folder.uuid].status_label.set_text(f"Uploading 1/{len(files_to_copy)}")
        tasks = []
        
        if len(files_to_copy) > 0:
            upload_task = upload_all_files(folder.base_path, files_to_copy, client.dest_address, folder.name, queue)
            track_task = track_upload_status(queue, len(files_to_copy), folder)
            tasks.extend([upload_task, track_task])
        if len(old_files_to_delete) > 0:
            delete_task = delete_all_files(folder.base_path, old_files_to_delete, client.dest_address, folder.name)
            tasks.append(delete_task)
        await asyncio.gather(*tasks)
        folder_rows[folder.uuid].status_label.set_text("Idle")
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
                ui.label(folder.base_path).style("border: solid 1px; width: 400px; padding: 10px")
                ui.space()
                spinner = ui.spinner()
                status_label = ui.label("Idle")
                spinner.set_visibility(False)
                sync = ui.button("Sync", on_click=lambda: sync_folder(folder))
                sync.tooltip("Sync folder to remote system.")
                delete = ui.button("Delete", on_click=lambda: remove_folder(folder))
                delete.tooltip("Delete tracked folder from list. (Does not delete any files at all.)")
                folder_rows[folder.uuid] = FolderRow(card, sync, delete, spinner, status_label)
        card.move(target_container=folders_panel)

async def input_changed():
    global input_name, input_base_path, add_folder_button
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

async def browser_folder(input_base_path: Input):
    result = await pick_folder()
    input_base_path.set_value(result)

with conf_panel:
    config = get_config_dc().get()
    input_target_address = ui.input("Target IP/Host", on_change=config_changed, value=config.client.dest_address)
    
with folders_panel:
    with ui.card().style("width: 80%"), ui.row().classes('items-center').style("width: 100%"):
        input_name = ui.input("Name ", on_change=input_changed)
        input_base_path = ui.input("Base Path ", on_change=input_changed).classes("w-1/2")
        ui.space()
        add_browse_button = ui.button(text="Browse", on_click=lambda: browser_folder(input_base_path))
        add_folder_button = ui.button(text="Add Folder", on_click=lambda: add_folder(TrackingFolder(name=input_name.value, base_path=input_base_path.value)))
        add_folder_button.disable()

def handle_exit():
    app.shutdown()

async def handle_queue_messages():
    while True:
        try:
            event = await communication_queue.get()
            if event == "Exit":
               handle_exit()
        except asyncio.QueueEmpty:
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
    ui.run(show=False, reload=False, title="Folder Sync")