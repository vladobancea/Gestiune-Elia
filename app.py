import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import urllib.parse
import calendar
from fpdf import FPDF

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Pensiune Manager Pro", layout="wide", initial_sidebar_state="collapsed")

# --- STYLING CSS AVANSAT (LINIE CONTINUĂ & ID CENTRAL) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 15px; }
    .custom-table { width: 100%; border-collapse: collapse; min-width: 1000px; table-layout: fixed; }
    .custom-table th, .custom-table td { border: 1px solid #eee; padding: 0px; text-align: center; height: 50px; }
    
    .sticky-col { 
        position: sticky; left: 0; background: #fff; z-index: 10; 
        font-weight: bold; border-right: 2px solid #3498db !important; width: 120px;
        padding: 10px !important;
    }
    
    .calendar-box { 
        height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; 
        font-size: 13px; font-weight: bold; color: white; margin: 0; padding: 0;
    }

    /* --- LOGICA CULORILOR PENTRU LINIE CONTINUĂ --- */
    .bg-liber { background: #2ECC71; margin: 2px; border-radius: 4px; height: 40px; }
    
    /* Ocupat (mijlocul sejurului) - fără margini rotunjite pentru continuitate */
    .bg-ocupat { background: #E74C3C; height: 40px; border-top: 2px solid #f8f9fa; border-bottom: 2px solid #f8f9fa; }
    
    /* Check-out (plecare) - rotunjit doar la dreapta */
    .bg-checkout { 
        background: linear-gradient(90deg, #E74C3C 50%, #2ECC71 50%); 
        height: 40px; border-radius: 0 4px 4px 0;
    }
    
    /* Check-in (intrare) - rotunjit doar la stânga */
    .bg-checkin { 
        background: linear-gradient(90deg, #2ECC71 50%, #E74C3C 50%); 
        height: 40px; border-radius: 4px 0 0 4px;
    }
    
    /* Schimb în aceeași zi (In/Out) */
    .bg-schimb { 
        background: linear-gradient(90deg, #E74C3C 48%, #ffffff 50%, #E74C3C 52%); 
        height: 40px;
    }
    
    .info-card { background: white; padding: 20px; border-radius: 12px; border: 2px solid #3498db; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE SETUP ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)''')
conn.commit()

# Patch pentru coloana note (dacă lipsește)
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
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Telefon: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    pdf.cell(0, 10, f"Perioada: {str(r['checkin'])[:16]} - {str(r['checkout'])[:16]}", ln=True)
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
menu = ["📅 Harta", "📊 Statistici", "➕ Nouă", "👥 Grup", "📋 Listă"]
choice = st.sidebar.radio("Meniu", menu)

# --- 1. HARTA DISPONIBILITĂȚII ---
if choice == "📅 Harta":
    st.title("Harta Disponibilității")
    d_start = st.date_input("Start:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    
    df_rez = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df_rez['checkin_d'] = pd.to_datetime(df_rez['checkin']).dt.date
    df_rez['checkout_d'] = pd.to_datetime(df_rez['checkout']).dt.date

    # Tabel HTML cu scroll
    html_code = '<div class="scroll-container"><table class="custom-table"><thead><tr>'
    html_code += '<th class="sticky-col">Cameră</th>'
    for d in zile: html_code += f'<th>{d.strftime("%d/%m")}</th>'
    html_code += '</tr></thead><tbody>'

    for cam in CAMERE_INFO.keys():
        html_code += f'<tr><td class="sticky-col">{cam}</td>'
        for d in zile:
            # Găsim toate rezervările care ating această zi
            rez_zi = df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] <= d) & (df_rez['checkout_d'] >= d)]
            
            plecare = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkout_d'] == d)].empty
            sosire = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] == d)].empty
            ocupat = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] < d) & (df_rez['checkout_d'] > d)].empty
            
            bg_class, label = "bg-liber", ""
            
            if plecare and sosire: bg_class = "bg-schimb"
            elif plecare: bg_class = "bg-checkout"
            elif sosire: bg_class = "bg-checkin"
            elif ocupat: bg_class = "bg-ocupat"
            
            # Logică ID Central (apare o singură dată la mijlocul sejurului)
            if not rez_zi.empty and bg_class != "bg-liber":
                r_act = rez_zi.iloc[0]
                mijloc_idx = (r_act['checkout_d'] - r_act['checkin_d']).days // 2
                mijloc_data = r_act['checkin_d'] + timedelta(days=mijloc_idx)
                if d == mijloc_data:
                    label = str(r_act['id'])
            
            html_code += f'<td><div class="calendar-box {bg_class}">{label}</div></td>'
        html_code += '</tr>'
    
    html_code += '</tbody></table></div>'
    st.markdown(html_code, unsafe_allow_html=True)

    # Selector Detalii sub Hartă
    st.markdown("---")
    id_sel = st.selectbox("🔍 Detalii pentru ID:", ["-"] + sorted(df_rez['id'].unique().tolist()))
    if id_sel != "-":
        r = df_rez[df_rez['id'] == int(id_sel)].iloc[0]
        st.markdown(f"""<div class="info-card">
            <h4>👤 {r['nume']}</h4>
            <p>📅 {str(r['checkin'])[5:16]} → {str(r['checkout'])[5:16]} | 💰 {r['pret_total']} RON</p>
            <p>📱 {r['telefon']} | 📝 {r['note'] if r['note'] else '-'}</p>
        </div>""", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.download_button("📄 PDF", genereaza_pdf(r), f"Rez_{id_sel}.pdf", key=f"pdf_h_{id_sel}")
        msg = f"Salut {r['nume']}! Confirmam rezervarea ({str(r['checkin'])[:10]})."
        c2.markdown(f'<a href="https://api.whatsapp.com/send?phone={r["telefon"]}&text={urllib.parse.quote(msg)}" target="_blank"><button style="width:100%; height:38px; background:#25D366; color:white; border:none; border-radius:5px;">📱 WA</button></a>', unsafe_allow_html=True)
        if c3.button("🗑️ Șterge", key=f"del_h_{id_sel}"):
            c.execute("DELETE FROM rezervari WHERE id=?", (id_sel,)); conn.commit(); st.rerun()

# --- 2. STATISTICI ---
elif choice == "📊 Statistici":
    st.title("📊 Statistici Venituri")
    df = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    if not df.empty:
        df['checkin'] = pd.to_datetime(df['checkin'])
        st.metric("Total Încasări", f"{df['pret_total'].sum():,.0f} RON")
        st.bar_chart(df.groupby(df['checkin'].dt.month)['pret_total'].sum())
    else: st.info("Nu există date pentru statistici.")

# --- 3. REZERVARE NOUĂ / GRUP ---
elif choice in ["➕ Nouă", "👥 Grup"]:
    st.title(choice)
    is_g = "Grup" in choice
    with st.form("add_form"):
        nume = st.text_input("Nume Client")
        tel = st.text_input("Telefon (ex: 407...)")
        cam = "Toate" if is_g else st.selectbox("Cameră", list(CAMERE_INFO.keys()))
        d1 = st.date_input("Check-in", date.today())
        d2 = st.date_input("Check-out", date.today() + timedelta(1))
        pret = st.number_input("Preț Total", value=float(sum(CAMERE_INFO.values()) if is_g else CAMERE_INFO[cam]))
        note = st.text_area("Note")
        if st.form_submit_button("Salvează"):
            t1, t2 = datetime.combine(d1, datetime.min.time().replace(hour=15)), datetime.combine(d2, datetime.min.time().replace(hour=11))
            cms = list(CAMERE_INFO.keys()) if is_g else [cam]
            if all(este_disponibila(c_n, t1, t2) for c_n in cms):
                for cn in cms: c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)", (nume, tel, cn, t1, t2, 'Confirmat', pret/6 if is_g else pret, note))
                conn.commit(); st.balloons(); st.rerun()
            else: st.error("Conflict de disponibilitate!")

# --- 4. LISTĂ REZERVĂRI ---
elif choice == "📋 Listă":
    st.title("Listă Rezervări")
    df_l = pd.read_sql_query("SELECT * FROM rezervari ORDER BY checkin DESC", conn)
    for _, r in df_l.iterrows():
        st.markdown(f"""<div style="background:white; padding:15px; border-radius:10px; border-left:8px solid #3498db; margin-bottom:10px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
            <b>{r['camera']} - {r['nume']}</b><br>{str(r['checkin'])[:10]} -> {str(r['checkout'])[:10]}</div>""", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.download_button("📄 PDF", genereaza_pdf(r), f"Rez_{r['id']}.pdf", key=f"dl_{r['id']}")
        wa = f"https://api.whatsapp.com/send?phone={r['telefon']}&text=Salut!"
        c2.markdown(f'<a href="{wa}" target="_blank"><button style="width:100%; height:35px; background:#25D366; color:white; border:none; border-radius:5px;">📱 WA</button></a>', unsafe_allow_html=True)
        if c3.button("🗑️", key=f"del_l_{r['id']}"):
            c.execute("DELETE FROM rezervari WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
