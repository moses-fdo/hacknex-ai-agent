"""Project Decision Memory Graph engine (persisted in .aether/memory_graph.json).

Fulfills PRD v1.3 FR-4:
- Deterministic fact ingestion
- Provisional vs verified decisions
- Provenance & stale invalidation
- Conflict detection against verified nodes
"""
import json
import os
import subprocess
from typing import Any, Dict, List, Optional, Set
from backend.models import MemoryNode, MemoryEdge

class MemoryGraphStore:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.aether_dir = os.path.join(self.repo_path, ".aether")
        self.graph_path = os.path.join(self.aether_dir, "memory_graph.json")
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self._load()

    def _get_head_commit(self) -> Optional[str]:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return None

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
        head_commit = self._get_head_commit()
        # Add deterministic facts
        self.add_node(
            MemoryNode(
                id="cmd:pytest",
                node_type="DeterministicFact",
                label="Baseline Test Command",
                properties={"command": "pytest tests -v", "framework": "pytest"},
                provenance_commit_sha=head_commit,
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
        self.save()

    def add_edge(self, edge: MemoryEdge) -> None:
        edge_dict = edge.model_dump()
        if edge_dict not in self.edges:
            self.edges.append(edge_dict)
            self.save()

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.nodes.get(node_id)

    def verify_node(self, node_id: str, verified: bool = True) -> bool:
        """FR-4.3: Manually mark provisional decision as verified."""
        if node_id in self.nodes:
            self.nodes[node_id]["is_provisional"] = not verified
            self.save()
            return True
        return False

    def get_advisory_hints(self) -> List[Dict[str, Any]]:
        """FR-4.3: Provisional entries act strictly as advisory hints."""
        return [n for n in self.nodes.values() if n.get("is_provisional", False) and not n.get("is_stale", False)]

    def get_verified_rules(self) -> List[Dict[str, Any]]:
        """Return verified architectural rules and deterministic facts."""
        return [
            n for n in self.nodes.values()
            if not n.get("is_provisional", False)
            and not n.get("is_stale", False)
            and n.get("node_type") in ("ArchitecturalDecision", "DeterministicFact", "VetoRecord")
        ]

    def query(self, search_term: str, depth: int = 1) -> List[Dict[str, Any]]:
        """Selective subgraph retrieval: returns matching non-stale nodes and their 1-hop neighbors."""
        term = search_term.lower()
        matched_ids = set()
        for node_id, node in self.nodes.items():
            if node.get("is_stale", False):
                continue
            label = node.get("label", "").lower()
            props = json.dumps(node.get("properties", {})).lower()
            if term in label or term in props:
                matched_ids.add(node_id)

        # Expand neighbors up to depth
        results = []
        for edge in self.edges:
            if edge["source"] in matched_ids:
                matched_ids.add(edge["target"])
            elif edge["target"] in matched_ids:
                matched_ids.add(edge["source"])

        for nid in matched_ids:
            if nid in self.nodes and not self.nodes[nid].get("is_stale", False):
                results.append(self.nodes[nid])
        return results

    def mark_stale_by_git(self) -> int:
        """FR-4.4: Invalidate nodes if referenced file changed between provenance_commit_sha and HEAD."""
        head_sha = self._get_head_commit()
        if not head_sha:
            return 0

        stale_count = 0
        for node in self.nodes.values():
            if node.get("is_stale", False):
                continue
            prov_sha = node.get("provenance_commit_sha")
            ref_file = node.get("properties", {}).get("file")

            if prov_sha and ref_file and prov_sha != head_sha:
                try:
                    res = subprocess.run(
                        ["git", "diff", "--name-only", prov_sha, head_sha],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True
                    )
                    if res.returncode == 0:
                        modified_files = res.stdout.splitlines()
                        if any(ref_file.endswith(mf) or mf.endswith(ref_file) for mf in modified_files):
                            node["is_stale"] = True
                            stale_count += 1
                except Exception:
                    pass

        if stale_count > 0:
            self.save()
        return stale_count

    def check_conflicts(self, proposed_files: List[str], proposed_symbols: List[str]) -> List[str]:
        """FR-4.5: Trigger conflict warning if worker proposal contradicts verified memory node."""
        conflicts = []
        verified_rules = self.get_verified_rules()

        for rule in verified_rules:
            props = rule.get("properties", {})
            r_file = props.get("file", "")
            r_symbol = props.get("symbol", "")
            r_veto = (rule.get("node_type") == "VetoRecord")

            for pf in proposed_files:
                if r_file and (r_file.endswith(pf) or pf.endswith(r_file)):
                    if r_veto:
                        conflicts.append(
                            f"VETO WARNING: Past run vetoed changes to '{r_file}' because: {rule.get('label')}"
                        )
                    elif rule.get("node_type") == "ArchitecturalDecision":
                        conflicts.append(
                            f"ARCHITECTURAL INVARIANT: '{r_file}' is constrained by: {rule.get('label')}"
                        )

            for ps in proposed_symbols:
                if r_symbol and ps == r_symbol and r_veto:
                    conflicts.append(
                        f"VETO WARNING: Symbol '{ps}' previously failed regression checks: {rule.get('label')}"
                    )

        return conflicts

    def sync_cartographer_index(self, index: Dict[str, Any], commit_sha: Optional[str] = None):
        """FR-4.2: Ingest deterministic AST symbols and import dependencies."""
        commit_sha = commit_sha or self._get_head_commit()
        for file_path, file_data in index.get("files", {}).items():
            file_id = f"file:{file_path}"
            self.add_node(
                MemoryNode(
                    id=file_id,
                    node_type="File",
                    label=file_path,
                    properties={"path": file_path, "imports": file_data.get("imports", [])},
                    provenance_commit_sha=commit_sha,
                    is_provisional=False,
                )
            )

            for sym in file_data.get("symbols", []):
                sym_id = f"symbol:{file_path}:{sym['name']}"
                self.add_node(
                    MemoryNode(
                        id=sym_id,
                        node_type="Symbol",
                        label=f"{sym['type'].capitalize()} {sym['name']}",
                        properties={
                            "name": sym["name"],
                            "type": sym["type"],
                            "file": file_path,
                            "lineno": sym["lineno"],
                            "args": sym.get("args", []),
                        },
                        provenance_commit_sha=commit_sha,
                        is_provisional=False,
                    )
                )
                self.add_edge(MemoryEdge(source=file_id, target=sym_id, relation="DEFINES"))

        self.save()
