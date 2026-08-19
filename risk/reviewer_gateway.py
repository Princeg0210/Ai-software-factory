import json
from typing import Dict, Any, Optional

class HumanReviewerGateway:
    """
    Manages human review routing and generates rich interactive
    Slack / Microsoft Teams / GitHub Webhook notification payloads.
    """
    
    @staticmethod
    def generate_slack_payload(
        issue_id: str,
        issue_title: str,
        patch_diff: str,
        rri_result: Dict[str, Any],
        lint_report: Dict[str, Any],
        mutation_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Creates a structured Slack Block Kit message payload.
        """
        rri_score = rri_result.get("rri_score", 1.0)
        risk_color = "#36a64f" if rri_score < 0.30 else "#ff0000"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Human Review Gate Required: {issue_id}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Issue Title:* {issue_title}\n*Regression Risk Index (RRI):* `{rri_score}` (Threshold: < 0.30)"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Linter Gate:* {'✅ Passed' if lint_report.get('passes_lint') else '❌ Failed'}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Mutation Score:* `{mutation_report.get('mutation_score', 0.0) * 100}%` (Killed: {mutation_report.get('killed_mutants', 0)}/{mutation_report.get('total_mutants', 0)})"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Proposed Diff:*\n```\n{patch_diff[:1500]}\n```"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve & Merge",
                            "emoji": True
                        },
                        "style": "primary",
                        "value": f"approve_{issue_id}",
                        "action_id": "btn_approve"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Reject Patch",
                            "emoji": True
                        },
                        "style": "danger",
                        "value": f"reject_{issue_id}",
                        "action_id": "btn_reject"
                    }
                ]
            }
        ]

        return {
            "text": f"AI Software Factory Review Gate for {issue_id}",
            "blocks": blocks
        }
