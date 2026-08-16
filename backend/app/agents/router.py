from app.core.config import settings


def choose_model(query: str, context_count: int = 0) -> str:
    """Deterministic first-pass router; replace with a learned/cost-aware policy after evaluation."""
    complexity = len(query.split()) + context_count * 10
    return settings.FAST_LLM_MODEL if complexity < 80 else settings.PRIMARY_LLM_MODEL
