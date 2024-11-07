# folder-sync

Manually One-Way sync folders across computers over HTTP.

## Features / Basics
* Triggered MANUALLY from a very simple NiceGUI.
* Maintains an index of Last-Modified and MD5 values for each file both in Source and Target computers.
* The indexes are ONLY updated when a sync action is triggered, nothing happens in the background or automatically.

## What's missing? (Cause I didn't need to didn't care)
* Compression, Encryption, Post-Copy verification.
* Schedule / Triggers.
* Retry mechanism.
* Authorization.
* Testing (or maybe even compatibility with Linux / Mac [I only used this on Windows 11])

## Installation 
### On both Client and Server PCs
* Clone / Download the Repo.
* Create python venv: `python -m venv .venv`
* Activate venv: `.venv/Scripts/activate`
* Install dependencies: `pip install -r requirements`

### On Server
* Run the server: `python server.py`
* Two files are generated: `server/config.json` and `server/data.json`
    * Add folders you want to copy files TO in `server/config.json` (Take hint from the example in there for syntax.)
    * Save the file.
    * No need to restart the server, this file is read every time a sync is performed.
* Make sure you have connectivity from client to server - In other words: No firewalls blocking, etc...

### On Client
* Run the client: `python client.py`
* You can open the GUI by clicking the systray icon.
* Add a folder for tracking.  The folder "Name" should be EXACTLY the same as the one configured on the server. (Case Sensitive!!!)
* Click Sync.

## Example
- PC A has folder `C:\SourceFolder`
- PC B has folder `D:\TargetFolder`
- Install Client on PC A, and Server on PC B
- On PC B, add to `server/config.json`:
```
    "folders": {
        "my_pictures": {
            "name": "my_pictures",
            "base_path": "D:\\MyPictures",
            "uuid": "6696648d-3027-4a42-a0a7-6188654fb729"
        }
    },
```
- Now on PC A, open the app, add the `my_pictures` and source folder.
- Click Sync.