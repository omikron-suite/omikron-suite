import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE PAGINA ---
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
    except Exception as e:
        st.error(f"Errore caricamento AXON: {e}")
        return pd.DataFrame()

df = load_axon()

# --- 3. SIDEBAR (Pannello di Controllo) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

st.sidebar.markdown("### 🎚️ Parametri VTG Gate")

# Slider Efficacia
min_sig = st.sidebar.slider(
    "Soglia Minima Segnale (VTG)", 
    0.0, 3.0, 0.8,
    help="Filtra i target in base alla potenza del segnale molecolare."
)
st.sidebar.caption("💡 *Sotto 0.8 è considerato rumore di fondo.*")

# Slider Tossicità
max_t = st.sidebar.slider(
    "Limite Tossicità (TMI)", 
    0.0, 1.0, 0.8,
    help="Indice di Tossicità Molecolare. Più basso è più sicuro."
)
st.sidebar.caption("⚠️ *Sopra 0.7 il rischio off-target è elevato.*")

st.sidebar.divider()

# Ricerca Target
st.sidebar.markdown("### 🔍 Target Intelligence")
search_query = st.sidebar.text_input(
    "Cerca Target Specifico", 
    placeholder="es. KRAS, HER2, EGFR",
    help="Cerca un biomarker specifico per l'incrocio dati AXON/GCI."
).strip()

# Logica di Filtro
if search_query:
    filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)]

# --- 4. DASHBOARD PRINCIPALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Analisi Efficacia vs Tossicità (AXON)")
    if not filtered_df.empty:
        fig = px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                     color_continuous_scale="RdYlGn_r", template="plotly_dark",
                     labels={'initial_score': 'Segnale VTG', 'toxicity_index': 'Rischio TMI'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun dato AXON corrispondente ai filtri.")

with col2:
    st.subheader("🥇 Top Efficiency Targets")
    if not filtered_df.empty:
        top_targets = filtered_df.sort_values('ces_score', ascending=False).head(10)
        st.dataframe(top_targets[['target_id', 'ces_score']], use_container_width=True)

# --- 5. RAGNATELA (Network Interaction Map) ---
st.divider()
st.subheader("🕸️ Network Interaction Map (AXON Web)")

if not filtered_df.empty:
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        G.add_node(row['target_id'], 
                   size=float(row.get('initial_score', 1)) * 20, 
                   color=float(row.get('toxicity_index', 0.5)))
    
    nodes = list(G.nodes())
    # Crea connessioni se ci sono più nodi
    if len(nodes) > 1:
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 3, len(nodes))):
                G.add_edge(nodes[i], nodes[j])
    
    pos = nx.spring_layout(G, k=1.0, seed=42)
    
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#555'), mode='lines', hoverinfo='none')

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y); node_text.append(node)
        node_color.append(G.nodes[node]['color']); node_size.append(G.nodes[node]['size'])

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=node_text, 
        textposition="top center",
        marker=dict(showscale=True, colorscale='RdYlGn_r', color=node_color, size=node_size, line_width=2)
    )

    fig_net = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 6. PORTALE CLINICO (GCI) ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI Database)")

if search_query:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        
        if not gci_df.empty:
            st.success(f"Trovate {len(gci_df)} evidenze cliniche per '{search_query}'")
            # Mostriamo colonne chiave
            cols_key = ['Canonical_Title', 'Phase', 'Year', 'Cancer_Type', 'Practice_Changing', 'Key_Results_PFS', 'Main_Toxicities']
            available = [c for c in cols_key if c in gci_df.columns]
            st.dataframe(gci_df[available], use_container_width=True)
        else:
            st.warning(f"Nessuna evidenza clinica nel Database GCI per '{search_query}'.")
    except Exception as e:
        st.error(f"Errore GCI: {e}")
else:
    st.info("💡 Digita un biomarker nella barra laterale per caricare i trial clinici dal database GCI.")
