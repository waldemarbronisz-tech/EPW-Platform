"""Task "edytor DI/DO/AI" - project_panels.py's pure data-logic
functions (sync_points_for_card/remove_points_for_card/points_for_card),
exercised without Qt - same reasoning as test_project_format.py's own
header: no widget needs to exist for "karty rodzą punkty" itself to be
correct. The QWidget classes (ProjectInfoPanel/CardsPanel/
PointRegistryPanel) are covered indirectly by main_window.py's own
smoke path (constructed, clicked through, screenshotted - see this
task's own chat report), not unit-tested here.
"""
from studio.shell.project_format import Card, Point, new_project
from studio.shell.project_panels import (
    points_for_card,
    remove_points_for_card,
    sync_points_for_card,
)


def _project():
    return new_project("Test")


def test_sync_points_for_card_creates_one_point_per_channel():
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=4)
    project.cards.append(card)
    sync_points_for_card(project, card)
    addresses = [p.address for p in project.points]
    assert addresses == ["ELA1.DI.1", "ELA1.DI.2", "ELA1.DI.3", "ELA1.DI.4"]


def test_sync_points_for_card_preserves_existing_descriptions():
    """"Karty rodzą punkty [...] Nie wpisujesz ich ręcznie" - but
    re-syncing (e.g. after editing the card's model, which doesn't
    change its address space) must never wipe out a name a user already
    typed into an existing point."""
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    project.cards.append(card)
    sync_points_for_card(project, card)
    project.points[0].description = "Wylacznik glowny"

    card.model = "ELA01-rev2"
    sync_points_for_card(project, card)

    assert project.points[0].description == "Wylacznik glowny"


def test_sync_points_for_card_drops_points_beyond_shrunk_channel_count():
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=4)
    project.cards.append(card)
    sync_points_for_card(project, card)
    project.points[3].description = "Doomed"

    card.channels = 2
    sync_points_for_card(project, card)

    addresses = [p.address for p in project.points]
    assert addresses == ["ELA1.DI.1", "ELA1.DI.2"]


def test_sync_points_for_card_grows_without_touching_existing_ones():
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    project.cards.append(card)
    sync_points_for_card(project, card)
    project.points[0].description = "Named"

    card.channels = 3
    sync_points_for_card(project, card)

    assert [p.address for p in project.points] == ["ELA1.DI.1", "ELA1.DI.2", "ELA1.DI.3"]
    assert project.points[0].description == "Named"
    assert project.points[2].description == ""


def test_sync_points_for_card_does_not_touch_other_cards():
    project = _project()
    card_a = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    card_b = Card(id="ADA1", model="ADA01", kind="DO", channels=2)
    project.cards.extend([card_a, card_b])
    sync_points_for_card(project, card_a)
    sync_points_for_card(project, card_b)
    next(p for p in project.points if p.address == "ADA1.DO.1").description = "Untouched"

    card_a.channels = 3
    sync_points_for_card(project, card_a)

    by_address = {p.address: p.description for p in project.points}
    assert by_address["ADA1.DO.1"] == "Untouched"
    assert "ELA1.DI.3" in by_address


def test_remove_points_for_card_removes_only_its_own_points():
    project = _project()
    card_a = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    card_b = Card(id="ADA1", model="ADA01", kind="DO", channels=2)
    project.cards.extend([card_a, card_b])
    sync_points_for_card(project, card_a)
    sync_points_for_card(project, card_b)

    remove_points_for_card(project, card_a)

    addresses = [p.address for p in project.points]
    assert addresses == ["ADA1.DO.1", "ADA1.DO.2"]


def test_points_for_card_filters_by_address_prefix():
    project = _project()
    card = Card(id="ELA1", model="ELA01", kind="DI", channels=2)
    project.cards.append(card)
    sync_points_for_card(project, card)
    project.points.append(Point(address="ADA1.DO.1"))

    result = points_for_card(project, card)

    assert {p.address for p in result} == {"ELA1.DI.1", "ELA1.DI.2"}
