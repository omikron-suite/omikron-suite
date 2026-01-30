import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE BASE ---
st.set_page_config(page_title="MAESTRO Suite", layout="wide")

# --- 2. CONNESSIONE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_core():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].astype(str).str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except: return pd.DataFrame()

df_axon = load_core()

# --- 3. SIDEBAR (MATTONCINI LEGO) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")

# Mattoncino 1: Ricerca Target (Sempre attivo)
st.sidebar.subheader("🧬 Core: Hub Focus")
t_search = st.sidebar.text_input("Target", "").strip().upper()

# Mattoncino 2: MODULO CORRELAZIONE (Il tasto "Icona" / Toggle)
st.sidebar.divider()
st.sidebar.subheader("🔗 Modulo Intelligence")
enable_drug_link = st.sidebar.toggle("Attiva Correlazione Farmaco", help="Clicca per aprire la ricerca ODI")

d_search = ""
if enable_drug_link:
    d_search = st.sidebar.text_input("💊 Cerca Farmaco (es. pembro)", "").strip().lower()

st.sidebar.divider()
min_sig = st.sidebar.slider("Soglia VTG", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite TMI", 0.0, 1.0, 0.8)

# --- 4. LOGICA DI FILTRO ---
gci_df, filtered_df = pd.DataFrame(), pd.DataFrame()
if t_search:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{t_search}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
    except: pass
    
    if not df_axon.empty:
        all_ids = df_axon['target_id'].tolist()
        if t_search in all_ids:
            idx = all_ids.index(t_search)
            neighbors = all_ids[max(0, idx-3):min(len(all_ids), idx+4)]
            filtered_df = df_axon[df_axon['target_id'].isin(neighbors)]
        else:
            filtered_df = df_axon[df_axon['target_id'].str.contains(t_search, na=False)]

# --- 5. DASHBOARD CENTRALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if t_search and not df_axon.empty:
    t_row = df_axon[df_axon['target_id'] == t_search]
    if not t_row.empty:
        r = t_row.iloc[0]
        st.header(f"🎼 Opera Director: {t_search}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", "ACTIVE")
        c3.metric("ODI", "LINKED" if enable_drug_link else "OFF")
        c4.metric("TMI", f"{r['toxicity_index']:.2f}")
        c5.metric("CES", f"{r['ces_score']:.2f}")
        st.divider()

# --- 6. FINESTRA CORRELAZIONE (Si apre solo se il Toggle è ON) ---
if enable_drug_link and d_search:
    st.subheader("🖇️ Finestra Hub-Farmaco: Analisi Correlazione")
    try:
        # Carichiamo ODI solo se serve
        res_odi = supabase.table("odi_database").select("*").execute()
        df_odi = pd.DataFrame(res_odi.data)
        
        matches = df_odi[df_odi['Generic_Name'].str.contains(d_search, case=False, na=False) | 
                        df_odi['Brand_Names'].str.contains(d_search, case=False, na=False)]
        
        if not matches.empty:
            drug_r = matches.iloc[0]
            drug_targets = str(drug_r['Targets']).upper()
            
            c_l1, c_l2 = st.columns([1, 2])
            if t_search and t_search in drug_targets:
                c_l1.success(f"✅ CORRELATO: {drug_r['Generic_Name']}")
                c_l2.info(f"Target Farmaco: `{drug_targets}`\n\nMeccanismo: {drug_r.get('Mechanism_Short', 'N/D')}")
            else:
                c_l1.warning(f"⚠️ DISCONNESSO: {drug_r['Generic_Name']}")
                c_l2.write(f"Il farmaco non agisce direttamente su {t_search}.")
        else:
            st.error("Farmaco non trovato nel database ODI.")
    except:
        st.error("Errore nel caricamento del modulo ODI.")
    st.divider()

# --- 7. RAGNATELA E GRAFICI ---
if not filtered_df.empty:
    tab_net, tab_data = st.tabs(["🕸️ Network Map", "🧪 Clinical Trial Data (GCI)"])
    
    with tab_net:
        G = nx.Graph()
        for _, row in filtered_df.iterrows():
            tid = row['target_id']
            is_f = tid == t_search
            G.add_node(tid, size=float(row['initial_score']) * (50 if is_f else 30), color=float(row['toxicity_index']))
        
        nodes = list(G.nodes())
        if t_search in nodes:
            for n in nodes:
                if n != t_search: G.add_edge(t_search, n)
        
        pos = nx.spring_layout(G, k=1.0, seed=42)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
        fig_net = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'),
            go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                       text=nodes, textposition="top center",
                       marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                       colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
        ])
        fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig_net, use_container_width=True)

    with tab_data:
        if not gci_df.empty:
            st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)
        else:
            st.info("Nessun dato clinico trovato.")

st.divider()
st.caption("MAESTRO Suite v7.1 | Modular Lego Build")
