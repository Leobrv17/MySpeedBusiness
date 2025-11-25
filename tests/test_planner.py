import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from msb.services.planner import Planner


def _tables_by_person(plan, excluded=None):
    excluded = set(excluded or [])
    mapping = defaultdict(list)
    for session in plan:
        for table_idx, people in enumerate(session):
            for person in people:
                if person in excluded:
                    continue
                mapping[person].append(table_idx)
    return mapping


def test_avoids_duplicate_tables_when_possible():
    planner = Planner()
    plan = planner.build_plan(
        num_tables=3,
        sessions=2,
        table_capacities=[2, 2, 2],
        fixed_leads=[],
        people=list(range(6)),
        seed=42,
    )

    per_person_tables = _tables_by_person(plan)
    assert all(len(set(tables)) == len(tables) for tables in per_person_tables.values())


def test_rotation_priority_with_fixed_leads_and_tight_capacity():
    planner = Planner()
    leads = [100, 101, 102]
    plan = planner.build_plan(
        num_tables=3,
        sessions=3,
        table_capacities=[3, 3, 3],
        fixed_leads=leads,
        people=list(range(6)),
        seed=7,
    )

    per_person_tables = _tables_by_person(plan, excluded=leads)
    for tables in per_person_tables.values():
        counts = Counter(tables)
        assert all(count <= 1 for count in counts.values())


def test_fallback_allows_duplicates_only_after_rotation():
    planner = Planner()
    plan = planner.build_plan(
        num_tables=2,
        sessions=3,
        table_capacities=[2, 2],
        fixed_leads=[],
        people=list(range(4)),
        seed=9,
    )

    per_person_tables = _tables_by_person(plan)
    for tables in per_person_tables.values():
        assert set(tables[:2]) == {0, 1}
        assert len(tables) == 3

def test_respects_capacities_and_includes_everyone():
    planner = Planner()
    plan = planner.build_plan(
        num_tables=2,
        sessions=2,
        table_capacities=[3, 3],
        fixed_leads=[10, 11],
        people=list(range(4)),
        seed=12,
    )

    expected_people = set(range(4)).union({10, 11})
    for session in plan:
        flat = [p for table in session for p in table]
        assert set(flat) == expected_people
        assert [len(table) for table in session] == [3, 3]
        assert session[0][0] == 10 and session[1][0] == 11


def test_raises_when_capacity_too_small_for_leads():
    planner = Planner()
    with pytest.raises(ValueError):
        planner.build_plan(
            num_tables=1,
            sessions=1,
            table_capacities=[0],
            fixed_leads=[99],
            people=[],
        )
