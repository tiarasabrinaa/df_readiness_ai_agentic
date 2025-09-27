from datetime import datetime
from typing import Any, Dict, List

def generate_email_template(manager) -> str:
    ctx = getattr(manager, "context", {}) or {}
    
    user_profile = ctx.get("user_profile", {})
    if isinstance(user_profile, str):
        user_profile = {}
    
    profile = user_profile
    
    level = (
        ctx.get("assessment_level")
        or (ctx.get("final_evaluation", {}) or {}).get("assessment_level")
        or "N/A"
    )
    total_questions = len(ctx.get("test_questions", []) or [])
    answered = len(ctx.get("test_answers", []) or [])

    evaluation: Dict[str, Any] = ctx.get("final_evaluation", {}) or {}
    score = evaluation.get("overall_score", "N/A")
    readiness = (
        evaluation.get("readiness_percent")
        or evaluation.get("readiness_percentage")
        or evaluation.get("readiness_level")
        or evaluation.get("overall_level")
        or "N/A"
    )
    
    # risk assessment
    risk_assessment = evaluation.get("risk_assessment", {})
    if isinstance(risk_assessment, str):
        risk_assessment = {}
    risk_level = risk_assessment.get("risk_level", "N/A") if isinstance(risk_assessment, dict) else "N/A"
    priority_score = risk_assessment.get("priority_score", "N/A") if isinstance(risk_assessment, dict) else "N/A"
    critical_gaps = risk_assessment.get("critical_gaps", []) if isinstance(risk_assessment, dict) else []
    if not isinstance(critical_gaps, list):
        critical_gaps = []

    # strengths and weaknesses
    strengths = evaluation.get("strengths", []) or []
    if not isinstance(strengths, list):
        strengths = []
    weaknesses = evaluation.get("weaknesses", []) or []
    if not isinstance(weaknesses, list):
        weaknesses = []

    # detailed analysis
    analysis_summary = evaluation.get("detailed_analysis", "")
    next_steps = evaluation.get("next_steps", "") or evaluation.get("improvement_roadmap", "")

    def render_list(items) -> str:
        if not items:
            return "<li>-</li>"
        if isinstance(items, dict):
            inner = ""
            for k, v in items.items():
                inner += f"<li><strong>{k}</strong></li>"
                inner += "<ul>"
                if isinstance(v, (list, tuple)):
                    inner += "".join(f"<li>{str(it)}</li>" for it in v)
                else:
                    inner += f"<li>{str(v)}</li>"
                inner += "</ul>"
            return inner
        if isinstance(items, (list, tuple)):
            return "".join(f"<li>{str(it)}</li>" for it in items) or "<li>-</li>"
        return f"<li>{str(items)}</li>"

    recommendations = evaluation.get("recommendations", []) or []
    rec_html = ""
    
    if isinstance(recommendations, list) and recommendations:
        # Handle new structure with category and items
        for rec in recommendations:
            if isinstance(rec, dict) and "category" in rec and "items" in rec:
                rec_html += f"<li><strong>{rec['category']}</strong><ul>"
                for item in rec['items']:
                    rec_html += f"<li>{str(item)}</li>"
                rec_html += "</ul></li>"
            elif isinstance(rec, str):
                rec_html += f"<li>{rec}</li>"
            else:
                rec_html += f"<li>{str(rec)}</li>"
    elif isinstance(recommendations, dict):
        rec_html = "".join(
            f"<li><strong>{cat}</strong><ul>{render_list(recs)}</ul></li>"
            for cat, recs in recommendations.items()
        )
    else:
        rec_html = render_list(recommendations)
    
    if not rec_html:
        rec_html = "<li>Lakukan pelatihan keamanan siber secara berkala</li><li>Implementasikan kebijakan keamanan yang komprehensif</li><li>Audit sistem keamanan secara rutin</li>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8" />
        <title>Digital Forensics Readiness Report</title>
        <style>
        body {{ font-family: Arial, sans-serif; color: #1f2937; margin: 0; padding: 0; }}
        .container {{ max-width: 720px; margin: 0 auto; padding: 24px; }}
        .card {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        h1 {{ color: #111827; }}
        h2 {{ color: #111827; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; }}
        .badge {{ display: inline-block; background: #eef2ff; color: #3730a3; padding: 4px 10px; border-radius: 9999px; font-size: 12px; margin-right: 8px; }}
        ul {{ padding-left: 20px; }}
        .muted {{ color: #6b7280; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .section {{ margin-top: 20px; }}
        </style>
    </head>
    <body>
    <div class="container">
        <div class="card">
        <h1>Digital Forensics Readiness Report</h1>
        <p class="muted">Comprehensive analysis of your organization's digital forensics readiness based on industry best practices.</p>

        <div class="section">
        <h2>Status</h2>
        <span class="badge">Assessment Complete</span>
        <span class="badge">Level: {level}</span>
        </div>

        <div class="section">
        <h2>Key Metrics</h2>
        <ul>
            <li>Overall Score: {score}</li>
            <li>Readiness: {readiness}</li>
            <li>Completion: {answered}/{total_questions} questions</li>
        </ul>
        </div>

        <div class="section">
        <h2>Risk Assessment</h2>
        <ul>
            <li>Risk Level: {risk_level}</li>
            <li>Priority Score: {priority_score}</li>
            <li>Critical Gaps:</li>
            <ul>
            {render_list(critical_gaps)}
            </ul>
        </ul>
        </div>

        <div class="section">
        <h2>Action Plan & Recommendations</h2>
        <ul>
            {rec_html}
        </ul>
        </div>

        <div class="section">
        <h2>Strengths & Areas for Improvement</h2>
        <h3>Key Strengths</h3>
        <ul>
            {render_list(strengths)}
        </ul>
        <h3>Areas for Improvement</h3>
        <ul>
            {render_list(weaknesses)}
        </ul>
        </div>

        <div class="section">
        <h2>Detailed Analysis</h2>
        <h3>Analysis Summary</h3>
        <p>{analysis_summary or 'Assessment telah diselesaikan dengan baik. Organisasi menunjukkan komitmen terhadap peningkatan keamanan digital.'}
        </p>
        <h3>Next Steps</h3>
        <p>{next_steps or 'Lanjutkan dengan implementasi rekomendasi yang diberikan dan lakukan evaluasi berkala.'}
        </p>
        </div>

        <div class="section">
        <h2>Organization Profile</h2>
        <div class="grid">
            <div>
            <ul>
                <li>Industry: {profile.get('industry', '-')}</li>
                <li>Company Size: {profile.get('company_size', '-')}</li>
                <li>Position: {profile.get('position', '-')}</li>
                <li>Experience: {profile.get('experience', '-')}</li>
                <li>Security Incidents: {profile.get('security_incidents', '-')}</li>
            </ul>
            </div>
            <div>
            <ul>
                <li>Security Team: {profile.get('has_security_team', '-')}</li>
                <li>Recent Audit: {profile.get('recent_audit', '-')}</li>
                <li>Sensitive Data: {profile.get('sensitive_data', '-')}</li>
                <li>Security Solution: {profile.get('security_solution', '-')}</li>
                <li>Training Frequency: {profile.get('training_frequency', '-')}</li>
            </ul>
            </div>
        </div>
        </div>

        <div class="section">
        <p class="muted">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        </div>
    </div>
    </body>
    </html>
    """
    return html