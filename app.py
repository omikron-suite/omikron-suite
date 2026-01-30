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
user_input = st.sidebar.text_input("🔍 Omni-Search (Target o Farmaco)", "").strip().upper()

st.sidebar.divider()
st.sidebar.error("### ⚠️ DISCLAIMER")
st.sidebar.caption("RESEARCH USE ONLY (RUO). I dati non sostituiscono il parere medico.")

# --- 3. LOGICA DI IDENTIFICAZIONE TARGET ---
search_query = user_input
found_drug_info = ""

if user_input and not df_odi_master.empty:
    m = df_odi_master[df_odi_master['Generic_Name'].str.contains(user_input, case=False, na=False) | 
                      df_odi_master['Brand_Names'].str.contains(user_input, case=False, na=False)]
    if not m.empty:
        row_d = m.iloc[0]
        found_drug_info = f"{row_d['Generic_Name']} ({row_d['Brand_Names']})"
        search_query = str(row_d['Targets']).split('(')[0].split(';')[0].strip().upper()

# --- 4. RECUPERO DATI INTEGRATI ---
gci_df, pmi_df, odi_target_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
if search_query:
    try:
        gci_df = pd.DataFrame(supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute().data)
        pmi_df = pd.DataFrame(supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute().data)
        odi_target_df = pd.DataFrame(supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute().data)
    except: pass

# --- 5. DASHBOARD PRINCIPALE (TUTTO INSIEME) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query:
    # --- HEADER: IDENTIFICAZIONE TARGET ---
    c_head1, c_head2 = st.columns([2, 1])
    with c_head1:
        st.markdown(f"# 🧬 Target ID: `{search_query}`")
        if found_drug_info:
            st.success(f"✅ Farmaco Identificato: **{found_drug_info}**")
    with c_head2:
        if not df_axon.empty and search_query in df_axon['target_id'].values:
            score = df_axon[df_axon['target_id'] == search_query]['ces_score'].values[0]
            st.metric("EFFICIENCY SCORE (CES)", f"{score:.2f}")

    st.divider()

    # --- PARTE 1: OPERA DIRECTOR (10 PARAMETRI) ---
    if not df_axon.empty and search_query in df_axon['target_id'].values:
        row = df_axon[df_axon['target_id'] == search_query].iloc[0]
        
        st.subheader("🎼 Opera Director Status")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("OMI (Biomarker)", "ACTIVE")
        m2.metric("SMI (Pathways)", f"{len(pmi_df)}")
        m3.metric("ODI (Drug Lib)", f"{len(odi_target_df)}")
        m4.metric("TMI (Toxicity)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        m5.metric("CES (Final)", f"{row['ces_score']:.2f}")

        m6, m7, m8, m9, m10 = st.columns(5)
        m6.metric("BCI (Context)", "OK"); m7.metric("GNI (Genomic)", "STABLE")
        m8.metric("EVI (Evidence)", "HIGH"); m9.metric("MBI (Microb.)", "NEUTRAL")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/A"
        m10.metric("GCI (Trials)", phase)
        
    st.divider()

    # --- PARTE 2: RAGNATELA (NETWORK MAP) ---
    st.subheader("🕸️ Network Interaction Map (Ragnatela)")
    
    # Creazione della rete intorno al target
    G = nx.Graph()
    if not df_axon.empty:
        # Prendiamo il target principale + 8 satelliti per la ragnatela
        main_target = search_query
        satellites = df_axon[df_axon['target_id'] != main_target].head(8)['target_id'].tolist()
        
        # Aggiungiamo il centro
        G.add_node(main_target, size=50, color='gold')
        # Aggiungiamo i satelliti e creiamo i link (le "tele")
        for sat in satellites:
            G.add_node(sat, size=25, color='skyblue')
            G.add_edge(main_target, sat) # Questo crea la linea!

        pos = nx.spring_layout(G, k=0.5, seed=42)
        
        # Disegno Linee
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), hoverinfo='none', mode='lines')
        
        # Disegno Nodi
        node_x = [pos[node][0] for node in G.nodes()]
        node_y = [pos[node][1] for node in G.nodes()]
        
        node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=list(G.nodes()), 
                                textposition="top center", marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()],
                                color=[G.nodes[n]['color'] for n in G.nodes()], line_width=2))

        fig_net = go.Figure(data=[edge_trace, node_trace],
                            layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'))
        st.plotly_chart(fig_net, use_container_width=True)

    st.divider()

    # --- PARTE 3: DEEP DIVE DATABASES ---
    st.subheader("🧪 Dettaglio Database Integrati")
    tab_odi, tab_pmi, tab_gci = st.tabs(["💊 Farmaci (ODI)", "🧬 Pathways (PMI)", "🔬 Clinical Trials (GCI)"])
    
    with tab_odi:
        if not odi_target_df.empty: st.dataframe(odi_target_df[['Generic_Name', 'Brand_Names', 'Drug_Class', 'Targets']], use_container_width=True)
        else: st.write("Nessun farmaco specifico trovato per questo target.")
        
    with tab_pmi:
        if not pmi_df.empty:
            for _, r_p in pmi_df.iterrows():
                with st.expander(f"Pathway: {r_p['Canonical_Name']}"):
                    st.write(f"**Key Targets:** {r_p['Key_Targets']}")
                    st.write(f"**Descrizione:** {r_p.get('Description_L0', 'Dettagli nel database.')}")
        else: st.write("Nessun pathway mappato.")

    with tab_gci:
        if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Primary_Biomarker']], use_container_width=True)
        else: st.write("Nessun trial clinico registrato.")

else:
    st.info("👋 Benvenuto. Inserisci un Target (es. KRAS) o un Farmaco (es. Pembro) nella barra laterale per iniziare l'analisi.")

st.caption("MAESTRO Suite v11.4 | Powered by Omikron Orchestra | RUO")
