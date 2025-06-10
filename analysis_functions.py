import pandas as pd # type: ignore
import numpy as np # type: ignore
from datetime import datetime

def analisar_novos_colaboradores(brasil_limpo, espanha_historico):
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

def analisar_divergencias_cadastrais(brasil_limpo, espanha_historico):
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


def analisar_divergencias_eventos(brasil_bruto, espanha_bruto):
    brasil_df = brasil_bruto.copy()
    espanha_df = espanha_bruto.copy()
    
    mapeamento_local_espanha = {'ID de usuario/empleado': 'chapa'}
    if 'ID de usuario/empleado' in espanha_df.columns:
        espanha_df.rename(columns=mapeamento_local_espanha, inplace=True)
        
        # --- LINHA DE CORREÇÃO ADICIONADA AQUI ---
        # Garante que a nova coluna 'chapa' da Espanha seja do tipo texto, igual à do Brasil.
        espanha_df['chapa'] = espanha_df['chapa'].astype(str).str.replace(r'\\.0$', '', regex=True).str.strip()
    
    colunas_essenciais = ['chapa', 'data_efetiva', 'motivo_evento']
    for df_name, df in [('Brasil', brasil_df), ('Espanha', espanha_df)]:
        if not all(col in df.columns for col in colunas_essenciais):
            colunas_faltantes = [col for col in colunas_essenciais if col not in df.columns]
            return pd.DataFrame({'Erro': [f"Na base {df_name}, colunas essenciais não encontradas: {colunas_faltantes}"]}), ""
            
    eventos_excluidos = ['EVE001', 'EVE012', 'EVE013']
    dfs_processados = []
    for df in [brasil_df, espanha_df]:
        temp_df = df.copy()
        temp_df['evento_codigo'] = temp_df['motivo_evento'].astype(str).str.split('-').str[0].str.strip()
        temp_df.dropna(subset=['data_efetiva', 'chapa'], inplace=True)
        temp_df.sort_values('data_efetiva', ascending=False, inplace=True)
        temp_df.drop_duplicates(subset='chapa', keep='first', inplace=True)
        dfs_processados.append(temp_df)
        
    brasil_proc, espanha_proc = dfs_processados
    brasil_filtrado = brasil_proc[~brasil_proc['evento_codigo'].isin(eventos_excluidos)]
    espanha_filtrado = espanha_proc[~espanha_proc['evento_codigo'].isin(eventos_excluidos)]
    
    df_merged = pd.merge(
        brasil_filtrado[['chapa', 'nome', 'motivo_evento', 'evento_codigo']],
        espanha_filtrado[['chapa', 'motivo_evento', 'evento_codigo']],
        on='chapa',
        suffixes=('_br', '_es')
    )
    
    df_divergencias = df_merged[df_merged['evento_codigo_br'] != df_merged['evento_codigo_es']].copy()
    if df_divergencias.empty: return pd.DataFrame(), ""
    
    colunas_finais = {
        'chapa': 'chapa',
        'nome': 'nome_completo',
        'motivo_evento_br': 'evento_brasil',
        'motivo_evento_es': 'evento_espanha'
    }
    df_relatorio = df_divergencias[list(colunas_finais.keys())].rename(columns=colunas_finais)
    df_relatorio['chapa'] = df_relatorio['chapa'].astype(str).str.split('.').str[0]
    
    chapas_para_envio = ';'.join(df_relatorio['chapa'].unique())
    conteudo_txt = ""
    if chapas_para_envio:
        conteudo_txt = "--------------OUTROS EVENTOS------------\n" + chapas_para_envio
        
    return df_relatorio, conteudo_txt