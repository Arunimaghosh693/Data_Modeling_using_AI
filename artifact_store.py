from __future__ import annotations

from typing import Dict
from uuid import uuid4

try:
    from schemas import ConceptualModel
except ImportError:  # pragma: no cover - supports package-style imports
    from .schemas import ConceptualModel


_CONCEPTUAL_ARTIFACTS: Dict[str, ConceptualModel] = {}


def save_conceptual_artifact(conceptual_model: ConceptualModel) -> str:
    artifact_id = str(uuid4())
    _CONCEPTUAL_ARTIFACTS[artifact_id] = conceptual_model
    return artifact_id


def get_conceptual_artifact(artifact_id: str) -> ConceptualModel | None:
    return _CONCEPTUAL_ARTIFACTS.get(artifact_id)
