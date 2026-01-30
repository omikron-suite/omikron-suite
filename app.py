import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Suite", layout="wide")

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

df_axon = load_axon()

# --- 3. SIDEBAR (LOGICA LEGO) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")

# Ricerca Target Principale
st.sidebar.subheader("🧬 Hub Focus")
t_search = st.sidebar.text_input("Target", "").strip().upper()

# TOGGLE CORRELAZIONE
st.sidebar.divider()
enable_intel = st.sidebar.toggle("🔍 Attiva Intelligence Hub-Drug", help="Attiva l'analisi incrociata ODI/GCI")

d_search = ""
if enable_intel:
    d_search = st.sidebar.text_input("💊 Cerca Farmaco (es. pembro)", "").strip().lower()

st.sidebar.divider()
min_sig = st.sidebar.slider("Soglia VTG", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite TMI", 0.0, 1.0, 0.8)

# --- 4. LOGICA DI FILTRO (POTENZIATA PER RAGNATELA) ---
gci_df, filtered_df = pd.DataFrame(), pd.DataFrame()

if not df_axon.empty:
    if t_search:
        # Recupero dati clinici GCI
        try:
            res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{t_search}%").execute()
            gci_df = pd.DataFrame(res_gci.data)
        except: pass
        
        # Logica Ragnatela: Target + Top 6 simili per punteggio (per non avere mai vuoti)
        target_exact = df_axon[df_axon['target_id'] == t_search]
        others = df_axon[df_axon['target_id'] != t_search].sort_values('initial_score', ascending=False).head(6)
        filtered_df = pd.concat([target_exact, others]).drop_duplicates()
    else:
        filtered_df = df_axon[(df_axon['initial_score'] >= min_sig) & (df_axon['toxicity_index'] <= max_t)].head(10)

# --- 5. OPERA DIRECTOR (GRIGLIA ORIGINALE) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if t_search and not df_axon.empty:
    t_row = df_axon[df_axon['target_id'] == t_search]
    if not t_row.empty:
        r = t_row.iloc[0]
        st.header(f"🎼 Opera Director: {t_search}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", "ACTIVE")
        c3.metric("ODI", "INTEL ON" if enable_intel else "READY")
        c4.metric("TMI", f"{r['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{r['ces_score']:.2f}")
        st.divider()

# --- 6. MODULO CORRELAZIONE (Il mattoncino aggiuntivo) ---
if enable_intel and d_search:
    st.subheader("🖇️ Intelligence Linker: Correlation Hub")
    try:
        res_odi = supabase.table("odi_database").select("*").execute()
        df_odi = pd.DataFrame(res_odi.data)
        matches = df_odi[df_odi['Generic_Name'].str.contains(d_search, case=False, na=False) | 
                        df_odi['Brand_Names'].str.contains(d_search, case=False, na=False)]
        
        if not matches.empty:
            dr = matches.iloc[0]
            dt = str(dr['Targets']).upper()
            cl1, cl2 = st.columns([1, 2])
            if t_search and t_search in dt:
                cl1.success(f"✅ CORRELAZIONE: {dr['Generic_Name']}")
                cl2.info(f"Il farmaco agisce su {t_search}. Meccanismo: {dr.get('Mechanism_Short', 'N/A')}")
            else:
                cl1.warning("⚠️ NESSUN LINK DIRETTO")
                cl2.write(f"Farmaco: {dr['Generic_Name']} | Target ODI: `{dt}`")
        else: st.error("Farmaco non trovato.")
    except: st.error("Database ODI non raggiungibile.")
    st.divider()

# --- 7. RAGNATELA (RIPRISTINATA E MIGLIORATA) ---
st.subheader("🕸️ Network Interaction Map")
if not filtered_df.empty:
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        tid = row['target_id']
        is_f = tid == t_search
        G.add_node(tid, size=float(row['initial_score']) * (60 if is_f else 30), color=float(row['toxicity_index']))
    
    nodes = list(G.nodes())
    if t_search in nodes:
        for n in nodes:
            if n != t_search: G.add_edge(t_search, n)
    else:
        # Se non c'è ricerca, connetti i nodi visibili tra loro
        for i in range(len(nodes)-1): G.add_edge(nodes[i], nodes[i+1])
    
    pos = nx.spring_layout(G, k=1.2, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#666'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 8. CLINICAL DATA PORTAL (GCI) ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")
if not gci_df.empty:
    st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)
else:
    st.info("In attesa di ricerca Target per popolare i dati clinici.")

st.caption("MAESTRO Suite v7.2 | Restoration Build | RUO")
