import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE & CONNESSIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("target_id,initial_score,toxicity_index").execute()
        d = pd.DataFrame(res.data or [])
        if not d.empty:
            d["target_id"] = d["target_id"].astype(str).str.strip().upper()
            d["initial_score"] = pd.to_numeric(d["initial_score"], errors="coerce").fillna(0.0)
            d["toxicity_index"] = pd.to_numeric(d["toxicity_index"], errors="coerce").fillna(0.0)
            d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except: return pd.DataFrame()

df = load_axon()

# --- 2. SIDEBAR & RICERCA ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control")

st.sidebar.markdown("### 🔍 Hub Focus")
search_query = st.sidebar.text_input("Inserisci Target ID", placeholder="es. KRAS").strip().upper()

# --- 3. LOGICA SATELLITI & CARTELLA FARMACI ---
odi_df, pmi_df, gci_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if search_query:
    try:
        # Carichiamo solo i dati necessari per l'hub selezionato
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])
    except: pass

# Modulo Cartella Farmaci nella Sidebar
if not odi_df.empty:
    st.sidebar.divider()
    st.sidebar.success(f"📂 **Cartella Farmaci: {len(odi_df)}**")
    with st.sidebar.expander("Vedi Lista"):
        for drug in odi_df['Generic_Name'].unique():
            st.write(f"💊 {drug}")

st.sidebar.divider()
st.sidebar.warning("⚠️ **Research Use Only**")

# --- 4. DASHBOARD: TARGET ID & OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query:
    st.markdown(f"# 🧬 Target Intelligence: `{search_query}`")
    
    if not df.empty and search_query in df['target_id'].values:
        row = df[df["target_id"] == search_query].iloc[0]
        
        # OPERA DIRECTOR (Griglia Integrale)
        st.markdown("##### 🎼 Opera Director Status")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Linked")
        c3.metric("ODI", f"{len(odi_df)} Drugs")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")

        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("BCI", "OPTIMAL"); c7.metric("GNI", "STABLE")
        c8.metric("EVI", "LOW RISK"); c9.metric("MBI", "BALANCED")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D"
        c10.metric("GCI", phase)
        st.divider()

# --- 5. RAGNATELA (HUB & SPOKE DINAMICA) ---
st.subheader("🕸️ Network Interaction Map")


if not df.empty:
    G = nx.Graph()
    
    # Se abbiamo un hub cercato, costruiamo i raggi verso l'esterno
    if search_query and search_query in df['target_id'].values:
        center = search_query
        G.add_node(center, size=60, color='gold', label=f"🎯 {center}")
        
        # 1. Collegamento Farmaci
        for _, drug in odi_df.head(5).iterrows():
            d_name = f"💊 {drug['Generic_Name']}"
            G.add_node(d_name, size=25, color='#87CEEB', label=d_name)
            G.add_edge(center, d_name) # Disegna la linea
            
        # 2. Collegamento Pathway
        for _, path in pmi_df.head(3).iterrows():
            p_name = f"🧬 {path['Canonical_Name']}"
            G.add_node(p_name, size=25, color='#D8BFD8', label=p_name)
            G.add_edge(center, p_name) # Disegna la linea

        # 3. Collegamento Target correlati (AXON)
        idx = df[df['target_id'] == center].index[0]
        neighbors = df.iloc[max(0, idx-4):min(len(df), idx+5)]
        for _, r in neighbors.iterrows():
            if r['target_id'] != center:
                G.add_node(r['target_id'], size=30, color='lightgray', label=r['target_id'])
                G.add_edge(center, r['target_id']) # Disegna la linea
    else:
        # Default: Top Hubs (Senza linee se non c'è focus)
        top = df.sort_values('initial_score', ascending=False).head(10)
        for _, r in top.iterrows():
            G.add_node(r['target_id'], size=35, color='gray', label=r['target_id'])

    # Layout a ragnatela esplosa
    pos = nx.spring_layout(G, k=1.4, seed=42)
    
    # Estrazione coordinate archi
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    # Linee
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'))
    # Nodi
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode='markers+text', text=list(G.nodes()), textposition="top center",
        marker=dict(size=[G.nodes[n].get('size', 25) for n in G.nodes()], 
                    color=[G.nodes[n].get('color', 'gray') for n in G.nodes()], 
                    line=dict(width=1.5, color='white'))
    ))

    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 6. TABELLE DATI BASSO ---
if search_query:
    st.divider()
    c_odi, c_gci = st.columns(2)
    with c_odi:
        st.header("💊 Therapeutics (ODI)")
        if not odi_df.empty: st.dataframe(odi_df[['Generic_Name', 'Drug_Class']], use_container_width=True)
    with c_gci:
        st.header("🧪 Clinical Trials (GCI)")
        if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase']], use_container_width=True)

st.caption("MAESTRO Suite | v18.0 Phoenix Build | RUO")
