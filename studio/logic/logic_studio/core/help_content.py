"""feat/help-system §1.2/§4 — loads the Help window's table of contents
and hand-written topic content (logic_studio/help/<language>/), plus
bridges the generated block catalog (core/block_catalog.py) into the
same topic-id space. Headless (no PySide6 import), same rule as every
other core/ module — this loading/search logic is testable without a
QApplication, and this exact split (core/help_content.py here vs. a
thin ui/help_window.py Qt front end) is deliberately copied from
EPW-OS's own epw_os/core/help_content.py + epw_os/gui/widgets/
help_window.py — task §1.2 found that format already exists, dual-
language and file-based, and asked to reuse it rather than invent a
second one.

Content is documentation, not UI chrome: plain Markdown, one file per
topic, with a per-language toc.json defining the chapter/topic tree and
the index terms — never hand-transcribed from the code, per §3's own
"treść pisana ręcznie" vs. §2's generated catalog split. Polish is the
PRIMARY and fallback language here (reversed from EPW-OS, whose primary
is English) — this app's own UI has no i18n layer at all, every string
in it is Polish, and §3.4 explicitly allows the English tree to exist
with Polish content marked for future translation rather than none.

Two kinds of topic id:
- a plain id ("gs_what", "concept_labels", ...) -> read straight from
  <root>/<language>/<topic_id>.md, exactly like EPW-OS.
- "block:<type_id>" -> generated on the fly from block_catalog.py,
  never a file on disk at all (§2.2: "katalog NIE MOŻE się zestarzeć").
- "category:<name>" -> ditto, a category's own landing/index page.
"""
import json
import os

from logic_studio.core import block_catalog
from logic_studio.core import shortcuts as shortcuts_module

# logic_studio/core/help_content.py -> logic_studio/help
HELP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "help")
FALLBACK_LANGUAGE = "pl"

# Owner 2026-09-25 ("przy bramkach logicznych przykłady zastosowania,
# może jakieś krótkie gify z działaniem"): a generated block page may
# carry two hand-written/rendered extras, looked up by type_id -
#   <root>/<lang>/blocks/<type_id>.md   worked examples of use (per language)
#   <root>/media/<type_id>.gif          a short animation of the block at
#                                       work, drawn from the editor's own
#                                       canvas by studio/logic/tools/
#                                       render_help_animations.py
# Neither is required; a block without them shows the catalogue page alone.
BLOCK_EXAMPLES_DIR = "blocks"
MEDIA_ROOT = os.path.join(HELP_ROOT, "media")


def animation_path(type_id: str):
    """The animation file of a block type, or None when there is none."""
    path = os.path.join(MEDIA_ROOT, f"{type_id}.gif")
    return path if os.path.isfile(path) else None


def animation_url(type_id: str):
    """The file:// URL a Markdown image link needs (the same on every OS)."""
    from pathlib import Path
    path = animation_path(type_id)
    return Path(path).as_uri() if path else None

_BLOCK_CATEGORY_CHAPTER_ID = "block_catalog"


class HelpContentStore:
    """Loads toc.json + topic Markdown files for one language, falling
    back to Polish for anything missing (mirrors EPW-OS's
    HelpContentStore, English<->Polish roles swapped). Never raises — a
    missing file/unknown topic id is exactly the case this exists to
    handle gracefully."""

    def __init__(self, language: str = "pl", root: str = None):
        self.language = language
        self.root = root or HELP_ROOT
        self._toc_cache = {}
        self._catalog_cache = None

    # ---- static content (hand-written .md, §3) -----------------------------

    def _toc_path(self, lang):
        return os.path.join(self.root, lang, "toc.json")

    def _topic_path(self, lang, topic_id):
        return os.path.join(self.root, lang, f"{topic_id}.md")

    @staticmethod
    def _read_json(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _read_text(path):
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def _static_toc(self) -> dict:
        if self.language in self._toc_cache:
            return self._toc_cache[self.language]
        toc = self._read_json(self._toc_path(self.language))
        if toc is None and self.language != FALLBACK_LANGUAGE:
            toc = self._read_json(self._toc_path(FALLBACK_LANGUAGE))
        if not isinstance(toc, dict):
            toc = {"chapters": [], "index": []}
        toc.setdefault("chapters", [])
        toc.setdefault("index", [])
        self._toc_cache[self.language] = toc
        return toc

    def _static_topic_title(self, topic_id: str):
        for chapter in self._static_toc()["chapters"]:
            for topic in chapter["topics"]:
                if topic["id"] == topic_id:
                    return topic["title"]
        return None

    def _load_static_markdown(self, topic_id: str) -> str:
        text = self._read_text(self._topic_path(self.language, topic_id))
        if text is None and self.language != FALLBACK_LANGUAGE:
            text = self._read_text(self._topic_path(FALLBACK_LANGUAGE, topic_id))
        return text

    def _examples_path(self, lang, type_id):
        return os.path.join(self.root, lang, BLOCK_EXAMPLES_DIR, f"{type_id}.md")

    def block_examples_markdown(self, type_id: str) -> str:
        """The hand-written examples of a block type in this language
        (Polish when the language has none), "" when there are none."""
        text = self._read_text(self._examples_path(self.language, type_id))
        if text is None and self.language != FALLBACK_LANGUAGE:
            text = self._read_text(self._examples_path(FALLBACK_LANGUAGE, type_id))
        return (text or "").strip()

    def block_page_markdown(self, entry: dict) -> str:
        """The generated catalogue page plus its extras: the animation
        right under the description (before the pin table), the examples
        as the last section."""
        from logic_studio.i18n import tr
        markdown = block_catalog.block_entry_markdown(entry)
        url = animation_url(entry["type_id"])
        if url:
            figure = f"![{tr('catalog.animation_alt')}]({url})\n\n*{tr('catalog.animation_caption')}*\n\n"
            head, sep, tail = markdown.partition("\n## ")
            markdown = head.rstrip("\n") + "\n\n" + figure + (sep + tail if sep else "")
        examples = self.block_examples_markdown(entry["type_id"])
        if examples:
            markdown = markdown.rstrip("\n") + "\n\n## " + tr("catalog.examples") + "\n\n" + examples + "\n"
        return markdown

    # ---- generated content (block catalog, §2/§4) --------------------------

    def _catalog(self) -> dict:
        if self._catalog_cache is None:
            self._catalog_cache = block_catalog.generate_catalog()
        return self._catalog_cache

    def block_catalog_chapter(self) -> dict:
        """{"id": ..., "title": "Block catalog", "topics": [...]} — one
        topic per CATEGORY (id "category:<name>") plus, nested under it
        conceptually (flattened here since toc.json's own shape is one
        level of chapter/topic — the Contents TREE widget in the window
        adds the category level back visually, §4.2), one topic per
        block type (id "block:<type_id>"). §2.2: rebuilt from
        BlockRegistry every time this is called — never cached across
        calls to a fresh HelpContentStore, so a block added mid-session
        (there is no such thing today, blocks register at import time,
        but nothing here assumes otherwise) would still show up."""
        from shared.logic import i18n as block_i18n
        topics = []
        for category, entries in self._catalog().items():
            topics.append({"id": f"category:{category}", "title": block_i18n.category_label(category, self.language),
                           "_is_category": True})
            for entry in entries:
                topics.append({"id": f"block:{entry['type_id']}", "title": entry["display_name"], "_category": category})
        from logic_studio.i18n import tr
        # The chapter's own title follows the interface language like the
        # generated pages do (Studio's one help already translated it on
        # its side; the standalone window showed "Block catalog" in Polish).
        return {"id": _BLOCK_CATEGORY_CHAPTER_ID, "title": tr("help.block_catalog"), "topics": topics}

    # ---- unified topic API --------------------------------------------------

    def load_toc(self) -> dict:
        """Static chapters (§3, hand-written toc.json) + one generated
        "Block catalog" chapter (§2) appended after them — the
        Contents tab (ui/help_window.py) renders both from this single
        structure without needing to know which is which."""
        toc = self._static_toc()
        chapters = list(toc["chapters"]) + [self.block_catalog_chapter()]
        return {"chapters": chapters, "index": toc["index"]}

    def topic_title(self, topic_id: str):
        if topic_id.startswith("block:"):
            type_id = topic_id[len("block:"):]
            entry = block_catalog.describe_block_type(type_id)
            return entry["display_name"] if entry else topic_id
        if topic_id.startswith("category:"):
            from shared.logic import i18n as block_i18n
            return block_i18n.category_label(topic_id[len("category:"):], self.language)
        return self._static_topic_title(topic_id)

    def load_topic_markdown(self, topic_id: str, version: str = "") -> str:
        """Never raises, never returns None — an unknown topic id shows
        a plain, honest placeholder instead of crashing the window (or
        the whole program), exactly like EPW-OS's own contract."""
        if topic_id.startswith("block:"):
            type_id = topic_id[len("block:"):]
            entry = block_catalog.describe_block_type(type_id)
            if entry is None:
                return f"# {type_id}\n\n*(Unknown block type.)*"
            return self.block_page_markdown(entry)

        if topic_id.startswith("category:"):
            from shared.logic import i18n as block_i18n
            category = topic_id[len("category:"):]
            entries = self._catalog().get(category, [])
            return block_catalog.category_index_markdown(block_i18n.category_label(category, self.language), entries)

        if topic_id == "shortcuts":
            # §3.3: generated from the actual _make_action() call sites
            # in ui/main_window.py, never hand-transcribed — see
            # core/shortcuts.py's own module docstring.
            return shortcuts_module.shortcuts_markdown()

        text = self._load_static_markdown(topic_id)
        if text is None:
            return f"# {topic_id}\n\n*(Content not found.)*"
        return text.replace("{version}", version) if version else text

    def all_topics(self):
        """[(topic_id, title, chapter_title)], flattened, in TOC order —
        used by the Index tab and Search. Category topics (pure
        navigation nodes) are included too — searching/indexing a
        category NAME is legitimate (e.g. "Logic gates")."""
        result = []
        for chapter in self.load_toc()["chapters"]:
            for topic in chapter["topics"]:
                result.append((topic["id"], topic["title"], chapter["title"]))
        return result

    def index_terms(self):
        """[(term, topic_id)] — static index (toc.json's "index" array,
        §3's own hand-authored hasła) plus one auto-generated entry per
        block type/alias (§2: the catalog must never need separate,
        hand-maintained index upkeep either)."""
        terms = [(entry["term"], entry["topic"]) for entry in self._static_toc()["index"]]
        for category, entries in self._catalog().items():
            for entry in entries:
                terms.append((entry["display_name"], f"block:{entry['type_id']}"))
                for alias in entry["aliases"]:
                    terms.append((alias, f"block:{entry['type_id']}"))
        return terms

    def search(self, query: str):
        """[(topic_id, title)] whose title OR Markdown content contains
        `query`, case-insensitively. Empty query matches nothing."""
        query = (query or "").strip().lower()
        if not query:
            return []
        results = []
        for topic_id, title, _chapter in self.all_topics():
            haystack = title.lower()
            if query not in haystack:
                haystack += "\n" + self.load_topic_markdown(topic_id).lower()
            if query in haystack:
                results.append((topic_id, title))
        return results
