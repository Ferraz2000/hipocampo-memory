"""Tests for hipocampo.views — DQL subset, execution, rendering, materialization.

Fixtures mirror the origin project's real dashboard shapes (TABLE with WHERE/
SORT/LIMIT, grouped TABLE WITHOUT ID with length(rows) and filter(...) counts,
LIST) so Phase-B migration compatibility is covered here.
"""

import tempfile
import unittest
from pathlib import Path

from hipocampo import views
from hipocampo.config import Config, DEFAULTS
from hipocampo.views import (Note, build_all, execute, iter_dataview_blocks,
                             parse_dql, render)


def _note(name, rel_dir="technical", **fields):
    return Note(f"/x/{name}.md", name, rel_dir, fields)


NOTES = [
    _note("a", status="active", impact="high", area="perf", implemented_at=""),
    _note("b", status="closed", impact="low", area="perf", implemented_at="2026-01-02"),
    _note("c", status="active", impact="medium", area="ux", implemented_at=""),
    _note("d", rel_dir="technical/deep", status="triage", impact="high", area="perf"),
]


class ParseTest(unittest.TestCase):
    def test_table_with_where_sort_limit(self):
        q = parse_dql('TABLE status AS "Status", impact\n'
                      'FROM "insights/technical"\n'
                      'WHERE status = "active" AND impact != "low"\n'
                      'SORT impact DESC\nLIMIT 5')
        self.assertEqual(q.kind, "table")
        self.assertEqual([c.label for c in q.columns], ["Status", "impact"])
        self.assertEqual(q.from_path, "insights/technical")
        self.assertEqual(q.limit, 5)
        self.assertEqual(q.sort, [("impact", "DESC")])

    def test_grouped_without_id(self):
        q = parse_dql('TABLE WITHOUT ID area AS "Area", length(rows) AS "Total"\n'
                      'FROM "insights/technical"\nGROUP BY area')
        self.assertTrue(q.without_id)
        self.assertEqual(q.group_by, "area")

    def test_list(self):
        q = parse_dql('LIST FROM "insights/technical" WHERE status = "triage"')
        self.assertEqual(q.kind, "list")


class ExecuteTest(unittest.TestCase):
    def test_where_and_sort(self):
        q = parse_dql('TABLE impact FROM "insights" WHERE status = "active" SORT impact DESC')
        rows = execute(q, NOTES, "insights")
        self.assertEqual([n.name for n in rows], ["a", "c"])  # high before medium

    def test_from_subdir_filters_rel_dir(self):
        q = parse_dql('LIST FROM "insights/technical/deep"')
        rows = execute(q, NOTES, "insights")
        self.assertEqual([n.name for n in rows], ["d"])

    def test_negation_and_truthy(self):
        q = parse_dql('LIST FROM "insights" WHERE !implemented_at AND status != "triage"')
        rows = execute(q, NOTES, "insights")
        self.assertEqual({n.name for n in rows}, {"a", "c"})

    def test_group_by_counts(self):
        q = parse_dql('TABLE WITHOUT ID area, length(rows) AS "n",\n'
                      '  filter(rows, (r) => r.status = "active") AS "active"\n'
                      'FROM "insights" GROUP BY area SORT length(rows) DESC')
        groups = execute(q, NOTES, "insights")
        self.assertEqual(groups[0].key, "perf")
        out = render(q, groups, "../insights")
        self.assertIn("| perf | 3 | 1 |", out)

    def test_render_table_links_and_empty(self):
        q = parse_dql('TABLE status FROM "insights" WHERE status = "active" SORT file.name ASC')
        out = render(q, execute(q, NOTES, "insights"), "../insights")
        self.assertIn("[a](../insights/technical/a.md)", out)
        empty = render(q, [], "../insights")
        self.assertEqual(empty, "_none_")


class MaterializeTest(unittest.TestCase):
    def test_build_all_end_to_end_and_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ins = root / "docs/brain/insights/technical"
            ins.mkdir(parents=True)
            (ins / "x.md").write_text(
                "---\ntitle: X\nstatus: active\nimpact: high\narea: perf\n---\n# X\n",
                encoding="utf-8")
            dash = root / "docs/brain/10-dash.md"
            dash.write_text(
                "# Dash\n\n## Active\n\n```dataview\n"
                'TABLE impact AS "Impact" FROM "insights" WHERE status = "active"\n'
                "```\n", encoding="utf-8")
            cfg = Config(DEFAULTS, root)

            built = build_all(cfg)
            self.assertEqual(len(built), 1)
            gen_path, content = next(iter(built.items()))
            self.assertIn("_generated", gen_path)
            self.assertIn("## Active", content)
            self.assertIn("[x](../insights/technical/x.md)", content)
            self.assertIn("| high |", content)
            self.assertIn("AUTO-GENERATED", content)

    def test_iter_blocks_tracks_nearest_heading(self):
        text = ("## First\n```dataview\nLIST\n```\n"
                "## Second\nprose\n```dataview\nTABLE x\n```\n")
        blocks = list(iter_dataview_blocks(text))
        self.assertEqual([h for h, _ in blocks], ["First", "Second"])


if __name__ == "__main__":
    unittest.main()
