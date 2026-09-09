# Starting the Program

The program starts with `python main.py`. At startup, EPW OS:

1. Loads the project (`project.json`) — point configuration,
   descriptions, project metadata.
2. Starts communication drivers and registers devices.
3. Starts the Historian (historical data recording) and applies
   database migrations if this is the first run.
4. Starts the time synchronization monitor.
5. Starts the system health monitor (see
   [System Health Monitoring](help://saf_kernel)).
6. Opens the main window at the **User** access level.

## Starting in Kiosk Mode

Adding the `--kiosk` parameter at startup (`python main.py --kiosk`)
launches the program immediately in fullscreen, borderless mode. More
on this in [Kiosk Mode](help://kiosk_what).

## First Run — PINs

On the very first run, the program generates random PINs for the
Operator and Engineer levels and shows them ONCE in the startup log
(console). Write them down right away — see
[Forgotten PIN](help://ts_forgot_pin).
