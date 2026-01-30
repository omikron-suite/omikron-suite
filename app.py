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
search_query = st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS").strip().upper()
st.sidebar.warning("⚠️ **Research Use Only**\n\nNot for use in diagnostic or therapeutic procedures.")

# --- 4. LOGICA DI FILTRO AVANZATA ---
if search_query and not df.empty:
    main_target_df = df[df['target_id'].str.upper() == search_query]
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

# --- 5. DASHBOARD ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

# --- NUOVO CARTIGLIO INFORMATIVO (TARGET CARD) ---
if search_query and not df.empty:
    target_data = df[df['target_id'].str.upper() == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"### 🎯 Target Intelligence Card: {search_query}")
        
        # Creazione del cartiglio con 4 metriche chiave
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            st.metric(label="VTG Signal Score", value=f"{row['initial_score']:.2f}", help="Potenza del segnale molecolare iniziale")
        with m2:
            tox_label = "SICURO" if row['toxicity_index'] < 0.4 else "MODERATO" if row['toxicity_index'] < 0.7 else "CRITICO"
            st.metric(label="TMI Toxicity Index", value=tox_label, delta=f"{row['toxicity_index']:.2f}", delta_color="inverse")
        with m3:
            st.metric(label="CES Efficiency", value=f"{row['ces_score']:.2f}", help="Combined Efficiency Score (Signal x Safety)")
        with m4:
            # Check rapido su GCI per vedere se ci sono trial
            try:
                gci_check = supabase.table("GCI_clinical_trials").select("Phase").ilike("Primary_Biomarker", f"%{search_query}%").execute()
                status = "In Trial" if gci_check.data else "Pre-clinico"
                st.metric(label="Clinical Status", value=status)
            except:
                st.metric(label="Clinical Status", value="N/D")
        st.markdown("---")

st.markdown(f"**Focus Mode:** {search_query if search_query else 'Global View'}")

# --- GRAFICI AXON ---
col1, col2 = st.columns([2, 1])
with col1:
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
with col2:
    if not filtered_df.empty:
        st.subheader("🥇 Top Neighbors")
        st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# --- 6. RAGNATELA DINAMICA ---
st.divider()
st.subheader("🕸️ Network Interaction Map (Relational Focus)")

if not filtered_df.empty:
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        is_focus = row['target_id'].upper() == search_query
        G.add_node(row['target_id'], 
                   size=float(row['initial_score']) * (40 if is_focus else 25), 
                   color=float(row['toxicity_index']))
    
    nodes = list(G.nodes())
    if search_query in nodes:
        for node in nodes:
            if node != search_query:
                G.add_edge(search_query, node)
    elif len(nodes) > 1:
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 3, len(nodes))):
                G.add_edge(nodes[i], nodes[j])

    pos = nx.spring_layout(G, k=0.8, seed=42)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#999'), mode='lines', hoverinfo='none')

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y); node_text.append(node)
        node_color.append(G.nodes[node]['color']); node_size.append(G.nodes[node]['size'])

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="top center",
        marker=dict(showscale=True, colorscale='RdYlGn_r', color=node_color, size=node_size, 
                    line=dict(color='white', width=2))
    )

    st.plotly_chart(go.Figure(data=[edge_trace, node_trace], layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')), use_container_width=True)

# --- 7. GCI PORTAL ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")
if search_query:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        if not gci_df.empty:
            st.success(f"Trovate {len(gci_df)} evidenze per '{search_query}'")
            st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type', 'Key_Results_PFS']], use_container_width=True)
        else:
            st.warning(f"Nessun dato clinico trovato per '{search_query}'")
    except:
        st.error("Errore di connessione al database clinico.")

# --- FOOTER ---
st.divider()
st.caption("""
    **Disclaimer:** This platform is for research purposes only (RUO). 
    Data provided by AXON Knowledge and GCI Database are intended for scientific analysis 
    and do not constitute medical advice or clinical guidelines.
""")
