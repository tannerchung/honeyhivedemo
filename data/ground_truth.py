"""
Enhanced ground truth labels designed for demo narrative.

Key Insights for Demo:
- Issue #3: Intentionally ambiguous (download = export), likely to be misrouted
- Issue #8: Another ambiguous case (CDN cache for uploads)
- Other issues: Clear routing paths with specific keyword requirements
- Keyword coverage varies to show metric diversity
"""

GROUND_TRUTH_ENHANCED = {
    # === Issue 1: Clear success case ===
    "1": {
        "expected_category": "upload_errors",
        "expected_keywords": ["404", "endpoint", "url", "path"],
        "expected_tone": "friendly_technical",
        "has_action_steps": True,
        "demo_note": "Perfect case - clear issue, good keywords, numbered steps expected"
    },

    # === Issue 2: Clear success case ===
    "2": {
        "expected_category": "account_access",
        "expected_keywords": ["sso", "redirect", "identity provider", "saml"],
        "expected_tone": "reassuring",
        "has_action_steps": True,
        "demo_note": "SSO issue - routes correctly, has good keywords"
    },

    # === Issue 3: INTENTIONAL FAILURE CASE ===
    "3": {
        "expected_category": "data_export",  # But says "download" which is ambiguous!
        "expected_keywords": ["queue", "status", "processing"],
        "expected_tone": "urgent_but_calm",
        "has_action_steps": True,
        "demo_note": "DEMO FAILURE CASE: Ambiguous issue. Says 'download' but should route to data_export. Model likely misroutes to upload_errors or other. Shows error cascade."
    },

    # === Issue 4: Success case ===
    "4": {
        "expected_category": "account_access",
        "expected_keywords": ["password", "reset", "link", "email"],
        "expected_tone": "reassuring",
        "has_action_steps": True,
    },

    # === Issue 5: Partial success (good routing, may miss some keywords) ===
    "5": {
        "expected_category": "upload_errors",
        "expected_keywords": ["browser", "safari", "https", "compatibility", "ssl"],
        "expected_tone": "friendly_technical",
        "has_action_steps": True,
        "demo_note": "Routes correctly but keywords are specific - may only hit 3/5 = 60%"
    },

    # === Issue 6: Good case ===
    "6": {
        "expected_category": "data_export",
        "expected_keywords": ["json", "csv", "limit", "format"],
        "expected_tone": "pragmatic",
        "has_action_steps": True,
    },

    # === Issue 7: Success case ===
    "7": {
        "expected_category": "account_access",
        "expected_keywords": ["2fa", "locked", "unlock", "administrator"],
        "expected_tone": "reassuring",
        "has_action_steps": True,
    },

    # === Issue 8: INTENTIONAL FAILURE CASE ===
    "8": {
        "expected_category": "upload_errors",  # Should be upload_errors (CDN cache issue)
        "expected_keywords": ["cdn", "cache", "purge", "cloudflare"],
        "expected_tone": "friendly_technical",
        "has_action_steps": True,
        "demo_note": "DEMO FAILURE CASE: Ambiguous 'cache' and 'stale' without 'upload' keyword. Will route to 'other' in heuristic mode. Shows pattern of ambiguous technical terms causing failures."
    },

    # === Issue 9: Success case ===
    "9": {
        "expected_category": "data_export",
        "expected_keywords": ["expired", "download", "regenerate", "24 hours"],
        "expected_tone": "pragmatic",
        "has_action_steps": True,
    },

    # === Issue 10: Success case ===
    "10": {
        "expected_category": "upload_errors",
        "expected_keywords": ["https", "mixed content", "ssl", "security"],
        "expected_tone": "friendly_technical",
        "has_action_steps": True,
    },
}

# For backwards compatibility
GROUND_TRUTH = GROUND_TRUTH_ENHANCED
