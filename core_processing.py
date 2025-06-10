import pandas as pd # type: ignore
import os

def load_and_prepare_data():
    print("--- CORE: Iniciando carga e preparação dos dados... ---")
    data_path = 'data'
    
    try:
        df_brasil_bruto = pd.read_excel(os.path.join(data_path, 'Base RM.xlsx'))
        df_espanha_bruto = pd.read_excel(os.path.join(data_path, 'Base SF.xlsx'))
    except FileNotFoundError as e:
        print(f"ERRO: Arquivo base não encontrado. Verifique se 'Base RM.xlsx' e 'Base SF.xlsx' estão na pasta 'data/'.\nDetalhe: {e}")
        return None, None
    except Exception as e:
        print(f"ERRO ao ler os arquivos base.\nDetalhe: {e}")
        return None, None

    colunas_brasil = {
        'LOCAL SYSTEM ID': 'id_sistema_local',
        'CHAPA': 'chapa',
        'FIRST NAME': 'nome_parcial',
        'LAST NAME': 'sobrenome',
        'HIRE DATE': 'data_admissao',
        'EFFECTIVE DATE': 'data_efetiva',
        'STATUS': 'status_empregado',
        'CONTRACT TYPE': 'tipo_contrato',
        'JOB': 'cargo',
        'FAMILY': 'familia',
        'CATEGORY': 'categoria',
        'EMPLOYMENT TYPE': 'tipo_empregado',
        'EVENT REASON': 'motivo_evento',
        'NATIONALITY': 'nacionalidade',
        'EXPA/LOCAL': 'expa_local',
        'BUSINESS UNIT': 'business_unit'
    }

    colunas_espanha = {
        'ID sist. nom. local': 'id_sistema_local',
        'Nombre': 'nome_parcial',
        'Primer apellido': 'sobrenome',
        'Expa/Local': 'expa_local',
        'Detalles de empleo Fecha de inicio original': 'data_admissao',
        'Detalles de empleo Fecha de terminación de contrato': 'data_demissao',
        'Fecha del evento': 'data_efetiva',
        'Estado de empleado': 'status_empregado',
        'Tipo de contrato': 'tipo_contrato',
        'Puesto': 'cargo',
        'Familia': 'familia',
        'Categoría': 'categoria',
        'Tipo empleado': 'tipo_empregado',
        'Motivo del evento': 'motivo_evento',
        'DG / DN corporativo': 'business_unit',
        'Primera nacionalidad': 'nacionalidade'
    }

    brasil_limpo = df_brasil_bruto.rename(columns=colunas_brasil)
    espanha_limpa = df_espanha_bruto.rename(columns=colunas_espanha)

    if 'nome_parcial' in brasil_limpo.columns and 'sobrenome' in brasil_limpo.columns:
        brasil_limpo['nome'] = brasil_limpo['nome_parcial'].astype(str) + ' ' + brasil_limpo['sobrenome'].astype(str)

    if 'nome_parcial' in espanha_limpa.columns and 'sobrenome' in espanha_limpa.columns:
        espanha_limpa['nome'] = espanha_limpa['nome_parcial'].astype(str) + ' ' + espanha_limpa['sobrenome'].astype(str)

    if 'chapa' not in brasil_limpo.columns and 'id_sistema_local' in brasil_limpo.columns:
        print("  - AVISO: Coluna 'CHAPA' não encontrada na base Brasil. Usando 'id_sistema_local' como 'chapa'.")
        brasil_limpo['chapa'] = brasil_limpo['id_sistema_local']
    
    datas_brasil = ['data_admissao', 'data_efetiva']
    for data in datas_brasil:
        if data in brasil_limpo.columns:
            brasil_limpo[data] = pd.to_datetime(brasil_limpo[data], errors='coerce')
    
    datas_espanha = ['data_admissao', 'data_efetiva', 'data_demissao']
    for data in datas_espanha:
        if data in espanha_limpa.columns:
            espanha_limpa[data] = pd.to_datetime(espanha_limpa[data], errors='coerce')
    
    print(f"\nBases carregadas. Brasil: {brasil_limpo.shape[0]} registros. Espanha: {espanha_limpa.shape[0]} registros.")
    
    mapeamentos_abas = {
        'status_empregado': 'Status', 'cargo': 'Cargo', 'familia': 'Familia', 'categoria': 'Categoria', 
        'tipo_empregado': 'Tipo de empregado', 'tipo_contrato': 'Tipo de contrato', 'business_unit': 'Business'
    }
    
    caminho_mapeamento_excel = os.path.join(data_path, 'mapeamento_valores.xlsx')

    for coluna, aba in mapeamentos_abas.items():
        if coluna in brasil_limpo.columns:
            try:
                df_map = pd.read_excel(caminho_mapeamento_excel, sheet_name=aba)
                map_dict = pd.Series(df_map.iloc[:, 1].values, index=df_map.iloc[:, 0]).to_dict()
                brasil_limpo[coluna] = brasil_limpo[coluna].map(map_dict).fillna(brasil_limpo[coluna])
                print(f"  - Mapeamento da aba '{aba}' para a coluna '{coluna}' aplicado com sucesso.")
            except Exception as e:
                print(f"  - AVISO: Não foi possível aplicar o mapeamento para '{coluna}' da aba '{aba}'. Detalhe: {e}")

    if 'status_empregado' in brasil_limpo.columns:
        brasil_limpo = brasil_limpo[brasil_limpo['status_empregado'] == 'Activo'].copy()
        print(f"  - Filtro de 'Activo' aplicado na base Brasil. Restam {brasil_limpo.shape[0]} registros.")

    print(f"  - A base Espanha será mantida com todos os {espanha_limpa.shape[0]} registros históricos.")

    for col in brasil_limpo.select_dtypes(include=['object']).columns:
        brasil_limpo[col] = brasil_limpo[col].str.strip()
            
    for col in espanha_limpa.select_dtypes(include=['object']).columns:
        espanha_limpa[col] = espanha_limpa[col].str.strip()

    # --- NOVO BLOCO DE PADRONIZAÇÃO DE CHAVES ---
    # Este bloco garante que as colunas de junção tenham o mesmo formato (texto limpo).
    print("\n--- CORE: Padronizando tipos de dados das chaves de junção ---")
    key_columns = ['id_sistema_local', 'chapa']

    for df_name, df in [('Brasil', brasil_limpo), ('Espanha', espanha_limpa)]:
        for col in key_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\\.0$', '', regex=True).str.strip()
                print(f"  - Coluna chave '{col}' da base {df_name} foi padronizada.")
    # --- FIM DO NOVO BLOCO ---

    print("--- CORE: Carga e preparação finalizadas. ---\n")
    return brasil_limpo, espanha_limpa