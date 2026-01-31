import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="MAESTRO Omikron Suite v2.6.2 build 2630012026", layout="wide")

st.markdown("""
<style>
div[data-testid="stAppViewContainer"] h1 { font-size: 1.75rem !important; line-height: 1.15 !important; margin-bottom: 0.35rem !important; }
div[data-testid="stAppViewContainer"] h2 { font-size: 1.35rem !important; line-height: 1.2 !important; margin-top: 0.6rem !important; margin-bottom: 0.35rem !important; }
div[data-testid="stAppViewContainer"] h3 { font-size: 1.10rem !important; line-height: 1.25 !important; margin-top: 0.55rem !important; margin-bottom: 0.3rem !important; }
div[data-testid="stAppViewContainer"] [data-testid="stHeader"] { margin-bottom: 0.25rem !important; }
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
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

def get_first_neighbors(df_all, hub, k, min_sig, max_t):
    if df_all.empty or not hub: return pd.DataFrame()
    cand = df_all[(df_all["target_id"] != hub) & (df_all["initial_score"] >= min_sig) & (df_all["toxicity_index"] <= max_t)].copy()
    if cand.empty: return cand
    return cand.sort_values(["ces_score", "initial_score"], ascending=False).head(int(k))

df = load_axon()

# --- 3. SIDEBAR (With Functional Notes) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("v2.6.2 Platinum Build | 2026")

with st.sidebar.expander("ℹ️ Quick Controls Guide"):
    st.write("""
    **VTG Threshold:** Sets the minimum signal potency for targets.
    **TMI Limit:** Maximum toxicity risk allowed.
    **Search Hub:** Centers the map on a specific gene.
    **Neighbors (K):** Number of primary connections to visualize.
    """)

min_sig = st.sidebar.slider("Minimum VTG Threshold", 0.0, 3.0, 0.8, 
                           help="Filters out targets with biological signal strength below this value.")
max_t = st.sidebar.slider("TMI Toxicity Limit", 0.0, 1.0, 0.8, 
                         help="Sets the upper limit for the Toxicity Management Index (lower is safer).")

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Search Hub Target", 
                                   help="Enter a Gene Symbol (e.g., METTL3) to perform a targeted interaction analysis.").strip().upper()
top_k = st.sidebar.slider("Number of Neighbors (K)", 3, 30, 10, 
                         help="Determines how many top-ranking related targets are pulled into the network view.")

# --- 4. DATA PORTALS ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 5. UI CORE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

# --- 6. NETWORK MAP & RANKING ---
st.divider()

if df.empty or ("error" in df.columns):
    st.error("Connection Error: Check Supabase settings.")
    st.stop()

if search_query:
    neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)
    hub_df = df[df["target_id"] == search_query]
    filtered_df = pd.concat([hub_df, neighbors_df], ignore_index=True) if not hub_df.empty else pd.DataFrame()
else:
    filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]

if not filtered_df.empty:
    st.subheader("🕸️ Network Interaction Map", help="Visual map of biological dependencies. Nodes are colored by TMI (Risk) and sized by VTG (Potency).")
    
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]
        is_hub = bool(search_query) and (tid == search_query)
        G.add_node(tid, size=float(r["initial_score"]) * (70 if is_hub else 35),
                  color=float(r["toxicity_index"]), is_hub=is_hub)

    nodes = list(G.nodes())
    if search_query and search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    elif len(nodes) > 1:
        for i in range(len(nodes) - 1): G.add_edge(nodes[i], nodes[i + 1])

    pos = nx.spring_layout(G, k=1.1, seed=42)
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]; x1, y1 = pos[b]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color="#444", width=0.9), hoverinfo="none"))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
        mode="markers+text", text=nodes, textposition="top center",
        marker=dict(
            size=[G.nodes[n]["size"] for n in nodes],
            color=[G.nodes[n]["color"] for n in nodes],
            colorscale="RdYlGn_r", cmin=0.0, cmax=1.0, showscale=True,
            line=dict(width=[3 if G.nodes[n].get("is_hub") else 1 for n in nodes], color="white")
        ),
        hovertemplate="<b>%{text}</b><extra></extra>"
    ))
    fig_net.update_layout(showlegend=False, margin=dict(b=0, l=0, r=0, t=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
    st.plotly_chart(fig_net, use_container_width=True)

    st.subheader("📊 Hub Signal Ranking", help="Ranking of targets by VTG intensity within the selected cluster.")
    fig_bar = px.bar(
        filtered_df.sort_values("initial_score", ascending=True).tail(15),
        x="initial_score", y="target_id", orientation="h",
        color="toxicity_index", color_continuous_scale="RdYlGn_r", range_color=(0.0, 1.0),
        template="plotly_dark"
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("No data matches current filters.")

# --- 7. HUB INTELLIGENCE DESK ---
if search_query and not filtered_df.empty:
    hub_row = df[df["target_id"] == search_query]
    if not hub_row.empty:
        row = hub_row.iloc[0]
        st.divider()
        st.subheader(f"📂 Hub Intelligence Desk: {search_query}")

        val_tmi = float(row.get('toxicity_index', 0))
        val_ces = float(row.get('ces_score', 0))
        tmi_color = "#28a745" if val_tmi < 0.3 else "#dc3545" if val_tmi > 0.7 else "#ffc107"
        ces_color = "#00d4ff" if val_ces > 0.5 else "#888888"

        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 25px;">
            <div title="OMI: Overall Molecular Intelligence. Strategic detection status." style="background: #111; padding: 15px; border-radius: 8px; border-top: 4px solid #007bff; text-align: center;">
                <span style="font-size: 0.7rem; color: #aaa;">OMI STATUS</span><br><span style="font-size: 1.1rem; font-weight: bold; color: white;">DETECTED</span>
            </div>
            <div title="SMI: Synergistic Mapping Interactions. Number of connected nodes." style="background: #111; padding: 15px; border-radius: 8px; border-top: 4px solid #6f42c1; text-align: center;">
                <span style="font-size: 0.7rem; color: #aaa;">SMI LINKS</span><br><span style="font-size: 1.1rem; font-weight: bold; color: white;">{len(filtered_df)-1}</span>
            </div>
            <div title="VTG: Vital Target Gradient. Raw biological signal strength." style="background: #111; padding: 15px; border-radius: 8px; border-top: 4px solid #fd7e14; text-align: center;">
                <span style="font-size: 0.7rem; color: #aaa;">VTG SIGNAL</span><br><span style="font-size: 1.1rem; font-weight: bold; color: white;">{row['initial_score']:.2f}</span>
            </div>
            <div title="TMI: Toxicity Management Index. 0=Safe, 1=Toxic." style="background: #111; padding: 15px; border-radius: 8px; border-top: 4px solid {tmi_color}; text-align: center;">
                <span style="font-size: 0.7rem; color: {tmi_color}; font-weight: bold;">TMI (RISK)</span><br><span style="font-size: 1.2rem; font-weight: bold; color: {tmi_color};">{val_tmi:.2f}</span>
            </div>
            <div title="CES: Combined Efficacy Score. Final balance VTG vs TMI." style="background: #111; padding: 15px; border-radius: 8px; border-top: 4px solid {ces_color}; text-align: center;">
                <span style="font-size: 0.7rem; color: #aaa;">CES (FINAL)</span><br><span style="font-size: 1.2rem; font-weight: bold; color: {ces_color};">{val_ces:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.info(f"**🧬 Biological Context:** {row.get('description_l0', 'Description pending in AXON database.')}")

        # --- DOWNLOAD FEATURE ---
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Analysis to CSV",
            data=csv,
            file_name=f"MAESTRO_{search_query}_Report.csv",
            mime="text/csv",
            help="Download the current dataset, including all scores and descriptions, as a CSV file."
        )

# --- 8. FOOTER & DOCUMENTATION ---
st.divider()
st.subheader("📚 MAESTRO Intelligence Repository")
exp1, exp2, exp3 = st.columns(3)
with exp1:
    with st.expander("🛡️ AXON Intelligence (OMI/BCI)"):
        st.write("**OMI:** Overall Molecular Intelligence. **BCI:** Biological Cost Index.")
with exp2:
    with st.expander("💊 ODI & PMI Systems"):
        st.write("**ODI:** Pharmaceutical Database. **PMI:** Pathway Mappings.")
with exp3:
    with st.expander("🧪 GCI & TMI (Clinical/Safety)"):
        st.write("**GCI:** Clinical Trial Monitoring. **TMI:** Toxicity Index.")

st.markdown("""
<div style="background-color: #0e1117; padding: 25px; border-radius: 12px; border: 1px solid #333; text-align: center; max-width: 900px; margin: 0 auto; margin-top: 20px;">
    <h4 style="color: #ff4b4b; margin-top: 0;">⚠️ SCIENTIFIC AND LEGAL DISCLAIMER</h4>
    <p style="font-size: 0.8rem; color: #888; text-align: justify; line-height: 1.5;">
        <b>MAESTRO Omikron Suite</b> is for Research Use Only (RUO). Data reflects the status of AXON databases as of Jan 2026.
    </p>
    <p style="font-size: 0.75rem; color: #444; margin-top: 15px;">
        MAESTRO v2.6.2 | © 2026 Omikron Orchestra Project | Powered by AXON Intelligence
    </p>
</div>
""", unsafe_allow_html=True)
