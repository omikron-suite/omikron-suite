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
            d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
            d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0).clip(0.0, 1.0)
            d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except Exception: return pd.DataFrame()

df = load_axon()

# --- 2. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
search_query = st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS").strip().upper()

# --- 3. RECUPERO DATI & LOGICA CARTELLA ---
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
    st.sidebar.divider()
    st.sidebar.success(f"📂 **Cartella Farmaci: {len(odi_df)}**")
    with st.sidebar.expander("Apri Cartella ODI"):
        for drug in odi_df['Generic_Name'].unique():
            st.write(f"💊 {drug}")

# --- 4. DASHBOARD & OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")
if search_query and not df.empty:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Linked")
        c3.metric("ODI", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- 5. RAGNATELA (COSTRUZIONE MANUALE ARCHI) ---
st.subheader("🕸️ Network Interaction Map")


if not df.empty:
    G = nx.Graph()
    
    # HUB CENTRALE (Se cercato, altrimenti prendiamo il top hub)
    if search_query and search_query in df['target_id'].values:
        center = search_query
        G.add_node(center, size=60, color='gold', label=f"🎯 {center}")
        
        # AGGIUNTA NODI E LINK FISICI (EDGES)
        # 1. Altri Target vicini
        idx = df[df['target_id'] == center].index[0]
        neighbors = df.iloc[max(0, idx-4):min(len(df), idx+5)]
        for _, r in neighbors.iterrows():
            if r['target_id'] != center:
                G.add_node(r['target_id'], size=30, color='skyblue', label=r['target_id'])
                G.add_edge(center, r['target_id'])
        
        # 2. Farmaci (Satelliti)
        for _, drug in odi_df.head(5).iterrows():
            d_label = f"💊 {drug['Generic_Name']}"
            G.add_node(d_label, size=25, color='orange', label=d_label)
            G.add_edge(center, d_label)
            
        # 3. Pathway (Satelliti)
        for _, path in pmi_df.head(3).iterrows():
            p_label = f"🧬 {path['Canonical_Name']}"
            G.add_node(p_label, size=25, color='violet', label=p_label)
            G.add_edge(center, p_label)

    else:
        # VISTA DEFAULT (Solo Hubs)
        top = df.sort_values('initial_score', ascending=False).head(10)
        center = top.iloc[0]['target_id']
        G.add_node(center, size=40, color='gray')
        for _, r in top.iloc[1:].iterrows():
            G.add_node(r['target_id'], size=30, color='gray')
            G.add_edge(center, r['target_id'])

    # LAYOUT DINAMICO (Ragnatela Esplosa)
    pos = nx.spring_layout(G, k=1.3, seed=42)
    
    # Coordinate Archi (LINEE)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure()
    
    # Disegno Linee
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(width=1.5, color='#888'), hoverinfo='none'))
    
    # Disegno Nodi
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

st.caption("MAESTRO Suite | True Network Build v17.5 | RUO")
