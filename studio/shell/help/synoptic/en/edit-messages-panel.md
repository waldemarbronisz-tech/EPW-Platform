# 9.7 The Messages Panel

The Messages panel, at the bottom of the window, collects messages from across the editor: info (e.g. "Project created: ..."), warnings (e.g. a symbol pointing at a nonexistent device - [6.4](help://synoptic/sym-device-binding)) and errors (e.g. a failed project save due to a validation error). Every entry carries a timestamp.

A message's severity is read from a text prefix: `[ERROR]` and `[WARNING]` at the start of the message color it as an error or a warning respectively; any other text is filed as plain info.
