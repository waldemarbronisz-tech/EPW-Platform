"""Loads the Help system's table of contents and topic content
(epw_os/help/<language>/) - headless (no PyQt import), same rule as
every other core/ module, so this loading/search logic is testable
without a QApplication and reusable if the Help window ever needs a
different front end.

Content is documentation, not UI chrome (GRANICE: "Tresc pomocy... to
dokumentacja - NIE przez tr()") - plain Markdown files, one per topic,
with a per-language toc.json defining the chapter/topic tree and the
index terms (task: "Hasla definiowane w plikach pomocy, nie zaszyte w
kodzie"). English is the fallback whenever the active language is
missing a file (task: "angielski jako zapasowy przy braku
tlumaczenia") - see HelpContentStore below.
"""
import json
import os

from epw_os.core.logging import log

# epw_os/core/help_content.py -> epw_os/help
HELP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "help")
FALLBACK_LANGUAGE = "en"


class HelpContentStore:
    """Loads toc.json + topic Markdown files for one language, falling
    back to English for anything missing. Never raises - a missing file
    is exactly the case this exists to handle gracefully (task: "brak
    pliku tematu nie wywala programu")."""

    def __init__(self, language: str, root: str = None):
        self.language = language
        self.root = root or HELP_ROOT
        self._toc_cache = {}

    def _toc_path(self, lang):
        return os.path.join(self.root, lang, "toc.json")

    def _topic_path(self, lang, topic_id):
        return os.path.join(self.root, lang, f"{topic_id}.md")

    @staticmethod
    def _read_json(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except OSError:
            # Missing file - the routine, EXPECTED case this store's
            # whole English-fallback design exists for (a language
            # directory or topic not translated yet - see load_toc()'s
            # own fallback and test_falls_back_to_english_*). Silent on
            # purpose: this fires on every untranslated topic lookup, so
            # logging it would drown out anything worth noticing.
            return None
        except ValueError as e:
            # The file EXISTS but isn't valid JSON - a real, actionable
            # problem (a hand-edit gone wrong, disk corruption), not the
            # routine "not translated yet" case above. Same "polykane
            # wyjatki" pattern as System.Mode - silently falling back to
            # English/a placeholder hid this from ever being noticed.
            log.warning(f"Malformed JSON in help file {path}: {e}")
            return None

    @staticmethod
    def _read_text(path):
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except OSError:
            # Same "routine, expected fallback" reasoning as
            # _read_json()'s OSError branch above - a missing topic file
            # in this language falls back to English, or to the "content
            # not found" placeholder if English doesn't have it either
            # (load_topic_markdown() handles that, never this method).
            return None

    def load_toc(self) -> dict:
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

    def topic_title(self, topic_id: str):
        for chapter in self.load_toc()["chapters"]:
            for topic in chapter["topics"]:
                if topic["id"] == topic_id:
                    return topic["title"]
        return None

    def load_topic_markdown(self, topic_id: str, version: str = "") -> str:
        """Never raises, never returns None - a topic id with no file in
        either language shows a plain, honest placeholder rather than
        crashing the window (or the whole program). `{version}` tokens
        in the content (welcome.md/about.md) are substituted here."""
        text = self._read_text(self._topic_path(self.language, topic_id))
        if text is None and self.language != FALLBACK_LANGUAGE:
            text = self._read_text(self._topic_path(FALLBACK_LANGUAGE, topic_id))
        if text is None:
            return f"# {topic_id}\n\n*(Content not found.)*"
        return text.replace("{version}", version) if version else text

    def all_topics(self):
        """[(topic_id, title, chapter_title)], flattened, in TOC order -
        used by the Index tab (already alphabetized there) and Search."""
        result = []
        for chapter in self.load_toc()["chapters"]:
            for topic in chapter["topics"]:
                result.append((topic["id"], topic["title"], chapter["title"]))
        return result

    def index_terms(self):
        """[(term, topic_id)], as authored in toc.json - NOT sorted here,
        so the caller controls presentation order explicitly."""
        return [(entry["term"], entry["topic"]) for entry in self.load_toc()["index"]]

    def search(self, query: str):
        """[(topic_id, title)] whose title OR Markdown content contains
        `query`, case-insensitively. Empty query matches nothing (an
        empty search box shouldn't just list every topic)."""
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
