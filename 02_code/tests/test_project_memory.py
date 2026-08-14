from __future__ import annotations

import copy
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if not (PROJECT_ROOT / "scripts").exists():
    # Keep the fixture runnable when this test is copied beside scripts/ locally.
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "check_project_state.py"
SPEC = importlib.util.spec_from_file_location("check_project_state", SCRIPT_PATH)
CHECKER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)


class ProjectMemoryValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        for directory in ("guide", "runs", "artifacts", "03_runs/debug_runs/smoke_001"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "PROJECT_STATE.yaml", self.root / "PROJECT_STATE.yaml")
        shutil.copy2(PROJECT_ROOT / "TASKS.yaml", self.root / "TASKS.yaml")
        state = yaml.safe_load((self.root / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        tasks = yaml.safe_load((self.root / "TASKS.yaml").read_text(encoding="utf-8"))
        spec_path = self.root / state["project"]["spec_path"]
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("fixture spec\n", encoding="utf-8")
        last_run = self.root / state["last_run"]
        last_run.parent.mkdir(parents=True, exist_ok=True)
        last_run.write_text("fixture run\n", encoding="utf-8")
        # The fixture follows the copied task graph, including newly completed
        # tasks, instead of hard-coding a stale list of legacy smoke artifacts.
        for task in tasks.values():
            if not isinstance(task, dict) or task.get("status") != "DONE":
                continue
            for artifact in task.get("produces", []):
                artifact_path = self.root / artifact
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.write_text("fixture evidence\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _read(self, filename: str):
        return yaml.safe_load((self.root / filename).read_text(encoding="utf-8"))

    def _write(self, filename: str, value) -> None:
        (self.root / filename).write_text(
            yaml.safe_dump(value, sort_keys=False), encoding="utf-8"
        )

    def test_initial_state_is_valid(self) -> None:
        self.assertEqual(CHECKER.validate(self.root), [])

    def test_illegal_status_is_rejected(self) -> None:
        tasks = self._read("TASKS.yaml")
        tasks["S0_H_DEFINITION"]["status"] = "almost done"
        self._write("TASKS.yaml", tasks)
        errors = CHECKER.validate(self.root)
        self.assertTrue(any("illegal status" in error for error in errors))

    def test_done_requires_existing_artifact(self) -> None:
        tasks = self._read("TASKS.yaml")
        tasks["S0_H_DEFINITION"].update(
            status="DONE", completed_by_run="fixture", produces=["artifacts/not-there.md"]
        )
        self._write("TASKS.yaml", tasks)
        errors = CHECKER.validate(self.root)
        self.assertTrue(any("missing DONE artifact" in error for error in errors))

    def test_gate_b_cannot_start_before_gate_a_pass(self) -> None:
        state = self._read("PROJECT_STATE.yaml")
        tasks = self._read("TASKS.yaml")
        state["gates"]["gate_b"]["status"] = "IN_PROGRESS"
        tasks["GATE_B"]["status"] = "IN_PROGRESS"
        self._write("PROJECT_STATE.yaml", state)
        self._write("TASKS.yaml", tasks)
        errors = CHECKER.validate(self.root)
        self.assertTrue(any("GATE_B may start only" in error for error in errors))

    def test_main_experiment_cannot_bypass_route_lock(self) -> None:
        state = self._read("PROJECT_STATE.yaml")
        tasks = self._read("TASKS.yaml")
        state["route"]["locked"] = "EQ-ANMA"
        state["route"]["locked_by_run"] = "fixture"
        tasks["MAIN_EXPERIMENT"]["status"] = "IN_PROGRESS"
        self._write("PROJECT_STATE.yaml", state)
        self._write("TASKS.yaml", tasks)
        errors = CHECKER.validate(self.root)
        self.assertTrue(any("ROUTE_LOCK is DONE" in error for error in errors))

    def test_blocked_requires_reason(self) -> None:
        tasks = self._read("TASKS.yaml")
        tasks["S0_H_DEFINITION"]["status"] = "BLOCKED"
        tasks["S0_H_DEFINITION"].pop("blocked_reason", None)
        self._write("TASKS.yaml", tasks)
        errors = CHECKER.validate(self.root)
        self.assertTrue(any("BLOCKED requires blocked_reason" in error for error in errors))

    def test_ready_task_cannot_be_named_by_active_blocker(self) -> None:
        state = self._read("PROJECT_STATE.yaml")
        tasks = self._read("TASKS.yaml")
        tasks["S0_H_DEFINITION"]["status"] = "READY"
        state["blockers"].append(
            {
                "id": "B_FIXTURE",
                "reason": "fixture blocker",
                "blocks": ["S0_H_DEFINITION"],
                "resolution": "remove fixture blocker",
            }
        )
        self._write("PROJECT_STATE.yaml", state)
        self._write("TASKS.yaml", tasks)
        errors = CHECKER.validate(self.root)
        self.assertTrue(any("READY task is named" in error for error in errors))

    def test_unknown_prerequisite_is_reported_without_crashing(self) -> None:
        tasks = self._read("TASKS.yaml")
        tasks["S0_H_DEFINITION"]["prerequisites"] = ["DOES_NOT_EXIST"]
        self._write("TASKS.yaml", tasks)
        errors = CHECKER.validate(self.root)
        self.assertTrue(any("unknown prerequisite" in error for error in errors))

    def test_stale_project_directory_is_rejected(self) -> None:
        state = self._read("PROJECT_STATE.yaml")
        state["project"]["server_root"] = "/home/song/projects/trust_algin"
        self._write("PROJECT_STATE.yaml", state)
        errors = CHECKER.validate(self.root)
        self.assertTrue(any("stale project directory" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
