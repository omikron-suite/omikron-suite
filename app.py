import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- 2. CONNESSIONE ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("target_id,initial_score,toxicity_index").execute()
        d = pd.DataFrame(res.data or [])
        if d.empty: return d
        d["target_id"] = d["target_id"].astype(str).str.strip().upper()
        d["initial_score"] = pd.to_numeric(d["initial_score"], errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d["toxicity_index"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Omni-Search")
raw_query = st.sidebar.text_input("Target o Farmaco", placeholder="es. KRAS o pembro").strip().upper()
st.sidebar.warning("⚠️ **Research Use Only**")

# --- 4. LOGICA DI INTELLIGENZA (Fuzzy Match & Data Recovery) ---
search_query = raw_query
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if raw_query:
    # Cerchiamo se l'input è un farmaco per estrarre il Target biologico
    try:
        res_drug = supabase.table("odi_database").select("*").ilike("Generic_Name", f"%{raw_query}%").execute()
        if res_drug.data:
            drug_data = res_drug.data[0]
            search_query = str(drug_data.get('Targets', '')).split('(')[0].split(';')[0].strip().upper()
            st.sidebar.success(f"Mappato: {raw_query} ➔ {search_query}")
    except: pass

    # Query database satelliti
    try:
        gci_df = pd.DataFrame(supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute().data or [])
        pmi_df = pd.DataFrame(supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute().data or [])
        odi_df = pd.DataFrame(supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute().data or [])
    except: pass

# Filtro per ragnatela
if not df.empty and "error" not in df.columns:
    if search_query:
        filtered_df = df[df["target_id"].str.contains(search_query, na=False)]
        if filtered_df.empty: # Fallback se il target cercato non è nel DB AXON
            filtered_df = df.sort_values("initial_score", ascending=False).head(10)
    else:
        filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)].head(15)
else:
    filtered_df = pd.DataFrame()

# --- 5. UI PRINCIPALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty and "error" not in df.columns:
    target_match = df[df["target_id"] == search_query]
    if not target_match.empty:
        row = target_match.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Linked")
        c3.metric("ODI", f"{len(odi_df)} Drugs")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- 6. RAGNATELA MULTI-NODO ---

st.subheader("🕸️ Network Interaction Map")
if not filtered_df.empty:
    G = nx.Graph()
    # 1. Nodi Target (AXON)
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]
        G.add_node(tid, type='target', size=float(r["initial_score"]) * (50 if tid == search_query else 30), color=float(r["toxicity_index"]))

    # 2. Nodi Farmaco & Pathway (Satelliti)
    if search_query:
        for _, dr in odi_df.head(3).iterrows():
            d_node = f"💊 {dr['Generic_Name']}"
            G.add_node(d_node, type='drug', size=25, color=0.2)
            G.add_edge(search_query, d_node)
        for _, pw in pmi_df.head(2).iterrows():
            p_node = f"🧬 {pw['Canonical_Name']}"
            G.add_node(p_node, type='pathway', size=25, color=0.8)
            G.add_edge(search_query, p_node)

    # 3. Connessioni tra hub
    t_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'target']
    if search_query in t_nodes:
        for tn in t_nodes:
            if tn != search_query: G.add_edge(search_query, tn)

    pos = nx.spring_layout(G, k=1.3, seed=42)
    
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]; x1, y1 = pos[b]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color='#888'), hoverinfo="none"))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode="markers+text", text=list(G.nodes()), textposition="top center",
        marker=dict(size=[G.nodes[n].get("size", 20) for n in G.nodes()],
                    color=[G.nodes[n].get("color", 0.5) for n in G.nodes()],
                    colorscale="RdYlGn_r", showscale=True, line=dict(width=2, color='white'))
    ))
    fig_net.update_layout(showlegend=False, margin=dict(b=0, l=0, r=0, t=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 7. DATA PORTALS ---
st.divider()
p_odi, p_gci = st.columns(2)
with p_odi:
    st.header("💊 Therapeutics (ODI)")
    if not odi_df.empty: st.dataframe(odi_df[["Generic_Name", "Drug_Class"]], use_container_width=True)
with p_gci:
    st.header("🧪 Clinical Trials (GCI)")
    if not gci_df.empty: st.dataframe(gci_df[["Canonical_Title", "Phase"]], use_container_width=True)

st.caption("MAESTRO Suite | Integrated v15.0 | RUO")
