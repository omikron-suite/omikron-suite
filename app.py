import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Omikron Suite Debug", layout="wide")

# Connessione
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

st.title("🛡️ Omikron Suite - Monitor di Connessione")

# Sidebar
search_query = st.sidebar.text_input("🔍 Cerca (prova: HER2)", "").strip()

# --- TEST DI CONNESSIONE DIRETTO ---
st.subheader("📡 Stato Connessione Database")
try:
    check_db = supabase.table("GCI_clinical_trials").select("count", count="exact").execute()
    st.success(f"Connessione OK! La tabella 'GCI_clinical_trials' contiene {check_db.count} righe.")
except Exception as e:
    st.error(f"ERRORE DI CONNESSIONE: {e}")

# --- RICERCA CLINICA ---
st.divider()
if search_query:
    st.info(f"Ricerca in corso per: {search_query}")
    try:
        # Query
        res = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        data = pd.DataFrame(res.data)
        
        if not data.empty:
            st.success(f"Trovati {len(data)} trial clinici!")
            st.dataframe(data, use_container_width=True)
        else:
            st.warning(f"La query non ha prodotto risultati per '{search_query}'.")
            st.write("Dati presenti nella colonna Biomarker:")
            all_data = supabase.table("GCI_clinical_trials").select("Primary_Biomarker").execute()
            st.write(pd.DataFrame(all_data.data)["Primary_Biomarker"].unique())
    except Exception as e:
        st.error(f"Errore durante la ricerca: {e}")
else:
    st.write("Inserisci una parola chiave nella sidebar per iniziare.")
