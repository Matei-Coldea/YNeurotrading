"""Tests for the FastAPI application with mocked TRIBE model."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from tribe_neural.constants import NUM_VERTICES
from tribe_neural.init_resources import Resources


def _make_mock_resources() -> Resources:
    """Create Resources with a mock TRIBE model."""
    mock_model = MagicMock()
    # Model returns 15 TRs of random cortical predictions
    rng = np.random.default_rng(42)
    mock_preds = rng.standard_normal((15, NUM_VERTICES)).astype(np.float32)
    mock_model.get_events_dataframe.return_value = MagicMock()
    mock_model.predict.return_value = (mock_preds, None)

    # Simple masks: each ROI gets a chunk of vertices
    masks = {}
    rois = [
        "fear_salience", "reward_limbic", "deliberation",
        "social_default", "action_motor", "attention",
    ]
    chunk = NUM_VERTICES // len(rois)
    for i, name in enumerate(rois):
        mask = np.zeros(NUM_VERTICES, dtype=bool)
        mask[i * chunk : (i + 1) * chunk] = True
        masks[name] = mask

    # Uniform weights
    weight_maps = {
        term: np.ones(NUM_VERTICES, dtype=np.float32)
        for term in ["fear", "reward", "conflict", "social", "uncertainty", "motor"]
    }

    return Resources(
        model=mock_model,
        masks=masks,
        weight_maps=weight_maps,
        signatures={"vifs": None, "pines": None},
    )


@pytest.fixture
def client():
    """Create a TestClient with mocked resources (no real model loading)."""
    with patch("tribe_neural.api.load_resources", return_value=_make_mock_resources()):
        from tribe_neural.api import app
        with TestClient(app) as c:
            yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "gpu_available" in data


class TestProcessEndpoint:
    def test_valid_request(self, client):
        resp = client.post(
            "/process",
            json={"text": "You are listening to the news. The reporter says: "
                          "Fed announces emergency 75 basis point rate hike."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        assert "processing_time_ms" in data
        assert "[Neural state reading for this moment]" in data["result"]
        assert "Dominant response:" in data["result"]

    def test_empty_text_rejected(self, client):
        resp = client.post("/process", json={"text": ""})
        assert resp.status_code == 422

    def test_too_short_text_rejected(self, client):
        resp = client.post("/process", json={"text": "short"})
        assert resp.status_code == 422

    def test_too_long_text_rejected(self, client):
        resp = client.post("/process", json={"text": "x" * 10_001})
        assert resp.status_code == 422

    def test_missing_text_field(self, client):
        resp = client.post("/process", json={})
        assert resp.status_code == 422

    def test_result_contains_composites(self, client):
        resp = client.post(
            "/process",
            json={"text": "The market is crashing. Investors are panicking about the recession."},
        )
        assert resp.status_code == 200
        result = resp.json()["result"]
        assert "valence:" in result
        assert "arousal:" in result
        assert "dominance:" in result
        assert "approach or avoid:" in result
