import pytest

from src.core.domain.policies.ingest_policy import IngestPolicy


@pytest.fixture
def ingest_policy() -> IngestPolicy:
    return IngestPolicy()


@pytest.fixture
def ingest_policy_with_pii() -> IngestPolicy:
    return IngestPolicy(enable_pii_detection=True)
