# Logic Internal Bits

The **Internal Bits** page shows, live, the bits of the logic program's
registry (`M.<name>`, `MR.` retentive, `MW.`/`MWR.` numeric registers),
as declared in Studio's Signals department.

**Direction** is the logic's point of view:

- **IN** - set by something outside the logic; the logic only reads it.
  Who may write it is declared on the bit in the project: the panel from
  a given access level (the *Written by* column), a Studio force always,
  REST/MQTT/Home Assistant only where the designer enabled it.
- **OUT** - written by the logic alone; the panel only shows it.

The **SET / CLEAR** buttons (or *Value…* for a register) are active only
on an IN bit and only at the access level its entry demands. Every panel
write reaches the audit log with the old and new value; so does every
refusal, with its reason.

**Apparatus permission.** In Studio's apparatus registry an OUT bit can
be named as the permission to switch on. While it is not TRUE, CLOSE is
refused with a reason naming the bit, e.g. *CLOSE KOT_KMG1 refused: no
permission M.KMG1_ZEZW (Interlock from Q1 open)*. OPEN is never blocked.
A stopped logic, an unknown bit or a controller before its first scan
mean no permission. ADA01's protection path depends on no logic bit.
