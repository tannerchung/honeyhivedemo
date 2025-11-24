"""
Ground truth metadata for evaluators.
"""

GROUND_TRUTH = {
    "1": {
        "expected_category": "upload_errors",
        "expected_keywords": ["404", "path", "https"],
        "expected_tone": "friendly_technical",
    },
    "2": {
        "expected_category": "account_access",
        "expected_keywords": ["sso", "idp", "redirect"],
        "expected_tone": "reassuring",
    },
    "3": {
        "expected_category": "data_export",
        "expected_keywords": ["queue", "15 minutes", "status"],
        "expected_tone": "urgent_but_calm",
    },
    "4": {
        "expected_category": "account_access",
        "expected_keywords": ["reset", "link", "15 minutes"],
        "expected_tone": "reassuring",
    },
    "5": {
        "expected_category": "upload_errors",
        "expected_keywords": ["browser", "safari", "https"],
        "expected_tone": "friendly_technical",
    },
    "6": {
        "expected_category": "data_export",
        "expected_keywords": ["json", "limit", "1m"],
        "expected_tone": "pragmatic",
    },
    "7": {
        "expected_category": "account_access",
        "expected_keywords": ["lock", "admin", "security"],
        "expected_tone": "reassuring",
    },
    "8": {
        "expected_category": "upload_errors",
        "expected_keywords": ["cdn", "cache", "clear"],
        "expected_tone": "friendly_technical",
    },
    "9": {
        "expected_category": "data_export",
        "expected_keywords": ["expired", "download", "24 hours"],
        "expected_tone": "pragmatic",
    },
    "10": {
        "expected_category": "upload_errors",
        "expected_keywords": ["https", "mixed content", "ssl"],
        "expected_tone": "friendly_technical",
    },
}
