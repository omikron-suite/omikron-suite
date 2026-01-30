import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- 2. CONNESSIONE (Diretta e Sicura) ---
# Usa i secrets se ci sono, altrimenti usa le stringhe di default per evitare crash
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")

try:
    supabase = create_client(URL, KEY)
except:
    st.error("Errore critico di connessione al database.")
    st.stop()

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("target_id,initial_score,toxicity_index").execute()
        data = res.data or []
        d = pd.DataFrame(data)
        if d.empty: return d
        # Pulizia dati
        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0).clip(0.0, 1.0)
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except Exception:
        return pd.DataFrame()

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control")

# Ricerca Semplice e Robusta
search_query = st.sidebar.text_input("Inserisci Target / Hub", placeholder="es. KRAS").strip().upper()

# --- LOGICA SATELLITI & CARTELLA ---
odi_df = pd.DataFrame()
pmi_df = pd.DataFrame()
gci_df = pd.DataFrame()

if search_query and not df.empty:
    try:
        # Recupero dati correlati solo se c'è una ricerca
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
        
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])

        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])
    except: pass

# Cartella Farmaci (Appare solo se ci sono risultati)
if not odi_df.empty:
    st.sidebar.divider()
    st.sidebar.success(f"📂 **Cartella Farmaci: {len(odi_df)}**")
    with st.sidebar.expander("Vedi Farmaci"):
        for drug in odi_df['Generic_Name'].unique():
            st.write(f"💊 {drug}")

st.sidebar.divider()
st.sidebar.warning("⚠️ **Research Use Only**")

# --- 4. DASHBOARD & SCORE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_match = df[df["target_id"] == search_query]
    if not target_match.empty:
        row = target_match.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Linked")
        c3.metric("ODI", f"{len(odi_df)} Drugs")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- 5. RAGNATELA (LA PARTE CRITICA) ---
st.subheader("🕸️ Network Interaction Map")

if not df.empty:
    G = nx.Graph()
    
    # --- SCENARIO A: UTENTE HA CERCATO UN HUB ---
    if search_query and search_query in df['target_id'].values:
        # 1. Centro
        G.add_node(search_query, size=60, color='gold', label=f"🎯 {search_query}", type='center')
        
        # 2. Satelliti Farmaci (ODI) -> COLLEGATI
        for _, drug in odi_df.head(5).iterrows():
            d_name = f"💊 {drug['Generic_Name']}"
            G.add_node(d_name, size=25, color='#87CEEB', label=d_name, type='drug')
            G.add_edge(search_query, d_name) # <--- QUESTA RIGA CREA LA LINEA
            
        # 3. Satelliti Pathway (PMI) -> COLLEGATI
        for _, path in pmi_df.head(3).iterrows():
            p_name = f"🧬 {path['Canonical_Name']}"
            G.add_node(p_name, size=25, color='#D8BFD8', label=p_name, type='pathway')
            G.add_edge(search_query, p_name) # <--- QUESTA RIGA CREA LA LINEA

        # 4. Satelliti Geni Vicini (AXON) -> COLLEGATI
        # Prendiamo i 5 vicini nel database per contesto
        idx = df[df['target_id'] == search_query].index[0]
        neighbors = df.iloc[max(0, idx-3):min(len(df), idx+4)]
        for _, r in neighbors.iterrows():
            if r['target_id'] != search_query:
                G.add_node(r['target_id'], size=30, color='lightgray', label=r['target_id'], type='gene')
                G.add_edge(search_query, r['target_id']) # <--- LINEA

    # --- SCENARIO B: NESSUNA RICERCA (DEFAULT) ---
    else:
        # Mostra i Top 10 Hub per non lasciare lo schermo nero
        top_hubs = df.sort_values('initial_score', ascending=False).head(10)
        center = top_hubs.iloc[0]['target_id']
        G.add_node(center, size=40, color='gray', label=center)
        
        for _, r in top_hubs.iloc[1:].iterrows():
            t_id = r['target_id']
            G.add_node(t_id, size=30, color='gray', label=t_id)
            G.add_edge(center, t_id) # Collega tutto al primo per fare "massa"

    # --- RENDERING GRAFICO ---
    # Spring layout con k=1.5 forza i nodi a distanziarsi (esplosione)
    pos = nx.spring_layout(G, k=1.5, seed=42)
    
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node in G.nodes():
        node_x.append(pos[node][0])
        node_y.append(pos[node][1])
        node_text.append(G.nodes[node].get('label', node))
        node_color.append(G.nodes[node].get('color', 'gray'))
        node_size.append(G.nodes[node].get('size', 20))

    fig_net = go.Figure()
    
    # Traccia Linee (Grigie)
    fig_net.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode='lines', 
        line=dict(width=1, color='#888'), hoverinfo='none'
    ))
    
    # Traccia Nodi (Colorati)
    fig_net.add_trace(go.Scatter(
        x=node_x, y=node_y, mode='markers+text', 
        text=node_text, textposition="top center",
        marker=dict(size=node_size, color=node_color, line=dict(width=2, color='white'))
    ))

    fig_net.update_layout(
        showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    
    st.plotly_chart(fig_net, use_container_width=True)

# --- 6. TABELLE DATI ---
st.divider()
c_odi, c_gci = st.columns(2)
with c_odi:
    st.header("💊 Therapeutics")
    if not odi_df.empty:
        st.dataframe(odi_df[['Generic_Name', 'Drug_Class', 'Targets']], use_container_width=True)
with c_gci:
    st.header("🧪 Clinical Trials")
    if not gci_df.empty:
        st.dataframe(gci_df[['Canonical_Title', 'Phase']], use_container_width=True)

st.caption("MAESTRO Suite v16.5 | Stable Build | RUO")
