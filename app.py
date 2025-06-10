import streamlit as st # type: ignore
import pandas as pd # type: ignore
from io import BytesIO
from datetime import datetime
from core_processing import load_and_prepare_data
from analysis_functions import analisar_novos_colaboradores, analisar_divergencias_cadastrais, analisar_divergencias_eventos

st.set_page_config(layout="wide", page_title="Análise de Colaboradores BR x ES")

@st.cache_data
def carregar_dados_wrapper():
    """Chama sua função de carregar dados e a guarda em cache."""
    return load_and_prepare_data()

def to_excel(df):
    """Converte um dataframe para download em Excel."""
    output = BytesIO()
    # A instalação da biblioteca 'xlsxwriter' é necessária
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

st.title("🔎 Ferramenta de Análise de Sincronia de Colaboradores")
st.markdown("**Origem:** Brasil | **Destino:** Espanha")

st.sidebar.header("Menu de Análises")
menu_selecao = st.sidebar.radio(
    "Escolha a análise:",
    ("Página Inicial", "Novos Colaboradores (EVE001/003)", "Divergências Cadastrais (EVE012/013)", "Divergências de Eventos")
)

# Página Inicial (sem processamento)
if menu_selecao == "Página Inicial":
    st.header("Bem-vindo(a)!")
    st.markdown("Esta aplicação automatiza a validação de dados de colaboradores entre as bases do Brasil e da Espanha.")
    st.info("Selecione uma análise no menu ao lado para começar.")

# Bloco de Análises (executa somente a análise selecionada)
else:
    brasil_df, espanha_df = carregar_dados_wrapper()
    
    if brasil_df is None or espanha_df is None:
        st.error("Falha Crítica ao carregar os dados. Verifique os arquivos na pasta 'data' e o terminal para mais detalhes.")
    else:
        agora = datetime.now().strftime('%d%m%Y_%H%M')
        df_relatorio, txt_content = pd.DataFrame(), ""
        filename_base = ""
        header = ""

        with st.spinner("Executando análise..."):
            if menu_selecao == "Novos Colaboradores (EVE001/003)":
                header = "Análise de Novos Colaboradores e Reativações"
                df_relatorio, txt_content = analisar_novos_colaboradores(brasil_df, espanha_df)
                filename_base = f"EVE001_003_pendencias_{agora}"
            
            elif menu_selecao == "Divergências Cadastrais (EVE012/013)":
                header = "Análise de Divergências Cadastrais"
                df_relatorio, txt_content = analisar_divergencias_cadastrais(brasil_df, espanha_df)
                filename_base = f"EVE012_013_divergencias_{agora}"

            elif menu_selecao == "Divergências de Eventos":
                header = "Análise de Divergências de Motivo de Evento"
                df_relatorio, txt_content = analisar_divergencias_eventos(brasil_df, espanha_df)
                filename_base = f"Divergencia_Eventos_{agora}"

        st.header(header)
        if "Erro" in df_relatorio.columns:
            st.error(df_relatorio["Erro"].iloc[0])
        elif df_relatorio.empty:
            st.success("✅ Nenhuma pendência ou divergência encontrada.")
        else:
            st.metric("Total de Registros Encontrados", value=len(df_relatorio))
            col1, col2 = st.columns(2)
            col1.download_button("📥 Baixar Relatório (.xlsx)", to_excel(df_relatorio), f"{filename_base}.xlsx")
            col2.download_button("📥 Baixar Chapas (.txt)", txt_content, f"{filename_base}.txt")
            st.dataframe(df_relatorio)