"""App-wide tooltip apparition delay (Task: "podpowiedzi po najechaniu
kursorem... opoznienie okolo pol sekundy przed pojawieniem sie - na tyle,
zeby nie migaly przy przesuwaniu mysza, ale zeby nie trzeba bylo czekac").

A QProxyStyle overriding exactly one styleHint() - everything else
(rendering, every other timing) passes through unchanged to whatever the
platform's real style already does (see main.py, where this wraps
app.style() rather than replacing it). Tooltip CONTENT stays the
standard Qt mechanism (QWidget.setToolTip()/QToolTip) everywhere in the
app, per GRANICE/the task's own "Standardowe podpowiedzi Qt" - this only
tunes how long the cursor has to sit still before one appears, centrally,
instead of relying on whatever the default happens to be per-platform.
"""
from PySide6.QtWidgets import QProxyStyle, QStyle

TOOLTIP_DELAY_MS = 500


class TooltipTimingStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return TOOLTIP_DELAY_MS
        return super().styleHint(hint, option, widget, returnData)
