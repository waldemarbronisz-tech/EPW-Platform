### How it works

| S1 | R | Q |
|---|---|---|
| 0 | 0 | unchanged (remembers) |
| 1 | 0 | **1** |
| 0 | 1 | 0 |
| 1 | 1 | **1** - Set dominates |

A latch **remembers** its state between scans: a short pulse on S1 sets Q
for good, until R comes. When S1 and R are active together, S1 wins. If
STOP must win in your circuit, take [RS](help:block:memory.rs) - usually
the right choice for drives. Full description: [Latches and edge
detection](help:concept_memory_edges).

### 1. Holding after a pulse

The START button gives a pulse; the drive must keep running after it is
released: `START` -> S1, `STOP` -> R, Q -> `DO contactor`. After the
controller's supply drops and returns, the latch starts with Q = FALSE
(safe).

### 2. A latched alarm

A protection trip must be remembered until the operator clears it, even
when the cause is gone: `Protection` -> S1, `Clear from panel (IN bit
M.KASUJ)` -> R, Q -> lamp and siren. Set-dominant guarantees the clear
does nothing while the cause persists.

### 3. Operating mode

`Switch to AUTO` -> S1, `Switch to MANUAL` -> R; Q = TRUE means AUTO.
