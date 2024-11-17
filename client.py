import enum
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
from file_picker import local_file_picker
from getmac import get_mac_address
from wakeonlan import send_magic_packet

class FolderStatus(enum.Enum):
    IDLE = "Idle"
    SYNCING = "Syncing"

@dataclass
class FolderRow():
    status_label: str
    folder: TrackingFolder
    status: FolderStatus = FolderStatus.IDLE
    spinner_visible = False
    buttons_enabled = True

    def set_syncing(self):
        self.status_label = "Syncing..."
        self.status = FolderStatus.SYNCING
        self.spinner_visible = True
        self.buttons_enabled = False

    def set_idle(self):
        self.status_label = "Idle"
        self.status = FolderStatus.IDLE
        self.spinner_visible = False
        self.buttons_enabled = True

communication_queue = asyncio.Queue()
systray_init_done = False
folder_rows: Dict[str, FolderRow] = {}
input_base_path = None
timer = None
dest_address = get_config_dc().get().client.dest_address

fh = FileHandler(get_config_dc(), get_data_dc())

def remove_folder(folder_to_delete: TrackingFolder):
    global folder_rows
    config = get_config_dc().get()
    folders = {k: v for k, v in config.folders.items() if v.uuid != folder_to_delete.uuid}
    folder_rows.pop(folder_to_delete.uuid)
    config.folders = folders
    get_config_dc().update_data(config)
    display_folders.refresh()

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
        folder_rows[folder.uuid].status_label = f"Uploading {uploaded_count}/{total}"
        if uploaded_count > total:
            queue.task_done()
            return

async def sync_folder(folder: TrackingFolder):
    global folder_rows
    print(f"Sync folder: {folder}")
    client = get_config_dc().get().client
    folder_row = folder_rows[folder.uuid]
    folder_row.set_syncing()

    try:
        local_folder_state_task = run.cpu_bound(fh.get_folder_metadata, folder.name)
        target_folder_state_task = get_target_files_state(client.dest_address, folder.name)
        local_folder_state, target_folder_state = await asyncio.gather(local_folder_state_task, target_folder_state_task)
        print("Calculating...")
        new_files_to_copy = set(local_folder_state.files.keys()) - set(target_folder_state.files.keys())
        old_files_to_delete = set(set(target_folder_state.files.keys() - local_folder_state.files.keys()))
        
        changed_files_to_copy = {
            key for key in local_folder_state.files.keys() & target_folder_state.files.keys()
            if local_folder_state.files[key].md5 != target_folder_state.files[key].md5
        }
        
        queue = asyncio.Queue[UploadResult]()
        files_to_copy = new_files_to_copy.union(changed_files_to_copy)
        folder_rows[folder.uuid].status_label = f"Uploading 1/{len(files_to_copy)}"
        tasks = []
        
        if len(files_to_copy) > 0:
            upload_task = upload_all_files(folder.base_path, files_to_copy, client.dest_address, folder.name, queue)
            track_task = track_upload_status(queue, len(files_to_copy), folder)
            tasks.extend([upload_task, track_task])
        if len(old_files_to_delete) > 0:
            delete_task = delete_all_files(folder.base_path, old_files_to_delete, client.dest_address, folder.name)
            tasks.append(delete_task)
        await asyncio.gather(*tasks)
        folder_row.set_idle()
    except:
        pass
    finally:
        folder_row.set_idle()

async def add_folder_row(folder: TrackingFolder):
    global folder_rows
    folder_rows[folder.uuid] = FolderRow("Idle", folder)
    # ui.update()
    display_folders.refresh()
    print("Updated UI")

async def input_changed(input_name: str, input_base_path: str, add_folder_button: Button):
    print(f"input_name: {input_name}, input_base_path: {input_base_path}")
    if input_name and input_base_path:
        add_folder_button.enable()
    else:
        add_folder_button.disable()

async def update_dest_ip(new_ip: str):
    print("Config Changed")
    dest_address = new_ip
    config = get_config_dc().get()
    config.client.dest_address = dest_address
    try:
        mac = await run.io_bound(get_mac_address, ip=new_ip.split(":")[0])
        print(mac)
        if mac:
            config.client.mac_address = mac
    except Exception as e:
        print(e)
        pass
    get_config_dc().update_data(config)
    display_config.refresh()

async def config_changed(new_ip: str):
    global timer
    if timer:
        timer.cancel()
        timer = None
    timer = ui.timer(callback=lambda: update_dest_ip(new_ip), once=True, interval=3.0)

@ui.refreshable
def display_folders():
    global folder_list_container
    folder_list_container.clear()
    with folder_list_container:
        folders = get_config_dc().get().folders
        for _, folder in folders.items():
            print(f"Rendering folder: {folder}")
            folder_row = folder_rows[folder.uuid]
            with ui.card().props("square outline").style("width: 80%"):
                with ui.row().classes('items-center').style("width: 100%"):
                    ui.label(folder.name).style("border: solid 1px; width: 150px; padding: 10px")
                    ui.label(folder.base_path).style("border: solid 1px; width: 400px; padding: 10px")
                    ui.space()
                    spinner = ui.spinner().bind_visibility_from(folder_row, 'spinner_visible')
                    spinner.set_visibility(folder_row.status == FolderStatus.SYNCING)
                    # ui.label(folder_row.status_label)
                    ui.label().bind_text_from(folder_row, 'status_label')
                    sync = ui.button("Sync", on_click=lambda folder=folder: sync_folder(folder)).bind_enabled_from(folder_row, 'buttons_enabled')
                    sync.tooltip("Sync folder to remote system.")
                    delete = ui.button("Delete", on_click=lambda folder=folder: remove_folder(folder)).bind_enabled_from(folder_row, 'buttons_enabled')
                    delete.tooltip("Delete tracked folder from list. (Does not delete any files at all.)")

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

async def browse(input_base_path: Input):
    result = await local_file_picker('~', multiple=False)
    input_base_path.set_value(result)
    ui.update()

async def wake_up():
    mac = get_config_dc().get().client.mac_address.replace(":", ".")
    print(f"Waking up: {mac}")
    await run.io_bound(send_magic_packet, mac.replace(":", "."))

@ui.refreshable
def display_config():
    config = get_config_dc().get()
    with ui.row().classes('w-full items-center'):
        with ui.input("Target IP/Host", on_change=lambda e: config_changed(e.value), value=config.client.dest_address):
            ui.tooltip(config.client.mac_address)
        ui.button("Wake Up", on_click=wake_up)

@ui.page('/')
def index():
    global folder_list_container, input_name
    config = get_config_dc().get()
    ui.dark_mode(True)
    with ui.expansion('Configuration', icon='work').classes('w-full'):
        display_config()
    with ui.expansion('Folders', icon='work').classes('w-full') as folders_panel:
        with ui.row().classes('w-full'):
            with ui.card().style("width: 80%"), ui.row().classes('items-center').style("width: 100%"):
                add_folder_button = None
                input_name = None
                input_base_path = None
                input_name = ui.input("Name ", on_change=lambda: input_changed(input_name.value, input_base_path.value, add_folder_button))
                input_base_path = ui.input("Base Path ", on_change=lambda: input_changed(input_name.value, input_base_path.value, add_folder_button)).classes("w-1/2")
                ui.space()
                ui.button(text="Browse", on_click=lambda: browse(input_base_path))
                add_folder_button = ui.button(text="Add Folder", on_click=lambda: add_folder(TrackingFolder(name=input_name.value, base_path=input_base_path.value)))
                add_folder_button.disable()

        folder_list_container = ui.column().classes('w-full')
        folders_panel.open()
        display_folders()

ui.timer(0.1, handle_queue_messages, once = True)
ui.timer(0.5, add_tray_icon, once = True)

if __name__ in {'__mp_main__', '__main__'}:
    asyncio.run(add_saved_folders())
    ui.run(show=False, title="Folder Sync", native=False)