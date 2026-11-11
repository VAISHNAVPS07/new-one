import time

from tests.conftest import build_deck


def upload(client, path):
    with open(path, "rb") as fh:
        return client.post("/api/jobs", files={"file": (path.name, fh, "application/octet-stream")})


def wait_done(client, job_id, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(0.1)
    raise AssertionError("timeout")


def test_full_phase2_flow(client, deck_path):
    r = upload(client, deck_path)
    assert r.status_code == 201
    job = r.json()
    jid = job["job_id"]
    assert job["status"] == "uploaded"

    v = client.post(f"/api/jobs/{jid}/validate")
    assert v.status_code == 200 and v.json()["status"] == "pass"

    assert client.post(f"/api/jobs/{jid}/start").status_code == 202
    done = wait_done(client, jid)
    assert done["status"] == "completed"
    assert done["stages"]["markdown_conversion"]["status"] == "done"
    assert "## Slide 2: Problem Statement" in client.get(f"/api/jobs/{jid}/markdown").text

    events = [e["event"] for e in client.get(f"/api/jobs/{jid}/audit").json()]
    assert "job_created" in events and "stage_done" in events


def test_start_blocked_on_failed_validation(client, tmp_path):
    jid = upload(client, build_deck(tmp_path / "x.pptx", omit={"problem"})).json()["job_id"]
    assert client.post(f"/api/jobs/{jid}/validate").json()["status"] == "fail"
    assert client.post(f"/api/jobs/{jid}/start").status_code == 409
    assert client.post(f"/api/jobs/{jid}/start?force=true").status_code == 202
    assert wait_done(client, jid)["status"] == "completed"


def test_resume_skips_completed_stages(client, deck_path, settings):
    jid = upload(client, deck_path).json()["job_id"]
    client.post(f"/api/jobs/{jid}/start")
    wait_done(client, jid)
    md = settings.storage_dir / jid / "markdown" / "disclosure.md"
    mtime = md.stat().st_mtime_ns
    client.post(f"/api/jobs/{jid}/start")
    wait_done(client, jid)
    assert md.stat().st_mtime_ns == mtime  # not regenerated


def test_upload_rejections(client, tmp_path):
    bad = tmp_path / "notes.txt"; bad.write_text("hi")
    assert upload(client, bad).status_code == 415
    ppt = tmp_path / "old.ppt"; ppt.write_bytes(b"x")
    assert upload(client, ppt).status_code == 415
    fake = tmp_path / "fake.pptx"; fake.write_text("not a zip")
    assert upload(client, fake).status_code == 400
    corrupt = tmp_path / "corrupt.pptx"; corrupt.write_bytes(b"PK" + b"\x00" * 50)
    jid = upload(client, corrupt).json()["job_id"]
    assert client.post(f"/api/jobs/{jid}/validate").status_code == 422


def test_unknown_and_traversal_job_ids(client):
    assert client.get("/api/jobs/JOB_nope").status_code == 404
    assert client.get("/api/jobs/..%2Fetc").status_code == 404


def test_api_key_enforced(settings, deck_path):
    from fastapi.testclient import TestClient
    from backend.main import create_app
    s = settings.model_copy(update={"api_key": "secret"})
    c = TestClient(create_app(s))
    assert c.get("/api/jobs").status_code == 401
    assert c.get("/api/jobs", headers={"Authorization": "Bearer secret"}).status_code == 200
