"""
In-memory knowledge base for the support agent.
"""

KNOWLEDGE_BASE = {
    "upload_errors": [
        "404 errors usually mean the upload URL or path is incorrect. Verify the endpoint and trailing slashes.",
        "Ensure the file size is under 100MB; larger files require chunked uploads.",
        "Clear CDN or browser cache after redeploying static assets to avoid stale 404s.",
        "Uploads must use HTTPS; mixed content (HTTP) can be blocked by the browser."
    ],
    "account_access": [
        "Password resets expire after 15 minutes; resend if the link has lapsed.",
        "Two-factor authentication codes can drift—sync device time and retry.",
        "Admins can unlock accounts from the Security > Sessions page.",
        "SSO users must initiate login from the company portal, not the direct login form."
    ],
    "data_export": [
        "Exports are queued; large exports may take up to 15 minutes to generate.",
        "CSV exports are limited to 1M rows—use JSON for larger datasets.",
        "Check the Exports page for status and download links; links expire after 24 hours.",
        "If an export fails, retry after reducing filters or date range."
    ],
    "other": [
        "For issues outside documented categories, collect logs and timestamps before escalation.",
        "Share browser, OS, and app version to speed up troubleshooting.",
        "Check status page for ongoing incidents before deep-diving."
    ],
}
