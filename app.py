import streamlit as st
import pandas as pd
import sqlite3
import hashlib

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Copa 2026 - Collector Pro", layout="wide", page_icon="⚽")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .fig-card {
        border: 2px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        background-color: white;
        margin-bottom: 10px;
    }
    .colada { background-color: #28a745 !important; color: white !important; border-color: #1e7e34 !important; }
    .faltando { background-color: #f8f9fa; color: #6c757d; }
    .rep-badge {
        background-color: #ffc107;
        color: black;
        border-radius: 50%;
        padding: 2px 7px;
        font-weight: bold;
        font-size: 0.8em;
        position: relative;
        top: -5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- LÓGICA DE BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('copa2026_v2.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (username TEXT PRIMARY KEY, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS figurinhas (username TEXT, id_fig TEXT, colada INTEGER, repetidas INTEGER, PRIMARY KEY(username, id_fig))')
    conn.commit()
    conn.close()

def hash_pass(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def update_sticker(user, fid, col, rep):
    conn = sqlite3.connect('copa2026_v2.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO figurinhas VALUES (?,?,?,?)', (user, fid, col, rep))
    conn.commit()
    conn.close()

# --- DEFINIÇÃO DAS SEÇÕES DO ÁLBUM ---
SECOES_ESPECIAIS = ["ESTÁDIOS", "MUSEU FIFA", "LENDAS", "CIDADES SEDE"]
SELECOES_2026 = [
    "Canadá", "México", "Estados Unidos", "Argentina", "Brasil", "Uruguai", "Colômbia", "Equador", "Paraguai",
    "Alemanha", "França", "Espanha", "Inglaterra", "Portugal", "Holanda", "Bélgica", "Itália", "Croácia", "Suíça", 
    "Dinamarca", "Sérvia", "Polônia", "Áustria", "Turquia", "Nigéria", "Egito", "Senegal", "Marrocos", "Argélia", 
    "Tunísia", "Costa do Marfim", "Camarões", "Mali", "Japão", "Coreia do Sul", "Austrália", "Arábia Saudita", 
    "Irã", "Iraque", "Uzbequistão", "Catar", "Panamá", "Costa Rica", "Jamaica", "Honduras", "Nova Zelândia"
]
TODAS_SECOES = SECOES_ESPECIAIS + SELECOES_2026
FIGS_POR_SECAO = 20 # Média de figurinhas por página

# --- INTERFACE PRINCIPAL ---
def main():
    init_db()
    if 'auth' not in st.session_state: st.session_state.auth = False

    # TELA DE ACESSO
    if not st.session_state.auth:
        st.title("⚽ Álbum Copa 2026")
        aba_log, aba_reg = st.tabs(["Login", "Cadastrar Nova Conta"])
        
        with aba_log:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                conn = sqlite3.connect('copa2026_v2.db')
                c = conn.cursor()
                c.execute('SELECT password FROM usuarios WHERE username=?', (u,))
                res = c.fetchone()
                if res and res[0] == hash_pass(p):
                    st.session_state.auth = True
                    st.session_state.user = u
                    st.rerun()
                else: st.error("Usuário ou senha incorretos.")

        with aba_reg:
            nu = st.text_input("Escolha um Usuário")
            np = st.text_input("Escolha uma Senha", type="password")
            if st.button("Criar Conta"):
                try:
                    conn = sqlite3.connect('copa2026_v2.db')
                    c = conn.cursor()
                    c.execute('INSERT INTO usuarios VALUES (?,?)', (nu, hash_pass(np)))
                    conn.commit()
                    st.success("Conta criada com sucesso! Vá para a aba Login.")
                except: st.error("Este nome de usuário já está em uso.")

    # APP LOGADO
    else:
        user = st.session_state.user
        st.sidebar.title(f"Cup 2026")
        st.sidebar.write(f"Usuário: **{user}**")
        if st.sidebar.button("Sair"):
            st.session_state.auth = False
            st.rerun()

        # Carregar dados do usuário logado
        conn = sqlite3.connect('copa2026_v2.db')
        df_user = pd.read_sql(f"SELECT * FROM figurinhas WHERE username='{user}'", conn)
        conn.close()

        menu = st.tabs(["🖼️ MODO ÁLBUM", "📋 MODO LISTA"])

        with menu[0]:
            secao = st.selectbox("Escolha a Página", TODAS_SECOES)
            st.divider()
            cols = st.columns(5)
            for i in range(1, FIGS_POR_SECAO + 1):
                fid = f"{secao[:3].upper()}-{i:02d}"
                row = df_user[df_user['id_fig'] == fid]
                c_val = row['colada'].values[0] == 1 if not row.empty else False
                r_val = int(row['repetidas'].values[0]) if not row.empty else 0
                
                with cols[(i-1)%5]:
                    clase = "colada" if c_val else "faltando"
                    rep_html = f'<span class="rep-badge">+{r_val}</span>' if r_val > 0 else ""
                    st.markdown(f'<div class="fig-card {clase}"><b>{fid}</b><br>{rep_html}</div>', unsafe_allow_html=True)
                    if st.button("Editar", key=fid):
                        st.session_state.edit = (fid, c_val, r_val)

        with menu[1]:
            st.subheader("Gerenciamento Rápido")
            # Filtro para a lista
            filtro = st.radio("Mostrar:", ["Todas", "Só Faltando", "Só Repetidas"], horizontal=True)
            
            lista_full = []
            for s in TODAS_SECOES:
                for i in range(1, FIGS_POR_SECAO + 1):
                    fid = f"{s[:3].upper()}-{i:02d}"
                    row = df_user[df_user['id_fig'] == fid]
                    colada = row['colada'].values[0] == 1 if not row.empty else False
                    reps = int(row['repetidas'].values[0]) if not row.empty else 0
                    
                    item = {"Seção": s, "ID": fid, "Status": "✅ Colada" if colada else "❌ Faltando", "Repetidas": reps}
                    
                    if filtro == "Só Faltando" and colada: continue
                    if filtro == "Só Repetidas" and reps == 0: continue
                    lista_full.append(item)
            
            st.dataframe(pd.DataFrame(lista_full), use_container_width=True, hide_index=True)

        # Painel lateral de edição (Ativado ao clicar em Editar no álbum)
        if 'edit' in st.session_state:
            with st.sidebar:
                st.divider()
                fid, col, rep = st.session_state.edit
                st.subheader(f"Atualizar {fid}")
                nc = st.checkbox("Já Colei!", value=col)
                nr = st.number_input("Qtd. Repetidas", min_value=0, value=rep)
                if st.button("Salvar Alterações"):
                    update_sticker(user, fid, 1 if nc else 0, nr)
                    del st.session_state.edit
                    st.rerun()
                if st.button("Cancelar"):
                    del st.session_state.edit
                    st.rerun()

if __name__ == "__main__":
    main()
