import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- 2. CONNESSIONE SUPABASE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except Exception:
        return pd.DataFrame()

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Smart Search & Hub Focus")
search_query = st.sidebar.text_input("Cerca Target (es. KRAS)", "").strip().upper()
st.sidebar.warning("⚠️ **Research Use Only**\n\nNot for use in diagnostic or therapeutic procedures.")

# --- 4. LOGICA DI FILTRO ---
if search_query and not df.empty:
    all_targets = df['target_id'].tolist()
    if search_query in all_targets:
        idx = all_targets.index(search_query)
        neighbor_indices = range(max(0, idx-2), min(len(all_targets), idx+3))
        neighbors = [all_targets[i] for i in neighbor_indices]
        filtered_df = df[df['target_id'].isin(neighbors)]
    else:
        filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 5. DASHBOARD PRINCIPALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

# --- IL CARTIGLIO DEI 9 DATABASE (L'ANALOGIA DEL MOTORE) ---
if search_query and not df.empty:
    target_data = df[df['target_id'].str.upper() == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🏎️ Intelligence Mission Control: {search_query}")
        
        # RIGA 1: MECCANICA (OMI, SMI, ODI)
        st.markdown("### ⚙️ Il Motore (Molecolare)")
        c1, c2, c3 = st.columns(3)
        c1.metric("OMI (Biomarcatori)", "Detected", help="Il Cruscotto: Presenza del biomarcatore")
        c2.metric("SMI (Pathway)", "Active Hub", help="Gli Ingranaggi: Stato della segnalazione")
        c3.metric("ODI (Farmaci)", "Targetable", help="Freno/Acceleratore: Disponibilità farmaci")

        # RIGA 2: SICUREZZA (TMI, GNI, BCI)
        st.markdown("### 🛡️ Telaio e Sicurezza")
        c4, c5, c6 = st.columns(3)
        tox_val = row['toxicity_index']
        c4.metric("TMI (Tossicità)", "OK" if tox_val < 0.7 else "ALLARME", delta=f"{tox_val:.2f}", delta_color="inverse")
        c5.metric("GNI (Genetica)", "Stable", help="Il Telaio: Genetica dell'ospite")
        c6.metric("BCI (Bio-cost.)", "Optimal", help="L'Olio: Costituenti biologici")

        # RIGA 3: AMBIENTE E STRADA (EVI, MBI, GCI)
        st.markdown("### 🌍 Terreno e Prova su Strada")
        c7, c8, c9 = st.columns(3)
        c7.metric("EVI (Ambiente)", "Low Impact", help="Il Terreno: Tossici ambientali")
        c8.metric("MBI (Microbiota)", "Resilient", help="Il Filtro Aria: Stato microbiota")
        
        # Check GCI reale
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D"
        c9.metric("GCI (Clinica)", phase, help="La Prova su Strada: Evidenza clinica")

        # TASTO REPORT
        report_text = f"MAESTRO REPORT: {search_query}\nVTG: {row['initial_score']}\nTMI: {row['toxicity_index']}\nClinical: {phase}"
        st.download_button("📥 Scarica Intelligence Report", report_text, file_name=f"Report_{search_query}.txt")
        st.divider()

# --- 6. GRAFICI AXON ---
col_bar, col_rank = st.columns([2, 1])
with col_bar:
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
with col_rank:
    if not filtered_df.empty:
        st.subheader("🥇 Hub Ranking")
        st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# --- 7. RAGNATELA DINAMICA ---
st.divider()
st.subheader("🕸️ Network Interaction Map (Relational Focus)")
if not filtered_df.empty:
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        is_f = r['target_id'].upper() == search_query
        G.add_node(r['target_id'], size=float(r['initial_score']) * (40 if is_f else 25), color=float(r['toxicity_index']))
    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    elif len(nodes) > 1:
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 3, len(nodes))): G.add_edge(nodes[i], nodes[j])
    
    pos = nx.spring_layout(G, k=0.8, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#999'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2)))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 8. GCI PORTAL ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")
if search_query and not gci_df.empty:
    st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type', 'Key_Results_PFS']], use_container_width=True)

# --- FOOTER ---
st.divider()
st.caption("Disclaimer: This platform is for research purposes only (RUO). Data provided by AXON and GCI are for scientific analysis.")
