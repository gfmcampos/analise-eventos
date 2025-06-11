import streamlit as st # type: ignore
import pandas as pd # type: ignore
import plotly.express as px # type: ignore
from io import BytesIO
from datetime import datetime
import textwrap

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
    st.info("Desenvolvido por guilherme.campos")

@st.cache_data
def carregar_dados_wrapper():
    return load_and_prepare_data()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

def wrap_labels(labels, width=20):
    return [ '<br>'.join(textwrap.wrap(str(label), width=width)) for label in labels ]

# --- LÓGICA DE EXIBIÇÃO DAS PÁGINAS ---

brasil_df, espanha_df = carregar_dados_wrapper()

if menu_selecao == "Página inicial":
    st.header("Dashboard Geral de Pendências", divider='rainbow')

    if brasil_df is None or espanha_df is None:
        st.error("Falha Crítica ao carregar os dados. Verifique os arquivos na pasta 'data'.")
    else:
        with st.spinner("Calculando totais de pendências..."):
            df_admissoes, _ = analisar_admissoes_recontratacoes(brasil_df, espanha_df)
            df_divergencias, _ = analisar_divergencias_info(brasil_df, espanha_df)
            df_demissoes, _ = analisar_demissoes(brasil_df, espanha_df)

        total_admissoes = len(df_admissoes)
        total_divergencias = len(df_divergencias)
        total_demissoes = len(df_demissoes)
        total_pendencias = total_admissoes + total_divergencias + total_demissoes

        st.subheader("Resumo Geral")
        cols = st.columns(4)
        cols[0].metric("Total de Pendências", f"{total_pendencias}")
        cols[1].metric("Admissões / Recontratações", f"{total_admissoes}")
        cols[2].metric("Divergências de Cadastro", f"{total_divergencias}")
        cols[3].metric("Pendências de Demissão", f"{total_demissoes}")
        
        st.subheader("Distribuição das Pendências")
        col1, col2 = st.columns([0.4, 0.6])

        with col1:
            summary_data = {
                'Tipo de Análise': ['Admissões & Recontratações', 'Info. Pessoais & Cargo', 'Demissões'],
                'Quantidade': [total_admissoes, total_divergencias, total_demissoes]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary = df_summary[df_summary['Quantidade'] > 0]

            if not df_summary.empty:
                fig = px.pie(df_summary, names='Tipo de Análise', values='Quantidade', hole=0.5,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05, 0.05, 0.05])
                fig.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("🎉 Ótima notícia! Nenhuma pendência encontrada em todas as análises.")
        
        with col2:
             st.markdown("""
            Esta plataforma foi desenhada para simplificar e automatizar a validação de dados de colaboradores entre as bases do Brasil e da Espanha.
            Navegue pelo **Menu de Análises** na barra lateral para executar as validações necessárias para cada caso.
            
            - **Admissões & Recontratações:** Verifica novos colaboradores e reativações.
            - **Informações Pessoais & de Cargo:** Compara campos-chave para garantir consistência.
            - **Demissões:** Identifica colaboradores desligados no Brasil que ainda constam como ativos na Espanha.
            """)
else:
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
            st.subheader("📊 Dashboard Interativo")
            with st.container(border=True):
                df_chart, fig = pd.DataFrame(), None
                x_axis, y_axis, color, filter_col = None, None, None, None
                
                # --- LÓGICA RESTAURADA PARA DEFINIR filter_col ---
                if menu_selecao == "Admissões & Recontratações":
                    df_chart, x_axis, y_axis, color, filter_col = df_relatorio['evento_sugerido'].value_counts().reset_index(), "evento_sugerido", "count", "#0083B8", "evento_sugerido"
                elif menu_selecao == "Informações pessoais & Informações de cargo":
                    df_chart, x_axis, y_axis, color, filter_col = df_relatorio['campo_divergente'].value_counts().reset_index(), "campo_divergente", "count", "#FF6347", "campo_divergente"
                elif menu_selecao == "Demissões":
                    df_chart, x_axis, y_axis, color, filter_col = df_relatorio['evento_demissao_brasil'].value_counts().reset_index(), "evento_demissao_brasil", "count", "#4B0082", "evento_demissao_brasil"
                
                if not df_chart.empty:
                    total_registros = df_chart[y_axis].sum()
                    df_chart['percentage_label'] = (df_chart[y_axis] / total_registros).map('{:.1%}'.format)
                    df_chart[x_axis] = wrap_labels(df_chart[x_axis])
                    fig = px.bar(df_chart, x=x_axis, y=y_axis, text='percentage_label', color_discrete_sequence=[color])
                    fig.update_layout(
                        xaxis_title=None, yaxis_visible=False, bargap=0.4, plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)', xaxis_tickangle=0, uniformtext_minsize=12,
                        hovermode=False, dragmode=False
                    )
                    fig.update_traces(textfont_size=16, textposition="outside", cliponaxis=False)
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            st.subheader("📄 Relatório Detalhado")
            opcoes_filtro = ['Mostrar Todos'] + df_relatorio[filter_col].unique().tolist()
            filtro_selecionado = st.selectbox("Filtrar relatório por categoria:", options=opcoes_filtro)
            
            df_to_show = df_relatorio
            if filtro_selecionado != 'Mostrar Todos':
                df_to_show = df_relatorio[df_relatorio[filter_col] == filtro_selecionado].copy()

            with st.container(border=True):
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    st.metric(label=metrica_label, value=f"{len(df_to_show)}", delta=f"de {len(df_relatorio)} no total", delta_color="off")
                with col2:
                    st.write("")
                    btn1, btn2 = st.columns(2)
                    btn1.download_button("📥 Baixar Relatório (.xlsx)", to_excel(df_to_show), f"{filename_base}_filtrado.xlsx", use_container_width=True)
                    btn2.download_button("📥 Baixar Chapas (.txt)", txt_content, f"{filename_base}.txt", use_container_width=True)
            
            st.dataframe(df_to_show, use_container_width=True)