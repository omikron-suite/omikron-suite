import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px

# --- 1. CONFIGURAZIONE & CONNESSIONE ---
st.set_page_config(page_title="MAESTRO FULL SUITE", layout="wide")

URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_all_data():
    try:
        axon = pd.DataFrame(supabase.table("axon_knowledge").select("*").execute().data)
        odi = pd.DataFrame(supabase.table("odi_database").select("*").execute().data)
        if not axon.empty:
            axon['target_id'] = axon['target_id'].astype(str).str.strip().upper()
            axon['ces_score'] = axon['initial_score'] * (1 - axon['toxicity_index'])
        return axon, odi
    except: return pd.DataFrame(), pd.DataFrame()

df_axon, df_odi_master = load_all_data()

# --- 2. SIDEBAR & FILTRI ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")

# Mattoncino 1: Ricerca Target
st.sidebar.subheader("🧬 Core: Hub Focus")
t_search = st.sidebar.text_input("Inserisci Target (es. KRAS)", "").strip().upper()

# Mattoncino 2: Tasto Correlazione (Lego Toggle)
st.sidebar.divider()
enable_drug_link = st.sidebar.toggle("🔗 Attiva Analisi Farmaco", help="Abilita il cross-link con database ODI")

d_search = ""
if enable_drug_link:
    d_search = st.sidebar.text_input("💊 Cerca Farmaco (es. pembro)", "").strip().lower()

st.sidebar.divider()
st.sidebar.error("### ⚠️ DISCLAIMER")
st.sidebar.caption("RESEARCH USE ONLY (RUO). I dati non sostituiscono il parere medico clinico.")

# --- 3. LOGICA DI FILTRO & SATELLITI ---
search_query = t_search
found_drug_label = ""
gci_df, pmi_df, odi_target_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Se il farmaco è attivo, cerchiamo la correlazione
if enable_drug_link and d_search and not df_odi_master.empty:
    m = df_odi_master[df_odi_master['Generic_Name'].str.contains(d_search, case=False, na=False) | 
                      df_odi_master['Brand_Names'].str.contains(d_search, case=False, na=False)]
    if not m.empty:
        dr = m.iloc[0]
        found_drug_label = f"{dr['Generic_Name']} ({dr['Brand_Names']})"
        if not t_search: # Se non c'è target manuale, il farmaco comanda
            search_query = str(dr['Targets']).split('(')[0].split(';')[0].strip().upper()

if search_query:
    try:
        gci_df = pd.DataFrame(supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute().data)
        pmi_df = pd.DataFrame(supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute().data)
        odi_target_df = pd.DataFrame(supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute().data)
    except: pass

# --- 4. DASHBOARD CENTRALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query:
    st.markdown(f"# 🧬 Hub Intelligence: `{search_query}`")
    
    # FINESTRA HUB-FARMACO (Modulo Lego richiesto)
    if enable_drug_link and d_search:
        st.subheader("🖇️ Hub-Drug Linker")
        c_link1, c_link2 = st.columns([1, 2])
        if found_drug_label:
            if search_query in str(dr['Targets']).upper():
                c_link1.success(f"✅ CORRELATO: {found_drug_label}")
                c_link2.info(f"Il farmaco agisce direttamente su {search_query}.")
            else:
                c_link1.warning("⚠️ NESSUN LINK DIRETTO")
                c_link2.write(f"Farmaco: {found_drug_label} | Target ODI: `{dr['Targets']}`")
        st.divider()

    # OPERA DIRECTOR (10 PARAMETRI)
    if not df_axon.empty and search_query in df_axon['target_id'].values:
        row = df_axon[df_axon['target_id'] == search_query].iloc[0]
        st.subheader("🎼 Opera Director Status")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("OMI", "DETECTED")
        m2.metric("SMI", f"{len(pmi_df)} Path")
        m3.metric("ODI", "LINKED" if not odi_target_df.empty else "NO DRUG")
        m4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        m5.metric("CES", f"{row['ces_score']:.2f}")

        m6, m7, m8, m9, m10 = st.columns(5)
        m6.metric("BCI", "OPTIMAL"); m7.metric("GNI", "STABLE")
        m8.metric("EVI", "HIGH"); m9.metric("MBI", "NEUTRAL")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/A"
        m10.metric("GCI", phase)
    
    st.divider()

    # RAGNATELA (NETWORK MAP)
    st.subheader("🕸️ Network Interaction Map")
    
    if not df_axon.empty:
        G = nx.Graph()
        # Centro + Satelliti
        satellites = df_axon[df_axon['target_id'] != search_query].sort_values('initial_score', ascending=False).head(8)['target_id'].tolist()
        G.add_node(search_query, size=60, color='gold')
        for s in satellites:
            G.add_node(s, size=30, color='skyblue')
            G.add_edge(search_query, s) # Forza i link visibili

        pos = nx.spring_layout(G, k=0.6, seed=42)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
        fig_net = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#888'), mode='lines', hoverinfo='none'),
            go.Scatter(x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()], 
                       mode='markers+text', text=list(G.nodes()), textposition="top center",
                       marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], color=[G.nodes[n]['color'] for n in G.nodes()],
                       colorscale='Viridis', line_width=2))
        ])
        fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig_net, use_container_width=True)

    # DATABASE PORTALS
    st.divider()
    tab1, tab2, tab3 = st.tabs(["💊 Farmaci (ODI)", "🧬 Pathways (PMI)", "🔬 Clinical Trials (GCI)"])
    with tab1: st.dataframe(odi_target_df, use_container_width=True)
    with tab2: st.dataframe(pmi_df, use_container_width=True)
    with tab3: st.dataframe(gci_df, use_container_width=True)

else:
    st.info("👋 Inserisci un Target o attiva la Correlazione Farmaco per visualizzare l'orchestra.")

st.caption("MAESTRO Suite v11.5 | LEGO Architecture | RUO")
