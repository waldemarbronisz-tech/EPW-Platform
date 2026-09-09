# Engineer Mode (Protection Verification)

The **Engineer Mode** page (left navigation panel) is a service tool
for formally testing a protection stage's actual pickup and trip
timing against its configured setting, and keeping a dated record of
the result. It is a different tool from the Electrical protections
page ([Electrical Protections](help://prot_electrical)), which only
displays and edits settings — Engineer Mode actually runs a test
against whatever's configured there.

## Before a test can start

The program refuses to start unless every one of these holds, and
tells you which one failed:

- You are at the **Engineer** level.
- The incoming voltage is present (busbars energized).
- The feeder being tested is closed (active).
- No other feeder that the test could trip is currently closed.
- No switching command is pending.
- No trip is currently active anywhere in the system.
- Communication with the device is online.

## Running a test

Pick a protection stage from the dropdown and click **Start Test**.
The program ramps the relevant measurement (voltage, frequency, or
current, depending on the protection) toward the stage's setting,
watches for the real feedback that the output actually operated, and
then restores the simulated value and the feeder's prior state
automatically.

## The report

Each completed test is added to the table below the terminal: date,
time, protection, and result. Behind those columns, the program keeps
the configured vs. measured pickup value and the configured vs.
measured trip delay for every test — a timeout waiting for feedback
is recorded as a FAIL rather than left incomplete. Reports accumulate
across sessions; there is no on-screen way to clear them.

Requires the **Engineer** level to view this page at all — see
[What Each Level Can Do](help://al_matrix).
