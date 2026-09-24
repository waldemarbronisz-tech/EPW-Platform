"""A QTextBrowser that plays the animated GIFs a help page embeds.

QTextDocument loads an image once, as a still - a GIF shows its first
frame and stops. Both help viewers of the platform (EPW Studio's one help
panel and Logic Studio's standalone help window) show the same generated
block pages, which since 2026-09-25 carry a short animation of the block
at work (logic_studio/help/media/<type_id>.gif, drawn from the editor's
own canvas by studio/logic/tools/render_help_animations.py) - so the
player lives here, once, imported by both.

How: loadResource() is asked for every image the document draws; for a
.gif it starts a QMovie on the file and, on every frame, re-registers
that frame as the document's image resource under the same URL and
repaints - the ordinary "animate inside a QTextEdit" technique, no timer
of our own. Any other resource goes the default way. setMarkdown() stops
the movies of the previous page.
"""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QMovie, QTextDocument
from PySide6.QtWidgets import QTextBrowser


def is_animation_url(url) -> bool:
    return str(url.toString() if hasattr(url, "toString") else url).lower().endswith(".gif")


def local_path(url) -> str:
    """The file a help:// page's image URL names - file:///D:/x/y.gif,
    a plain absolute path, or a relative one (left as given)."""
    if isinstance(url, str):
        url = QUrl(url)
    if url.isLocalFile():
        return url.toLocalFile()
    return url.toString()


class AnimatedHelpBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._movies = {}

    # --- Qt asks here for every image the page draws ---------------------------------------

    def loadResource(self, resource_type, url):
        if resource_type == QTextDocument.ResourceType.ImageResource and is_animation_url(url):
            movie = self._movie_for(url)
            if movie is not None:
                return movie.currentPixmap()
        return super().loadResource(resource_type, url)

    def _movie_for(self, url):
        key = url.toString()
        movie = self._movies.get(key)
        if movie is not None:
            return movie
        movie = QMovie(local_path(url), b"", self)
        if not movie.isValid():
            return None
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        movie.frameChanged.connect(lambda _frame, u=url, m=movie: self._on_frame(u, m))
        self._movies[key] = movie
        movie.start()
        return movie

    def _on_frame(self, url, movie):
        self.document().addResource(QTextDocument.ResourceType.ImageResource, url, movie.currentPixmap())
        self.viewport().update()

    # --- a new page: the old page's movies stop ---------------------------------------------

    def setMarkdown(self, markdown, *args, **kwargs):
        self.stop_animations()
        super().setMarkdown(markdown, *args, **kwargs)

    def setHtml(self, html):
        self.stop_animations()
        super().setHtml(html)

    def stop_animations(self):
        # Stopped and detached, never deleteLater()'d: a browser that is
        # itself dropped by Python before the event loop runs again would
        # otherwise be destroyed with a deferred delete of its own child
        # still queued - Qt aborts on that (seen in the test suite).
        for movie in self._movies.values():
            movie.stop()
            try:
                movie.frameChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            movie.setParent(None)
        self._movies = {}

    def animations(self) -> list:
        """The URLs of the animations playing on this page (for tests and diagnostics)."""
        return [key for key, movie in self._movies.items() if movie.state() == QMovie.MovieState.Running]
