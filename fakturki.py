import streamlit as st, requests, hashlib, hmac, datetime, json, calendar, smtplib, base64, os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# --- KONFIGURACJA PLIKU ---
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: return None
    return None

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)
    st.success("✅ Ustawienia zapisane!")
    st.rerun()

# --- ŁADOWANIE DANYCH ---
if 'config' not in st.session_state:
    st.session_state.config = load_config()

# --- PANEL KONFIGURACJI ---
if st.session_state.config is None or st.sidebar.toggle("⚙️ Ustawienia API/Email"):
    st.title("⚙️ Konfiguracja Twoich danych")
    with st.form("config_form"):
        c1, c2 = st.columns(2)
        old = st.session_state.config or {}
        with c1:
            u_l = st.text_input("iFirma Login", value=old.get("USER_LOGIN", ""))
            k_f = st.text_input("Klucz FAKTURA", value=old.get("KEY_FAKTURA", ""), type="password")
            k_w = st.text_input("Klucz WYDATEK", value=old.get("KEY_WYDATEK", ""), type="password")
        with c2:
            g_u = st.text_input("Gmail User", value=old.get("GMAIL_USER", ""))
            g_p = st.text_input("Gmail Hasło Aplikacji", value=old.get("GMAIL_PASSWORD", ""), type="password")
            r_e = st.text_input("Odbiorca (Księgowość)", value=old.get("RECIPIENT_EMAIL", ""))
        
        if st.form_submit_button("Zapisz Ustawienia"):
            new_conf = {"USER_LOGIN": u_l, "KEY_FAKTURA": k_f, "KEY_WYDATEK": k_w, "GMAIL_USER": g_u, "GMAIL_PASSWORD": g_p, "RECIPIENT_EMAIL": r_e}
            st.session_state.config = new_conf
            save_config(new_conf)
    st.stop()

# PRZYPISANIE ZMIENNYCH
C = st.session_state.config
DANE_FALCK = {"nazwa": "Falck Digital Technology Poland Sp. z o.o.", "nip": "5272997346", "ulica": "Prosta 67", "kod": "00-838", "miasto": "Warszawa"}

# --- FUNKCJE API (SKRÓCONE DO LOGIKI) ---
def get_auth(u, k, c, url, kt):
    msg = f"{url}{u}{kt}{c}".encode('utf-8')
    h = hmac.new(bytes.fromhex(k.strip()), msg, hashlib.sha1).hexdigest()
    return f"IAPIS user={u}, hmac-sha1={h}"

def send_mail(pdf, m_t, extra=None):
    try:
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = C["GMAIL_USER"], C["RECIPIENT_EMAIL"], f"Faktura {m_t}"
        msg.attach(MIMEText(f"Dzień dobry,\n\nPrzesyłam fakturę za {m_t}.\n\nPozdrawiam", 'plain', 'utf-8'))
        p1 = MIMEBase('application', "pdf")
        p1.set_payload(pdf); encoders.encode_base64(p1)
        p1.add_header('Content-Disposition', f'attachment; filename="Faktura_{m_t}.pdf"')
        msg.attach(p1)
        if extra:
            p2 = MIMEBase('application', "octet-stream")
            p2.set_payload(extra.getvalue()); encoders.encode_base64(p2)
            p2.add_header('Content-Disposition', f'attachment; filename="{extra.name}"')
            msg.attach(p2)
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls()
        s.login(C["GMAIL_USER"], C["GMAIL_PASSWORD"]); s.send_message(msg); s.quit()
        return True
    except Exception as e: st.error(f"Błąd: {e}"); return False

# --- INTERFEJS ---
st.sidebar.success(f"Połączono: {C['USER_LOGIN']}")
menu = st.sidebar.radio("Menu", ["📤 Wystaw Falck", "📥 Dodaj Koszt"])

if menu == "📤 Wystaw Falck":
    st.title("📄 Faktura dla Falck")
    if 'rows' not in st.session_state: st.session_state.rows = [{"u": "Usługi programistyczne", "h": 160.0, "c": 170.0}]
    
    # Renderowanie wierszy
    for i, r in enumerate(st.session_state.rows):
        col1, col2, col3 = st.columns([3,1,1])
        st.session_state.rows[i]['u'] = col1.text_input("Usługa", r['u'], key=f"u{i}")
        st.session_state.rows[i]['h'] = col2.number_input("Godziny", r['h'], key=f"h{i}")
        st.session_state.rows[i]['c'] = col3.number_input("Cena", r['c'], key=f"c{i}")

    if st.button("🚀 Wystaw i wyślij"):
        # Logika wystawiania (identyczna jak wcześniej)
        # ... (wycięte dla zwięzłości, użyj logiki res.status_code == 201)
        st.info("Faktura zostanie wygenerowana zgodnie z API iFirma...")

# [Tutaj wstaw brakujące funkcje pomocnicze wyswietl_pdf i pobierz_pdf z poprzednich wersji]