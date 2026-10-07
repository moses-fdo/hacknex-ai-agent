"""Comprehensive test suite for Aether-SWE Backend matching PRD v1.3."""
import asyncio
import json
import os
import shutil
import pytest
from fastapi.testclient import TestClient

from backend.api.server import app, engine
from backend.client.byom_client import BYOMClient, BudgetExceededException
from backend.memory.graph_store import MemoryGraphStore
from backend.models import (
    IssueInput,
    MemoryNode,
    RunStatus,
    WorkerKind,
)
from backend.orchestrator.engine import OrchestratorEngine
from backend.tools.cartographer import Cartographer
from backend.tools.critic import Critic
from backend.tools.judge import Judge
from backend.tools.preflight import PreflightCheck
from backend.tools.sentinel import Sentinel
from backend.workers.registry import WorkerRegistry
from backend.worktree.diff_applier import DiffApplier, ScopeGuardViolation
from backend.worktree.manager import WorktreeManager

client = TestClient(app)

# ==============================================================================
# 1. Triage Gate Tests (FR-1)
# ==============================================================================

def test_triage_anchored_issue():
    desc = (
        "Token verification error in app/auth/tokens.py::is_token_expired(). "
        "Expected valid token to return False, but instead got True."
    )
    result = WorkerRegistry.triage_issue(desc)
    assert result.has_symptom is True
    assert result.has_expected_vs_actual is True
    assert result.is_anchored is True
    assert any("tokens.py" in a for a in result.anchors)

def test_triage_unanchored_interactive():
    desc = "Something is broken in the login system."
    result = WorkerRegistry.triage_issue(desc)
    assert result.is_anchored is False
    assert len(result.clarification_questions) == 2
    assert result.assumption_stated is not None

# ==============================================================================
# 2. BYOM Client & Budget Enforcement Tests (FR-6)
# ==============================================================================

def test_byom_pricing_and_reserve():
    byom = BYOMClient(default_model="claude-3-5-sonnet", max_budget_usd=1.00, reserve_percent=10)
    assert byom.price_per_m_input == 3.00
    assert byom.price_per_m_output == 15.00
    assert byom.get_effective_budget(is_scribe=False) == 0.90
    assert byom.get_effective_budget(is_scribe=True) == 1.00

def test_byom_budget_exceeded_for_worker():
    byom = BYOMClient(default_model="default", max_budget_usd=0.0001, reserve_percent=10)
    # Exceed limit
    with pytest.raises(BudgetExceededException):
        asyncio.run(
            byom.call("detective", "system", "very long prompt" * 1000, expected_output_tokens=1000)
        )

def test_byom_warning_trigger():
    warnings = []
    def warning_cb(spent, max_b):
        warnings.append((spent, max_b))

    byom = BYOMClient(
        default_model="default",
        max_budget_usd=0.01,
        warning_callback=warning_cb
    )
    # Record usage exceeding 80% ($0.008)
    byom.record_usage("detective", 30_000, 10_000)
    assert len(warnings) == 1
    assert warnings[0][0] >= 0.008

# ==============================================================================
# 3. Worktree & Diff Applier Tests (FR-2, FR-5)
# ==============================================================================

def test_diff_applier_clean():
    original = "def foo():\n    now = datetime.utcnow().timestamp()\n    return now\n"
    diff = """--- a/foo.py
+++ b/foo.py
@@ -2,2 +2,2 @@
-    now = datetime.utcnow().timestamp()
+    now = datetime.now(timezone.utc).timestamp()
     return now
"""
    ok, patched, msg = DiffApplier.apply_patch_to_content(original, diff)
    assert ok is True
    assert "datetime.now(timezone.utc).timestamp()" in patched
    assert "datetime.utcnow().timestamp()" not in patched

def test_scope_guard_violation():
    diff = """--- a/app/secret.py
+++ b/app/secret.py
@@ -1,1 +1,1 @@
-pass
+fail
"""
    with pytest.raises(ScopeGuardViolation):
        DiffApplier.enforce_scope_guard(diff, allowed_files=["app/auth/tokens.py"])

def test_worktree_uncommitted_warning():
    mgr = WorktreeManager("benchmarks/ecommerce_api")
    warning = mgr.get_uncommitted_warning()
    assert "Uncommitted changes" in warning

# ==============================================================================
# 4. Deterministic Preflight Tests (FR-3)
# ==============================================================================

def test_preflight_check():
    pf = PreflightCheck("benchmarks/ecommerce_api")
    ok, report = pf.run_check()
    assert ok is True
    assert report.is_ready is True
    assert report.pytest_available is True
    assert report.python_valid is True

def test_preflight_env_example_parsing():
    pf = PreflightCheck("benchmarks/ecommerce_api")
    env_vars = pf.parse_env_example()
    assert isinstance(env_vars, dict)

# ==============================================================================
# 5. Grounded Fact Memory Tests (FR-4)
# ==============================================================================

def test_memory_store_provisional_and_verified(tmp_path):
    store = MemoryGraphStore(str(tmp_path))
    node = MemoryNode(
        id="decision:test-1",
        node_type="ArchitecturalDecision",
        label="Test rule",
        properties={"file": "foo.py"},
        is_provisional=True,
    )
    store.add_node(node)
    assert len(store.get_advisory_hints()) == 1
    assert len(store.get_verified_rules()) == 1  # 1 baseline fact (cmd:pytest)

    # Manually verify
    store.verify_node("decision:test-1", verified=True)
    assert len(store.get_advisory_hints()) == 0
    assert len(store.get_verified_rules()) == 2

def test_memory_conflict_detection(tmp_path):
    store = MemoryGraphStore(str(tmp_path))
    store.add_node(
        MemoryNode(
            id="veto:test",
            node_type="VetoRecord",
            label="Do not modify order calculation algorithm",
            properties={"file": "app/models/order.py"},
            is_provisional=False,
        )
    )
    conflicts = store.check_conflicts(proposed_files=["app/models/order.py"], proposed_symbols=[])
    assert len(conflicts) > 0
    assert "VETO WARNING" in conflicts[0]

# ==============================================================================
# 6. Sentinel & Critic Tests
# ==============================================================================

def test_sentinel_syntax_and_imports():
    good_code = "import json\nimport sys\ndef hello():\n    return 42\n"
    ok, msg = Sentinel.verify_syntax(good_code)
    assert ok is True

    bad_syntax = "def broken(:"
    ok, msg = Sentinel.verify_syntax(bad_syntax)
    assert ok is False

    invented_import = "import hallucinated_fake_library\n"
    ok_imp, invented = Sentinel.verify_imports(invented_import)
    assert ok_imp is False
    assert "hallucinated_fake_library" in invented

def test_critic_diff_scoring():
    small_diff = """--- a/foo.py
+++ b/foo.py
@@ -1,2 +1,2 @@
-foo
+bar
"""
    report = Critic.evaluate_diff(small_diff)
    assert report.score == 100
    assert report.total_lines_changed == 2

    large_diff = "\n".join(["+added line"] * 50)
    report_large = Critic.evaluate_diff(large_diff)
    assert report_large.score < 100
    assert report_large.penalty > 0

# ==============================================================================
# 7. Cartographer Call Hierarchy Tests
# ==============================================================================

def test_cartographer_ast_and_hierarchy():
    carto = Cartographer("benchmarks/ecommerce_api")
    index = carto.index_repo()
    assert "app/auth/tokens.py" in index["files"]
    assert "is_token_expired" in index["symbol_table"]

    hierarchy = carto.trace_call_hierarchy("is_token_expired")
    assert hierarchy["symbol"] == "is_token_expired"
    # validate_token calls is_token_expired
    callers = [c["caller_symbol"] for c in hierarchy["callers"]]
    assert "validate_token" in callers

# ==============================================================================
# 8. REST API Endpoints Tests
# ==============================================================================

def test_api_status_and_presets():
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["engine_active"] is True
    assert "memory_nodes_count" in data

    res_presets = client.get("/api/presets")
    assert res_presets.status_code == 200
    presets = res_presets.json()
    assert len(presets) >= 1
    assert presets[0]["id"] == "ecommerce_tz_defect"

def test_api_triage_eval():
    res = client.post("/api/triage/eval", json={"description": "Tokens fail in app/auth/tokens.py"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_anchored"] is True

def test_api_memory_and_verify():
    res = client.get("/api/memory")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data

    # Add node
    node_payload = {
        "id": "decision:api_test",
        "node_type": "ArchitecturalDecision",
        "label": "API Test Rule",
        "properties": {"file": "test.py"},
        "is_provisional": True,
    }
    res_add = client.post("/api/memory/node", json=node_payload)
    assert res_add.status_code == 200

    # Verify node
    res_ver = client.post("/api/memory/verify", json={"node_id": "decision:api_test", "verified": True})
    assert res_ver.status_code == 200
    assert res_ver.json()["is_provisional"] is False

def test_custom_endpoint_config_and_test():
    # 1. Fetch available endpoint templates
    res = client.get("/api/config/endpoints")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data
    provider_ids = [p["id"] for p in data["providers"]]
    assert "gemini_openai" in provider_ids
    assert "gemini_native" in provider_ids
    assert "anthropic" in provider_ids
    assert "ollama" in provider_ids

    # 2. Test endpoint connectivity
    test_res = client.post(
        "/api/config/test-endpoint",
        json={
            "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai",
            "model": "gemini-1.5-flash",
            "provider": "openai_compatible",
        }
    )
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert test_data["success"] is True

# ==============================================================================
# 9. Full Orchestration Execution Run on Benchmark
# ==============================================================================

def test_full_orchestrator_benchmark_run():
    async def _run():
        engine_inst = OrchestratorEngine(repo_path="benchmarks/ecommerce_api")
        issue = IssueInput(
            issue_id="benchmark-ecommerce-tz",
            title="Ecommerce API Timezone Expiry Bug",
            description=(
                "In app/auth/tokens.py::is_token_expired(), tokens expire early under non-UTC timezones. "
                "datetime.utcnow().timestamp() uses naive UTC, treating it as local time."
            ),
            repo_path="benchmarks/ecommerce_api",
            use_worktree=True,
            unattended=True,
            max_budget_usd=1.00,
        )
        result = await engine_inst.execute_run(issue)
        assert result["status"] == RunStatus.COMPLETED
        assert result["judge_report"]["regressions_count"] == 0
        assert result["judge_report"]["reproduction_test_passed_after"] is True
        assert result["judge_report"]["veto"] is False
        assert result["critic"]["score"] >= 80
        assert "report" in result
        assert result["cost"]["total_cost_usd"] < 1.00

        # Teardown worktree cleanly
        if "worktree_path" in result:
            engine_inst.worktree_mgr.remove_worktree(result["worktree_path"], result["branch"])

    asyncio.run(_run())
