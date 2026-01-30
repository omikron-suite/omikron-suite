import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omni-Search", layout="wide")

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

@st.cache_data(ttl=600)
def search_all_databases(query):
    """Il cuore del motore: cerca ovunque e correla i dati"""
    results = {
        'drug': pd.DataFrame(),
        'target_axon': pd.DataFrame(),
        'pathways': pd.DataFrame(),
        'trials': pd.DataFrame(),
        'active_target_id': query.upper()
    }
    
    if not query: return results

    # 1. Cerca nel database Farmaci (ODI)
    try:
        res_odi = supabase.table("odi_database").select("*").ilike("Generic_Name", f"%{query}%").execute()
        if not res_odi.data:
            res_odi = supabase.table("odi_database").select("*").ilike("Brand_Names", f"%{query}%").execute()
        
        results['drug'] = pd.DataFrame(res_odi.data)
        
        # Se troviamo un farmaco, estraiamo il target per espandere la ricerca
        if not results['drug'].empty:
            raw_target = str(results['drug'].iloc[0]['Targets'])
            results['active_target_id'] = raw_target.split('(')[0].split(';')[0].strip().upper()
    except: pass

    target_to_lookup = results['active_target_id']

    # 2. Cerca nel database Molecolare (AXON)
    try:
        res_axon = supabase.table("axon_knowledge").select("*").eq("target_id", target_to_lookup).execute()
        results['target_axon'] = pd.DataFrame(res_axon.data)
    except: pass

    # 3. Cerca nei Pathway (PMI)
    try:
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{target_to_lookup}%").execute()
        results['pathways'] = pd.DataFrame(res_pmi.data)
    except: pass

    # 4. Cerca nei Trial (GCI)
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{target_to_lookup}%").execute()
        results['trials'] = pd.DataFrame(res_gci.data)
    except: pass

    return results

# Caricamento base AXON per ragnatela
df_axon_full = load_axon()

# --- 3. SIDEBAR: OMNI-SEARCH ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Omni-Search")

main_query = st.sidebar.text_input("🔍 Cerca Farmaco o Target", placeholder="es. pembro, KRAS, HER2").strip()

st.sidebar.divider()
min_sig = st.sidebar.slider("Soglia VTG", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite TMI", 0.0, 1.0, 0.8)

# --- 4. ESECUZIONE RICERCA UNIFICATA ---
intel = search_all_databases(main_query)
target_id = intel['active_target_id']

# --- 5. DASHBOARD HEADER & OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if main_query:
    st.markdown(f"### 🌐 Analisi Integrata per: `{main_query.upper()}`")
    
    # Visualizzazione Farmaco Trovato (se presente)
    if not intel['drug'].empty:
        d = intel['drug'].iloc[0]
        st.success(f"💊 **Farmaco Rilevato:** {d['Generic_Name']} ({d['Brand_Names']}) | **Target Mappato:** {target_id}")

    # Opera Director (Griglia 10 Parametri)
    if not intel['target_axon'].empty:
        row = intel['target_axon'].iloc[0]
        # Calcolo CES se mancante
        ces = row['initial_score'] * (1 - row['toxicity_index'])
        
        st.markdown(f"#### 🎼 Opera Director: {target_id}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(intel['pathways'])} Path")
        c3.metric("ODI", "LINKED" if not intel['drug'].empty else "SEARCHING")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{ces:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("BCI", "OPTIMAL"); c7.metric("GNI", "STABLE"); c8.metric("EVI", "LOW RISK"); c9.metric("MBI", "RESILIENT")
        phase = intel['trials']['Phase'].iloc[0] if not intel['trials'].empty else "PRE-CLIN"
        c10.metric("GCI", phase)
        st.divider()

# --- 6. RAGNATELA DINAMICA ---
st.subheader("🕸️ Network Interaction Map")
# Prepariamo i dati per la ragnatela
if not df_axon_full.empty:
    if target_id in df_axon_full['target_id'].values:
        # Prendi il target e i top 6 hub per creare una rete densa
        exact = df_axon_full[df_axon_full['target_id'] == target_id]
        others = df_axon_full[df_axon_full['target_id'] != target_id].sort_values('initial_score', ascending=False).head(6)
        f_df = pd.concat([exact, others]).drop_duplicates()
    else:
        f_df = df_axon_full[(df_axon_full['initial_score'] >= min_sig) & (df_axon_full['toxicity_index'] <= max_t)].head(10)

    if not f_df.empty:
        G = nx.Graph()
        for _, r in f_df.iterrows():
            tid = str(r['target_id'])
            is_f = tid == target_id
            G.add_node(tid, size=float(r['initial_score']) * (60 if is_f else 30), color=float(r['toxicity_index']))
            if is_f: # Connetti il focus a tutti gli altri
                for n in f_df['target_id']:
                    if n != tid: G.add_edge(tid, n)
        
        pos = nx.spring_layout(G, k=1.0, seed=42)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
        fig = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#666'), mode='lines', hoverinfo='none'),
            go.Scatter(x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()], 
                       mode='markers+text', text=list(G.nodes()), textposition="top center",
                       marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], color=[G.nodes[n]['color'] for n in G.nodes()],
                       colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
        ])
        fig.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig, use_container_width=True)

# --- 7. DEEP DIVE TABS ---
st.divider()
t1, t2, t3 = st.tabs(["💊 Therapeutics (ODI)", "🧬 Pathways (SMI/PMI)", "🧪 Clinical Trials (GCI)"])

with t1:
    if not intel['drug'].empty: st.dataframe(intel['drug'], use_container_width=True)
    else: st.info("Cerca un farmaco per vedere i dettagli ODI.")

with t2:
    if not intel['pathways'].empty:
        for _, p in intel['pathways'].iterrows():
            with st.expander(f"Pathway: {p['Canonical_Name']}"):
                st.write(p['Description_L0'])
                st.caption(f"Priority: {p['Evidence_Priority']}")
    else: st.info("Nessun pathway correlato trovato.")

with t3:
    if not intel['trials'].empty: st.dataframe(intel['trials'][['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)
    else: st.info("Nessun trial clinico trovato.")

st.caption("MAESTRO Omni-Search v8.0 | Integrated Logic")
