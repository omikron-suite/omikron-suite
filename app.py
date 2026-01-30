import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Omikron Orchestra Suite", layout="wide")

# --- 2. PASSWORD ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("Inserisci la chiave d'accesso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.error("😕 Accesso negato")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. CONNESSIONE SUPABASE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon_data():
    res = supabase.table("axon_knowledge").select("*").execute()
    df = pd.DataFrame(res.data)
    df['ces_score'] = df['initial_score'] * (1 - df['toxicity_index'])
    return df

df = load_axon_data()

# --- 4. SIDEBAR & FILTRI ---
st.title("🛡️ Omikron Orchestra Suite")
st.sidebar.header("Parametri VTG Gate")
min_sig = st.sidebar.slider("Soglia Minima Segnale", 0.0, 3.0, 0.8)
max_tox = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)
search_query = st.sidebar.text_input("🔍 Cerca Target Specifico (es. HER2)", "").strip()

if search_query:
    filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_tox)]

# --- 5. ANALISI GRAFICA (AXON) ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Analisi Efficacia vs Tossicità")
    fig = px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index",
                 color_continuous_scale="RdYlGn_r", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🥇 Top Target (Efficiency)")
    top_5 = filtered_df.sort_values('ces_score', ascending=False).head(5)
    st.dataframe(top_5[['target_id', 'ces_score']], use_container_width=True)

# --- 6. RAGNATELA (AXON Web) ---
st.divider()
st.subheader("🕸️ Network Interaction Map (AXON Web)")

if not filtered_df.empty:
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        G.add_node(row['target_id'], size=float(row['initial_score'])*20, color=float(row['toxicity_index']))
    
    nodes = list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i + 1, min(i + 5, len(nodes))):
            G.add_edge(nodes[i], nodes[j])

    pos = nx.spring_layout(G, k=0.5)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), mode='lines', hoverinfo='none')
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y); node_text.append(node)
        node_color.append(G.nodes[node]['color']); node_size.append(G.nodes[node]['size'])

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="bottom center",
                            marker=dict(showscale=True, colorscale='RdYlGn_r', color=node_color, size=node_size))

    fig_net = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
                                                                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 7. INTEGRAZIONE CLINICA (GCI DATABASE) ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")

if search_query:
    try:
        # Recupero dinamico per evitare errori di colonne
        res_gci = supabase.table("clinical_trials").select("*").execute()
        gci_df = pd.DataFrame(res_gci.data)
        
        if not gci_df.empty:
            # Troviamo la colonna Primary_Biomarker (case-insensitive)
            col_target = next((c for c in gci_df.columns if c.lower() == 'primary_biomarker'), None)
            
            if col_target:
                trials = gci_df[gci_df[col_target].str.contains(search_query, case=False, na=False)]
                
                if not trials.empty:
                    st.success(f"Trovate {len(trials)} evidenze cliniche per '{search_query}'")
                    cols_to_show = ['Canonical_Title', 'Phase', 'Year', 'Cancer_Type', 'Key_Results_PFS', 'Main_Toxicities']
                    # Filtriamo solo le colonne che esistono davvero
                    actual_cols = [c for c in trials.columns if c in cols_to_show]
                    st.dataframe(trials[actual_cols], use_container_width=True)
                else:
                    st.warning(f"Nessun dato clinico GCI per '{search_query}'.")
            else:
                st.error("Colonna 'Primary_Biomarker' non trovata nel database GCI.")
    except Exception as e:
        st.error(f"Errore caricamento dati clinici: {e}")
else:
    st.info("💡 Cerca un biomarker nella sidebar per vedere i dati clinici correlati.")
