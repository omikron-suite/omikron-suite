import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# 1. CONFIGURAZIONE PAGINA (Deve essere la prima istruzione Streamlit)
st.set_page_config(page_title="Omikron Orchestra Suite", layout="wide")

# 2. FUNZIONE PASSWORD
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Inserisci la chiave d'accesso per Omikron Orchestra", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password errata. Riprova:", type="password", on_change=password_entered, key="password")
        st.error("😕 Accesso negato")
        return False
    return True

if not check_password():
    st.stop()

# 3. TITOLO E CONNESSIONE
st.title("🛡️ Omikron Orchestra Suite")

URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

# 4. RECUPERO DATI AXON
@st.cache_data(ttl=600)
def load_data():
    response = supabase.table("axon_knowledge").select("*").execute()
    df = pd.DataFrame(response.data)
    df['ces_score'] = df['initial_score'] * (1 - df['toxicity_index'])
    return df

df = load_data()

# 5. SIDEBAR
st.sidebar.header("Parametri VTG Gate")
min_signal = st.sidebar.slider("Soglia Minima Segnale", 0.0, 3.0, 0.8)
max_tox = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Cerca Target Specifico (es. HER2, PD-L1)", "").strip()

# 6. LOGICA DI FILTRO
if search_query:
    filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_signal) & (df['toxicity_index'] <= max_tox)]

# 7. EXPORT
st.sidebar.divider()
csv = filtered_df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button("📥 Scarica Report AXON", data=csv, file_name='omikron_report.csv', mime='text/csv')

# 8. LAYOUT PRINCIPALE
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Analisi Efficacia vs Tossicità")
    fig = px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index",
                 color_continuous_scale="RdYlGn_r", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🥇 Top Target")
    top_5 = filtered_df.sort_values('ces_score', ascending=False).head(5)
    st.dataframe(top_5[['target_id', 'ces_score']], use_container_width=True)

# --- 9. RAGNATELA (AXON Web) ---
st.divider()
st.subheader("🕸️ Network Interaction Map (AXON Web)")

if not filtered_df.empty:
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        G.add_node(row['target_id'], size=float(row['initial_score'])*20, color=float(row['toxicity_index']))
    
    target_list = filtered_df['target_id'].tolist()
    for i in range(len(target_list)):
        for j in range(i + 1, min(i + 5, len(target_list))):
            G.add_edge(target_list[i], target_list[j])

    pos = nx.spring_layout(G, k=0.5)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), mode='lines')
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y); node_text.append(node)
        node_color.append(G.nodes[node]['color']); node_size.append(G.nodes[node]['size'])

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="bottom center",
                            marker=dict(showscale=True, colorscale='RdYlGn_r', color=node_color, size=node_size))

    fig_net = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0)))
    st.plotly_chart(fig_net, use_container_width=True)
else:
    st.warning("⚠️ Nessun target AXON corrisponde ai filtri.")

# =========================================================
# --- 10. INTEGRAZIONE CLINICAL TRIALS (GCI) ---
# NB: Questo blocco DEVE essere fuori dall' "if not filtered_df.empty"
# =========================================================

st.markdown("---") # Linea di separazione forzata
st.subheader("🧪 Clinical Evidence Portal (GCI Database)")

if search_query:
    st.info(f"Ricerca in corso per il biomarker: **{search_query}**...")
    try:
        # Cerchiamo nel database GCI
        clinical_res = supabase.table("clinical_trials").select("*").or_(
            f"Primary_Biomarker.ilike.%{search_query}%,Target_Gene_Variant.ilike.%{search_query}%"
        ).execute()
        
        trials = pd.DataFrame(clinical_res.data)

        if not trials.empty:
            st.success(f"Trovati {len(trials)} trial clinici nel Database GCI.")
            
            # Layout Metriche
            m1, m2, m3 = st.columns(3)
            m1.metric("Trial Totali", len(trials))
            
            if 'Practice_Changing' in trials.columns:
                pc = len(trials[trials['Practice_Changing'].astype(str).str.contains('Yes', case=False, na=False)])
                m2.metric("Practice Changing", pc)
            
            m3.metric("Fase Prevalente", trials['Phase'].mode()[0] if 'Phase' in trials.columns else "N/A")

            # Tabella Dati
            cols_to_show = ['Canonical_Title', 'Phase', 'Year', 'Cancer_Type', 'Key_Results_PFS', 'Main_Toxicities']
            available_cols = [c for c in cols_to_show if c in trials.columns]
            st.dataframe(trials[available_cols], use_container_width=True)
        else:
            st.warning(f"Nessuna evidenza clinica trovata per '{search_query}'.")
            st.caption("Suggerimento: Prova a cercare 'HER2' o 'PD-1' per testare il database.")
            
    except Exception as e:
        st.error(f"Errore di connessione a 'clinical_trials': {e}")
else:
    st.write("Cerca un target nella barra laterale per attivare il report clinico.")
