import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse
import calendar

# Configurare Pagina
st.set_page_config(page_title="Gestiune Pensiune", layout="centered")

# --- DATABASE SETUP ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATE, checkout DATE, status TEXT, pret_total REAL)''')
conn.commit()

# --- DATE PENSIUNE ---
CAMERE_INFO = {
    "Camera 1": 200, "Camera 2": 200, "Camera 3": 250, 
    "Camera 4": 250, "Camera 5": 300, "Camera 6": 350
}
STATUSURI = ["În așteptare", "Confirmat", "Anulat"]

# --- FUNCTII ---
def trimite_whatsapp(nume, telefon, camera, checkin, checkout):
    mesaj = f"Salut {nume}! Confirmăm rezervarea pentru {camera} (Perioada: {checkin} - {checkout}). Te așteptăm cu drag!"
    msg_encoded = urllib.parse.quote(mesaj)
    return f"https://api.whatsapp.com/send?phone={telefon}&text={msg_encoded}"

# --- INTERFATA ---
st.sidebar.title("Meniu Pensiune")
choice = st.sidebar.radio("Navigare", ["Rezervare Nouă", "Calendar & Listă", "Rapoarte & Statistici"])

if choice == "Rezervare Nouă":
    st.header("➕ Adaugă Rezervare")
    with st.form("form_rez"):
        nume = st.text_input("Nume Client")
        telefon = st.text_input("Telefon (ex: 407xxxxxxxx)")
        camera = st.selectbox("Alege Camera", list(CAMERE_INFO.keys()))
        col1, col2 = st.columns(2)
        checkin = col1.date_input("Check-in")
        checkout = col2.date_input("Check-out")
        status = st.selectbox("Status", STATUSURI)
        submit = st.form_submit_button("Salvează Rezervarea")
        
        if submit:
            nopti = (checkout - checkin).days
            if nopti <= 0:
                st.error("Data de check-out invalidă!")
            else:
                pret_total = nopti * CAMERE_INFO[camera]
                c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total) VALUES (?,?,?,?,?,?,?)",
                          (nume, telefon, camera, str(checkin), str(checkout), status, pret_total))
                conn.commit()
                st.success(f"Rezervare salvată! Total: {pret_total} RON")
                url_wa = trimite_whatsapp(nume, telefon, camera, checkin, checkout)
                st.markdown(f'[📱 Trimite Confirmare WhatsApp]({url_wa})')

elif choice == "Calendar & Listă":
    st.header("📋 Rezervări")
    df = pd.read_sql_query("SELECT * FROM rezervari", conn)
    if not df.empty:
        st.dataframe(df)
        if st.button("Șterge toate datele (Reset)"):
            c.execute("DELETE FROM rezervari")
            conn.commit()
            st.rerun()
    else:
        st.info("Nu sunt rezervări.")

elif choice == "Rapoarte & Statistici":
    st.header("📊 Analiză")
    df = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    if not df.empty:
        df['checkin'] = pd.to_datetime(df['checkin'])
        df['checkout'] = pd.to_datetime(df['checkout'])
        df['nopti'] = (df['checkout'] - df['checkin']).dt.days
        df['luna'] = df['checkin'].dt.month
        df['an'] = df['checkin'].dt.year
        
        an_selectat = st.selectbox("An", sorted(df['an'].unique(), reverse=True))
        df_an = df[df['an'] == an_selectat]
        
        incasari = df_an['pret_total'].sum()
        grad = (df_an['nopti'].sum() / (6 * 365)) * 100
        
        st.metric("Incasări An", f"{incasari} RON")
        st.metric("Grad Ocupare An", f"{grad:.1f}%")
        
        raport_lunar = df_an.groupby('luna').agg({'pret_total': 'sum', 'nopti': 'sum'}).reset_index()
        st.bar_chart(data=raport_lunar, x='luna', y='pret_total')
    else:
        st.info("Lipsă date pentru rapoarte.")
