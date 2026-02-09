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
    .main { background-color: #f8f9fa; }
    .calendar-box { 
        height: 40px; width: 100%; border-radius: 4px; border: 1px solid #ddd; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 11px; font-weight: bold; color: white; text-shadow: 1px 1px 2px black;
    }
    .bg-liber { background: #2ECC71; }
    .bg-ocupat { background: #E74C3C; }
    .bg-checkout { background: linear-gradient(90deg, #E74C3C 50%, #2ECC71 50%); }
    .bg-checkin { background: linear-gradient(90deg, #2ECC71 50%, #E74C3C 50%); }
    .bg-schimb { background: linear-gradient(90deg, #E74C3C 48%, #ffffff 50%, #E74C3C 52%); }
    .cam-name { font-weight: bold; padding-top: 10px; font-size: 14px; }
    .info-card { background: #ffffff; padding: 20px; border-radius: 12px; border: 2px solid #3498db; margin-top: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE SETUP ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)''')
conn.commit()

# Patch bază de date pentru coloane noi
try:
    c.execute("ALTER TABLE rezervari ADD COLUMN note TEXT")
    conn.commit()
except: pass

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- FUNCȚII ---
def genereaza_pdf(r):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "CONFIRMARE REZERVARE", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Pensiunea Mea - Bran", ln=True)
    pdf.cell(0, 10, f"Data document: {date.today()}", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Telefon: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    pdf.cell(0, 10, f"Check-in: {str(r['checkin'])[:16]}", ln=True)
    pdf.cell(0, 10, f"Check-out: {str(r['checkout'])[:16]}", ln=True)
    pdf.cell(0, 10, f"Pret Total: {r['pret_total']} RON", ln=True)
    if r['note']:
        pdf.ln(5)
        pdf.multi_cell(0, 10, f"Note: {r['note']}")
    return pdf.output(dest='S').encode('latin-1')

def este_disponibila(camera, start, end):
    query = "SELECT * FROM rezervari WHERE status != 'Anulat' AND camera = ? AND NOT (checkout <= ? OR checkin >= ?)"
    c.execute(query, (camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')))
    return len(c.fetchall()) == 0

# --- NAVIGARE ---
st.sidebar.title("🏨 Manager Pensiune")
menu = ["📅 Harta Disponibilității", "📊 Statistici & Venituri", "➕ Rezervare Nouă", "👥 Rezervare Grup", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Navigare", menu)

# --- 1. HARTA DISPONIBILITĂȚII ---
if choice == "📅 Harta Disponibilității":
    st.title("Harta Disponibilității")
    d_start = st.date_input("Vezi de la data:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    
    # Grid Header
    cols = st.columns([1.5] + [1]*14)
    cols[0].write("**Cameră**")
    for i, d in enumerate(zile): cols[i+1].write(f"**{d.strftime('%d/%m')}**")

    # Date Rezervări
    df_rez = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df_rez['checkin_d'] = pd.to_datetime(df_rez['checkin']).dt.date
    df_rez['checkout_d'] = pd.to_datetime(df_rez['checkout']).dt.date

    for cam in CAMERE_INFO.keys():
        row = st.columns([1.5] + [1]*14)
        row[0].markdown(f"<div class='cam-name'>{cam}</div>", unsafe_allow_html=True)
        for i, d in enumerate(zile):
            # Identificăm rezervarea pentru celula curentă (ID-ul)
            rez_aici = df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] <= d) & (df_rez['checkout_d'] >= d)]
            
            plecare = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkout_d'] == d)].empty
            sosire = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] == d)].empty
            ocupat = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] < d) & (df_rez['checkout_d'] > d)].empty
            
            clasa, label = "bg-liber", ""
            if plecare and sosire: clasa = "bg-schimb"
            elif plecare: clasa = "bg-checkout"
            elif sosire: clasa = "bg-checkin"
            elif ocupat: clasa = "bg-ocupat"
            
            if not rez_aici.empty and clasa != "bg-liber":
                label = str(rez_aici.iloc[0]['id'])

            row[i+1].markdown(f'<div class="calendar-box {clasa}">{label}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🔍 Detalii Rezervare (Selectează ID de pe hartă)")
    id_sel = st.selectbox("Alege ID-ul pentru detalii:", ["-"] + sorted(df_rez['id'].unique().tolist()))
    
    if id_sel != "-":
        r = df_rez[df_rez['id'] == int(id_sel)].iloc[0]
        st.markdown(f"""<div class="info-card">
            <h3>👤 {r['nume']}</h3>
            <p>📅 {str(r['checkin'])[5:16]} → {str(r['checkout'])[5:16]} | 🛏️ {r['camera']}</p>
            <p>💰 <b>Pret Total:</b> {r['pret_total']} RON | 📱 <b>Tel:</b> {r['telefon']}</p>
            <p>📝 <b>Note:</b> {r['note'] if r['note'] else '-'}</p>
        </div>""", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        pdf_b = genereaza_pdf(r)
        c1.download_button("📄 Descarcă PDF", pdf_b, f"Rez_{id_sel}.pdf", key=f"pdf_h_{id_sel}")
        msg = f"Salut {r['nume']}! Confirmam rezervarea ({str(r['checkin'])[:10]})."
        c2.markdown(f'<a href="https://api.whatsapp.com/send?phone={r["telefon"]}&text={urllib.parse.quote(msg)}" target="_blank"><button style="width:100%; height:38px; background-color:#25D366; color:white; border:none; border-radius:5px;">📱 WhatsApp</button></a>', unsafe_allow_html=True)
        if c3.button("🗑️ Șterge", key=f"del_h_{id_sel}"):
            c.execute("DELETE FROM rezervari WHERE id=?", (id_sel,))
            conn.commit()
            st.rerun()

# --- 2. STATISTICI ---
elif choice == "📊 Statistici & Venituri":
    st.title("Rapoarte Performanță")
    df = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    if not df.empty:
        df['checkin'] = pd.to_datetime(df['checkin'])
        df['checkout'] = pd.to_datetime(df['checkout'])
        df['an'] = df['checkin'].dt.year
        df['luna'] = df['checkin'].dt.month
        df['nopti'] = (df['checkout'] - df['checkin']).dt.days
        
        an_sel = st.selectbox("An", sorted(df['an'].unique(), reverse=True))
        df_an = df[df['an'] == an_sel]
        
        col1, col2 = st.columns(2)
        col1.metric("Venituri Totale", f"{df_an['pret_total'].sum():,.0f} RON")
        grad = (df_an['nopti'].sum() / (6 * (366 if calendar.isleap(an_sel) else 365))) * 100
        col2.metric("Grad Ocupare", f"{grad:.1f}%")
        
        st.bar_chart(df_an.groupby('luna')['pret_total'].sum())
    else: st.info("Nu există date.")

# --- 3. REZERVARE NOUĂ / GRUP ---
elif choice in ["➕ Rezervare Nouă", "👥 Rezervare Grup"]:
    st.title(choice)
    is_g = "Grup" in choice
    with st.form("add_form"):
        nume = st.text_input("Nume Client")
        tel = st.text_input("Telefon (40...)")
        cam = "Toate" if is_g else st.selectbox("Cameră", list(CAMERE_INFO.keys()))
        d1, d2 = st.columns(2)
        in_d = d1.date_input("Check-in", date.today())
        out_d = d2.date_input("Check-out", date.today() + timedelta(1))
        pret = st.number_input("Pret Total", value=float(sum(CAMERE_INFO.values()) if is_g else CAMERE_INFO[cam]))
        note = st.text_area("Note")
        if st.form_submit_button("Salvează"):
            t1, t2 = datetime.combine(in_d, datetime.min.time().replace(hour=15)), datetime.combine(out_d, datetime.min.time().replace(hour=11))
            cms = list(CAMERE_INFO.keys()) if is_g else [cam]
            if all(este_disponibila(x, t1, t2) for x in cms):
                for x in cms: c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)", (nume, tel, x, t1, t2, 'Confirmat', pret/6 if is_g else pret, note))
                conn.commit()
                st.balloons(); st.rerun()
            else: st.error("Conflict de date!")

# --- 4. LISTĂ REZERVĂRI ---
elif choice == "📋 Listă Rezervări":
    st.title("Listă Rezervări")
    df_l = pd.read_sql_query("SELECT * FROM rezervari ORDER BY checkin DESC", conn)
    for _, r in df_l.iterrows():
        with st.container():
            st.markdown(f"""<div style="background:white; padding:15px; border-radius:10px; border-left:8px solid #3498db; margin-bottom:10px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
                <b>{r['camera']} - {r['nume']}</b><br>{str(r['checkin'])[:10]} -> {str(r['checkout'])[:10]} | {r['pret_total']} RON</div>""", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.download_button("📄 PDF", genereaza_pdf(r), f"Rez_{r['id']}.pdf", key=f"dl_{r['id']}")
            wa = f"https://api.whatsapp.com/send?phone={r['telefon']}&text=Salut!"
            c2.markdown(f'<a href="{wa}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; border-radius:5px; height:35px;">📱 WA</button></a>', unsafe_allow_html=True)
            if c3.button("🗑️", key=f"del_l_{r['id']}"):
                c.execute("DELETE FROM rezervari WHERE id=?", (r['id'],))
                conn.commit(); st.rerun()
