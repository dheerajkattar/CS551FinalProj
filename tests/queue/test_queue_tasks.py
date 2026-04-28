import importlib
import json
from pathlib import Path

import pandas as pd
import pytest


MODULE_NAME = "Applications.QUEUE_APP.tasks"


@pytest.fixture
def tasks_module(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("results").mkdir(exist_ok=True)
    return importlib.import_module(MODULE_NAME)


@pytest.mark.unit
@pytest.mark.asyncmock
def test_process_csv_etl_success(tasks_module):
    input_file = Path("input.csv")
    input_file.write_text(
        "id,name,value\n1,A,10\n1,A,10\n2,B,\n3,,30\n",
        encoding="utf-8",
    )

    result = tasks_module.process_csv_etl.run(str(input_file), "job-ok")

    output_csv = Path("results/job-ok_output.csv")
    result_json = Path("results/job-ok_result.json")

    assert output_csv.exists()
    assert result_json.exists()
    assert result["job_id"] == "job-ok"
    assert result["original_rows"] == 4
    assert result["processed_rows"] == 3
    assert result["duplicate_rows_removed"] == 1
    assert "processed_at" in result["columns"]
    assert "value_normalized" in result["columns"]
    assert not input_file.exists()

    processed_df = pd.read_csv(output_csv)
    assert "value_normalized" in processed_df.columns
    assert processed_df["name"].isnull().sum() == 0


@pytest.mark.unit
@pytest.mark.asyncmock
def test_process_csv_etl_error_path_writes_error_and_cleans_file(tasks_module, monkeypatch):
    input_file = Path("bad.csv")
    input_file.write_text("anything", encoding="utf-8")

    def raise_read_error(_):
        raise ValueError("invalid csv format")

    monkeypatch.setattr(tasks_module.pd, "read_csv", raise_read_error)

    with pytest.raises(ValueError, match="invalid csv format"):
        tasks_module.process_csv_etl.run(str(input_file), "job-fail")

    error_file = Path("results/job-fail_error.json")
    assert error_file.exists()
    error_payload = json.loads(error_file.read_text(encoding="utf-8"))
    assert error_payload["error_type"] == "ValueError"
    assert not input_file.exists()
