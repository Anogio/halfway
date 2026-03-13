from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from transit_offline.common.artifacts import archive_existing_artifacts


class ArtifactArchiveTest(unittest.TestCase):
    def test_archive_existing_artifacts_moves_matches_into_old_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            artifacts = Path(td)
            (artifacts / "graph_v1_weekday.json").write_text("{}", encoding="utf-8")
            (artifacts / "nodes_v1.csv").write_text("node_idx\n", encoding="utf-8")
            (artifacts / "keep.txt").write_text("keep", encoding="utf-8")

            archived = archive_existing_artifacts(
                artifacts,
                patterns=("graph_*_weekday.json", "nodes_*.csv"),
            )

            self.assertEqual(len(archived), 2)
            self.assertFalse((artifacts / "graph_v1_weekday.json").exists())
            self.assertFalse((artifacts / "nodes_v1.csv").exists())
            self.assertTrue((artifacts / "keep.txt").exists())
            self.assertTrue((artifacts / "old").exists())
            self.assertTrue(all(path.parent == artifacts / "old" for path in archived))
            archived_names = sorted(path.name.split("_", 1)[1] for path in archived)
            self.assertEqual(archived_names, ["graph_v1_weekday.json", "nodes_v1.csv"])
