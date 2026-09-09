# Active vs. Unacknowledged Alarm

An alarm in the program can be in one of four states, distinguished by
the row's color:

| State | Row color | Meaning |
|---|---|---|
| Active, unacknowledged | dark red | the cause is still present, nobody has acknowledged it yet |
| Active, acknowledged | dark amber | the cause is still present, someone has already noticed |
| Cleared, unacknowledged | gray | the cause is gone, but nobody has acknowledged it |
| Normal | white | the cause is gone and the alarm has been acknowledged |

The key distinction: **"active" describes whether the alarm's cause is
still present**, while **"acknowledged" describes whether someone has
noticed it** — these are two independent things. An alarm can therefore
clear before anyone gets a chance to acknowledge it, and it stays
visible until it's acknowledged.
