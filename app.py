import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import urllib.parse
import calendar
from fpdf import FPDF

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Pensiune Manager Pro", layout="wide")

# --- STYLING CSS ---
st.markdown("""
    <style>
    .calendar-box { height: 40px; width: 100%; border-radius: 4px; border: 1px solid #ddd; display: flex; align-items: center; justify-content: center; font-size: 10px; color: white; }
    .bg-liber { background: #2ECC71; }
    .bg-ocupat { background: #E74C3C; }
    .bg-checkout { background: linear-gradient(90deg, #E74C3C 50%, #2ECC71 50%); }
    .bg-checkin { background: linear-gradient(90deg, #2ECC71 50%, #E74C3C 50%); }
    .bg-schimb { background: linear-gradient(90deg, #E74C3C 48%, #ffffff 50%, #E74C3C 52%); }
    .cam-name { font-weight: bold; padding-top: 10px; font-size: 14px; }
    .info-card { background: #ebf5fb; padding: 15px; border-radius: 10px; border: 1px solid #3498db; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE SETUP ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)''')
conn.commit()

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- FUNCTII ---
def genereaza_pdf(r):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "DETALII REZERVARE", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Perioada: {str(r['checkin'])[:16]} - {str(r['checkout'])[:16]}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    pdf.cell(0, 10, f"Pret: {r['pret_total']} RON", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- MENIU ---
menu = ["📅 Harta Disponibilității", "📊 Statistici", "➕ Rezervare Nouă", "👥 Rezervare Grup", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Navigare", menu)

if choice == "📅 Harta Disponibilității":
    st.title("Harta Disponibilității")
    d_start = st.date_input("Vezi de la data:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    
    cols = st.columns([1.5] + [1]*14)
    cols[0].write("**Cameră**")
    for i, d in enumerate(zile): cols[i+1].write(f"**{d.strftime('%d/%m')}**")

    df_rez = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df_rez['checkin_d'] = pd.to_datetime(df_rez['checkin']).dt.date
    df_rez['checkout_d'] = pd.to_datetime(df_rez['checkout']).dt.date

    for cam in CAMERE_INFO.keys():
        row = st.columns([1.5] + [1]*14)
        row[0].markdown(f"<div class='cam-name'>{cam}</div>", unsafe_allow_html=True)
        for i, d in enumerate(zile):
            rez_zi = df_rez[(df_rez['camera'] == cam) & ((df_rez['checkin_d'] <= d) & (df_rez['checkout_d'] >= d))]
            
            plecare = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkout_d'] == d)].empty
            sosire = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] == d)].empty
            ocupat = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] < d) & (df_rez['checkout_d'] > d)].empty
            
            clasa = "bg-liber"
            label = ""
            if plecare and sosire: clasa = "bg-schimb"
            elif plecare: clasa = "bg-checkout"
            elif sosire: clasa = "bg-checkin"
            elif ocupat: clasa = "bg-ocupat"
            
            # Punem ID-ul rezervarii in celula daca e ocupat
            if not rez_zi.empty and (ocupat or sosire or plecare):
                label = str(rez_zi.iloc[0]['id'])

            row[i+1].markdown(f'<div class="calendar-box {clasa}">{label}</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # --- SECTIUNEA DE DETALII INTERACTIVA ---
    st.subheader("🔍 Detalii Rezervare")
    id_cautat = st.selectbox("Selectează ID-ul de pe hartă pentru detalii:", ["-"] + sorted(df_rez['id'].unique().tolist()), index=0)
    
    if id_cautat != "-":
        r_detalii = df_rez[df_rez['id'] == int(id_cautat)].iloc[0]
        with st.container():
            st.markdown(f"""
                <div class="info-card">
                    <h4>👤 Client: {r_detalii['nume']}</h4>
                    <p>📱 <b>Telefon:</b> {r_detalii['telefon']}</p>
                    <p>📅 <b>Perioada:</b> {str(r_detalii['checkin'])[:16]} — {str(r_detalii['checkout'])[:16]}</p>
                    <p>🛏️ <b>Camera:</b> {r_detalii['camera']} | 💰 <b>Preț:</b> {r_detalii['pret_total']} RON</p>
                    <p>📝 <b>Note:</b> {r_detalii['note'] if r_detalii['note'] else 'Fără note'}</p>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            # PDF
            pdf_bytes = genereaza_pdf(r_detalii)
            c1.download_button("📄 Descarcă PDF", pdf_bytes, f"Rezervare_{id_cautat}.pdf", key=f"pdf_h_{id_cautat}")
            
            # WhatsApp
            msg = f"Salut {r_detalii['nume']}! Confirmam rezervarea ({str(r_detalii['checkin'])[:10]})."
            url_wa = f"https://api.whatsapp.com/send?phone={r_detalii['telefon']}&text={urllib.parse.quote(msg)}"
            c2.markdown(f'<a href="{url_wa}" target="_blank"><button style="width:100%; height:38px; background-color:#25D366; color:white; border:none; border-radius:5px;">📱 WhatsApp</button></a>', unsafe_allow_html=True)
            
            # Stergere
            if c3.button("🗑️ Șterge Rezervarea", key=f"del_h_{id_cautat}"):
                c.execute("DELETE FROM rezervari WHERE id=?", (id_cautat,))
                conn.commit()
                st.rerun()

# --- REZERVĂRILE ȘI STATISTICILE RĂMÂN LA FEL CA ÎN CODUL ANTERIOR ---
# (Pastreaza restul codului de la choice == "📊 Statistici", "➕ Rezervare Nouă", etc.)
