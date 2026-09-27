"""
statistics/config.py
--------------------
Configuration parameters for Year-over-Year Statistical Analysis.
Includes configurable significance thresholds, PSI binning parameters,
and canonical jurisdiction mappings.
"""

import os
from dataclasses import dataclass
from typing import Dict


# Documented canonical jurisdiction mappings across fiscal years
CANONICAL_STATE_MAP: Dict[str, str] = {
    "CHHATTISGARH": "CHATTISGARH",
    "CHATTISGARH": "CHATTISGARH",
    "JAMMU AND KASHMIR": "JAMMU & KASHMIR",
    "JAMMU & KASHMIR": "JAMMU & KASHMIR",
    "Other Territory": "OTHER TERRITORY",
    "OTHER TERRITORY": "OTHER TERRITORY",
}


@dataclass(frozen=True)
class StatisticalConfig:
    """Configurable thresholds and parameters for statistical testing."""
    alpha: float = float(os.getenv("STATISTICAL_ALPHA", "0.05"))
    psi_threshold_moderate: float = float(os.getenv("PSI_THRESHOLD_MODERATE", "0.10"))
    psi_threshold_significant: float = float(os.getenv("PSI_THRESHOLD_SIGNIFICANT", "0.25"))
    psi_epsilon: float = float(os.getenv("PSI_EPSILON", "1e-4"))
    min_sample_size_ks: int = 5
    default_state_bins: int = 5
    default_chapter_bins: int = 10
    default_matrix_bins: int = 10


DEFAULT_STATISTICAL_CONFIG = StatisticalConfig()
