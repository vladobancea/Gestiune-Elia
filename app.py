import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date, time  # Am adăugat 'time' aici
import urllib.parse
import calendar
from fpdf import FPDF

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Pensiune Manager Pro", layout="wide", initial_sidebar_state="collapsed")

# --- STYLING CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 15px; }
    .custom-table { width: 100%; border-collapse: collapse; min-width: 1000px; table-layout: fixed; border: none; }
    .custom-table th { border: 1px solid #ddd; padding: 10px; background: #f1f3f4; font-size: 14px; }
    .custom-table td { border: none; padding: 0 !important; margin: 0 !important; height: 50px; vertical-align: middle; }
    .sticky-col { 
        position: sticky; left: 0; background: #fff; z-index: 10; 
        font-weight: bold; border-right: 2px solid #3498db !important; width: 120px;
        padding: 5px !important; border-top: 1px solid #eee; border-bottom: 1px solid #eee;
    }
    .calendar-box { 
        height: 42px; width: 100%; display: flex; align-items: center; justify-content: center; 
        font-size: 14px; font-weight: bold; color: white; margin: 0; padding: 0;
    }
    .bg-liber { background: #2ECC71; border: 1px solid #fff; border-radius: 4px; height: 38px; width: 95%; margin: auto; }
    .bg-ocupat { background: #E74C3C; border-top: 2px solid #f8f9fa; border-bottom: 2px solid #f8f9fa; width: 100%; }
    .bg-checkout { background: linear-gradient(90deg, #E74C3C 50%, #2ECC71 50%); border-top: 2px solid #f8f9fa; border-bottom: 2px solid #f8f9fa; }
    .bg-checkin { background: linear-gradient(90deg, #2ECC71 50%, #E74C3C 50%); border-top: 2px solid #f8f9fa; border-bottom: 2px solid #f8f9fa; }
    .bg-schimb { background: linear-gradient(90deg, #E74C3C 48%, #ffffff 50%, #E74C3C 52%); }
    .info-card { background: white; padding: 20px; border-radius: 12px; border: 2px solid #3498db; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)''')
conn.commit()

try:
    c.execute("ALTER TABLE rezervari ADD COLUMN note TEXT")
    conn.commit()
except: pass

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- FUNCȚII ---
def este_disponibila(camera, start, end):
    query = "SELECT * FROM rezervari WHERE status != 'Anulat' AND camera = ? AND NOT (checkout <= ? OR checkin >= ?)"
    c.execute(query, (camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')))
    return len(c.fetchall()) == 0

def genereaza_pdf(r):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "CONFIRMARE REZERVARE", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12); pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']} | Perioada: {str(r['checkin'])[:10]} - {str(r['checkout'])[:10]}", ln=True)
    pdf.cell(0, 10, f"Pret Total: {r['pret_total']} RON", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- MENIU ---
menu = ["📅 Harta", "📊 Statistici", "➕ Nouă", "👥 Grup", "📋 Listă"]
choice = st.sidebar.radio("Navigare", menu)

# --- 1. HARTA DISPONIBILITĂȚII ---
if choice == "📅 Harta":
    st.title("Harta Disponibilității")
    d_start = st.date_input("Start:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    
    df_rez = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df_rez['checkin_d'] = pd.to_datetime(df_rez['checkin']).dt.date
    df_rez['checkout_d'] = pd.to_datetime(df_rez['checkout']).dt.date

    html_code = '<div class="scroll-container"><table class="custom-table"><thead><tr><th class="sticky-col">Cameră</th>'
    for d in zile: html_code += f'<th>{d.strftime("%d/%m")}</th>'
    html_code += '</tr></thead><tbody>'

    for cam in CAMERE_INFO.keys():
        html_code += f'<tr><td class="sticky-col">{cam}</td>'
        for d in zile:
            rez_activa = df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] <= d) & (df_rez['checkout_d'] >= d)]
            plecare = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkout_d'] == d)].empty
            sosire = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] == d)].empty
            ocupat_full = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin_d'] < d) & (df_rez['checkout_d'] > d)].empty
            
            bg, label = "bg-liber", ""
            if plecare and sosire: bg = "bg-schimb"
            elif plecare: bg = "bg-checkout"
            elif sosire: bg = "bg-checkin"
            elif ocupat_full: bg = "bg-ocupat"
            
            if not rez_activa.empty and bg != "bg-liber":
                r = rez_activa.iloc[0]
                mijloc = r['checkin_d'] + timedelta(days=(r['checkout_d'] - r['checkin_d']).days // 2)
                if d == mijloc: label = str(r['id'])
            
            html_code += f'<td><div class="calendar-box {bg}">{label}</div></td>'
        html_code += '</tr>'
    
    st.markdown(html_code + '</tbody></table></div>', unsafe_allow_html=True)

    # Detalii rapide sub hartă
    st.markdown("---")
    id_sel = st.selectbox("🔍 Detalii pentru ID:", ["-"] + sorted([str(i) for i in df_rez['id'].unique()]))
    if id_sel != "-":
        r_det = df_rez[df_rez['id'] == int(id_sel)].iloc[0]
        st.markdown(f'<div class="info-card"><h4>👤 {r_det["nume"]}</h4><p>📅 {str(r_det["checkin"])[5:16]} → {str(r_det["checkout"])[5:16]}</p><p>📱 {r_det["telefon"]} | 💰 {r_det["pret_total"]} RON</p></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.download_button("📄 PDF", genereaza_pdf(r_det), f"Rez_{id_sel}.pdf", key=f"hp_{id_sel}")
        wa = f"https://api.whatsapp.com/send?phone={r_det['telefon']}&text=Salut!"
        c2.markdown(f'<a href="{wa}" target="_blank"><button style="width:100%; height:38px; background:#25D366; color:white; border:none; border-radius:5px;">📱 WA</button></a>', unsafe_allow_html=True)
        if c3.button("🗑️ Șterge", key=f"hd_{id_sel}"):
            c.execute("DELETE FROM rezervari WHERE id=?", (id_sel,)); conn.commit(); st.rerun()

# --- 2. STATISTICI ---
elif choice == "📊 Statistici":
    st.title("📊 Statistici")
    df = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    if not df.empty:
        st.metric("Total Venituri", f"{df['pret_total'].sum():,.0f} RON")
        df['luna'] = pd.to_datetime(df['checkin']).dt.month
        st.bar_chart(df.groupby('luna')['pret_total'].sum())
    else: st.info("Lipsă date.")

# --- 3. REZERVARE NOUĂ / GRUP ---
elif choice in ["➕ Nouă", "👥 Grup"]:
    st.title(choice)
    is_g = "Grup" in choice
    with st.form("f_add"):
        nume = st.text_input("Nume Client"); tel = st.text_input("Telefon (40...)")
        cam = "Toate" if is_g else st.selectbox("Cameră", list(CAMERE_INFO.keys()))
        d1 = st.date_input("In", date.today()); d2 = st.date_input("Out", date.today()+timedelta(1))
        pret = st.number_input("Pret Total", value=float(sum(CAMERE_INFO.values()) if is_g else CAMERE_INFO[cam]))
        note = st.text_area("Note")
        if st.form_submit_button("Salvează"):
            # REPARARE EROARE: folosim time(15,0) direct din import
            t1, t2 = datetime.combine(d1, time(15, 0)), datetime.combine(d2, time(11, 0))
            cms = list(CAMERE_INFO.keys()) if is_g else [cam]
            if all(este_disponibila(c_n, t1, t2) for c_n in cms):
                for cn in cms: c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)", (nume, tel, cn, t1, t2, 'Confirmat', pret/6 if is_g else pret, note))
                conn.commit(); st.balloons(); st.rerun()
            else: st.error("Cameră ocupată!")

# --- 4. LISTĂ REZERVĂRI ---
elif choice == "📋 Listă":
    st.title("Listă Rezervări")
    df_l = pd.read_sql_query("SELECT * FROM rezervari ORDER BY checkin DESC", conn)
    for _, r in df_l.iterrows():
        st.markdown(f'<div class="booking-card"><b>{r["camera"]} - {r["nume"]}</b><br>{str(r["checkin"])[:10]} -> {str(r["checkout"])[:10]} | {r["pret_total"]} RON</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.download_button("📄 PDF", genereaza_pdf(r), f"Rez_{r['id']}.pdf", key=f"lp_{r['id']}")
        if c2.button("🗑️ Șterge", key=f"ld_{r['id']}"):
            c.execute("DELETE FROM rezervari WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
