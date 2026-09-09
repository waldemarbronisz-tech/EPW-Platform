"""Tests for the Help system's content loading/search
(epw_os/core/help_content.py) - headless, no Qt needed at all."""

import json
import os

import pytest

from epw_os.core.help_content import HelpContentStore, HELP_ROOT


@pytest.fixture
def pl_store():
    return HelpContentStore("pl")


@pytest.fixture
def en_store():
    return HelpContentStore("en")


# --- DOWÓD: the contents tree builds from files, a missing topic file
# does not crash the program ------------------------------------------

def test_toc_builds_a_real_chapter_and_topic_tree(pl_store):
    toc = pl_store.load_toc()
    assert len(toc["chapters"]) >= 10, "expected a real, non-trivial chapter list"
    total_topics = sum(len(c["topics"]) for c in toc["chapters"])
    assert total_topics >= 30, "expected a real, non-trivial topic list"
    for chapter in toc["chapters"]:
        assert chapter["id"]
        assert chapter["title"]
        for topic in chapter["topics"]:
            assert topic["id"]
            assert topic["title"]


def test_missing_topic_file_does_not_raise(pl_store):
    # DOWÓD: "brak pliku tematu nie wywala programu" - exercised directly
    # against a topic id that is guaranteed not to exist anywhere.
    text = pl_store.load_topic_markdown("this_topic_id_does_not_exist_anywhere")
    assert isinstance(text, str)
    assert "this_topic_id_does_not_exist_anywhere" in text


def test_missing_toc_file_does_not_raise(tmp_path):
    # A language directory that doesn't exist at all - load_toc() must
    # fall back to English gracefully rather than raising.
    store = HelpContentStore("zz_nonexistent", root=str(tmp_path))
    toc = store.load_toc()
    assert toc == {"chapters": [], "index": []}, \
        "with no en/ directory to fall back to either, an empty-but-valid TOC is expected"


# --- Every topic referenced in the TOC actually has a file (both
# languages) - a structural regression guard -----------------------------

@pytest.mark.parametrize("language", ["pl", "en"])
def test_every_toc_topic_has_a_matching_markdown_file(language):
    store = HelpContentStore(language)
    for topic_id, title, chapter_title in store.all_topics():
        path = os.path.join(HELP_ROOT, language, f"{topic_id}.md")
        assert os.path.exists(path), f"{language}/{topic_id}.md is missing (chapter: {chapter_title})"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_every_topic_file_loads_and_is_not_empty(language):
    store = HelpContentStore(language)
    for topic_id, title, _chapter in store.all_topics():
        text = store.load_topic_markdown(topic_id)
        assert text.strip(), f"{language}/{topic_id}.md is empty"
        assert "(Content not found.)" not in text, f"{language}/{topic_id}.md resolved to the not-found placeholder"


# --- English fallback (task: "angielski jako zapasowy przy braku
# tlumaczenia") ---------------------------------------------------------

def test_falls_back_to_english_when_the_topic_file_is_missing_in_this_language(tmp_path):
    lang_dir = tmp_path / "de"
    en_dir = tmp_path / "en"
    lang_dir.mkdir()
    en_dir.mkdir()
    (lang_dir / "toc.json").write_text(json.dumps({"chapters": [], "index": []}), encoding="utf-8")
    (en_dir / "toc.json").write_text(json.dumps({"chapters": [], "index": []}), encoding="utf-8")
    (en_dir / "only_in_english.md").write_text("# English only\n\nContent.", encoding="utf-8")

    store = HelpContentStore("de", root=str(tmp_path))
    text = store.load_topic_markdown("only_in_english")
    assert "English only" in text


def test_falls_back_to_english_toc_when_the_language_toc_is_entirely_missing(tmp_path):
    en_dir = tmp_path / "en"
    en_dir.mkdir()
    (en_dir / "toc.json").write_text(
        json.dumps({"chapters": [{"id": "c1", "title": "Chapter", "topics": [{"id": "t1", "title": "Topic"}]}],
                    "index": []}),
        encoding="utf-8",
    )
    store = HelpContentStore("de", root=str(tmp_path))  # de/ directory doesn't exist at all
    toc = store.load_toc()
    assert len(toc["chapters"]) == 1
    assert toc["chapters"][0]["id"] == "c1"


def test_own_language_file_wins_over_english_when_both_exist(tmp_path):
    for lang, content in (("pl", "# Polski\n"), ("en", "# English\n")):
        d = tmp_path / lang
        d.mkdir()
        (d / "toc.json").write_text(json.dumps({"chapters": [], "index": []}), encoding="utf-8")
        (d / "shared_topic.md").write_text(content, encoding="utf-8")
    store = HelpContentStore("pl", root=str(tmp_path))
    assert "Polski" in store.load_topic_markdown("shared_topic")


# --- DOWÓD: search finds topics by content ------------------------------

def test_search_finds_topics_by_title(pl_store):
    results = pl_store.search("Poziomy dostępu")
    ids = [r[0] for r in results]
    assert "al_three" in ids


def test_search_finds_topics_by_body_content_not_just_title(en_store):
    # "safety_kernel" is mentioned in the body of several topics whose
    # titles don't contain that word at all - proves this searches the
    # actual Markdown content, not just the title.
    results = en_store.search("safety_kernel")
    ids = [r[0] for r in results]
    assert "saf_kernel" in ids
    assert len(ids) > 1, "expected more than just the one topic literally named after it"


def test_search_is_case_insensitive(pl_store):
    lower = {r[0] for r in pl_store.search("engineer")}
    upper = {r[0] for r in pl_store.search("ENGINEER")}
    assert lower == upper
    assert lower


def test_empty_search_returns_nothing(pl_store):
    assert pl_store.search("") == []
    assert pl_store.search("   ") == []


def test_search_for_nonsense_returns_nothing(pl_store):
    assert pl_store.search("xyzzy_not_a_real_word_qqq") == []


# --- Index (task: "hasla definiowane w plikach pomocy, nie zaszyte w
# kodzie") ---------------------------------------------------------------

@pytest.mark.parametrize("language", ["pl", "en"])
def test_every_index_entry_points_to_a_real_topic(language):
    store = HelpContentStore(language)
    valid_ids = {topic_id for topic_id, _title, _chapter in store.all_topics()}
    for term, topic_id in store.index_terms():
        assert term
        assert topic_id in valid_ids, f"index term {term!r} points to unknown topic {topic_id!r}"


def test_index_has_a_substantial_number_of_terms(pl_store):
    assert len(pl_store.index_terms()) >= 20


# --- DOWÓD (Task: uzupelnienie dokumentacji, B2): every page in the left
# navigation tree has at least one real help topic, in BOTH languages -
# not just "some topic id is referenced somewhere in toc.json" (already
# covered above), but specifically tied to nav_model.py's own page ids,
# so a brand-new page added later with no help coverage at all fails
# this test instead of silently shipping undocumented. -----------------

# One representative topic id per nav page - built by manually walking
# nav_model.NAV_STRUCTURE against both languages' toc.json chapters (see
# SESSION_REPORT.md's help-audit section). Deliberately NOT auto-derived
# from anything (there is no formal page_id -> topic_id link anywhere in
# the actual program) - a hand-maintained map is exactly what should
# force a human decision (and an update here) the next time a page is
# added, rather than a heuristic that could silently "pass" against a
# page nobody actually documented.
_PAGE_ID_TO_HELP_TOPIC = {
    "main_view": "mv_synoptic",
    "digital_inputs": "dio_purpose",
    "analog_inputs": "ap_what",
    "control_outputs": "dio_purpose",
    "intrusion_overview": "intr_what",
    "intrusion_history": "intr_history",
    "intrusion_config": "intr_zones_lines",
    "power_quality": "pq_what",
    "trends": "trends_page",
    "events": "ea_recorder",
    "alarms": "alm_source",
    "audit_log": "ea_audit_log",
    "system_topology": "st_what",
    "bus_diagnostics": "bus_diag_what",
    "engineer_mode": "saf_engineer_mode",
    "protection_electrical": "prot_electrical",
    "protection_process": "prot_process",
}


def test_every_nav_page_id_is_mapped_to_a_help_topic():
    from epw_os.core.nav_model import all_page_ids
    missing = set(all_page_ids()) - set(_PAGE_ID_TO_HELP_TOPIC)
    assert not missing, f"nav page(s) with no known help topic mapping: {missing}"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_every_nav_pages_help_topic_exists_in_this_language(language):
    store = HelpContentStore(language)
    valid_ids = {topic_id for topic_id, _title, _chapter in store.all_topics()}
    for page_id, topic_id in _PAGE_ID_TO_HELP_TOPIC.items():
        assert topic_id in valid_ids, f"page {page_id!r}'s help topic {topic_id!r} does not exist in {language}/"


# --- {version} substitution (welcome.md / about.md) ---------------------

def test_version_token_is_substituted_when_requested(pl_store):
    text = pl_store.load_topic_markdown("welcome", version="9.9.9")
    assert "9.9.9" in text
    assert "{version}" not in text


def test_version_token_left_alone_when_not_requested(pl_store):
    text = pl_store.load_topic_markdown("welcome")
    assert "{version}" in text
