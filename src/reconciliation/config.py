"""
reconciliation/config.py
------------------------
Configuration management for reconciliation tolerances and governance rules.
Adheres to governance constraint 10: Tolerances must be configurable rather
than hard-coded throughout the codebase. Exposes both absolute_tolerance and
relative_tolerance.
"""

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class ReconciliationConfig:
    """Configurable tolerances and thresholds for validation checks."""
    absolute_tolerance: float = float(os.getenv("RECONCILIATION_ABSOLUTE_TOLERANCE", os.getenv("RECONCILIATION_FLOAT_TOLERANCE", "0.0001")))
    relative_tolerance: float = float(os.getenv("RECONCILIATION_RELATIVE_TOLERANCE", "1e-7"))
    
    # Backwards compatibility alias
    @property
    def float_tolerance(self) -> float:
        return self.absolute_tolerance

    allow_advisory_failures: bool = os.getenv("ALLOW_ADVISORY_FAILURES", "true").lower() == "true"
    
    # Official expected sheet names
    expected_worksheets: tuple = (
        "Tab I_Stat_to_Stat_Revised_Road",
        "Tab II_Chap_Revised_Road",
        "Tab III_Outward_Revised_Road",
        "Tab IV_Inward_Revised_Road",
        "Tab V_Internal_Revised_Road",
    )

    # Official expected entity counts
    expected_state_count: int = 33
    expected_chapter_count: int = 90
    expected_published_national_total: float = 20319786.98011017
    expected_published_outward_total: float = 10429324.40404665
    expected_published_internal_total: float = 9890462.576063517

    # Official 33 observed source jurisdictions (source spelling preserved)
    expected_states: tuple = (
        "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM", "BIHAR", "CHANDIGARH",
        "CHATTISGARH", "DELHI", "GOA", "GUJARAT", "HARYANA",
        "HIMACHAL PRADESH", "JAMMU & KASHMIR", "JHARKHAND", "KARNATAKA", "KERALA",
        "MADHYA PRADESH", "MAHARASHTRA", "MANIPUR", "MEGHALAYA", "MIZORAM",
        "NAGALAND", "ODISHA", "OTHER TERRITORY", "PUDUCHERRY", "PUNJAB",
        "RAJASTHAN", "SIKKIM", "TAMIL NADU", "TELANGANA", "TRIPURA",
        "UTTAR PRADESH", "UTTARAKHAND", "WEST BENGAL"
    )

    # Official 90 observed source chapter codes ('10' through '99')
    expected_chapters: tuple = tuple(f"{i:02d}" if i < 10 else str(i) for i in range(10, 100))


# Default configuration singleton
DEFAULT_CONFIG = ReconciliationConfig()
