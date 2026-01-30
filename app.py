import streamlit as st
# ... gli altri import rimangono uguali ...

def check_password():
    """Restituisce True se l'utente ha inserito la password corretta."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Rimuove la password dalla memoria
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Visualizza l'input per la password
        st.text_input("Inserisci la chiave d'accesso per Omikron Orchestra", 
                     type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Password errata
        st.text_input("Password errata. Riprova:", 
                     type="password", on_change=password_entered, key="password")
        st.error("😕 Accesso negato")
        return False
    else:
        # Password corretta
        return True

if not check_password():
    st.stop()  # Ferma l'esecuzione se la password non è corretta

# --- DA QUI IN POI IL TUO CODICE ESISTENTE ---
# st.set_page_config(...) ecc.







import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- CONFIGURAZIONE DASHBOARD ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

# --- CONNESSIONE DATABASE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

# --- RECUPERO DATI ---
@st.cache_data(ttl=600)
def load_data():
    response = supabase.table("axon_knowledge").select("*").execute()
    df = pd.DataFrame(response.data)
    # Calcolo Clinical Efficiency Score
    df['ces_score'] = df['initial_score'] * (1 - df['toxicity_index'])
    return df

df = load_data()




# --- SIDEBAR DI CONTROLLO ---
st.sidebar.header("Parametri VTG Gate")
min_signal = st.sidebar.slider("Soglia Minima Segnale", 0.0, 3.0, 0.8)
max_tox = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)



# --- RICERCA POTENZIATA ---
st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Cerca Target Specifico", "").strip()

if search_query:
    # Cerchiamo in modo "case-insensitive" (ignora maiuscole/minuscole)
    # e rimuoviamo eventuali spazi vuoti
    filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
    
    if filtered_df.empty:
        st.sidebar.warning(f"Nessun risultato per '{search_query}'")
    else:
        st.sidebar.success(f"Trovati {len(filtered_df)} match!")
else:
    # Se la ricerca è vuota, usa i filtri degli slider
    filtered_df = df[(df['initial_score'] >= min_signal) & (df['toxicity_index'] <= max_tox)]





# Filtro dinamico
#filtered_df = df[(df['initial_score'] >= min_signal) & (df['toxicity_index'] <= max_tox)]



# --- TASTO EXPORT REPORT ---
st.sidebar.divider()
st.sidebar.subheader("💾 Backup & Report")

# Trasforma il dataframe filtrato in CSV
csv = filtered_df.to_csv(index=False).encode('utf-8')

st.sidebar.download_button(
    label="📥 Scarica Report AXON (CSV)",
    data=csv,
    file_name='omikron_suite_report.csv',
    mime='text/csv',
    help="Scarica i dati attualmente visualizzati in formato Excel/CSV"
)






# --- LAYOUT PRINCIPALE ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Analisi Efficacia vs Tossicità")
    fig = px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index",
                 color_continuous_scale="RdYlGn_r", template="plotly_dark",
                 labels={'initial_score': 'Potenza d\'Urto', 'toxicity_index': 'Rischio TMI'})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🥇 Top Target (Efficiency Score)")
    top_5 = filtered_df.sort_values('ces_score', ascending=False).head(5)
    st.dataframe(top_5[['target_id', 'initial_score', 'toxicity_index', 'ces_score']], use_container_width=True)

# --- NETWORK GRAPH (SOTTO) ---
st.divider()
st.subheader("🕸️ Network Interaction Map (AXON Web)")
# Qui il codice per la ragnatela che abbiamo testato su Colab

# ... (lo caricheremo nel file completo su GitHub)





# --- CODICE AGGIORNATO PER LA RAGNATELA (AXON Web) ---
st.divider()
st.subheader("🕸️ Network Interaction Map (AXON Web)")

if not filtered_df.empty:
    G = nx.Graph()
    
    # Aggiunta nodi con parametri di sicurezza
    for i, row in filtered_df.iterrows():
        # Assicuriamoci che i valori siano numerici
        size_val = float(row['initial_score']) * 20 if pd.notnull(row['initial_score']) else 10
        tox_val = float(row['toxicity_index']) if pd.notnull(row['toxicity_index']) else 0.5
        G.add_node(row['target_id'], size=size_val, color=tox_val)

    # Connessioni logiche tra i target
    target_list = filtered_df['target_id'].tolist()
    for i in range(len(target_list)):
        for j in range(i + 1, min(i + 5, len(target_list))): # Limita le connessioni per chiarezza
            G.add_edge(target_list[i], target_list[j])

    pos = nx.spring_layout(G, k=0.5)

    # Tracciamento Linee
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')

    # Tracciamento Nodi
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y)
        node_text.append(node)
        node_color.append(G.nodes[node]['color'])
        node_size.append(G.nodes[node]['size'])

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=node_text,
        textposition="bottom center", hoverinfo='text',
        marker=dict(
            showscale=True, colorscale='RdYlGn_r', color=node_color,
            size=node_size, colorbar=dict(thickness=15, title='Rischio TMI')
        )
    )

    fig_network = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
                 paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                 xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                 yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))

    st.plotly_chart(fig_network, use_container_width=True)
else:
    st.warning("⚠️ Nessun target corrisponde ai filtri selezionati. Regola gli slider per visualizzare la rete.")




# ... (fine del codice della ragnatela) ...


# --- INTEGRAZIONE GCI DATABASE ---
    if search_query:
        st.divider()
        st.header(f"📑 Evidence Report: {search_query}")
        
        try:
            # Cerchiamo il target nelle colonne chiave del tuo file GCI
            clinical_res = supabase.table("clinical_trials").select("*").or_(
                f"Primary_Biomarker.ilike.%{search_query}%,Target_Gene_Variant.ilike.%{search_query}%"
            ).execute()
            
            trials = pd.DataFrame(clinical_res.data)
            
            if not trials.empty:
                # Metriche basate sulle tue colonne reali
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Trial Totali", len(trials))
                with m2:
                    # Usiamo la tua colonna 'Practice_Changing'
                    pc_count = len(trials[trials['Practice_Changing'] == 'Yes'])
                    st.metric("Practice Changing", pc_count)
                with m3:
                    # Usiamo la colonna 'Phase'
                    top_phase = trials['Phase'].mode()[0] if 'Phase' in trials.columns else "N/A"
                    st.metric("Fase Prevalente", top_phase)

                # Tabella Dettagliata con le tue colonne
                st.subheader("Dettaglio Studi Clinici (GCI Database)")
                # Selezioniamo solo le colonne che esistono nel tuo CSV
                cols_to_show = ['Canonical_Title', 'Phase', 'Year', 'Cancer_Type', 'Key_Results_PFS', 'Main_Toxicities']
                # Filtriamo solo quelle effettivamente presenti per evitare errori
                existing_cols = [c for c in cols_to_show if c in trials.columns]
                
                st.dataframe(trials[existing_cols], use_container_width=True)
            else:
                st.info(f"Nessun trial clinico trovato per '{search_query}'. Prova con 'HER2' o 'PD-L1'.")
                
        except Exception as e:
            st.error(f"Errore di connessione: Verifica che la tabella si chiami 'clinical_trials'. Dettaglio: {e}")
