import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="MAESTRO Omikron Suite v2.6.3 build 2630012026", layout="wide")

# --- GLOBAL TYPOGRAPHY TUNING ---
st.markdown("""
<style>
div[data-testid="stAppViewContainer"] h1 { font-size: 1.75rem !important; line-height: 1.15 !important; margin-bottom: 0.35rem !important; }
div[data-testid="stAppViewContainer"] h2 { font-size: 1.35rem !important; line-height: 1.2 !important; margin-top: 0.6rem !important; margin-bottom: 0.35rem !important; }
div[data-testid="stAppViewContainer"] h3 { font-size: 1.10rem !important; line-height: 1.25 !important; margin-top: 0.55rem !important; margin-bottom: 0.3rem !important; }
</style>
""", unsafe_allow_html=True)

# --- PDF GENERATOR FUNCTION ---
def generate_pdf(query, row, odi, gci, pmi):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(255, 75, 75)
    pdf.cell(0, 10, f"MAESTRO HUB INTELLIGENCE REPORT: {query}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(100)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | v2.6.3 Platinum", ln=True, align='C')
    pdf.ln(5)

    # Core Metrics Section
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0)
    pdf.cell(0, 10, " 1. CORE ANALYTICS (AXON)", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    pdf.ln(2)
    pdf.cell(0, 7, f"Vitality Gene Score (VTG): {row['initial_score']:.2f}", ln=True)
    pdf.cell(0, 7, f"Toxicity Management Index (TMI): {row['toxicity_index']:.2f}", ln=True)
    pdf.cell(0, 7, f"Combined Efficiency Score (CES): {row['ces_score']:.2f}", ln=True)
    pdf.ln(5)

    # Biological Context
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " 2. BIOLOGICAL DESCRIPTION", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    pdf.ln(2)
    pdf.multi_cell(0, 7, row.get('description_l0', 'No description available.'))
    pdf.ln(5)

    # Therapeutics
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f" 3. THERAPEUTICS (ODI: {len(odi)} items)", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    pdf.ln(2)
    if not odi.empty:
        for _, r in odi.head(10).iterrows():
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 7, f"- {r.get('Generic_Name', 'N/A')}", ln=True)
            pdf.set_font("Arial", size=9)
            pdf.multi_cell(0, 5, f"Class: {r.get('Drug_Class', 'N/A')}\nMechanism: {r.get('Description_L0', 'N/A')}\n")
    else:
        pdf.cell(0, 7, "No pharmacological data found.", ln=True)
    
    # Disclaimer
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(150)
    pdf.multi_cell(0, 5, "DISCLAIMER: This report is for Research Use Only (RUO). MAESTRO Omikron Suite does not provide medical diagnoses or treatment recommendations. Validate findings clinically.")

    return pdf.output(dest='S').encode('latin-1')

# --- 2. CONNECTION ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data or [])
        if d.empty: return d
        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0)
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        if "description_l0" not in d.columns: d["description_l0"] = ""
        return d
    except Exception as e: return pd.DataFrame({"error": [str(e)]})

def get_first_neighbors(df_all, hub, k, min_sig, max_t):
    if df_all.empty or not hub: return pd.DataFrame()
    cand = df_all[(df_all["target_id"] != hub) & (df_all["initial_score"] >= min_sig) & (df_all["toxicity_index"] <= max_t)].copy()
    if cand.empty: return cand
    return cand.sort_values(["ces_score", "initial_score"], ascending=False).head(int(k))

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("v2.6.3 Platinum Build | 2026")
min_sig = st.sidebar.slider("Minimum VTG Threshold", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("TMI Toxicity Limit", 0.0, 1.0, 0.8)
st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Search Hub Target", placeholder="e.g. KRAS").strip().upper()
top_k = st.sidebar.slider("Number of Neighbors (K)", 3, 30, 10)

# --- 4. DATA PORTALS ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
if search_query and not df.empty and "error" not in df.columns:
    try:
        gci_df = pd.DataFrame(supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute().data or [])
        pmi_df = pd.DataFrame(supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute().data or [])
        odi_df = pd.DataFrame(supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute().data or [])
    except: pass

# --- 5. UI: OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if not df.empty and search_query:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # Metrics Display
        cols = st.columns(5)
        metrics = [("OMI", "DETECTED"), ("SMI", f"{len(pmi_df)} Linked"), ("ODI", f"{len(odi_df)} Items"), ("TMI", f"{row['toxicity_index']:.2f}"), ("CES", f"{row['ces_score']:.2f}")]
        for col, (label, val) in zip(cols, metrics):
            col.metric(label, val)

        st.warning(f"**🧬 Biological Description L0:** {row.get('description_l0', 'Analyzing...')}")

        # PDF & TXT Export
        c1, c2 = st.columns(2)
        with c1:
            pdf_data = generate_pdf(search_query, row, odi_df, gci_df, pmi_df)
            st.download_button("📕 Download Full Intelligence (PDF)", pdf_data, file_name=f"MAESTRO_{search_query}_Report.pdf", mime="application/pdf")
        with c2:
            st.download_button("📄 Export Basic Data (TXT)", f"Target: {search_query}\nCES: {row['ces_score']}", file_name=f"{search_query}.txt")

# --- 6. NETWORK MAP ---
st.divider()
if search_query:
    neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)
    filtered_df = pd.concat([df[df["target_id"] == search_query], neighbors_df], ignore_index=True) if search_query in df["target_id"].values else df
    
    st.subheader("🕸️ Network Interaction Map")
    
    

    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        G.add_node(r["target_id"], size=r["initial_score"]*40, color=r["toxicity_index"])
        if r["target_id"] != search_query: G.add_edge(search_query, r["target_id"])
    
    pos = nx.spring_layout(G, k=1.1, seed=42)
    node_x = [pos[n][0] for n in G.nodes()]; node_y = [pos[n][1] for n in G.nodes()]
    
    fig_net = go.Figure(data=[go.Scatter(x=node_x, y=node_y, mode='markers+text', text=list(G.nodes()), textposition="top center",
                                        marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], color=[G.nodes[n]['color'] for n in G.nodes()], colorscale='RdYlGn_r', showscale=True))])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), height=500, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_net, use_container_width=True)

# --- 7. RANKING & DESK ---
st.subheader("📊 Hub Signal Ranking")



fig_bar = px.bar(filtered_df.sort_values("initial_score").tail(15), x="initial_score", y="target_id", orientation="h", color="toxicity_index", color_continuous_scale="RdYlGn_r", template="plotly_dark")
st.plotly_chart(fig_bar, use_container_width=True)

if search_query:
    st.divider()
    st.subheader(f"📂 Hub Intelligence Desk: {search_query}")
    c_odi, c_gci, c_pmi = st.columns(3)
    with c_odi:
        st.markdown(f"### 💊 Therapeutics (ODI: {len(odi_df)})")
        for _, r in odi_df.head(5).iterrows():
            with st.expander(f"**{r.get('Generic_Name', 'N/A')}**"): st.write(r.get('Description_L0', 'N/A'))
    with c_gci:
        st.markdown(f"### 🧪 Clinical Trials (GCI: {len(gci_df)})")
        for _, r in gci_df.head(5).iterrows():
            with st.expander(f"**{r.get('NCT_Number', 'N/A')}**"): st.write(r.get('Canonical_Title', 'N/A'))
    with c_pmi:
        st.markdown(f"### 🧬 Pathways (PMI: {len(pmi_df)})")
        for _, r in pmi_df.head(5).iterrows():
            with st.expander(f"**{r.get('Canonical_Name', 'N/A')}**"): st.write(r.get('Description_L0', 'N/A'))

# --- 8. FOOTER ---
st.divider()
st.markdown("<center>MAESTRO v2.6.3 | © 2026 Omikron Orchestra Project | Powered by AXON Intelligence</center>", unsafe_allow_html=True)
