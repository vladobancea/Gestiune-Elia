import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time
import urllib.parse
import calendar
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import base64
import os

# ==========================================
# 1. CONFIGURARE PAGINĂ & DESIGN 2026
# ==========================================
st.set_page_config(
    page_title="Elia PMS", 
    page_icon="🏔️", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- FUNCȚIE PENTRU IMAGINE DE FUNDAL (LOCALĂ) ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_bg_hack(main_bg):
    '''
    O funcție care setează o imagine locală ca fundal
    '''
    try:
        bin_str = get_base64_of_bin_file(main_bg)
        page_bg_img = '''
        <style>
        .stApp {
            background-image: linear-gradient(rgba(255, 255, 255, 0.4), rgba(255, 255, 255, 0.6)), url("data:image/jpg;base64,%s");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        </style>
        ''' % bin_str
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except FileNotFoundError:
        # Fallback dacă nu găsește poza
        pass

# Setăm imaginea de fundal (Bucegi)
# Asigură-te că fișierul este lângă app.py
if os.path.exists("Bucegi National Park 2.jpg"):
    set_bg_hack("Bucegi National Park 2.jpg")

# --- CSS MODERN (THEME 2026 - Ajustat pentru fundal) ---
st.markdown("""
    <style>
    /* IMPORT FONT MODERN */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;700&display=swap');

    /* RESET GENERAL */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        color: #1f2937;
    }

    /* LOGO STYLING */
    [data-testid="stSidebar"] img {
        margin-top: 20px;
        margin-bottom: 20px;
        transition: transform 0.3s ease;
        background: rgba(255, 255, 255, 0.1); /* Ușor fundal sub logo dacă e transparent */
        padding: 10px;
        border-radius: 10px;
    }
    [data-testid="stSidebar"] img:hover {
        transform: scale(1.05);
    }

    /* SIDEBAR (Gradient Întunecat - Semi-transparent pentru modernitate) */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.98) 100%);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    
    /* TITLURI */
    h1, h2, h3 {
        font-weight: 700 !important;
        background: -webkit-linear-gradient(45deg, #2563eb, #7c3aed); /* Albastru mai puternic pentru contrast */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 10px;
        text-shadow: 0px 2px 4px rgba(255,255,255,0.5);
    }

    /* CARDURI INFORMATIVE (Glassmorphism Puternic) */
    /* Fundal alb mai opac pentru a se citi textul peste poza de fundal */
    .info-card {
        background: rgba(255, 255, 255, 0.85); 
        backdrop-filter: blur(15px);
        padding: 25px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.6);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .info-card:hover {
        transform: scale(1.01);
    }

    /* TABEL HARTA */
    .scroll-container { 
        overflow-x: auto; 
        padding-bottom: 20px; 
        border-radius: 15px;
        background: rgba(255, 255, 255, 0.9); /* Aproape opac */
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        backdrop-filter: blur(8px);
        padding: 10px;
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    .custom-table { width: 100%; border-collapse: separate; border-spacing: 0; min-width: 1000px; table-layout: fixed; }
    
    /* Header Tabel */
    .custom-table th { 
        background: rgba(248, 250, 252, 0.95); 
        color: #475569; 
        font-size: 12px; 
        text-transform: uppercase; 
        letter-spacing: 1px;
        padding: 15px; 
        border-bottom: 2px solid #e2e8f0;
        position: sticky; top: 0; z-index: 5; 
    }
    
    /* Celule */
    .custom-table td { 
        border-bottom: 1px solid #f1f5f9; 
        padding: 0 !important; 
        height: 60px; 
        vertical-align: middle; 
    }
    
    /* Sticky Column */
    .sticky-col { 
        position: sticky; left: 0; 
        background: rgba(255, 255, 255, 0.95); 
        z-index: 10; 
        font-weight: 600; 
        color: #1e293b;
        border-right: 2px solid #f1f5f9 !important; 
        width: 140px; 
        box-shadow: 4px 0 5px -2px rgba(0,0,0,0.05);
        padding-left: 15px !important;
    }

    /* BANDA CALENDAR */
    .calendar-box { 
        height: 40px; width: 100%; display: flex; align-items: center; justify-content: center; 
        font-size: 12px; font-weight: 700; color: white; border-radius: 0; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-shadow: 1px 1px 2px rgba(0,0,0,0.4);
    }

    /* INPUT-URI MODERNE */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 12px !important;
        background-color: rgba(255, 255, 255, 0.9) !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    }

    /* CULORI STATUS */
    .bg-liber { background: rgba(0,0,0,0.05); border-radius: 8px; height: 30px; width: 30px; margin: auto; border: 1px dashed #cbd5e1; }
    .bg-ocupat { background: #ef4444; width: 100.5%; }
    .bg-checkin { background: linear-gradient(90deg, rgba(255,255,255,0) 0%, #10b981 15%, #ef4444 85%); width: 100.5%; border-radius: 10px 0 0 10px; }
    .bg-checkout { background: linear-gradient(90deg, #ef4444 15%, #10b981 85%, rgba(255,255,255,0) 100%); width: 100.5%; border-radius: 0 10px 10px 0; }
    .bg-schimb { background: linear-gradient(90deg, #ef4444 45%, #ffffff 50%, #10b981 50%, #ef4444 55%); width: 100.5%; color: #111; }

    /* CARD CALENDAR LUNAR */
    .month-day-card {
        border-radius: 12px; padding: 12px; text-align: center; transition: all 0.2s; height: 80px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        background: rgba(255,255,255,0.95);
    }
    .month-day-card:hover { transform: translateY(-3px); box-shadow: 0 8px 16px rgba(0,0,0,0.2); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONEXIUNE & LOGICĂ
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

CAMERE_INFO = {
    "Camera 1": 200, "Camera 2": 200, 
    "Camera 3": 250, "Camera 4": 250, 
    "Camera 5": 300, "Camera 6": 350
}

def get_data():
    try:
        df = conn.read(worksheet="Rezervari", ttl=0)
        required_cols = ['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note']
        if df.empty or not all(col in df.columns for col in required_cols): return pd.DataFrame(columns=required_cols)
        df['checkin'] = pd.to_datetime(df['checkin'], errors='coerce')
        df['checkout'] = pd.to_datetime(df['checkout'], errors='coerce')
        df = df.dropna(subset=['checkin', 'checkout'])
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df['pret_total'] = pd.to_numeric(df['pret_total'], errors='coerce').fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Eroare date: {e}"); return pd.DataFrame(columns=['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note'])

def update_data(df):
    try:
        df_s = df.copy()
        df_s['checkin'] = df_s['checkin'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_s['checkout'] = df_s['checkout'].dt.strftime('%Y-%m-%d %H:%M:%S')
        conn.update(worksheet="Rezervari", data=df_s)
    except Exception as e: st.error(f"Err: {e}")

def este_disponibila(df, camera, start, end, exclude_id=None):
    if df.empty: return True
    mask = (df['status'] != 'Anulat') & (df['camera'] == camera)
    conflict = mask & ~( (df['checkout'] <= start) | (df['checkin'] >= end) )
    if exclude_id: conflict = conflict & (df['id'] != exclude_id)
    return df[conflict].empty

def genereaza_pdf(r):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "CONFIRMARE", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Client: {r['nume']}", ln=True); pdf.cell(0, 10, f"Tel: {r['telefon']}", ln=True)
    pdf.cell(0, 10, f"Camera: {r['camera']}", ln=True); pdf.cell(0, 10, f"Total: {r['pret_total']} RON", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. SIDEBAR (LOGO & MENIU)
# ==========================================

# LOGO PROPRIU
# Asigură-te că fișierul "LOGO final.png" este în folderul principal
if os.path.exists("LOGO final.png"):
    st.sidebar.image("LOGO final.png", use_container_width=True)
else:
    st.sidebar.warning("Logo lipsă. Încarcă 'LOGO final.png'")

st.sidebar.markdown("### 🏔️ Elia Management")

if st.sidebar.button("✨ Rezervare Nouă", use_container_width=True, type="primary"):
    st.session_state['show_add_modal'] = True

menu = {
    "📅 Harta": "Harta",
    "🗓️ Calendar": "Calendar Lunar",
    "📊 Statistici": "Statistici", 
    "📋 Registru": "Listă Rezervări"
}
choice = st.sidebar.radio("Navigare", list(menu.keys()), format_func=lambda x: x)
sel_page = menu[choice]
df_master = get_data()

# ==========================================
# 4. MODAL ADAUGARE (Clean UI)
# ==========================================
if st.session_state.get('show_add_modal', False):
    st.markdown("---")
    with st.container():
        st.markdown("<div class='info-card'><h3>✨ Adaugă Rezervare Rapidă</h3>", unsafe_allow_html=True)
        with st.form("quick_add"):
            c1, c2 = st.columns(2)
            nume = c1.text_input("Nume Client", placeholder="ex: Popescu Ion")
            tel = c2.text_input("Telefon", placeholder="07xx...")
            cam = c1.selectbox("Cameră", list(CAMERE_INFO.keys()) + ["Toate (Grup)"])
            c3, c4 = st.columns(2)
            d1 = c3.date_input("Check-in", date.today())
            d2 = c4.date_input("Check-out", date.today() + timedelta(1))
            
            pret_def = sum(CAMERE_INFO.values()) if "Grup" in cam else CAMERE_INFO.get(cam, 0)
            pret = st.number_input("Preț Total (RON)", value=float(pret_def))
            note = st.text_area("Note Speciale", placeholder="ex: pat suplimentar...")
            
            b1, b2 = st.columns([1, 4])
            if b1.form_submit_button("🚀 Salvează"):
                t1, t2 = datetime.combine(d1, time(15, 0)), datetime.combine(d2, time(11, 0))
                camere_target = list(CAMERE_INFO.keys()) if "Grup" in cam else [cam]
                if all(este_disponibila(df_master, c, t1, t2) for c in camere_target):
                    new_rows = []
                    max_id = df_master['id'].max() if not df_master.empty else 0
                    for i, c_name in enumerate(camere_target):
                        p_part = pret / 6 if "Grup" in cam else pret
                        new_rows.append({"id": int(max_id + 1 + i), "nume": nume, "telefon": tel, "camera": c_name, "checkin": t1, "checkout": t2, "status": "Confirmat", "pret_total": p_part, "note": note})
                    updated_df = pd.concat([df_master, pd.DataFrame(new_rows)], ignore_index=True)
                    update_data(updated_df)
                    st.session_state['show_add_modal'] = False; st.toast("✅ Rezervare Salvată!", icon="🎉"); st.rerun()
                else: st.error("⚠️ Conflict! Camera este ocupată.")
            if b2.form_submit_button("❌ Anulează"):
                st.session_state['show_add_modal'] = False; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 5. HARTA (Dashboard Look)
# ==========================================
if sel_page == "Harta":
    # Header Vizual
    st.markdown("""
    <div style="background: rgba(255,255,255,0.85); backdrop-filter: blur(10px); padding: 20px; border-radius: 15px; border-left: 6px solid #7c3aed; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h1 style="margin:0; padding:0; background:none; -webkit-text-fill-color: #1f2937;">🗺️ Disponibilitate Camere</h1>
        <p style="margin:0; color: #4b5563;">Status în timp real pentru Pensiunea Elia</p>
    </div>
    """, unsafe_allow_html=True)

    c_date, c_filtru = st.columns([1, 3])
    d_start = c_date.date_input("Vezi începând cu:", date.today())
    
    zile = [d_start + timedelta(days=i) for i in range(14)]
    d_end_view = zile[-1]
    
    if not df_master.empty:
        df_view = df_master[df_master['status'] != 'Anulat'].copy()
        df_view['checkin_d'] = df_view['checkin'].dt.date
        df_view['checkout_d'] = df_view['checkout'].dt.date
    else: df_view = pd.DataFrame(columns=df_master.columns)

    html = '<div class="scroll-container"><table class="custom-table"><thead><tr><th class="sticky-col">Cameră</th>'
    for d in zile: html += f'<th>{d.strftime("%d")}<br><small>{d.strftime("%b")}</small></th>'
    html += '</tr></thead><tbody>'

    for cam in CAMERE_INFO.keys():
        html += f'<tr><td class="sticky-col">{cam}</td>'
        for d in zile:
            if df_view.empty: html += f'<td><div class="bg-liber"></div></td>'; continue
            
            r_out = df_view[(df_view['camera'] == cam) & (df_view['checkout_d'] == d)]
            r_in = df_view[(df_view['camera'] == cam) & (df_view['checkin_d'] == d)]
            r_stay = df_view[(df_view['camera'] == cam) & (df_view['checkin_d'] < d) & (df_view['checkout_d'] > d)]
            
            bg, label = "bg-liber", "" 
            
            if not r_out.empty and not r_in.empty:
                bg, label = "bg-schimb", f"{int(r_out.iloc[0]['id'])} ⟷ {int(r_in.iloc[0]['id'])}"
            elif not r_out.empty:
                bg = "bg-checkout"; r = r_out.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1: label = str(int(r['id']))
                else: 
                     v_s, v_e = max(r['checkin_d'], d_start), min(r['checkout_d'], d_end_view)
                     if d == v_s + timedelta(days=(v_e - v_s).days // 2): label = str(int(r['id']))
            elif not r_in.empty:
                bg = "bg-checkin"; r = r_in.iloc[0]
                if (r['checkout_d'] - r['checkin_d']).days <= 1: label = str(int(r['id']))
                else:
                     v_s, v_e = max(r['checkin_d'], d_start), min(r['checkout_d'], d_end_view)
                     if d == v_s + timedelta(days=(v_e - v_s).days // 2): label = str(int(r['id']))
            elif not r_stay.empty:
                bg = "bg-ocupat"; r = r_stay.iloc[0]
                v_s, v_e = max(r['checkin_d'], d_start), min(r['checkout_d'], d_end_view)
                if d == v_s + timedelta(days=(v_e - v_s).days // 2): label = str(int(r['id']))
            
            if bg == "bg-liber": html += f'<td><div class="{bg}"></div></td>'
            else: html += f'<td><div class="calendar-box {bg}">{label}</div></td>'
        html += '</tr>'
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

    if not df_view.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        active_ids = sorted(df_view['id'].unique().tolist())
        id_sel = st.selectbox("🛠️ Administrează Rezervare (Selectează ID):", ["-"] + [str(i) for i in active_ids])
        
        if id_sel != "-":
            try:
                r_idx = df_master[df_master['id'] == int(id_sel)].index[0]; r = df_master.iloc[r_idx]
                st.markdown(f"""
                <div class="info-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h2 style="margin:0; background:none; -webkit-text-fill-color: #1f2937;">👤 {r['nume']}</h2>
                        <span style="background:#7c3aed; color:white; padding:5px 10px; border-radius:10px; font-weight:bold;">ID: {id_sel}</span>
                    </div>
                    <p style="color:#6b7280; margin-top:5px;">🛏️ {r['camera']} &nbsp; | &nbsp; 📅 {r['checkin'].strftime('%d %b')} - {r['checkout'].strftime('%d %b')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                n_tel = c1.text_input("Telefon", r['telefon'])
                n_pret = c2.number_input("Preț", value=float(r['pret_total']))
                n_note = c3.text_area("Note", r['note'] if pd.notna(r['note']) else "")
                
                b1, b2, b3, b4 = st.columns(4)
                if b1.button("💾 Actualizează"):
                    df_master.at[r_idx, 'telefon'] = n_tel; df_master.at[r_idx, 'pret_total'] = n_pret; df_master.at[r_idx, 'note'] = n_note
                    update_data(df_master); st.toast("Actualizat!"); st.rerun()
                
                b2.download_button("📄 PDF Confirmare", genereaza_pdf(r), f"Rez_{id_sel}.pdf")
                
                wa = urllib.parse.quote(f"Salut {r['nume']}, te așteptăm la Elia!")
                b3.markdown(f'<a href="https://api.whatsapp.com/send?phone={n_tel}&text={wa}" target="_blank"><button style="width:100%;background:#10b981;color:white;border:none;padding:10px;border-radius:12px;font-weight:bold;cursor:pointer;box-shadow: 0 4px 6px rgba(0,0,0,0.1);">💬 WhatsApp</button></a>', unsafe_allow_html=True)
                
                if b4.button("🗑️ Șterge", type="primary"):
                    df_master = df_master[df_master['id'] != int(id_sel)]; update_data(df_master); st.toast("Șters!"); st.rerun()
            except: pass

# ==========================================
# 6. CALENDAR LUNAR (Grid Modern)
# ==========================================
elif sel_page == "Calendar Lunar":
    st.markdown("""
    <div style="background: rgba(255,255,255,0.85); backdrop-filter: blur(10px); padding: 20px; border-radius: 15px; border-left: 6px solid #2563eb; margin-bottom: 20px;">
        <h1 style="margin:0; padding:0; background:none; -webkit-text-fill-color: #1f2937;">🗓️ Calendar General</h1>
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.columns([1,3]); an = c1.selectbox("An", [2024, 2025, 2026], index=1); luna = c2.selectbox("Luna", list(range(1, 13)), index=datetime.now().month-1)
    
    cal = calendar.monthcalendar(an, luna)
    cols = st.columns(7)
    for i, z in enumerate(["Lu", "Ma", "Mi", "Jo", "Vi", "Sâ", "Du"]):
        cols[i].markdown(f"<div style='text-align:center; color:#1e293b; font-weight:bold; margin-bottom:10px; background:rgba(255,255,255,0.8); padding:5px; border-radius:5px;'>{z}</div>", unsafe_allow_html=True)
    
    df_act = df_master[df_master['status'] != 'Anulat'].copy() if not df_master.empty else pd.DataFrame()
    if not df_act.empty:
        df_act['checkin_n'] = df_act['checkin'].dt.normalize(); df_act['checkout_n'] = df_act['checkout'].dt.normalize()

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0: cols[i].write(""); continue
            curr = pd.Timestamp(year=an, month=luna, day=day)
            nr = 0
            if not df_act.empty:
                nr = len(df_act[(df_act['checkin_n'] <= curr) & (df_act['checkout_n'] > curr)]['camera'].unique())
            
            bg = "rgba(255,255,255,0.9)"; border = "#e2e8f0"; txt = "#1e293b"
            if nr >= 6: bg = "#fee2e2"; border = "#ef4444"; txt = "#991b1b"
            elif nr > 0: bg = "#ffedd5"; border = "#f97316"; txt = "#9a3412"
            else: bg = "#ecfdf5"; border = "#10b981"; txt = "#065f46"
            
            cols[i].markdown(f"""
            <div class="month-day-card" style="background:{bg}; border:1px solid {border};">
                <span style="font-size:20px; font-weight:800; color:{txt}">{day}</span>
                <span style="font-size:12px; color:{txt}; opacity:0.8;">{nr}/6 Cam</span>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 7. STATISTICI & LISTA (Cards)
# ==========================================
elif sel_page == "Statistici":
    st.markdown("""
    <div style="background: rgba(255,255,255,0.85); backdrop-filter: blur(10px); padding: 20px; border-radius: 15px; border-left: 6px solid #10b981; margin-bottom: 20px;">
        <h1 style="margin:0; padding:0; background:none; -webkit-text-fill-color: #1f2937;">📊 Rapoarte Financiare</h1>
    </div>
    """, unsafe_allow_html=True)
    
    if not df_master.empty:
        df_a = df_master[df_master['status'] != 'Anulat'].copy()
        df_a['luna'] = df_a['checkin'].dt.strftime('%B')
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='info-card'><h3 style='margin:0; background:none; -webkit-text-fill-color: #059669;'>💰 {df_a['pret_total'].sum():,.0f} RON</h3><p>Total Încasări</p></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='info-card'><h3 style='margin:0; background:none; -webkit-text-fill-color: #2563eb;'>🔖 {len(df_a)}</h3><p>Rezervări Totale</p></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='info-card'><h3 style='margin:0; background:none; -webkit-text-fill-color: #7c3aed;'>📈 {df_a['pret_total'].mean():,.0f} RON</h3><p>Medie / Sejur</p></div>", unsafe_allow_html=True)
        
        st.subheader("Evoluție Lunară")
        st.bar_chart(df_a.groupby('luna')['pret_total'].sum())
    else: st.info("Nu există date.")

elif sel_page == "Listă Rezervări":
    st.markdown("""
    <div style="background: rgba(255,255,255,0.85); backdrop-filter: blur(10px); padding: 20px; border-radius: 15px; border-left: 6px solid #f59e0b; margin-bottom: 20px;">
        <h1 style="margin:0; padding:0; background:none; -webkit-text-fill-color: #1f2937;">📋 Registru Digital</h1>
    </div>
    """, unsafe_allow_html=True)
    if not df_master.empty:
        st.dataframe(df_master[['id', 'nume', 'telefon', 'camera', 'checkin', 'checkout', 'pret_total', 'note']].sort_values(by='checkin', ascending=False), use_container_width=True)
    else: st.info("Baza de date este goală.")
