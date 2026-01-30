import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="MAESTRO Omikron Suite v2.6.4", layout="wide")

# --- GLOBAL TYPOGRAPHY TUNING ---
st.markdown("""
<style>
div[data-testid="stAppViewContainer"] h1 { font-size: 1.75rem !important; line-height: 1.15 !important; }
div[data-testid="stAppViewContainer"] h2 { font-size: 1.35rem !important; line-height: 1.2 !important; }
div[data-testid="stAppViewContainer"] h3 { font-size: 1.10rem !important; line-height: 1.25 !important; }
</style>
""", unsafe_allow_html=True)

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
    return cand.sort_values(["ces_score", "initial_score"], ascending=False).head(int(k))

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("v2.6.4 Build | 2026")

min_sig = st.sidebar.slider("Minimum VTG Threshold", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("TMI Toxicity Limit", 0.0, 1.0, 0.8)
st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Search Hub Target", placeholder="e.g. KRAS").strip().upper()
top_k = st.sidebar.slider("Number of Neighbors (K)", 3, 30, 10)

# --- 4. DATA PORTALS ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
if search_query and not df.empty:
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
        
        # Display Grid
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Linked")
        c3.metric("ODI", f"{len(odi_df)} Items")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}")
        c5.metric("CES", f"{row['ces_score']:.2f}")

        st.warning(f"**🧬 Biological Description L0:** {row.get('description_l0', 'Analyzing...')}")

        # --- ADVANCED EXPORT FUNCTION ---
        neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)
        
        # Create CSV Buffer
        csv_buffer = io.StringIO()
        
        # Consolidate Data for CSV
        export_df = pd.concat([pd.DataFrame([row]), neighbors_df], ignore_index=True)
        export_df['export_timestamp'] = datetime.now()
        export_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📊 Download Full Intelligence Portfolio (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"MAESTRO_{search_query}_Full_Report.csv",
            mime="text/csv",
            help="Download all metrics, neighbors, and metadata for this hub."
        )

# --- 6. NETWORK MAP ---
st.divider()
if not df.empty:
    if search_query:
        neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)
        hub_df = df[df["target_id"] == search_query]
        filtered_df = pd.concat([hub_df, neighbors_df], ignore_index=True)
    else:
        filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]

    if not filtered_df.empty:
        st.subheader("🕸️ Network Interaction Map")
        
        
        G = nx.Graph()
        for _, r in filtered_df.iterrows():
            G.add_node(r["target_id"], size=r["initial_score"]*40, color=r["toxicity_index"])
            if search_query and r["target_id"] != search_query:
                G.add_edge(search_query, r["target_id"])
        
        pos = nx.spring_layout(G, k=1.1, seed=42)
        fig_net = go.Figure()
        fig_net.add_trace(go.Scatter(
            x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
            mode='markers+text', text=list(G.nodes()), textposition="top center",
            marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], color=[G.nodes[n]['color'] for n in G.nodes()],
            colorscale='RdYlGn_r', showscale=True, line=dict(width=1, color='white'))
        ))
        fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), height=500, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_net, use_container_width=True)

# --- 7. FOOTER ---
st.divider()
st.caption("MAESTRO v2.6.4 | © 2026 Omikron Orchestra Project | Research Use Only (RUO)")
