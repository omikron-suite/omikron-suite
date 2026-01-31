import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io  # <--- AGGIUNGI QUESTA RIGA


# --- 1. CONFIGURATION ---
st.set_page_config(page_title="MAESTRO Omikron Suite v2.6.2 build 2630012026", layout="wide")

# --- GLOBAL TYPOGRAPHY TUNING (shrink big titles only) ---
st.markdown("""
<style>
div[data-testid="stAppViewContainer"] h1 {
    font-size: 1.75rem !important;
    line-height: 1.15 !important;
    margin-bottom: 0.35rem !important;
}
div[data-testid="stAppViewContainer"] h2 {
    font-size: 1.35rem !important;
    line-height: 1.2 !important;
    margin-top: 0.6rem !important;
    margin-bottom: 0.35rem !important;
}
div[data-testid="stAppViewContainer"] h3 {
    font-size: 1.10rem !important;
    line-height: 1.25 !important;
    margin-top: 0.55rem !important;
    margin-bottom: 0.3rem !important;
}
div[data-testid="stAppViewContainer"] [data-testid="stHeader"] {
    margin-bottom: 0.25rem !important;
}
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
        if d.empty:
            return d

        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0)
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])

        if "description_l0" not in d.columns:
            d["description_l0"] = ""

        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})


def get_first_neighbors(df_all, hub, k, min_sig, max_t):
    if df_all.empty or not hub:
        return pd.DataFrame()

    cand = df_all[
        (df_all["target_id"] != hub) &
        (df_all["initial_score"] >= min_sig) &
        (df_all["toxicity_index"] <= max_t)
    ].copy()

    if cand.empty:
        return cand

    return cand.sort_values(
        ["ces_score", "initial_score"], ascending=False
    ).head(int(k))


df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("v2.6.2 Platinum Build | 2026")

min_sig = st.sidebar.slider("Minimum VTG Threshold", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("TMI Toxicity Limit", 0.0, 1.0, 0.8)

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Search Hub Target").strip().upper()
top_k = st.sidebar.slider("Number of Neighbors (K)", 3, 30, 10)


# --- 4. DATA PORTALS ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# --- 5. UI CORE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")


# --- 6. NETWORK MAP & RANKING ---
st.divider()

if df.empty or ("error" in df.columns):
    st.stop()

# Hub Mode: network = hub + neighbors
if search_query:
    neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)
    hub_df = df[df["target_id"] == search_query]
    if not hub_df.empty and not neighbors_df.empty:
        filtered_df = pd.concat([hub_df, neighbors_df], ignore_index=True)
    else:
        filtered_df = hub_df
else:
    filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]

if not filtered_df.empty:
    st.subheader("🕸️ Network Interaction Map")
    
    

    G = nx.Graph()

    # Nodes
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]
        is_hub = bool(search_query) and (tid == search_query)
        G.add_node(
            tid,
            size=float(r["initial_score"]) * (70 if is_hub else 35),
            color=float(r["toxicity_index"]),
            is_hub=is_hub
        )

    nodes = list(G.nodes())

    # Edges
    if search_query and search_query in nodes:
        for n in nodes:
            if n != search_query:
                G.add_edge(search_query, n)
    elif len(nodes) > 1:
        for i in range(len(nodes) - 1):
            G.add_edge(nodes[i], nodes[i + 1])

    pos = nx.spring_layout(G, k=1.1, seed=42)

    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(color="#444", width=0.9),
        hoverinfo="none"
    ))

    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes],
        y=[pos[n][1] for n in nodes],
        mode="markers+text",
        text=nodes,
        textposition="top center",
        textfont=dict(size=10, color="white"),
        marker=dict(
            size=[G.nodes[n]["size"] for n in nodes],
            color=[G.nodes[n]["color"] for n in nodes],
            colorscale="RdYlGn_r",
            showscale=True,
            line=dict(
                width=[3 if G.nodes[n].get("is_hub") else 1 for n in nodes],
                color="white"
            )
        ),
        hovertemplate="<b>%{text}</b><extra></extra>"
    ))

    fig_net.update_layout(
        showlegend=False,
        margin=dict(b=0, l=0, r=0, t=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=500
    )
    st.plotly_chart(fig_net, use_container_width=True)

    st.subheader("📊 Hub Signal Ranking")
    
    

    fig_bar = px.bar(
        filtered_df.sort_values("initial_score", ascending=True).tail(15),
        x="initial_score",
        y="target_id",
        orientation="h",
        color="toxicity_index",
        color_continuous_scale="RdYlGn_r",
        template="plotly_dark"
    )
    fig_bar.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("No data available with current filters.")

# --- 7. HUB INTELLIGENCE DESK ---
if search_query:
    st.divider()
    st.subheader(f"📂 Hub Intelligence Desk: {search_query}")
    c_odi, c_gci, c_pmi = st.columns(3)

    with c_odi:
        st.markdown(f"### 💊 Therapeutics (ODI: {len(odi_df)})")
        if not odi_df.empty:
            for _, r in odi_df.iterrows():
                with st.expander(f"**{r.get('Generic_Name', 'N/A')}**"):
                    st.write(f"**Class:** {r.get('Drug_Class', 'N/A')}")
                    st.write(f"**Mechanism:** {r.get('Description_L0', 'Details not available.')}")
                    st.caption(f"Status: {r.get('Regulatory_Status_US', 'N/A')}")
        else:
            st.info("No ODI items found.")

    with c_gci:
        st.markdown(f"### 🧪 Clinical Trials (GCI: {len(gci_df)})")
        if not gci_df.empty:
            for _, r in gci_df.iterrows():
                with st.expander(f"**Phase {r.get('Phase', 'N/A')} Trial**"):
                    st.write(f"**ID:** {r.get('NCT_Number', 'N/A')}")
                    st.write(f"**Title:** {r.get('Canonical_Title', 'Details not available.')}")
        else:
            st.info("No GCI trials found.")

    with c_pmi:
        st.markdown(f"### 🧬 Pathways (PMI: {len(pmi_df)})")
        if not pmi_df.empty:
            for _, r in pmi_df.iterrows():
                with st.expander(f"**{r.get('Canonical_Name', 'N/A')}**"):
                    st.write(f"**Detail:** {r.get('Description_L0', 'Details not available.')}")
        else:
            st.info("No PMI pathways found.")


