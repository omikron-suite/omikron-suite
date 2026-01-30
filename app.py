import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- 0. GESTIONE STATE (Click Interattivo) ---
if 'selected_hub' not in st.session_state:
    st.session_state.selected_hub = ""

def update_from_search():
    st.session_state.selected_hub = st.session_state.search_widget.upper()

# --- CONNESSIONE ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("target_id,initial_score,toxicity_index").execute()
        data = res.data or []
        d = pd.DataFrame(data)
        if d.empty: return d
        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0).clip(0.0, 1.0)
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

df = load_axon()

# --- SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Hub Focus")

# Input di ricerca sincronizzato con il click del grafico
search_query = st.sidebar.text_input(
    "Cerca Target o Clicca sul Grafico", 
    value=st.session_state.selected_hub, 
    key="search_widget",
    on_change=update_from_search,
    placeholder="es. KRAS"
).strip().upper()

# --- LOGICA CARTELLA FARMACI (SIDEBAR) ---
odi_df = pd.DataFrame()
pmi_df = pd.DataFrame()
gci_df = pd.DataFrame()

if search_query and not df.empty:
    try:
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
        
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])

        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])
    except: pass

if not odi_df.empty:
    st.sidebar.success(f"📂 **Cartella Farmaci: {len(odi_df)}**")
    with st.sidebar.expander("Apri Cartella ODI"):
        for drug in odi_df['Generic_Name'].unique():
            st.write(f"💊 {drug}")

st.sidebar.warning("⚠️ **Research Use Only**")

# --- FILTRO DATI ---
def safe_df_cols(dfx: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in dfx.columns]

if "error" in df.columns:
    st.error(f"Errore caricamento: {df['error'].iloc[0]}")
    df = pd.DataFrame()

# Logica: Se c'è una query, filtro su quella. Se non c'è, mostro i top hub.
if search_query and not df.empty:
    filtered_df = df[df["target_id"].str.contains(search_query, na=False)]
else:
    filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)].sort_values("initial_score", ascending=False).head(15)

# --- UI ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Linked")
        c3.metric("ODI", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- RAGNATELA INTERATTIVA (CLICK-TO-OPEN) ---
st.subheader("🕸️ Network Interaction Map")


if not filtered_df.empty:
    G = nx.Graph()
    
    # 1. Aggiunta Nodi Target (Nucleo)
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]
        is_hub = (tid == search_query)
        # Se è l'hub cercato è Oro, altrimenti Grigio/Verde
        color_node = 'gold' if is_hub else float(r["toxicity_index"])
        size_node = 60 if is_hub else 30
        
        G.add_node(tid, size=size_node, color=color_node, type="target", label=tid)

    # 2. LOGICA LINK: Disegno linee SOLO se c'è un Hub selezionato (search_query attiva)
    if search_query and search_query in G.nodes:
        
        # A. Satelliti Farmaci (Solo se Hub attivo)
        for _, drug in odi_df.head(5).iterrows():
            d_name = f"💊 {drug['Generic_Name']}"
            G.add_node(d_name, size=25, color='skyblue', type="drug", label=d_name)
            G.add_edge(search_query, d_name) # Link Hub-Farmaco
            
        # B. Satelliti Pathway (Solo se Hub attivo)
        for _, path in pmi_df.head(3).iterrows():
            p_name = f"🧬 {path['Canonical_Name']}"
            G.add_node(p_name, size=25, color='violet', type="pathway", label=p_name)
            G.add_edge(search_query, p_name) # Link Hub-Pathway

        # C. Link tra Hub e altri Target vicini
        nodes = list(G.nodes())
        for n in nodes:
            if n != search_query and G.nodes[n].get("type") == "target":
                G.add_edge(search_query, n) # Link Hub-TargetVicino

    # Calcolo Layout
    # Se non c'è hub, layout più sparso. Se c'è hub, layout centrato.
    k_val = 1.2 if search_query else 2.0 
    pos = nx.spring_layout(G, k=k_val, seed=42)
    
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]; x1, y1 = pos[b]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    
    # TRACCIA LINEE (Solo se ci sono edges)
    if edge_x:
        fig_net.add_trace(go.Scatter(
            x=edge_x, y=edge_y, 
            mode="lines", 
            line=dict(width=1.5, color='#888'), 
            hoverinfo="none"
        ))
    
    # TRACCIA NODI
    # Gestiamo i colori: se è numerico usa scala, se stringa (es. gold/skyblue) usa mappa
    node_colors = []
    for n in G.nodes():
        c = G.nodes[n].get("color", 0.5)
        node_colors.append(c)

    # Nota: Per semplicità visiva qui uso una logica ibrida per i colori
    # Se è un target non selezionato, usa la scala cromatica della tossicità
    
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], 
        y=[pos[n][1] for n in G.nodes()],
        mode="markers+text", 
        text=[G.nodes[n].get('label', n) for n in G.nodes()], 
        textposition="top center",
        marker=dict(
            size=[G.nodes[n].get("size", 30) for n in G.nodes()],
            # Qui semplifico: se è float usa scala, se no grigio default (sovrascritto da logica complessa se necessario)
            color=[c if isinstance(c, float) else 0.1 for c in node_colors], 
            colorscale="RdYlGn_r", 
            showscale=False, 
            line=dict(width=2, color='white')
        )
    ))

    # Configurazione Interattività
    fig_net.update_layout(
        showlegend=False, 
        margin=dict(b=0,l=0,r=0,t=0), 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), 
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        clickmode='event+select' # Abilita il click
    )
    
    # --- IL CUORE DELL'INTERATTIVITÀ ---
    # on_select="rerun" ricarica l'app quando clicchi un punto
    selection = st.plotly_chart(fig_net, use_container_width=True, on_select="rerun", selection_mode="points")
    
    # Gestione del Click
    if selection and selection["selection"]["points"]:
        clicked_node_text = selection["selection"]["points"][0]["text"]
        # Pulizia del testo (rimuovi emoji se presenti per ottenere l'ID pulito)
        clean_id = clicked_node_text.replace("🎯 ", "").replace("💊 ", "").replace("🧬 ", "").split(" ")[0]
        
        # Se clicco su un nodo diverso da quello attuale, aggiorno
        if clean_id != st.session_state.selected_hub:
            st.session_state.selected_hub = clean_id
            st.rerun() # Forza il ricaricamento immediato per mostrare le linee

# --- PORTALI DATI ---
st.divider()
p_odi, p_gci = st.columns(2)
with p_odi:
    st.header("💊 Therapeutics (ODI)")
    cols = safe_df_cols(odi_df, ["Generic_Name", "Drug_Class"])
    if not odi_df.empty and cols:
        st.dataframe(odi_df[cols], use_container_width=True)
with p_gci:
    st.header("🧪 Clinical Trials (GCI)")
    cols = safe_df_cols(gci_df, ["Canonical_Title", "Phase"])
    if not gci_df.empty and cols:
        st.dataframe(gci_df[cols], use_container_width=True)

st.caption("MAESTRO Suite | Integrated v16.0 (Interactive) | RUO")
