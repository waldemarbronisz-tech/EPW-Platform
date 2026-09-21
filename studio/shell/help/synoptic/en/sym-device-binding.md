# 6.4 Binding a Symbol to a Device

Every symbol (except pure graphics and lines) has an Aparat field in Properties - a dropdown of every device in the project. A symbol with NO device assigned is a fully valid state - it is pure graphics with no relation to the device list at all.

Choosing a device while the symbol's own Designation field is empty auto-fills it with that device's designation - but ONLY once, at the moment of choosing, and ONLY when it was empty. Changing the device's own designation afterward does not change the symbol's already-filled designation (and typing something else into Designation by hand is never overwritten by picking a device again).

The same device assigned to many different symbols is valid and reports no error - see [4.1](help://synoptic/dev-why-not-in-screen). A symbol pointing at a device id that no longer exists in the registry (e.g. it was deleted) still renders completely normally, but gets a dashed red outline and is reported to the Messages panel as a warning - see [9.7](help://synoptic/edit-messages-panel) and [chapter 11](help://synoptic/ts-symbol-red-outline).
