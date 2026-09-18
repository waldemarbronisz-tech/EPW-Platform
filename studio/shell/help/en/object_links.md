# Object Links

An object is several controllers, and one sometimes needs a state from
another: the entry gate wants to know the house is armed, the boiler
room that the garage reports a flood. A link is a pair: a **source
point** on one controller and a **`Link.<Id>.In<n>` tag** on another.

The mechanism is the MQTT both controllers have anyway: the source
publishes its tags at `<prefix>/tag/<path>/state`, the target has an
incoming mapping in MQTT Integration that turns that topic into a
local `Link.*` tag. Studio writes those mappings itself (grey in MQTT
Integration, with their origin; manual mappings are never touched),
enables MQTT and sets a topic prefix where there was none. The broker
is shared — its address goes into each controller's MQTT Integration.

The `Link.*` tag on the target is **information, never a command**:
logic may read it, a screen may show a symbol bound to it, but nothing
controls the other controller through it. When the source falls silent
for longer than "stale after", the tag on the target goes STALE.

Links belong to the object file; "Save Object" saves them together with
the projects whose MQTT Integration Studio changed. Removing a
controller from the object removes its links both ways.
