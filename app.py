import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time
import urllib.parse
import calendar
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import base64
import os
import io
from pypdf import PdfWriter, PdfReader
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ==========================================
# 1. CONFIGURARE PAGINĂ
# ==========================================
st.set_page_config(
    page_title="Elia PMS", 
    page_icon="🏔️", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- CONFIGURARE CULORI CAMERE (PASTEL) ---
ROOM_COLORS = {
    "Camera 1": "#AEC6CF", # Pastel Blue
    "Camera 2": "#77DD77", # Pastel Green
    "Camera 3": "#F49AC2", # Pastel Pink
    "Camera 4": "#FDFD96", # Pastel Yellow
    "Camera 5": "#B39EB5", # Pastel Purple
    "Camera 6": "#FFB347"  # Pastel Orange
}
DEFAULT_COLOR = "#cccccc"

# --- TEXT REGULAMENT ---
REGULAMENT_TEXT = """
REGULAMENT INTERN SI BUNA CONVIETUIRE
Va multumim ca ati ales Pensiunea Elia! Pentru a va asigura un sejur relaxant, va rugam sa parcurgeti urmatoarele reguli de bun simt:

Check-in / Out - Accesul in camere se face dupa ora 16:00, iar eliberarea acestora se face pana la ora 11:00.
Ore de liniste - Va rugam sa respectati linistea intre orele 23:00 si 07:00. Petrecerile zgomotoase nu sunt permise in interiorul pensiunii.
Semineul - Din motive de siguranta, semineul se aprinde exclusiv de catre personalul pensiunii, la cerere.
Caldura - Temperatura se regleaza individual din termostatul fiecarei camere. Va rugam sa nu fortati setarile sau robinetii caloriferelor.
Fumatul - Fumatul este strict interzis in interior. Va rugam sa folositi scrumierele din spatiile exterioare.
Grija si respect - Va rugam sa folositi papuci de casa si sa pastrati integritatea obiectelor din dotare.
"""

# --- FUNCȚIE CURĂȚARE TEXT ---
def clean_text(text):
    if not isinstance(text, str): return str(text)
    replacements = {
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
        'Ă': 'A', 'Â': 'A', 'Î': 'I', 'Ș': 'S', 'Ț': 'T',
        'ş': 's', 'ţ': 't', 'Ş': 'S', 'Ţ': 'T', '„': '"', '”': '"'
    }
    for k, v in replacements.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- CACHE & BACKGROUND ---
@st.cache_resource
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f: data = f.read()
    return base64.b64encode(data).decode()

def set_bg_hack(main_bg):
    try:
        bin_str = get_base64_of_bin_file(main_bg)
        st.markdown(f'''<style>.stApp {{background-image: linear-gradient(rgba(255,255,255,0.85), rgba(255,255,255,0.95)), url("data:image/jpg;base64,{bin_str}"); background-size: cover; background-attachment: fixed;}}</style>''', unsafe_allow_html=True)
    except: pass

if os.path.exists("Bucegi National Park 2.jpg"): set_bg_hack("Bucegi National Park 2.jpg")

# --- CSS MODERN ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; color: #1f2937; }

    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e5e7eb; }
    [data-testid="stSidebar"] * { color: #1f2937 !important; }
    
    .info-card { background: rgba(255, 255, 255, 0.95); padding: 20px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #f1f5f9; }

    /* TABEL RAPID HTML */
    .scroll-container { overflow-x: auto; padding-bottom: 10px; background: rgba(255, 255, 255, 0.9); border-radius: 15px; }
    .custom-table { width: 100%; border-collapse: separate; border-spacing: 0; min-width: 1200px; } 
    .custom-table th { background: #f8fafc; color: #475569; padding: 5px; border-bottom: 2px solid #e2e8f0; font-size: 11px; text-transform: uppercase; text-align: center; }
    .custom-table td { border-bottom: 1px solid #f1f5f9; height: 45px; vertical-align: middle; padding: 0 !important; }
    .first-col { background: #ffffff; font-weight: 600; color: #1e293b; width: 90px; padding-left: 5px !important; position: sticky; left: 0; z-index: 10; border-right: 1px solid #eee; }

    .calendar-box { height: 35px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: #333; text-shadow: 0px 0px 1px rgba(255,255,255,0.8); }
    .bg-liber { background: #f8fafc; border-radius: 50%; height: 6px; width: 6px; margin: auto; opacity: 0.5; }

    .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; margin-top: 10px; }
    .cal-day-header { text-align: center; font-weight: bold; font-size: 12px; color: #64748b; margin-bottom: 5px; }
    .cal-day-cell { background: white; border-radius: 8px; padding: 5px; min-height: 50px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid #e2e8f0; font-size: 14px; font-weight: bold; }
    .occ-low { background: #ecfdf5; border-color: #10b981; color: #065f46; }
    .occ-med { background: #ffedd5; border-color: #f97316; color: #9a3412; }
    .occ-high { background: #fee2e2; border-color: #ef4444; color: #991b1b; }
    
    div[data-testid="stButton"] button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. LOGICĂ & DATABASE
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
CAMERE_INFO = {"Camera 1": 200, "Camera 2": 200, "Camera 3": 250, "Camera 4": 250, "Camera 5": 300, "Camera 6": 350}

@st.cache_data(ttl=3600)
def get_data_cached():
    try:
        df = conn.read(worksheet="Rezervari", ttl=0)
        req = ['id', 'nume', 'telefon', 'email', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note']
        if df.empty: return pd.DataFrame(columns=req)
        for col in req:
            if col not in df.columns: df[col] = ""
        df['checkin'] = pd.to_datetime(df['checkin'], errors='coerce')
        df['checkout'] = pd.to_datetime(df['checkout'], errors='coerce')
        df = df.dropna(subset=['checkin', 'checkout'])
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        df['pret_total'] = pd.to_numeric(df['pret_total'], errors='coerce').fillna(0.0)
        df['telefon'] = df['telefon'].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '')
        df['email'] = df['email'].astype(str).replace('nan', '')
        return df
    except: return pd.DataFrame(columns=['id', 'nume', 'telefon', 'email', 'camera', 'checkin', 'checkout', 'status', 'pret_total', 'note'])

def update_data(df):
    try:
        df_s = df.copy()
        df_s['checkin'] = df_s['checkin'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_s['checkout'] = df_s['checkout'].dt.strftime('%Y-%m-%d %H:%M:%S')
        conn.update(worksheet="Rezervari", data=df_s)
        st.cache_data.clear()
    except Exception as e: st.error(str(e))

def este_disponibila(df, camera, start, end):
    if df.empty: return True
    mask = (df['status'] != 'Anulat') & (df['camera'] == camera)
    conflict = mask & ~( (df['checkout'] <= start) | (df['checkin'] >= end) )
    return df[conflict].empty

# --- PDF GENERATOR ---
def genereaza_pdf_bytes(r):
    pdf = FPDF(); pdf.add_page()
    if os.path.exists("LOGO final.png"): pdf.image("LOGO final.png", x=10, y=8, w=30); pdf.ln(20)
    
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, clean_text("CONFIRMARE REZERVARE"), ln=True, align='C'); pdf.ln(5)
    
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, clean_text(f"ID Rezervare: {r['id']}"), ln=True)
    pdf.cell(0, 8, clean_text(f"Client: {r['nume']}"), ln=True)
    pdf.cell(0, 8, clean_text(f"Email: {r.get('email', '-')}"), ln=True)
    pdf.cell(0, 8, clean_text(f"Telefon: {r['telefon']}"), ln=True)
    pdf.cell(0, 8, clean_text(f"Camera(e): {r['camera']}"), ln=True)
    
    try: d1, d2 = r['checkin'].strftime('%d-%m-%Y'), r['checkout'].strftime('%d-%m-%Y')
    except: d1, d2 = str(r['checkin']), str(r['checkout'])
    pdf.cell(0, 8, f"Perioada: {d1} -> {d2}", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, clean_text(f"Total de Plata: {r['pret_total']} RON"), ln=True)
    if pd.notna(r['note']) and r['note']: 
        pdf.set_font("Arial", 'I', 10); pdf.multi_cell(0, 6, clean_text(f"Note: {r['note']}")); pdf.ln(2)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, clean_text("REGULAMENT INTERN:"), ln=True)
    pdf.set_font("Arial", '', 9)
    pdf.multi_cell(0, 5, clean_text(REGULAMENT_TEXT))

    pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
    pdf1_buffer = io.BytesIO(pdf_bytes)
    output_writer = PdfWriter()
    output_writer.add_page(PdfReader(pdf1_buffer).pages[0])
    
    if os.path.exists("General pag2.pdf"):
        try:
            doc2 = PdfReader("General pag2.pdf")
            for page in doc2.pages: output_writer.add_page(page)
        except: pass
    
    final_buffer = io.BytesIO()
    output_writer.write(final_buffer)
    return final_buffer.getvalue()

# --- EMAIL SENDER ---
def trimite_email_cu_pdf(destinatar, r, pdf_bytes):
    try:
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = destinatar
        msg['Subject'] = f"Confirmare Rezervare Elia - {r['nume']}"

        body = f"""Buna ziua {r['nume']},

Va multumim pentru rezervare!
Atasat gasiti confirmarea oficiala si regulamentul pensiunii.

Detalii pe scurt:
Camera: {r['camera']}
Perioada: {r['checkin'].strftime('%d-%m-%Y')} -> {r['checkout'].strftime('%d-%m-%Y')}
Total: {r['pret_total']} RON

{REGULAMENT_TEXT}

Echipa Elia
"""
        msg.attach(MIMEText(body, 'plain'))

        part = MIMEApplication(pdf_bytes, Name=f"Rezervare_{r['id']}.pdf")
        part['Content-Disposition'] = f'attachment; filename="Rezervare_{r["id"]}.pdf"'
        msg.attach(part)

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, "Email trimis!"
    except Exception as e: return False, f"Eroare: {str(e)}"

# ==========================================
# 3. INTERFAȚĂ
# ==========================================
if os.path.exists("LOGO final.png"): st.sidebar.image("LOGO final.png", use_container_width=True)
st.sidebar.markdown("### 🏔️ Elia PMS")
if st.sidebar.button("✨ Rezervare Nouă", use_container_width=True, type="primary"): st.session_state['show_add_modal'] = True
menu = {"📅 Harta": "Harta", "🗓️ Calendar": "Calendar", "📊 Statistici": "Statistici", "📋 Registru": "Lista"}
choice = st.sidebar.radio("Meniu", list(menu.keys()), format_func=lambda x: x)
sel_page = menu[choice]
df_master = get_data_cached()

# ==========================================
# 4. MODAL ADĂUGARE
# ==========================================
if st.session_state.get('show_add_modal', False):
    st.markdown("---")
    with st.container():
        st.markdown("<div class='info-card'><h3>✨ Adaugă Rezervare</h3>", unsafe_allow_html=True)
        with st.form("quick_add"):
            c1, c2 = st.columns(2)
            nume = c1.text_input("Nume", placeholder="Client / Grup")
            tel = c2.text_input("Tel", placeholder="07xx")
            
            c_email, c_cam = st.columns(2)
            email_client = c_email.text_input("Email", placeholder="client@email.com")
            camere_selectate = c_cam.multiselect("Camere", list(CAMERE_INFO.keys()))
            
            d1 = c1.date_input("In", date.today()); d2 = c2.date_input("Out", date.today()+timedelta(1))
            
            st.markdown("---")
            st.markdown("**💰 Configurare Preț**")
            tip_pret = st.radio("Cum introduci prețul?", ["Total Sejur (Global)", "Per Noapte / Cameră"], horizontal=True)
            val_introdusa = st.number_input("Valoare (RON)", value=0.0, step=50.0)
            
            # Logică calcul afișat (doar informativ)
            num_nopti = (d2 - d1).days
            num_camere = len(camere_selectate) if camere_selectate else 0
            pret_final_total = 0.0
            
            if num_camere > 0 and num_nopti > 0:
                if tip_pret == "Total Sejur (Global)":
                    pret_final_total = val_introdusa
                    st.info(f"Total de plată: **{pret_final_total:.0f} RON** (Grup)")
                else:
                    pret_final_total = val_introdusa * num_nopti * num_camere
                    st.info(f"Calculat Total: **{pret_final_total:.0f} RON** ({val_introdusa} x {num_nopti} nopți x {num_camere} camere)")
            
            note = st.text_area("Note")
            trimite_mail_acum = st.checkbox("📩 Trimite automat email?", value=False)
            
            if st.form_submit_button("🚀 Salvează"):
                if not camere_selectate:
                    st.error("Selectează cel puțin o cameră!")
                else:
                    t1, t2 = datetime.combine(d1, time(15,0)), datetime.combine(d2, time(11,0))
                    if all(este_disponibila(df_master, c, t1, t2) for c in camere_selectate):
                        new_rows = []
                        max_id = df_master['id'].max() if not df_master.empty else 0
                        group_id = int(max_id + 1)
                        created_reservations = []
                        
                        # SALVĂM PREȚUL TOTAL PE FIECARE LINIE (Așa a cerut userul)
                        # La statistici vom filtra duplicatele ID
                        
                        for cn in camere_selectate:
                            new_r = {"id": group_id, "nume": nume, "telefon": tel, "email": email_client, "camera": cn, "checkin": t1, "checkout": t2, "status": "Confirmat", "pret_total": pret_final_total, "note": note}
                            new_rows.append(new_r); created_reservations.append(new_r)
                        
                        update_data(pd.concat([df_master, pd.DataFrame(new_rows)], ignore_index=True))
                        
                        status_msg = ""
                        if trimite_mail_acum and email_client and "@" in email_client:
                            with st.spinner("Se trimite email..."):
                                r_mail = created_reservations[0].copy()
                                r_mail['camera'] = ", ".join(camere_selectate)
                                r_mail['pret_total'] = pret_final_total
                                pdf_bytes = genereaza_pdf_bytes(r_mail)
                                ok, msg = trimite_email_cu_pdf(email_client, r_mail, pdf_bytes)
                                status_msg = f" | {msg}"
                        
                        st.session_state['show_add_modal'] = False
                        st.toast(f"Salvat! {status_msg}"); st.rerun()
                    else: st.error("Una dintre camere este ocupată!")
            
            if st.form_submit_button("Închide"): st.session_state['show_add_modal'] = False; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 5. HARTA (TABEL RAPID & COLORAT & SELECTOR ANI)
# ==========================================
if sel_page == "Harta":
    st.markdown("<h2 style='text-align:center'>🗺️ Harta Disponibilității</h2>", unsafe_allow_html=True)
    
    # Selector LUNA pentru navigare
    c_nav1, c_nav2 = st.columns(2)
    
    # --- MODIFICARE: SELECTOR ANI DINAMIC (2017 -> PREZENT + 5) ---
    an_curent = datetime.now().year
    lista_ani = list(range(2017, an_curent + 6))
    idx_an_curent = lista_ani.index(an_curent) if an_curent in lista_ani else 0
    
    an_viz = c_nav1.selectbox("An", lista_ani, index=idx_an_curent)
    luna_viz = c_nav2.selectbox("Luna", list(calendar.month_name)[1:], index=datetime.now().month-1)
    
    luna_idx = list(calendar.month_name).index(luna_viz)
    zile_in_luna = calendar.monthrange(an_viz, luna_idx)[1]
    d_start_luna = date(an_viz, luna_idx, 1)
    zile = [d_start_luna + timedelta(days=i) for i in range(zile_in_luna)]
    
    df_v = df_master[df_master['status']!='Anulat'].copy() if not df_master.empty else pd.DataFrame(columns=df_master.columns)
    if not df_v.empty: df_v['ci'] = df_v['checkin'].dt.date; df_v['co'] = df_v['checkout'].dt.date

    # Generare Tabel HTML Colorat
    html = '<div class="scroll-container"><table class="custom-table"><thead><tr><th class="first-col">Cam</th>'
    for d in zile:
        bg_h = "#e2e8f0" if d.weekday() >= 5 else "#f8fafc" # Weekend usor gri
        html += f'<th style="background:{bg_h}">{d.strftime("%d")}<br><small>{d.strftime("%a")}</small></th>'
    html += '</tr></thead><tbody>'
    
    for cam in CAMERE_INFO.keys():
        html += f'<tr><td class="first-col">{cam}</td>'
        room_color = ROOM_COLORS.get(cam, DEFAULT_COLOR)
        
        for d in zile:
            if df_v.empty: html += '<td><div class="bg-liber"></div></td>'; continue
            
            r_out = df_v[(df_v['camera']==cam) & (df_v['co']==d)]
            r_in = df_v[(df_v['camera']==cam) & (df_v['ci']==d)]
            r_stay = df_v[(df_v['camera']==cam) & (df_v['ci']<d) & (df_v['co']>d)]
            
            cell_style, lbl = "", ""
            
            if not r_out.empty and not r_in.empty:
                # Schimb de tura - Gradient
                cell_style = f"background: linear-gradient(90deg, {room_color} 45%, #ffffff 50%, {room_color} 55%); width: 100.5%; color: #000;"
                lbl = f"{int(r_out.iloc[0]['id'])}↔{int(r_in.iloc[0]['id'])}"
            elif not r_out.empty:
                # Checkout (Iese)
                cell_style = f"background: linear-gradient(90deg, {room_color} 20%, #ffffff 80%); width: 100.5%; border-radius: 0 10px 10px 0;"
                lbl = str(int(r_out.iloc[0]['id']))
            elif not r_in.empty:
                # Checkin (Intra)
                cell_style = f"background: linear-gradient(90deg, #ffffff 20%, {room_color} 80%); width: 100.5%; border-radius: 10px 0 0 10px;"
                lbl = str(int(r_in.iloc[0]['id']))
            elif not r_stay.empty:
                # Full Stay
                cell_style = f"background: {room_color}; width: 100.5%; box-shadow:inset 0 0 0 1px rgba(255,255,255,0.2);"
                lbl = str(int(r_stay.iloc[0]['id']))
            
            if cell_style == "": html += f'<td><div class="bg-liber"></div></td>'
            else: html += f'<td><div class="calendar-box" style="{cell_style}">{lbl}</div></td>'
        html += '</tr>'
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

    # CĂUTARE & ADMINISTRARE
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='info-card'>", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        search_id = c1.number_input("🔎 Caută ID:", min_value=0, step=1, value=0)
        
        if search_id > 0 and not df_master.empty:
            found = df_master[df_master['id'] == search_id]
            if not found.empty:
                r = found.iloc[0]
                camere_grup = found['camera'].tolist()
                total_grup = r['pret_total'] # Pretul e deja total pe fiecare linie
                camere_str = ", ".join(camere_grup)
                
                st.markdown(f"### 👤 {r['nume']}") 
                st.markdown(f"**Camere:** {camere_str}")
                st.markdown(f"**Perioada:** {r['checkin'].strftime('%d.%m')} - {r['checkout'].strftime('%d.%m')} | **Total:** {total_grup:.0f} RON")
                
                with st.expander("✏️ Editează Rezervarea", expanded=False):
                    with st.form(key=f"e_{r['id']}"):
                        ce1, ce2 = st.columns(2)
                        nn = ce1.text_input("Nume", r['nume']); nt = ce2.text_input("Tel", r['telefon'])
                        ne = ce1.text_input("Email", r.get('email', ''))
                        np_total = ce2.number_input("Pret Total Grup (Nou)", value=float(total_grup))
                        nno = st.text_area("Note", r['note'])
                        
                        if st.form_submit_button("💾 Salvează Modificările"):
                            mask = df_master['id'] == r['id']
                            df_master.loc[mask, 'nume'] = nn
                            df_master.loc[mask, 'telefon'] = nt
                            df_master.loc[mask, 'email'] = ne
                            df_master.loc[mask, 'pret_total'] = np_total 
                            df_master.loc[mask, 'note'] = nno
                            update_data(df_master); st.toast("Actualizat!"); st.rerun()

                col_act1, col_act2 = st.columns(2)
                
                r_export = r.copy()
                r_export['camera'] = camere_str
                r_export['pret_total'] = total_grup
                
                pdf_bytes = genereaza_pdf_bytes(r_export)
                col_act1.download_button("📄 PDF", data=pdf_bytes, file_name=f"Rez_{r['id']}.pdf", mime="application/pdf", use_container_width=True)
                
                if col_act1.button("📧 Trimite Email", use_container_width=True):
                    if r.get('email') and "@" in str(r['email']):
                        with st.spinner("Trimit..."):
                            ok, msg = trimite_email_cu_pdf(r['email'], r_export, pdf_bytes)
                            if ok: st.success(msg)
                            else: st.error(msg)
                    else: st.error("Fără email!")

                msg_t = f"Salut {r['nume']}, confirmare Elia.\nCam: {camere_str}\nPerioada: {r['checkin'].strftime('%d.%m')} - {r['checkout'].strftime('%d.%m')}\nTotal: {total_grup} RON.\n\nRegulament:\nCheck-in >16:00, Out <11:00\nLiniste 23-07."
                wa = urllib.parse.quote(msg_t)
                col_act2.markdown(f'<a href="https://api.whatsapp.com/send?phone={r["telefon"]}&text={wa}" target="_blank"><button style="width:100%;background:#25D366;color:white;border:none;padding:10px;border-radius:5px;font-weight:bold;height:38px;margin-bottom:15px">💬 WhatsApp</button></a>', unsafe_allow_html=True)
                
                if col_act2.button("🗑️ ȘTERGE REZERVAREA", type="primary", use_container_width=True):
                    df_master = df_master[df_master['id'] != r['id']]
                    update_data(df_master)
                    st.toast("Șters cu succes!"); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 6. CALENDAR & STATISTICI
# ==========================================
elif sel_page == "Calendar":
    st.markdown("### 🗓️ Calendar")
    c1, c2 = st.columns([1,3]); an = c1.selectbox("An", [2024, 2025, 2026], index=1); luna = c2.selectbox("Luna", range(1, 13), index=datetime.now().month-1)
    cal = calendar.monthcalendar(an, luna)
    html_cal = '<div class="calendar-grid">'
    for z in ["Lu", "Ma", "Mi", "Jo", "Vi", "Sâ", "Du"]: html_cal += f'<div class="cal-day-header">{z}</div>'
    df_act = df_master[df_master['status']!='Anulat'].copy() if not df_master.empty else pd.DataFrame()
    if not df_act.empty: df_act['cin'] = df_act['checkin'].dt.normalize(); df_act['con'] = df_act['checkout'].dt.normalize()
    for week in cal:
        for day in week:
            if day == 0: html_cal += '<div></div>'; continue
            curr = pd.Timestamp(an, luna, day); nr = 0
            if not df_act.empty: nr = len(df_act[(df_act['cin'] <= curr) & (df_act['con'] > curr)]['camera'].unique())
            cls = "occ-low"
            if nr >= 6: cls = "occ-high"
            elif nr > 0: cls = "occ-med"
            html_cal += f'<div class="cal-day-cell {cls}">{day}<span style="font-size:10px; font-weight:normal">{nr}/6</span></div>'
    html_cal += '</div>'; st.markdown(html_cal, unsafe_allow_html=True)

elif sel_page == "Statistici":
    st.markdown("### 📊 Statistici Avansate")
    if not df_master.empty:
        df_s = df_master[df_master['status'] != 'Anulat'].copy()
        
        col_f1, col_f2 = st.columns(2)
        # --- SELECTOR ANI DINAMIC STATISTICI ---
        ani_disp = sorted(df_s['checkin'].dt.year.unique().tolist())
        if not ani_disp: ani_disp = [date.today().year]
        if 2017 not in ani_disp: ani_disp = [2017] + ani_disp # Force 2017 if missing
        
        an_selectat = col_f1.selectbox("Anul", ani_disp, index=len(ani_disp)-1)
        luni_nume = list(calendar.month_name)[1:]
        luni_selectate = col_f2.multiselect("Lunile (Gol = Tot Anul)", luni_nume)
        
        df_filtrat = df_s[df_s['checkin'].dt.year == an_selectat]
        if luni_selectate:
             month_indices = [list(calendar.month_name).index(m) for m in luni_selectate]
             df_filtrat = df_filtrat[df_filtrat['checkin'].dt.month.isin(month_indices)]
        
        # Venituri unice pe ID
        venit_total = df_filtrat.drop_duplicates(subset=['id'])['pret_total'].sum()
        
        total_capacity_days = 0; occupied_days = 0
        if luni_selectate:
             target_months = [list(calendar.month_name).index(m) for m in luni_selectate]
             days_to_check = []
             for m in target_months:
                 num_days = calendar.monthrange(an_selectat, m)[1]
                 days_to_check.extend([date(an_selectat, m, 1) + timedelta(days=i) for i in range(num_days)])
        else:
             s_y = date(an_selectat, 1, 1); e_y = date(an_selectat, 12, 31)
             days_to_check = [s_y + timedelta(days=i) for i in range((e_y - s_y).days + 1)]
             
        total_capacity_days = len(days_to_check) * 6
        relevant_bookings = df_s[(df_s['checkin'].dt.date <= date(an_selectat, 12, 31)) & (df_s['checkout'].dt.date >= date(an_selectat, 1, 1))]
        occupied_set = set()
        for _, row in relevant_bookings.iterrows():
            stay_dates = pd.date_range(row['checkin'], row['checkout'] - timedelta(days=1)).date
            for d in stay_dates:
                if d in days_to_check: occupied_set.add((d, row['camera']))
        
        grad_ocupare = (len(occupied_set) / total_capacity_days) * 100 if total_capacity_days > 0 else 0

        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='info-card'><h2 style='color:#059669;margin:0'>{venit_total:,.0f} RON</h2><small>Venituri</small></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='info-card'><h2 style='color:#2563eb;margin:0'>{grad_ocupare:.1f}%</h2><small>Grad Ocupare</small></div>", unsafe_allow_html=True)
        st.divider()
        
        col_g1, col_g2 = st.columns(2)
        monthly_stats = []
        for m in range(1, 13):
            month_name = calendar.month_name[m]
            
            m_data = df_s[(df_s['checkin'].dt.year == an_selectat) & (df_s['checkin'].dt.month == m)]
            rev = m_data.drop_duplicates(subset=['id'])['pret_total'].sum()
            
            days_in_m = calendar.monthrange(an_selectat, m)[1]
            cap_m = days_in_m * 6
            start_m = date(an_selectat, m, 1); end_m = date(an_selectat, m, days_in_m)
            m_bookings = df_s[(df_s['checkin'].dt.date <= end_m) & (df_s['checkout'].dt.date >= start_m)]
            occ_set_m = set()
            for _, row in m_bookings.iterrows():
                stay = pd.date_range(row['checkin'], row['checkout'] - timedelta(days=1)).date
                for d in stay:
                    if d.month == m and d.year == an_selectat: occ_set_m.add((d, row['camera']))
            monthly_stats.append({"Luna": month_name, "Venituri": rev, "Grad Ocupare": round((len(occ_set_m)/cap_m)*100, 1)})
            
        df_charts = pd.DataFrame(monthly_stats)
        if luni_selectate: df_charts = df_charts[df_charts['Luna'].isin(luni_selectate)]

        col_g1.subheader("💰 Venituri Lunare")
        col_g1.bar_chart(df_charts.set_index("Luna")['Venituri'], color="#059669")
        col_g2.subheader("📈 Grad Ocupare (%)")
        col_g2.line_chart(df_charts.set_index("Luna")['Grad Ocupare'], color="#2563eb")
    else: st.info("Nu există date.")

elif sel_page == "Lista":
    st.markdown("### 📋 Registru")
    if not df_master.empty: st.dataframe(df_master[['id','nume','camera','checkin','pret_total']].sort_values(by='checkin', ascending=False), use_container_width=True)
