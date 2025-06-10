import pandas as pd # type: ignore
import numpy as np # type: ignore
from datetime import datetime, timedelta

def analisar_admissoes_recontratacoes(brasil_limpo, espanha_historico):
    brasil_limpo = brasil_limpo[brasil_limpo['status_empregado'] == 'Activo'].copy()
    expats_br_list = ['expaIn', 'expaOut']
    filtro_br_expat = brasil_limpo['expa_local'].isin(expats_br_list)
    expats_es_list = ['Expatriado entrante', 'Expatriado no oficial', 'Expatriado saliente']
    filtro_es_expat = espanha_historico['expa_local'].isin(expats_es_list)
    brasil_para_analise = brasil_limpo[~filtro_br_expat].copy()
    espanha_para_analise = espanha_historico[~filtro_es_expat].copy()
    lista_pendencias = []
    brasil_recente_para_novos = brasil_para_analise.sort_values('data_efetiva').drop_duplicates(subset='id_sistema_local', keep='last')
    df_merged_novos = pd.merge(brasil_recente_para_novos, espanha_para_analise[['id_sistema_local']].drop_duplicates(), on='id_sistema_local', how='left', indicator=True)
    novos_nao_encontrados = df_merged_novos[df_merged_novos['_merge'] == 'left_only'].copy()
    hoje = pd.to_datetime(datetime.now().date())
    data_limite_admissao = hoje - pd.Timedelta(days=7)
    pendencias_eve001 = novos_nao_encontrados[novos_nao_encontrados['data_admissao'] <= data_limite_admissao].copy()
    if not pendencias_eve001.empty:
        pendencias_eve001['evento_sugerido'] = 'EVE001 - Nova Contratação'
        lista_pendencias.append(pendencias_eve001)
    brasil_recente = brasil_para_analise.sort_values('data_efetiva').drop_duplicates(subset='id_sistema_local', keep='last')
    espanha_recente = espanha_para_analise.sort_values('data_efetiva').drop_duplicates(subset='id_sistema_local', keep='last')
    df_merged_status = pd.merge(brasil_recente, espanha_recente, on='id_sistema_local', suffixes=('_br', '_es'))
    if 'status_empregado_br' in df_merged_status.columns and 'status_empregado_es' in df_merged_status.columns:
        filtro_status = (df_merged_status['status_empregado_br'] == 'Activo') & (df_merged_status['status_empregado_es'] == 'Con terminación de contrato')
        pendencias_eve003_023 = df_merged_status[filtro_status].copy()
        if not pendencias_eve003_023.empty:
            pendencias_eve003_023['nome'] = pendencias_eve003_023['nome_br']
            pendencias_eve003_023['evento_sugerido'] = 'VERIFICAR: EVE003/023 - Ativo no BR, Terminado na ES'
            lista_pendencias.append(pendencias_eve003_023)
    if not lista_pendencias: return pd.DataFrame(), ""
    df_relatorio_final = pd.concat(lista_pendencias, ignore_index=True)
    colunas_relatorio_base = ['chapa', 'nome', 'data_admissao', 'evento_sugerido']
    colunas_existentes = [col for col in colunas_relatorio_base if col in df_relatorio_final.columns]
    for col in ['status_empregado_br', 'status_empregado_es']:
        if col in df_relatorio_final.columns: colunas_existentes.append(col)
    df_relatorio_final = df_relatorio_final[colunas_existentes].copy()
    df_relatorio_final.rename(columns={'status_empregado_br': 'status_brasil', 'status_empregado_es': 'status_espanha'}, inplace=True)
    if 'chapa' in df_relatorio_final.columns: df_relatorio_final['chapa'] = df_relatorio_final['chapa'].astype(str).str.split('.').str[0]
    chapas_eve001 = df_relatorio_final[df_relatorio_final['evento_sugerido'].str.contains('EVE001', na=False)]['chapa'].unique()
    chapas_verificar = df_relatorio_final[df_relatorio_final['evento_sugerido'].str.contains('VERIFICAR', na=False)]['chapa'].unique()
    conteudo_txt = []
    if chapas_eve001.size > 0:
        conteudo_txt.append("--------------EVE001------------")
        conteudo_txt.append(';'.join(chapas_eve001.astype(str)))
    if chapas_verificar.size > 0:
        if conteudo_txt: conteudo_txt.append("\n")
        conteudo_txt.append("---VERIFICAR: EVE003 ou EVE023---")
        conteudo_txt.append(';'.join(chapas_verificar.astype(str)))
    return df_relatorio_final, '\n'.join(conteudo_txt)

def analisar_divergencias_info(brasil_limpo, espanha_historico):
    brasil_limpo = brasil_limpo[brasil_limpo['status_empregado'] == 'Activo'].copy()
    espanha_ativos = espanha_historico[espanha_historico['status_empregado'] == 'Activo'].copy()
    brasil_limpo_recente = brasil_limpo.sort_values('data_efetiva', ascending=False).drop_duplicates('id_sistema_local')
    espanha_ativos_recente = espanha_ativos.sort_values('data_efetiva', ascending=False).drop_duplicates('id_sistema_local')
    df_merged = pd.merge(brasil_limpo_recente, espanha_ativos_recente, on='id_sistema_local', how='inner', suffixes=('_br', '_es'))
    if df_merged.empty: return pd.DataFrame(), ""
    colunas_para_comparar = ['cargo', 'categoria', 'familia', 'tipo_empregado', 'tipo_contrato', 'business_unit']
    df_relatorio_final = pd.DataFrame()
    for col in colunas_para_comparar:
        col_br, col_es = f"{col}_br", f"{col}_es"
        if col_br in df_merged.columns and col_es in df_merged.columns:
            divergencias = df_merged[df_merged[col_br] != df_merged[col_es]].copy()
            if not divergencias.empty:
                temp_df = divergencias[['id_sistema_local', 'chapa', 'nome_br', col_br, col_es]].copy()
                temp_df.rename(columns={'chapa':'chapa_brasil', 'nome_br': 'nome', col_br: 'valor_brasil', col_es: 'valor_espanha'}, inplace=True)
                temp_df['campo_divergente'] = col
                df_relatorio_final = pd.concat([df_relatorio_final, temp_df], ignore_index=True)
    if df_relatorio_final.empty: return pd.DataFrame(), ""
    df_relatorio_final['evento_sugerido'] = np.where(df_relatorio_final['campo_divergente'] == 'business_unit', 'EVE013', 'EVE012')
    df_relatorio_final['chapa_brasil'] = df_relatorio_final['chapa_brasil'].astype(str).str.split('.').str[0]
    chapas_012 = df_relatorio_final[df_relatorio_final['evento_sugerido'] == 'EVE012']['chapa_brasil'].unique()
    chapas_013 = df_relatorio_final[df_relatorio_final['evento_sugerido'] == 'EVE013']['chapa_brasil'].unique()
    txt = []
    if chapas_012.size > 0: txt.extend(["--------------EVE012------------", ';'.join(chapas_012)])
    if chapas_013.size > 0:
        if txt: txt.append("\n")
        txt.extend(["--------------EVE013------------", ';'.join(chapas_013)])
    return df_relatorio_final, "\n".join(txt)

def analisar_demissoes(brasil_limpo, espanha_historico):
    """
    Função atualizada para analisar demissões com a nova regra de negócio.
    Filtra por eventos de demissão no Brasil, verifica se o colaborador ainda está ativo na Espanha
    e se o pagamento da rescisão ocorreu há mais de 5 dias.
    """
    eventos_demissao = ['eve005', 'eve008', 'eve009', 'eve010', 'eve011', 'eve024', 'eve025', 'eve026', 'eve027']
    
    if 'dt_pagto_rescisao' not in brasil_limpo.columns:
        return pd.DataFrame({'Erro': ["A coluna 'DTPAGTORESCISAO' não foi encontrada na Base RM."]}), ""

    brasil_recente = brasil_limpo.sort_values('data_efetiva', ascending=False).drop_duplicates('id_sistema_local', keep='first')
    brasil_recente['evento_codigo'] = brasil_recente['motivo_evento'].astype(str).str.split('-').str[0].str.strip().str.lower()
    
    colaboradores_demitidos_br = brasil_recente[brasil_recente['evento_codigo'].isin(eventos_demissao)].copy()
    if colaboradores_demitidos_br.empty: return pd.DataFrame(), ""
        
    df_merged = pd.merge(
        colaboradores_demitidos_br,
        espanha_historico[['id_sistema_local', 'status_empregado']],
        on='id_sistema_local', how='left', suffixes=('_br', '_es')
    )
    
    pendencias_status = df_merged[df_merged['status_empregado_es'] == 'Activo'].copy()
    if pendencias_status.empty: return pd.DataFrame(), ""
        
    # --- NOVA REGRA DE NEGÓCIO APLICADA AQUI ---
    # Remove registros sem data de pagamento para evitar erros
    pendencias_status.dropna(subset=['dt_pagto_rescisao'], inplace=True)
    # Define a data limite: hoje - 5 dias
    data_limite = datetime.now() - timedelta(days=5)
    # Filtra apenas as rescisões pagas ANTES da data limite (ou seja, há mais de 5 dias)
    pendencias_finais = pendencias_status[pendencias_status['dt_pagto_rescisao'] < data_limite].copy()

    if pendencias_finais.empty: return pd.DataFrame(), ""

    df_relatorio = pendencias_finais.rename(columns={
        'chapa': 'chapa_brasil', 'nome': 'nome_completo', 'status_empregado_br': 'status_brasil',
        'status_empregado_es': 'status_espanha', 'motivo_evento': 'evento_demissao_brasil',
        'dt_pagto_rescisao': 'data_pagamento_rescisao'
    })
    
    df_relatorio = df_relatorio[[
        'id_sistema_local', 'chapa_brasil', 'nome_completo', 'status_brasil', 'status_espanha', 
        'evento_demissao_brasil', 'data_pagamento_rescisao'
    ]]
    
    chapas_para_envio = ';'.join(df_relatorio['chapa_brasil'].unique())
    conteudo_txt = "--------------DEMISSÕES (PAGTO > 5 DIAS)------------\n" + chapas_para_envio if chapas_para_envio else ""

    return df_relatorio, conteudo_txt