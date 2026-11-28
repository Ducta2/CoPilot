"""A failing answer hook (#1305) must not empty the comment the SOC just wrote.

``mark_answered_by_comment`` runs on the request's own session, after the comment is committed.
When its UPDATE failed it used to roll that session back, and SQLAlchemy expires every object
on rollback: both comment routes then answered ``200 {"comment": {}}``. Here the UPDATE itself
is made to fail, and both routes must still return the comment's text; the question stays open.

Run with: cd backend && python -m pytest tests/test_soc_request_answer_hook_rollback.py
"""

from unittest.mock import patch

from sqlalchemy import text

from app.db.universal_models import CustomerPortalSocRequest
from tests.test_customer_portal_soc_requests import BASE
from tests.test_customer_portal_soc_requests import as_user
from tests.test_customer_portal_soc_requests import ask
from tests.test_customer_portal_soc_requests import call
from tests.test_customer_portal_soc_requests import rows


class _BrokenUpdate:
    """Stands in for ``update(...)``: the statement it builds fails in the database."""

    def where(self, *args, **kwargs):
        return self

    def values(self, *args, **kwargs):
        return text("UPDATE no_such_table SET x = 1")


def test_a_failing_answer_update_still_returns_the_comment_on_both_routes():
    async def scenario(client, rec):
        await ask(client, "case", rec.ids["open_case"])
        await ask(client, "alert", rec.ids["lonely"], target="alert")
        with patch("app.customer_portal.services.soc_request_answers.update", lambda *_: _BrokenUpdate()):
            on_case = await client.post(
                "/incidents/db_operations/case/comment",
                json={"case_id": rec.ids["open_case"], "comment": "Answer on the case", "user_name": "x"},
                headers=as_user("ana"),
            )
            on_alert = await client.post(
                "/incidents/db_operations/alert/comment",
                json={"alert_id": rec.ids["lonely"], "comment": "Answer on the alert", "user_name": "x"},
                headers=as_user("ana"),
            )
        questions = await rows(rec.db, CustomerPortalSocRequest)
        case_view = (await client.get(f"{BASE}/case/{rec.ids['open_case']}", headers=as_user("jane"))).json()["requests"]
        return on_case, on_alert, questions, case_view

    on_case, on_alert, questions, case_view = call(scenario)
    assert on_case.status_code == 200, on_case.text
    assert on_alert.status_code == 200, on_alert.text
    assert on_case.json()["comment"]["comment"] == "Answer on the case"
    assert on_alert.json()["comment"]["comment"] == "Answer on the alert"
    assert sorted(q.status for q in questions) == ["open", "open"]
    assert [r["status"] for r in case_view] == ["open"]
