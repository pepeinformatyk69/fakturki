import streamlit as st, requests, hashlib, hmac, datetime, json, calendar, smtplib, base64, os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# --- INICJALIZACJA SESJI ---
# Dane nie są zapisywane na dysku serwera, lecz w pamięci Twojej przeglądarki.
if 'config' not in st.session_state:
    st.session_state.config = None

# --- PANEL KONFIGURACJI ---
with st.sidebar:
    st.image("https://www.ifirma.pl/wp-content/themes/ifirma/img/logo-ifirma.svg", width=150)
    st.divider()
    if st.session_state.config:
        st.success(f"Zalogowany: {st.session_state.config.get('USER_LOGIN')}")
        if st.button("🚪 Wyloguj i wyczyść dane", use_container_width=True):
            st.session_state.config = None
            st.rerun()

if st.session_state.config is None:
    st.title("⚙️ Skonfiguruj połączenie")
    st.info("Wprowadź dane – będą one aktywne tylko w tej sesji przeglądarki. Po zamknięciu karty dane znikną ze względów bezpieczeństwa.")
    with st.form("config_form"):
        c1, c2 = st.columns(2)
        with c1:
            u_l = st.text_input("iFirma Login (email)", placeholder="np. filip...@gmail.com")
            k_f = st.text_input("Klucz FAKTURA", type="password")
            k_w = st.text_input("Klucz WYDATEK", type="password")
        with c2:
            g_u = st.text_input("Gmail Login", placeholder="Twój email Gmail")
            g_p = st.text_input("Gmail Hasło Aplikacji", type="password", help="Wymagane 16-znakowe hasło aplikacji wygenerowane w koncie Google.")
            r_e = st.text_input("Email Odbiorcy", value="filip.lubecki.it@gmail.com")
        
        if st.form_submit_button("Uruchom Aplikację", use_container_width=True, type="primary"):
            st.session_state.config = {
                "USER_LOGIN": u_l, "KEY_FAKTURA": k_f, "KEY_WYDATEK": k_w,
                "GMAIL_USER": g_u, "GMAIL_PASSWORD": g_p, "RECIPIENT_EMAIL": r_e
            }
            st.rerun()
    st.stop()

# PRZYPISANIE ZMIENNYCH Z SESJI
C = st.session_state.config
DANE_FALCK = {"nazwa": "Falck Digital Technology Poland Sp. z o.o.", "nip": "5272997346", "ulica": "Prosta 67", "kod": "00-838", "miasto": "Warszawa"}

# --- FUNKCJE POMOCNICZE ---
def get_auth_header(user, key, content, custom_url=None, key_type="faktura"):
    url = custom_url if custom_url else "https://www.ifirma.pl/iapi/fakturakraj.json"
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
        msg.attach(MIMEText(f"Dzień dobry,\n\nW załączniku przesyłam fakturę za {miesiac_rok} oraz raport godzinowy.\n\nPozdrawiam,\nFilip Lubecki", 'plain', 'utf-8'))
        p1 = MIMEBase('application', "pdf")
        p1.set_payload(pdf_faktura); encoders.encode_base64(p1)
        p1.add_header('Content-Disposition', f'attachment; filename="Faktura_Lubecki_{miesiac_rok}.pdf"')
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
    base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=0" width="100%" height="1000" style="border:none;"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- INTERFEJS GŁÓWNY ---
st.set_page_config(page_title="iFirma Automatyzacja", layout="wide", page_icon="🚀")
tryb = st.sidebar.radio("Nawigacja", ["📤 Wystaw dla Falck", "📥 Dodaj Koszt"])

if tryb == "📤 Wystaw dla Falck":
    st.title("🚀 Faktura dla Falck Digital")
    
    if 'rows_f' not in st.session_state: 
        st.session_state.rows_f = [{"u": "Usługi programistyczne", "h": 160.0, "c": 170.0}]
    
    akt_poz = []
    for idx, r in enumerate(st.session_state.rows_f):
        c1, c2, c3, c4 = st.columns([4, 1, 2, 0.5])
        u = c1.text_input("Usługa", r['u'], key=f"u_{idx}")
        h = c2.number_input("h", r['h'], key=f"h_{idx}", step=1.0)
        s = c3.number_input("Stawka", r['c'], key=f"s_{idx}", step=1.0)
        st.session_state.rows_f[idx] = {"u": u, "h": h, "c": s}
        if c4.button("➕", key=f"btn_{idx}"): 
            st.session_state.rows_f.append({"u": "", "h": 0.0, "c": 0.0})
            st.rerun()
        akt_poz.append({"StawkaVat": 0.23, "Ilosc": h, "CenaJednostkowa": s, "NazwaPelna": u, "Jednostka": "h", "TypStawkiVat": "PRC", "StawkaRyczaltu": 0.12})

    dz = datetime.date.today()
    m_pl = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"]
    m_t = f"{m_pl[dz.month-1]} {dz.year}"
    ost = calendar.monthrange(dz.year, dz.month)[1]
    d_f = datetime.date(dz.year, dz.month, ost)

    if st.button("🚀 WYSTAW FAKTURĘ W IFIRMA", type="primary", use_container_width=True):
        with st.spinner("Komunikacja z iFirma..."):
            pay = {"Zaplacono": 0, "LiczOd": "NET", "DataWystawienia": d_f.isoformat(), "DataSprzedazy": d_f.isoformat(), "FormatDatySprzedazy": "MSC", "SposobZaplaty": "PRZ", "TerminPlatnosci": (d_f + datetime.timedelta(days=10)).isoformat(), "Pozycje": akt_poz, "Kontrahent": {"Nazwa": DANE_FALCK["nazwa"], "NIP": DANE_FALCK["nip"], "Ulica": DANE_FALCK["ulica"], "KodPocztowy": DANE_FALCK["kod"], "Miejscowosc": DANE_FALCK["miasto"]}, "RodzajPodpisuOdbiorcy": "BWO", "MiejsceWystawienia": "Warszawa"}
            json_b = json.dumps(pay, separators=(',', ':'))
            auth = get_auth_header(C["USER_LOGIN"], C["KEY_FAKTURA"], json_b)
            res = requests.post("https://www.ifirma.pl/iapi/fakturakraj.json", data=json_b, headers={"Content-Type": "application/json", "Authentication": auth})
            
            if res.status_code == 201 or (res.json().get('response', {}).get('Kod') == 0):
                f_id = res.json()['response']['Identyfikator']
                st.session_state["pdf_f"] = pobierz_pdf(f_id)
                st.balloons()
                st.success(f"✅ Faktura wystawiona! ID: {f_id}")
            else:
                st.error(f"❌ iFirma błąd: {res.json().get('response', {}).get('Informacja')}")

    if "pdf_f" in st.session_state:
        st.divider()
        col_f, col_m = st.columns([1, 1])
        with col_f:
            rap = st.file_uploader("📎 Dołącz raport godzinowy", type=None)
        with col_m:
            st.write(" ")
            if st.button("📧 WYŚLIJ KOMPLET DO FALCK", use_container_width=True, type="primary"):
                with st.spinner("Wysyłanie..."):
                    if wyslij_email(st.session_state["pdf_f"], m_t, rap):
                        st.success("📩 Wysłano!")
        
        st.divider()
        st.download_button("💾 Pobierz PDF", data=st.session_state["pdf_f"], file_name=f"Faktura_{m_t}.pdf", mime="application/pdf")
        wyswietl_pdf(st.session_state["pdf_f"])

elif tryb == "📥 Dodaj Koszt":
    st.title("📥 Rejestracja Wydatku")
    up_f = st.file_uploader("Przeciągnij plik PDF/Obraz", type=["pdf", "jpg", "png"])
    if up_f:
        c1, c2 = st.columns([1, 2])
        f_b = up_f.read()
        with c1:
            if up_f.type=="application/pdf":
                wyswietl_pdf(f_b)
            else:
                st.image(f_b)
        with c2:
            with st.form("cost_form"):
                n_d = st.text_input("Numer faktury")
                k_n = st.text_input("Sprzedawca")
                brut = st.number_input("Brutto", step=0.01)
                net = st.number_input("Netto", step=0.01)
                if st.form_submit_button("🚀 PRZEŚLIJ DO IFIRMA", use_container_width=True):
                    enc = base64.b64encode(f_b).decode('utf-8')
                    pay_w = {"NumerDokumentu": n_d, "DataWystawienia": datetime.date.today().isoformat(), "NazwaWydatku": k_n, "KwotaBrutto": brut, "KwotaNetto": net, "Zalacznik": {"Nazwa": up_f.name, "Zawartosc": enc}}
                    json_w = json.dumps(pay_w, separators=(',', ':'))
                    auth_w = get_auth_header(C["USER_LOGIN"], C["KEY_WYDATEK"], json_w, custom_url="https://www.ifirma.pl/iapi/wydatek.json", key_type="wydatek")
                    res_w = requests.post("https://www.ifirma.pl/iapi/wydatek.json", data=json_w, headers={"Content-Type": "application/json", "Authentication": auth_w})
                    if res_w.status_code == 201:
                        st.success("✅ Dodano koszt!")
                    else:
                        st.error(f"❌ Błąd: {res_w.text}")
