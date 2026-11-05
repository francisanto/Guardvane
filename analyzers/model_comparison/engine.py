"""
PromptShield AI — Multi-Category Comparison Engine Orchestrator.
================================================================
Coordinates local feature extraction, task classification, token counting,
cost estimation, suitability scoring, and multi-criteria ranking across:
- Category A: Foundation Models (OpenAI GPT, Google Gemini, Anthropic Claude, xAI Grok)
- Category B: IDEs & Coding Assistants (Cursor, Windsurf, GitHub Copilot, Google Antigravity)
- Category C: AI App Builders (Vercel v0, Bolt.new, Lovable, Replit)

Enforces complete offline execution without external API dependencies.
Maintains strict category separation: candidates from one category are never mixed
or ranked alongside candidates from another category.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from analyzers.model_comparison.registry import (
    ModelMetadata,
    IDEProductMetadata,
    AppBuilderMetadata,
    ProductCategory,
    ProductAvailability,
    LifecycleStatus,
    registry
)
from analyzers.model_comparison.tokenizer_adapters import get_tokenizer_adapter
from analyzers.model_comparison.feature_extractor import PromptFeatures, feature_extractor
from analyzers.model_comparison.task_classifier import TaskClassificationResult, task_classifier
from analyzers.model_comparison.cost_calculator import CostBreakdown, calculate_model_cost
from analyzers.model_comparison.suitability import calculate_suitability
from analyzers.model_comparison.ranker import (
    CandidateEvaluation,
    RankedModel,
    RankedProduct,
    RankingMethod,
    RankingPreset,
    rank_models,
    rank_products,
    validate_and_normalize_weights
)


@dataclass
class ModelComparisonDetails:
    """Detailed specifications and costing for a foundation model."""
    model_id: str
    display_name: str
    provider: str
    context_window_tokens: int
    token_count: int
    token_count_method: str  # "exact", "approximate", "unsupported"
    is_exact_token_count: bool
    estimated_output_tokens: int
    cost_breakdown: CostBreakdown
    suitability_score: float
    capabilities: List[str]
    strengths: List[str]
    provenance: Dict[str, str]
    lifecycle_status: str = "active"
    source_url: str = ""
    verification_date: str = "2026-10-26"
    last_audit_date: str = "2026-10-26"
    unverified_fields: List[str] = field(default_factory=list)
    token_count_confidence: float = 1.0
    token_count_disclaimer: str = ""


@dataclass
class ProductComparisonDetails:
    """Detailed specifications and pricing for an IDE or App Builder product."""
    product_id: str
    display_name: str
    vendor: str
    category: str
    availability: str
    pricing_tier_summary: str
    pricing_model: str
    free_tier: str
    paid_tiers: List[str]
    key_capabilities: List[str]
    context_or_stack_details: List[str]
    privacy_or_limitations: str
    description: str
    source_url: str
    verification_date: str
    provenance: Dict[str, str]
    last_audit_date: str = "2026-10-25"
    unverified_fields: List[str] = field(default_factory=list)


@dataclass
class ModelComparisonReport:
    """Unified report containing comparison results for the selected category."""
    prompt_text: str
    prompt_features: PromptFeatures
    task_classification: TaskClassificationResult
    ranking_method: str
    ranking_preset: str
    applied_weights: Dict[str, float]
    category: str = "foundation_model"
    ranked_models: List[RankedModel] = field(default_factory=list)
    model_details: Dict[str, ModelComparisonDetails] = field(default_factory=dict)
    ranked_products: Optional[List[RankedProduct]] = None
    product_details: Optional[Dict[str, ProductComparisonDetails]] = None
    provenance_declarations: Dict[str, str] = field(default_factory=dict)


class ModelComparisonEngine:
    """Orchestrates multi-category comparison, costing, and ranking."""

    def __init__(self):
        self.registry = registry
        self.feature_extractor = feature_extractor
        self.task_classifier = task_classifier

    def compare_prompt(
        self,
        prompt: str,
        category: ProductCategory = ProductCategory.FOUNDATION_MODEL,
        method: RankingMethod = RankingMethod.WEIGHTED_SUM,
        preset: Union[RankingPreset, str] = RankingPreset.BALANCED,
        custom_weights: Optional[Dict[str, float]] = None,
        model_ids: Optional[List[str]] = None,
        output_tokens_override: Optional[int] = None,
        include_deprecated: bool = False,
        include_preview: bool = False
    ) -> ModelComparisonReport:
        """
        Runs local prompt analysis, feature extraction, and multi-criteria ranking
        for the designated category (foundation_model, ide_assistant, or app_builder).
        """
        # 1. Feature Extraction (runs locally for all requests)
        features = self.feature_extractor.extract_features(prompt)
        output_tokens = output_tokens_override or features.estimated_output_tokens

        # 2. Local Task Classification (runs locally for all requests)
        task_res = self.task_classifier.classify_task(prompt)

        preset_str = preset.value if hasattr(preset, "value") else str(preset)

        # ===================================================================
        # ===================================================================
        # Category A: Foundation Models
        # ===================================================================
        if category == ProductCategory.FOUNDATION_MODEL:
            # Model Selection with single consistent registry snapshot
            if model_ids:
                target_models = []
                for mid in model_ids:
                    m = self.registry.get_foundation_model(mid)
                    if m and (include_deprecated or self.registry.is_model_eligible(m.model_id, category, include_preview=include_preview)):
                        target_models.append(m)
            else:
                target_models = self.registry.list_models(
                    include_deprecated=include_deprecated,
                    include_preview=include_preview
                )

            candidates: List[CandidateEvaluation] = []
            details_map: Dict[str, ModelComparisonDetails] = {}

            ranking_preset_enum = RankingPreset.BALANCED
            for p in RankingPreset:
                if p.value == preset_str:
                    ranking_preset_enum = p
                    break

            for model in target_models:
                adapter = get_tokenizer_adapter(model.model_id)
                tok_res = adapter.count_tokens(prompt)

                cost = calculate_model_cost(
                    model=model,
                    input_tokens=tok_res.token_count,
                    estimated_output_tokens=output_tokens
                )

                suitability = calculate_suitability(
                    model=model,
                    features=features,
                    predicted_task=task_res.predicted_category,
                    task_confidence=task_res.confidence,
                    task_result=task_res
                )

                candidates.append(CandidateEvaluation(
                    model_id=model.model_id,
                    display_name=model.display_name,
                    provider=model.provider,
                    token_count=tok_res.token_count,
                    token_count_method=tok_res.token_count_method,
                    suitability_score=suitability,
                    total_cost_usd=cost.total_estimated_cost_usd,
                    input_cost_usd=cost.input_cost_usd,
                    output_cost_usd=cost.output_cost_usd,
                    context_window_tokens=model.context_window_tokens,
                    lifecycle_status=model.lifecycle_status.value if hasattr(model.lifecycle_status, "value") else str(model.lifecycle_status),
                    latency_ms=None,
                    pricing_date=cost.pricing_effective_date,
                    pricing_status=cost.pricing_status,
                    estimated_output_tokens=output_tokens,
                    input_cost_per_m=model.pricing.input_cost_per_m,
                    output_cost_per_m=model.pricing.output_cost_per_m,
                    token_count_confidence=tok_res.token_count_confidence,
                    token_count_disclaimer=tok_res.token_count_disclaimer
                ))

                details_map[model.model_id] = ModelComparisonDetails(
                    model_id=model.model_id,
                    display_name=model.display_name,
                    provider=model.provider,
                    context_window_tokens=model.context_window_tokens,
                    token_count=tok_res.token_count,
                    token_count_method=tok_res.token_count_method,
                    is_exact_token_count=tok_res.is_exact,
                    estimated_output_tokens=output_tokens,
                    cost_breakdown=cost,
                    suitability_score=suitability,
                    capabilities=model.capabilities,
                    strengths=model.strengths,
                    provenance={
                        "token_count": "exact_local_bpe" if tok_res.is_exact else "calibrated_offline_estimate",
                        "input_cost": "calculated_from_token_count_and_published_pricing" if cost.pricing_status == "known" else "unknown_unverified",
                        "output_cost": "estimated_from_heuristic_response_length_and_published_pricing" if cost.pricing_status == "known" else "unknown_unverified",
                        "task_category": f"predicted_by_local_ml_model (confidence: {task_res.confidence})",
                        "suitability_score": "heuristically_predicted_from_structural_features_and_task_alignment",
                        "latency": "unavailable (not measured or fabricated offline)",
                        "external_benchmark_scores": "unavailable (not fabricated offline)",
                        "billing_note": tok_res.billing_disclaimer
                    },
                    lifecycle_status=model.lifecycle_status.value if hasattr(model.lifecycle_status, "value") else str(model.lifecycle_status),
                    source_url=model.source_url,
                    verification_date=model.verification_date,
                    last_audit_date=getattr(model, "last_audit_date", "2026-10-26"),
                    unverified_fields=getattr(model, "unverified_fields", []),
                    token_count_confidence=tok_res.token_count_confidence,
                    token_count_disclaimer=tok_res.token_count_disclaimer
                )

            ranked = rank_models(
                candidates=candidates,
                method=method,
                preset=ranking_preset_enum,
                custom_weights=custom_weights
            )

            effective_weights = validate_and_normalize_weights(custom_weights, ranking_preset_enum)

            return ModelComparisonReport(
                prompt_text=prompt,
                prompt_features=features,
                task_classification=task_res,
                ranking_method=method.value if hasattr(method, "value") else str(method),
                ranking_preset=preset_str,
                applied_weights=effective_weights,
                category=category.value,
                ranked_models=ranked,
                model_details=details_map,
                ranked_products=None,
                product_details=None,
                provenance_declarations={
                    "offline_execution": "100% local execution; zero prompts transmitted to external model APIs.",
                    "token_counting": "OpenAI token counts are exact via official tiktoken; Gemini, Claude, and Grok token counts are calibrated offline estimates.",
                    "pricing_data": "Public pricing snapshot verified against official documentation (audited 2026-10-25; USD per 1M tokens).",
                    "benchmarks": "No third-party quality benchmarks or live latencies are fabricated.",
                    "scoring_interpretation": "Scores represent relative multi-criteria heuristic recommendation trade-offs [0.0, 1.0], not measured answer quality or latency."
                }
            )

        # ===================================================================
        # Category B: IDEs & Coding Assistants
        # ===================================================================
        elif category == ProductCategory.IDE_ASSISTANT:
            if model_ids:
                target_ides = []
                for pid in model_ids:
                    ide = self.registry.get_ide(pid)
                    if ide and (include_deprecated or self.registry.is_model_eligible(ide.product_id, category)):
                        target_ides.append(ide)
            else:
                target_ides = self.registry.list_ides(include_discontinued=include_deprecated)

            ranked_products_list, effective_weights = rank_products(
                products=target_ides,
                category="ide_assistant",
                method=method,
                preset=preset_str,
                custom_weights=custom_weights,
                prompt_text=prompt
            )

            product_details_map: Dict[str, ProductComparisonDetails] = {}
            for ide in target_ides:
                product_details_map[ide.product_id] = ProductComparisonDetails(
                    product_id=ide.product_id,
                    display_name=ide.display_name,
                    vendor=ide.vendor,
                    category="ide_assistant",
                    availability=ide.availability.value,
                    pricing_tier_summary=ide.pricing_tier_summary,
                    pricing_model=ide.pricing_model,
                    free_tier=ide.free_tier,
                    paid_tiers=ide.paid_tiers,
                    key_capabilities=ide.key_capabilities,
                    context_or_stack_details=ide.context_features,
                    privacy_or_limitations=ide.privacy_statement,
                    description=ide.description,
                    source_url=ide.source_url,
                    verification_date=ide.verification_date,
                    last_audit_date=getattr(ide, "last_audit_date", "2026-10-25"),
                    unverified_fields=getattr(ide, "unverified_fields", []),
                    provenance={
                        "category": "ide_assistant",
                        "scoring_method": f"Multi-criteria {method.value.upper()} on documented IDE capabilities and prompt relevance",
                        "execution_type": "Offline capability-based ranking; no remote IDE or model calls",
                        "pricing_source": "Official vendor pricing documentation (audited 2026-10-25)",
                        "privacy_verification": ide.privacy_statement
                    }
                )

            return ModelComparisonReport(
                prompt_text=prompt,
                prompt_features=features,
                task_classification=task_res,
                ranking_method=method.value if hasattr(method, "value") else str(method),
                ranking_preset=preset_str,
                applied_weights=effective_weights,
                category="ide_assistant",
                ranked_models=[],
                model_details={},
                ranked_products=ranked_products_list,
                product_details=product_details_map,
                provenance_declarations={
                    "category": "ide_assistant",
                    "offline_execution": "100% local execution; evaluates developer environments and coding assistants without API calls.",
                    "criteria_evaluated": "Multi-file agent autonomy, codebase indexing, terminal execution, model flexibility, ecosystem integration, privacy controls, and plan affordability.",
                    "product_distinction": "IDEs are evaluated as development environments, not as raw foundation models.",
                    "scoring_interpretation": "Relative multi-criteria heuristic recommendation score [0.0, 1.0] reflecting suitability for requested coding tasks."
                }
            )

        # ===================================================================
        # Category C: AI App Builders
        # ===================================================================
        elif category == ProductCategory.APP_BUILDER:
            if model_ids:
                target_builders = []
                for pid in model_ids:
                    b = self.registry.get_app_builder(pid)
                    if b and (include_deprecated or self.registry.is_model_eligible(b.product_id, category)):
                        target_builders.append(b)
            else:
                target_builders = self.registry.list_app_builders(include_discontinued=include_deprecated)

            ranked_products_list, effective_weights = rank_products(
                products=target_builders,
                category="app_builder",
                method=method,
                preset=preset_str,
                custom_weights=custom_weights,
                prompt_text=prompt
            )

            builder_details_map: Dict[str, ProductComparisonDetails] = {}
            for b in target_builders:
                builder_details_map[b.product_id] = ProductComparisonDetails(
                    product_id=b.product_id,
                    display_name=b.display_name,
                    vendor=b.vendor,
                    category="app_builder",
                    availability=b.availability.value,
                    pricing_tier_summary=b.pricing_tier_summary,
                    pricing_model=b.pricing_model,
                    free_tier=b.free_tier,
                    paid_tiers=b.paid_tiers,
                    key_capabilities=b.key_capabilities,
                    context_or_stack_details=b.primary_stacks,
                    privacy_or_limitations="; ".join(b.documented_limitations),
                    description=b.description,
                    source_url=b.source_url,
                    verification_date=b.verification_date,
                    last_audit_date=getattr(b, "last_audit_date", "2026-10-25"),
                    unverified_fields=getattr(b, "unverified_fields", []),
                    provenance={
                        "category": "app_builder",
                        "scoring_method": f"Multi-criteria {method.value.upper()} on documented platform capabilities and prompt requirement alignment",
                        "execution_type": "Offline platform evaluation; no remote builder or code generation calls",
                        "pricing_source": "Official vendor pricing documentation (audited 2026-10-25)",
                        "code_export_verification": b.source_code_export
                    }
                )

            return ModelComparisonReport(
                prompt_text=prompt,
                prompt_features=features,
                task_classification=task_res,
                ranking_method=method.value if hasattr(method, "value") else str(method),
                ranking_preset=preset_str,
                applied_weights=effective_weights,
                category="app_builder",
                ranked_models=[],
                model_details={},
                ranked_products=ranked_products_list,
                product_details=builder_details_map,
                provenance_declarations={
                    "category": "app_builder",
                    "offline_execution": "100% local execution; evaluates full-stack and UI application builders without external generation API calls.",
                    "criteria_evaluated": "Full-stack backend/database support, frontend UI quality, deployment/hosting, GitHub exportability, autonomous debugging, and pricing accessibility.",
                    "product_distinction": "App builders are evaluated as end-to-end application scaffolding platforms, not as raw foundation models.",
                    "scoring_interpretation": "Relative multi-criteria score reflecting suitability for requested software stack and application architecture."
                }
            )

        else:
            raise ValueError(f"Unsupported product category '{category}'. Valid: foundation_model, ide_assistant, app_builder.")


# Singleton engine instance
comparison_engine = ModelComparisonEngine()
