import streamlit as st
import pandas as pd
from supabase import create_client

# --- 1. CONFIGURAZIONE ---
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

# --- 3. CONNESSIONE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

# --- 4. LOGICA DASHBOARD ---
st.title("🛡️ Omikron Orchestra Suite")
search_query = st.sidebar.text_input("🔍 Cerca Biomarker (es. HER2)", "").strip()

# --- 5. SEZIONE CLINICA (GCI) ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")

if search_query:
    try:
        # Recuperiamo i dati
        res = supabase.table("clinical_trials").select("*").execute()
        gci_df = pd.DataFrame(res.data)

        if not gci_df.empty:
            # AUTO-ISPEZIONE DELLE COLONNE
            # Cerchiamo la colonna giusta anche se Supabase ha cambiato i nomi in minuscolo
            col_biomarker = next((c for c in gci_df.columns if c.lower() == 'primary_biomarker'), None)
            
            if col_biomarker:
                # Filtriamo i dati in locale per massima precisione
                trials = gci_df[gci_df[col_biomarker].str.contains(search_query, case=False, na=False)]
                
                if not trials.empty:
                    st.success(f"Trovate {len(trials)} evidenze per '{search_query}'")
                    
                    # Visualizzazione Tabella con le colonne disponibili
                    cols_interessanti = ['Canonical_Title', 'Phase', 'Year', 'Cancer_Type', 'Key_Results_PFS', 'Main_Toxicities']
                    cols_presenti = [c for c in trials.columns if c in cols_interessanti or c.lower() in [x.lower() for x in cols_interessanti]]
                    
                    st.dataframe(trials[cols_presenti], use_container_width=True)
                else:
                    st.warning(f"Nessun match per '{search_query}' nella colonna {col_biomarker}.")
                    with st.expander("Controlla i nomi presenti nel Database"):
                        st.write(gci_df[col_biomarker].unique()[:20]) # Mostra i primi 20 per debug
            else:
                st.error(f"Errore: Non trovo la colonna 'Primary_Biomarker'. Colonne trovate: {list(gci_df.columns)}")
        else:
            st.error("La tabella 'clinical_trials' è vuota su Supabase.")
            
    except Exception as e:
        st.error(f"Errore di connessione: {e}")
else:
    st.info("Digita un biomarker nella sidebar per vedere i trial clinici.")
