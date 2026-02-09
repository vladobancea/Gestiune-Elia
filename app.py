import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import urllib.parse
import calendar

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Pensiune Manager Pro", layout="wide")

# --- STYLING CSS ---
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

# Patch bază de date
try:
    c.execute("ALTER TABLE rezervari ADD COLUMN note TEXT")
    conn.commit()
except:
    pass

CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

# --- FUNCTII ---
def este_disponibila(camera, start, end):
    query = "SELECT * FROM rezervari WHERE status != 'Anulat' AND camera = ? AND NOT (checkout <= ? OR checkin >= ?)"
    c.execute(query, (camera, start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')))
    return len(c.fetchall()) == 0

# --- MENIU SIDEBAR ---
st.sidebar.title("🏨 Manager Pensiune")
menu = ["📅 Harta Disponibilității", "📊 Statistici & Rapoarte", "➕ Rezervare Nouă", "👥 Rezervare Grup", "📋 Listă Rezervări"]
choice = st.sidebar.radio("Navigare", menu)

# --- 1. HARTA DISPONIBILITĂȚII ---
if choice == "📅 Harta Disponibilității":
    st.title("Harta Disponibilității")
    data_start = st.date_input("Vezi de la data:", date.today())
    zile = [data_start + timedelta(days=i) for i in range(14)]
    
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

# --- 2. STATISTICI & RAPOARTE ---
elif choice == "📊 Statistici & Rapoarte":
    st.title("Statistici Performanță")
    df = pd.read_sql_query("SELECT * FROM rezervari WHERE status != 'Anulat'", conn)
    
    if not df.empty:
        df['checkin'] = pd.to_datetime(df['checkin'])
        df['checkout'] = pd.to_datetime(df['checkout'])
        df['luna'] = df['checkin'].dt.month
        df['an'] = df['checkin'].dt.year
        df['nopti'] = (df['checkout'] - df['checkin']).dt.days

        an_selectat = st.selectbox("Alege Anul", sorted(df['an'].unique(), reverse=True))
        df_an = df[df['an'] == an_selectat]

        # KPI-uri Anuale
        venit_anual = df_an['pret_total'].sum()
        nopti_totale = df_an['nopti'].sum()
        zile_an = 366 if calendar.isleap(an_selectat) else 365
        grad_anual = (nopti_totale / (6 * zile_an)) * 100

        c1, c2 = st.columns(2)
        c1.metric(f"Venituri Totale {an_selectat}", f"{venit_anual:,.0f} RON")
        c2.metric("Grad Ocupare Mediu", f"{grad_anual:.1f}%")

        # Detaliere pe Luni
        st.subheader("Evoluție Lunară")
        raport_lunar = df_an.groupby('luna').agg({'pret_total': 'sum', 'nopti': 'sum'}).reset_index()
        
        def calc_grad(row):
            z_luna = calendar.monthrange(an_selectat, int(row['luna']))[1]
            return (row['nopti'] / (6 * z_luna)) * 100

        raport_lunar['Grad Ocupare (%)'] = raport_lunar.apply(calc_grad, axis=1)
        raport_lunar['Luna'] = raport_lunar['luna'].apply(lambda x: calendar.month_name[x])
        
        st.bar_chart(data=raport_lunar, x='Luna', y='pret_total')
        st.table(raport_lunar[['Luna', 'pret_total', 'Grad Ocupare (%)']].rename(columns={'pret_total': 'Venit (RON)'}))
    else:
        st.info("Nu există date pentru statistici.")

# --- 3. REZERVARE NOUA ---
elif choice in ["➕ Rezervare Nouă", "👥 Rezervare Grup"]:
    st.title(choice)
    is_grup = "Grup" in choice
    with st.form("form_add"):
        nume = st.text_input("Nume Client")
        telefon = st.text_input("Telefon")
        cam_sel = "Toate" if is_grup else st.selectbox("Cameră", list(CAMERE_INFO.keys()))
        c1, c2 = st.columns(2)
        d_in = c1.date_input("Check-in", date.today())
        d_out = c2.date_input("Check-out", date.today() + timedelta(days=1))
        pret_final = st.number_input("Preț Total (RON)", value=float(sum(CAMERE_INFO.values()) if is_grup else CAMERE_INFO[cam_sel]))
        status = st.selectbox("Status", ["Confirmat", "În așteptare", "Anulat"])
        note = st.text_area("Note")
        
        if st.form_submit_button("Salvează"):
            t_in = datetime.combine(d_in, datetime.strptime("15:00", "%H:%M").time())
            t_out = datetime.combine(d_out, datetime.strptime("11:00", "%H:%M").time())
            camere_vizate = list(CAMERE_INFO.keys()) if is_grup else [cam_sel]
            
            if all(este_disponibila(c_n, t_in, t_out) for c_n in camere_vizate):
                for cv in camere_vizate:
                    p_u = pret_final/6 if is_grup else pret_final
                    c.execute("INSERT INTO rezervari (nume, telefon, camera, checkin, checkout, status, pret_total, note) VALUES (?,?,?,?,?,?,?,?)",
                              (nume, telefon, cv, t_in, t_out, status, p_u, note))
                conn.commit()
                st.balloons()
                st.rerun()
            else:
                st.error("Conflict de disponibilitate!")

# --- 4. LISTA REZERVARI ---
elif choice == "📋 Listă Rezervări":
    st.title("Listă Rezervări")
    df_list = pd.read_sql_query("SELECT * FROM rezervari ORDER BY checkin DESC", conn)
    for i, r in df_list.iterrows():
        with st.container():
            st.markdown(f"""<div style='background:white; padding:15px; border-radius:10px; border-left:8px solid #3498DB; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                <h3 style='margin:0;'>{r['camera']} - {r['nume']}</h3>
                <p style='margin:5px 0;'>📅 {str(r['checkin'])[:16]} → {str(r['checkout'])[:16]}</p>
                <p style='margin:0;'>💰 {r['pret_total']} RON | 📱 {r['telefon']}</p>
                <p style='margin:5px 0; font-size: 14px; color: #666;'>📝 {r['note'] if r['note'] else '-'}</p>
                </div>""", unsafe_allow_html=True)
            if st.button(f"Șterge ID {r['id']}", key=f"del_{r['id']}"):
                c.execute("DELETE FROM rezervari WHERE id=?", (r['id'],))
                conn.commit()
                st.rerun()
