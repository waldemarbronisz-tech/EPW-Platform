# Electrical vs. Process Protections

**ZABEZPIECZENIA** in the left navigation splits into two pages,
different enough in kind that they're never mixed on one screen:

- **Electrical** — overcurrent, short-circuit, voltage, and frequency
  protections: settings in amps, volts, hertz, and seconds, matching
  the ANSI protection-relay function numbers a real switchgear relay
  would use (27 Under Voltage, 51 Time Overcurrent, and so on).
  Eventually executed in hardware, by ADA01, independent of this
  computer — today this page is a configuration table for those
  settings, not a live evaluation of them.
- **Process** — a simple threshold (upper and lower, with hysteresis
  and a delay) on an existing analog point: temperature, humidity,
  level, pressure, or anything else already wired in as an Analog
  Input. Evaluated live, in software, by this program itself, and
  publishes a signal tag for logic to react to.

Both pages, like every alarm/supervision page in this program, only
ever *report*. Neither one drives an output, a siren, or any hardware
action directly — see [Electrical Protections](help://prot_electrical)
and [Process Protections](help://prot_process) for what each actually
does with what it observes.
