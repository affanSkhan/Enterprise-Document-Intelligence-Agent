from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class ModelPolicy:
    model: str
    max_output_tokens: int
    estimated_usd_per_1k_tokens: float


POLICIES = {
    settings.FAST_LLM_MODEL: ModelPolicy(settings.FAST_LLM_MODEL, 1024, 0.001),
    settings.PRIMARY_LLM_MODEL: ModelPolicy(settings.PRIMARY_LLM_MODEL, 4096, 0.005),
}


def choose_cost_aware_model(query_tokens: int, context_tokens: int, *, budget_usd: float | None = None) -> ModelPolicy:
    complexity = query_tokens + context_tokens
    fast = POLICIES[settings.FAST_LLM_MODEL]
    primary = POLICIES[settings.PRIMARY_LLM_MODEL]
    if budget_usd is not None and budget_usd <= 0:
        raise ValueError("budget_usd must be positive")
    if complexity < 1200 and (budget_usd is None or budget_usd >= fast.estimated_usd_per_1k_tokens):
        return fast
    if budget_usd is not None and budget_usd < primary.estimated_usd_per_1k_tokens:
        return fast
    return primary
