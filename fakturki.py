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
if st.session_state.config is None or st.sidebar.toggle("⚙️ Ustawienia API/Email", False):
    st.title("⚙️ Konfiguracja Danych")
    st.info("Wprowadź dane raz – zostaną zapisane w config.json (lub w sesji chmury).")
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
            r_e = st.text_input("Odbiorca Email", value=old.get("RECIPIENT_EMAIL", ""))
        
        if st.form_submit_button("Zapisz i przejdź do aplikacji"):
            new_conf = {"USER_LOGIN": u_l, "KEY_FAKTURA": k_f, "KEY_WYDATEK": k_w, "GMAIL_USER": g_u, "GMAIL_PASSWORD": g_p, "RECIPIENT_EMAIL": r_e}
            st.session_state.config = new_conf
            save_config(new_conf)
    st.stop()

# --- PRZYPISANIE ZMIENNYCH ---
C = st.session_state.config
API_URL = "https://www.ifirma.pl/iapi/fakturakraj.json"
WYDATEK_URL = "https://www.ifirma.pl/iapi/wydatek.json"
DANE_FALCK = {"nazwa": "Falck Digital Technology Poland Spółka Z Ograniczoną Odpowiedzialnością", "nip": "5272997346", "ulica": "Prosta 67", "kod": "00-838", "miasto": "Warszawa"}

# --- FUNKCJE POMOCNICZE ---
def get_auth_header(user, key, content, custom_url=None, key_type="faktura"):
    url = custom_url if custom_url else API_URL
    message = f"{url}{user}{key_type}{content}".encode('utf-8')
    key_bytes = bytes.fromhex(key.strip())
    return f"IAPIS user={user}, hmac-sha1={hmac.new(key_bytes, message, hashlib.sha1).hexdigest()}"

def pobierz_pdf(faktura_id):
    pdf_url = f"https://www.ifirma.pl/iapi/fakturakraj/{faktura_id}.pdf"
    auth = get_auth_header(C["USER_LOGIN"], C["KEY_FAKTURA"], "", custom_url=pdf_url)
    res = requests.get(pdf_url, headers={"Accept": "application/pdf", "Authentication": auth})
    return res.content if res.status_code == 200 else None

def wyslij_email(pdf_faktura, miesiac_rok, dodatkowy_plik=None):
    try:
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = C["GMAIL_USER"], C["RECIPIENT_EMAIL"], f"Filip Lubecki - faktura {miesiac_rok}"
        msg.attach(MIMEText(f"Witam,\n\nW załączniku faktura za {miesiac_rok} oraz raport.\n\nPozdrawiam,\nFilip", 'plain', 'utf-8'))
        p1 = MIMEBase('application', "pdf")
        p1.set_payload(pdf_faktura); encoders.encode_base64(p1)
        p1.add_header('Content-Disposition', f'attachment; filename="Filip Lubecki - faktura {miesiac_rok}.pdf"')
        msg.attach(p1)
        if dodatkowy_plik:
            p2 = MIMEBase('application', "octet-stream")
            p2.set_payload(dodatkowy_plik.getvalue()); encoders.encode_base64(p2)
            p2.add_header('Content-Disposition', f'attachment; filename="{dodatkowy_plik.name}"')
            msg.attach(p2)
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls()
        s.login(C["GMAIL_USER"], C["GMAIL_PASSWORD"]); s.send_message(msg); s.quit()
        return True
    except Exception as e:
        st.error(f"Błąd e-mail: {e}"); return False

def wyswietl_pdf(pdf_content):
    b64 = base64.b64encode(pdf_content).decode('utf-8')
    st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="800"></iframe>', unsafe_allow_html=True)

# --- INTERFEJS ---
st.set_page_config(page_title="iFirma System", layout="wide")
st.sidebar.caption(f"Zalogowany: {C['USER_LOGIN']}")
tryb = st.sidebar.radio("Nawigacja", ["📤 Falck (Wystaw)", "📥 Wydatki (Koszty)"])

if tryb == "📤 Falck (Wystaw)":
    st.title("🚀 Faktura dla Falck Digital")
    if 'rows_f' not in st.session_state: st.session_state.rows_f = [{"u": "Usługi programistyczne", "h": 160.0, "c": 170.0}]
    
    akt_poz = []
    # Logika dynamicznych wierszy z PLUSEM ➕
    for idx, r in enumerate(st.session_state.rows_f):
        c1, c2, c3, c4 = st.columns([4, 1, 2, 0.5])
        u = c1.text_input("Usługa", r['u'], key=f"u_{idx}")
        h = c2.number_input("h", r['h'], key=f"h_{idx}")
        s = c3.number_input("Stawka", r['c'], key=f"s_{idx}")
        st.session_state.rows_f[idx] = {"u": u, "h": h, "c": s} # Zapisz zmiany w sesji
        
        if c4.button("➕", key=f"btn_{idx}"): 
            st.session_state.rows_f.append({"u": "", "h": 0.0, "c": 0.0})
            st.rerun()
        akt_poz.append({"StawkaVat": 0.23, "Ilosc": h, "CenaJednostkowa": s, "NazwaPelna": u, "Jednostka": "h", "TypStawkiVat": "PRC", "StawkaRyczaltu": 0.12})

    dz = datetime.date.today(); m_pl = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"]
    m_t = f"{m_pl[dz.month-1]} {dz.year}"; ost = calendar.monthrange(dz.year, dz.month)[1]; d_f = datetime.date(dz.year, dz.month, ost)

    if st.button("🚀 WYSTAW I POBIERZ PDF", type="primary", use_container_width=True):
        pay = {"Zaplacono": 0, "LiczOd": "NET", "DataWystawienia": d_f.isoformat(), "DataSprzedazy": d_f.isoformat(), "FormatDatySprzedazy": "MSC", "SposobZaplaty": "PRZ", "TerminPlatnosci": (d_f + datetime.timedelta(days=10)).isoformat(), "Pozycje": akt_poz, "Kontrahent": {"Nazwa": DANE_FALCK["nazwa"], "NIP": DANE_FALCK["nip"], "Ulica": DANE_FALCK["ulica"], "KodPocztowy": DANE_FALCK["kod"], "Miejscowosc": DANE_FALCK["miasto"]}, "RodzajPodpisuOdbiorcy": "BWO", "MiejsceWystawienia": "Warszawa"}
        json_b = json.dumps(pay, separators=(',', ':'))
        res = requests.post(API_URL, data=json_b, headers={"Content-Type": "application/json", "Authentication": get_auth_header(C["USER_LOGIN"], C["KEY_FAKTURA"], json_b)})
        if res.status_code == 201:
            st.session_state["pdf_f"] = pobierz_pdf(res.json()['response']['Identyfikator']); st.success("✅ Wystawiono!")
        else: st.error(res.json())

    if "pdf_f" in st.session_state:
        st.divider()
        cf, cm = st.columns([1, 1])
        with cf: rap = st.file_uploader("📎 Załącz raport (z pulpitu)", type=None)
        with cm:
            if st.button("📧 WYŚLIJ MAIL (KOMPLET)", use_container_width=True):
                if wyslij_email(st.session_state["pdf_f"], m_t, rap): st.success("📩 Wysłano!")
        wyswietl_pdf(st.session_state["pdf_f"])

elif tryb == "📥 Wydatki (Koszty)":
    st.title("📥 Dodawanie Wydatków")
    up_f = st.file_uploader("Wrzuć plik kosztowy", type=["pdf", "jpg", "png"])
    if up_f:
        c1, c2 = st.columns([1, 1]); f_b = up_f.read()
        with c1: wyswietl_pdf(f_b) if up_f.type=="application/pdf" else st.image(f_b)
        with c2:
            n_d = st.text_input("Nr faktury"); k_n = st.text_input("Sprzedawca"); brut = st.number_input("Brutto"); net = st.number_input("Netto")
            if st.button("🚀 Wyślij do iFirma", type="primary", use_container_width=True):
                enc = base64.b64encode(f_b).decode('utf-8')
                pay_w = {"NumerDokumentu": n_d, "DataWystawienia": datetime.date.today().isoformat(), "NazwaWydatku": f"Zakup: {k_n}", "KwotaBrutto": brut, "KwotaNetto": net, "Zalacznik": {"Nazwa": up_f.name, "Zawartosc": enc}}
                json_w = json.dumps(pay_w, separators=(',', ':'))
                auth_w = get_auth_header(C["USER_LOGIN"], C["KEY_WYDATEK"], json_w, custom_url=WYDATEK_URL, key_type="wydatek")
                res_w = requests.post(WYDATEK_URL, data=json_w, headers={"Content-Type": "application/json", "Authentication": auth_w})
                if res_w.status_code == 201: st.success("✅ Dodano koszt!")
                else: st.error(f"Błąd: {res_w.text}")
