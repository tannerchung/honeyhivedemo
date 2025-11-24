from data.datasets import load_dataset
from tracing.tracer import Tracer
from utils.exporters import export_to_json


def test_dataset_loads_ground_truth():
    ds = load_dataset("mock")
    assert len(ds) >= 1
    first = ds[0]
    assert "ground_truth" in first
    assert "expected_category" in first["ground_truth"]


def test_tracer_metadata():
    tracer = Tracer()
    tracer.start_trace(ticket_id="1", version="v1", run_id="run123", datapoint_id="dp1", prompt_version="pv1")
    tracer.record_step("dummy", {"a": 1}, {"b": 2}, attributes={"attr": "val"})
    trace = tracer.end_trace()
    assert trace["run_id"] == "run123"
    assert trace["datapoint_id"] == "dp1"
    assert trace["prompt_version"] == "pv1"
    assert trace["steps"][0]["attributes"]["attr"] == "val"


def test_export_uses_metadata(tmp_path):
    results = [
        {
            "run_id": "run123",
            "dataset": "mock",
            "prompt_version": "v1",
            "output": {},
            "evaluations": {"composite": {"passed": True}},
        }
    ]
    out_file = tmp_path / "out.json"
    payload = export_to_json(results, filename=str(out_file))
    assert payload["run_id"] == "run123"
    assert payload["dataset"] == "mock"
    assert payload["summary"]["total"] == 1
