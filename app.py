import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

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
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_odi_master():
    try:
        res = supabase.table("odi_database").select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

df = load_axon()
df_odi_full = load_odi_master()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Omni-Search & Hub Focus")
# Ricerca flessibile: accetta Target o parte del nome di un Farmaco
user_input = st.sidebar.text_input("Cerca Target o Farmaco (es. pembro, KRAS)", "").strip().upper()
st.sidebar.warning("⚠️ **Research Use Only**")

# --- 4. LOGICA DI MAPPATURA INTELLIGENTE ---
search_query = user_input
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if user_input:
    # A. Verifica se l'input è un farmaco (Ricerca Flessibile)
    if not df_odi_full.empty:
        drug_matches = df_odi_full[
            df_odi_full['Generic_Name'].str.contains(user_input, case=False, na=False) | 
            df_odi_full['Brand_Names'].str.contains(user_input, case=False, na=False)
        ]
        if not drug_matches.empty:
            found_drug = drug_matches.iloc[0]
            # Mappatura: estrae il target dal farmaco trovato (es. PDCD1 da "PDCD1 (PD-1)")
            search_query = str(found_drug['Targets']).split('(')[0].split(';')[0].strip().upper()
            st.sidebar.success(f"Farmaco rilevato: {found_drug['Generic_Name']} ➔ Target: {search_query}")

    # B. Caricamento Dati Satelliti per il target (derivato o diretto)
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data)
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data)
    except: pass

    # C. Filtro per Ragnatela
    if not df.empty:
        all_targets = df['target_id'].tolist()
        if search_query in all_targets:
            idx = all_targets.index(search_query)
            neighbors = all_targets[max(0, idx-3):min(len(all_targets), idx+4)]
            filtered_df = df[df['target_id'].isin(neighbors)]
        else:
            filtered_df = df[df['target_id'].str.contains(search_query, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 5. OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df['target_id'] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
        r1c1.metric("OMI", "DETECTED")
        r1c2.metric("SMI (Pathway)", f"{len(pmi_df)} Linked")
        r1c3.metric("ODI (Drug)", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        r1c4.metric("TMI (Tox)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1c5.metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- 6. RAGNATELA DINAMICA (SOLE-HUB) ---
st.subheader("🕸️ Network Interaction Map")

if not filtered_df.empty:
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = str(r['target_id'])
        is_f = tid == search_query
        G.add_node(tid, size=float(r['initial_score']) * (60 if is_f else 30), color=float(r['toxicity_index']))
    
    nodes = list(G.nodes())
    if search_query in nodes:
        # Crea i link: tutti i satelliti si connettono al Sole (Search Query)
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    
    pos = nx.spring_layout(G, k=1.0, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#777'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 7. DEEP DIVE TABS ---
st.divider()
t1, t2, t3 = st.tabs(["💊 Therapeutics (ODI)", "🧬 Pathways (SMI)", "🧪 Clinica (GCI)"])
with t1:
    if not odi_df.empty: st.dataframe(odi_df[['Generic_Name', 'Brand_Names', 'Drug_Class']], use_container_width=True)
with t2:
    if not pmi_df.empty:
        for _, p in pmi_df.iterrows():
            with st.expander(f"Pathway: {p['Canonical_Name']}"):
                st.write(p.get('Description_L0', 'Dettagli non disponibili'))
with t3:
    if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)

st.caption("MAESTRO Suite | Omni-Search Engine | RUO")
