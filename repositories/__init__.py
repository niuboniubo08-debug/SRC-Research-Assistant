"""Focused persistence repositories used by the phase-5 management services."""

from repositories.evidence_repository import EvidenceRepository
from repositories.vulnerability_repository import VulnerabilityRepository

__all__ = ["EvidenceRepository", "VulnerabilityRepository"]
