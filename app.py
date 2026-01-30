import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Suite v13.9", layout="wide")

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
st.sidebar.markdown("### 🎚️ Ricalibrazione Segnale")
min_sig = st.sidebar.slider("Soglia VTG (Segnale)", 0.0, 3.0, 0.5) # Abbassato default
max_t = st.sidebar.slider("Limite TMI (Tossicità)", 0.0, 1.0, 0.9)  # Alzato default

# --- 4. LOGICA DI RECUPERO DATI (ROBUSTA) ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
filtered_df = pd.DataFrame()

if search_query:
    try:
        gci_df = pd.DataFrame(supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute().data)
        pmi_df = pd.DataFrame(supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute().data)
        odi_df = pd.DataFrame(supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute().data)
        
        if not df.empty:
            # Match esatto o parziale
            match_df = df[df['target_id'].str.contains(search_query, na=False)]
            if not match_df.empty:
                idx = match_df.index[0]
                filtered_df = df.iloc[max(0, idx-5):min(len(df), idx+6)]
            else:
                # Se non trova il target, mostra i top hub per non lasciare vuoto
                filtered_df = df.sort_values('initial_score', ascending=False).head(10)
    except: pass
else:
    # VISTA DEFAULT: Se i filtri bloccano tutto, forza i primi 10
    if not df.empty:
        filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)]
        if filtered_df.empty:
            filtered_df = df.sort_values('initial_score', ascending=False).head(10)

# --- 5. OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df['target_id'] == search_query]
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

# --- 6. RAGNATELA PERSISTENTE ---
st.subheader("🕸️ Network Interaction Map")


if not filtered_df.empty:
    G = nx.Graph()
    
    # Nodo centrale: la query o il miglior target visibile
    central_node = search_query if (search_query and search_query in filtered_df['target_id'].values) else filtered_df['target_id'].iloc[0]
    
    # Costruzione nodi e archi
    for _, r in filtered_df.iterrows():
        tid = r['target_id']
        is_center = tid == central_node
        G.add_node(tid, size=55 if is_center else 30, color=float(r['toxicity_index']), label=f"🎯 {tid}" if is_center else tid)
        if not is_center:
            G.add_edge(central_node, tid)

    # Inserimento Farmaci e Pathway (solo se presenti)
    if not odi_df.empty and search_query:
        for _, drug in odi_df.head(4).iterrows():
            d_name = drug['Generic_Name']
            G.add_node(d_name, size=20, color=0.2, label=f"💊 {d_name}")
            G.add_edge(central_node, d_name)

    if not pmi_df.empty and search_query:
        for _, path in pmi_df.head(3).iterrows():
            p_name = path['Canonical_Name']
            G.add_node(p_name, size=20, color=0.8, label=f"🧬 {p_name}")
            G.add_edge(central_node, p_name)

    # Layout dinamico
    pos = nx.spring_layout(G, k=1.4, iterations=100, seed=42)
    
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#666'), mode='lines', hoverinfo='none'))
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
    st.warning("⚠️ Errore nel caricamento dati. Verifica la connessione al database.")

# --- 7. TABELLE ---
if not odi_df.empty or not gci_df.empty:
    st.divider()
    t1, t2 = st.columns(2)
    with t1:
        st.subheader("💊 ODI Database")
        st.dataframe(odi_df[['Generic_Name', 'Targets', 'Drug_Class']], use_container_width=True)
    with t2:
        st.subheader("🧪 GCI Trials")
        st.dataframe(gci_df[['Canonical_Title', 'Phase']], use_container_width=True)

st.caption("MAESTRO Suite v13.9 | Auto-Recovery Build | RUO")
