import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="MAESTRO Omikron Suite v2.6.4 Platinum", layout="wide")

# Typography Tuning
st.markdown("""
<style>
div[data-testid="stAppViewContainer"] h1 { font-size: 1.75rem !important; margin-bottom: 0.35rem !important; }
div[data-testid="stAppViewContainer"] h2 { font-size: 1.35rem !important; margin-top: 0.6rem !important; }
div[data-testid="stAppViewContainer"] h3 { font-size: 1.10rem !important; margin-top: 0.55rem !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONNECTION ---
URL = st.secrets.get("SUPABASE_URL", "")
KEY = st.secrets.get("SUPABASE_KEY", "")

if not URL or not KEY:
    st.error("Missing Supabase Secrets! Please check your configuration.")
    st.stop()

supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        # Carichiamo la tabella axon_knowledge
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data or [])
        
        if d.empty:
            return d

        # --- LOGICA DI PULIZIA AUTOMATICA (PURGE) ---
        # Rimuoviamo OMI- se è rimasto qualcosa nel DB per errore
        d["target_id"] = d["target_id"].astype(str).str.replace("OMI-", "").str.strip().str.upper()
        d["source_id"] = d["source_id"].astype(str).str.replace("OMI-", "").str.strip().str.upper()

        # Normalizzazione punteggi
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0)
        
        # Ricalcolo CES se mancante o per sicurezza
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])

        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

def get_first_neighbors(df_all, hub, k, min_sig, max_t):
    if df_all.empty or not hub: return pd.DataFrame()
    cand = df_all[
        (df_all["target_id"] != hub) & 
        (df_all["initial_score"] >= min_sig) & 
        (df_all["toxicity_index"] <= max_t)
    ].copy()
    return cand.sort_values(["ces_score", "initial_score"], ascending=False).head(int(k))

# --- 3. DATA LOADING ---
df = load_axon()

# --- 4. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("v2.6.4 Platinum | 2026")

min_sig = st.sidebar.slider("Minimum VTG Threshold", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("TMI Toxicity Limit", 0.0, 1.0, 0.8)

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Search Hub Target", placeholder="e.g. KRAS").strip().upper()
top_k = st.sidebar.slider("Neighbors (K)", 3, 30, 10)

# --- 5. UI: MAIN INTERFACE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if df.empty:
    st.error("🚨 AXON database empty or unavailable. Please check your Supabase Table 'axon_knowledge'.")
elif "error" in df.columns:
    st.error(f"Error loading AXON: {df['error'].iloc[0]}")
else:
    if search_query:
        target_data = df[df["target_id"] == search_query]

        if target_data.empty:
            st.info(f"No hub found for: **{search_query}**")
        else:
            row = target_data.iloc[0]
            st.markdown(f"## 🎼 Opera Director: {search_query}")

            # Fetch Correlated Data from other tables
            try:
                gci_df = pd.DataFrame(supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute().data or [])
                pmi_df = pd.DataFrame(supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute().data or [])
                odi_df = pd.DataFrame(supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute().data or [])
            except:
                gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

            # Metric Grid
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("OMI", "DETECTED")
            c2.metric("SMI (PMI)", f"{len(pmi_df)} Linked")
            c3.metric("ODI Items", f"{len(odi_df)} Items")
            c4.metric("TMI", f"{row['toxicity_index']:.2f}")
            c5.metric("CES", f"{row['ces_score']:.2f}")

            st.warning(f"**🧬 Biological Context:** {row.get('description_l0', 'Analysis in progress...')}")
            if row.get('pdb_id'):
                st.info(f"**💎 Protein Structure (PDB):** {row['pdb_id']}")

            # --- EXPORT SECTION ---
            st.markdown("### 📥 Advanced Intelligence Export")
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)

            def create_full_report():
                output = io.StringIO()
                output.write(f"MAESTRO INTELLIGENCE REPORT - HUB: {search_query}\nGenerated: {timestamp}\n\n")
                
                output.write("--- 1. CORE ANALYTICS (AXON) ---\n")
                pd.DataFrame([row]).to_csv(output, index=False)
                
                output.write("\n--- 2. MOLECULAR NEIGHBORS ---\n")
                neighbors_df.to_csv(output, index=False)
                
                output.write("\n--- 3. THERAPEUTICS (ODI) ---\n")
                odi_df.to_csv(output, index=False)
                
                output.write("\n--- 4. CLINICAL TRIALS (GCI) ---\n")
                gci_df.to_csv(output, index=False)
                
                return output.getvalue()

            st.download_button(
                label="📊 Download Full Intelligence Dossier (CSV)",
                data=create_full_report(),
                file_name=f"MAESTRO_{search_query}_Dossier.csv",
                mime="text/csv"
            )

# --- 6. NETWORK MAP (SUBSTITUTE WITH YOUR VIZ CODE) ---
st.divider()
st.subheader("🕸️ Network Map & Rankings")
# [Qui inserisci il tuo codice Plotly/NetworkX già esistente per la ragnatela]
