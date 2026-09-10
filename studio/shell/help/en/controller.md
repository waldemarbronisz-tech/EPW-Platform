# Controller Connection

The address (e.g. `http://192.168.1.50:8000`) and access token for the
EPW-OS controller's REST API — stored locally (not in the project
file, since a token is an operator secret, not project data meant to
be shared).

**Test Connection** and **Fetch Tag Preview** are real — they connect
to the controller's actual `/api/v1/health` and `/api/v1/tags`
endpoints.

**Send to Device** and **Receive from Device** are deliberately,
honestly incomplete: the controller's REST API **does not yet have**
any endpoint for uploading/downloading project configuration or
checking a revision — clicking either shows this fact plainly instead
of pretending a sync succeeded. This needs a runtime-side extension,
outside Studio's own scope.
