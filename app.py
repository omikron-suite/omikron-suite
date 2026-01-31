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

# --- GLOBAL TYPOGRAPHY TUNING ---
st.markdown("""
<style>
div[data-testid="stAppViewContainer"] h1 { font-size: 1.75rem !important; }
div[data-testid="stAppViewContainer"] h2 { font-size: 1.35rem !important; }
div[data-testid="stAppViewContainer"] h3 { font-size: 1.10rem !important; }
</style>
""", unsafe_allow_html=True)


# --- 2. CONNECTION ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    res = supabase.table("axon_knowledge").select("*").execute()
    d = pd.DataFrame(res.data or [])
    if d.empty:
        return d
    d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
    d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
    d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0)
    d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
    if "description_l0" not in d.columns:
        d["description_l0"] = ""
    return d


def get_first_neighbors(df_all, hub, k, min_sig, max_t):
    cand = df_all[
        (df_all["target_id"] != hub) &
        (df_all["initial_score"] >= min_sig) &
        (df_all["toxicity_index"] <= max_t)
    ]
    return cand.sort_values(["ces_score", "initial_score"], ascending=False).head(k)


df = load_axon()


# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("v2.6.2 Platinum Build | 2026")

min_sig = st.sidebar.slider("Minimum VTG Threshold", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("TMI Toxicity Limit", 0.0, 1.0, 0.8)

search_query = st.sidebar.text_input("🔍 Search Hub Target").strip().upper()
top_k = st.sidebar.slider("Number of Neighbors (K)", 3, 30, 10)

# 🔹 INFORMATION NOTES (RESTORED)
with st.sidebar.expander("📘 Metrics & Concepts Guide"):
    st.markdown("""
**VTG – Vitality Gene Score**  
Represents the biological signal intensity of a target.  
Higher VTG → stronger functional relevance.

**TMI – Toxicity Management Index (0–1)**  
Estimates toxicological or translational risk.  
Lower TMI → safer biological profile.

**CES – Combined Efficiency Score**  
`CES = VTG × (1 − TMI)`  
Balances efficacy and safety into a single prioritization metric.

**Hub Target**  
A central molecular entity under investigation.

**First Neighbors**  
Top-ranked molecular partners contextualizing the hub in its network.
""")


# --- 4. UI CORE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")
st.info(
    "MAESTRO is a **research intelligence environment** designed to explore, contextualize "
    "and prioritize molecular targets. All outputs are **Research Use Only (RUO)**."
)


# --- 5. NETWORK MAP & RANKING ---
st.divider()

if search_query:
    neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)
    hub_df = df[df["target_id"] == search_query]
    filtered_df = pd.concat([hub_df, neighbors_df], ignore_index=True)
else:
    filtered_df = df

if not filtered_df.empty:

    # 🔹 NETWORK EXPLANATION
    with st.expander("🕸️ How to read the Network Interaction Map"):
        st.markdown("""
- **Each node** represents a molecular target  
- **Node size** ∝ VTG (biological signal strength)  
- **Node color** represents TMI (green = low toxicity, red = high toxicity)  
- **Central node (hub)** is the searched target  
- **Edges** indicate contextual association (not causality)
""")

    st.subheader("🕸️ Network Interaction Map")

    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        G.add_node(
            r["target_id"],
            size=float(r["initial_score"]) * 40,
            color=float(r["toxicity_index"])
        )

    for n in G.nodes():
        if search_query and n != search_query:
            G.add_edge(search_query, n)

    pos = nx.spring_layout(G, seed=42)

    fig_net = go.Figure()

    for a, b in G.edges():
        fig_net.add_trace(go.Scatter(
            x=[pos[a][0], pos[b][0]],
            y=[pos[a][1], pos[b][1]],
            mode="lines",
            line=dict(color="#444", width=0.9),
            hoverinfo="none"
        ))

    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()],
        y=[pos[n][1] for n in G.nodes()],
        mode="markers+text",
        text=list(G.nodes()),
        marker=dict(
            size=[G.nodes[n]["size"] for n in G.nodes()],
            color=[G.nodes[n]["color"] for n in G.nodes()],
            colorscale="RdYlGn_r",
            cmin=0.0,
            cmax=1.0,
            showscale=True,
            colorbar=dict(title="TMI")
        )
    ))

    st.plotly_chart(fig_net, use_container_width=True)

    # 🔹 RANKING EXPLANATION
    with st.expander("📊 What does the Hub Signal Ranking show?"):
        st.markdown("""
This ranking highlights targets with the **highest biological signal (VTG)**  
while visually encoding **toxicity risk (TMI)**.

It helps answer:
- *Which targets are strong but safe?*
- *Which ones require caution despite high activity?*
""")

    st.subheader("📊 Hub Signal Ranking")

    fig_bar = px.bar(
        filtered_df.sort_values("initial_score").tail(15),
        x="initial_score",
        y="target_id",
        orientation="h",
        color="toxicity_index",
        color_continuous_scale="RdYlGn_r",
        range_color=(0.0, 1.0),
        template="plotly_dark"
    )
    st.plotly_chart(fig_bar, use_container_width=True)


# --- FOOTER ---
st.divider()
st.caption(
    "MAESTRO Omikron Suite — Research Use Only (RUO). "
    "Designed for exploratory biological intelligence, not for clinical decision making."
)
