# Point Registry

Every channel of every card, in one table. Points are **not added
here** — they are born from [cards](help://io_cards). Here you give them
meaning.

The **Card** filter at the top narrows the view to one module.

## Columns for every point

| Column | What to enter |
|---|---|
| **Address** | `id.KIND.number` — read-only, it comes from the card |
| **Description** | what is wired to this terminal; this is what the operator reads |
| **Location** | blank = inherited from the card; you may override it |
| **Technical note** | for the technician: the core number, the terminal strip, the sensor type |
| **Device** | read-only: which apparatus has taken this point |

**Set Location for Selected…** gives a location to many points at once.

## Columns for analog points (AI/AO)

| Column | Meaning |
|---|---|
| **Signal type** | `4-20mA`, `0-10V`, `0-3.3V ADC (raw)` or "value ready" (no conversion) |
| **Raw min / max** | the range the card delivers |
| **Eng min / max** | what it converts to |
| **Unit** | `°C`, `bar`, `A`, `%` |
| **Decimals** | how many digits to show |

The conversion is linear. "Value ready" means the card already delivers
an engineering value and nothing needs scaling.

## The column for DI points

**Counter warning at** — after how many operations the apparatus on this
point should ask for a service. The Switching Counters module counts
them; the counters themselves can be read in [Controller
Connection](help://controller).

## Live mode and forcing

When Studio is connected to a controller, the **Live** column shows each
point's current value. The same works in Cards ("Responds") and in the
screen editor.

**Force mode (Engineer)** turns on operating on the value:

- **Force Value…** — pins the selected point to a value you give;
- **Release Force** / **Release All Forces**;
- a forced point shows `F → value` and who forced it.

A force is a technician's tool: it needs an Engineer token, it is
written to the controller's audit log, it **only lives as long as Studio
keeps confirming it is there** (a heartbeat), and it is released when
the connection closes, when the controller restarts, and when the
[project is reloaded](help://controller) — a force pins a tag the new
project may not even have.
