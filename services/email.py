"""
BlendPilot — Email Review Service

Handles sending review emails for human approval and parsing
reviewer feedback into structured change requests.

Phase: 9 (interface defined, implementation pending)

SAFETY RULES:
- Never send emails automatically — always require explicit user approval
- Log all sent emails for audit
- Parse feedback into structured format — never execute raw text as commands
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("blendpilot.services.email")


# ── Data Models ─────────────────────────────────────────────


class ReviewEmailContent(BaseModel):
    """Content for a review email."""

    asset_name: str = Field(...,
                            description="Name of the asset being reviewed")
    version: str = Field(default="1.0", description="Asset version string")
    preview_image_path: str = Field(...,
                                    description="Path to the preview render")
    triangle_count: int = Field(default=0, ge=0)
    triangle_limit: int = Field(default=0, ge=0)
    validation_status: str = Field(default="PASS", description="PASS or FAIL")
    validation_issues: list[dict[str, Any]] = Field(default_factory=list)
    changes_summary: str = Field(
        default="", description="Summary of changes made")
    design_spec_summary: str = Field(
        default="", description="Original design requirements")


class EmailSendResult(BaseModel):
    """Result of sending an email."""

    sent: bool = False
    message_id: str | None = None
    recipient: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    error: str | None = None


class FeedbackItem(BaseModel):
    """A single piece of feedback from a reviewer."""

    target: str = Field(...,
                        description="Object or area the feedback applies to")
    instruction: str = Field(..., description="What should be changed")
    priority: str = Field(default="medium", description="low, medium, or high")


class ParsedFeedback(BaseModel):
    """Structured feedback parsed from a reviewer's response."""

    reviewer: str = ""
    timestamp: str = ""
    overall_decision: str = Field(
        default="",
        description="APPROVE, REQUEST_CHANGE, ROLLBACK, or REJECT",
    )
    changes: list[FeedbackItem] = Field(default_factory=list)
    free_text_notes: str = ""


# ── Service ─────────────────────────────────────────────────


class EmailService:
    """Handles review email sending and feedback parsing.

    This service is used by the Feedback Agent (Workflow 9)
    for asynchronous human review workflows.

    IMPORTANT: The send_review_email method must only be called
    AFTER explicit user approval. The system never sends emails
    automatically.

    Usage:
        email = EmailService(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            username="...",
            password="...",
        )
        result = await email.send_review_email(
            to="reviewer@example.com",
            content=ReviewEmailContent(
                asset_name="SciFi Crate v1",
                preview_image_path="./output/preview.png",
                ...
            ),
        )
    """

    def __init__(
        self,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    async def send_review_email(
        self,
        to: str,
        content: ReviewEmailContent,
    ) -> EmailSendResult:
        """Compose and send a review email.

        REQUIRES EXPLICIT USER APPROVAL before calling.

        Args:
            to: Recipient email address.
            content: Review email content including preview and QA results.

        Returns:
            EmailSendResult with send status and message ID.
        """
        logger.info("Preparing review email to %s for asset '%s'",
                    to, content.asset_name)

        # Phase 9: implement actual SMTP sending
        # For now, log the intent and return a stub
        logger.warning(
            "Email sending not yet implemented — returning stub result.")

        return EmailSendResult(
            sent=False,
            recipient=to,
            error="Email service not yet implemented (Phase 9).",
        )

    async def parse_feedback(self, email_body: str, sender: str = "") -> ParsedFeedback:
        """Parse a reviewer's email response into structured feedback.

        Uses LLM to extract change requests from free-form email text
        into structured FeedbackItem objects.

        Args:
            email_body: Raw text of the reviewer's email.
            sender: Email address of the reviewer.

        Returns:
            ParsedFeedback with extracted change requests.
        """
        logger.info("Parsing feedback email from '%s' (%d chars)",
                    sender, len(email_body))

        # Phase 9: implement actual LLM-based parsing
        # For now, return empty feedback
        logger.warning(
            "Feedback parsing not yet implemented — returning empty result.")

        return ParsedFeedback(
            reviewer=sender,
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_decision="",
            changes=[],
            free_text_notes=email_body,
        )

    def compose_review_html(self, content: ReviewEmailContent) -> str:
        """Generate HTML email body for a review email.

        Args:
            content: Review email content.

        Returns:
            HTML string for the email body.
        """
        issues_html = ""
        if content.validation_issues:
            issues_list = "".join(
                f"<li><strong>{issue.get('issue_type', 'Unknown')}</strong> on "
                f"{issue.get('object_name', '?')}: {issue.get('message', '')}</li>"
                for issue in content.validation_issues
            )
            issues_html = f"<h3>Validation Issues</h3><ul>{issues_list}</ul>"

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1>BlendPilot — Asset Review</h1>
            <h2>{content.asset_name} (v{content.version})</h2>

            <p><strong>Validation:</strong> {content.validation_status}</p>
            <p><strong>Triangles:</strong> {content.triangle_count:,} / {content.triangle_limit:,}</p>

            <h3>Design Requirements</h3>
            <p>{content.design_spec_summary}</p>

            <h3>Changes Made</h3>
            <p>{content.changes_summary}</p>

            {issues_html}

            <hr>
            <p>Please reply with one of:</p>
            <ul>
                <li><strong>APPROVE</strong> — Accept the asset as-is</li>
                <li><strong>REQUEST CHANGE</strong> — Describe what needs to change</li>
                <li><strong>ROLLBACK</strong> — Revert to a previous version</li>
                <li><strong>REJECT</strong> — Discard this asset</li>
            </ul>

            <p style="color: #888; font-size: 12px;">
                Generated by BlendPilot — {content.version}
            </p>
        </body>
        </html>
        """
