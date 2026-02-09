import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import urllib.parse

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Pensiune Manager Pro", layout="wide", initial_sidebar_state="collapsed")

# --- STYLING CSS PENTRU LOOK PREMIUM ---
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .calendar-box {
        display: inline-block;
        width: 100%;
        padding: 10px 0;
        text-align: center;
        border-radius: 5px;
        font-weight: bold;
        font-size: 12px;
        color: #fff;
    }
    .status-liber { background-color: #2ECC71; }
    .status-ocupat { background-color: #E74C3C; }
    .status-schimb { background-color: #F1C40F; color: #000; }
    .status-sosire { background-color: #3498DB; }
    .status-plecare { background-color: #9B59B6; }
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

# --- LOGICĂ ---
def este_disponibila(camera, start, end):
    query = "SELECT * FROM rezervari WHERE camera = ? AND status != 'Anulat' AND NOT (checkout <= ? OR checkin >= ?)"
    c.execute(query, (camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')))
    return len(c.fetchall()) == 0

# --- SIDEBAR NAV ---
st.sidebar.title("🏨 Pensiunea Mea")
menu = ["📅 Harta Disponibilității", "➕ Rezervare Nouă", "👥 Rezervare Grup", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Navigare", menu)

# --- 1. HARTA DISPONIBILITĂȚII (HEATMAP) ---
if choice == "📅 Harta Disponibilității":
    st.title("Harta Disponibilității")
    
    col_date, col_stat = st.columns([1, 2])
    data_start = col_date.date_input("Vezi de la data:", date.today())
    
    # Generăm 14 zile
    zile = [data_start + timedelta(days=i) for i in range(14)]
    
    # Header zile
    header_cols = st.columns([1.5] + [1]*14)
    header_cols[0].write("**Cameră**")
    for i, d in enumerate(zile):
        header_cols[i+1].write(f"**{d.strftime('%d/%m')}**")

    # Date rezervări
    df_rez = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    df_rez['checkin'] = pd.to_datetime(df_rez['checkin']).dt.date
    df_rez['checkout'] = pd.to_datetime(df_rez['checkout']).dt.date

    for cam in CAMERE_INFO.keys():
        row_cols = st.columns([1.5] + [1]*14)
        row_cols[0].markdown(f"**{cam}**")
        
        for i, d in enumerate(zile):
            plecare = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkout'] == d)].empty
            sosire = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin'] == d)].empty
            ocupat = not df_rez[(df_rez['camera'] == cam) & (df_rez['checkin'] < d) & (df_rez['checkout'] > d)].empty
            
            if plecare and sosire: label, clasa = "🔄", "status-schimb"
            elif plecare: label, clasa = "📤", "status-plecare"
            elif sosire: label, clasa = "📥", "status-sosire"
            elif ocupat: label, clasa = "🔴", "status-ocupat"
            else: label, clasa = "🟢", "status-liber"
            
            row_cols[i+1].markdown(f'<div class="calendar-box {clasa}">{label}</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("Legenda: 🟢 Liber | 🔴 Ocupat | 🔄 Schimb (In/Out) | 📥 Sosire | 📤 Plecare")

# --- 2. REZERVARE NOUĂ ---
elif choice in ["➕ Rezervare Nouă", "👥 Rezervare Grup"]:
    st.title(choice)
    is_grup = "Grup" in choice
    
    with st.expander("📝 Formular Rezervare", expanded=True):
        with st.form("my_form"):
            nume = st.text_input("👤 Nume Client")
            telefon = st.text_input("📱 Telefon (ex: 40722123456)")
            cam_sel = "Toate" if is_grup else st.selectbox("🛏️ Camera", list(CAMERE_INFO.keys()))
            
            c1, c2 = st.columns(2)
            d_in = c1.date_input("📥 Data Check-in", date.today())
            d_out = c2.date_input("📤 Data Check-out", date.today() + timedelta(days=1))
            
            pret_sugerat = sum(CAMERE_INFO.values()) if is_grup else CAMERE_INFO[cam_sel]
            pret_final = st.number_input("💰 Preț Total (RON)", value=float(pret_sugerat))
            
            status = st.selectbox("Status", ["Confirmat", "În așteptare", "Anulat"])
            note = st.text_area("📝 Note (Preferințe, avans, etc.)")
            
            submit = st.form_submit_button("✅ SALVEAZĂ REZERVAREA")
            
            if submit:
                t_in = datetime.combine(d_in, datetime.strptime("15:00", "%H:%M").time())
                t_out = datetime.combine(d_out, datetime.strptime("11:00", "%H:%M").time())
                
                camere_vizate = list(CAMERE_INFO.keys()) if is_grup else [cam_sel]
                conflict = [c for c in camere_vizate if not este_disponibila(c, t_in, t_out)]
                
                if conflict:
                    st.error(f"❌ Camere ocupate: {', '.join(conflict)}")
                else:
                    for cam_name in camere_vizate:
                        p_unit = pret_final / 6 if is_grup else pret_final
                        c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)",
                                  (nume, telefon, cam_name, t_in, t_out, status, p_unit, note))
                    conn.commit()
                    st.balloons()
                    st.success(f"Rezervare salvată pentru {nume}!")
                    
                    # Buton WhatsApp
                    mesaj = f"Salut {nume}! Confirmăm rezervarea ({d_in} - {d_out}). Te așteptăm!"
                    url_wa = f"https://api.whatsapp.com/send?phone={telefon}&text={urllib.parse.quote(mesaj)}"
                    st.markdown(f'[📱 Trimite Confirmare WhatsApp]({url_wa})')

# --- 3. LISTA REZERVĂRI (CARDURI) ---
elif choice == "📋 Listă Rezervări":
    st.title("Listă Rezervări")
    df = pd.read_sql_query("SELECT * FROM rezervari ORDER BY checkin DESC", conn)
    
    for i, r in df.iterrows():
        color = "#2ECC71" if r['status'] == "Confirmat" else "#F1C40F"
        if r['status'] == "Anulat": color = "#E74C3C"
        
        with st.container():
            st.markdown(f"""
                <div style="background-color: white; padding: 15px; border-radius: 10px; border-left: 8px solid {color}; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="margin:0;">{r['camera']} - {r['nume']}</h3>
                    <p style="margin:5px 0;">📅 {r['checkin'][5:16]} | 💰 {r['pret_total']} RON</p>
                    <p style="margin:0; font-size: 14px; color: #666;">📝 {r['note'] if r['note'] else '-'}</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"Șterge ID {r['id']}", key=f"del_{r['id']}"):
                c.execute("DELETE FROM rezervari WHERE id = ?", (r['id'],))
                conn.commit()
                st.rerun()
