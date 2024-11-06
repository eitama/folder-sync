import pystray
from PIL import Image
import webbrowser
from sys import exit
from asyncio import Queue, BaseEventLoop, run_coroutine_threadsafe

icon = None
communication_queue: Queue = None

def init_systray_icon(queue: Queue):
    global icon, communication_queue, event_loop
    communication_queue = queue
    image = Image.open("resources/systray_icon.png")
    # In order for the icon to be displayed, you must provide an icon
    icon = pystray.Icon('test name', icon=image, menu=pystray.Menu(
        pystray.MenuItem(text="Open",action=open_browser,default=True),
        pystray.MenuItem(text="Exit", action=quit)
    ))
    icon.run()
    print("Done loading systray icon")

def open_browser():
    webbrowser.open('http://127.0.0.1:8080', new = 2)

def quit():
   communication_queue.put_nowait("Exit")
   icon.stop()
   print("Quit Clicked")