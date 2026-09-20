# The Logic Indicator

The status bar carries one field, **Logic**, with four possible
readings. Hovering it gives the full numbers.

| Reading | What it means |
|---|---|
| **RUN** | the scan is running: how many blocks, the cycle time, how many scans so far, the last and the longest scan in milliseconds, and how many outputs the logic drives |
| **STOPPED** | a program is loaded but **the scan is not running** — its interlocks are not being evaluated, and its outputs were driven to their safe state |
| **FAULT** | the program is not running, with the reason |
| **none** | this project carries no logic program; the controller runs without user logic |

## Why the longest scan matters

The last scan tells you what is happening now; the **longest** tells you
what the program is capable of under load. A cycle time that is
comfortable on average but occasionally ten times longer is a program
that will surprise somebody eventually — the number is there so it does
not have to be a surprise.

## STOPPED is not "idle"

This is the reading worth knowing by sight. The program exists, the
diagram is right, everything looks configured — and none of its
interlocks are protecting anything. Outputs sit in their safe state.

The same information is available over REST and in Studio, on the
[Controller Connection](help://api_what) panel.
