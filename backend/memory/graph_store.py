"""Project Decision Memory Graph engine (persisted in .aether/memory_graph.json)."""
import json
import os
from typing import Any, Dict, List, Optional
from backend.models import MemoryNode, MemoryEdge

class MemoryGraphStore:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.aether_dir = os.path.join(repo_path, ".aether")
        self.graph_path = os.path.join(self.aether_dir, "memory_graph.json")
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.nodes = {n["id"]: n for n in data.get("nodes", [])}
                    self.edges = data.get("edges", [])
            except Exception:
                self.nodes = {}
                self.edges = []
        else:
            self._init_defaults()

    def _init_defaults(self):
        """Populate initial baseline facts for the repo."""
        os.makedirs(self.aether_dir, exist_ok=True)
        # Add deterministic facts
        self.add_node(
            MemoryNode(
                id="cmd:pytest",
                node_type="DeterministicFact",
                label="Baseline Test Command",
                properties={"command": "pytest tests -v", "framework": "pytest"},
                is_provisional=False,
            )
        )
        self.save()

    def save(self):
        os.makedirs(self.aether_dir, exist_ok=True)
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "repo": self.repo_path,
                    "nodes": list(self.nodes.values()),
                    "edges": self.edges,
                },
                f,
                indent=2,
            )

    def add_node(self, node: MemoryNode) -> None:
        self.nodes[node.id] = node.model_dump()

    def add_edge(self, edge: MemoryEdge) -> None:
        self.edges.append(edge.model_dump())

    def query(self, search_term: str, depth: int = 1) -> List[Dict[str, Any]]:
        """Selective subgraph retrieval: returns matching nodes and their 1-hop neighbors."""
        term = search_term.lower()
        matched_ids = set()
        for node_id, node in self.nodes.items():
            if term in node["label"].lower() or term in json.dumps(node["properties"]).lower():
                matched_ids.add(node_id)

        # Expand neighbors
        results = []
        for edge in self.edges:
            if edge["source"] in matched_ids:
                matched_ids.add(edge["target"])
            elif edge["target"] in matched_ids:
                matched_ids.add(edge["source"])

        for nid in matched_ids:
            if nid in self.nodes:
                results.append(self.nodes[nid])
        return results

    def mark_stale_if_modified(self, modified_files: List[str]) -> int:
        count = 0
        for node in self.nodes.values():
            ref_file = node.get("properties", {}).get("file")
            if ref_file and any(mf in ref_file for mf in modified_files):
                node["is_stale"] = True
                count += 1
        if count > 0:
            self.save()
        return count
