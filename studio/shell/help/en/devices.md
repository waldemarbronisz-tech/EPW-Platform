# Device Composition

The list of this controller's functional modules - Intrusion Alarm,
Electrical Protection, Trends and so on - COPIED from the real runtime
mechanism (`epw_os/core/feature_config.py`), not invented for Studio.

**This is NOT a "temporarily enable/disable a feature" switch list.**
It is the device's composition, decided once, when the project is
created - a watering controller **does not have** an intrusion alarm,
the same way a thermostat doesn't, not as "disabled" but as a fact
about what the device consists of.

Each row: a name, a one-sentence description, and a two-state [0][I]
switch with its state also spelled out in words (TAK/NIE) next to it -
so the state is visible, not just implied by an icon.

**A module outside the composition disappears from the project tree
ENTIRELY** - the Intrusion Alarm or Electrical Protection branch simply
does not exist until you check that module here. Disabling a module
that already has data (e.g. configured zones) asks for confirmation
first - data is never deleted, only hidden; re-enabling the module
restores it unchanged.

A few entries (Trends, Power Quality, Bus Diagnostics...) correspond to
real runtime functions Studio doesn't have its own configuration panel
for yet - checking them is saved honestly in the project, simply
without a visible effect in the tree yet.
