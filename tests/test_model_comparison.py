"""
PromptShield AI — Test Suite for Multi-Category Comparison, Freshness Audit & Lifecycle Verification.
=====================================================================================================
Tests:
1. Model Registry & Strict Lifecycle Eligibility (Active vs Deprecated/Retired).
2. Deep Audit of Target Models (gpt-4o, o1, o3-mini, gemini-2.0-flash, gemini-2.5, claude-3-7-sonnet, grok-3).
3. Stale Pricing and Unverified Metadata Rejection.
4. Category Separation: Foundation Models, IDE Assistants, and AI App Builders.
5. Local Tokenizer Adapters (Exact tiktoken vs Calibrated Heuristic estimates).
6. Published Pricing & Cost Calculations (No zero-cost fabrication).
7. Multi-Criteria Ranking (WSM and TOPSIS) with Missing Value Handling.
8. IDE and App Builder Multi-Criteria Ranking.
9. Lifecycle Filtering Enforcement (Default vs Historical Access).
10. Consistency between GET /models and POST /compare-models.
11. Provenance Compliance & Absence of Fabricated Metrics.
12. FastAPI Endpoints for all categories, specific lookups, and error conditions.
13. Strict 100% Offline Operation: Outbound networking blocked to guarantee zero provider API calls.
"""

import math
from pathlib import Path
import socket
import sys
from unittest.mock import patch

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from fastapi.testclient import TestClient

from main import app
from analyzers.model_comparison import (
    registry,
    LifecycleStatus,
    ProductCategory,
    ProductAvailability,
    ModelPricing,
    ModelMetadata,
    IDEProductMetadata,
    AppBuilderMetadata,
    get_tokenizer_adapter,
    OpenAITokenizerAdapter,
    GeminiTokenizerAdapter,
    ClaudeTokenizerAdapter,
    feature_extractor,
    task_classifier,
    calculate_model_cost,
    calculate_suitability,
    RankingMethod,
    RankingPreset,
    rank_models,
    comparison_engine
)
from analyzers.model_comparison.ranker import (
    CandidateEvaluation,
    validate_and_normalize_weights,
    rank_models_weighted_sum,
    rank_models_topsis,
    rank_products
)
from analyzers.model_comparison.tokenizer_adapters import (
    UnsupportedTokenizerAdapter,
    GrokTokenizerAdapter,
    DeepSeekTokenizerAdapter
)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Model Registry & Strict Lifecycle Tests
# ---------------------------------------------------------------------------

def test_model_registry_coverage_and_lifecycle():
    # 1. Default recommendation pool excludes deprecated, retired, preview, and unverified models
    active_models = registry.list_models(include_deprecated=False)
    assert len(active_models) == 21, f"Expected exactly 21 active models, found {len(active_models)}"
    assert all(m.lifecycle_status == LifecycleStatus.ACTIVE for m in active_models)
    assert all(registry.is_model_eligible(m.model_id) for m in active_models)

    # Verify modern active models across 5 providers
    active_ids = {m.model_id for m in active_models}

    # OpenAI (7 modern verified models)
    assert "gpt-5.5" in active_ids
    assert "gpt-5.5-pro" in active_ids
    assert "gpt-5" in active_ids
    assert "gpt-5-mini" in active_ids
    assert "gpt-6-astra" in active_ids
    assert "gpt-6-sol" in active_ids
    assert "gpt-6-luna" in active_ids

    # Google (6 modern verified models)
    assert "gemini-4-argon" in active_ids
    assert "gemini-3.8-flash" in active_ids
    assert "gemini-3.7-flash" in active_ids
    assert "gemini-3.6-flash" in active_ids
    assert "gemini-3.5-flash" in active_ids
    assert "gemini-3.5-flash-lite" in active_ids

    # Anthropic (4 modern verified models)
    assert "claude-fable-5-1" in active_ids
    assert "claude-opus-5-5" in active_ids
    assert "claude-sonnet-5-5" in active_ids
    assert "claude-haiku-5-5" in active_ids

    # xAI (2 modern verified models)
    assert "grok-4.7" in active_ids
    assert "grok-4.3" in active_ids

    # DeepSeek (2 modern verified models)
    assert "deepseek-v4-pro" in active_ids
    assert "deepseek-flash" in active_ids

    # Crucial negative tests: Gemini 1.x models MUST NOT be active
    assert "gemini-1.0-pro" not in active_ids
    assert "gemini-1.5-pro" not in active_ids
    assert "gemini-1.5-flash" not in active_ids

    # Retired legacy models MUST NOT be active
    assert "deepseek-reasoner" not in active_ids
    assert "deepseek-chat" not in active_ids
    assert "gpt-4o" not in active_ids
    assert "gpt-4o-mini" not in active_ids
    assert "o1" not in active_ids
    assert "claude-3-7-sonnet" not in active_ids
    assert "gemini-2.0-flash" not in active_ids

    # 2. Including deprecated/retired/preview exposes full historical catalogue
    all_models = registry.list_models(include_deprecated=True)
    assert len(all_models) >= 40, f"Expected at least 40 total models, found {len(all_models)}"

    providers = {m.provider for m in all_models}
    assert "openai" in providers
    assert "google" in providers
    assert "anthropic" in providers
    assert "xai" in providers
    assert "deepseek" in providers


# ---------------------------------------------------------------------------
# 2. Audit Target Models Lifecycle & Provenance Verification
# ---------------------------------------------------------------------------

def test_audit_target_models_lifecycle_and_provenance():
    """
    Validates lifecycle status, exact IDs, and eligibility for all key audit targets.
    """
    # Active GA targets (verified in official docs)
    ga_targets = [
        ("gpt-5.5", 1_050_000, 5.00, 30.00),
        ("gpt-5.5-pro", 1_050_000, 30.00, 180.00),
        ("gpt-5", 400_000, 1.25, 10.00),
        ("gpt-5-mini", 400_000, 0.25, 2.00),
        ("gpt-6-astra", 1_050_000, 10.00, 50.00),
        ("gpt-6-sol", 1_050_000, 2.00, 10.00),
        ("gpt-6-luna", 1_050_000, 0.10, 0.50),
        ("gemini-4-argon", 1_048_576, 2.00, 10.00),
        ("gemini-3.8-flash", 1_048_576, 0.75, 3.75),
        ("gemini-3.7-flash", 1_048_576, 0.75, 3.75),
        ("gemini-3.6-flash", 1_048_576, 0.75, 3.75),
        ("gemini-3.5-flash", 1_048_576, 1.50, 9.00),
        ("gemini-3.5-flash-lite", 1_048_576, 0.30, 2.50),
        ("claude-fable-5-1", 1_000_000, 10.00, 50.00),
        ("claude-opus-5-5", 1_000_000, 4.00, 20.00),
        ("claude-sonnet-5-5", 1_000_000, 2.00, 10.00),
        ("claude-haiku-5-5", 1_000_000, 0.10, 0.50),
        ("grok-4.7", 500_000, 2.00, 6.00),
        ("grok-4.3", 1_000_000, 1.25, 2.50),
        ("deepseek-v4-pro", 1_000_000, 0.66, 1.98),
        ("deepseek-flash", 1_000_000, 0.15, 0.60),
    ]

    for model_id, expected_ctx, exp_in_cost, exp_out_cost in ga_targets:
        m = registry.get_foundation_model(model_id)
        assert m is not None, f"Model '{model_id}' must exist in catalogue"
        assert m.lifecycle_status == LifecycleStatus.ACTIVE, f"Model '{model_id}' must be ACTIVE"
        assert registry.is_model_eligible(model_id) is True, f"Model '{model_id}' must be eligible"
        assert m.context_window_tokens == expected_ctx
        assert m.pricing.input_cost_per_m == exp_in_cost
        assert m.pricing.output_cost_per_m == exp_out_cost
        assert m.pricing.is_known is True
        assert m.pricing.is_stale is False

    # Excluded targets: unverified, preview, or deprecated/retired
    excluded_targets = [
        ("gemini-3.1-pro-preview", LifecycleStatus.PREVIEW),
        ("gemini-2.5-pro", LifecycleStatus.UNVERIFIED),
        ("gemini-2.5-flash", LifecycleStatus.UNVERIFIED),
        ("grok-3", LifecycleStatus.PREVIEW),
        ("grok-3-mini", LifecycleStatus.PREVIEW),
        ("deepseek-chat", LifecycleStatus.RETIRED),
        ("deepseek-reasoner", LifecycleStatus.RETIRED),
        ("gemini-1.5-pro", LifecycleStatus.RETIRED),
        ("gemini-1.5-flash", LifecycleStatus.RETIRED),
        ("gemini-1.0-pro", LifecycleStatus.RETIRED),
        ("gemini-2.0-flash", LifecycleStatus.RETIRED),
        ("gpt-4o", LifecycleStatus.RETIRED),
        ("claude-3-7-sonnet", LifecycleStatus.RETIRED),
        ("gpt-4-turbo", LifecycleStatus.DEPRECATED),
        ("gpt-3.5-turbo", LifecycleStatus.RETIRED),
    ]

    for model_id, expected_status in excluded_targets:
        m = registry.get_foundation_model(model_id)
        assert m is not None, f"Target '{model_id}' must exist in full catalogue"
        assert m.lifecycle_status == expected_status
        assert registry.is_model_eligible(model_id) is False, (
            f"Target '{model_id}' ({expected_status}) must NOT be eligible for default rankings"
        )


def test_gemini_1x_exclusion_from_default_listings():
    """Regression test: Gemini 1.x models must NEVER appear in active default listings or rankings."""
    active_models = registry.list_models(include_deprecated=False)
    active_ids = {m.model_id for m in active_models}
    assert "gemini-1.0-pro" not in active_ids
    assert "gemini-1.5-pro" not in active_ids
    assert "gemini-1.5-flash" not in active_ids

    # Must be in historical catalogue marked as retired
    historical = registry.list_historical_models()
    hist_ids = {m.model_id for m in historical}
    assert "gemini-1.0-pro" in hist_ids
    assert "gemini-1.5-pro" in hist_ids
    assert "gemini-1.5-flash" in hist_ids

    assert registry.get_foundation_model("gemini-1.5-pro").lifecycle_status == LifecycleStatus.RETIRED
    assert registry.is_model_eligible("gemini-1.5-pro") is False


def test_preview_opt_in_behavior():
    """Regression test: Preview models must be excluded by default and only included on explicit opt-in."""
    # Default: preview models excluded
    default_models = registry.list_models(include_deprecated=False, include_preview=False)
    default_ids = {m.model_id for m in default_models}
    assert "gemini-3.1-pro-preview" not in default_ids
    assert registry.is_model_eligible("gemini-3.1-pro-preview", include_preview=False) is False

    # Explicit opt-in: verified preview models become eligible
    preview_models = registry.list_models(include_deprecated=False, include_preview=True)
    preview_ids = {m.model_id for m in preview_models}
    assert "gemini-3.1-pro-preview" in preview_ids
    assert registry.is_model_eligible("gemini-3.1-pro-preview", include_preview=True) is True

    # Unverified models with missing pricing remain ineligible even with include_preview=True
    assert registry.is_model_eligible("gemini-2.5-pro", include_preview=True) is False
    assert registry.is_model_eligible("grok-3", include_preview=True) is False


def test_exact_model_ids_and_pricing_freshness():
    """Regression test: All 21 active GA models have exact IDs, non-zero pricing, and valid audit dates."""
    active_models = registry.list_active_models()
    assert len(active_models) == 21
    for m in active_models:
        assert m.pricing.is_known is True
        assert m.pricing.input_cost_per_m is not None and m.pricing.input_cost_per_m > 0
        assert m.pricing.output_cost_per_m is not None and m.pricing.output_cost_per_m > 0
        assert m.pricing.is_stale is False
        assert m.context_window_tokens >= 64000
        assert m.last_audit_date in ["2026-10-26", "2026-10-27", "2026-10-28"]
        assert m.source_url.startswith("https://")


def test_both_model_comparison_stages_and_deltas():
    """Regression test: Compare prompt across original and optimized stages, verifying delta metrics."""
    orig_prompt = "Write a basic Python function to upload user avatars to AWS S3."
    opt_prompt = (
        "Write a robust, production-ready Python function to upload user avatars to AWS S3. "
        "Validate content types (PNG/JPEG only), enforce a 5MB size limit, generate secure UUID keys, "
        "and handle botocore ClientError exceptions gracefully."
    )

    orig_report = comparison_engine.compare_prompt(orig_prompt, category=ProductCategory.FOUNDATION_MODEL)
    opt_report = comparison_engine.compare_prompt(opt_prompt, category=ProductCategory.FOUNDATION_MODEL)

    assert len(orig_report.ranked_models) == 21
    assert len(opt_report.ranked_models) == 21

    orig_top = orig_report.ranked_models[0]
    opt_top = opt_report.ranked_models[0]

    # Verify deltas can be computed properly
    tok_delta = opt_top.token_count - orig_top.token_count
    cost_delta = (opt_top.estimated_cost_usd or 0.0) - (orig_top.estimated_cost_usd or 0.0)
    assert tok_delta > 0, "Optimized prompt must have higher token count due to guardrails"
    assert cost_delta >= 0, "Optimized prompt cost delta must be non-negative"


# ---------------------------------------------------------------------------
# 3. Stale Pricing and Unverified Rejection Tests
# ---------------------------------------------------------------------------

def test_stale_pricing_and_unverified_exclusion():
    # 1. Model with stale pricing is excluded from default recommendation pool
    stale_model = ModelMetadata(
        model_id="test-stale-pricing-model",
        display_name="Test Stale Model",
        provider="openai",
        family="test",
        context_window_tokens=128000,
        max_output_tokens=4096,
        pricing=ModelPricing(
            input_cost_per_m=1.0,
            output_cost_per_m=2.0,
            is_stale=True  # Stale pricing flag
        ),
        tokenizer_name="cl100k_base",
        lifecycle_status=LifecycleStatus.ACTIVE
    )
    registry.register_model(stale_model)
    try:
        assert registry.is_model_eligible("test-stale-pricing-model") is False
        active_list = [m.model_id for m in registry.list_models(include_deprecated=False)]
        assert "test-stale-pricing-model" not in active_list
    finally:
        if "test-stale-pricing-model" in registry._models:
            del registry._models["test-stale-pricing-model"]

    # 2. Model with unverified lifecycle is excluded from default recommendation pool
    unverified_model = ModelMetadata(
        model_id="test-unverified-model",
        display_name="Test Unverified Model",
        provider="anthropic",
        family="test",
        context_window_tokens=128000,
        max_output_tokens=4096,
        pricing=ModelPricing(input_cost_per_m=1.0, output_cost_per_m=2.0),
        tokenizer_name="cl100k_base",
        lifecycle_status=LifecycleStatus.UNVERIFIED
    )
    registry.register_model(unverified_model)
    try:
        assert registry.is_model_eligible("test-unverified-model") is False
        active_list = [m.model_id for m in registry.list_models(include_deprecated=False)]
        assert "test-unverified-model" not in active_list
    finally:
        if "test-unverified-model" in registry._models:
            del registry._models["test-unverified-model"]


# ---------------------------------------------------------------------------
# 4. Category Separation & Product Catalogues
# ---------------------------------------------------------------------------

def test_category_separation_and_catalogues():
    # 1. Foundation models do not contain IDEs or App Builders
    f_models = registry.list_models()
    f_ids = {m.model_id for m in f_models}
    assert "cursor" not in f_ids
    assert "v0-dev" not in f_ids

    # 2. IDE catalogue contains verified coding assistants
    ides = registry.list_ides()
    assert len(ides) == 4
    ide_ids = {i.product_id for i in ides}
    assert "cursor" in ide_ids
    assert "windsurf" in ide_ids
    assert "github-copilot" in ide_ids
    assert "google-antigravity" in ide_ids
    assert all(i.category == ProductCategory.IDE_ASSISTANT for i in ides)
    assert all(i.availability == ProductAvailability.GENERALLY_AVAILABLE for i in ides)
    assert all(i.last_audit_date == "2026-10-26" for i in ides)

    # 3. App Builder catalogue contains verified platforms
    builders = registry.list_app_builders()
    assert len(builders) == 4
    builder_ids = {b.product_id for b in builders}
    assert "v0-dev" in builder_ids
    assert "bolt-new" in builder_ids
    assert "lovable-dev" in builder_ids
    assert "replit-agent" in builder_ids
    assert all(b.category == ProductCategory.APP_BUILDER for b in builders)
    assert all(b.availability == ProductAvailability.GENERALLY_AVAILABLE for b in builders)
    assert all(b.last_audit_date == "2026-10-26" for b in builders)

    # 4. Product eligibility checks
    assert registry.is_model_eligible("cursor", category=ProductCategory.IDE_ASSISTANT) is True
    assert registry.is_model_eligible("cursor", category=ProductCategory.FOUNDATION_MODEL) is False
    assert registry.is_model_eligible("v0-dev", category=ProductCategory.APP_BUILDER) is True
    assert registry.is_model_eligible("v0-dev", category=ProductCategory.FOUNDATION_MODEL) is False


# ---------------------------------------------------------------------------
# 5. Local Tokenizer Adapters Tests (Exact vs Approximate vs Unsupported)
# ---------------------------------------------------------------------------

def test_tokenizer_adapters_accuracy_and_provenance():
    test_prompt = (
        "Write a Python function to implement quicksort with in-place partitioning "
        "and explain its asymptotic time complexity."
    )

    openai_tok = get_tokenizer_adapter("gpt-5.5")
    gemini_tok = get_tokenizer_adapter("gemini-3.8-flash")
    claude_tok = get_tokenizer_adapter("claude-sonnet-5-5")
    grok_tok = get_tokenizer_adapter("grok-4.7")
    deepseek_tok = get_tokenizer_adapter("deepseek-v4-pro")

    # OpenAI exact count via tiktoken
    res_openai = openai_tok.count_tokens(test_prompt)
    assert res_openai.is_exact is True
    assert res_openai.token_count_method == "exact"
    assert res_openai.token_count_confidence == 1.0
    assert res_openai.tokenizer_name == "o200k_base"
    assert res_openai.token_count > 0
    assert res_openai.token_count_disclaimer != ""

    # Google Gemini approximate count
    res_gemini = gemini_tok.count_tokens(test_prompt)
    assert res_gemini.is_exact is False
    assert res_gemini.token_count_method == "approximate"
    assert res_gemini.token_count_confidence == 0.90
    assert "gemini" in res_gemini.tokenizer_name
    assert "approximate" in res_gemini.token_count_disclaimer.lower()

    # Anthropic Claude approximate count
    res_claude = claude_tok.count_tokens(test_prompt)
    assert res_claude.is_exact is False
    assert res_claude.token_count_method == "approximate"
    assert res_claude.token_count_confidence == 0.90
    assert "claude" in res_claude.tokenizer_name
    assert "approximate" in res_claude.token_count_disclaimer.lower()

    # xAI Grok approximate count
    res_grok = grok_tok.count_tokens(test_prompt)
    assert res_grok.is_exact is False
    assert res_grok.token_count_method == "approximate"
    assert res_grok.token_count_confidence == 0.90

    # DeepSeek approximate count
    res_ds = deepseek_tok.count_tokens(test_prompt)
    assert res_ds.is_exact is False
    assert res_ds.token_count_method == "approximate"
    assert res_ds.token_count_confidence == 0.90

    # Unsupported adapter fallback
    unsupported = get_tokenizer_adapter("unknown-custom-architecture-99")
    assert isinstance(unsupported, UnsupportedTokenizerAdapter)
    res_unsup = unsupported.count_tokens(test_prompt)
    assert res_unsup.token_count_method == "unsupported"
    assert res_unsup.token_count_confidence == 0.50


# ---------------------------------------------------------------------------
# 6. Pricing & Cost Calculations (No zero-cost fabrication)
# ---------------------------------------------------------------------------

def test_cost_calculation_freshness_and_explicit_status():
    m = registry.get_foundation_model("gpt-5.5")
    assert m is not None

    cost = calculate_model_cost(model=m, input_tokens=1000, estimated_output_tokens=500)
    assert cost.pricing_status == "known"
    assert cost.input_cost_usd is not None
    assert cost.output_cost_usd is not None
    assert cost.total_estimated_cost_usd is not None
    assert cost.total_estimated_cost_usd > 0
    assert cost.pricing_effective_date == "2026-04-23"

    # Unpriced model handling
    unpriced = ModelMetadata(
        model_id="unpriced-test-model",
        display_name="Unpriced Model",
        provider="custom",
        family="custom",
        context_window_tokens=128000,
        max_output_tokens=4096,
        pricing=ModelPricing(input_cost_per_m=None, output_cost_per_m=None, is_known=False),
        tokenizer_name="cl100k_base"
    )
    cost_unpriced = calculate_model_cost(model=unpriced, input_tokens=1000, estimated_output_tokens=500)
    assert cost_unpriced.pricing_status == "unknown"
    assert cost_unpriced.total_estimated_cost_usd is None


# ---------------------------------------------------------------------------
# 7. Multi-Criteria Ranking: Foundation Models
# ---------------------------------------------------------------------------

def test_foundation_model_ranking_wsm_and_topsis():
    test_prompt = "Build a scalable REST API in FastAPI with PostgreSQL, Redis caching, and Docker support."

    # 1. Test Weighted Sum Ranking
    report_wsm = comparison_engine.compare_prompt(
        prompt=test_prompt,
        category=ProductCategory.FOUNDATION_MODEL,
        method=RankingMethod.WEIGHTED_SUM,
        preset=RankingPreset.BALANCED
    )

    assert report_wsm.category == "foundation_model"
    assert report_wsm.ranking_method == "weighted_sum"
    assert len(report_wsm.ranked_models) == 21
    assert all(r.lifecycle_status == "active" for r in report_wsm.ranked_models)
    assert all(r.score_type == "heuristic_recommendation_score" for r in report_wsm.ranked_models)

    # Strictly monotonic sequential ranks
    ranks_wsm = [r.rank for r in report_wsm.ranked_models]
    assert ranks_wsm == list(range(1, 22))

    # Descending scores
    scores_wsm = [r.score for r in report_wsm.ranked_models]
    assert scores_wsm == sorted(scores_wsm, reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores_wsm)

    # 2. Test TOPSIS Ranking
    report_topsis = comparison_engine.compare_prompt(
        prompt=test_prompt,
        category=ProductCategory.FOUNDATION_MODEL,
        method=RankingMethod.TOPSIS,
        preset=RankingPreset.BALANCED
    )

    assert report_topsis.ranking_method == "topsis"
    ranks_topsis = [r.rank for r in report_topsis.ranked_models]
    assert ranks_topsis == list(range(1, 22))

    # 3. Cost-optimized preset favors affordable models
    report_cost = comparison_engine.compare_prompt(
        prompt=test_prompt,
        category=ProductCategory.FOUNDATION_MODEL,
        preset=RankingPreset.COST_OPTIMIZED
    )
    top_cost_model = report_cost.ranked_models[0].model_id
    assert top_cost_model in ["gpt-6-luna", "claude-haiku-5-5", "deepseek-flash", "gemini-3.5-flash-lite", "gpt-5-mini", "gemini-3.8-flash"]

    # 4. Quality-optimized preset favors frontier models
    report_quality = comparison_engine.compare_prompt(
        prompt=test_prompt,
        category=ProductCategory.FOUNDATION_MODEL,
        preset=RankingPreset.QUALITY_OPTIMIZED
    )
    top_quality_model = report_quality.ranked_models[0].model_id
    assert top_quality_model in ["deepseek-v4-pro", "gpt-6-astra", "claude-fable-5-1", "claude-opus-5-5", "claude-sonnet-5-5", "gpt-5.5-pro", "gemini-4-argon", "gpt-5.5"]


# ---------------------------------------------------------------------------
# 8. Missing Price Penalty in Ranking Tests
# ---------------------------------------------------------------------------

def test_missing_price_penalty_in_ranking():
    """
    Ensures models with missing or unverified pricing receive maximum cost penalties
    and are never treated as free or lowest cost.
    """
    candidates = [
        CandidateEvaluation(
            model_id="known-expensive",
            display_name="Known Expensive",
            provider="openai",
            token_count=100,
            token_count_method="exact",
            suitability_score=0.90,
            total_cost_usd=0.05,
            input_cost_usd=0.01,
            output_cost_usd=0.04,
            context_window_tokens=128000,
            pricing_status="known"
        ),
        CandidateEvaluation(
            model_id="known-cheap",
            display_name="Known Cheap",
            provider="google",
            token_count=100,
            token_count_method="approximate",
            suitability_score=0.88,
            total_cost_usd=0.0005,
            input_cost_usd=0.0001,
            output_cost_usd=0.0004,
            context_window_tokens=128000,
            pricing_status="known"
        ),
        CandidateEvaluation(
            model_id="unpriced-model",
            display_name="Unpriced Model",
            provider="custom",
            token_count=100,
            token_count_method="approximate",
            suitability_score=0.89,
            total_cost_usd=None,
            input_cost_usd=None,
            output_cost_usd=None,
            context_window_tokens=128000,
            pricing_status="unknown"
        )
    ]

    # In WSM:
    ranked_wsm = rank_models_weighted_sum(candidates, weights={"suitability": 0.3, "cost": 0.6, "context": 0.1})
    unpriced_rank = next(r for r in ranked_wsm if r.model_id == "unpriced-model")
    cheap_rank = next(r for r in ranked_wsm if r.model_id == "known-cheap")

    # The unpriced model must NOT outrank the verified cheap model on cost
    assert cheap_rank.score > unpriced_rank.score
    assert "Pricing metadata unverified" in unpriced_rank.reasoning

    # In TOPSIS:
    ranked_topsis = rank_models_topsis(candidates, weights={"suitability": 0.3, "cost": 0.6, "context": 0.1})
    unpriced_t_rank = next(r for r in ranked_topsis if r.model_id == "unpriced-model")
    cheap_t_rank = next(r for r in ranked_topsis if r.model_id == "known-cheap")
    assert cheap_t_rank.score > unpriced_t_rank.score


# ---------------------------------------------------------------------------
# 9. Multi-Criteria Ranking: IDEs & Coding Assistants
# ---------------------------------------------------------------------------

def test_ide_assistant_ranking():
    prompt = "Modify an existing TypeScript monorepo to add an authenticated API endpoint, update tests, and explain the affected files."

    # 1. WSM Balanced Ranking
    report_wsm = comparison_engine.compare_prompt(
        prompt=prompt,
        category=ProductCategory.IDE_ASSISTANT,
        method=RankingMethod.WEIGHTED_SUM,
        preset="balanced"
    )

    assert report_wsm.category == "ide_assistant"
    assert report_wsm.ranked_products is not None
    assert len(report_wsm.ranked_products) == 4
    assert len(report_wsm.ranked_models) == 0

    ranks = [rp.rank for rp in report_wsm.ranked_products]
    assert ranks == [1, 2, 3, 4]

    product_ids = {rp.product_id for rp in report_wsm.ranked_products}
    assert product_ids == {"cursor", "windsurf", "github-copilot", "google-antigravity"}
    assert all(rp.score_type == "heuristic_recommendation_score" for rp in report_wsm.ranked_products)

    # 2. TOPSIS Agentic Power Ranking
    report_topsis = comparison_engine.compare_prompt(
        prompt=prompt,
        category=ProductCategory.IDE_ASSISTANT,
        method=RankingMethod.TOPSIS,
        preset="agentic_power"
    )
    assert report_topsis.ranking_method == "topsis"
    assert report_topsis.ranked_products is not None
    assert len(report_topsis.ranked_products) == 4
    top_agentic = report_topsis.ranked_products[0].product_id
    assert top_agentic in ["google-antigravity", "cursor", "windsurf"]


# ---------------------------------------------------------------------------
# 10. Multi-Criteria Ranking: AI App Builders
# ---------------------------------------------------------------------------

def test_app_builder_ranking():
    prompt = "Build a full-stack event registration application with authentication, PostgreSQL database, admin dashboards, and deployment."

    # 1. Full-stack preset favors Lovable / Replit
    report_fs = comparison_engine.compare_prompt(
        prompt=prompt,
        category=ProductCategory.APP_BUILDER,
        method=RankingMethod.WEIGHTED_SUM,
        preset="full_stack"
    )

    assert report_fs.category == "app_builder"
    assert report_fs.ranked_products is not None
    assert len(report_fs.ranked_products) == 4
    assert len(report_fs.ranked_models) == 0

    top_builder = report_fs.ranked_products[0].product_id
    assert top_builder in ["lovable-dev", "replit-agent"]
    assert all(rp.score_type == "heuristic_recommendation_score" for rp in report_fs.ranked_products)

    # 2. Frontend UI prompt favors v0
    ui_prompt = "Generate a responsive React landing page with Tailwind CSS, hero banner, dark mode, and pricing tables."
    report_ui = comparison_engine.compare_prompt(
        prompt=ui_prompt,
        category=ProductCategory.APP_BUILDER,
        method=RankingMethod.WEIGHTED_SUM,
        preset="frontend_ui"
    )
    assert report_ui.ranked_products[0].product_id in ["v0-dev", "lovable-dev"]


# ---------------------------------------------------------------------------
# 11. Lifecycle Filtering Enforcement (Default vs Historical Access)
# ---------------------------------------------------------------------------

def test_retired_models_excluded_from_ranking():
    # If user requests retired or unverified models in default mode (include_deprecated=False),
    # they must be filtered out by shared eligibility policy
    report_default = comparison_engine.compare_prompt(
        prompt="Write a quicksort in C++",
        category=ProductCategory.FOUNDATION_MODEL,
        model_ids=["gpt-4-turbo", "gemini-2.5-pro", "grok-3", "gpt-5.5", "gemini-1.5-pro"],
        include_deprecated=False
    )
    ranked_ids = [r.model_id for r in report_default.ranked_models]
    assert "gpt-5.5" in ranked_ids
    assert "gpt-4-turbo" not in ranked_ids
    assert "gemini-2.5-pro" not in ranked_ids
    assert "grok-3" not in ranked_ids
    assert "gemini-1.5-pro" not in ranked_ids

    # If user explicitly requests historical access (include_deprecated=True),
    # historical models can be evaluated
    report_historical = comparison_engine.compare_prompt(
        prompt="Write a quicksort in C++",
        category=ProductCategory.FOUNDATION_MODEL,
        model_ids=["gpt-4-turbo", "gemini-2.5-pro", "grok-3", "gpt-5.5", "gemini-1.5-pro"],
        include_deprecated=True
    )
    hist_ranked_ids = [r.model_id for r in report_historical.ranked_models]
    assert "gpt-5.5" in hist_ranked_ids
    assert "gpt-4-turbo" in hist_ranked_ids
    assert "gemini-2.5-pro" in hist_ranked_ids
    assert "grok-3" in hist_ranked_ids
    assert "gemini-1.5-pro" in hist_ranked_ids


# ---------------------------------------------------------------------------
# 12. Consistency Between GET /models and POST /compare-models
# ---------------------------------------------------------------------------

def test_consistency_between_get_models_and_compare_models(client):
    # GET /models returns the active foundation models
    res_get = client.get("/models")
    assert res_get.status_code == 200
    get_models = res_get.json()
    get_ids = sorted([m["model_id"] for m in get_models])

    # POST /compare-models default pool should match exactly
    res_post = client.post("/compare-models", json={
        "prompt": "Evaluate API authentication.",
        "category": "foundation_model"
    })
    assert res_post.status_code == 200
    post_data = res_post.json()
    post_ids = sorted([m["model_id"] for m in post_data["ranked_models"]])

    assert get_ids == post_ids, f"Mismatch between GET /models ({get_ids}) and POST /compare-models ({post_ids})"


# ---------------------------------------------------------------------------
# 13. Provenance & Offline Guarantees
# ---------------------------------------------------------------------------

def test_provenance_and_offline_execution():
    test_prompt = "Analyze database query performance."
    report = comparison_engine.compare_prompt(test_prompt)

    assert "100% local execution" in report.provenance_declarations["offline_execution"]
    assert "No third-party quality benchmarks" in report.provenance_declarations["benchmarks"]
    assert "heuristic" in report.provenance_declarations["scoring_interpretation"].lower()

    for rm in report.ranked_models:
        assert rm.latency_status == "unavailable"
        assert "not fabricate" in rm.benchmark_status.lower()
        assert rm.score_type == "heuristic_recommendation_score"
        assert "heuristic" in rm.reasoning.lower()


# ---------------------------------------------------------------------------
# 14. Strict 100% Offline Network Block Verification
# ---------------------------------------------------------------------------

def test_strict_offline_zero_network_calls():
    """
    Blocks all outbound socket connections and HTTP calls.
    Verifies that model comparison, token counting, cost calculation,
    and ranking execute 100% locally with zero external network attempts.
    """
    def block_connect(*args, **kwargs):
        raise RuntimeError("CRITICAL ERROR: Outbound network call attempted during offline comparison!")

    with patch.object(socket.socket, "connect", side_effect=block_connect):
        test_prompt = "Analyze application security vulnerabilities in JWT signature validation."
        report = comparison_engine.compare_prompt(
            prompt=test_prompt,
            category=ProductCategory.FOUNDATION_MODEL,
            method=RankingMethod.WEIGHTED_SUM,
            preset=RankingPreset.BALANCED
        )
        assert len(report.ranked_models) == 21
        assert report.ranked_models[0].score > 0
        assert report.model_details["gpt-5.5"].token_count > 0


# ---------------------------------------------------------------------------
# 15. FastAPI Endpoint Integration Tests
# ---------------------------------------------------------------------------

def test_fastapi_models_endpoint_categories(client):
    # 1. Default GET /models returns active foundation models
    res = client.get("/models")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 21
    assert all(m["category"] == "foundation_model" for m in data)
    assert all(m["lifecycle_status"] == "active" for m in data)
    assert all(m["last_audit_date"] in ["2026-10-26", "2026-10-27", "2026-10-28"] for m in data)

    # 2. GET /models?category=ide_assistant returns 4 IDEs
    res_ide = client.get("/models?category=ide_assistant")
    assert res_ide.status_code == 200
    data_ide = res_ide.json()
    assert len(data_ide) == 4
    assert all(m["category"] == "ide_assistant" for m in data_ide)

    # 3. GET /models?category=app_builder returns 4 App Builders
    res_b = client.get("/models?category=app_builder")
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert len(data_b) == 4
    assert all(m["category"] == "app_builder" for m in data_b)

    # 4. Unknown category returns 400
    res_bad = client.get("/models?category=invalid_category")
    assert res_bad.status_code == 400


def test_fastapi_get_specific_items(client):
    # Active foundation models
    res_fm = client.get("/models/gpt-5.5")
    assert res_fm.status_code == 200
    assert res_fm.json()["model_id"] == "gpt-5.5"
    assert res_fm.json()["lifecycle_status"] == "active"
    assert res_fm.json()["last_audit_date"] in ["2026-10-26", "2026-10-27", "2026-10-28"]

    # Gemini 3.8 Flash
    res_gem = client.get("/models/gemini-3.8-flash")
    assert res_gem.status_code == 200
    assert res_gem.json()["lifecycle_status"] == "active"

    # Claude Sonnet 5.5
    res_claude = client.get("/models/claude-sonnet-5-5")
    assert res_claude.status_code == 200
    assert res_claude.json()["lifecycle_status"] == "active"
    assert res_claude.json()["input_cost_per_m"] == 2.00
    assert res_claude.json()["output_cost_per_m"] == 10.00

    # xAI Grok 4.7 canonical and alias
    res_grok = client.get("/models/grok-4.7")
    assert res_grok.status_code == 200
    assert res_grok.json()["model_id"] == "grok-4.7"

    res_grok_alias = client.get("/models/grok-4-7")
    assert res_grok_alias.status_code == 200
    assert res_grok_alias.json()["model_id"] == "grok-4.7"

    # Preview foundation model
    res_prev = client.get("/models/gemini-3.1-pro-preview")
    assert res_prev.status_code == 200
    assert res_prev.json()["lifecycle_status"] == "preview"

    # Preview alias resolution
    res_prev_alias = client.get("/models/gemini-3.1-pro")
    assert res_prev_alias.status_code == 200
    assert res_prev_alias.json()["model_id"] == "gemini-3.1-pro-preview"

    # Retired legacy model
    res_ret = client.get("/models/gemini-1.5-pro")
    assert res_ret.status_code == 200
    assert res_ret.json()["lifecycle_status"] == "retired"

    # Unverified foundation model
    res_unv = client.get("/models/gemini-2.5-pro")
    assert res_unv.status_code == 200
    assert res_unv.json()["lifecycle_status"] == "unverified"
    assert "model_id" in res_unv.json()["unverified_fields"]

    # Deprecated model
    res_dep = client.get("/models/gpt-4-turbo")
    assert res_dep.status_code == 200
    assert res_dep.json()["lifecycle_status"] == "deprecated"

    # IDE item
    res_ide = client.get("/models/cursor")
    assert res_ide.status_code == 200
    assert res_ide.json()["category"] == "ide_assistant"

    # App builder item
    res_app = client.get("/models/v0-dev")
    assert res_app.status_code == 200
    assert res_app.json()["category"] == "app_builder"

    # Nonexistent ID returns 404
    res_404 = client.get("/models/nonexistent-item-12345")
    assert res_404.status_code == 404


def test_fastapi_compare_models_endpoint_all_categories(client):
    # 1. Foundation model comparison
    payload_fm = {
        "prompt": "Review this FastAPI authentication design for security flaws and recommend fixes.",
        "category": "foundation_model",
        "method": "weighted_sum",
        "preset": "balanced"
    }
    res_fm = client.post("/compare-models", json=payload_fm)
    assert res_fm.status_code == 200
    data_fm = res_fm.json()
    assert data_fm["category"] == "foundation_model"
    assert len(data_fm["ranked_models"]) == 21
    assert data_fm["ranked_products"] is None
    assert all(r["score_type"] == "heuristic_recommendation_score" for r in data_fm["ranked_models"])
    assert "token_count_method" in data_fm["ranked_models"][0]
    assert "token_count_confidence" in data_fm["ranked_models"][0]

    # 2. IDE assistant comparison
    payload_ide = {
        "prompt": "Modify an existing TypeScript monorepo to add an authenticated API endpoint, update tests, and explain the affected files.",
        "category": "ide_assistant",
        "method": "weighted_sum",
        "preset": "balanced"
    }
    res_ide = client.post("/compare-models", json=payload_ide)
    assert res_ide.status_code == 200
    data_ide = res_ide.json()
    assert data_ide["category"] == "ide_assistant"
    assert len(data_ide["ranked_models"]) == 0
    assert len(data_ide["ranked_products"]) == 4
    assert data_ide["ranked_products"][0]["rank"] == 1
    assert all(r["score_type"] == "heuristic_recommendation_score" for r in data_ide["ranked_products"])

    # 3. App Builder comparison
    payload_builder = {
        "prompt": "Build a full-stack event registration application with authentication, PostgreSQL, admin dashboards, and deployment.",
        "category": "app_builder",
        "method": "weighted_sum",
        "preset": "full_stack"
    }
    res_builder = client.post("/compare-models", json=payload_builder)
    assert res_builder.status_code == 200
    data_builder = res_builder.json()
    assert data_builder["category"] == "app_builder"
    assert len(data_builder["ranked_models"]) == 0
    assert len(data_builder["ranked_products"]) == 4
    assert data_builder["ranked_products"][0]["rank"] == 1

    # 4. Unsupported category returns 422 (Pydantic validation error)
    res_bad_cat = client.post("/compare-models", json={"prompt": "Test", "category": "invalid_cat"})
    assert res_bad_cat.status_code == 422


# ---------------------------------------------------------------------------
# 16. Phase 8 Catalogue Integrity & Canonical Aliases Tests
# ---------------------------------------------------------------------------

def test_phase8_model_catalogue_integrity_and_aliases():
    """
    Phase 8 Catalogue Audit & Integrity:
    1. Verifies exact canonical public identifiers from official docs (e.g. grok-4.7, grok-4.3).
    2. Verifies alias resolution for hyphenated legacy IDs (grok-4-7 -> grok-4.7).
    3. Verifies canonical preview identifier (gemini-3.1-pro-preview) and alias resolution (gemini-3.1-pro).
    4. Verifies duplicate gemini-3.1-pro is removed from PREVIEW_MODELS dictionary keys.
    5. Verifies verified Claude Sonnet 5.5 pricing at $2.00/$10.00.
    6. Verifies verified Claude Fable 5.1 presence in active GA pool.
    7. Verifies official retirement of deepseek-chat and deepseek-reasoner on 2026-07-24.
    8. Verifies maximum output token limits (128k Claude, 384k DeepSeek).
    9. Verifies zero unverified fields in the default active recommendation pool.
    """
    # 1. Canonical xAI IDs
    active_models = registry.list_active_models()
    active_ids = {m.model_id for m in active_models}
    assert "grok-4.7" in active_ids
    assert "grok-4.3" in active_ids
    assert "grok-4-7" not in active_ids
    assert "grok-4-3" not in active_ids

    # 2. Alias resolution
    m_grok = registry.get_foundation_model("grok-4-7")
    assert m_grok is not None
    assert m_grok.model_id == "grok-4.7"

    m_grok_43 = registry.get_foundation_model("grok-4-3")
    assert m_grok_43 is not None
    assert m_grok_43.model_id == "grok-4.3"

    # 3. Preview canonical ID and alias resolution
    m_gemini_prev = registry.get_foundation_model("gemini-3.1-pro")
    assert m_gemini_prev is not None
    assert m_gemini_prev.model_id == "gemini-3.1-pro-preview"
    assert m_gemini_prev.lifecycle_status == LifecycleStatus.PREVIEW

    # 4. Duplicate removal from PREVIEW_MODELS
    from analyzers.model_comparison.registry import PREVIEW_MODELS
    assert "gemini-3.1-pro-preview" in PREVIEW_MODELS
    assert "gemini-3.1-pro" not in PREVIEW_MODELS

    # 5. Claude Sonnet 5.5 verified pricing
    sonnet = registry.get_foundation_model("claude-sonnet-5-5")
    assert sonnet.pricing.input_cost_per_m == 2.00
    assert sonnet.pricing.output_cost_per_m == 10.00
    assert sonnet.max_output_tokens == 128_000

    # 6. Claude Fable 5.1 verified active model
    fable = registry.get_foundation_model("claude-fable-5-1")
    assert fable is not None
    assert fable.lifecycle_status == LifecycleStatus.ACTIVE
    assert fable.pricing.input_cost_per_m == 10.00
    assert fable.pricing.output_cost_per_m == 50.00
    assert fable.context_window_tokens == 1_000_000
    assert fable.max_output_tokens == 128_000

    # 7. DeepSeek retired models
    ds_chat = registry.get_foundation_model("deepseek-chat")
    assert ds_chat.lifecycle_status == LifecycleStatus.RETIRED
    assert ds_chat.retirement_date == "2026-07-24"
    assert ds_chat.replacement_model_id == "deepseek-flash"
    assert registry.is_model_eligible("deepseek-chat") is False

    ds_r1 = registry.get_foundation_model("deepseek-reasoner")
    assert ds_r1.lifecycle_status == LifecycleStatus.RETIRED
    assert ds_r1.retirement_date == "2026-07-24"
    assert ds_r1.replacement_model_id == "deepseek-v4-pro"
    assert registry.is_model_eligible("deepseek-reasoner") is False

    # 8. Output token limits
    opus = registry.get_foundation_model("claude-opus-5-5")
    assert opus.max_output_tokens == 128_000
    dsv4 = registry.get_foundation_model("deepseek-v4-pro")
    assert dsv4.max_output_tokens == 384_000

    # 9. Default recommendation pool integrity: strictly 21 active models, 0 unverified critical fields
    default_pool = registry.list_models(include_deprecated=False, include_preview=False)
    assert len(default_pool) == 21
    for m in default_pool:
        assert m.lifecycle_status == LifecycleStatus.ACTIVE
        assert not m.unverified_fields, f"Active model {m.model_id} has unverified fields: {m.unverified_fields}"
        assert m.pricing.is_known is True
        assert m.pricing.is_stale is False
        assert m.pricing.input_cost_per_m is not None and m.pricing.input_cost_per_m > 0
        assert m.pricing.output_cost_per_m is not None and m.pricing.output_cost_per_m > 0
