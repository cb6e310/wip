#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np


# The loader is kept under the source data namespace; make the test runnable
# both from unittest discovery and directly from the repository root.
SOURCE_DATA = Path(__file__).resolve().parents[1] / "src" / "data"
sys.path.insert(0, str(SOURCE_DATA))
import zuco2_loader as loader  # noqa: E402

SCRIPT_DATA = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DATA))
import audit_zuco2_data as audit  # noqa: E402


class ZuCoLoaderContractTest(unittest.TestCase):
    def test_task_specs_are_explicit(self):
        self.assertEqual(set(loader.TASKS), {"task1_nr", "task2_tsr"})
        self.assertEqual(loader.TASKS["task1_nr"]["raw_glob"], "*_NR_EEG.mat")
        self.assertEqual(loader.TASKS["task2_tsr"]["raw_glob"], "*_TSR_EEG.mat")
        self.assertEqual(loader.TASKS["task1_nr"]["material_glob"], "nr_[1-7].csv")
        self.assertEqual(loader.TASKS["task2_tsr"]["material_glob"], "tsr_[1-7].csv")

    def test_material_rows_preserve_source_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "task_materials").mkdir()
            (root / "task_materials" / "nr_1.csv").write_text(
                "1;2;A sentence;LABEL\n", encoding="utf-8"
            )
            rows = loader.read_material_rows(root, "task1_nr")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].source_columns, ("1", "2", "A sentence", "LABEL"))

    def test_control_question_files_are_not_mixed_with_materials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "task_materials").mkdir()
            (root / "task_materials" / "nr_1.csv").write_text(
                "1;2;A sentence;\n", encoding="utf-8"
            )
            (root / "task_materials" / "nr_1_control_questions.csv").write_text(
                "paragraph_id;sentence_id;control_question;answer1;answer2;answer3;correct_answer\n",
                encoding="utf-8",
            )
            rows = loader.read_material_rows(root, "task1_nr")
            self.assertEqual([row.source_file for row in rows], ["nr_1.csv"])

    def test_matlab_reference_decode_and_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.mat"
            with h5py.File(path, "w") as handle:
                refs = handle.create_group("#refs#")
                text = refs.create_dataset("text", data=np.asarray([65, 66], dtype="uint16"))
                signal = refs.create_dataset("signal", data=np.zeros((3, 105), dtype="float32"))
                sentence = handle.create_group("sentenceData")
                content = sentence.create_dataset("content", shape=(1, 1), dtype=h5py.ref_dtype)
                raw = sentence.create_dataset("rawData", shape=(1, 1), dtype=h5py.ref_dtype)
                content[0, 0] = text.ref
                raw[0, 0] = signal.ref
            with h5py.File(path, "r") as handle:
                value = loader.sentence_value(handle, "content", 0)
                self.assertEqual(loader.decode_matlab_string(handle, value), "AB")
                self.assertEqual(
                    loader.dataset_shape(handle, loader.sentence_value(handle, "rawData", 0)),
                    (3, 105),
                )
                self.assertEqual(
                    loader.numeric_eeg_reference_status(
                        handle, loader.sentence_value(handle, "rawData", 0)
                    ),
                    (True, "valid"),
                )
                record = loader.summary_record(handle, 0)
                self.assertIsInstance(record["word_reference"], type(None))

    def test_indexed_value_supports_row_and_column_vectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vectors.mat"
            with h5py.File(path, "w") as handle:
                row = handle.create_dataset("row", shape=(1, 2), dtype=h5py.ref_dtype)
                col = handle.create_dataset("col", shape=(2, 1), dtype=h5py.ref_dtype)
                a = handle.create_dataset("a", data=np.asarray([1], dtype="uint8"))
                b = handle.create_dataset("b", data=np.asarray([2], dtype="uint8"))
                row[0, 0], row[0, 1] = a.ref, b.ref
                col[0, 0], col[1, 0] = a.ref, b.ref
                self.assertEqual(loader.dereference(handle, loader.indexed_value(row, 1)).name, "/b")
                self.assertEqual(loader.dereference(handle, loader.indexed_value(col, 1)).name, "/b")

    def test_no_implicit_channel_mapping_api(self):
        self.assertFalse(hasattr(loader, "map_channels"))
        self.assertFalse(hasattr(loader, "compute_bandpower"))

    def test_deep_audit_preserves_all_sentence_and_fixation_layers(self):
        """A malformed counter must not truncate the remainder of a file."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "resultsTST_NR.mat"
            with h5py.File(path, "w") as handle:
                refs = handle.create_group("#refs#")
                sentence = handle.create_group("sentenceData")
                content = sentence.create_dataset("content", shape=(2, 1), dtype=h5py.ref_dtype)
                raw_data = sentence.create_dataset("rawData", shape=(2, 1), dtype=h5py.ref_dtype)
                words = sentence.create_dataset("word", shape=(2, 1), dtype=h5py.ref_dtype)
                for index, code in enumerate((65, 66)):
                    text = refs.create_dataset(f"text{index}", data=np.asarray([code], dtype="uint16"))
                    signal = refs.create_dataset(f"signal{index}", data=np.zeros((4, 105), dtype="float32"))
                    container = refs.create_dataset(f"container{index}", shape=(1, 1), dtype=h5py.ref_dtype)
                    container[0, 0] = signal.ref
                    group = refs.create_group(f"word{index}")
                    word_content = group.create_dataset("content", shape=(1, 1), dtype=h5py.ref_dtype)
                    word_eeg = group.create_dataset("rawEEG", shape=(1, 1), dtype=h5py.ref_dtype)
                    word_content[0, 0] = text.ref
                    word_eeg[0, 0] = container.ref
                    content[index, 0] = text.ref
                    raw_data[index, 0] = signal.ref
                    words[index, 0] = group.ref
            result = audit.audit_summary(path, "task1_nr", "TST", deep=True)
            self.assertEqual(result["status"], "PASS", result.get("error"))
            self.assertEqual(result["sentence_count"], 2)
            self.assertEqual(result["sentence_rawdata_valid"], 2)
            self.assertEqual(result["word_slots"], 2)
            self.assertEqual(result["word_group_valid"], 2)
            self.assertEqual(result["word_raw_eeg_fixation_valid"], 2)


if __name__ == "__main__":
    unittest.main()
