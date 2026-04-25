import io

from .conftest import auth_header


def test_bulk_team_csv_import(client):
    admin = auth_header(client, "root")
    # Create a handful of users who will be referenced by the CSV.
    auth_header(client, "alice")
    auth_header(client, "bob")
    auth_header(client, "carol")

    csv_text = (
        "team_name,owner,members\n"  # header, ignored
        "The Apples,alice,bob\n"
        "Solo Act,carol\n"
        "Ghost Team,nobody\n"        # no resolvable members → skipped
        "The Apples,alice\n"         # duplicate team name → skipped
    ).encode()

    r = client.post(
        "/api/admin/teams/import",
        headers=admin,
        files={"file": ("teams.csv", io.BytesIO(csv_text), "text/csv")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["teams_created"] == 2
    assert body["members_added"] == 3  # 2 in Apples + 1 in Solo Act
    # Two skipped rows: unknown user + duplicate name.
    assert any("already exists" in s for s in body["skipped"])
    assert any("nobody" in s or "no resolvable" in s for s in body["skipped"])


def test_one_team_rule(client):
    ha = auth_header(client, "alice")
    hb = auth_header(client, "bob")
    hc = auth_header(client, "carol")

    t = client.post("/api/teams", json={"name": "T1"}, headers=ha).json()
    # Alice cannot create a second team.
    r = client.post("/api/teams", json={"name": "T2"}, headers=ha)
    assert r.status_code == 400

    # Bob can join via code.
    r = client.post("/api/teams/join", json={"join_code": t["join_code"]}, headers=hb)
    assert r.status_code == 200

    # Carol creates T2, Bob cannot then join T2 while already in T1.
    t2 = client.post("/api/teams", json={"name": "T2"}, headers=hc).json()
    r = client.post("/api/teams/join", json={"join_code": t2["join_code"]}, headers=hb)
    assert r.status_code == 400


def test_owner_leaves_promotes_member(client):
    ha = auth_header(client, "alice")
    hb = auth_header(client, "bob")
    t = client.post("/api/teams", json={"name": "T"}, headers=ha).json()
    client.post("/api/teams/join", json={"join_code": t["join_code"]}, headers=hb)

    r = client.delete(f"/api/teams/{t['id']}/leave", headers=ha)
    assert r.status_code == 200

    mine = client.get("/api/teams/my", headers=hb).json()
    assert mine[0]["members"][0]["role"] == "owner"
    assert mine[0]["members"][0]["username"] == "bob"


def test_delete_team_with_join_requests(client):
    ha = auth_header(client, "alice")
    hb = auth_header(client, "bob")
    t = client.post("/api/teams", json={"name": "T"}, headers=ha).json()
    # Bob sends a request; that used to break cascade delete.
    r = client.post(f"/api/teams/{t['id']}/request", json={"message": "hi"}, headers=hb)
    assert r.status_code == 200

    r = client.delete(f"/api/teams/{t['id']}", headers=ha)
    assert r.status_code == 200

    # No orphans.
    assert client.get(f"/api/teams/{t['id']}", headers=ha).status_code == 404
