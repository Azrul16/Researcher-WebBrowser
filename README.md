# Researcher

Researcher is a desktop academic browser built with `PyQt6` and `Qt WebEngine`.
It is designed for focused research workflows: browsing papers, searching Google Scholar, saving bookmarks, reviewing history, and using an AI assistant to drive the browser.

---

## Overview

Researcher combines three ideas into one app:

- an academic-first browser
- a compact desktop AI copilot
- a safer deployment path for AI credentials

The app is optimized around research browsing rather than general web surfing. New tabs open to Google Scholar, the UI is tailored for paper discovery, and the browser can block distracting sites in research mode.

---

## Features

### Core Browser

- multi-tab browsing
- pinned tabs
- Google Scholar as the default homepage
- search-or-URL omnibox
- bookmark toggle on the current page
- saved browsing history
- popup pages opening in new tabs
- session restore

### Research Workflow

- Google Scholar-first searching
- article and paper browsing in desktop WebEngine
- bookmark library page
- history library page
- optional PSTU proxy support
- local persistence for settings, tabs, history, and bookmarks

### AI Assistant

- floating command input inside the browser window
- search Scholar from plain language
- summarize the current page
- bookmark or pin tabs through commands
- answer questions using page context

### Safer AI Access

Researcher supports two AI modes:

1. `Backend proxy mode`
   The desktop app calls your own server. Your Groq key stays on the server.

2. `Local secure key mode`
   On first launch, the app can ask for a Groq key and store it in the OS credential store instead of bundling it into the app.

---

## UI Notes

The current UI uses a hybrid desktop/web approach:

- `PyQt6` for the native application shell and WebEngine browser
- `HTML/CSS/JavaScript` for the browser chrome and floating assistant input
- `QWebChannel` to connect the web UI to Python actions

This keeps the browsing engine stable while allowing the controls to feel more modern and easier to style.

---

## Project Structure

```text
researcher/
├── main.py
├── browser_window.py
├── browser_tab.py
├── browser_chrome.py
├── chat_panel.py
├── agent_controller.py
├── tools.py
├── groq_client.py
├── credential_store.py
├── api_access_dialog.py
├── proxy_manager.py
├── bookmark_manager.py
├── history_manager.py
├── settings_manager.py
├── session_manager.py
├── app_paths.py
├── server/
│   └── researcher_proxy.py
├── assets/
│   ├── browser_chrome.html
│   └── chat_panel.html
├── images/
│   ├── app icon.png
│   └── app_icon.ico
├── installer/
│   └── ResearcherAcademicBrowser.iss
├── build_release.ps1
└── requirements.txt
```

---

## Local Development

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Run the app

```powershell
python main.py
```

---

## Environment Variables

Researcher reads `.env.local` when present.

### AI Client / Proxy

```powershell
$env:RESEARCHER_PROXY_URL="https://your-server.example.com"
$env:RESEARCHER_PROXY_TOKEN="optional-shared-token"
$env:GROQ_API_KEY="your-local-groq-key"
```

### PSTU Proxy

```powershell
$env:PSTU_PROXY_ENABLED="true"
$env:PSTU_PROXY_HOST="proxy.example.edu"
$env:PSTU_PROXY_PORT="8080"
$env:PSTU_PROXY_USERNAME="username"
$env:PSTU_PROXY_PASSWORD="password"
```

### Notes

- if `RESEARCHER_PROXY_URL` is set, the app prefers backend proxy mode
- if no backend proxy is configured, the app can use a locally stored Groq key
- if neither is available, AI falls back to non-Groq behavior

---

## AI Setup

### Option A: Recommended Production Setup

Run the backend proxy and keep the Groq key off the desktop client.

Start the server:

```powershell
$env:GROQ_API_KEY="your-server-side-groq-key"
$env:RESEARCHER_PROXY_TOKEN="optional-shared-token"
python server\researcher_proxy.py
```

Point the desktop app to the server:

```powershell
$env:RESEARCHER_PROXY_URL="http://127.0.0.1:8787"
$env:RESEARCHER_PROXY_TOKEN="optional-shared-token"
python main.py
```

### Option B: Secure Local Desktop Setup

Run the desktop app with no bundled key:

```powershell
python main.py
```

On first launch, Researcher can prompt for a Groq key and store it securely using the OS credential store.

---

## Packaging and Installer

Researcher can be packaged as a Windows installer.

### Build the packaged app and installer

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

### Output

```text
release\Setup.exe
```

That single file can be shared with another Windows user for installation.

### What the installer does

- installs `Researcher` under `Program Files`
- can create a desktop shortcut
- adds a Start menu entry
- uses the app icon from `images\app_icon.ico`

### Important Packaging Note

The installer does not bundle your private `.env.local` secrets by default.
That is intentional.

---

## Useful Commands

### Run the desktop app

```powershell
.\.venv\Scripts\python.exe main.py
```

### Run the backend proxy

```powershell
.\.venv\Scripts\python.exe server\researcher_proxy.py
```

### Rebuild the installer

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

### Compile-check core Python files

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py browser_window.py browser_tab.py browser_chrome.py chat_panel.py groq_client.py
```

### Install or refresh dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Security Notes

- do not bundle a real Groq key into the installer if you care about security
- use backend proxy mode for shared/public installs
- use local secure key storage only for trusted single-user installs
- keep `.env.local` private and out of version control

---

## Current Status

Researcher is already usable as a desktop academic browser MVP with:

- custom browser chrome
- floating assistant input
- bookmark and history pages
- packaged Windows installer
- safer AI credential handling paths

There is still room to improve:

- richer page extraction for better summaries
- favicon support in tabs
- cleaner proxy diagnostics
- stronger academic source navigation tools
- more polished settings and onboarding screens

---

## Build Summary

If you just want the short version:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

And for the installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```
