# Time Sync Indicator Shows Red

The "Time Sync" indicator on the bottom status bar shows whether the
system clock on the computer running EPW OS is synchronized according
to the operating system's own time service (Windows Time /
timedatectl / chrony — depending on the OS). **Red** means NOT SYNCED —
the computer's time is not confirmed to be correct.

Hover over the indicator to see details (the time source's name,
whether NTP is even configured at all).

## What to check

1. Whether the computer has network access to a time source (an NTP
   server on the plant network, or the internet).
2. Whether the operating system's time-sync service is running.
3. Whether the operating system's date/time even looks reasonable.

## Why it matters

An incorrect system clock means incorrect timestamps in the event log,
the audit log, and exported historical data — making it harder to
reconstruct the sequence of events later. The indicator is purely
informational — it does not block any function of the program.
