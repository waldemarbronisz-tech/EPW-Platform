"""Help > Topics.../Index... - a Windows 98 Help-style window (task:
"pomoc ma wygladac jak Windows Help z tamtych lat").

Content loading/search itself lives in epw_os/core/help_content.py
(headless, no PyQt) - this module is purely the Qt presentation layer on
top of it. Rendering uses QTextBrowser.setMarkdown() (built into Qt
since 5.14) - no new dependency, per GRANICE.

Only the WINDOW CHROME here (toolbar buttons, tab labels, the window
title) goes through tr() with locales/en.json + pl.json keys - never
the help content itself (GRANICE: "Tresc pomocy... to dokumentacja -
NIE przez tr()")."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QListWidget, QListWidgetItem, QLineEdit, QLabel, QSplitter,
    QTextBrowser,
)

from epw_os.core.help_content import HelpContentStore
from epw_os.i18n import tr, get_language
from epw_os.version import __version__


class HelpWindow(QWidget):
    """The Help window itself. Non-modal, independent top-level window
    (task: reachable "z dowolnego miejsca w programie" without blocking
    the rest of the app) - reused across repeated F1 presses/menu clicks
    rather than rebuilt each time, so Back/Forward history survives."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("IndustrialDialog")
        self.setWindowTitle(tr("help.window_title"))
        self.resize(780, 540)

        self._store = HelpContentStore(get_language())
        self._history = []       # list[topic_id]
        self._history_index = -1  # position within _history currently shown

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        toolbar = QHBoxLayout()
        self.btn_hide = QPushButton(tr("help.btn_hide"))
        self.btn_hide.clicked.connect(self._toggle_left_panel)
        toolbar.addWidget(self.btn_hide)
        self.btn_back = QPushButton(tr("help.btn_back"))
        self.btn_back.clicked.connect(self._go_back)
        toolbar.addWidget(self.btn_back)
        self.btn_forward = QPushButton(tr("help.btn_forward"))
        self.btn_forward.clicked.connect(self._go_forward)
        toolbar.addWidget(self.btn_forward)
        toolbar.addStretch()
        outer.addLayout(toolbar)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(self._splitter, stretch=1)

        self.tabs = QTabWidget()
        self._build_contents_tab()
        self._build_index_tab()
        self._build_search_tab()
        self._splitter.addWidget(self.tabs)

        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(False)
        self.viewer.setOpenLinks(False)
        self.viewer.anchorClicked.connect(self._on_anchor_clicked)
        self._splitter.addWidget(self.viewer)
        self._splitter.setSizes([230, 550])

        self.show_welcome()
        self._update_nav_buttons()

    # --- left panel: Contents ------------------------------------------

    def _build_contents_tab(self):
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        for chapter in self._store.load_toc()["chapters"]:
            chapter_item = QTreeWidgetItem([chapter["title"]])
            chapter_item.setData(0, Qt.ItemDataRole.UserRole, None)
            for topic in chapter["topics"]:
                topic_item = QTreeWidgetItem([topic["title"]])
                topic_item.setData(0, Qt.ItemDataRole.UserRole, topic["id"])
                chapter_item.addChild(topic_item)
            self.tree.addTopLevelItem(chapter_item)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        self.tabs.addTab(self.tree, tr("help.tab_contents"))

    def _on_tree_item_clicked(self, item, _column):
        topic_id = item.data(0, Qt.ItemDataRole.UserRole)
        if topic_id is None:
            # A chapter ("book") node - toggle expand/collapse, same as
            # classic Windows Help; it has no content of its own.
            item.setExpanded(not item.isExpanded())
            return
        self.navigate_to(topic_id)

    # --- left panel: Index ------------------------------------------

    def _build_index_tab(self):
        self.index_list = QListWidget()
        for term, topic_id in sorted(self._store.index_terms(), key=lambda pair: pair[0].lower()):
            item = QListWidgetItem(term)
            item.setData(Qt.ItemDataRole.UserRole, topic_id)
            self.index_list.addItem(item)
        self.index_list.itemClicked.connect(
            lambda item: self.navigate_to(item.data(Qt.ItemDataRole.UserRole))
        )
        self.tabs.addTab(self.index_list, tr("help.tab_index"))

    # --- left panel: Search ------------------------------------------

    def _build_search_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("help.search_placeholder"))
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self.search_edit)
        self.search_results = QListWidget()
        self.search_results.itemClicked.connect(
            lambda item: self.navigate_to(item.data(Qt.ItemDataRole.UserRole))
        )
        layout.addWidget(self.search_results, stretch=1)
        self.tabs.addTab(container, tr("help.tab_search"))

    def _on_search_text_changed(self, text):
        self.search_results.clear()
        for topic_id, title in self._store.search(text):
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, topic_id)
            self.search_results.addItem(item)

    # --- navigation / history ------------------------------------------

    def select_tab(self, tab: str):
        index = {"contents": 0, "index": 1, "search": 2}.get(tab, 0)
        self.tabs.setCurrentIndex(index)

    def show_welcome(self):
        md = self._store.load_topic_markdown("welcome", version=__version__)
        self.viewer.setMarkdown(md)
        self.setWindowTitle(tr("help.window_title"))

    def navigate_to(self, topic_id: str, _record_history=True):
        if not topic_id:
            return
        title = self._store.topic_title(topic_id) or topic_id
        self.viewer.setMarkdown(self._store.load_topic_markdown(topic_id))
        self.setWindowTitle(f"{tr('help.window_title')} - {title}")
        if _record_history:
            # A fresh navigation drops any "forward" history beyond the
            # current position - same as a browser.
            self._history = self._history[: self._history_index + 1]
            self._history.append(topic_id)
            self._history_index = len(self._history) - 1
        self._update_nav_buttons()

    def _go_back(self):
        if self._history_index > 0:
            self._history_index -= 1
            self.navigate_to(self._history[self._history_index], _record_history=False)

    def _go_forward(self):
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.navigate_to(self._history[self._history_index], _record_history=False)

    def _update_nav_buttons(self):
        self.btn_back.setEnabled(self._history_index > 0)
        self.btn_forward.setEnabled(self._history_index < len(self._history) - 1)

    def _toggle_left_panel(self):
        showing = self.tabs.isVisible()
        self.tabs.setVisible(not showing)
        self.btn_hide.setText(tr("help.btn_show") if showing else tr("help.btn_hide"))

    def _on_anchor_clicked(self, url: QUrl):
        # Internal cross-references only (e.g. [Access Levels](help://al_three))
        # - never opens a real browser or any external link (GRANICE: no
        # new dependency, and no reason for this offline help to reach
        # the network at all).
        if url.scheme() == "help":
            topic_id = url.host() or url.path().lstrip("/")
            self.navigate_to(topic_id)
