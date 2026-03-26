"""
frontend.py — Streamlit frontend for PermitAgent.

Visual style inspired by FilmLA.com:
- Dark navy palette (#10131b, #202535, #3f4a6a)
- Cyan blue (#009cde) and lime green (#97d700) accents
- Nunito Sans typography
- Professional, institutional look
"""

import sys
import json
from datetime import datetime

import streamlit as st

sys.path.insert(0, ".")

from app.schemas import SceneInput, ScriptInput
from workflows.pipeline import run_pipeline, run_script_pipeline
from app.doc_generator import generate_single_scene_doc, generate_script_doc


def _parse_uploaded_file(uploaded_file) -> str:
    """Extract text from uploaded PDF, DOCX, TXT, FDX, or Fountain files."""
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".txt") or name.endswith(".fountain"):
            return uploaded_file.read().decode("utf-8", errors="replace")

        elif name.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(uploaded_file)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)

        elif name.endswith(".docx"):
            from docx import Document
            doc = Document(uploaded_file)
            return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

        elif name.endswith(".fdx"):
            # Final Draft XML format — extract paragraph text
            import xml.etree.ElementTree as ET
            tree = ET.parse(uploaded_file)
            root = tree.getroot()
            paragraphs = []
            for para in root.iter("Paragraph"):
                texts = []
                for text_elem in para.iter("Text"):
                    if text_elem.text:
                        texts.append(text_elem.text)
                if texts:
                    line = " ".join(texts).strip()
                    # Add slug line formatting
                    ptype = para.get("Type", "")
                    if ptype == "Scene Heading":
                        paragraphs.append(f"\n{line}\n")
                    elif ptype == "Character":
                        paragraphs.append(f"\n{line}")
                    elif ptype == "Dialogue":
                        paragraphs.append(line)
                    elif ptype == "Parenthetical":
                        paragraphs.append(f"({line})")
                    else:
                        paragraphs.append(line)
            return "\n".join(paragraphs)

        else:
            return uploaded_file.read().decode("utf-8", errors="replace")

    except Exception as e:
        st.error(f"Error reading file: {e}")
        return ""

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PermitAgent — Film Permit Intelligence",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — FilmLA-inspired theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:ital,wght@0,400;0,600;0,700;0,900;1,400&display=swap');

    /* === Global === */
    html, body, [class*="css"] {
        font-family: 'Nunito Sans', sans-serif;
    }

    /* === Main background === */
    .stApp {
        background-color: #10131b;
        color: #ffffff;
    }

    /* === Sidebar === */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #202535 0%, #10131b 100%);
        border-right: 2px solid #3f4a6a;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] label {
        color: #e0e0e0 !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stTextArea label,
    section[data-testid="stSidebar"] .stTextInput label {
        color: #009cde !important;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.75em;
        letter-spacing: 1px;
    }

    /* === Headings === */
    h1 {
        color: #ffffff !important;
        font-weight: 900 !important;
        letter-spacing: -0.5px;
    }
    h2, h3 {
        color: #009cde !important;
        font-weight: 900 !important;
    }
    h4, h5 {
        color: #97d700 !important;
        font-weight: 700 !important;
    }

    /* === Tabs === */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #202535;
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #9fa4b4;
        font-weight: 700;
        font-size: 0.85em;
        border-radius: 6px;
        padding: 8px 16px;
        background-color: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background-color: #3f4a6a !important;
        border-bottom: 3px solid #009cde !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #97d700;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background-color: #1a1e2e;
        border-radius: 0 0 8px 8px;
        padding: 20px;
    }

    /* === Metrics === */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #202535, #2a2f45);
        border: 1px solid #3f4a6a;
        border-radius: 8px;
        padding: 16px;
    }
    [data-testid="stMetricLabel"] {
        color: #9fa4b4 !important;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.7em !important;
        letter-spacing: 1px;
    }
    [data-testid="stMetricValue"] {
        color: #009cde !important;
        font-weight: 900 !important;
        font-size: 1.8em !important;
    }

    /* === Expanders === */
    .streamlit-expanderHeader {
        background-color: #202535 !important;
        border: 1px solid #3f4a6a !important;
        border-radius: 6px !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    .streamlit-expanderHeader:hover {
        border-color: #009cde !important;
        color: #97d700 !important;
    }
    .streamlit-expanderContent {
        background-color: #1a1e2e !important;
        border: 1px solid #3f4a6a !important;
        border-top: none !important;
        border-radius: 0 0 6px 6px !important;
    }

    /* === Buttons === */
    .stButton > button {
        background: linear-gradient(90deg, #009cde, #97d700) !important;
        color: #10131b !important;
        font-weight: 900 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 12px 24px !important;
        font-size: 1em !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #97d700, #009cde) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0, 156, 222, 0.4) !important;
    }

    /* === Progress bar === */
    .stProgress > div > div {
        background: linear-gradient(90deg, #009cde, #97d700) !important;
    }
    .stProgress {
        background-color: #3f4a6a;
    }

    /* === Info/Warning/Success boxes === */
    .stAlert {
        background-color: #202535 !important;
        border-radius: 6px !important;
    }

    /* === JSON viewer === */
    [data-testid="stJson"] {
        background-color: #202535 !important;
        border-radius: 8px;
    }

    /* === Dividers === */
    hr {
        border-color: #3f4a6a !important;
    }

    /* === Text styling === */
    .stMarkdown p {
        color: #e0e0e0;
        line-height: 1.6;
    }
    .stMarkdown strong {
        color: #ffffff;
    }
    .stMarkdown li {
        color: #e0e0e0;
    }
    .stCaption {
        color: #9fa4b4 !important;
    }

    /* === Custom card class === */
    .permit-card {
        background: linear-gradient(135deg, #202535, #2a2f45);
        border: 1px solid #3f4a6a;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .permit-card:hover {
        border-color: #009cde;
    }
    .risk-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85em;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .risk-low { background-color: #008009; color: #ffffff; }
    .risk-medium { background-color: #ffb81c; color: #10131b; }
    .risk-high { background-color: #aa1609; color: #ffffff; }
    .risk-critical { background-color: #a50050; color: #ffffff; }

    .stat-number {
        font-size: 3em;
        font-weight: 900;
        color: #009cde;
        line-height: 1;
    }
    .stat-label {
        color: #9fa4b4;
        font-size: 0.8em;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
    }

    /* === Hero banner === */
    .hero-banner {
        background: linear-gradient(135deg, #202535 0%, #3f4a6a 50%, #47819a 100%);
        border-radius: 12px;
        padding: 40px 30px;
        margin-bottom: 20px;
        text-align: center;
    }
    .hero-banner h1 {
        font-size: 2.5em !important;
        margin-bottom: 0 !important;
        text-shadow: 3px 3px 0 #009cde;
    }
    .hero-banner p {
        color: #9fa4b4;
        font-size: 1.1em;
        margin-top: 8px;
    }

    /* === Pipeline flow === */
    .pipeline-step {
        display: inline-block;
        background-color: #3f4a6a;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.8em;
        margin: 3px;
    }
    .pipeline-arrow {
        display: inline-block;
        color: #97d700;
        font-weight: 900;
        font-size: 1.2em;
        margin: 0 4px;
    }

    /* === Selectbox / inputs === */
    .stSelectbox > div > div,
    .stTextArea > div > div > textarea,
    .stTextInput > div > div > input {
        background-color: #202535 !important;
        color: #ffffff !important;
        border: 1px solid #3f4a6a !important;
        border-radius: 6px !important;
    }
    .stTextArea > div > div > textarea:focus,
    .stTextInput > div > div > input:focus {
        border-color: #009cde !important;
        box-shadow: 0 0 0 1px #009cde !important;
    }

    /* === Spinner === */
    .stSpinner > div {
        border-top-color: #009cde !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 10px 0 20px 0;">
        <h1 style="font-size: 1.8em; margin: 0; text-shadow: 2px 2px 0 #009cde;">
            🎬 PERMIT<span style="color: #97d700;">AGENT</span>
        </h1>
        <p style="color: #9fa4b4; font-size: 0.75em; text-transform: uppercase; letter-spacing: 2px; margin-top: 4px;">
            Film Permit Intelligence System
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Mode toggle
    mode = st.radio(
        "ANALYSIS MODE",
        ["Single Scene", "Full Script"],
        horizontal=True,
    )

    st.markdown("")

    # Initialize state
    analyze_btn = False
    script_btn = False
    scene_text = ""
    location = ""
    notes = ""
    script_text = ""
    default_location = "Los Angeles, CA"
    production_notes = ""

    if mode == "Single Scene":
        # Sample scenes
        SAMPLES = {
            "(Select a sample scene)": {"scene_text": "", "location": "", "notes": ""},
            "🌙 Street Night Shooting": {
                "scene_text": "EXT. DOWNTOWN LOS ANGELES - NIGHT. Detective Cruz walks down a rain-slicked street, passing neon signs. She spots the suspect ducking into an alley. A police cruiser screeches to a halt at the corner. 20 extras mill around as bystanders.",
                "location": "Spring Street, Downtown Los Angeles, CA",
                "notes": "Night shoot. Wet-down required for rain effect. 20 extras as pedestrians.",
            },
            "🌳 Park Dialogue": {
                "scene_text": "EXT. GRIFFITH PARK - DAY. Maya and Jordan sit on a bench overlooking the city. A dog walker passes with three golden retrievers. They argue quietly about the letter.",
                "location": "Griffith Park, Los Angeles, CA",
                "notes": "Simple dialogue scene. Minimal crew. Two actors, natural light.",
            },
            "🚁 Drone Beach Shot": {
                "scene_text": "EXT. VENICE BEACH - SUNSET. A drone rises over the boardwalk capturing the golden hour light. Below, 50 extras jog, skate, and dance along the waterfront. The camera pushes in on a lone surfer paddling out.",
                "location": "Venice Beach, Los Angeles, CA",
                "notes": "Drone operator certified. Sunset golden hour window is approximately 45 minutes.",
            },
            "🔫 Prop Weapon Scene": {
                "scene_text": "INT. ABANDONED WAREHOUSE - NIGHT. Marcus pulls a pistol from his waistband and slides it across the table. The rival gang leader picks up a rifle leaning against the wall. Smoke drifts through the broken windows. 8 actors in the scene.",
                "location": "Arts District, Los Angeles, CA",
                "notes": "All weapons are non-firing replicas. Smoke machine for atmosphere. Weapons handler on set.",
            },
            "☕ Small Indoor Shoot": {
                "scene_text": "INT. COFFEE SHOP - DAY. Emily types on her laptop. The barista calls her name. She walks to the counter, picks up her latte, and returns to her seat.",
                "location": "Silver Lake, Los Angeles, CA",
                "notes": "Small crew of 6. Private location secured.",
            },
        }

        sample_choice = st.selectbox("QUICK LOAD SAMPLE", list(SAMPLES.keys()))
        sample = SAMPLES[sample_choice]

        scene_text = st.text_area(
            "SCENE DESCRIPTION",
            value=sample["scene_text"],
            height=160,
            placeholder="EXT. VENICE BEACH - NIGHT. A drone rises over the boardwalk...",
        )
        location = st.text_input(
            "FILMING LOCATION",
            value=sample["location"],
            placeholder="Venice Beach, Los Angeles, CA",
        )
        notes = st.text_input(
            "PRODUCTION NOTES",
            value=sample["notes"],
            placeholder="Night shoot, 40 extras, drone required.",
        )

        st.markdown("")
        analyze_btn = st.button("🔍  ANALYZE SCENE", type="primary", use_container_width=True)

    else:  # Full Script mode
        # Load sample script
        try:
            with open("tests/sample_script.txt", "r") as f:
                sample_script = f.read()
        except FileNotFoundError:
            sample_script = ""

        SCRIPT_SAMPLES = {
            "(Paste your own or upload)": "",
            "📄 Sample: 5-Scene Short Film": sample_script,
        }
        script_choice = st.selectbox("LOAD SCRIPT", list(SCRIPT_SAMPLES.keys()))

        # File uploader
        uploaded_file = st.file_uploader(
            "UPLOAD SCREENPLAY",
            type=["pdf", "txt", "docx", "fdx", "fountain"],
            help="Supports PDF, TXT, DOCX, FDX (Final Draft), and Fountain formats.",
        )

        # Parse uploaded file
        uploaded_text = ""
        if uploaded_file is not None:
            uploaded_text = _parse_uploaded_file(uploaded_file)
            if uploaded_text:
                st.markdown(f"""
                <div style="background: #202535; border: 1px solid #97d700; border-radius: 6px; padding: 8px 12px; margin: 5px 0;">
                    <span style="color: #97d700; font-weight: 700;">✓</span>
                    <span style="color: #e0e0e0; font-size: 0.85em;">
                        Loaded <strong>{uploaded_file.name}</strong> — {len(uploaded_text)} characters
                    </span>
                </div>
                """, unsafe_allow_html=True)

        # Determine text area content: uploaded > sample > empty
        if uploaded_text:
            prefill = uploaded_text
        else:
            prefill = SCRIPT_SAMPLES[script_choice]

        script_text = st.text_area(
            "FULL SCREENPLAY",
            value=prefill,
            height=300,
            placeholder="EXT. VENICE BEACH - SUNSET\n\nA drone rises over the boardwalk...\n\nINT. WAREHOUSE - NIGHT\n\nMarcus pulls a pistol...",
        )
        default_location = st.text_input(
            "DEFAULT LOCATION",
            value="Los Angeles, CA",
            placeholder="Default city for scenes without a specific location",
        )
        production_notes = st.text_input(
            "PRODUCTION NOTES",
            value="",
            placeholder="General notes for the entire production.",
        )

        st.markdown("")
        script_btn = st.button("🎬  ANALYZE FULL SCRIPT", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 10px 0;">
        <p style="color: #9fa4b4; font-size: 0.7em;">
            Powered by GPT-4o + Google Maps<br>
            <span style="color: #3f4a6a;">v0.3.0 — Research Prototype</span>
        </p>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main area — Landing
# ---------------------------------------------------------------------------
if not analyze_btn and not script_btn:
    # Hero banner
    st.markdown("""
    <div class="hero-banner">
        <h1>🎬 PERMIT<span style="color: #97d700;">AGENT</span></h1>
        <p>Multi-Agent System for Narrative-to-Bureaucratic Alignment in Film Production</p>
    </div>
    """, unsafe_allow_html=True)

    # Pipeline visualization
    st.markdown("#### Pipeline Architecture")
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <span class="pipeline-step">📋 Scene Breakdown</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-step">🌍 Environment</span>
        <span style="color: #97d700; font-weight: 700;"> + </span>
        <span class="pipeline-step">⚠️ Exposures</span>
        <span style="color: #9fa4b4; font-size: 0.7em;">(parallel)</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-step">📖 Rules</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-step">📝 Compliance</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-step">🎲 Simulation</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Feature cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="permit-card">
            <h4 style="margin-top: 0;">Real Regulations</h4>
            <p>40+ rules from LAMC, FilmLA, FAA, LAFD, LADOT, and more. Cited with specific code sections.</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="permit-card">
            <h4 style="margin-top: 0;">Smart Detection</h4>
            <p>AI-powered scene analysis identifies drones, weapons, crowds, pyrotechnics, and other reportable elements.</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="permit-card">
            <h4 style="margin-top: 0;">Location Intelligence</h4>
            <p>Google Maps integration detects nearby schools, hospitals, and government buildings within 1000 ft.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <p style="color: #9fa4b4;">👈 Select a sample scene or paste a full screenplay in the sidebar, then click <strong style="color: #97d700;">ANALYZE</strong>.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ===========================================================================
# FULL SCRIPT MODE
# ===========================================================================
if script_btn and script_text.strip():
    script_input = ScriptInput(
        script_text=script_text,
        default_location=default_location,
        production_notes=production_notes,
    )

    progress_bar = st.progress(0, text="Parsing screenplay...")

    def update_progress(current, total):
        progress_bar.progress(
            current / total,
            text=f"Analyzing scene {current}/{total}...",
        )

    script_result = run_script_pipeline(script_input, progress_callback=update_progress)
    progress_bar.progress(1.0, text="Analysis complete!")

    sm = script_result.summary
    risk_colors_css = {"low": "risk-low", "medium": "risk-medium", "high": "risk-high", "critical": "risk-critical"}

    # --- Script Summary Header ---
    feas_pct = int(sm.average_feasibility * 100)
    feas_color = "#97d700" if sm.average_feasibility >= 0.7 else "#ffb81c" if sm.average_feasibility >= 0.5 else "#aa1609"
    risk_css = risk_colors_css.get(sm.highest_risk.value, "risk-medium")

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #202535, #3f4a6a); border-radius: 12px; padding: 25px; margin: 15px 0;">
        <div style="display: flex; justify-content: space-around; text-align: center; flex-wrap: wrap; gap: 15px;">
            <div>
                <div class="stat-number">{sm.total_scenes}</div>
                <div class="stat-label">Scenes</div>
            </div>
            <div>
                <div class="stat-number">{sm.total_exposures}</div>
                <div class="stat-label">Exposures</div>
            </div>
            <div>
                <div class="stat-number">{sm.total_rules_matched}</div>
                <div class="stat-label">Rules</div>
            </div>
            <div>
                <div class="stat-number">{len(sm.unique_permits_required)}</div>
                <div class="stat-label">Permits</div>
            </div>
            <div>
                <div class="stat-number">{sm.max_lead_time_days}</div>
                <div class="stat-label">Lead Time</div>
            </div>
            <div>
                <div class="stat-number" style="color: {feas_color};">{feas_pct}%</div>
                <div class="stat-label">Feasibility</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Recommendation ---
    st.markdown(f"""
    <div class="permit-card" style="border-color: {feas_color};">
        <h4 style="margin-top: 0;">Overall Recommendation</h4>
        <p style="font-size: 1.05em;">{sm.overall_recommendation}</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Tabs: Summary, Per-scene, Permits, JSON ---
    stab1, stab2, stab3, stab4 = st.tabs([
        "📊 SUMMARY",
        "🎬 SCENE-BY-SCENE",
        "📋 ALL PERMITS & NOTIFICATIONS",
        "📦 JSON",
    ])

    with stab1:
        # High-risk scenes
        if sm.high_risk_scenes:
            st.markdown("#### High-Risk Scenes")
            for hrs in sm.high_risk_scenes:
                st.markdown(f"""
                <div class="permit-card" style="border-color: #aa1609;">
                    <span style="color: #aa1609; font-weight: 700;">🔴</span> {hrs}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="permit-card" style="border-color: #008009;">
                <p style="color: #97d700; font-weight: 700;">✓ No high-risk scenes detected.</p>
            </div>
            """, unsafe_allow_html=True)

        # Parsed scenes list
        st.markdown("#### Scenes Detected")
        for ps in script_result.parsed_scenes:
            sr = script_result.scene_results[ps.scene_number - 1] if ps.scene_number <= len(script_result.scene_results) else None
            risk_val = sr.exposures.overall_risk.value if sr else "low"
            risk_badge = risk_colors_css.get(risk_val, "risk-low")
            exp_count = len(sr.exposures.exposures) if sr else 0
            feas_val = f"{sr.simulation.overall_feasibility:.0%}" if sr else "N/A"
            st.markdown(f"""
            <div class="permit-card">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <span style="color: #009cde; font-weight: 900;">#{ps.scene_number}</span>
                        <span style="font-weight: 700; margin-left: 8px;">{ps.slug_line}</span>
                    </div>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <span style="color: #9fa4b4; font-size: 0.85em;">{exp_count} exposures</span>
                        <span style="color: #9fa4b4; font-size: 0.85em;">Feas: {feas_val}</span>
                        <span class="risk-badge {risk_badge}">{risk_val}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with stab2:
        # Per-scene detailed view
        for i, sr in enumerate(script_result.scene_results):
            ps = script_result.parsed_scenes[i]
            risk_val = sr.exposures.overall_risk.value
            risk_badge = risk_colors_css.get(risk_val, "risk-low")

            with st.expander(f"#{ps.scene_number} — {ps.slug_line}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Time", sr.breakdown.time_of_day)
                col2.metric("Exposures", len(sr.exposures.exposures))
                col3.metric("Feasibility", f"{sr.simulation.overall_feasibility:.0%}")

                st.markdown(f"**Summary:** {sr.breakdown.summary}")
                st.markdown(f"**Environment:** {sr.environment.environment_type.value} — {sr.environment.jurisdiction}")

                if sr.exposures.exposures:
                    st.markdown("**Exposures:**")
                    for e in sr.exposures.exposures:
                        st.markdown(f"- {e.element} ({e.category}, {e.risk_level.value})")

                if sr.rules.matched_rules:
                    st.markdown(f"**Rules Matched:** {len(sr.rules.matched_rules)}")

                st.markdown(f"**Permits:** {', '.join(sr.compliance_plan.required_permits)}")
                st.markdown(f"**Lead Time:** {sr.compliance_plan.estimated_lead_time_days} days")
                st.markdown(f"**Recommendation:** {sr.simulation.recommendation}")

    with stab3:
        col1, col2 = st.columns(2)
        with col1:
            permits_html = "".join(f'<li style="margin: 6px 0;"><span style="color: #97d700;">✓</span> {p}</li>' for p in sm.unique_permits_required)
            st.markdown(f"""
            <div class="permit-card">
                <h4 style="margin-top:0;">All Required Permits ({len(sm.unique_permits_required)})</h4>
                <ul style="list-style: none; padding-left: 0;">{permits_html}</ul>
            </div>
            """, unsafe_allow_html=True)

            ins_html = "".join(f'<li style="margin: 6px 0;"><span style="color: #009cde;">🛡</span> {i}</li>' for i in sm.unique_insurance)
            st.markdown(f"""
            <div class="permit-card">
                <h4 style="margin-top:0;">Insurance Requirements</h4>
                <ul style="list-style: none; padding-left: 0;">{ins_html}</ul>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            notif_html = "".join(f'<li style="margin: 6px 0;"><span style="color: #ffb81c;">📞</span> {n}</li>' for n in sm.unique_notifications)
            st.markdown(f"""
            <div class="permit-card">
                <h4 style="margin-top:0;">All Notifications Required</h4>
                <ul style="list-style: none; padding-left: 0;">{notif_html}</ul>
            </div>
            """, unsafe_allow_html=True)

    with stab4:
        st.json(json.loads(script_result.model_dump_json()))

    # --- Download Document ---
    st.markdown("---")
    st.markdown("#### 📥 Download Permit Application Package")

    doc_buffer = generate_script_doc(script_result)
    st.download_button(
        label="📄  DOWNLOAD PERMIT PACKAGE (.DOCX)",
        data=doc_buffer,
        file_name=f"PermitAgent_Script_Package_{datetime.now().strftime('%Y%m%d')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
    st.markdown("""
    <div class="permit-card" style="border-color: #3f4a6a;">
        <h4 style="margin-top: 0;">What's in the document?</h4>
        <ul style="color: #e0e0e0;">
            <li><strong>Executive Summary</strong> — overall feasibility and recommendation</li>
            <li><strong>All Required Permits</strong> — consolidated across all scenes</li>
            <li><strong>Scene-by-Scene Analysis</strong> — exposures, rules, permit descriptions</li>
            <li><strong>Master Submission Checklist</strong> — everything you need to file</li>
        </ul>
        <p style="color: #9fa4b4; font-size: 0.85em; margin-top: 10px;">
            Fill in the [TO BE COMPLETED] fields with your production details before submitting to FilmLA.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.stop()


# ===========================================================================
# SINGLE SCENE MODE
# ===========================================================================
if not scene_text.strip():
    st.stop()

scene_input = SceneInput(scene_text=scene_text, location=location, notes=notes)

with st.spinner("Running 6-agent pipeline..."):
    result = run_pipeline(scene_input)


# ---------------------------------------------------------------------------
# Results header
# ---------------------------------------------------------------------------
risk_colors_css = {"low": "risk-low", "medium": "risk-medium", "high": "risk-high", "critical": "risk-critical"}
risk_icons = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}

# Summary stats bar
st.markdown("""
<div style="background: linear-gradient(135deg, #202535, #3f4a6a); border-radius: 12px; padding: 25px; margin-bottom: 20px;">
    <div style="display: flex; justify-content: space-around; text-align: center; flex-wrap: wrap; gap: 15px;">
        <div>
            <div class="stat-number">{exposures}</div>
            <div class="stat-label">Exposures</div>
        </div>
        <div>
            <div class="stat-number">{rules}</div>
            <div class="stat-label">Rules Matched</div>
        </div>
        <div>
            <div class="stat-number">{permits}</div>
            <div class="stat-label">Permits Required</div>
        </div>
        <div>
            <div class="stat-number">{lead_time}</div>
            <div class="stat-label">Lead Time (Days)</div>
        </div>
        <div>
            <div class="stat-number" style="color: {feas_color};">{feasibility}%</div>
            <div class="stat-label">Feasibility</div>
        </div>
    </div>
</div>
""".format(
    exposures=len(result.exposures.exposures),
    rules=len(result.rules.matched_rules),
    permits=len(result.compliance_plan.required_permits),
    lead_time=result.compliance_plan.estimated_lead_time_days,
    feasibility=int(result.simulation.overall_feasibility * 100),
    feas_color="#97d700" if result.simulation.overall_feasibility >= 0.7 else "#ffb81c" if result.simulation.overall_feasibility >= 0.5 else "#aa1609",
), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📋 BREAKDOWN",
    "🌍 ENVIRONMENT",
    "⚠️ EXPOSURES",
    "📖 RULES",
    "📝 COMPLIANCE",
    "🎲 SIMULATION",
    "📦 JSON",
])

# --- Tab 1: Scene Breakdown ---
with tab1:
    b = result.breakdown

    col1, col2, col3 = st.columns(3)
    col1.metric("Time of Day", b.time_of_day)
    col2.metric("INT / EXT", b.interior_exterior)
    col3.metric("Crowd Size", b.crowd_size_estimate)

    st.markdown("")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="permit-card">
            <h4 style="margin-top:0;">Setting</h4>
            <p>{b.setting_description}</p>
            <h4>Summary</h4>
            <p>{b.summary}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        chars = "".join(f"<li>{c}</li>" for c in b.characters) if b.characters else "<li style='color:#9fa4b4;'>None detected</li>"
        props = "".join(f"<li>{p}</li>" for p in b.props) if b.props else "<li style='color:#9fa4b4;'>None detected</li>"
        vehicles = "".join(f"<li>{v}</li>" for v in b.vehicles) if b.vehicles else "<li style='color:#9fa4b4;'>None detected</li>"
        sfx = "".join(f"<li>{s}</li>" for s in b.special_effects) if b.special_effects else "<li style='color:#9fa4b4;'>None detected</li>"

        st.markdown(f"""
        <div class="permit-card">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div><h4 style="margin-top:0;">Characters</h4><ul>{chars}</ul></div>
                <div><h4 style="margin-top:0;">Vehicles</h4><ul>{vehicles}</ul></div>
                <div><h4 style="margin-top:0;">Props</h4><ul>{props}</ul></div>
                <div><h4 style="margin-top:0;">Special FX</h4><ul>{sfx}</ul></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# --- Tab 2: Environment ---
with tab2:
    env = result.environment

    col1, col2, col3 = st.columns(3)
    col1.metric("Type", env.environment_type.value.upper())
    col2.metric("Access", env.public_or_private.upper())
    col3.metric("Noise Rules", "YES" if env.noise_restrictions else "NO")

    st.markdown("")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="permit-card">
            <h4 style="margin-top:0;">Jurisdiction</h4>
            <p style="font-size: 1.1em; color: #009cde; font-weight: 700;">{env.jurisdiction}</p>
            {"<h4>Sub-Zone</h4><p>" + env.sub_zone + "</p>" if env.sub_zone else ""}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if env.nearby_sensitive_sites:
            sites_html = "".join(f"<li>{s}</li>" for s in env.nearby_sensitive_sites)
            st.markdown(f"""
            <div class="permit-card" style="border-color: #ffb81c;">
                <h4 style="margin-top:0; color: #ffb81c !important;">⚠ Nearby Sensitive Sites</h4>
                <ul>{sites_html}</ul>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="permit-card">
                <h4 style="margin-top:0;">Nearby Sensitive Sites</h4>
                <p style="color: #97d700;">✓ No sensitive sites detected within 1000 ft.</p>
            </div>
            """, unsafe_allow_html=True)


# --- Tab 3: Exposures ---
with tab3:
    exp = result.exposures

    overall_css = risk_colors_css.get(exp.overall_risk.value, "risk-medium")
    st.markdown(f"""
    <div style="margin-bottom: 15px;">
        <span style="color: #9fa4b4; font-weight: 700; text-transform: uppercase; font-size: 0.8em;">Overall Risk: </span>
        <span class="risk-badge {overall_css}">{exp.overall_risk.value}</span>
    </div>
    """, unsafe_allow_html=True)

    if not exp.exposures:
        st.markdown("""
        <div class="permit-card" style="border-color: #008009;">
            <p style="color: #97d700; font-weight: 700;">✓ No reportable exposures detected. Standard FilmLA permit should suffice.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for e in exp.exposures:
            badge_css = risk_colors_css.get(e.risk_level.value, "risk-medium")
            notif = ", ".join(e.requires_notification) if e.requires_notification else "None required"
            st.markdown(f"""
            <div class="permit-card">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <span style="font-size: 1.1em; font-weight: 700; color: #ffffff;">{e.element}</span>
                        <span style="color: #9fa4b4; font-size: 0.85em; margin-left: 8px;">({e.category})</span>
                    </div>
                    <span class="risk-badge {badge_css}">{e.risk_level.value}</span>
                </div>
                <p style="margin-top: 10px; font-size: 0.95em;">{e.description}</p>
                <p style="margin-top: 5px; font-size: 0.85em; color: #009cde;">
                    <strong style="color: #9fa4b4;">Notify:</strong> {notif}
                </p>
            </div>
            """, unsafe_allow_html=True)


# --- Tab 4: Rules ---
with tab4:
    rules = result.rules

    st.markdown(f"""
    <p style="color: #9fa4b4; margin-bottom: 15px;">
        <strong style="color: #009cde;">{len(rules.matched_rules)}</strong> regulations matched for this scene.
    </p>
    """, unsafe_allow_html=True)

    for r in rules.matched_rules:
        applies = ", ".join(r.applies_to) if r.applies_to else "General"
        mandatory_badge = '<span style="color: #aa1609; font-weight: 700;">MANDATORY</span>' if r.mandatory else '<span style="color: #ffb81c; font-weight: 700;">ADVISORY</span>'
        st.markdown(f"""
        <div class="permit-card">
            <div style="display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap;">
                <div>
                    <span style="color: #009cde; font-weight: 900; font-size: 0.85em;">{r.rule_id}</span>
                    <span style="color: #9fa4b4; margin-left: 8px; font-size: 0.85em;">{r.source}</span>
                </div>
                {mandatory_badge}
            </div>
            <p style="margin-top: 10px;">{r.summary}</p>
            <p style="color: #9fa4b4; font-size: 0.8em; margin-top: 5px;">Applies to: <span style="color: #97d700;">{applies}</span></p>
        </div>
        """, unsafe_allow_html=True)

    if rules.unmatched_exposures:
        unmatched_str = ", ".join(rules.unmatched_exposures)
        st.markdown(f"""
        <div class="permit-card" style="border-color: #ffb81c;">
            <h4 style="margin-top: 0; color: #ffb81c !important;">⚠ Unmatched Exposures</h4>
            <p>No specific rules found for: <strong>{unmatched_str}</strong></p>
            <p style="color: #9fa4b4; font-size: 0.85em;">These may require further manual research or consultation with FilmLA.</p>
        </div>
        """, unsafe_allow_html=True)


# --- Tab 5: Compliance Plan ---
with tab5:
    plan = result.compliance_plan

    st.markdown(f"""
    <div class="permit-card" style="border-color: #009cde; border-width: 2px;">
        <h4 style="margin-top: 0;">Permit Application Description</h4>
        <p style="font-style: italic; font-size: 1.05em; line-height: 1.8; color: #ffffff;">"{plan.permit_description}"</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        permits_html = "".join(f'<li style="margin: 6px 0;"><span style="color: #97d700;">✓</span> {p}</li>' for p in plan.required_permits)
        st.markdown(f"""
        <div class="permit-card">
            <h4 style="margin-top:0;">Required Permits ({len(plan.required_permits)})</h4>
            <ul style="list-style: none; padding-left: 0;">{permits_html}</ul>
        </div>
        """, unsafe_allow_html=True)

        ins_html = "".join(f'<li style="margin: 6px 0;"><span style="color: #009cde;">🛡</span> {i}</li>' for i in plan.insurance_requirements)
        st.markdown(f"""
        <div class="permit-card">
            <h4 style="margin-top:0;">Insurance Requirements</h4>
            <ul style="list-style: none; padding-left: 0;">{ins_html}</ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        notif_html = "".join(f'<li style="margin: 6px 0;"><span style="color: #ffb81c;">📞</span> {n}</li>' for n in plan.required_notifications)
        st.markdown(f"""
        <div class="permit-card">
            <h4 style="margin-top:0;">Required Notifications</h4>
            <ul style="list-style: none; padding-left: 0;">{notif_html}</ul>
        </div>
        """, unsafe_allow_html=True)

        if plan.conditions:
            cond_html = "".join(f'<li style="margin: 6px 0;"><span style="color: #aa1609;">⚡</span> {c}</li>' for c in plan.conditions)
        else:
            cond_html = '<li style="color: #9fa4b4;">No special conditions.</li>'
        st.markdown(f"""
        <div class="permit-card">
            <h4 style="margin-top:0;">Special Conditions</h4>
            <ul style="list-style: none; padding-left: 0;">{cond_html}</ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    st.metric("Estimated Lead Time", f"{plan.estimated_lead_time_days} business days")


# --- Tab 6: Risk Simulation ---
with tab6:
    sim = result.simulation
    feas = sim.overall_feasibility

    if feas >= 0.8:
        feas_label, feas_color_hex = "HIGH", "#97d700"
    elif feas >= 0.5:
        feas_label, feas_color_hex = "MODERATE", "#ffb81c"
    else:
        feas_label, feas_color_hex = "LOW", "#aa1609"

    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0;">
        <div class="stat-number" style="font-size: 4em; color: {feas_color_hex};">{feas:.0%}</div>
        <div class="stat-label" style="font-size: 1em; margin-top: 5px;">Overall Feasibility — {feas_label}</div>
    </div>
    """, unsafe_allow_html=True)

    st.progress(feas)

    st.markdown(f"""
    <div class="permit-card" style="border-color: {feas_color_hex}; margin-top: 15px;">
        <h4 style="margin-top: 0;">Recommendation</h4>
        <p style="font-size: 1.05em;">{sim.recommendation}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown("#### Risk Scenarios")

    for s in sim.scenarios:
        badge_css = risk_colors_css.get(s.impact.value, "risk-medium")
        prob_bar_width = int(s.probability * 100)
        st.markdown(f"""
        <div class="permit-card">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 8px;">
                <span style="font-weight: 700; color: #ffffff;">{s.scenario_name}</span>
                <span class="risk-badge {badge_css}">{s.impact.value}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span style="color: #9fa4b4; font-size: 0.8em; min-width: 80px;">P = {s.probability:.0%}</span>
                <div style="flex: 1; background: #3f4a6a; border-radius: 4px; height: 6px;">
                    <div style="width: {prob_bar_width}%; background: linear-gradient(90deg, #009cde, #97d700); height: 100%; border-radius: 4px;"></div>
                </div>
            </div>
            <p style="font-size: 0.9em;"><strong style="color: #97d700;">Mitigation:</strong> {s.mitigation}</p>
        </div>
        """, unsafe_allow_html=True)


# --- Tab 7: Full JSON ---
with tab7:
    st.markdown("""
    <p style="color: #9fa4b4; margin-bottom: 10px;">Complete pipeline output in JSON format.</p>
    """, unsafe_allow_html=True)
    st.json(json.loads(result.model_dump_json()))

# --- Download Document ---
st.markdown("---")
st.markdown("#### 📥 Download Permit Application Package")

doc_buffer = generate_single_scene_doc(result)
st.download_button(
    label="📄  DOWNLOAD PERMIT PACKAGE (.DOCX)",
    data=doc_buffer,
    file_name=f"PermitAgent_{result.breakdown.scene_id}_{datetime.now().strftime('%Y%m%d')}.docx",
    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    use_container_width=True,
)
st.markdown("""
<div class="permit-card" style="border-color: #3f4a6a;">
    <h4 style="margin-top: 0;">What's in the document?</h4>
    <ul style="color: #e0e0e0;">
        <li><strong>Production Information</strong> — fill in your company details</li>
        <li><strong>Location Details</strong> — environment, jurisdiction, sensitive sites</li>
        <li><strong>Activity Description</strong> — permit-ready narrative</li>
        <li><strong>Reportable Elements</strong> — exposures and risk levels</li>
        <li><strong>Applicable Regulations</strong> — all matched rules with citations</li>
        <li><strong>Permits & Notifications</strong> — complete checklist</li>
        <li><strong>Risk Assessment</strong> — scenarios and mitigations</li>
        <li><strong>Submission Checklist</strong> — everything you need to file</li>
    </ul>
    <p style="color: #9fa4b4; font-size: 0.85em; margin-top: 10px;">
        Fill in the [TO BE COMPLETED] fields with your production details before submitting to FilmLA.
    </p>
</div>
""", unsafe_allow_html=True)
