import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import urllib.parse
import calendar
from fpdf import FPDF

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Pensiune Manager Pro", layout="wide")

# --- STYLING CSS (Harta & Carduri) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .calendar-box { height: 40px; width: 100%; border-radius: 4px; border: 1px solid #ddd; }
    .bg-liber { background: #2ECC71; }
    .bg-ocupat { background: #E74C3C; }
    .bg-checkout { background: linear-gradient(90deg, #E74C3C 50%, #2ECC71 50%); }
    .bg-checkin { background: linear-gradient(90deg, #2ECC71 50%, #E74C3C 50%); }
    .bg-schimb { background: linear-gradient(90deg, #E74C3C 48%, #ffffff 50%, #E74C3C 52%); }
    .cam-name { font-weight: bold; padding-top: 10px; font-size: 14px; }
    .booking-card { 
        background: white; 
        padding: 15px; 
        border-radius: 12px; 
        border-left: 8px solid #3498DB; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        margin-bottom: 15px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE SETUP ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)''')
conn.commit()

# Patch pentru baza de date (asigură coloana note)
try:
    c.execute("ALTER TABLE rezervari ADD COLUMN note TEXT")
    conn.commit()
except:
    pass

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- FUNCTII AJUTATOARE ---
def este_disponibila(camera, start, end):
    query = "SELECT * FROM rezervari WHERE status != 'Anulat' AND camera = ? AND NOT (checkout <= ? OR checkin >= ?)"
    c.execute(query, (camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')))
    return len(c.fetchall()) == 0

def genereaza_pdf(r):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "CONFIRMARE REZERVARE", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Pensiunea Mea - Bran, Romania", ln=True)
    pdf.cell(0, 10, f"Data document: {date.today()}", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Telefon: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    pdf.cell(0, 10, f"Check-in: {str(r['checkin'])[:16]}", ln=True)
    pdf.cell(0, 10, f"Check-out: {str(r['checkout'])[:16]}", ln=True)
    pdf.cell(0, 10, f"Total de plata: {r['pret_total']} RON", ln=True)
    if r['note']:
        pdf.ln(5)
        pdf.multi_cell(0, 10, f"Note: {r['note']}")
    return pdf.output(dest='S').encode('latin-1')

# --- MENIU SIDEBAR ---
st.sidebar.title("🏨 Manager Pensiune")
menu = ["📅 Harta Disponibilității", "📊 Statistici", "➕ Rezervare Nouă", "👥 Rezervare Grup", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Navigare", menu)

# --- 1. HARTA DISPONIBILITĂȚII ---
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
            plecare = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkout_d'] == d)].empty
            sosire = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] == d)].empty
            ocupat = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] < d) & (df_rez['checkout_d'] > d)].empty
            
            clasa = "bg-liber"
            if plecare and sosire: clasa = "bg-schimb"
            elif plecare: clasa = "bg-checkout"
            elif sosire: clasa = "bg-checkin"
            elif ocupat: clasa = "bg-ocupat"
            row[i+1].markdown(f'<div class="calendar-box {clasa}"></div>', unsafe_allow_html=True)

# --- 2. STATISTICI ---
elif choice == "📊 Statistici":
    st.title("📊 Statistici Performanță")
    df = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    if not df.empty:
        df['checkin'] = pd.to_datetime(df['checkin'])
        df['checkout'] = pd.to_datetime(df['checkout'])
        df['luna'] = df['checkin'].dt.month
        df['an'] = df['checkin'].dt.year
        df['nopti'] = (df['checkout'] - df['checkin']).dt.days
        
        an_sel = st.selectbox("Anul", sorted(df['an'].unique(), reverse=True))
        df_an = df[df['an'] == an_sel]
        
        c1, c2 = st.columns(2)
        c1.metric("Venituri Totale", f"{df_an['pret_total'].sum():,.0f} RON")
        z_an = 366 if calendar.isleap(an_sel) else 365
        c2.metric("Grad Ocupare", f"{(df_an['nopti'].sum() / (6 * z_an))*100:.1f}%")
        st.bar_chart(df_an.groupby('luna')['pret_total'].sum())
    else:
        st.info("Nu există date încă.")

# --- 3. REZERVARE NOUĂ / GRUP ---
elif choice in ["➕ Rezervare Nouă", "👥 Rezervare Grup"]:
    st.title(choice)
    is_grup = "Grup" in choice
    
    with st.form("form_rezervare"):
        nume = st.text_input("Nume Client")
        tel = st.text_input("Telefon (ex: 40722123456)")
        cam_sel = "Toate (Grup)" if is_grup else st.selectbox("Cameră", list(CAMERE_INFO.keys()))
        
        col1, col2 = st.columns(2)
        d_in = col1.date_input("Data Check-in", date.today())
        d_out = col2.date_input("Data Check-out", date.today() + timedelta(days=1))
        
        pret_sugerat = sum(CAMERE_INFO.values()) if is_grup else CAMERE_INFO[cam_sel]
        pret = st.number_input("Preț Total (RON)", value=float(pret_sugerat))
        note = st.text_area("Note / Observații")
        
        if st.form_submit_button("✅ Salvează Rezervarea"):
            # Setăm orele by default
            t_in = datetime.combine(d_in, datetime.strptime("15:00", "%H:%M").time())
            t_out = datetime.combine(d_out, datetime.strptime("11:00", "%H:%M").time())
            
            camere_de_rezervat = list(CAMERE_INFO.keys()) if is_grup else [cam_sel]
            
            # Verificăm disponibilitatea pentru toate camerele selectate
            conflict = [c for c in camere_de_rezervat if not este_disponibila(c, t_in, t_out)]
            
            if conflict:
                st.error(f"❌ Camerele următoare sunt deja ocupate: {', '.join(conflict)}")
            else:
                for c_name in camere_de_rezervat:
                    p_individual = pret / 6 if is_grup else pret
                    c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)",
                              (nume, tel, c_name, t_in, t_out, "Confirmat", p_individual, note))
                conn.commit()
                st.balloons()
                st.success(f"Rezervare salvată cu succes pentru {nume}!")
                st.rerun()

# --- 4. LISTĂ REZERVĂRI ---
elif choice == "📋 Listă Rezervări":
    st.title("📋 Lista Rezervărilor")
    df_list = pd.read_sql_query("SELECT * FROM rezervari ORDER BY checkin DESC", conn)
    
    if df_list.empty:
        st.info("Nu există rezervări înregistrate.")
    else:
        for index, r in df_list.iterrows():
            with st.container():
                st.markdown(f"""
                    <div class="booking-card">
                        <h3 style="margin:0;">{r['camera']} - {r['nume']}</h3>
                        <p style="margin:5px 0;">📅 {str(r['checkin'])[5:16]} → {str(r['checkout'])[5:16]}</p>
                        <p style="margin:0;">💰 {r['pret_total']} RON | 📱 {r['telefon']}</p>
                        <p style="margin:5px 0; font-size: 14px; color: #666;">📝 {r['note'] if r['note'] else '-'}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                
                # PDF Button
                pdf_bytes = genereaza_pdf(r)
                c1.download_button(label="📄 Descarcă PDF", data=pdf_bytes, file_name=f"Rezervare_{r['nume']}.pdf", mime="application/pdf", key=f"pdf_{r['id']}")
                
                # WhatsApp Button
                msg = f"Salut {r['nume']}! Confirmam rezervarea la Pensiune ({str(r['checkin'])[:10]}). Te asteptam!"
                wa_url = f"https://api.whatsapp.com/send?phone={r['telefon']}&text={urllib.parse.quote(msg)}"
                c2.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; height:38px; background-color:#25D366; color:white; border:none; border-radius:5px; cursor:pointer;">📱 WhatsApp</button></a>', unsafe_allow_html=True)
                
                # Delete Button
                if c3.button(f"🗑️ Șterge", key=f"del_{r['id']}"):
                    c.execute("DELETE FROM rezervari WHERE id = ?", (r['id'],))
                    conn.commit()
                    st.rerun()
