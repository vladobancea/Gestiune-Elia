import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date, time
import urllib.parse
import calendar
from fpdf import FPDF

# --- 1. CONFIGURARE ȘI CSS ---
st.set_page_config(page_title="Manager Pensiune Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Stiluri Generale */
    .main { background-color: #f8f9fa; }
    
    /* Container Scrollabil pentru Mobil */
    .scroll-container { overflow-x: auto; white-space: nowrap; padding-bottom: 20px; }
    
    /* Tabel Optimizat - Fără spații între celule pentru continuitate */
    .custom-table { width: 100%; border-collapse: collapse; min-width: 1000px; table-layout: fixed; border: none; }
    .custom-table th { border: 1px solid #ddd; padding: 10px; background: #f1f3f4; font-size: 14px; position: sticky; top: 0; z-index: 5; }
    .custom-table td { border: none; padding: 0 !important; margin: 0 !important; height: 55px; vertical-align: middle; position: relative; }
    
    /* Coloana Fixă (Nume Cameră) */
    .sticky-col { 
        position: sticky; left: 0; background: #fff; z-index: 10; 
        font-weight: bold; border-right: 3px solid #3498db !important; width: 130px;
        padding: 5px !important; border-top: 1px solid #eee; border-bottom: 1px solid #eee;
        color: #2c3e50;
    }
    
    /* Celula Calendar - Design Bandă */
    .calendar-box { 
        height: 46px; width: 100%; display: flex; align-items: center; justify-content: center; 
        font-size: 13px; font-weight: bold; color: white; margin: 0; padding: 0; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    }

    /* --- CULORI ȘI CONTINUITATE --- */
    /* Liber: Celulă distinctă */
    .bg-liber { background: #2ECC71; border: 1px solid #fff; border-radius: 6px; height: 40px; width: 90%; margin: auto; opacity: 0.3; }
    
    /* Ocupat: Bandă continuă (100.5% lățime ca să acopere bordura) */
    .bg-ocupat { background: #E74C3C; width: 100.5%; border-top: 3px solid #f8f9fa; border-bottom: 3px solid #f8f9fa; }
    
    /* Check-in: Gradient Verde -> Roșu */
    .bg-checkin { background: linear-gradient(90deg, #f8f9fa 5%, #2ECC71 5%, #2ECC71 45%, #E74C3C 55%); border-top: 3px solid #f8f9fa; border-bottom: 3px solid #f8f9fa; width: 100.5%; }
    
    /* Check-out: Gradient Roșu -> Verde */
    .bg-checkout { background: linear-gradient(90deg, #E74C3C 45%, #2ECC71 55%, #2ECC71 95%, #f8f9fa 95%); border-top: 3px solid #f8f9fa; border-bottom: 3px solid #f8f9fa; width: 100.5%; }
    
    /* Schimb: Roșu -> Alb -> Roșu */
    .bg-schimb { background: linear-gradient(90deg, #E74C3C 45%, #ffffff 50%, #E74C3C 55%); border-top: 3px solid #f8f9fa; border-bottom: 3px solid #f8f9fa; width: 100.5%; color: #333 !important; text-shadow: none; font-size: 11px; }

    /* Carduri Informative */
    .info-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #3498db; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 15px; }
    
    /* Buton Mare Sidebar */
    .big-button { width: 100%; font-size: 18px; font-weight: bold; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE SETUP ---
conn = sqlite3.connect('pensiune.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rezervari 
             (id INTEGER PRIMARY KEY, nume TEXT, telefon TEXT, camera TEXT, 
              checkin DATETIME, checkout DATETIME, status TEXT, pret_total REAL, note TEXT)''')
conn.commit()

# Patch pentru coloana note (dacă lipsește în versiuni vechi)
try:
    c.execute("ALTER TABLE rezervari ADD COLUMN note TEXT")
    conn.commit()
except: pass

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- 3. FUNCȚII UTILITARE ---
def este_disponibila(camera, start, end, exclude_id=None):
    query = "SELECT * FROM rezervari WHERE status != 'Anulat' AND camera = ? AND NOT (checkout <= ? OR checkin >= ?)"
    params = [camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')]
    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)
    c.execute(query, params)
    return len(c.fetchall()) == 0

def genereaza_pdf(r):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "CONFIRMARE REZERVARE", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True)
    pdf.cell(0, 10, f"Telefon: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True)
    pdf.cell(0, 10, f"Perioada: {str(r['checkin'])[:10]} -> {str(r['checkout'])[:10]}", ln=True)
    pdf.cell(0, 10, f"Total Plata: {r['pret_total']} RON", ln=True)
    if r['note']:
        pdf.ln(5); pdf.multi_cell(0, 10, f"Note: {r['note']}")
    return pdf.output(dest='S').encode('latin-1')

# --- 4. SIDEBAR & NAVIGARE ---
st.sidebar.title("🏨 Manager Pensiune")

# Buton Universal de Adăugare
if st.sidebar.button("➕ ADAUGĂ REZERVARE", key="btn_add_sidebar", use_container_width=True, type="primary"):
    st.session_state['show_add_modal'] = True

menu = ["📅 Harta Disponibilității", "🗓️ Calendar Lunar", "📊 Statistici", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Meniu", menu)

# --- 5. MODAL ADĂUGARE REZERVARE (Apare oriunde) ---
if st.session_state.get('show_add_modal', False):
    st.markdown("---")
    with st.container():
        st.subheader("📝 Rezervare Nouă")
        with st.form("quick_add"):
            c1, c2 = st.columns(2)
            nume = c1.text_input("Nume Client")
            tel = c2.text_input("Telefon (ex: 407...)")
            cam = c1.selectbox("Cameră", list(CAMERE_INFO.keys()) + ["Toate (Grup)"])
            d1 = c2.date_input("Check-in", date.today())
            d2 = c2.date_input("Check-out", date.today() + timedelta(1))
            
            pret_default = sum(CAMERE_INFO.values()) if "Grup" in cam else (CAMERE_INFO[cam] if cam in CAMERE_INFO else 0)
            pret = c1.number_input("Preț Total", value=float(pret_default))
            note = st.text_area("Note")
            
            cols = st.columns(2)
            if cols[0].form_submit_button("✅ Salvează"):
                t1, t2 = datetime.combine(d1, time(15, 0)), datetime.combine(d2, time(11, 0))
                camere_target = list(CAMERE_INFO.keys()) if "Grup" in cam else [cam]
                
                if all(este_disponibila(c, t1, t2) for c in camere_target):
                    for c_name in camere_target:
                        p_part = pret / 6 if "Grup" in cam else pret
                        c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)", 
                                  (nume, tel, c_name, t1, t2, 'Confirmat', p_part, note))
                    conn.commit()
                    st.session_state['show_add_modal'] = False
                    st.success("Rezervare Salvată!"); st.rerun()
                else:
                    st.error("⚠️ Conflict! Una dintre camere este ocupată.")
            
            if cols[1].form_submit_button("❌ Închide"):
                st.session_state['show_add_modal'] = False
                st.rerun()
    st.markdown("---")

# --- 6. PAGINA: HARTA (14 Zile) ---
if choice == "📅 Harta Disponibilității":
    st.title("Harta Disponibilității")
    d_start = st.date_input("Start:", date.today())
    zile = [d_start + timedelta(days=i) for i in range(14)]
    d_end_view = zile[-1]
    
    df = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df['checkin_d'] = pd.to_datetime(df['checkin']).dt.date
    df['checkout_d'] = pd.to_datetime(df['checkout']).dt.date

    # Construire Tabel HTML
    html = '<div class="scroll-container"><table class="custom-table"><thead><tr><th class="sticky-col">Cameră</th>'
    for d in zile: html += f'<th>{d.strftime("%d/%m")}</th>'
    html += '</tr></thead><tbody>'

    for cam in CAMERE_INFO.keys():
        html += f'<tr><td class="sticky-col">{cam}</td>'
        for d in zile:
            # Filtrare rezervări relevante pentru ziua și camera curentă
            r_out = df[(df['camera'] == cam) & (df['checkout_d'] == d)]
            r_in = df[(df['camera'] == cam) & (df['checkin_d'] == d)]
            r_stay = df[(df['camera'] == cam) & (df['checkin_d'] < d) & (df['checkout_d'] > d)]
            
            bg, label = "bg-liber", ""
            
            # --- LOGICĂ VIZUALĂ & ID ---
            # 1. SCHIMB (Out + In)
            if not r_out.empty and not r_in.empty:
                bg = "bg-schimb"
                label = f"{r_out.iloc[0]['id']}|{r_in.iloc[0]['id']}"
            
            # 2. CHECK-OUT
            elif not r_out.empty:
                bg = "bg-checkout"
                r = r_out.iloc[0]
                # Afișare ID dacă e rezervare de 1 noapte sau dacă d e mijlocul vizibil
                if (r['checkout_d'] - r['checkin_d']).days <= 1: label = str(r['id'])
                else:
                     v_start = max(r['checkin_d'], d_start)
                     v_end = min(r['checkout_d'], d_end_view)
                     if d == v_start + timedelta(days=(v_end - v_start).days // 2): label = str(r['id'])

            # 3. CHECK-IN
            elif not r_in.empty:
                bg = "bg-checkin"
                r = r_in.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1: label = str(r['id'])
                else:
                     v_start = max(r['checkin_d'], d_start)
                     v_end = min(r['checkout_d'], d_end_view)
                     if d == v_start + timedelta(days=(v_end - v_start).days // 2): label = str(r['id'])

            # 4. OCUPAT COMPLET
            elif not r_stay.empty:
                bg = "bg-ocupat"
                r = r_stay.iloc[0]
                v_start = max(r['checkin_d'], d_start)
                v_end = min(r['checkout_d'], d_end_view)
                if d == v_start + timedelta(days=(v_end - v_start).days // 2): label = str(r['id'])
            
            html += f'<td><div class="calendar-box {bg}">{label}</div></td>'
        html += '</tr>'
    
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

    # --- SECȚIUNE EDITARE / DETALII ---
    st.markdown("### 🔍 Detalii & Editare")
    ids = sorted([str(i) for i in df['id'].unique()])
    id_sel = st.selectbox("Selectează ID-ul de pe hartă:", ["-"] + ids)
    
    if id_sel != "-":
        r = df[df['id'] == int(id_sel)].iloc[0]
        
        with st.container():
            st.info(f"Editare rezervare: {r['nume']} ({r['camera']})")
            
            # Formular Editare
            c1, c2, c3 = st.columns(3)
            new_tel = c1.text_input("Telefon", r['telefon'])
            new_pret = c2.number_input("Preț", value=float(r['pret_total']))
            new_note = c3.text_area("Note", r['note'])
            
            btn_col = st.columns(4)
            if btn_col[0].button("💾 Salvează Modificări"):
                c.execute("UPDATE rezervari SET telefon=?, pret_total=?, note=? WHERE id=?", (new_tel, new_pret, new_note, id_sel))
                conn.commit()
                st.success("Actualizat!"); st.rerun()
            
            # Butoane PDF / WhatsApp / Sterge
            btn_col[1].download_button("📄 PDF", genereaza_pdf(r), f"Rez_{id_sel}.pdf")
            
            wa_msg = urllib.parse.quote(f"Salut {r['nume']}, confirmam rezervarea la Elia pe {r['checkin_d']}.")
            btn_col[2].markdown(f'<a href="https://api.whatsapp.com/send?phone={new_tel}&text={wa_msg}" target="_blank"><button style="width:100%; border:none; background:#25D366; color:white; padding:5px; border-radius:5px;">📱 WhatsApp</button></a>', unsafe_allow_html=True)
            
            if btn_col[3].button("🗑️ Șterge"):
                c.execute("DELETE FROM rezervari WHERE id=?", (id_sel,))
                conn.commit(); st.warning("Șters!"); st.rerun()

# --- 7. PAGINA: CALENDAR LUNAR ---
elif choice == "🗓️ Calendar Lunar":
    st.title("🗓️ Calendar de Ansamblu")
    c1, c2 = st.columns(2)
    an = c1.selectbox("An", [2024, 2025, 2026], index=1)
    luna = c2.selectbox("Luna", list(range(1, 13)), index=datetime.now().month-1)
    
    cal = calendar.monthcalendar(an, luna)
    df = pd.read_sql_query("SELECT * FROM rezervari", conn)
    df['checkin_d'] = pd.to_datetime(df['checkin']).dt.date
    df['checkout_d'] = pd.to_datetime(df['checkout']).dt.date

    st.markdown("### Grad de ocupare")
    cols = st.columns(7)
    zile_sapt = ["Lu", "Ma", "Mi", "Jo", "Vi", "Sâ", "Du"]
    for i, z in enumerate(zile_sapt): cols[i].markdown(f"**{z}**")
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                curr_date = date(an, luna, day)
                # Numărăm câte camere sunt ocupate în această zi
                ocupate = df[(df['checkin_d'] <= curr_date) & (df['checkout_d'] > curr_date)]
                nr_cam = len(ocupate['camera'].unique())
                
                bg = "#e8f8f5" # Verde pal (liber)
                txt = "#27ae60"
                if nr_cam >= 6: bg, txt = "#fadbd8", "#c0392b" # Roșu (plin)
                elif nr_cam > 0: bg, txt = "#fdebd0", "#d35400" # Portocaliu (parțial)
                
                cols[i].markdown(f"""
                <div style="background:{bg}; padding:10px; border-radius:8px; text-align:center; border:1px solid {txt};">
                    <span style="font-size:18px; font-weight:bold; color:{txt}">{day}</span><br>
                    <span style="font-size:12px;">{nr_cam}/6 Oc.</span>
                </div>
                """, unsafe_allow_html=True)

# --- 8. PAGINA: STATISTICI ---
elif choice == "📊 Statistici":
    st.title("📊 Statistici Financiare")
    df = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    if not df.empty:
        df['luna'] = pd.to_datetime(df['checkin']).dt.month_name()
        
        c1, c2 = st.columns(2)
        c1.metric("Venituri Totale", f"{df['pret_total'].sum():,.0f} RON")
        c2.metric("Rezervări Totale", len(df))
        
        st.subheader("Venituri Lunare")
        st.bar_chart(df.groupby('luna')['pret_total'].sum())
    else:
        st.info("Nu există date.")

# --- 9. PAGINA: LISTĂ ---
elif choice == "📋 Listă Rezervări":
    st.title("📋 Registru Rezervări")
    df = pd.read_sql_query("SELECT id, nume, telefon, camera, checkin, checkout, pret_total FROM rezervari ORDER BY checkin DESC", conn)
    st.dataframe(df, use_container_width=True)
