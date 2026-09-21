# 1.3 Governing Principle: the Screen Informs, the Hardware Protects

The whole platform architecture holds to one rule: THE SCREEN INFORMS, THE HARDWARE PROTECTS. The synoptic and EPW-Logic-Studio's own logic show the operator state and provide convenient, contextual interlocks - but the final protection (a fuse, a contactor with its own undervoltage coil, a check valve) has to exist physically, independent of whatever the screen is doing.

In this editor the rule shows up directly in the SWITCHED device contract: the `safeState` field (see [4.4](help://synoptic/dev-switched)) describes what the device itself should do ON STARTUP and ON LINK LOSS - not what an operator should do by hand in that situation. The hardware and its own configuration decide the safe state, not the screen's logic.

Likewise: no feedback (`feedback.mode` NONE, see [4.4](help://synoptic/dev-switched)) means the screen will never confirm whether a command actually took effect. That is a deliberate, allowed configuration choice - but its consequence is named outright in the device form, not hidden.
