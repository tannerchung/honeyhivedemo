"""
Enhanced mock customer support tickets designed for demo narrative.

Story Arc:
- Issues 1-2: Clear successes (routing, keywords, steps all work)
- Issue 3: CLEAR FAILURE - ambiguous issue that fails routing (demo debugging case)
- Issues 4-7: Mix of partial successes (some metrics pass, some fail)
- Issue 8: Another clear failure (shows error cascade)
- Issues 9-10: Successes to end on positive note

Overall: ~70-75% pass rate (realistic, shows room for improvement)
"""

MOCK_TICKETS_ENHANCED = [
    # === CLEAR SUCCESSES (Issues 1-2) ===
    {
        "id": "1",
        "customer": "Alice Martinez",
        "issue": "I'm getting a 404 error when I try to upload files through the dashboard.",
        "complexity": "straightforward",
        "expected_outcome": "success",
    },
    {
        "id": "2",
        "customer": "Ben Chen",
        "issue": "I can't log into my account because the SSO redirect keeps looping back to the login page.",
        "complexity": "straightforward",
        "expected_outcome": "success",
    },

    # === CLEAR FAILURE - Demo Debugging Case (Issue 3) ===
    {
        "id": "3",
        "customer": "Cara Johnson",
        "issue": "My download isn't working and I've been waiting for 20 minutes.",
        "complexity": "ambiguous",  # Could be export OR upload issue!
        "expected_outcome": "failure",
        "demo_note": "Ambiguous issue - could be data_export or upload_errors. Model will likely misroute to upload_errors. Use this to show error cascade debugging."
    },

    # === MIXED RESULTS (Issues 4-7) ===
    {
        "id": "4",
        "customer": "Diego Ramirez",
        "issue": "The password reset email expired before I could use it and now I'm locked out.",
        "complexity": "straightforward",
        "expected_outcome": "success",
    },
    {
        "id": "5",
        "customer": "Ella Thompson",
        "issue": "File uploads fail in Safari but work fine in Chrome. Is this a known browser issue?",
        "complexity": "medium",
        "expected_outcome": "partial_success",
        "demo_note": "Routes correctly but may miss some keywords or action steps"
    },
    {
        "id": "6",
        "customer": "Farah Patel",
        "issue": "I need to export more than a million records but the CSV format has a row limit. Can you help?",
        "complexity": "medium",
        "expected_outcome": "partial_success",
    },
    {
        "id": "7",
        "customer": "Gina Williams",
        "issue": "My account is locked after too many failed 2FA attempts. How do I unlock it?",
        "complexity": "straightforward",
        "expected_outcome": "success",
    },

    # === ANOTHER FAILURE - Show Pattern (Issue 8) ===
    {
        "id": "8",
        "customer": "Hank Davis",
        "issue": "The system shows stale files even after I refreshed. Cache issue maybe?",
        "complexity": "ambiguous",
        "expected_outcome": "failure",
        "demo_note": "Ambiguous cache issue - removed 'upload' keyword to ensure routing failure. Shows pattern of ambiguous technical terms failing."
    },

    # === SUCCESSES to Close Strong (Issues 9-10) ===
    {
        "id": "9",
        "customer": "Ivan Sokolov",
        "issue": "The export download link says it expired and I can't retrieve my data anymore.",
        "complexity": "straightforward",
        "expected_outcome": "success",
    },
    {
        "id": "10",
        "customer": "Judy Anderson",
        "issue": "My browser blocks the file upload saying 'mixed content'. What does that mean?",
        "complexity": "straightforward",
        "expected_outcome": "success",
    },
]

# For backwards compatibility
MOCK_TICKETS = MOCK_TICKETS_ENHANCED
