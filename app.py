import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- 1. CONNESSIONE ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("target_id,initial_score,toxicity_index").execute()
        d = pd.DataFrame(res.data or [])
        if not d.empty:
            d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
            d["initial_score"] = pd.to_numeric(d["initial_score"], errors="coerce").fillna(0.0)
            d["toxicity_index"] = pd.to_numeric(d["toxicity_index"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
            d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except Exception: return pd.DataFrame()

df = load_axon()

# --- 2. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
search_query = st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS").strip().upper()

# --- 3. LOGICA CARTELLA & DATI ---
odi_df, pmi_df, gci_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
if search_query and not df.empty:
    try:
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])
    except: pass

if not odi_df.empty:
    st.sidebar.success(f"📂 **Cartella Farmaci: {len(odi_df)}**")
    with st.sidebar.expander("Dettagli ODI"):
        for drug in odi_df['Generic_Name'].unique():
            st.write(f"💊 {drug}")

# --- 4. OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")
if search_query and not df.empty:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Linked")
        c3.metric("ODI", f"{len(odi_df)} Drugs")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- 5. RAGNATELA (MODIFICATA PER EVITARE IL CERCHIO) ---
st.subheader("🕸️ Network Interaction Map")


if not df.empty:
    G = nx.Graph()
    # Se c'è un hub selezionato
    if search_query and search_query in df['target_id'].values:
        # Hub Centrale
        G.add_node(search_query, size=60, color='gold', label=f"🎯 {search_query}")
        
        # Link Farmaci (ODI)
        for _, drug in odi_df.head(5).iterrows():
            d_name = f"💊 {drug['Generic_Name']}"
            G.add_node(d_name, size=25, color='#87CEEB', label=d_name)
            G.add_edge(search_query, d_name)
            
        # Link Pathway (PMI)
        for _, path in pmi_df.head(3).iterrows():
            p_name = f"🧬 {path['Canonical_Name']}"
            G.add_node(p_name, size=25, color='#D8BFD8', label=p_name)
            G.add_edge(search_query, p_name)

        # Link Target vicini (AXON)
        idx = df[df['target_id'] == search_query].index[0]
        neighbors = df.iloc[max(0, idx-4):min(len(df), idx+5)]
        for _, r in neighbors.iterrows():
            if r['target_id'] != search_query:
                G.add_node(r['target_id'], size=30, color='lightgray', label=r['target_id'])
                G.add_edge(search_query, r['target_id'])
    else:
        # Default se vuoto
        top = df.sort_values('initial_score', ascending=False).head(10)
        for _, r in top.iterrows():
            G.add_node(r['target_id'], size=35, color='gray', label=r['target_id'])

    # LAYOUT: k=1.5 forza i nodi a distanziarsi, rompendo il cerchio
    pos = nx.spring_layout(G, k=1.5, iterations=100, seed=42)
    
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.2, color='#666'), mode='lines', hoverinfo='none'))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode='markers+text', text=list(G.nodes()), textposition="top center",
        marker=dict(size=[G.nodes[n].get('size', 20) for n in G.nodes()], 
                    color=[G.nodes[n].get('color', 'gray') for n in G.nodes()], 
                    line=dict(width=2, color='white'))
    ))

    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 6. TABELLE ---
st.divider()
c_odi, c_gci = st.columns(2)
with c_odi:
    st.header("💊 Therapeutics (ODI)")
    if not odi_df.empty: st.dataframe(odi_df[['Generic_Name', 'Drug_Class']], use_container_width=True)
with c_gci:
    st.header("🧪 Clinical Trials (GCI)")
    if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase']], use_container_width=True)

st.caption("MAESTRO Suite | Anti-Circle Build | RUO")
