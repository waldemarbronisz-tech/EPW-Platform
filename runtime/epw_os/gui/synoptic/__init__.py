"""Runtime renderer for the screens Studio embeds in projekt.epw (punkt 2
/ luka 5: "screen renderer in runtime").

    geometry.py      shared/symbols/geometry.json - every symbol of the
                     Synoptic Editor's library as drawing primitives,
                     exported by studio/synoptic/tools/geometry_export
    svg_path.py      SVG path data -> QPainterPath (the Path primitive)
    painter.py       draws a primitive tree with QPainter - generic, knows
                     nine primitive kinds and no symbol by name
    screen_state.py  what a screen object shows right now: its symbol
                     state and text from the apparatus register and the
                     live tags (pure Python, no Qt)
    screen_widget.py the whole screen: background, frames, walls, wires,
                     symbols with labels, meters and signal panels
    page_synoptic.py the "Synoptic" page in the main window
"""
