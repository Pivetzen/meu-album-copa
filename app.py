import streamlit as st
import pandas as pd
import hashlib
import firebase_admin
import json
import unicodedata
from firebase_admin import credentials, firestore
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Collector 2026 Pro", layout="wide", page_icon="⚽")

# --- INICIALIZAÇÃO DO FIREBASE ---
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            fb_dict = dict(st.secrets["firebase_credentials"])
            if "private_key" in fb_dict:
                fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n")
            
            cred = credentials.Certificate(fb_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro ao carregar Firebase: {e}")
            return None
    return firestore.client()

db = init_firebase()

# --- MAPEAMENTO DE DADOS ---
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

# --- FUNÇÃO DE PDF ---
def gerar_pdf_faltantes(user_name, my_figs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Collector 2026 Pro - Lista de Faltas", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Usuario: {user_name}", ln=True, align="C")
    pdf.ln(5)

    for secao in LISTA_FINAL_ALBUM:
        ids_secao = get_fig_ids(secao)
        faltantes = [fid for fid in ids_secao if not my_figs.get(fid, {}).get('colada', False)]
        if faltantes:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(240, 240, 240)
            # Normalização para garantir que caracteres especiais não quebrem o PDF
            secao_limpa = unicodedata.normalize('NFKD', secao).encode('ascii', 'ignore').decode('ascii')
            pdf.cell(0, 8, f" {secao_limpa}", ln=True, fill=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 7, ", ".join(faltantes))
            pdf.ln(2)
    
    # Retorna o PDF como bytes compatíveis com st.download_button
    return pdf.output()

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .fig-card { border: 2px solid #ddd; border-radius: 10px; padding: 10px; text-align: center; background-color: white; margin-bottom: 5px; position: relative; min-height: 80px; display: flex; align-items: center; justify-content: center; flex-direction: column; }
    .colada { background-color: #1b5e20 !important; color: white !important; border-color: #003300 !important; }
    .faltando { background-color: #f1f3f4; color: #5f6368; }
    .rep-badge { background-color: #ffd600; color: black; border-radius: 50%; padding: 2px 7px; font-weight: bold; font-size: 0.8em; position: absolute; top: 5px; right: 5px; }
    .msg-box { background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 5px; border-left: 5px solid #25D366; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .stProgress > div > div > div > div { background-color: #1b5e20; }
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
            if st.button("Entrar", use_container_width=True):
                if db:
                    res = db.collection("usuarios").document(u).get()
                    if res.exists and res.to_dict()['password'] == hash_pass(p):
                        st.session_state.auth = True; st.session_state.user = u; st.rerun()
                    else: st.error("Usuário ou senha inválidos.")
                else: st.error("Firebase não inicializado.")
        with aba2:
            nu = st.text_input("Novo Usuário").lower().strip()
            np = st.text_input("Nova Senha", type="password")
            if st.button("Criar Conta", use_container_width=True):
                if nu and np and db:
                    db.collection("usuarios").document(nu).set({'password': hash_pass(np)})
                    st.success("Conta criada! Faça login.")

    else:
        user = st.session_state.user
        st.sidebar.title(f"👋 Olá, {user.capitalize()}!")
        
        # Carregamento de dados
        docs = db.collection("usuarios").document(user).collection("figurinhas").stream()
        my_figs = {doc.id: doc.to_dict() for doc in docs}
        
        # Estatísticas Globais
        total_album = sum(len(get_fig_ids(s)) for s in LISTA_FINAL_ALBUM)
        coladas_total = sum(1 for f in my_figs.values() if f.get('colada'))
        reps_total = sum(f.get('repetidas', 0) for f in my_figs.values())
        progresso_global = coladas_total / total_album if total_album > 0 else 0

        # Sidebar Stats
        st.sidebar.subheader("📊 Seu Progresso")
        st.sidebar.write(f"Figurinhas: **{coladas_total} / {total_album}**")
        st.sidebar.write(f"Repetidas: **{reps_total}**")
        st.sidebar.progress(progresso_global)

        # Exportar PDF
        try:
            pdf_bytes = gerar_pdf_faltantes(user, my_figs)
            st.sidebar.download_button(
                label="📄 Exportar Lista de Faltas (PDF)",
                data=pdf_bytes,
                file_name=f"faltas_{user}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception:
            st.sidebar.error("Erro ao preparar PDF")

        if st.sidebar.button("Sair", use_container_width=True): 
            st.session_state.auth = False
            st.rerun()

        tab_album, tab_trocas, tab_chat = st.tabs(["🖼️ ÁLBUM", "🤝 TROCAS", "💬 MEU CHAT"])

        with tab_album:
            col_filt1, col_filt2 = st.columns([0.7, 0.3])
            with col_filt1:
                secao_sel = st.selectbox("Navegar por Seleção", LISTA_FINAL_ALBUM)
            with col_filt2:
                filtro_view = st.radio("Visualizar:", ["Todas", "Faltantes", "Repetidas"], horizontal=True)

            ids_da_secao = get_fig_ids(secao_sel)
            
            # Filtro Lógico
            ids_filtrados = []
            for fid in ids_da_secao:
                info = my_figs.get(fid, {"colada": False, "repetidas": 0})
                if filtro_view == "Faltantes" and info['colada']: continue
                if filtro_view == "Repetidas" and info['repetidas'] == 0: continue
                ids_filtrados.append((fid, info))

            # Header da Seção
            c1, c2 = st.columns([0.85, 0.15])
            with c1: 
                coladas_secao = sum(1 for fid, info in ids_filtrados if info['colada'])
                st.subheader(f"{secao_sel} ({coladas_secao}/{len(ids_da_secao)})")
            with c2:
                if secao_sel in BANDEIRAS:
                    st.image(f"https://flagcdn.com/w80/{BANDEIRAS[secao_sel]}.png", width=50)

            # Grid de Figurinhas
            if not ids_filtrados:
                st.info("Nenhuma figurinha corresponde ao filtro nesta seção.")
            else:
                cols = st.columns(4)
                for idx, (fid, info) in enumerate(ids_filtrados):
                    with cols[idx % 4]:
                        clase = "colada" if info['colada'] else "faltando"
                        rep_html = f'<div class="rep-badge">+{info["repetidas"]}</div>' if info["repetidas"] > 0 else ""
                        st.markdown(f'''
                            <div class="fig-card {clase}">
                                <b>{fid}</b>
                                {rep_html}
                            </div>
                        ''', unsafe_allow_html=True)
                        if st.button("✏️", key=f"btn_{fid}", use_container_width=True):
                            st.session_state.edit = (fid, info['colada'], info['repetidas'])

        with tab_trocas:
            st.subheader("🤝 Central de Matches")
            todas_figs = [f for s in LISTA_FINAL_ALBUM for f in get_fig_ids(s)]
            minhas_faltas = [f for f in todas_figs if not my_figs.get(f, {}).get('colada', False)]
            minhas_reps = [fid for fid, info in my_figs.items() if info.get('repetidas', 0) > 0]
            
            matches = []
            usuarios_ref = db.collection("usuarios").stream()
            for u in usuarios_ref:
                if u.id == user: continue
                reps_p = db.collection("usuarios").document(u.id).collection("figurinhas").where("repetidas", ">", 0).stream()
                for r in reps_p:
                    if r.id in minhas_faltas:
                        matches.append({"Dono": u.id, "Figurinha": r.id, "Qtd": r.to_dict()['repetidas']})
            
            if matches:
                df = pd.DataFrame(matches)
                st.dataframe(df, use_container_width=True, hide_index=True)
                parceiro = st.selectbox("Deseja propor troca para:", df['Dono'].unique())
                if parceiro:
                    p_figs_docs = db.collection("usuarios").document(parceiro).collection("figurinhas").stream()
                    p_figs = {d.id: d.to_dict() for d in p_figs_docs}
                    dele = df[df['Dono'] == parceiro]['Figurinha'].tolist()
                    meu = [f for f in minhas_reps if not p_figs.get(f, {}).get('colada', False)]
                    
                    st.info(f"**Ele tem o que você precisa:** {', '.join(dele)}")
                    if meu: 
                        st.success(f"**Você tem o que ele precisa:** {', '.join(meu)}")
                        if st.button("Enviar Proposta via Chat", use_container_width=True):
                            txt = f"Olá {parceiro}! Vi que você tem {', '.join(dele)} repetidas. Eu tenho {', '.join(meu)} que você não tem. Topa trocar?"
                            db.collection("mensagens").add({
                                'de': user, 'para': parceiro, 'texto': txt, 'timestamp': firestore.SERVER_TIMESTAMP
                            })
                            st.success("Proposta enviada!")
                    else:
                        st.warning("Ele tem o que você precisa, mas você não tem repetidas que faltam para ele no momento.")
            else:
                st.info("Nenhum match automático encontrado. Continue atualizando seu álbum!")

        with tab_chat:
            st.subheader("💬 Suas Mensagens")
            try:
                msgs = db.collection("mensagens").where("para", "==", user).order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
                found_msg = False
                for m in msgs:
                    found_msg = True
                    d = m.to_dict()
                    col_m1, col_m2 = st.columns([0.85, 0.15])
                    with col_m1:
                        st.markdown(f'<div class="msg-box"><b>@{d["de"]}</b>: {d["texto"]}</div>', unsafe_allow_html=True)
                    with col_m2:
                        if st.button("🗑️", key=f"del_{m.id}"):
                            db.collection("mensagens").document(m.id).delete()
                            st.rerun()
                if not found_msg: st.info("Sua caixa de entrada está vazia.")
            except:
                st.info("Sua caixa de entrada está vazia ou ainda não possui mensagens.")

        # Modal de Edição na Sidebar
        if 'edit' in st.session_state:
            with st.sidebar:
                st.markdown("---")
                fid, col, rep = st.session_state.edit
                st.write(f"⚙️ Editando: **{fid}**")
                nc = st.checkbox("Já colada no álbum?", value=col)
                nr = st.number_input("Quantidade de repetidas", min_value=0, value=int(rep))
                
                c_edit1, c_edit2 = st.columns(2)
                with c_edit1:
                    if st.button("Salvar", use_container_width=True, type="primary"):
                        db.collection("usuarios").document(user).collection("figurinhas").document(fid).set({'colada': nc, 'repetidas': nr})
                        del st.session_state.edit
                        st.rerun()
                with c_edit2:
                    if st.button("Cancelar", use_container_width=True):
                        del st.session_state.edit
                        st.rerun()

if __name__ == "__main__":
    main()
