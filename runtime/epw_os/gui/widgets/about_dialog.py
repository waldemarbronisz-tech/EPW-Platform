import os

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextBrowser
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from epw_os.i18n import tr, get_language
from epw_os.version import __version__, APP_NAME
from epw_os.core.help_content import HelpContentStore

# epw_os/gui/widgets/about_dialog.py -> epw_os/resources
_LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "resources", "about_logo.png",
)
_LOGO_MAX_WIDTH = 320
_LOGO_MAX_HEIGHT = 160


class AboutDialog(QDialog):
    """Help > About EPW OS. Name/version come from epw_os/version.py (one
    source of truth, task requirement). The long text (background,
    author, license, the project's governing principle) is documentation,
    not UI chrome (GRANICE: not through tr()) - it's the same Markdown +
    per-language-directory mechanism the Help window itself uses
    (HelpContentStore), just for the single "about" topic; English is
    the fallback the same way it is there.

    The logo (epw_os/resources/about_logo.png) is scaled down to fit,
    never up - a missing or unreadable file must not crash this dialog
    (task requirement), so QPixmap.isNull() is checked and the label is
    simply omitted rather than shown broken."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("about.title"))
        self.setModal(True)
        self.setMinimumSize(420, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        pixmap = QPixmap(_LOGO_PATH)
        if not pixmap.isNull():
            logo_label = QLabel()
            scaled = pixmap.scaled(
                _LOGO_MAX_WIDTH, _LOGO_MAX_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(scaled)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)
        # else: no logo file (or an unreadable one) - the dialog still
        # works fine without it, just without the image.

        header = QLabel(APP_NAME)
        header.setObjectName("SectionHeader")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        version = QLabel(f"{tr('about.version_label')}: {__version__}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        # The long, scrollable text - background, what makes this
        # different, the name's origin, the visual style, the author,
        # license/availability, and the project's governing principle.
        # See epw_os/help/<lang>/about.md - documentation, not tr().
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(False)
        store = HelpContentStore(get_language())
        text_browser.setMarkdown(store.load_topic_markdown("about", version=__version__))
        layout.addWidget(text_browser, stretch=1)

        btn_close = QPushButton(tr("about.btn_close"))
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)
