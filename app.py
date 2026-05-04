import streamlit as st
import pandas as pd
import hashlib
import firebase_admin
import urllib.parse
from firebase_admin import credentials, firestore

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Collector 2026 Pro", layout="wide", page_icon="⚽")

# --- INICIALIZAÇÃO DO FIREBASE SEGURA ---
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            # Em vez de carregar o arquivo, carregamos do dicionário de Secrets do Streamlit
            firebase_secrets = st.secrets["firebase_credentials"]
            # Converter o Secrets em um dicionário Python comum
            cred_dict = dict(firebase_secrets)
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro ao carregar Firebase: {e}")
            return None
    return firestore.client()

db = init_firebase()

# --- MAPEAMENTO DE SIGLAS E BANDEIRAS ---
SIGLAS_CUSTOM = {
    "Página inicial": "FWC", "México": "MEX", "África do Sul": "RSA", "Coreia do Sul": "KOR", 
    "Rep. Tcheca": "CZE", "Canadá": "CAN", "Bósnia": "BIH", "Qatar": "QAT", "Suíça": "SUI",
    "Brasil": "BRA", "Marrocos": "MAR", "Haiti": "HAI", "Escócia": "SCO", "EUA": "USA",
    "Paraguai": "PAR", "Austrália": "AUS", "Turquia": "TUR", "Alemanha": "GER", 
    "Curaçao": "CUW", "Costa do Marfim": "CIV", "Equador": "ECU", "Holanda": "NED",
    "Japão": "JPN", "Suécia": "SWE", "Tunísia": "TUN", "Bélgica": "BEL", "Egito": "EGY",
    "Irã": "IRN", "Nova Zelândia": "NZL", "Espanha": "ESP", "Cabo Verde": "CPV",
    "Arábia Saudita": "KSA", "Uruguai": "URU", "França": "FRA", "Senegal": "SEN",
    "Iraque": "IRQ", "Noruega": "NOR", "Argentina": "ARG", "Argélia": "ALG",
    "Áustria": "AUT", "Jordânia": "JOR", "Portugal": "POR", "RD Congo": "COD",
    "Uzbequistão": "UZB", "Colômbia": "COL", "Inglaterra": "ENG", "Croácia": "CRO",
    "Gana": "GHA", "Panamá": "PAN", "FIFA World Cup History": "FWC", "Figurinhas da Coca-Cola": "CC"
}

BANDEIRAS = {
    "México": "mx", "África do Sul": "za", "Coreia do Sul": "kr", "Rep. Tcheca": "cz",
    "Canadá": "ca", "Bósnia": "ba", "Qatar": "qa", "Suíça": "ch", "Brasil": "br", 
    "Marrocos": "ma", "Haiti": "ht", "Escócia": "gb-sct", "EUA": "us", "Paraguai": "py", 
    "Austrália": "au", "Turquia": "tr", "Alemanha": "de", "Curaçao": "cw", "Costa do Marfim": "ci", 
    "Equador": "ec", "Holanda": "nl", "Japão": "jp", "Suécia": "se", "Tunísia": "tn",
    "Bélgica": "be", "Egito": "eg", "Irã": "ir", "Nova Zelândia": "nz", "Espanha": "es", 
    "Cabo Verde": "cv", "Arábia Saudita": "sa", "Uruguai": "uy", "França": "fr", 
    "Senegal": "sn", "Iraque": "iq", "Noruega": "no", "Argentina": "ar", "Argélia": "dz", 
    "Áustria": "at", "Jordânia": "jo", "Portugal": "pt", "RD Congo": "cd", "Uzbequistão": "uz", 
    "Colômbia": "co", "Inglaterra": "gb-eng", "Croácia": "hr", "Gana": "gh", "Panamá": "pa"
}

GRUPOS_SORTEIO = {
    "GRUPO A": ["México", "África do Sul", "Coreia do Sul", "Rep. Tcheca"],
    "GRUPO B": ["Canadá", "Bósnia", "Qatar", "Suíça"],
    "GRUPO C": ["Brasil", "Marrocos", "Haiti", "Escócia"],
    "GRUPO D": ["EUA", "Paraguai", "Austrália", "Turquia"],
    "GRUPO E": ["Alemanha", "Curaçao", "Costa do Marfim", "Equador"],
    "GRUPO F": ["Holanda", "Japão", "Suécia", "Tunísia"],
    "GRUPO G": ["Bélgica", "Egito", "Irã", "Nova Zelândia"],
    "GRUPO H": ["Espanha", "Cabo Verde", "Arábia Saudita", "Uruguai"],
    "GRUPO I": ["França", "Senegal", "Iraque", "Noruega"],
    "GRUPO J": ["Argentina", "Argélia", "Áustria", "Jordânia"],
    "GRUPO K": ["Portugal", "RD Congo", "Uzbequistão", "Colômbia"],
    "GRUPO L": ["Inglaterra", "Croácia", "Gana", "Panamá"]
}

LISTA_FINAL_ALBUM = ["Página inicial"] + [time for grupo in GRUPOS_SORTEIO.values() for time in grupo] + ["FIFA World Cup History", "Figurinhas da Coca-Cola"]

# --- LÓGICA DE GERAÇÃO DE IDs ---
def get_fig_ids(secao):
    sigla = SIGLAS_CUSTOM.get(secao)
    if secao == "Página inicial":
        return [f"{sigla}-00"] + [f"{sigla}-{i:02d}" for i in range(1, 9)]
    elif secao == "FIFA World Cup History":
        return [f"{sigla}-{i:02d}" for i in range(9, 20)]
    elif secao == "Figurinhas da Coca-Cola":
        return [f"{sigla}{i}" for i in range(1, 15)]
    else:
        return [f"{sigla}-{i:02d}" for i in range(1, 21)]

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .fig-card { border: 2px solid #ddd; border-radius: 10px; padding: 10px; text-align: center; background-color: white; margin-bottom: 5px; position: relative; }
    .colada { background-color: #1b5e20 !important; color: white !important; border-color: #003300 !important; }
    .faltando { background-color: #f1f3f4; color: #5f6368; }
    .rep-badge { background-color: #ffd600; color: black; border-radius: 50%; padding: 2px 7px; font-weight: bold; font-size: 0.8em; position: absolute; top: 5px; right: 5px; }
    .msg-box { background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 5px; border-left: 5px solid #25D366; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

def hash_pass(p): return hashlib.sha256(str.encode(p)).hexdigest()

def main():
    if 'auth' not in st.session_state: st.session_state.auth = False

    if not st.session_state.auth:
        st.title("🏆 Collector 2026 Pro")
        aba1, aba2 = st.tabs(["Login", "Cadastrar"])
        with aba1:
            u = st.text_input("Usuário").lower().strip()
            p = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                res = db.collection("usuarios").document(u).get()
                if res.exists and res.to_dict()['password'] == hash_pass(p):
                    st.session_state.auth = True; st.session_state.user = u; st.rerun()
                else: st.error("Usuário ou senha inválidos.")
        with aba2:
            nu = st.text_input("Novo Usuário").lower().strip()
            np = st.text_input("Nova Senha", type="password")
            # REMOVIDO O CAMPO WHATSAPP
            if st.button("Criar Conta"):
                if nu and np:
                    db.collection("usuarios").document(nu).set({'password': hash_pass(np)})
                    st.success("Conta criada com sucesso! Faça login na outra aba.")

    else:
        user = st.session_state.user
        st.sidebar.title(f"Bem-vindo, {user.capitalize()}!")
        if st.sidebar.button("Sair"): st.session_state.auth = False; st.rerun()

        docs = db.collection("usuarios").document(user).collection("figurinhas").stream()
        my_figs = {doc.id: doc.to_dict() for doc in docs}

        tab_album, tab_trocas, tab_chat = st.tabs(["🖼️ ÁLBUM", "🤝 TROCAS", "💬 MEU CHAT"])

        with tab_album:
            secao_sel = st.selectbox("Navegar por Seleção", LISTA_FINAL_ALBUM)
            c1, c2 = st.columns([0.8, 0.2])
            with c1: st.subheader(secao_sel)
            with c2:
                if secao_sel in BANDEIRAS:
                    st.image(f"https://flagcdn.com/w80/{BANDEIRAS[secao_sel]}.png", width=50)

            ids_da_secao = get_fig_ids(secao_sel)
            cols = st.columns(4)
            for idx, fid in enumerate(ids_da_secao):
                info = my_figs.get(fid, {"colada": False, "repetidas": 0})
                with cols[idx % 4]:
                    clase = "colada" if info['colada'] else "faltando"
                    rep_html = f'<div class="rep-badge">+{info["repetidas"]}</div>' if info["repetidas"] > 0 else ""
                    st.markdown(f'<div class="fig-card {clase}"><b>{fid}</b>{rep_html}</div>', unsafe_allow_html=True)
                    if st.button("✏️", key=fid, use_container_width=True):
                        st.session_state.edit = (fid, info['colada'], info['repetidas'])

        with tab_trocas:
            st.subheader("Central de Matches")
            
            # Gerar lista dinâmica de faltas baseada na nova ordem
            todas_figs = []
            for s in LISTA_FINAL_ALBUM: todas_figs.extend(get_fig_ids(s))
            
            minhas_faltas = [f for f in todas_figs if not my_figs.get(f, {}).get('colada', False)]
            minhas_reps = [fid for fid, info in my_figs.items() if info.get('repetidas', 0) > 0]
            
            matches = []
            for u in db.collection("usuarios").stream():
                if u.id == user: continue
                reps_parceiro = db.collection("usuarios").document(u.id).collection("figurinhas").where("repetidas", ">", 0).stream()
                for r in reps_parceiro:
                    if r.id in minhas_faltas:
                        matches.append({"Dono": u.id, "Figurinha": r.id, "Qtd": r.to_dict()['repetidas']})
            
            if matches:
                df = pd.DataFrame(matches)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.divider()
                parceiro = st.selectbox("Selecionar parceiro para proposta:", df['Dono'].unique())
                
                if parceiro:
                    p_figs = {doc.id: doc.to_dict() for doc in db.collection("usuarios").document(parceiro).collection("figurinhas").stream()}
                    interesses_dele = [f for f in minhas_reps if not p_figs.get(f, {}).get('colada', False)]
                    figs_dele = df[df['Dono'] == parceiro]['Figurinha'].tolist()

                    c1, c2 = st.columns(2)
                    with c1: st.info(f"**Ele tem pra você:**\n\n {', '.join(figs_dele)}")
                    with c2:
                        if interesses_dele: st.success(f"**Você tem pra ele:**\n\n {', '.join(interesses_dele)}")
                        else: st.warning("Você não tem repetidas que ele precise.")

                    msg_sugerida = f"Oi {parceiro}! Vi que você tem {', '.join(figs_dele)}. Eu tenho {', '.join(interesses_dele)} pra você. Bora trocar?"
                    txt_final = st.text_area("Mensagem:", value=msg_sugerida)
                    
                    if st.button("Enviar Proposta no App"):
                        db.collection("mensagens").add({'de': user, 'para': parceiro, 'texto': txt_final, 'timestamp': firestore.SERVER_TIMESTAMP})
                        st.success(f"✅ Mensagem enviada com sucesso para @{parceiro}!")
                        # REMOVIDA A FUNCIONALIDADE DE NOTIFICAR NO WHATSAPP
            else: st.info("Nenhuma troca disponível no momento.")

        with tab_chat:
            st.subheader("Caixa de Entrada")
            try:
                msgs = db.collection("mensagens").where("para", "==", user).order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
                found = False
                for m in msgs:
                    found = True
                    d = m.to_dict()
                    col_msg, col_del = st.columns([0.9, 0.1])
                    with col_msg:
                        st.markdown(f'<div class="msg-box"><b>De: @{d["de"]}</b><br>{d["texto"]}</div>', unsafe_allow_html=True)
                    with col_del:
                        if st.button("🗑️", key=f"del_{m.id}"):
                            db.collection("mensagens").document(m.id).delete()
                            st.rerun()
                if not found: st.info("Você não recebeu mensagens ainda.")
            except: st.warning("O chat está sendo indexado ou não há mensagens.")

        if 'edit' in st.session_state:
            with st.sidebar:
                st.divider()
                fid, col, rep = st.session_state.edit
                st.write(f"Editando: **{fid}**")
                nc = st.checkbox("Já colada?", value=col)
                nr = st.number_input("Qtd de Repetidas", min_value=0, value=int(rep))
                if st.button("Salvar"):
                    db.collection("usuarios").document(user).collection("figurinhas").document(fid).set({'colada': nc, 'repetidas': nr})
                    del st.session_state.edit; st.rerun()

if __name__ == "__main__":
    main()
