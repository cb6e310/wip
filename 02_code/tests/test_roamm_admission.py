from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_code" / "src"))

from data.roamm_admission import (  # noqa: E402
    EXPECTED_SINGLE_PAGE,
    STORIES,
    audit_coordinates,
    build_subject_run_inventory,
    canonical_json_bytes,
    canonical_yaml_text,
    compute_support,
    construct_primary_records,
    manifest_hash,
    normalize_item,
    parse_raw_bdf_path,
    parse_synced_path,
    structural_n50,
)


def coordinate_rows() -> dict[str, list[dict[str, object]]]:
    rows = {story: [] for story in STORIES}
    rows["history_of_film"] = [
        {
            "words": "Alpha",
            "word_key": "key-a",
            "sentence_id": "history_of_film_0",
            "sentence": "Alpha beta.",
            "page": 0,
        },
        {
            "words": "beta",
            "word_key": "key-b",
            "sentence_id": "history_of_film_0",
            "sentence": "Alpha beta.",
            "page": 1,
        },
        {
            "words": "Gamma",
            "word_key": "key-c",
            "sentence_id": "history_of_film_1",
            "sentence": "Gamma.",
            "page": 1,
        },
    ]
    for story in STORIES[1:]:
        rows[story] = [
            {
                "words": story,
                "word_key": f"key-{story}",
                "sentence_id": f"{story}_0",
                "sentence": f"{story} text.",
                "page": 0,
            }
        ]
    return rows


def event(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "subject": "sub-10014",
        "run": 1,
        "story": "history_of_film",
        "page": 2,
        "first_pass_reading": True,
        "is_fix": True,
        "finite_eeg": True,
        "fix_start": 1.0,
        "fix_end": 1.2,
        "word_key": "key-c",
        "is_mw": False,
    }
    value.update(updates)
    return value


class RoammAdmissionTests(unittest.TestCase):
    def test_exact_subject_run_filenames(self) -> None:
        self.assertEqual(
            parse_synced_path(
                "derivatives/synced/sub-10014/"
                "sub-10014_task-ReMind_run-01_mldata.pkl"
            ),
            ("10014", 1),
        )
        self.assertEqual(
            parse_raw_bdf_path("derivatives/raw_data/s10014/eeg/MR_s10014_r5.bdf"),
            ("10014", 5),
        )
        with self.assertRaises(ValueError):
            parse_synced_path(
                "derivatives/synced/sub-10014/"
                "sub-10015_task-ReMind_run-01_mldata.pkl"
            )

    def test_inventory_reports_missing_and_duplicate_runs(self) -> None:
        entries = [
            {
                "filename": "derivatives/raw_data/s10014/eeg/MR_s10014_r1.bdf",
                "id": "SHA256E-s1--" + "a" * 64 + ".bdf",
                "size": 1,
                "annexed": True,
                "directory": False,
            },
            {
                "filename": (
                    "derivatives/synced/sub-10014/"
                    "sub-10014_task-ReMind_run-01_mldata.pkl"
                ),
                "id": "SHA256E-s2--" + "b" * 64 + ".pkl",
                "size": 2,
                "annexed": True,
                "directory": False,
            },
        ]
        report = build_subject_run_inventory(["sub-10014"], entries)
        self.assertEqual(report["expected_cells"], 5)
        self.assertTrue(any("run-2" in value for value in report["hard_failures"]))
        duplicate = entries + [dict(entries[0], filename=entries[0]["filename"])]
        with self.assertRaises(ValueError):
            build_subject_run_inventory(["sub-10014"], duplicate)

    def test_duplicate_and_empty_word_keys_hard_fail(self) -> None:
        rows = coordinate_rows()
        rows["pluto"][0]["word_key"] = ""
        with self.assertRaisesRegex(ValueError, "empty word_key"):
            audit_coordinates(rows)
        rows = coordinate_rows()
        rows["pluto"][0]["word_key"] = "key-a"
        with self.assertRaisesRegex(ValueError, "duplicate word_key"):
            audit_coordinates(rows)

    def test_sentence_id_cannot_map_to_multiple_texts(self) -> None:
        rows = coordinate_rows()
        rows["history_of_film"][1]["sentence"] = "Different text."
        with self.assertRaisesRegex(ValueError, "multiple texts"):
            audit_coordinates(rows)

    def test_cross_page_sentences_are_separated(self) -> None:
        report, _ = audit_coordinates(coordinate_rows())
        self.assertEqual(report["cross_page_sentence_ids"], ["history_of_film_0"])
        self.assertIn("history_of_film_1", report["single_page_sentence_ids"])

    def test_unknown_fixation_key_enters_failure_ledger_only(self) -> None:
        _, index = audit_coordinates(coordinate_rows())
        result = construct_primary_records(
            [event(word_key="unknown")],
            index,
            allowed_subjects={"sub-10014"},
            allowed_stories={"history_of_film"},
            page_offset=1,
        )
        self.assertEqual(result["primary"]["trials"], [])
        self.assertEqual(result["failure_ledger"][0]["reason"], "unknown_word_key")

    def test_story_and_page_identity_are_exact(self) -> None:
        _, index = audit_coordinates(coordinate_rows())
        story = construct_primary_records(
            [event(story="pluto")],
            index,
            allowed_subjects={"sub-10014"},
            allowed_stories=set(STORIES),
            page_offset=1,
        )
        self.assertEqual(story["failure_ledger"][0]["reason"], "story_mismatch")
        page = construct_primary_records(
            [event(page=1)],
            index,
            allowed_subjects={"sub-10014"},
            allowed_stories={"history_of_film"},
            page_offset=1,
        )
        self.assertEqual(page["failure_ledger"][0]["reason"], "page_mismatch")

    def test_first_pass_is_a_primary_inclusion_rule(self) -> None:
        _, index = audit_coordinates(coordinate_rows())
        result = construct_primary_records(
            [event(first_pass_reading=False), event(fix_start=2.0)],
            index,
            allowed_subjects={"sub-10014"},
            allowed_stories={"history_of_film"},
            page_offset=1,
        )
        self.assertEqual(len(result["primary"]["trials"]), 1)

    def test_is_mw_flip_leaves_primary_bytes_identical(self) -> None:
        _, index = audit_coordinates(coordinate_rows())
        original = [event(), event(fix_start=2.0, fix_end=2.2, is_mw=False)]
        flipped = [dict(row, is_mw=not bool(row["is_mw"])) for row in original]
        kwargs = {
            "allowed_subjects": {"sub-10014"},
            "allowed_stories": {"history_of_film"},
            "page_offset": 1,
        }
        left = construct_primary_records(original, index, **kwargs)
        right = construct_primary_records(flipped, index, **kwargs)
        self.assertEqual(
            canonical_json_bytes(left["primary"]), canonical_json_bytes(right["primary"])
        )
        self.assertNotEqual(left["mw_diagnostic_counts"], right["mw_diagnostic_counts"])

    def test_fixation_event_deduplication_uses_full_event_key(self) -> None:
        _, index = audit_coordinates(coordinate_rows())
        events = [event(), event(), event(fix_start=2.0, fix_end=2.2)]
        result = construct_primary_records(
            events,
            index,
            allowed_subjects={"sub-10014"},
            allowed_stories={"history_of_film"},
            page_offset=1,
        )
        self.assertEqual(result["deduplicated_event_count"], 2)
        self.assertEqual(result["primary"]["support"]["unique_trial_item_observations"], 1)

    def test_trial_item_contributes_at_most_one_support_observation(self) -> None:
        rows = [
            {
                "trial_id": "t1",
                "item_id": "i1",
                "subject": "s1",
                "story": "pluto",
            },
            {
                "trial_id": "t1",
                "item_id": "i1",
                "subject": "s1",
                "story": "pluto",
            },
        ]
        result = compute_support(
            rows, allowed_subjects={"s1"}, allowed_stories={"pluto"}
        )
        self.assertEqual(result["unique_trial_item_observations"], 1)
        self.assertEqual(result["items"][0]["n_obs"], 1)

    def test_support_gate_requires_observations_and_subjects(self) -> None:
        rows = []
        for index in range(20):
            rows.append(
                {
                    "trial_id": f"s{index % 5}|t{index}",
                    "item_id": "item-pass",
                    "subject": f"s{index % 5}",
                    "story": "pluto",
                }
            )
            rows.append(
                {
                    "trial_id": f"s0|x{index}",
                    "item_id": "item-one-subject",
                    "subject": "s0",
                    "story": "pluto",
                }
            )
        result = compute_support(
            rows,
            allowed_subjects={f"s{index}" for index in range(5)},
            allowed_stories={"pluto"},
        )
        lookup = {row["item_id"]: row for row in result["items"]}
        self.assertTrue(lookup["item-pass"]["supported"])
        self.assertFalse(lookup["item-one-subject"]["supported"])

    def test_outer_train_selector_never_reads_outer_test(self) -> None:
        base = [
            {"trial_id": "train", "item_id": "i", "subject": "s1", "story": "pluto"}
        ]
        test = {
            "trial_id": "test",
            "item_id": "i",
            "subject": "s-test",
            "story": "serena_williams",
        }
        kwargs = {"allowed_subjects": {"s1"}, "allowed_stories": {"pluto"}}
        self.assertEqual(compute_support(base, **kwargs), compute_support(base + [test], **kwargs))

    def test_item_normalization_is_nfkc_casefold_without_stemming(self) -> None:
        self.assertEqual(normalize_item("  CAFE\u0301s  ")[0], "roamm|remind|caf\u00e9s")
        self.assertEqual(normalize_item("123")[1], "no_unicode_letter")
        self.assertEqual(normalize_item("!!!")[1], "no_unicode_letter")

    def test_structural_n50_is_only_an_upper_bound(self) -> None:
        report = {
            "single_page_per_story": EXPECTED_SINGLE_PAGE,
            "single_page_sentence_ids": [
                f"{story}_{index}"
                for story, count in EXPECTED_SINGLE_PAGE.items()
                for index in range(count)
            ],
        }
        result = structural_n50(report, {"pluto_0"})
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["full_n50_feasibility"], "DELEGATED_TO_S0_CANDIDATES")
        pluto = next(row for row in result["stories"] if row["story"] == "pluto")
        self.assertEqual(pluto["structural_negative_upper_bound"], 87)
        self.assertEqual(pluto["supported_sentence_count"], 1)

    def test_json_yaml_and_manifest_are_deterministic(self) -> None:
        left = {"b": [2, 1], "a": {"x": True}}
        right = copy.deepcopy(left)
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))
        self.assertEqual(canonical_yaml_text(left), canonical_yaml_text(right))
        self.assertEqual(manifest_hash(left), manifest_hash(right))
        self.assertEqual(len(manifest_hash(left)), 64)


if __name__ == "__main__":
    unittest.main()
