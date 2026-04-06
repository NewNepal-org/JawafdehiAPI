"""
Constants for the CIAA Caseworker workflow.
"""

# Hardcoded list of CIAA Special Court case numbers to process.
# This is the single source of truth used by both the
# discover_and_draft_cases management command and get_eligible_cases().
CIAA_CASE_NUMBERS: list[str] = [
    "081-CR-0022",
    "081-CR-0044",
    "081-CR-0048",
    "081-CR-0060",
    "081-CR-0076",
    "081-CR-0087",
    "081-CR-0090",
    "081-CR-0091",
    "081-CR-0095",
    "081-CR-0097",
    "081-CR-0104",
    "081-CR-0107",
    "081-CR-0116",
    "081-CR-0121",
    "081-CR-0122",
    "081-CR-0123",
    "081-CR-0127",
    "081-CR-0136",
    "081-CR-0138",
]
