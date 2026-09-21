"""EPW Studio's ONE help (owner, 2026-09-21: "jeden program inżynierski,
help jeden, spójny i powiązany, nie ważne w którym miejscu stoję").

Three sources, one tree, one language - Studio's current one:

  * Studio's own topics    - studio/shell/help/<lang>/<key>.md (generate_help.py,
                             _manifest.py), keys as they always were ("points",
                             "screens", ...);
  * the screen editor's    - studio/shell/help/synoptic/ (toc.json + <lang>/<id>.md),
                             written from the editor's own content by
                             studio/synoptic/tools/help_export/export.mjs;
                             keys "synoptic/<id>";
  * the logic editor's     - logic_studio.core.help_content.HelpContentStore,
                             the same store its standalone window uses (hand-
                             written topics, the generated block catalog, the
                             shortcut table), read here in Studio's language;
                             keys "logic/<id>", including "logic/block:<type>"
                             and "logic/category:<name>".

Links: every source's own cross-references are rewritten on load to the
namespaced `help://` form this module resolves (`help://points`,
`help://synoptic/intro-what`, `help://logic/concept_stubs`), so a topic of
one editor can point into another and F1 lands in the same place from
any department.
"""
import json
import os
import re

from studio.shell.i18n import tr

SYNOPTIC_PREFIX = "synoptic/"
LOGIC_PREFIX = "logic/"

_HELP_DIR = os.path.dirname(os.path.abspath(__file__))
_SYNOPTIC_DIR = os.path.join(_HELP_DIR, "synoptic")

# Logic Studio's own pages link as `help:<topic>` (a single colon - its
# ids carry a colon of their own, "block:logic.and") and its generated
# category pages as `help://block:<type>`; both become help://logic/<topic>
# here. Links already namespaced (help://logic/..., help://synoptic/...)
# are left alone.
_LOGIC_LINK = re.compile(r"\]\(help:(?://)?(?!logic/|synoptic/)([^)\s]+)\)")


class HelpNode:
    """One row of the help tree: a chapter (no key, only children) or a topic (a key)."""

    __slots__ = ("key", "title", "children")

    def __init__(self, title, key=None, children=None):
        self.title = title
        self.key = key
        self.children = list(children or [])

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


def split_key(key: str):
    """("synoptic", "intro-what") / ("logic", "block:logic.and") / ("", "points")."""
    for prefix in (SYNOPTIC_PREFIX, LOGIC_PREFIX):
        if key.startswith(prefix):
            return prefix[:-1], key[len(prefix):]
    return "", key


def key_from_url(url) -> str:
    """The topic key a help:// link names: `help://points` (host only),
    `help://synoptic/intro-what` (host + path), and the single-colon
    `help:concept_stubs` form (path only) - all three appear, the last
    one in Logic Studio's own files."""
    host = url.host() or ""
    path = (url.path() or "").lstrip("/")
    if host and path:
        return f"{host}/{path}"
    return host or path


class UnifiedHelp:
    def __init__(self, lang: str):
        self.lang = lang if lang in ("pl", "en") else "en"
        self._logic_store = None
        self._synoptic_toc = None

    # --- the sources ------------------------------------------------------------------------

    def _logic(self):
        if self._logic_store is None:
            from studio.shell.logic_path import ensure_importable
            ensure_importable()
            from logic_studio import i18n as logic_i18n
            from logic_studio.core.help_content import HelpContentStore
            from shared.logic.blocks import register_builtin_blocks
            # The block catalog is generated from the registry, which is
            # filled by importing the blocks - done by the logic editor when
            # it opens, done here too so the catalog exists before that.
            register_builtin_blocks()
            # The generated pages (block texts, the shortcut table) speak the
            # logic editor's language: Studio's, the same as this help.
            if logic_i18n.get_language() != self.lang:
                logic_i18n.set_language(self.lang)
            self._logic_store = HelpContentStore(self.lang)
        return self._logic_store

    def _synoptic(self) -> dict:
        if self._synoptic_toc is None:
            try:
                with open(os.path.join(_SYNOPTIC_DIR, "toc.json"), "r", encoding="utf-8") as f:
                    self._synoptic_toc = json.load(f)
            except (OSError, ValueError):
                self._synoptic_toc = {"chapters": []}
        return self._synoptic_toc

    # --- the tree ---------------------------------------------------------------------------

    def tree(self) -> list:
        """Top-level nodes: Studio's chapters, then the screen editor's
        chapters under one heading, then the logic editor's."""
        from studio.shell.help._manifest import CHAPTERS, TOPICS
        title_index = 1 if self.lang == "pl" else 2
        nodes = []
        by_chapter = {}
        for chapter_key, chapter_pl, chapter_en in CHAPTERS:
            node = HelpNode(chapter_pl if self.lang == "pl" else chapter_en)
            by_chapter[chapter_key] = node
            nodes.append(node)
        for entry in TOPICS:
            key, chapter = entry[0], entry[3]
            by_chapter[chapter].children.append(HelpNode(entry[title_index], key))
        nodes = [node for node in nodes if node.children]

        synoptic = HelpNode(tr("help.group_synoptic"))
        for chapter in self._synoptic().get("chapters", []):
            title = chapter.get("title", {})
            node = HelpNode(title.get(self.lang) or title.get("en") or chapter.get("id", ""))
            for topic in chapter.get("topics", []):
                t = topic.get("title", {})
                node.children.append(HelpNode(t.get(self.lang) or t.get("en") or topic["id"], SYNOPTIC_PREFIX + topic["id"]))
            if node.children:
                synoptic.children.append(node)
        if synoptic.children:
            nodes.append(synoptic)

        logic = HelpNode(tr("help.group_logic"))
        try:
            toc = self._logic().load_toc()
        except Exception:  # noqa: BLE001 - a broken logic install must not take the whole help down
            toc = {"chapters": []}
        for chapter in toc.get("chapters", []):
            is_catalog = any(topic.get("_is_category") for topic in chapter.get("topics", []))
            node = HelpNode(tr("help.block_catalog") if is_catalog else chapter.get("title", ""))
            category_node = None
            for topic in chapter.get("topics", []):
                if topic.get("_is_category"):
                    category_node = HelpNode(topic["title"], LOGIC_PREFIX + topic["id"])
                    node.children.append(category_node)
                elif topic.get("_category") and category_node is not None:
                    category_node.children.append(HelpNode(topic["title"], LOGIC_PREFIX + topic["id"]))
                else:
                    node.children.append(HelpNode(topic["title"], LOGIC_PREFIX + topic["id"]))
            if node.children:
                logic.children.append(node)
        if logic.children:
            nodes.append(logic)
        return nodes

    def keys(self) -> list:
        return [node.key for top in self.tree() for node in top.walk() if node.key]

    def title(self, key: str) -> str:
        for top in self.tree():
            for node in top.walk():
                if node.key == key:
                    return node.title
        return key

    # --- the text ---------------------------------------------------------------------------

    def markdown(self, key: str) -> str:
        source, topic = split_key(key)
        if source == "synoptic":
            path = os.path.join(_SYNOPTIC_DIR, self.lang, f"{topic}.md")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except OSError:
                return f"*({tr('help.missing', topic=key)})*"
        if source == "logic":
            try:
                from studio.shell.version import STUDIO_VERSION
                text = self._logic().load_topic_markdown(topic, version=STUDIO_VERSION)
            except Exception as e:  # noqa: BLE001 - shown, never raised into the panel
                return f"*({tr('help.missing', topic=key)}: {e})*"
            return _LOGIC_LINK.sub(lambda m: f"](help://logic/{m.group(1)})", text)
        from studio.shell.project_panels import load_help_topic_markdown
        return load_help_topic_markdown(topic, self.lang)

    # --- search -----------------------------------------------------------------------------

    def search(self, query: str) -> list:
        """Keys whose title or text contains every word of `query`, in tree order."""
        words = [w for w in query.lower().split() if w]
        if not words:
            return self.keys()
        hits = []
        for key in self.keys():
            haystack = (self.title(key) + "\n" + self.markdown(key)).lower()
            if all(word in haystack for word in words):
                hits.append(key)
        return hits
