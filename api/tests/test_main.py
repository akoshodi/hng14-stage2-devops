import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_redis():
    with patch("main.r") as mock_r:
        mock_r.ping.return_value = True
        mock_r.lpush.return_value = 1
        mock_r.hset.return_value = 1
        yield mock_r


@pytest.fixture
def client(mock_redis):
    from main import app
    return TestClient(app)


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"message": "API is running"}


def test_health_ok(client, mock_redis):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_health_redis_down(mock_redis):
    mock_redis.ping.side_effect = Exception("Connection refused")
    from main import app
    test_client = TestClient(app, raise_server_exceptions=False)
    res = test_client.get("/health")
    assert res.status_code == 503


def test_create_job(client, mock_redis):
    res = client.post("/jobs")
    assert res.status_code == 201
    data = res.json()
    assert "job_id" in data
    mock_redis.lpush.assert_called_once()
    mock_redis.hset.assert_called_once()


def test_get_job_found(client, mock_redis):
    mock_redis.hget.return_value = b"queued"
    res = client.get("/jobs/some-job-id")
    assert res.status_code == 200
    assert res.json()["status"] == "queued"


def test_get_job_not_found(client, mock_redis):
    mock_redis.hget.return_value = None
    res = client.get("/jobs/missing-id")
    assert res.status_code == 404
