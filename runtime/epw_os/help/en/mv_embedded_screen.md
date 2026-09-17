# The Embedded Screen (Synoptic)

**Main View → Synoptic** shows the screen drawn in Studio's Synoptic
Diagram and saved inside the project file (`projekt.epw`, section
`screens`) — live. Every symbol that has an apparatus assigned
(**Aparat** in the editor) follows that apparatus's feedback contact:
a breaker or contactor draws CLOSED/OPEN, a lamp ON/OFF, a fan
RUNNING/OFF, a valve OPEN/CLOSED; a measurement display shows the
analog value with its unit; meters and signal panels read the same
apparatuses. A symbol whose feedback is missing or not readable is
drawn in its FAULT look when the symbol has one.

**Controlling:** a click on a SWITCHED apparatus asks for confirmation
and sends the command the state calls for (CLOSE when it is open, OPEN
when it is closed) — the same Operator permission and the same command
path as on the one-line diagram. When the apparatus's state is not
known yet, no command is offered.

**When nothing is drawn:** the page says why — the project has no
screen, the embedded screen was refused, or the symbol library file
(`shared/symbols/geometry.json`, exported from the Synoptic Editor) is
missing on this controller (symbols are then drawn as plain boxes).

**Not yet drawn live:** wires keep the state saved in the file (the
editor's net colouring is not computed here), rotating symbols keep a
still pose, and a symbol type the current editor library no longer has
is shown as a magenta dashed frame.
