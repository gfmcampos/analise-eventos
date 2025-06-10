import streamlit as st # type: ignore
import pandas as pd # type: ignore
from io import BytesIO
from datetime import datetime
from core_processing import load_and_prepare_data
from analysis_functions import analisar_admissoes_recontratacoes, analisar_divergencias_info, analisar_demissoes

st.set_page_config(
    layout="wide",
    page_title="Análise de Colaboradores",
    initial_sidebar_state="expanded"
)

st.title("🔎 Ferramenta de Análise de Sincronia de Colaboradores")

with st.sidebar:
    st.image("imgs/login_logo.png", width=250)
    st.header("Painel de Controle")

    # Menu de análises com novos nomes e captions
    menu_selecao = st.radio(
        "**Menu de análises:**",
        options=["Página inicial", "Admissões & Recontratações", "Informações pessoais & Informações de cargo", "Demissões"],
        captions=["Visão geral", "Eventos EVE001 e EVE003", "Eventos EVE012 e EVE013", "Eventos de desligamento"]
    )

    with st.expander("🎨 Mudar o Tema"):
        st.write("""
        Para alternar entre o modo claro e escuro:
        1. Clique no menu **☰** no canto superior direito da tela.
        2. Clique em **Settings**.
        3. Na seção **Theme**, escolha entre 'Light' (Claro) e 'Dark' (Escuro).
        """)
    st.info("Desenvolvido por SF Teste - Junho/2025")

@st.cache_data
def carregar_dados_wrapper():
    return load_and_prepare_data()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

if menu_selecao == "Página inicial":
    st.header("Bem-vindo(a) à sua ferramenta de análise integrada!", divider='rainbow')
    st.markdown("Esta plataforma foi desenhada para simplificar e automatizar a validação de dados de colaboradores entre as bases do Brasil e da Espanha.")
    st.subheader("O que você pode fazer aqui?")
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown("##### 🚀 Admissões e Recontratações")
            st.write("Verifique novos colaboradores e reativações que precisam ser sincronizados com a Espanha.")
    with col2:
        with st.container(border=True):
            st.markdown("##### ✏️ Informações Pessoais e de Cargo")
            st.write("Compare campos-chave como cargo e categoria para garantir consistência entre as bases.")
    with col3:
        with st.container(border=True):
            st.markdown("##### 👋 Demissões")
            st.write("Identifique colaboradores desligados no Brasil que ainda constam como ativos na Espanha.")

else:
    brasil_df, espanha_df = carregar_dados_wrapper()
    if brasil_df is None or espanha_df is None:
        st.error("Falha Crítica ao carregar os dados. Verifique os arquivos na pasta 'data'.")
    else:
        agora = datetime.now().strftime('%d%m%Y_%H%M')
        df_relatorio, txt_content, filename_base, header, metrica_label = pd.DataFrame(), "", "", "", ""

        with st.spinner("Executando análise... Por favor, aguarde."):
            if menu_selecao == "Admissões & Recontratações":
                header, metrica_label = "Admissões & Recontratações", "Total de Pendências"
                df_relatorio, txt_content = analisar_admissoes_recontratacoes(brasil_df, espanha_df)
                filename_base = f"Admissoes_Recontratacoes_{agora}"
            
            elif menu_selecao == "Informações pessoais & Informações de cargo":
                header, metrica_label = "Divergências de Informações Pessoais e de Cargo", "Total de Divergências"
                df_relatorio, txt_content = analisar_divergencias_info(brasil_df, espanha_df)
                filename_base = f"Divergencias_Info_{agora}"

            elif menu_selecao == "Demissões":
                header, metrica_label = "Pendências de Demissão", "Total de Pendências"
                df_relatorio, txt_content = analisar_demissoes(brasil_df, espanha_df)
                filename_base = f"Pendencias_Demissao_{agora}"

        st.header(header, divider='rainbow')
        if "Erro" in df_relatorio.columns:
            st.error(df_relatorio["Erro"].iloc[0])
        elif df_relatorio.empty:
            st.success("✅ Nenhuma pendência ou divergência encontrada.")
        else:
            with st.container(border=True):
                col1, col2 = st.columns([0.3, 0.7])
                with col1:
                    st.metric(metrica_label, value=len(df_relatorio))
                with col2:
                    st.write("")
                    btn1, btn2 = st.columns(2)
                    btn1.download_button("📥 Baixar Relatório (.xlsx)", to_excel(df_relatorio), f"{filename_base}.xlsx", use_container_width=True)
                    btn2.download_button("📥 Baixar Chapas (.txt)", txt_content, f"{filename_base}.txt", use_container_width=True)
            st.dataframe(df_relatorio, use_container_width=True)