# 10.3 What the Editor Guarantees, and What It Does Not

The editor guarantees: a data shape matching `validateProjectSchema` (objects have ids, wires have at least two points and only horizontal/vertical segments, valid enum field values) and a device registry shape and set of rules matching `validateDeviceRegistry` on every save from the device form.

The editor does NOT guarantee: that the project "works" on real hardware, that every device is ACTUALLY connected to anything among the screen's symbols (a device with no symbol assigned to it at all is fully valid), or that data typed into the Editor Preview field has anything to do with the installation's real state - see [1.1](help://synoptic/intro-what).
