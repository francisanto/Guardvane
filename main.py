from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from models.schemas import (
    PromptRequest,
    ModelComparisonRequest,
    ModelComparisonResponse,
    ModelMetadataSchema,
    ProductCategoryEnum,
    OptimizePromptRequest,
    OptimizePromptResponse,
    ZeroGMetadataSchema,
    ZeroGReasoningSchema,
)
from analyzers.prompt_analyzer import analyze_prompt
from integrations.zero_g import zero_g_optimizer, ZeroGOptimizationResult
from analyzers.model_comparison import (
    comparison_engine,
    registry,
    RankingMethod,
    RankingPreset,
    ProductCategory,
    LifecycleStatus,
    ProductAvailability,
    ModelMetadata,
    IDEProductMetadata,
    AppBuilderMetadata
)
from auth.router import router as auth_router
from marketplace.router import router as marketplace_router
from db.database import check_db_health

app = FastAPI(
    title="Guardvane AI",
    description="Multi-model AI security analysis, local model comparison, and decentralized security marketplace connecting customers with automated AI defenses and human security experts.",
    version="1.5.0"
)

# Mount authentication and marketplace routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(marketplace_router, prefix="/marketplace", tags=["Marketplace"])

# Static files directory
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = STATIC_DIR / "favicon.ico"
    if icon_path.exists():
        return FileResponse(str(icon_path), media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def apple_touch_icon():
    icon_path = STATIC_DIR / "apple-touch-icon.png"
    if icon_path.exists():
        return FileResponse(str(icon_path), media_type="image/png")
    raise HTTPException(status_code=404, detail="Apple touch icon not found")


@app.get("/")
def home():
    return {
        "message": "PromptShield AI backend is running",
        "dashboard_ui": "/dashboard",
        "marketplace_api": "/marketplace/services",
        "health": "/health",
        "docs": "/docs"
    }


@app.get("/health/db")
def health_db():
    health = check_db_health()
    status_code = 200 if health["database_reachable"] else 503
    return JSONResponse(status_code=status_code, content=health)


@app.get("/health")
def health_summary():
    db_health = check_db_health()
    return {
        "status": "healthy" if db_health["database_reachable"] else "degraded",
        "service": "Guardvane AI Security Platform",
        "database": db_health
    }


@app.get("/dashboard", response_class=FileResponse)
@app.get("/dashboard/{full_path:path}", response_class=FileResponse)
@app.get("/console", response_class=FileResponse)
def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>Guardvane Console</h1><p>UI loading error</p>")


@app.post("/analyze")
def analyze(data: PromptRequest):
    mode = data.analysis_mode.value if hasattr(data.analysis_mode, "value") else str(data.analysis_mode)
    return analyze_prompt(data.prompt, analysis_mode=mode)


@app.post("/optimize", response_model=OptimizePromptResponse)
def optimize(data: OptimizePromptRequest):
    """
    Optimizes a user prompt using 0G Private Computer AI reasoning and optimization,
    grounded by PromptShield's local ML security classifiers and sensitive data detection.

    1. Runs local PromptShield security analysis (Prompt Injection, 15 Application Risks, Secrets).
    2. Sanitizes any detected credentials prior to inference to prevent secret leakage.
    3. Performs contextual reasoning via 0G Private Computer on detected attack surfaces.
    4. Synthesizes a structured, production-ready, hardened prompt preserving developer intent.
    5. Returns the optimized prompt, security analysis, reasoning breakdown, and 0G execution metadata.
    """
    mode = data.analysis_mode.value if hasattr(data.analysis_mode, "value") else str(data.analysis_mode)

    # 1. Run local PromptShield analysis
    analysis = analyze_prompt(data.prompt, analysis_mode=mode)

    # 2. Run 0G optimization (which internally handles secret sanitization, reasoning, and fallback)
    try:
        opt_res: ZeroGOptimizationResult = zero_g_optimizer.optimize(
            prompt=data.prompt,
            security_analysis=analysis,
            fallback_to_local=data.fallback_to_local if data.fallback_to_local is not None else True,
            temperature=data.temperature if data.temperature is not None else 0.5,
            max_tokens=data.max_tokens,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"0G Private Computer optimization failed: {str(exc)}"
        )

    reasoning_schema = None
    if opt_res.reasoning:
        reasoning_schema = ZeroGReasoningSchema(
            contextual_summary=opt_res.reasoning.contextual_summary,
            risk_explanations=opt_res.reasoning.risk_explanations,
            missing_security_requirements=opt_res.reasoning.missing_security_requirements,
            intent_preservation_notes=opt_res.reasoning.intent_preservation_notes,
            justifications=opt_res.reasoning.justifications,
        )

    metadata_schema = None
    if opt_res.metadata:
        metadata_schema = ZeroGMetadataSchema(
            model=opt_res.metadata.get("model"),
            response_id=opt_res.metadata.get("response_id"),
            request_id=opt_res.metadata.get("request_id"),
            usage=opt_res.metadata.get("usage"),
            finish_reason=opt_res.metadata.get("finish_reason"),
            http_status=opt_res.metadata.get("http_status"),
        )

    return OptimizePromptResponse(
        status="fallback" if opt_res.fallback_used else "success",
        original_prompt=opt_res.original_prompt,
        sanitized_prompt=opt_res.sanitized_prompt,
        optimized_prompt=opt_res.optimized_prompt,
        security_analysis=analysis,
        reasoning=reasoning_schema,
        applied_hardening_rules=opt_res.applied_hardening_rules,
        changes_summary=opt_res.changes_summary,
        missing_requirements_addressed=opt_res.missing_requirements_addressed,
        preserved_intent=opt_res.preserved_intent,
        engine=opt_res.engine,
        fallback_used=opt_res.fallback_used,
        fallback_reason=opt_res.fallback_reason,
        zero_g_metadata=metadata_schema,
        disclaimer=opt_res.disclaimer,
    )


# ---------------------------------------------------------------------------
# Multi-Category Comparison & Catalogue Endpoints
# ---------------------------------------------------------------------------

@app.get("/models", response_model=List[ModelMetadataSchema])
def list_models(
    category: Optional[str] = Query(None, description="Filter by category: 'foundation_model', 'ide_assistant', or 'app_builder' (default: foundation_model)"),
    provider: Optional[str] = Query(None, description="Filter by provider or vendor: openai, google, anthropic, xai, anysphere, codeium, vercel, etc."),
    include_deprecated: bool = Query(False, description="Whether to include deprecated or retired items (default: False)"),
    include_preview: bool = Query(False, description="Whether to include preview models (default: False)"),
    status: Optional[str] = Query(None, description="Filter by specific lifecycle status or product availability")
):
    """
    Returns registered systems across Foundation Models, IDEs, or AI App Builders.
    By default (category=None), returns active foundation models for backward compatibility.
    """
    cat_str = (category or "foundation_model").lower().strip()

    if cat_str in {"foundation_model", "model", "models"}:
        lifecycle_enum = None
        if status:
            try:
                lifecycle_enum = LifecycleStatus(status.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status '{status}'. Valid values for foundation models: active, deprecated, retired, preview, unverified."
                )

        models = registry.list_models(
            provider=provider,
            include_deprecated=include_deprecated,
            include_preview=include_preview,
            lifecycle_status=lifecycle_enum
        )

        return [
            ModelMetadataSchema(
                model_id=m.model_id,
                display_name=m.display_name,
                provider=m.provider,
                family=m.family,
                category="foundation_model",
                context_window_tokens=m.context_window_tokens,
                max_output_tokens=m.max_output_tokens,
                input_cost_per_m=m.pricing.input_cost_per_m,
                output_cost_per_m=m.pricing.output_cost_per_m,
                pricing_effective_date=m.pricing.pricing_effective_date,
                currency=m.pricing.currency,
                tokenizer_name=m.tokenizer_name,
                capabilities=m.capabilities,
                strengths=m.strengths,
                description=m.description,
                lifecycle_status=m.lifecycle_status.value if hasattr(m.lifecycle_status, "value") else str(m.lifecycle_status),
                source_url=m.source_url,
                verification_date=m.verification_date,
                deprecation_date=m.deprecation_date,
                replacement_model_id=m.replacement_model_id,
                last_audit_date=getattr(m, "last_audit_date", "2026-10-26"),
                unverified_fields=getattr(m, "unverified_fields", []),
                is_stale_pricing=m.pricing.is_stale,
                pricing_verification_date=m.pricing.pricing_verification_date
            )
            for m in models
        ]

    elif cat_str in {"ide_assistant", "ide", "ides"}:
        ides = registry.list_ides(include_discontinued=include_deprecated)
        if provider:
            ides = [i for i in ides if provider.lower() in i.vendor.lower()]
        if status:
            ides = [i for i in ides if i.availability.value == status.lower()]

        return [
            ModelMetadataSchema(
                model_id=i.product_id,
                display_name=i.display_name,
                provider=i.vendor,
                family="ide_assistant",
                category="ide_assistant",
                description=i.description,
                capabilities=i.key_capabilities,
                strengths=i.context_features,
                lifecycle_status=i.availability.value,
                source_url=i.source_url,
                verification_date=i.verification_date,
                pricing_tier_summary=i.pricing_tier_summary,
                supported_options=i.supported_models,
                last_audit_date=getattr(i, "last_audit_date", "2026-10-26"),
                unverified_fields=getattr(i, "unverified_fields", [])
            )
            for i in ides
        ]

    elif cat_str in {"app_builder", "builder", "builders"}:
        builders = registry.list_app_builders(include_discontinued=include_deprecated)
        if provider:
            builders = [b for b in builders if provider.lower() in b.vendor.lower()]
        if status:
            builders = [b for b in builders if b.availability.value == status.lower()]

        return [
            ModelMetadataSchema(
                model_id=b.product_id,
                display_name=b.display_name,
                provider=b.vendor,
                family="app_builder",
                category="app_builder",
                description=b.description,
                capabilities=b.key_capabilities,
                strengths=b.primary_stacks,
                lifecycle_status=b.availability.value,
                source_url=b.source_url,
                verification_date=b.verification_date,
                pricing_tier_summary=b.pricing_tier_summary,
                supported_options=b.supported_backends,
                last_audit_date=getattr(b, "last_audit_date", "2026-10-26"),
                unverified_fields=getattr(b, "unverified_fields", [])
            )
            for b in builders
        ]

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Valid categories: 'foundation_model', 'ide_assistant', 'app_builder'."
        )


@app.get("/models/{model_id}", response_model=ModelMetadataSchema)
def get_model(model_id: str):
    """
    Returns metadata, lifecycle/availability status, and specifications for a registered item.
    Supports querying across foundation models (e.g. 'gpt-6-astra', 'gemini-4-argon'),
    IDEs (e.g. 'cursor', 'windsurf'), and app builders (e.g. 'v0-dev', 'lovable-dev').
    """
    item = registry.get_model(model_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Item '{model_id}' not found in registry. Check /models for registered IDs."
        )

    if isinstance(item, ModelMetadata):
        return ModelMetadataSchema(
            model_id=item.model_id,
            display_name=item.display_name,
            provider=item.provider,
            family=item.family,
            category="foundation_model",
            context_window_tokens=item.context_window_tokens,
            max_output_tokens=item.max_output_tokens,
            input_cost_per_m=item.pricing.input_cost_per_m,
            output_cost_per_m=item.pricing.output_cost_per_m,
            pricing_effective_date=item.pricing.pricing_effective_date,
            currency=item.pricing.currency,
            tokenizer_name=item.tokenizer_name,
            capabilities=item.capabilities,
            strengths=item.strengths,
            description=item.description,
            lifecycle_status=item.lifecycle_status.value if hasattr(item.lifecycle_status, "value") else str(item.lifecycle_status),
            source_url=item.source_url,
            verification_date=item.verification_date,
            deprecation_date=item.deprecation_date,
            replacement_model_id=item.replacement_model_id,
            last_audit_date=getattr(item, "last_audit_date", "2026-10-26"),
            unverified_fields=getattr(item, "unverified_fields", []),
            is_stale_pricing=item.pricing.is_stale,
            pricing_verification_date=item.pricing.pricing_verification_date
        )
    elif isinstance(item, IDEProductMetadata):
        return ModelMetadataSchema(
            model_id=item.product_id,
            display_name=item.display_name,
            provider=item.vendor,
            family="ide_assistant",
            category="ide_assistant",
            description=item.description,
            capabilities=item.key_capabilities,
            strengths=item.context_features,
            lifecycle_status=item.availability.value,
            source_url=item.source_url,
            verification_date=item.verification_date,
            pricing_tier_summary=item.pricing_tier_summary,
            supported_options=item.supported_models,
            last_audit_date=getattr(item, "last_audit_date", "2026-10-26"),
            unverified_fields=getattr(item, "unverified_fields", [])
        )
    elif isinstance(item, AppBuilderMetadata):
        return ModelMetadataSchema(
            model_id=item.product_id,
            display_name=item.display_name,
            provider=item.vendor,
            family="app_builder",
            category="app_builder",
            description=item.description,
            capabilities=item.key_capabilities,
            strengths=item.primary_stacks,
            lifecycle_status=item.availability.value,
            source_url=item.source_url,
            verification_date=item.verification_date,
            pricing_tier_summary=item.pricing_tier_summary,
            supported_options=item.supported_backends,
            last_audit_date=getattr(item, "last_audit_date", "2026-10-26"),
            unverified_fields=getattr(item, "unverified_fields", [])
        )
    else:
        raise HTTPException(status_code=500, detail="Unexpected metadata item type.")


@app.post("/compare-models", response_model=ModelComparisonResponse)
def compare_models_endpoint(req: ModelComparisonRequest):
    """
    Evaluates a prompt across registered candidates for the selected product category:
    - 'foundation_model': token counts, costs, suitability, and multi-criteria WSM / TOPSIS ranking.
    - 'ide_assistant': multi-file agentic capabilities, codebase indexing, terminal execution, and privacy.
    - 'app_builder': full-stack backend, database/auth support, UI generation, and code exportability.
    Executes 100% offline without transmitting prompts to external model or builder APIs.
    """
    cat_val = req.category.value if hasattr(req.category, "value") else str(req.category)
    method_val = req.method.value if hasattr(req.method, "value") else str(req.method)
    preset_val = req.preset.value if hasattr(req.preset, "value") else str(req.preset)

    try:
        category = ProductCategory(cat_val)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported category '{cat_val}'. Valid: foundation_model, ide_assistant, app_builder."
        )

    try:
        method = RankingMethod(method_val)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported ranking method '{method_val}'. Valid: weighted_sum, topsis."
        )

    report = comparison_engine.compare_prompt(
        prompt=req.prompt,
        category=category,
        method=method,
        preset=preset_val,
        custom_weights=req.custom_weights,
        model_ids=req.models,
        output_tokens_override=req.expected_output_tokens,
        include_deprecated=bool(req.include_deprecated),
        include_preview=bool(req.include_preview)
    )

    # 1. Format foundation model details if applicable
    model_details_dict = {}
    if report.model_details:
        for mid, d in report.model_details.items():
            model_details_dict[mid] = {
                "model_id": d.model_id,
                "display_name": d.display_name,
                "provider": d.provider,
                "context_window_tokens": d.context_window_tokens,
                "token_count": d.token_count,
                "token_count_method": d.token_count_method,
                "is_exact_token_count": d.is_exact_token_count,
                "estimated_output_tokens": d.estimated_output_tokens,
                "cost_breakdown": {
                    "input_tokens": d.cost_breakdown.input_tokens,
                    "estimated_output_tokens": d.cost_breakdown.estimated_output_tokens,
                    "input_cost_usd": d.cost_breakdown.input_cost_usd,
                    "output_cost_usd": d.cost_breakdown.output_cost_usd,
                    "total_estimated_cost_usd": d.cost_breakdown.total_estimated_cost_usd,
                    "input_cost_per_m": d.cost_breakdown.input_cost_per_m,
                    "output_cost_per_m": d.cost_breakdown.output_cost_per_m,
                    "pricing_effective_date": d.cost_breakdown.pricing_effective_date,
                    "currency": d.cost_breakdown.currency,
                    "pricing_status": d.cost_breakdown.pricing_status
                },
                "suitability_score": d.suitability_score,
                "capabilities": d.capabilities,
                "strengths": d.strengths,
                "provenance": d.provenance,
                "lifecycle_status": d.lifecycle_status,
                "source_url": d.source_url,
                "verification_date": d.verification_date,
                "last_audit_date": getattr(d, "last_audit_date", "2026-10-26"),
                "unverified_fields": getattr(d, "unverified_fields", []),
                "token_count_confidence": getattr(d, "token_count_confidence", 1.0),
                "token_count_disclaimer": getattr(d, "token_count_disclaimer", "")
            }

    ranked_models_list = []
    if report.ranked_models:
        for rm in report.ranked_models:
            ranked_models_list.append({
                "rank": rm.rank,
                "model_id": rm.model_id,
                "display_name": rm.display_name,
                "provider": rm.provider,
                "score": rm.score,
                "suitability_score": rm.suitability_score,
                "estimated_cost_usd": rm.estimated_cost_usd,
                "token_count": rm.token_count,
                "token_count_provenance": rm.token_count_provenance,
                "latency_status": rm.latency_status,
                "benchmark_status": rm.benchmark_status,
                "reasoning": rm.reasoning,
                "lifecycle_status": rm.lifecycle_status,
                "score_type": getattr(rm, "score_type", "heuristic_recommendation_score"),
                "score_disclaimer": getattr(rm, "score_disclaimer", None),
                "token_count_method": getattr(rm, "token_count_method", "exact"),
                "token_count_confidence": getattr(rm, "token_count_confidence", 1.0),
                "token_count_disclaimer": getattr(rm, "token_count_disclaimer", None)
            })

    # 2. Format product details if applicable
    product_details_dict = None
    if report.product_details:
        product_details_dict = {}
        for pid, pd in report.product_details.items():
            product_details_dict[pid] = {
                "product_id": pd.product_id,
                "display_name": pd.display_name,
                "vendor": pd.vendor,
                "category": pd.category,
                "availability": pd.availability,
                "pricing_tier_summary": pd.pricing_tier_summary,
                "pricing_model": pd.pricing_model,
                "free_tier": pd.free_tier,
                "paid_tiers": pd.paid_tiers,
                "key_capabilities": pd.key_capabilities,
                "context_or_stack_details": pd.context_or_stack_details,
                "privacy_or_limitations": pd.privacy_or_limitations,
                "description": pd.description,
                "source_url": pd.source_url,
                "verification_date": pd.verification_date,
                "last_audit_date": getattr(pd, "last_audit_date", "2026-10-26"),
                "unverified_fields": getattr(pd, "unverified_fields", []),
                "provenance": pd.provenance
            }

    ranked_products_list = None
    if report.ranked_products:
        ranked_products_list = [
            {
                "rank": rp.rank,
                "product_id": rp.product_id,
                "display_name": rp.display_name,
                "vendor": rp.vendor,
                "category": rp.category,
                "score": rp.score,
                "availability": rp.availability,
                "pricing_summary": rp.pricing_summary,
                "key_strengths": rp.key_strengths,
                "reasoning": rp.reasoning,
                "supported_models_or_stacks": rp.supported_models_or_stacks,
                "source_url": rp.source_url,
                "verification_date": rp.verification_date,
                "score_type": getattr(rp, "score_type", "heuristic_recommendation_score"),
                "score_disclaimer": getattr(rp, "score_disclaimer", None)
            }
            for rp in report.ranked_products
        ]

    return {
        "status": "success",
        "category": report.category,
        "prompt_text": report.prompt_text,
        "prompt_features": {
            "char_length": report.prompt_features.char_length,
            "word_count": report.prompt_features.word_count,
            "line_count": report.prompt_features.line_count,
            "code_proportion": report.prompt_features.code_proportion,
            "has_code_block": report.prompt_features.has_code_block,
            "complexity_score": report.prompt_features.complexity_score,
            "technical_keyword_density": report.prompt_features.technical_keyword_density,
            "security_sensitivity": report.prompt_features.security_sensitivity,
            "estimated_output_tokens": report.prompt_features.estimated_output_tokens,
            "detected_indicators": report.prompt_features.detected_indicators
        },
        "task_classification": {
            "predicted_category": report.task_classification.predicted_category,
            "confidence": report.task_classification.confidence,
            "category_probabilities": report.task_classification.category_probabilities,
            "model_source": report.task_classification.model_source,
            "is_low_confidence": report.task_classification.is_low_confidence,
            "top_categories": report.task_classification.top_categories,
            "confidence_status": report.task_classification.confidence_status
        },
        "ranking_method": report.ranking_method,
        "ranking_preset": report.ranking_preset,
        "applied_weights": report.applied_weights,
        "ranked_models": ranked_models_list,
        "model_details": model_details_dict,
        "ranked_products": ranked_products_list,
        "product_details": product_details_dict,
        "provenance_declarations": report.provenance_declarations
    }