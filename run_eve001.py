import pandas as pd # type: ignore
import numpy as np # type: ignore
import os
from datetime import datetime
from core_processing import load_and_prepare_data

def run_analysis_novos_colaboradores():
    print("--- EXECUTANDO ANÁLISE EVE001, 003 e 023 ---")
    agora = datetime.now()
    nome_pasta_saida = f"eve001_003_023_{agora.strftime('%d_%m_%y_%Hh%M')}"
    output_dir = os.path.join('output', nome_pasta_saida)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Diretório de saída para esta execução: '{output_dir}'")

    brasil_limpo, espanha_historico = load_and_prepare_data()

    if brasil_limpo is None or espanha_historico is None:
        print("Execução interrompida devido a erro na carga dos dados.")
        return

    print("\nRegra 3: Removendo expatriados da análise...")
    
    expats_br_list = ['expaIn', 'expaOut']
    filtro_br_expat = brasil_limpo['expa_local'].isin(expats_br_list)
    
    expats_es_list = ['Expatriado entrante', 'Expatriado no oficial', 'Expatriado saliente']
    filtro_es_expat = espanha_historico['expa_local'].isin(expats_es_list)

    brasil_para_analise = brasil_limpo[~filtro_br_expat].copy()
    espanha_para_analise = espanha_historico[~filtro_es_expat].copy()
    print(f"  - Análise seguirá com {len(brasil_para_analise)} registros do Brasil e {len(espanha_para_analise)} da Espanha.")

    lista_pendencias = []

    print("\nRegra 1: Verificando novas contratações (EVE001)...")
    brasil_recente_para_novos = brasil_para_analise.sort_values('data_efetiva').drop_duplicates(subset='id_sistema_local', keep='last')
    
    df_merged_novos = pd.merge(brasil_recente_para_novos, espanha_para_analise[['id_sistema_local']].drop_duplicates(), on='id_sistema_local', how='left', indicator=True)
    novos_nao_encontrados = df_merged_novos[df_merged_novos['_merge'] == 'left_only'].copy()

    hoje = pd.to_datetime(datetime.now().date())
    data_limite_admissao = hoje - pd.Timedelta(days=7)
    
    pendencias_eve001 = novos_nao_encontrados[novos_nao_encontrados['data_admissao'] <= data_limite_admissao].copy()
    pendencias_eve001['evento_sugerido'] = 'EVE001 - Nova Contratação'
    lista_pendencias.append(pendencias_eve001)
    print(f"  - {len(pendencias_eve001)} pendências de EVE001 encontradas.")

    print("\nRegra 2: Verificando divergência de status (EVE003/023)...")
    brasil_recente = brasil_para_analise.sort_values('data_efetiva').drop_duplicates(subset='id_sistema_local', keep='last')
    espanha_recente = espanha_para_analise.sort_values('data_efetiva').drop_duplicates(subset='id_sistema_local', keep='last')

    df_merged_status = pd.merge(brasil_recente, espanha_recente, on='id_sistema_local', suffixes=('_br', '_es'))
    
    filtro_status = (df_merged_status['status_empregado_br'] == 'Activo') & (df_merged_status['status_empregado_es'] == 'Con terminación de contrato')
    pendencias_eve003_023 = df_merged_status[filtro_status].copy()

    pendencias_eve003_023['nome'] = pendencias_eve003_023['nome_br']
    
    pendencias_eve003_023['evento_sugerido'] = 'VERIFICAR: EVE003/023 - Ativo no BR, Terminado na ES'
    lista_pendencias.append(pendencias_eve003_023)
    print(f"  - {len(pendencias_eve003_023)} pendências de EVE003/023 encontradas.")

    if not lista_pendencias:
        print("\nNenhuma pendência encontrada. Análise concluída.")
        return

    df_relatorio_final = pd.concat(lista_pendencias, ignore_index=True)

    colunas_relatorio = ['chapa', 'nome', 'data_admissao', 'evento_sugerido']
    for col in ['status_empregado_br', 'status_empregado_es']:
        if col in df_relatorio_final.columns and col not in colunas_relatorio:
            colunas_relatorio.append(col)

    df_relatorio_final = df_relatorio_final[colunas_relatorio].copy()
    df_relatorio_final.rename(columns={'status_empregado_br': 'status_brasil', 'status_empregado_es': 'status_espanha'}, inplace=True)
    df_relatorio_final['chapa'] = df_relatorio_final['chapa'].astype(str).str.split('.').str[0]

    print("\nPrévia do Relatório de Pendências:")
    print(df_relatorio_final.head())

    caminho_excel = os.path.join(output_dir, 'eve001_003_023_pendencias.xlsx')
    df_relatorio_final.to_excel(caminho_excel, index=False)
    print(f"\n-> Relatório Excel gerado em: {caminho_excel}")

    chapas_eve001 = df_relatorio_final[df_relatorio_final['evento_sugerido'].str.contains('EVE001')]['chapa'].unique()
    chapas_verificar = df_relatorio_final[df_relatorio_final['evento_sugerido'].str.contains('VERIFICAR')]['chapa'].unique()

    conteudo_txt = []
    if chapas_eve001.size > 0:
        conteudo_txt.append("--------------EVE001------------")
        conteudo_txt.append(';'.join(chapas_eve001.astype(str)))
    if chapas_verificar.size > 0:
        if conteudo_txt: conteudo_txt.append("\n")
        conteudo_txt.append("---VERIFICAR: EVE003 ou EVE023---")
        conteudo_txt.append(';'.join(chapas_verificar.astype(str)))
        
    if conteudo_txt:
        caminho_txt = os.path.join(output_dir, 'chapas_eve001_003_023.txt')
        with open(caminho_txt, 'w', encoding='utf-8') as f:
            f.write('\n'.join(conteudo_txt))
        print(f"-> Arquivo TXT com chapas para EVE001/003/023 gerado em: {caminho_txt}")

if __name__ == '__main__':
    run_analysis_novos_colaboradores()