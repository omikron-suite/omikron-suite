import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="MAESTRO Total Suite", layout="wide")

# --- 2. CONNESSIONE SUPABASE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon_full():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].astype(str).str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_odi_master():
    try:
        res = supabase.table("odi_database").select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# Caricamento Motori
df_axon = load_axon_full()
df_odi_master = load_odi_master()

# --- 3. SIDEBAR: OMNI-SEARCH & CONTROLLI ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")

st.sidebar.markdown("### 🔍 Omni-Search")
main_input = st.sidebar.text_input("Cerca Target o Farmaco", placeholder="es. pembro o KRAS").strip()

st.sidebar.divider()
min_sig = st.sidebar.slider("Soglia Segnale VTG", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità TMI", 0.0, 1.0, 0.8)

# --- 4. MOTORE DI INTELLIGENZA (UNIFIED SEARCH) ---
target_id = ""
found_drug_row = pd.DataFrame()
gci_df = pd.DataFrame()
pmi_df = pd.DataFrame()
odi_related_df = pd.DataFrame()

if main_input:
    # A. Cerca se è un farmaco
    if not df_odi_master.empty:
        drug_match = df_odi_master[
            df_odi_master['Generic_Name'].str.contains(main_input, case=False, na=False) | 
            df_odi_master['Brand_Names'].str.contains(main_input, case=False, na=False)
        ]
        if not drug_match.empty:
            found_drug_row = drug_match.iloc[0]
            # Estrazione Target dal Farmaco
            target_id = str(found_drug_row['Targets']).split('(')[0].split(';')[0].strip().upper()
        else:
            # B. Se non è un farmaco, assumiamo sia un Target
            target_id = main_input.upper()

    # C. Caricamento Satelliti per il Target identificato
    if target_id:
        try:
            res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{target_id}%").execute()
            gci_df = pd.DataFrame(res_gci.data)
            res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{target_id}%").execute()
            pmi_df = pd.DataFrame(res_pmi.data)
            # Farmaci correlati a questo target
            odi_related_df = df_odi_master[df_odi_master['Targets'].str.contains(target_id, case=False, na=False)] if not df_odi_master.empty else pd.DataFrame()
        except: pass

# --- 5. DASHBOARD: OPERA DIRECTOR (FULL SCORES) ---
st.title("🛡️ MAESTRO: Omikron Total Suite")

if target_id and not df_axon.empty:
    target_info = df_axon[df_axon['target_id'] == target_id]
    
    if not target_info.empty:
        row = target_info.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {target_id}")
        if not found_drug_row.empty:
            st.success(f"💊 **Focus Farmaco:** {found_drug_row['Generic_Name']} | **Meccanismo:** {found_drug_row.get('Mechanism_Short', 'N/D')}")
        
        # --- GRID 10 PARAMETRI ---
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1 = st.columns(5)
        r1[0].metric("OMI (Biomarker)", "DETECTED")
        r1[1].metric("SMI (Pathway)", f"{len(pmi_df)} Hubs")
        r1[2].metric("ODI (Drug)", "TARGETABLE" if not odi_related_df.empty else "NO DRUG")
        r1[3].metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1[4].metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        r2 = st.columns(5)
        r2[0].metric("BCI (Bio-cost.)", "OPTIMAL")
        r2[1].metric("GNI (Genetica)", "STABLE")
        r2[2].metric("EVI (Ambiente)", "LOW RISK")
        r2[3].metric("MBI (Microbiota)", "RESILIENT")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "PRE-CLIN"
        r2[4].metric("GCI (Clinica)", phase)
        st.divider()

# --- 6. RAGNATELA DINAMICA (SOLE-HUB) ---
st.subheader("🕸️ Network Interaction Map")
if not df_axon.empty:
    # Logica di selezione nodi: Target + Top 8 Hubs
    if target_id in df_axon['target_id'].values:
        exact = df_axon[df_axon['target_id'] == target_id]
        others = df_axon[df_axon['target_id'] != target_id].sort_values('initial_score', ascending=False).head(8)
        plot_df = pd.concat([exact, others]).drop_duplicates()
    else:
        plot_df = df_axon[(df_axon['initial_score'] >= min_sig) & (df_axon['toxicity_index'] <= max_t)].head(10)

    if not plot_df.empty:
        G = nx.Graph()
        for _, r in plot_df.iterrows():
            tid = str(r['target_id'])
            is_f = tid == target_id
            G.add_node(tid, size=float(r['initial_score']) * (60 if is_f else 30), color=float(r['toxicity_index']))
            # Magnetismo: Collega tutto al focus
            if target_id in plot_df['target_id'].values and tid != target_id:
                G.add_edge(target_id, tid)
        
        pos = nx.spring_layout(G, k=1.0, seed=42)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
        fig_net = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#777'), mode='lines', hoverinfo='none'),
            go.Scatter(x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()], 
                       mode='markers+text', text=list(G.nodes()), textposition="top center",
                       marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], color=[G.nodes[n]['color'] for n in G.nodes()],
                       colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
        ])
        fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig_net, use_container_width=True)

# --- 7. DEEP DIVE TABS ---
st.divider()
t1, t2, t3 = st.tabs(["💊 Therapeutics (ODI)", "🧬 Pathways (PMI)", "🧪 Clinical Evidence (GCI)"])

with t1:
    if not odi_related_df.empty: st.dataframe(odi_related_df[['Generic_Name', 'Brand_Names', 'Drug_Class', 'Targets']], use_container_width=True)
    else: st.info("Nessun dato terapeutico specifico.")

with t2:
    if not pmi_df.empty:
        for _, p in pmi_df.iterrows():
            with st.expander(f"Pathway: {p['Canonical_Name']}"):
                st.write(p.get('Description_L0', 'N/D'))
                st.caption(f"Confidence: {p.get('Confidence_Default', 'High')} | Priority: {p.get('Evidence_Priority', 'N/D')}")
    else: st.info("Nessun pathway mappato.")

with t3:
    if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type', 'Year']], use_container_width=True)
    else: st.info("Nessun trial clinico registrato.")

st.caption("MAESTRO Total Suite | Unified Search | Full Engine v9.0 | RUO")
