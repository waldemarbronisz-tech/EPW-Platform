# Automatic Logout

Once your level is raised above User, a 5-minute inactivity timer
starts. Any mouse movement, click, or key press resets it back to zero.

If there is no activity for 5 minutes, the program:

1. Automatically drops the level back to User.
2. Shows a session-timeout notice.
3. Switches the view back to Main View.

This is independent of screen sleep (see
[Screen Sleep](help://set_screen_sleep)) — these are two separate
mechanisms: one is about the access level, the other is purely about
screen brightness.

**In Kiosk Mode this works exactly the same way** — if the menu bar
appeared after reaching Engineer, after 5 minutes of inactivity the
level drops back to User and the menu bar automatically disappears
again. Kiosk Mode itself stays on — automatic logout never exits the
kiosk, it only lowers the access level.
