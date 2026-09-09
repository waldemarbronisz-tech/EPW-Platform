# Screen Sleep

**Settings → Screen Sleep...** — after a configured idle time (mouse
movement, click, key press), the screen dims, covered by a solid
overlay. Any touch, click, or key press wakes it up immediately.

Setting it to 0 minutes disables screen sleep entirely. This setting is
remembered on this specific machine (not in the project file).

This is **independent** of the 5-minute automatic logout described in
[Automatic Logout](help://al_timeout) — screen sleep never changes the
access level, and lowering the access level never puts the screen to
sleep. These are two completely separate mechanisms that happen to
react to the same idle time.
