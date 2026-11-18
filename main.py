import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from auth.router import router as auth_router
from marketplace.router import router as marketplace_router
from db.database import check_db_health
from integrations.zero_g import zero_g_optimizer, ZeroGOptimizationResult
from integrations.zero_g.sanitizer import detect_sensitive_data

logger = logging.getLogger("guardvane.main")

app = FastAPI(
    title="Guardvane AI",
    description="Confidential AI security platform and decentralized marketplace powered by 0G Private Computer and Arkiv.",
    version="2.0.0"
)

# Mount authentication and marketplace routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(marketplace_router, prefix="/marketplace", tags=["Marketplace"])

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

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


@app.get("/", response_class=FileResponse)
def home():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        content={
            "message": "Guardvane AI Platform is running",
            "dashboard_ui": "/dashboard",
            "marketplace_api": "/marketplace/services",
            "health": "/health",
            "docs": "/docs"
        }
    )


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


# ---------------------------------------------------------------------------
# Request Schemas for 0G AI Scanning & Optimization
# ---------------------------------------------------------------------------

class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    analysis_mode: Optional[str] = "both"


class OptimizePromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    analysis_mode: Optional[str] = "both"
    fallback_to_local: Optional[bool] = False
    bypass_cache: Optional[bool] = False
    temperature: Optional[float] = 0.3
    max_tokens: Optional[int] = 2000


@app.post("/analyze")
def analyze(data: PromptRequest):
    """
    Scans a prompt for secrets and adversarial injection vectors using
    0G Private Computer AI reasoning and regex credential sanitization.
    """
    s_data = detect_sensitive_data(data.prompt)

    injection_detected = False
    confidence = 0.0
    risk_category = "Low Risk"
    detected_risks = []

    if zero_g_optimizer.client.is_configured:
        try:
            zg_res = zero_g_optimizer.optimize(
                prompt=data.prompt,
                bypass_cache=False,
                temperature=0.2,
                max_tokens=1000,
            )
            findings = zg_res.security_analysis_findings or []
            if findings:
                risk_category = zg_res.overall_risk or "Medium Risk"
                for f in findings:
                    vuln = f.get("vulnerability", "")
                    if "injection" in vuln.lower() or "override" in vuln.lower() or "jailbreak" in vuln.lower():
                        injection_detected = True
                        confidence = float(f.get("confidence", 0.85))
                    detected_risks.append(vuln)
        except Exception as e:
            logger.warning(f"0G analyze scan exception: {e}")

    if s_data.get("has_sensitive_data"):
        risk_category = "Critical Risk"

    return {
        "status": "success",
        "prompt_security": {
            "is_injection_detected": injection_detected,
            "malicious_probability": confidence if injection_detected else 0.05,
            "confidence_score": confidence,
            "risk_category": risk_category,
        },
        "sensitive_data": s_data,
        "application_risks": {
            "detected_risks": detected_risks,
        },
        "task_classification": {
            "predicted_category": "AI Security Prompt",
            "confidence": 0.95,
        },
    }


@app.post("/optimize")
def optimize(data: OptimizePromptRequest, x_user_id: Optional[str] = Header(None)):
    """
    Performs primary security reasoning, threat modeling, and prompt hardening on 0G Private Computer.
    """
    try:
        opt_res: ZeroGOptimizationResult = zero_g_optimizer.optimize(
            prompt=data.prompt,
            user_id=x_user_id,
            bypass_cache=bool(data.bypass_cache),
            temperature=data.temperature if data.temperature is not None else 0.3,
            max_tokens=data.max_tokens or 2000,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"0G Private Computer reasoning failed: {str(exc)}"
        )

    s_data = detect_sensitive_data(data.prompt)

    findings_list = []
    for f in (opt_res.security_analysis_findings or []):
        if isinstance(f, dict):
            findings_list.append({
                "vulnerability": f.get("vulnerability", ""),
                "severity": f.get("severity", "medium"),
                "confidence": float(f.get("confidence", 0.8)),
                "evidence": f.get("evidence", ""),
                "attack_scenario": f.get("attack_scenario", ""),
                "explanation": f.get("explanation", ""),
                "recommendation": f.get("recommendation", ""),
            })

    structured = {
        "task_understanding": opt_res.task_understanding or {
            "application_type": "AI Security Task",
            "user_intent": "Hardening prompt against adversarial extraction",
            "technologies": ["0G Private Computer"],
        },
        "security_analysis": {
            "overall_risk": opt_res.overall_risk or "Low",
            "findings": findings_list,
        },
        "missing_security_requirements": opt_res.missing_requirements_addressed or [],
        "hardened_prompt": opt_res.optimized_prompt,
        "changes_made": opt_res.changes_made or [],
        "assumptions": opt_res.assumptions or [],
        "remaining_risks": opt_res.remaining_risks or [],
    }

    return {
        "status": opt_res.status,
        "original_prompt": opt_res.original_prompt,
        "sanitized_prompt": opt_res.sanitized_prompt,
        "optimized_prompt": opt_res.optimized_prompt,
        "hardened_prompt": opt_res.optimized_prompt,
        "security_analysis": {
            "sensitive_data": s_data,
            "findings": findings_list,
            "overall_risk": opt_res.overall_risk,
        },
        "structured_reasoning": structured,
        "reasoning": {
            "structured": structured,
            "contextual_summary": getattr(opt_res.reasoning, "contextual_summary", "") if opt_res.reasoning else "",
            "risk_explanations": getattr(opt_res.reasoning, "risk_explanations", {}) if opt_res.reasoning else {},
            "task_understanding": structured["task_understanding"],
            "security_analysis": structured["security_analysis"],
            "changes_made": structured["changes_made"],
            "assumptions": structured["assumptions"],
            "remaining_risks": structured["remaining_risks"],
        },
        "applied_hardening_rules": opt_res.applied_hardening_rules,
        "changes_summary": opt_res.changes_summary,
        "missing_requirements_addressed": opt_res.missing_requirements_addressed,
        "preserved_intent": opt_res.preserved_intent,
        "engine": opt_res.engine,
        "fallback_used": opt_res.fallback_used,
        "fallback_reason": opt_res.fallback_reason,
        "zero_g_metadata": opt_res.metadata,
        "disclaimer": opt_res.disclaimer,
        "error": opt_res.error_message,
    }
