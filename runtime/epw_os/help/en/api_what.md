# The REST API: Endpoints, Authentication, Exposure

EPW OS runs a small REST API on its own background thread every time
the program starts - not something you turn on separately. By default
it only listens on this computer (`127.0.0.1:8000`), for integrations
that run alongside it (a script, a dashboard, another program on the
same machine).

## Endpoints

- `GET /api/v1/health` - subsystem health states.
- `GET /api/v1/tags` - every tag's current value/quality (optionally
  `?prefix=DI` to narrow it to one family of tags).
- `GET /api/v1/tags/export` - the full signal list, for Logic Studio/
  Synoptic Editor - see [Exporting the Signal List](help://tools_export_tag_list).
- `GET /api/v1/tags/{name}` - one specific tag.
- `GET /api/v1/alarms` - currently active alarms.
- `POST /api/v1/commands` - issue a command (open/close a device). The
  only endpoint that changes anything - see Authentication below.

The five `GET` endpoints above need no authentication - they only read
data, at the same level a person browsing the program at the **User**
level already sees with no PIN at all (see
[What Each Level Can Do](help://al_matrix)).

## Authentication

`POST /api/v1/commands` requires an **Operator or Engineer** API
token, sent as an HTTP header:

```
Authorization: Bearer <token>
```

Two tokens exist - one for Operator, one for Engineer - generated
automatically the first time the program runs, on the same principle
as the Operator/Engineer PINs (see
[Changing Level and Entering a PIN](help://al_pin)): a long random
value, shown **exactly once** in the startup log, then only its hash
is kept, in `epw_os/config/api_tokens.local.json` - a file that is
never committed to source control (like `access.local.json`, the PIN
file). Lost a token? Delete that file and restart; both are
regenerated.

A request with no token, or one that doesn't match, is refused
(`401`) - **there is no way to issue a command over the API without a
valid token**, matching the GUI's own rule that User cannot control
devices. The identity recorded in the [Audit Log](help://ea_audit_log)
for every command issued this way - and for every rejected
authentication attempt - is always the level the token itself proved
(`API:Operator` / `API:Engineer`), never anything the request claims
about itself.

## Exposing it beyond this computer

`api_host` in the project file controls what the API listens on -
`127.0.0.1` (the default) means only this computer can reach it.
Setting it to anything else (e.g. `0.0.0.0`) makes it reachable from
the network: anyone who can reach the port can read every tag and
alarm, and anyone with a stolen or guessed Operator/Engineer token can
issue commands. **If you don't have a specific reason to do this,
don't** - the API was designed for local integrations, not as a
network-facing control interface, and there is no additional network
hardening (TLS, rate limiting) beyond the token check described above.

If `api_host` is ever set to anything other than this computer, EPW OS
tells you loudly, twice: a warning in the startup log, and a red
status-bar indicator that stays visible the whole session
(`⚠ API EXPOSED: <host>`) - so this is never a silent, easy-to-miss
setting.
