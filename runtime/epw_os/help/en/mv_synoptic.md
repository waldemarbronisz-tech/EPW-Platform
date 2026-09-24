# The One-Line Diagram

Main View is the program's starting page — a one-line diagram of a
sample installation, on the left side of the screen.

Layout (top to bottom): Incoming supply → **Q1** (breaker, DO01) →
**KMG** (generator contactor, DO02) → busbar → two feeders: **KM1**
(contactor, DO03) feeding "HOUSE" and **KM2** (contactor, DO04) feeding
"WORKSHOP".

Each device is drawn in a color showing its current state
(open/closed) and reacts to clicking — see
[Controlling Devices and Required Permissions](help://mv_control).
The "HOUSE"/"WORKSHOP" labels and device descriptions come from the
same descriptions set in Control Outputs — a description change there
will show up here the next time the program is opened.

## Push buttons

A screen may carry **push buttons** (the "Push Button" symbol in the
editor). A button does not command an apparatus — it writes one of the
logic's **IN internal bits** (e.g. `M.START`), which the logic reads with
its "Bit input" block. The cap shows the bit's value: green = TRUE. The
designer picks the mode: **toggle** (each click flips the bit) or
**pulse** (TRUE, then FALSE after the set time). The write follows the
same rules as the [Internal bits](help://dio_internal_bits) page: the
access level from the bit's registry entry, an audit entry, and a bit
forced from Studio cannot be switched — a refusal shows the reason.
