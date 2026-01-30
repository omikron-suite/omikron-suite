import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Suite v13.8", layout="wide")

# --- 2. CONNESSIONE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].astype(str).str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except: return pd.DataFrame()

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")
search_query = st.sidebar.text_input("🔍 Omni-Search (Target o Farmaco)", placeholder="es. KRAS").strip().upper()

st.sidebar.divider()
min_sig = st.sidebar.slider("Soglia VTG (Segnale)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite TMI (Tossicità)", 0.0, 1.0, 0.8)

# --- 4. LOGICA DI RECUPERO DATI ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
filtered_df = pd.DataFrame()

if search_query:
    try:
        gci_df = pd.DataFrame(supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute().data)
        pmi_df = pd.DataFrame(supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute().data)
        odi_df = pd.DataFrame(supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute().data)
        
        if not df.empty:
            if search_query in df['target_id'].values:
                idx = df[df['target_id'] == search_query].index[0]
                filtered_df = df.iloc[max(0, idx-4):min(len(df), idx+5)]
            else:
                filtered_df = df[df['target_id'].str.contains(search_query, na=False)]
    except: pass
else:
    # VISTA DEFAULT: Se non c'è ricerca, prendi i migliori per punteggio
    if not df.empty:
        filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)].sort_values('initial_score', ascending=False).head(12)

# --- 5. OPERA DIRECTOR (SOLO CON SEARCH) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty and search_query in df['target_id'].values:
    row = df[df['target_id'] == search_query].iloc[0]
    st.markdown(f"## 🎼 Opera Director: {search_query}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("OMI", "DETECTED")
    c2.metric("SMI", f"{len(pmi_df)} Linked")
    c3.metric("ODI", f"{len(odi_df)} Drugs")
    c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
    c5.metric("CES", f"{row['ces_score']:.2f}")
    st.divider()

# --- 6. RAGNATELA PERSISTENTE ---
st.subheader("🕸️ Network Interaction Map (Dynamic Spider)")


G = nx.Graph()

if not filtered_df.empty:
    # Definiamo il nodo centrale
    if search_query and search_query in filtered_df['target_id'].values:
        central_node = search_query
    else:
        central_node = filtered_df['target_id'].iloc[0]
    
    # Aggiunta Nodi Target
    for _, r in filtered_df.iterrows():
        tid = r['target_id']
        is_center = tid == central_node
        G.add_node(tid, size=50 if is_center else 30, color=float(r['toxicity_index']), label=f"🎯 {tid}" if is_center else tid)
        if not is_center:
            G.add_edge(central_node, tid)

    # Aggiunta Farmaci (solo se cercati)
    if not odi_df.empty:
        for _, drug in odi_df.head(4).iterrows():
            d_name = drug['Generic_Name']
            G.add_node(d_name, size=20, color=0.2, label=f"💊 {d_name}")
            G.add_edge(central_node, d_name)

    # Aggiunta Pathway (solo se cercati)
    if not pmi_df.empty:
        for _, path in pmi_df.head(3).iterrows():
            p_name = path['Canonical_Name']
            G.add_node(p_name, size=20, color=0.8, label=f"🧬 {p_name}")
            G.add_edge(central_node, p_name)

    # Layout e Disegno
    pos = nx.spring_layout(G, k=1.3, iterations=100, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#777'), mode='lines', hoverinfo='none'))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode='markers+text', text=[G.nodes[n].get('label', n) for n in G.nodes()],
        textposition="top center",
        marker=dict(showscale=True, colorscale='RdYlGn_r', 
                    color=[G.nodes[n].get('color', 0.5) for n in G.nodes()],
                    size=[G.nodes[n].get('size', 20) for n in G.nodes()],
                    line=dict(color='white', width=1.5))
    ))
    
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)
else:
    st.warning("Caricamento database AXON in corso o filtri troppo restrittivi.")

# --- 7. TABELLE DATI ---
if search_query:
    st.divider()
    t1, t2 = st.columns(2)
    with t1:
        st.subheader("💊 ODI Database")
        st.dataframe(odi_df[['Generic_Name', 'Targets', 'Drug_Class']] if not odi_df.empty else pd.DataFrame(), use_container_width=True)
    with t2:
        st.subheader("🧪 GCI Trials")
        st.dataframe(gci_df[['Canonical_Title', 'Phase']] if not gci_df.empty else pd.DataFrame(), use_container_width=True)

st.caption("MAESTRO Suite v13.8 | Persistent Network Build | RUO")
