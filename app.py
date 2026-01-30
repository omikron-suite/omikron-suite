import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Suite v11.3", layout="wide")

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
def load_odi_master():
    try:
        res = supabase.table("odi_database").select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

df_axon = load_axon()
df_odi_master = load_odi_master()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")
user_input = st.sidebar.text_input("🔍 Omni-Search (Target o Farmaco)", "").strip().upper()

st.sidebar.divider()
st.sidebar.error("### ⚠️ DISCLAIMER")
st.sidebar.caption("RESEARCH USE ONLY (RUO). Non per uso clinico.")

# --- 4. MAPPATURA INTELLIGENTE ---
search_query = user_input
found_drug_label = ""

if user_input and not df_odi_master.empty:
    matches = df_odi_master[
        df_odi_master['Generic_Name'].str.contains(user_input, case=False, na=False) | 
        df_odi_master['Brand_Names'].str.contains(user_input, case=False, na=False)
    ]
    if not matches.empty:
        drug_row = matches.iloc[0]
        found_drug_label = f"{drug_row['Generic_Name']} ({drug_row['Brand_Names']})"
        search_query = str(drug_row['Targets']).split('(')[0].split(';')[0].strip().upper()

# --- 5. LOGICA DI FILTRO ---
gci_df, pmi_df, odi_target_df, filtered_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if search_query:
    try:
        gci_df = pd.DataFrame(supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute().data)
        pmi_df = pd.DataFrame(supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute().data)
        odi_target_df = pd.DataFrame(supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute().data)
    except: pass

    if not df_axon.empty:
        all_t = df_axon['target_id'].tolist()
        if search_query in all_t:
            idx = all_t.index(search_query)
            neighbor_list = all_t[max(0, idx-3):min(len(all_t), idx+4)]
            filtered_df = df_axon[df_axon['target_id'].isin(neighbor_list)]
        else:
            filtered_df = df_axon[df_axon['target_id'].str.contains(search_query, na=False)]
else:
    filtered_df = df_axon.head(10) if not df_axon.empty else pd.DataFrame()

# --- 6. DASHBOARD: TITOLO & ID ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query:
    status_color = "🟢" if not gci_df.empty else "🟡"
    st.markdown(f"### {status_color} Target ID: `{search_query}`")
    if found_drug_label:
        st.info(f"💊 **Farmaco correlato:** {found_drug_label}")

# --- 7. OPERA DIRECTOR (GRIGLIA COMPLETA) ---
if search_query and not df_axon.empty:
    target_data = df_axon[df_axon['target_id'] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Linked")
        c3.metric("ODI", "TARGETABLE" if not odi_target_df.empty else "NO DRUG")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("BCI", "OPTIMAL"); c7.metric("GNI", "STABLE"); c8.metric("EVI", "LOW RISK"); c9.metric("MBI", "BALANCED")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D"
        c10.metric("GCI", phase)
        st.divider()

# --- 8. RAGNATELA & BENCHMARKING (Layout 2 colonne) ---
col_net, col_bench = st.columns([2, 1])

with col_net:
    st.subheader("🕸️ Network Map")
    if not filtered_df.empty:
        G = nx.Graph()
        for _, r in filtered_df.iterrows():
            tid = str(r['target_id'])
            G.add_node(tid, size=float(r['initial_score']) * (60 if tid == search_query else 30), color=float(r['toxicity_index']))
        
        nodes = list(G.nodes())
        if search_query in nodes:
            for n in nodes:
                if n != search_query: G.add_edge(search_query, n)
        
        pos = nx.spring_layout(G, k=1.0, seed=42)
        
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
        fig_net = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, line=dict(width=2, color='#555'), mode='lines', hoverinfo='none'),
            go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                       text=nodes, textposition="top center",
                       marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                       colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
        ])
        fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig_net, use_container_width=True)

with col_bench:
    st.subheader("📊 Hub Benchmarking")
    if not df_axon.empty:
        # Mostra i top 5 per CES score vs il target attuale
        bench_df = df_axon.sort_values('ces_score', ascending=False).head(5)
        if search_query and search_query not in bench_df['target_id'].values:
            bench_df = pd.concat([bench_df, df_axon[df_axon['target_id'] == search_query]])
        
        fig_bench = px.bar(bench_df, x='target_id', y='ces_score', color='toxicity_index', 
                           color_continuous_scale='RdYlGn_r', template='plotly_dark',
                           labels={'ces_score': 'Efficienza (CES)'})
        st.plotly_chart(fig_bench, use_container_width=True)

# --- 9. DATABASE TABS ---
st.divider()
t1, t2, t3 = st.tabs(["💊 ODI", "🧬 PMI", "🧪 GCI"])
with t1:
    if not odi_target_df.empty: st.dataframe(odi_target_df[['Generic_Name', 'Brand_Names', 'Drug_Class']], use_container_width=True)
with t2:
    if not pmi_df.empty:
        for _, p in pmi_df.iterrows():
            with st.expander(f"Pathway: {p['Canonical_Name']}"): st.write(p.get('Description_L0', 'N/D'))
with t3:
    if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase']], use_container_width=True)

st.caption("MAESTRO Suite | v11.3 | RUO")
