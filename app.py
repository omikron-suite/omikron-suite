import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- CONFIGURAZIONE DASHBOARD ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- CONNESSIONE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    res = supabase.table("axon_knowledge").select("*").execute()
    d = pd.DataFrame(res.data)
    d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
    return d

df = load_axon()

# --- SIDEBAR RIORGANIZZATA ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Orchestra Control")

st.sidebar.markdown("""
### 🎚️ VTG Gate Settings
Il **VTG Gate** filtra i target in base alla qualità del segnale e al rischio biologico.
""")

# 1. Slider Efficacia
min_sig = st.sidebar.slider(
    "Soglia Minima Segnale (VTG)", 
    0.0, 3.0, 0.8,
    help="Definisce il limite inferiore per la potenza del segnale molecolare (Initial Score)."
)
st.sidebar.caption("💡 *Sotto 0.8 il segnale è considerato rumore di fondo.*")

# 2. Slider Tossicità
max_t = st.sidebar.slider(
    "Limite Tossicità (TMI)", 
    0.0, 1.0, 0.8,
    help="Indice di Tossicità Molecolare (TMI). Più basso è il valore, più sicuro è il target."
)
st.sidebar.caption("⚠️ *Sopra 0.7 il rischio di tossicità off-target aumenta.*")

st.sidebar.divider()

# 3. Ricerca Specifica (Sotto gli slider)
st.sidebar.markdown("### 🔍 Target Intelligence")
search_query = st.sidebar.text_input(
    "Cerca Target Specifico", 
    placeholder="es. HER2, BRCA, PD-L1",
    help="Digita il nome del biomarker per attivare il cross-referencing con il Database GCI."
).strip()

if search_query:
    st.sidebar.success(f"Focus su: **{search_query}**")
    filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)]

# --- TITOLO PRINCIPALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")
st.markdown("---")

# --- LAYOUT DASHBOARD ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Analisi Efficacia vs Tossicità (AXON Knowledge)")
    fig = px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                 color_continuous_scale="RdYlGn_r", template="plotly_dark",
                 labels={'initial_score': 'Segnale VTG', 'toxicity_index': 'Rischio TMI'})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🥇 Top Efficiency Targets")
    top_5 = filtered_df.sort_values('ces_score', ascending=False).head(10)
    st.dataframe(top_5[['target_id', 'ces_score', 'initial_score']], use_container_width=True)

# Ragnatela
st.divider()
st.subheader("🕸️ Network Interaction Map (AXON Web)")
# [Image of a network graph showing molecular target interactions with nodes colored by safety profile]
if not filtered_df.empty:
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        G.add_node(row['target_id'], size=float(row['initial_score'])*20, color=float(row['toxicity_index']))
    nodes = list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i + 1, min(i + 5, len(nodes))):
            G.add_edge(nodes[i], nodes[j])
    pos = nx.spring_layout(G, k=0.5)
    node_x, node_y, node_color, node_size = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y)
        node_color.append(G.nodes[node]['color']); node_size.append(G.nodes[node]['size'])
    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=nodes, textposition="bottom center", 
                            marker=dict(showscale=True, colorscale='RdYlGn_r', color=node_color, size=node_size))
    st.plotly_chart(go.Figure(data=[node_trace], layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
                                                                 paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')), use_container_width=True)

# --- INTEGRAZIONE GCI ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI Database)")

if search_query:
    try:
        # Recupero dalla tabella a 62 colonne
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        
        if not gci_df.empty:
            st.success(f"Trovate {len(gci_df)} evidenze cliniche per '{search_query}'")
            # Mostriamo una selezione intelligente delle 62 colonne per non affollare la vista
            cols_pro = ['Canonical_Title', 'Phase', 'Year', 'Cancer_Type', 'Practice_Changing', 'Key_Results_PFS', 'Main_Toxicities']
            available = [c for c in cols_pro if c in gci_df.columns]
            st.dataframe(gci_df[available], use_container_width=True)
            
            with st.expander("🔍 Visualizza Deep Data (Tutte le 62 colonne)"):
                st.write(gci_df)
        else:
            st.warning(f"Nessuna evidenza clinica nel Database GCI per '{search_query}'.")
    except Exception as e:
        st.error(f"Errore caricamento dati clinici: {e}")
else:
    st.info("💡 Digita un biomarker nella barra laterale (es. HER2) per caricare i trial clinici dal database GCI.")
