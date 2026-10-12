"""poppy-sidecar: the first independent developer kit for the Personal Agent Protocol.

Generate, validate, and test ``poppy.json`` discovery documents (PAP draft 0.1),
plus a compliance testbed that checks whether an agent respects declared scopes.
"""

__version__ = "0.1.0"
__protocol_version__ = "0.1"  # PAP draft version this kit targets

from poppy_sidecar.generator import generate, interactive_profile
from poppy_sidecar.validator import validate, ValidationReport
from poppy_sidecar.testbed import run_testbed, TestbedReport
from poppy_sidecar.core import DiscoveryDoc, AgentTrace, AttemptedAction, conformance_report

__all__ = [
    "__version__",
    "__protocol_version__",
    "generate",
    "interactive_profile",
    "validate",
    "ValidationReport",
    "run_testbed",
    "TestbedReport",
    "DiscoveryDoc",
    "AgentTrace",
    "AttemptedAction",
    "conformance_report",
]
