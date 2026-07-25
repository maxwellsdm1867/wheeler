"""Regression test for issue #86: failed theorizer task surfaces error reason.

Issue: When an Asta theorizer run fails server-side (status.state != "completed"),
the returned artifact has state=failed but no error reason is surfaced to the user.
The error reason extracted by job_outcome should be captured in the ImportReport
and surfaced in the CLI output.

This test verifies that when a theorizer task fails:
1. The Execution node is created with status="failed"
2. The failure reason from the job status is captured and stored on the report
3. The error reason can be accessed by the CLI to surface it to the user
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from wheeler.config import WheelerConfig, load_config
from wheeler.integrations.asta.theorizer import ingest_theorizer
from wheeler.integrations.asta._marshal import job_outcome, JobOutcome, ImportReport


class TestTheorizerFailureReasonCapture:
    """Verify that failed theorizer tasks surface their error reason."""

    def test_job_outcome_extracts_message_when_present(self):
        """job_outcome should extract status.message when present and use it as detail."""
        failed_task = {
            "id": "task-123",
            "kind": "task",
            "status": {
                "state": "failed",
                "timestamp": "2026-07-12T16:06:00.841041+00:00",
                "message": {
                    "parts": [
                        {
                            "kind": "text",
                            "text": "quota exceeded: 50 requests/hour limit",
                        }
                    ]
                },
            },
            "artifacts": [],
        }
        outcome = job_outcome(failed_task)
        assert outcome.ok is False
        assert outcome.state == "failed"
        # The detail must be non-empty and contain the message text
        assert outcome.detail, "outcome.detail should be non-empty when message is present"
        assert "quota" in outcome.detail.lower() or "exceeded" in outcome.detail.lower()

    def test_import_report_has_error_reason_field(self):
        """DESIRED: ImportReport must have an error_reason field to hold failure reason.

        This test asserts the DESIRED post-fix behavior: ImportReport should have
        a field to capture and carry the failure reason from job_outcome.
        """
        report = ImportReport()
        # The desired behavior: error_reason field must exist
        assert hasattr(
            report, "error_reason"
        ), "ImportReport should have error_reason field to surface failure reason"

    def test_failed_theorizer_captures_error_reason(self):
        """DESIRED: ingest_theorizer must capture outcome.detail in report.error_reason.

        When a theorizer task fails with a reason in status.message, the ingest
        should populate report.error_reason so the CLI can surface it to the user.
        This test FAILS on main and PASSES after the fix.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            failed_task_with_reason = {
                "id": "task-456",
                "kind": "task",
                "status": {
                    "state": "failed",
                    "timestamp": "2026-07-12T16:06:00.841041+00:00",
                    "message": {
                        "parts": [
                            {
                                "kind": "text",
                                "text": "internal server error: connection pool exhausted",
                            }
                        ]
                    },
                },
                "history": [{"parts": [{"kind": "text", "text": "Task accepted"}]}],
                "artifacts": [],
            }

            config = load_config()
            report = loop.run_until_complete(
                ingest_theorizer(
                    failed_task_with_reason,
                    link_to=None,
                    config=config,
                    artifact_path=None,
                    used_inputs=None,
                )
            )

            # The desired behavior: report should have error_reason field
            assert hasattr(
                report, "error_reason"
            ), "report should have error_reason field"

            # The error_reason should be non-empty for a failed task with a message
            assert report.error_reason, (
                "report.error_reason should be non-empty when task failed with a reason"
            )

            # The error_reason should contain the actual failure message
            assert (
                "server error" in report.error_reason.lower()
                or "connection pool" in report.error_reason.lower()
                or "pool exhausted" in report.error_reason.lower()
            ), (
                "report.error_reason should contain the extracted error message, "
                f"got: {report.error_reason}"
            )

            # Verify other expected fields are set correctly
            assert report.failed is True, "report.failed should be True"
            assert report.job_state == "failed", "report.job_state should be 'failed'"
        finally:
            loop.close()

    def test_failed_theorizer_without_message_generates_fallback_reason(self):
        """DESIRED: When no status.message is present, a fallback reason is generated.

        Even when status.message is missing, report.error_reason should have SOME
        indication that the job failed, not be empty.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Failed task with NO status.message (the original issue scenario)
            failed_task_no_message = {
                "id": "task-789",
                "kind": "task",
                "status": {
                    "state": "failed",
                    "timestamp": "2026-07-12T16:06:00.841041+00:00",
                },
                "history": [{"parts": [{"kind": "text", "text": "Task accepted"}]}],
                "artifacts": [],
            }

            config = load_config()
            report = loop.run_until_complete(
                ingest_theorizer(
                    failed_task_no_message,
                    link_to=None,
                    config=config,
                    artifact_path=None,
                    used_inputs=None,
                )
            )

            # The desired behavior: error_reason should still be populated,
            # even with a fallback message
            assert hasattr(
                report, "error_reason"
            ), "report should have error_reason field"
            assert report.error_reason, (
                "report.error_reason should be non-empty even when no status.message "
                "(should contain a fallback reason like 'did not complete')"
            )

            # Verify other expected fields are set correctly
            assert report.failed is True, "report.failed should be True"
            assert report.job_state == "failed", "report.job_state should be 'failed'"
        finally:
            loop.close()
