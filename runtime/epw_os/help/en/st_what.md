# System Topology: What's Real, What's Not

The diagram and the device tree's top-level **Status** field
(RUNNING/ONLINE/OFFLINE) reflect real communication state from
DeviceManager — the same source the Main View Device Status panel uses.

Every other field in the information panel below the tree (CPU Load,
Memory Usage, Temperature, Firmware, Hardware Revision, Serial Number,
Frames RX/TX, CRC Errors, Timeouts, ...) has no live source anywhere in
the system today. Rather than show a plausible-looking fabricated
number, those fields display **"No data"** — a deliberate placeholder,
not a bug and not missing configuration.
