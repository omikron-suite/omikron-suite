import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="MAESTRO Omikron Suite v2.6.2 build 2630012026", layout="wide")

# --- GLOBAL TYPOGRAPHY TUNING (shrink big titles only) ---
st.markdown("""
<style>
/* Streamlit main title (st.title) */
div[data-testid="stAppViewContainer"] h1 {
    font-size: 1.75rem !important;
    line-height: 1.15 !important;
    margin-bottom: 0.35rem !important;
}

/* Section headers from markdown ## and similar */
div[data-testid="stAppViewContainer"] h2 {
    font-size: 1.35rem !important;
    line-height: 1.2 !important;
    margin-top: 0.6rem !important;
    margin-bottom: 0.35rem !important;
}

/* Subheaders / markdown ### */
div[data-testid="stAppViewContainer"] h3 {
    font-size: 1.10rem !important;
    line-height: 1.25 !important;
    margin-top: 0.55rem !important;
    margin-bottom: 0.3rem !important;
}

/* Optional: slightly smaller "st.subheader" spacing without changing body text */
div[data-testid="stAppViewContainer"] [data-testid="stHeader"] {
    margin-bottom: 0.25rem !important;
}
</style>
""", unsafe_allow_html=True)

# --- 2. CONNECTION (Secrets Recommended) ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon() -> pd.DataFrame:
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data or [])
        if d.empty:
            return d

        # Normalization
        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0)

        # CES Formula: CES = VTG * (1 - TMI)
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])

        # Optional Description Column
        if "description_l0" not in d.columns:
            d["description_l0"] = ""

        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

def get_first_neighbors(df_all: pd.DataFrame, hub: str, k: int, min_sig: float, max_t: float) -> pd.DataFrame:
    """
    Defines "first neighbors" as Top-K candidates ordered by CES (then initial_score),
    respecting the VTG/TMI filters.
    """
    if df_all.empty or not hub:
        return pd.DataFrame()

    cand = df_all[
        (df_all["target_id"] != hub) &
        (df_all["initial_score"] >= min_sig) &
        (df_all["toxicity_index"] <= max_t)
    ].copy()

    if cand.empty:
        return cand

    cand = cand.sort_values(["ces_score", "initial_score"], ascending=False).head(int(k))
    return cand

# --------- EXPORT HELPERS (NEW) ---------
def _safe_cols(df: pd.DataFrame, preferred: list[str]) -> list[str]:
    return [c for c in preferred if c in df.columns]

def _df_to_markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return "_No data._"
    return df.head(max_rows).to_markdown(index=False)

def build_hub_report(
    *,
    app_title: str,
    build_id: str,
    hub: str,
    hub_row: pd.Series,
    min_sig: float,
    max_t: float,
    top_k: int,
    neighbors_df: pd.DataFrame,
    odi_df: pd.DataFrame,
    pmi_df: pd.DataFrame,
    gci_df: pd.DataFrame,
    axon_df_all: pd.DataFrame,
) -> str:
    """
    Builds a detailed TXT report for a given hub/target.
    Includes filters, hub metrics, neighbors and linked portal previews.
    """

    ts = datetime.now().isoformat(timespec="seconds")

    lines = []
    lines.append(f"{app_title}")
    lines.append(f"Build: {build_id}")
    lines.append(f"Timestamp: {ts}")
    lines.append("")
    lines.append("=== RUO DISCLAIMER ===")
    lines.append("Research Use Only (RUO). Outputs are exploratory and do not constitute medical advice.")
    lines.append("")

    lines.append("=== QUERY CONTEXT ===")
    lines.append(f"Hub/Target: {hub}")
    lines.append(f"Filters: min_VTG={min_sig:.3f} | max_TMI={max_t:.3f} | topK={int(top_k)}")
    lines.append("")

    # HUB METRICS
    lines.append("=== HUB METRICS (AXON) ===")
    hub_common = _safe_cols(axon_df_all, ["target_id", "initial_score", "toxicity_index", "ces_score", "description_l0"])
    hub_payload = {}
    for c in hub_common:
        hub_payload[c] = hub_row.get(c, "")

    # Optional extra AXON columns (capped)
    extra_cols = [c for c in axon_df_all.columns if c not in hub_common]
    extra_cols = [c for c in extra_cols if not str(c).lower().startswith("description_l")]
    for c in extra_cols[:12]:
        v = hub_row.get(c, None)
        if pd.notna(v) and v != "":
            hub_payload[c] = v

    for k, v in hub_payload.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    # NEIGHBORS
    lines.append("=== FIRST NEIGHBORS (Top-K by CES) ===")
    if neighbors_df is None or neighbors_df.empty:
        lines.append("_No neighbors found under current filters._")
        lines.append("")
    else:
        neigh_cols = _safe_cols(neighbors_df, ["target_id", "ces_score", "initial_score", "toxicity_index"])
        neigh_view = neighbors_df[neigh_cols].copy() if neigh_cols else neighbors_df.copy()
        neigh_view = neigh_view.rename(columns={"initial_score": "VTG", "toxicity_index": "TMI", "ces_score": "CES"})
        lines.append(_df_to_markdown_table(neigh_view, max_rows=int(top_k)))
        lines.append("")

    # PORTALS
    def portal_block(name: str, dfp: pd.DataFrame, preferred_cols: list[str], max_rows: int = 10) -> None:
        lines.append(f"=== {name} ===")
        n = 0 if dfp is None else len(dfp)
        lines.append(f"Items linked: {n}")
        if dfp is None or dfp.empty:
            lines.append("_No linked items._")
            lines.append("")
            return
        cols = _safe_cols(dfp, preferred_cols)
        preview = dfp[cols].head(max_rows) if cols else dfp.head(max_rows)
        lines.append(_df_to_markdown_table(preview, max_rows=max_rows))
        lines.append("")

    portal_block(
        "ODI (Therapeutics)",
        odi_df,
        preferred_cols=["Generic_Name", "Brand_Names", "Drug_Class", "Modality", "Mechanism_Short", "Targets", "Regulatory_Status_US", "Regulatory_Status_EU"],
        max_rows=10
    )
    portal_block(
        "PMI (Pathways)",
        pmi_df,
        preferred_cols=["Canonical_Name", "Key_Targets", "Mechanism_Category", "Mechanism_Subtype", "Description_L0"],
        max_rows=10
    )
    portal_block(
        "GCI (Clinical Trials)",
        gci_df,
        preferred_cols=["Phase", "Year", "NCT_Number", "ClinicalTrials_ID", "Canonical_Title", "Cancer_Type", "Primary_Biomarker", "Primary_Endpoint"],
        max_rows=10
    )

    lines.append("=== REPRODUCIBILITY NOTES ===")
    lines.append("Neighbor selection is performed by sorting candidates by CES (then VTG), after applying VTG/TMI filters.")
    lines.append("Portal linkage is retrieved by ILIKE matching the hub string against Primary_Biomarker / Key_Targets / Targets fields.")
    lines.append("")

    return "\n".join(lines)

# --- LOAD MAIN AXON DATA ---
df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("v2.6.2 Platinum Build | 2026")

min_sig = st.sidebar.slider(
    "Minimum VTG Threshold", 0.0, 3.0, 0.8,
    help="VTG (Vitality Gene Score): Intensity of the detected biological signal. Higher values mean the hub is 'active'."
)
max_t = st.sidebar.slider(
    "TMI Toxicity Limit", 0.0, 1.0, 0.8,
    help="TMI (Toxicity Management Index): Toxicological risk threshold. Filters out potentially harmful targets."
)

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Search Hub Target", placeholder="e.g. KRAS").strip().upper()
top_k = st.sidebar.slider(
    "Number of Neighbors (K)", 3, 30, 10,
    help="Number of neighboring partners to display around the selected hub."
)

st.sidebar.markdown("""
<div style="background-color: #1a1a1a; padding: 12px; border-radius: 8px; border-left: 4px solid #ff4b4b; margin-top: 10px;">
    <p style="font-size: 0.75rem; color: #ff4b4b; font-weight: bold; margin-bottom: 5px;">⚠️ RUO STATUS</p>
    <p style="font-size: 0.7rem; color: #aaa; text-align: justify; line-height: 1.2;">
        Research Use Only (RUO). Data does not constitute medical or clinical advice.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. DATA PORTALS ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if search_query and not df.empty and "error" not in df.columns:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
    except Exception:
        pass

# --- 5. UI: OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if df.empty:
    st.error("AXON database empty or unavailable.")
elif "error" in df.columns:
    st.error(f"Error loading AXON: {df['error'].iloc[0]}")
else:
    if search_query:
        target_data = df[df["target_id"] == search_query]

        if target_data.empty:
            st.info(f"No hub found for: **{search_query}**")
        else:
            row = target_data.iloc[0]
            st.markdown(f"## 🎼 Opera Director: {search_query}")

            st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 15px;">
                <div title="OMI: Molecular Identification" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #007bff; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">OMI</span><br><span style="font-size: 1.2rem; font-weight: bold;">DETECTED</span>
                </div>
                <div title="SMI: Pathway Connection Index" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #6f42c1; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">SMI</span><br><span style="font-size: 1.2rem; font-weight: bold;">{len(pmi_df)} Linked</span>
                </div>
                <div title="ODI: Drugs/Molecules available" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #ffc107; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">ODI</span><br><span style="font-size: 1.2rem; font-weight: bold;">{len(odi_df)} Items</span>
                </div>
                <div title="TMI: Toxicity Index" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #dc3545; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">TMI</span><br><span style="font-size: 1.2rem; font-weight: bold;">{row['toxicity_index']:.2f}</span>
                </div>
                <div title="CES: Combined Efficiency Score" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #28a745; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">CES</span><br><span style="font-size: 1.2rem; font-weight: bold;">{row['ces_score']:.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.warning(f"**🧬 Biological Description L0:** {row.get('description_l0', 'Functional target analysis in progress: critical signaling hub detected.')}")

            neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)

            st.markdown("### 🔗 First Neighbors (Hub Context)")
            if neighbors_df.empty:
                st.info("No neighbors found with current filters. Try lowering VTG or increasing TMI.")
            else:
                chips = []
                for _, r in neighbors_df.iterrows():
                    chips.append(
                        f"**{r['target_id']}** · CES {r['ces_score']:.2f} · "
                        f"TMI {r['toxicity_index']:.2f} · VTG {r['initial_score']:.2f}"
                    )
                st.markdown("\n".join([f"- {c}" for c in chips]))

                show_cols = ["target_id", "initial_score", "toxicity_index", "ces_score"]
                st.dataframe(neighbors_df[show_cols], use_container_width=True, hide_index=True)

            # --- EXPORT (IMPROVED) ---
            report_txt = build_hub_report(
                app_title="MAESTRO Omikron Suite",
                build_id="v2.6.2 build 2630012026",
                hub=search_query,
