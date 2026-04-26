"""Smoke tests for the learning zone endpoints. Covers the contract,
not the rendering — the React markdown pipeline is exercised by the
frontend's own tests."""
from .conftest import auth_header


def _section_payload(slug="bases", title="Bases"):
    return {
        "slug": slug,
        "title_fr": title, "title_en": title,
        "description_fr": "fr desc", "description_en": "en desc",
        "order_idx": 0, "is_published": True,
    }


def _lesson_payload(slug="hello", title="Hello"):
    return {
        "slug": slug,
        "title_fr": title, "title_en": title,
        "content_fr": "# Salut", "content_en": "# Hello",
        "order_idx": 0, "is_published": True,
    }


def test_admin_only_writes(client):
    auth_header(client, "root")  # bootstrap admin
    alice = auth_header(client, "alice")
    r = client.post("/api/admin/learning/sections", json=_section_payload(), headers=alice)
    assert r.status_code in (401, 403)


def test_section_lesson_lifecycle(client):
    admin = auth_header(client, "root")

    # Create section
    r = client.post("/api/admin/learning/sections", json=_section_payload(), headers=admin)
    assert r.status_code == 200, r.text
    sid = r.json()["id"]

    # Listing as admin includes the section.
    r = client.get("/api/admin/learning/sections", headers=admin)
    assert any(s["id"] == sid for s in r.json())

    # Slug collision rejected.
    r = client.post("/api/admin/learning/sections", json=_section_payload(), headers=admin)
    assert r.status_code == 409

    # Add a lesson.
    r = client.post(
        f"/api/admin/learning/sections/{sid}/lessons",
        json=_lesson_payload(), headers=admin,
    )
    assert r.status_code == 200, r.text
    lid = r.json()["id"]

    # Student sees the published section + lesson.
    student = auth_header(client, "alice")
    r = client.get("/api/learning/sections", headers=student)
    secs = r.json()
    assert any(s["id"] == sid for s in secs)

    r = client.get("/api/learning/sections/bases/lessons", headers=student)
    assert any(l["id"] == lid for l in r.json())

    # Read the lesson body — should auto-create progress="started".
    r = client.get(f"/api/learning/lessons/{lid}", headers=student)
    assert r.status_code == 200
    body = r.json()
    assert body["content_fr"] == "# Salut"
    assert body["progress_status"] == "started"

    # Mark completed.
    r = client.put(
        f"/api/learning/lessons/{lid}/progress",
        json={"status": "completed"}, headers=student,
    )
    assert r.status_code == 200
    assert r.json()["progress_status"] == "completed"

    # Section listing shows the completed counter incremented.
    r = client.get("/api/learning/sections", headers=student)
    sec = next(s for s in r.json() if s["id"] == sid)
    assert sec["completed_count"] == 1
    assert sec["lesson_count"] == 1


def test_unpublished_section_hidden_from_students(client):
    admin = auth_header(client, "root")
    payload = _section_payload(slug="hidden", title="Hidden")
    payload["is_published"] = False
    r = client.post("/api/admin/learning/sections", json=payload, headers=admin)
    assert r.status_code == 200

    alice = auth_header(client, "alice")
    r = client.get("/api/learning/sections", headers=alice)
    assert all(s["slug"] != "hidden" for s in r.json())

    r = client.get("/api/learning/sections/hidden/lessons", headers=alice)
    assert r.status_code == 404


def test_unpublished_lesson_hidden_from_students(client):
    admin = auth_header(client, "root")
    sid = client.post(
        "/api/admin/learning/sections",
        json=_section_payload(), headers=admin,
    ).json()["id"]
    payload = _lesson_payload(slug="draft", title="Draft")
    payload["is_published"] = False
    lid = client.post(
        f"/api/admin/learning/sections/{sid}/lessons",
        json=payload, headers=admin,
    ).json()["id"]

    alice = auth_header(client, "alice")
    r = client.get("/api/learning/sections/bases/lessons", headers=alice)
    assert all(l["id"] != lid for l in r.json())

    # Direct fetch by id 404s for non-admins on a draft.
    r = client.get(f"/api/learning/lessons/{lid}", headers=alice)
    assert r.status_code == 404

    # But the admin can read it for preview purposes.
    r = client.get(f"/api/learning/lessons/{lid}", headers=admin)
    assert r.status_code == 200
    assert r.json()["title_fr"] == "Draft"


def test_invalid_slug_rejected(client):
    admin = auth_header(client, "root")
    payload = _section_payload(slug="Bad Slug With Spaces!")
    r = client.post("/api/admin/learning/sections", json=payload, headers=admin)
    assert r.status_code == 422  # Pydantic validation
