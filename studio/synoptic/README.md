# EPW Synoptic Editor

Professional industrial HMI/SCADA synoptic editor for EPW OS. Inspired by SimCity 2000 engineering workflow, featuring drag-and-drop process design, real-time visualization, and seamless integration with EPW Logic Studio and Runtime.

## Overview
EPW Synoptic Editor is a standalone application responsible ONLY for EDITING `.epwsyn` project files. It does not handle runtime execution, Modbus communication, or logic gates—those are handled by EPW OS Synoptic Runtime and EPW Logic Studio.

## Prerequisites
- Node.js (v22.22 or higher, compatible with current Vite version)
- NPM
- Python 3.9+ (only for the native desktop window - see below; not needed to run the app in a browser)

## How to Start (Windows, browser)
Double-click `START_EPW_SYNOPTIC.bat`. This script will:
1. Verify Node.js is installed.
2. Automatically run `npm install` if dependencies are missing.
3. Start the application locally and open it in your default web browser (typically `http://127.0.0.1:5173`).

## How to Start (Manually, browser)
1. Install dependencies:
   ```bash
   npm install
   ```
2. Start the development server:
   ```bash
   npm run dev
   ```

## How to Start (Native Desktop Window, no browser)
The exact same editor, opened in its own OS window - no address bar, no
tabs, no browser chrome - via `pywebview`. The frontend itself is
completely unchanged; this only serves the built app locally and points
a native window at it.

1. Install the one Python dependency (once):
   ```bash
   pip install -r requirements.txt
   ```
2. Launch:
   ```bash
   python main.py
   ```
   The first run builds the frontend automatically (`npm run build`) if
   `dist/` doesn't exist yet; later runs skip straight to launching. Use
   `python main.py --rebuild` after pulling new frontend changes, or
   `python main.py --dev` to point the window at an already-running
   `npm run dev` server instead (useful while developing the UI).

Note: the app's own File > Exit menu item still confirms unsaved changes
before closing, exactly as it always has. Closing the native window
directly via its OS close button does not - pywebview does not
guarantee it honors the page's own `beforeunload` handler the way a
real browser tab does. This is a known limitation of wrapping a web app
this way, not a bug in the editor.

## How to Build
To build the application for production, run:
```bash
npm run build
```

## .epwsyn File Format
The editor saves projects in `.epwsyn` format, which is a pure JSON schema that holds the application drawing and logic bindings but contains no executable code.

## Current Project Status
- Complete functional UI inspired by 1998 industrial engineering software.
- Full drag-and-drop functionality with infinite canvas.
- Project loading and saving logic decoupled into a proper ProjectManager layer.
- Responsive resizable panels and property inspectors.
