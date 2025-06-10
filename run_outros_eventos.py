import pandas as pd # type: ignore
import os
from datetime import datetime
from core_processing import load_and_prepare_data

def run_analysis_outros_eventos():
    print("--- EXECUTANDO ANÁLISE GERAL DE DIVERGÊNCIA DE EVENTOS ---")
    agora = datetime.now()
    nome_pasta_saida = f"outros_eventos_{agora.strftime('%d_%m_%y_%Hh%M')}"
    output_dir = os.path.join('output', nome_pasta_saida)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Diretório de saída para esta execução: '{output_dir}'")

    brasil_bruto, espanha_bruto = load_and_prepare_data()

    if brasil_bruto is None or espanha_bruto is None:
        print("Execução interrompida devido a erro na carga dos dados.")
        return

    mapeamento_local_espanha = {
        'ID de usuario/empleado': 'chapa'
    }
    colunas_para_renomear_es = {k: v for k, v in mapeamento_local_espanha.items() if k in espanha_bruto.columns}
    if colunas_para_renomear_es:
        espanha_bruto.rename(columns=colunas_para_renomear_es, inplace=True)
        print("\n--- AJUSTE LOCAL: Coluna 'chapa' criada para a base Espanha. ---")

    # 2. Ajuste para a base do Brasil: Garante que a coluna 'nome' exista,
    #    criando-a a partir de 'nome_parcial' e 'sobrenome' se necessário.
    if 'nome' not in brasil_bruto.columns and 'nome_parcial' in brasil_bruto.columns:
        brasil_bruto['nome'] = brasil_bruto['nome_parcial'].fillna('') + ' ' + brasil_bruto['sobrenome'].fillna('')
        brasil_bruto['nome'] = brasil_bruto['nome'].str.strip()
        print("--- AJUSTE LOCAL: Coluna 'nome' criada para a base Brasil. ---")
    # --- FIM DO BLOCO DE AJUSTE LOCAL ---

    colunas_essenciais = ['chapa', 'nome', 'data_efetiva', 'motivo_evento']
    for df_name, df in [('Brasil', brasil_bruto), ('Espanha', espanha_bruto)]:
        if not all(col in df.columns for col in colunas_essenciais):
            print(f"\nERRO CRÍTICO: Colunas essenciais não encontradas na base {df_name} após padronização.")
            print(f"Colunas disponíveis: {df.columns.tolist()}")
            print("Verifique os nomes das colunas na planilha original ou o mapeamento local neste script.")
            return

    eventos_excluidos = ['EVE001', 'EVE012', 'EVE013']
    print(f"\nExcluindo eventos predefinidos da análise: {eventos_excluidos}")

    for df in [brasil_bruto, espanha_bruto]:
        df['evento_codigo'] = df['motivo_evento'].astype(str).str.split('-').str[0].str.strip()
        df.dropna(subset=['data_efetiva', 'chapa'], inplace=True)
        df.sort_values('data_efetiva', ascending=False, inplace=True)
        df.drop_duplicates(subset='chapa', keep='first', inplace=True)

    brasil_filtrado = brasil_bruto[~brasil_bruto['evento_codigo'].isin(eventos_excluidos)]
    espanha_filtrado = espanha_bruto[~espanha_bruto['evento_codigo'].isin(eventos_excluidos)]

    print(f"Registros únicos e mais recentes no Brasil (pós-filtro): {brasil_filtrado.shape[0]}")
    print(f"Registros únicos e mais recentes na Espanha (pós-filtro): {espanha_filtrado.shape[0]}")

    df_merged = pd.merge(
        brasil_filtrado[['chapa', 'nome', 'motivo_evento', 'evento_codigo']],
        espanha_filtrado[['chapa', 'motivo_evento', 'evento_codigo']],
        on='chapa',
        suffixes=('_br', '_es')
    )

    df_divergencias = df_merged[df_merged['evento_codigo_br'] != df_merged['evento_codigo_es']].copy()

    if df_divergencias.empty:
        print("\nNenhuma divergência de outros eventos encontrada entre as bases.")
    else:
        print(f"\nEncontradas {df_divergencias.shape[0]} divergências de eventos.")
        colunas_finais = {
            'chapa': 'chapa',
            'nome': 'nome_completo',
            'motivo_evento_br': 'evento_brasil',
            'motivo_evento_es': 'evento_espanha'
        }
        df_relatorio = df_divergencias[list(colunas_finais.keys())].rename(columns=colunas_finais)
        df_relatorio['chapa'] = df_relatorio['chapa'].astype(str).str.split('.').str[0]

        print("\nPrévia do Relatório de Divergências de Eventos:")
        print(df_relatorio.head())

        caminho_excel = os.path.join(output_dir, 'outros_eventos_divergentes.xlsx')
        df_relatorio.to_excel(caminho_excel, index=False)
        print(f"\n-> Relatório Excel gerado em: {caminho_excel}")

        chapas_para_envio = ';'.join(df_relatorio['chapa'].unique())
        caminho_txt = os.path.join(output_dir, 'chapas_outros_eventos.txt')
        try:
            with open(caminho_txt, 'w', encoding='utf-8') as f:
                f.write("--------------OUTROS EVENTOS------------\n")
                f.write(chapas_para_envio)
            print(f"-> Arquivo TXT com chapas gerado em: {caminho_txt}")
        except Exception as e:
            print(f"ERRO ao gerar arquivo TXT: {e}")

if __name__ == '__main__':
    run_analysis_outros_eventos()