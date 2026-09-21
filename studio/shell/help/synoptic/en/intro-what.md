# 1.1 What EPW-Synoptic-Editor Is

EPW-Synoptic-Editor creates and validates project files for an electrical/water/ventilation schematic screen: symbols, wires, meters, signal panels. It is an EDITING tool - it runs offline, against a file on disk, and has no notion of any live plant state.

The editor does NOT execute control logic, does NOT poll controllers over Modbus or any other protocol, and does NOT know whether a contactor is currently energized. Everything shown on screen while editing - a lit diode, a value on a meter - is a preview set by hand in the `Editor Preview` field, not a reading from a real device.

The output of working in this editor is a project file (`.epwsyn`) holding the screen geometry and the device list. That file is INTENDED to run on [EPW-OS](help://synoptic/intro-platform) - see chapter 10 for exactly what that path actually does today.

> **Note:** A rule that comes back in every chapter of this help: if something is not plainly visible in the program or in the project file, it does not exist. This text describes the code as it actually is.
