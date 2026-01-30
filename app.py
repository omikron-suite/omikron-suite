import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- CONNESSIONE (consigliato via secrets) ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("target_id,initial_score,toxicity_index").execute()
        data = res.data or []
        d = pd.DataFrame(data)
        if d.empty:
            return d

        # Normalizzazione
        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()

        # Cast numerico robusto
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

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8, help="VTG (Vitality Gene Score): intensità del segnale biologico rilevato per il target.")
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8, help="TMI (Toxicity Management Index): soglia massima di rischio tossicologico ammessa.")

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Smart Search & Hub Focus")
search_query = st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS")
search_query = (search_query or "").strip().upper()

# --- DISCLAIMER SIDEBAR ---
st.sidebar.markdown("""
<div style="background-color: #1a1a1a; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-top: 20px;">
    <p style="font-size: 0.75rem; color: #ff4b4b; font-weight: bold; margin-bottom: 5px;">⚠️ RUO - RESEARCH USE ONLY</p>
    <p style="font-size: 0.7rem; color: #888; text-align: justify; line-height: 1.2;">
        Le analisi generate sono destinate esclusivamente ad attività di ricerca scientifica. Non costituiscono diagnosi medica o prescrizione terapeutica.
    </p>
</div>
""", unsafe_allow_html=True)

# --- DATA PORTALS ---
gci_df = pd.DataFrame()
pmi_df = pd.DataFrame()
odi_df = pd.DataFrame()

def safe_df_cols(dfx: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in dfx.columns]

filtered_df = pd.DataFrame()

if "error" in df.columns:
    st.error(f"Errore caricamento axon_knowledge: {df['error'].iloc[0]}")
    df = pd.DataFrame()

if search_query and not df.empty:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])

        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])

        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
    except Exception as e:
        st.sidebar.error(f"Errore query Supabase: {e}")

    filtered_df = df[df["target_id"].str.contains(search_query, na=False)]
else:
    filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)] if not df.empty else df

# --- UI ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI (Biomarker)", "DETECTED", help="OMI: Rilevamento della presenza del Target nel database AXON.")
        c2.metric("SMI (Pathway)", f"{len(pmi_df)} Linked", help="SMI: Numero di pathway biologici mappati nel sistema PMI.")
        c3.metric("ODI (Drug)", "TARGETABLE" if not odi_df.empty else "NO DRUG", help="ODI: Disponibilità di molecole o farmaci approvati/sperimentali nel database ODI.")
        c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse", help="TMI: Indice di tossicità specifica (0.0 = sicuro, 1.0 = critico).")
        c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}", help="CES (Combined Efficiency Score): bilancio tra potenzialità terapeutica e sicurezza.")

        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        r2c1.metric("BCI", "OPTIMAL", help="BCI (Biological Cost Index): impatto metabolico del target sulla rete cellulare.")
        r2c2.metric("GNI", "STABLE", help="GNI (Genomic Network Index): stabilità del nodo all'interno della rete genomica.")
        r2c3.metric("EVI", "LOW RISK", help="EVI: vulnerabilità del target a mutazioni ambientali.")
        r2c4.metric("MBI", "RESILIENT", help="MBI: Indice di interazione microbiotica.")
        phase = gci_df["Phase"].iloc[0] if ("Phase" in gci_df.columns and not gci_df.empty) else "N/D"
        r2c5.metric("GCI (Clinica)", phase, help="GCI: Stato di avanzamento della sperimentazione clinica del Target.")
        st.divider()

st.subheader("🕸️ Network Interaction Map", help="Rappresentazione grafica delle interazioni tra hub. Il nodo centrale rappresenta il target cercato, collegato ai nodi satelliti filtrati.")

if not filtered_df.empty:
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]
        is_f = (tid == search_query)
        G.add_node(
            tid,
            size=float(r["initial_score"]) * (50 if is_f else 30),
            color=float(r["toxicity_index"]),
        )

    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query:
                G.add_edge(search_query, n)
    elif len(nodes) > 1:
        for i in range(len(nodes) - 1):
            G.add_edge(nodes[i], nodes[i + 1])

    pos = nx.spring_layout(G, k=1.2, seed=42)

    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", hoverinfo="none", line=dict(color="#444", width=1)))

    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes],
        y=[pos[n][1] for n in nodes],
        mode="markers+text",
        text=nodes,
        textposition="top center",
        marker=dict(
            size=[G.nodes[n]["size"] for n in nodes],
            color=[G.nodes[n]["color"] for n in nodes],
            colorscale="RdYlGn_r",
            showscale=True,
            line=dict(width=2),
        )
    ))

    fig_net.update_layout(
        showlegend=False,
        margin=dict(b=0, l=0, r=0, t=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    st.plotly_chart(fig_net, use_container_width=True)
else:
    st.info("Nessun risultato con i filtri attuali.")

st.divider()
p_odi, p_gci = st.columns(2)
with p_odi:
    st.header("💊 Therapeutics (ODI)", help="Database dei farmaci approvati o sperimentali associati al Target selezionato.")
    cols = safe_df_cols(odi_df, ["Generic_Name", "Drug_Class"])
    if not odi_df.empty and cols:
        st.dataframe(odi_df[cols], use_container_width=True)
    elif search_query:
        st.caption("Nessun farmaco associato trovato.")

with p_gci:
    st.header("🧪 Clinical Trials (GCI)", help="Dati estratti dai trial clinici internazionali relativi al biomarcatore analizzato.")
    cols = safe_df_cols(gci_df, ["Canonical_Title", "Phase"])
    if not gci_df.empty and cols:
        st.dataframe(gci_df[cols], use_container_width=True)
    elif search_query:
        st.caption("Nessun trial clinico associato trovato.")

# --- FOOTER & DISCLAIMER CENTRALE ---
st.divider()
st.markdown("""
<div style="background-color: #0e1117; padding: 30px; border-radius: 12px; border: 1px solid #333; text-align: center; max-width: 900px; margin: 0 auto;">
    <h4 style="color: #ff4b4b; margin-top: 0;">⚠️ DISCLAIMER LEGALE E SCIENTIFICO</h4>
    <p style="font-size: 0.85rem; color: #aaa; text-align: justify; line-height: 1.6;">
        <b>MAESTRO Omikron Suite</b> è una piattaforma di analisi computazionale destinata esclusivamente ad uso di <b>Ricerca Scientifica (Research Use Only - RUO)</b>. 
        Le informazioni fornite, inclusi i punteggi OMI, TMI e CES, sono derivate da modelli algoritmici basati su database proprietari (AXON, ODI, GCI) e 
        non costituiscono parere medico, diagnosi o indicazione di trattamento clinico. L'accuratezza dei collegamenti nella rete interattiva è soggetta 
        alle limitazioni dei dati disponibili e deve essere validata tramite sperimentazione in vitro/in vivo. Omikron Project non si assume alcuna 
        responsabilità per decisioni terapeutiche o di sviluppo farmacologico basate sui dati qui riportati.
    </p>
    <p style="font-size: 0.8rem; color: #555; margin-top: 20px;">
        MAESTRO Omikron Suite v20.4 | © 2026 Omikron Orchestra Project | Powered by AXON Intelligence
    </p>
</div>
<br>
""", unsafe_allow_html=True)
