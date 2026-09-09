# Bus Diagnostics

Per-device statistics for the communication bus - built now, on the
simulator, so it's ready the day a real serial driver (Modbus RTU/TCP)
exists. Engineer level.

## What each column means

- **Sent / Received** — frames transmitted to this device, and frames
  actually received back, since the last reset.
- **Timeout / CRC / Invalid** — three separate error counters: no
  response at all, a checksum mismatch, and a response that arrived but
  wasn't valid (wrong length, unexpected content).
- **Last / Avg / Worst (ms)** — response time of the most recent
  successful exchange, the average across all of them, and the slowest
  one recorded, since the last reset.
- **Since Success** — how long it's been since this device last
  answered successfully.
- **Success %** — the percentage of sent frames that got a valid
  response back.

## Today, on the simulator

There is no real bus yet - every device is served by the simulator, so
error counters stay at zero (there's nothing to fail) and the response
times shown are the real, measured cost of the simulated exchange
itself, not an invented number. They'll be very small - that's honest,
not a placeholder.

## Recent Errors

Below the table, the most recent errors across every device, newest
first, with a timestamp and a short description of what went wrong.

## Reset All Counters

Zeros every device's counters (frames, errors, response times) and
clears the recent errors list. There's no way to reset just one
device's counters from this page - it's a full-board reset, matching
commissioning practice ("clear everything, start a clean run").
