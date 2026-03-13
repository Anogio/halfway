from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from transit_backend.core.artifacts import load_runtime_data


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class ArtifactsLoadTest(unittest.TestCase):
    def test_missing_graph_artifact_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "nodes_vtest.csv",
                "node_idx,stop_id,stop_name,lat,lon\n0,S0,Stop 0,48.85,2.35\n",
            )
            with self.assertRaises(FileNotFoundError):
                load_runtime_data(root, "vtest")

    def test_malformed_graph_json_raises_decode_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "graph_vtest_weekday.json", "{broken json")
            _write(
                root / "nodes_vtest.csv",
                "node_idx,stop_id,stop_name,lat,lon\n0,S0,Stop 0,48.85,2.35\n",
            )
            with self.assertRaises(json.JSONDecodeError):
                load_runtime_data(root, "vtest")

    def test_missing_required_graph_arrays_raises_key_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "graph_vtest_weekday.json", json.dumps({"version": "vtest"}))
            _write(
                root / "nodes_vtest.csv",
                "node_idx,stop_id,stop_name,lat,lon\n0,S0,Stop 0,48.85,2.35\n",
            )
            with self.assertRaises(KeyError):
                load_runtime_data(root, "vtest")

    def test_load_runtime_data_parses_v2_node_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "graph_v2_weekday.json",
                json.dumps(
                    {
                        "version": "v2",
                        "profile": "weekday_non_holiday",
                        "nodes_count": 2,
                        "nodes_index": {"A": 0},
                        "node_key_index": {"A": 0, "A::R1::0": 1},
                        "adj_offsets": [0, 1, 1],
                        "adj_targets": [1],
                        "adj_weights_s": [120],
                        "edge_kind": [1],
                        "edge_route_id": ["R1"],
                        "route_labels": {"R1": "R1"},
                        "edge_kind_legend": {"1": "boarding"},
                    }
                ),
            )
            _write(
                root / "nodes_v2.csv",
                "\n".join(
                    [
                        "node_idx,node_kind,node_key,stop_id,stop_name,parent_station,lat,lon,location_type,is_rail_like,physical_node_idx,route_id,direction_id",
                        "0,physical,A,STOP_A,Stop A,,48.85,2.35,0,1,,,",
                        "1,onboard,A::R1::0,STOP_A,Stop A,,48.85,2.35,0,1,0,R1,0",
                    ]
                )
                + "\n",
            )

            runtime = load_runtime_data(root, "v2")
            self.assertEqual(runtime.version, "v2")
            self.assertEqual(runtime.nodes[0].node_kind, "physical")
            self.assertEqual(runtime.nodes[1].node_kind, "onboard")
            self.assertEqual(runtime.nodes[1].physical_node_idx, 0)
            self.assertEqual(runtime.node_key_index["A::R1::0"], 1)
            self.assertEqual(runtime.reverse_offsets, [0, 0, 1])
            self.assertEqual(runtime.reverse_targets, [0])
            self.assertEqual(runtime.reverse_weights, [120])
            self.assertEqual(runtime.reverse_edge_to_forward, [0])
