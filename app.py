import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- CONFIGURAZIONE E CONNESSIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

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
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=80)
st.sidebar.title("Parametri di Controllo")

st.sidebar.markdown("""
### 🎚️ VTG Gate Thresholds
Regola le soglie per filtrare i target nel database AXON.
""")

# Slider 1: Segnale
min_sig = st.sidebar.slider(
    "Soglia Minima Segnale (VTG)", 
    0.0, 3.0, 0.8,
    help="Valore minimo di potenza d'urto del segnale molecolare rilevato."
)
st.sidebar.caption("Sotto 0.8: Rumore di fondo. Sopra 2.0: Segnale forte.")

# Slider 2: Tossicità
max_t = st.sidebar.slider(
    "Limite Tossicità (TMI)", 
    0.0, 1.0, 0.8,
    help="Indice di tossicità massima accettabile (TMI). 0 è sicuro, 1 è tossico."
)
st.sidebar.caption("Valore ottimale: < 0.4 per massima sicurezza.")

st.sidebar.divider()

# Ricerca (ora sotto gli slider)
st.sidebar.markdown("### 🔍 Target Intelligence")
search_query = st.sidebar.text_input(
    "Cerca Target Specifico", 
    placeholder="es. HER2, BRCA, PD-1",
    help="Digita un biomarker per attivare il cross-referencing clinico GCI."
).strip()

if search_query:
    st.sidebar.info(f"Modalità Focus attiva su: **{search_query}**")
    filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)]

# --- LAYOUT DASHBOARD (AXON) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("Analisi Efficacia vs Tossicità (AXON)")
    st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                           color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
with col2:
    st.subheader("🥇 Top Target (Efficiency)")
    st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# Ragnatela
st.divider()
st.subheader("🕸️ Network Interaction Map")
# [Codice ragnatela rimane uguale]
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
    st.plotly_chart(go.Figure(data=[node_trace], layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0))), use_container_width=True)

# --- INTEGRAZIONE GCI ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")
if search_query:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        if not gci_df.empty:
            st.success(f"Trovate {len(gci_df)} evidenze per '{search_query}'")
            st.dataframe(gci_df, use_container_width=True)
        else:
            st.warning(f"Nessun dato clinico per '{search_query}'.")
    except Exception as e:
        st.error(f"Errore GCI: {e}")
else:
    st.info("💡 Inserisci un biomarker nella barra laterale per caricare i trial clinici.")
