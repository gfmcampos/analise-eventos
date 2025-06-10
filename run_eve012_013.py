import pandas as pd # type: ignore
import numpy as np # type: ignore
import os
from datetime import datetime
from core_processing import load_and_prepare_data

def run_analysis_divergencias():
    print("--- EXECUTANDO ANÁLISE EVE012 & EVE013 (DIVERGÊNCIAS) ---")
    agora = datetime.now()
    nome_pasta_saida = f"eve012_013_{agora.strftime('%d_%m_%y_%Hh%M')}"
    output_dir = os.path.join('output', nome_pasta_saida)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Diretório de saída para esta execução: '{output_dir}'")

    brasil_limpo, espanha_historico = load_and_prepare_data()

    if brasil_limpo is None or espanha_historico is None:
        print("Execução interrompida devido a erro na carga dos dados.")
        return

    espanha_ativos = espanha_historico[espanha_historico['status_empregado'] == 'Activo'].copy()
    
    print("\nRemovendo duplicados e mantendo apenas o registro mais recente por data efetiva...")
    
    if 'data_efetiva' not in brasil_limpo.columns or 'data_efetiva' not in espanha_ativos.columns:
        print("ERRO CRÍTICO: A coluna 'data_efetiva' é necessária para a análise, mas não foi encontrada em uma das bases.")
        return
        
    brasil_limpo = brasil_limpo.sort_values('data_efetiva').drop_duplicates(subset='id_sistema_local', keep='last')
    espanha_ativos = espanha_ativos.sort_values('data_efetiva').drop_duplicates(subset='id_sistema_local', keep='last')
    
    print(f"  - Registros únicos na base Brasil para análise: {brasil_limpo.shape[0]}")
    print(f"  - Registros únicos na base Espanha para análise: {espanha_ativos.shape[0]}")

    df_merged = pd.merge(
        brasil_limpo, 
        espanha_ativos, 
        on='id_sistema_local', 
        how='inner',
        suffixes=('_br', '_es')
    )

    colunas_para_comparar = [
        'cargo', 'familia', 'categoria', 'tipo_empregado', 
        'tipo_contrato', 'business_unit'
    ]

    colunas_comparaveis = [
        col for col in colunas_para_comparar
        if f'{col}_br' in df_merged.columns and f'{col}_es' in df_merged.columns
    ]
    
    if len(colunas_comparaveis) < len(colunas_para_comparar):
        colunas_ignoradas = set(colunas_para_comparar) - set(colunas_comparaveis)
        print(f"\nAVISO: As seguintes colunas serão ignoradas por não existirem em ambas as bases: {list(colunas_ignoradas)}")

    divergencias = []

    for index, row in df_merged.iterrows():
        for coluna in colunas_comparaveis:
            valor_br = row[f'{coluna}_br']
            valor_es = row[f'{coluna}_es']
            
            if pd.notna(valor_br) and pd.notna(valor_es) and valor_br != valor_es:
                divergencias.append({
                    'id_sistema_local': row['id_sistema_local'],
                    'chapa': row['chapa'],
                    'nome': row.get('nome_br', row.get('nome_es')),
                    'campo_divergente': coluna,
                    'valor_brasil': valor_br,
                    'valor_espanha': valor_es
                })

    if not divergencias:
        print("\nNenhuma divergência encontrada entre as bases Brasil e Espanha para as colunas analisadas.")
        return

    df_relatorio_final = pd.DataFrame(divergencias)
    df_relatorio_final['chapa'] = df_relatorio_final['chapa'].astype(str).str.split('.').str[0]
    df_relatorio_final['evento_sugerido'] = np.where(df_relatorio_final['campo_divergente'] == 'business_unit', 'eve013', 'eve012')

    print("\nPrévia do Relatório de Divergências:")
    print(df_relatorio_final.head())

    caminho_excel = os.path.join(output_dir, 'eve012_013_divergencias_detectadas.xlsx')
    df_relatorio_final.to_excel(caminho_excel, index=False)
    print(f"\n-> Relatório Excel gerado em: {caminho_excel}")
    
    chapas_eve012 = df_relatorio_final[df_relatorio_final['evento_sugerido'] == 'eve012']['chapa'].unique()
    chapas_eve013 = df_relatorio_final[df_relatorio_final['evento_sugerido'] == 'eve013']['chapa'].unique()

    conteudo_txt = []
    if chapas_eve012.size > 0:
        conteudo_txt.append("--------------EVE012------------")
        conteudo_txt.append(';'.join(chapas_eve012.astype(str)))
    if chapas_eve013.size > 0:
        if conteudo_txt: conteudo_txt.append("\n")
        conteudo_txt.append("--------------EVE013------------")
        conteudo_txt.append(';'.join(chapas_eve013.astype(str)))
        
    if conteudo_txt:
        caminho_txt = os.path.join(output_dir, 'chapas_eve012_013.txt')
        with open(caminho_txt, 'w', encoding='utf-8') as f:
            f.write('\n'.join(conteudo_txt))
        print(f"-> Arquivo TXT com chapas para EVE012/013 gerado em: {caminho_txt}")

if __name__ == '__main__':
    run_analysis_divergencias()