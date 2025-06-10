# Documentação Técnica - Sincronizador de Colaboradores BR-ES

## 1. Visão Geral

Este projeto automatiza a validação e comparação de dados de colaboradores entre o sistema de RH do Brasil (Base RM) e o sistema corporativo da Espanha (Base SF).

O objetivo principal é identificar novos funcionários, funcionários com dados divergentes e outras mudanças de status para manter ambos os sistemas sincronizados, gerando relatórios e arquivos de apoio para a atualização manual ou semi-manual no sistema da Espanha.

## 2. Estrutura de Pastas

```
/projeto-sincronizador
|
|-- data/
|   |-- Base RM.xlsx - ZVW_NOMINA_COMPLEMENTO.csv  (Dados do Brasil)
|   |-- Base SF.xlsx - 1_Validacion_datos_empleado_Emp.csv (Dados da Espanha)
|   |-- mapeamento_valores.xlsx (Arquivo com abas para traduzir valores)
|
|-- output/
|   |-- (Pastas com os resultados de cada execução são criadas aqui)
|
|-- docs/
|   |-- DOCUMENTACAO_TECNICA.md (Este arquivo)
|
|-- core_processing.py
|-- run_eve001.py
|-- run_eve012_013.py
|-- run_outros_eventos.py
```

- **`data/`**: Contém os arquivos de entrada (CSV) extraídos dos sistemas de RH.
- **`output/`**: Diretório onde os relatórios (Excel e TXT) de cada análise são salvos. Cada execução cria uma subpasta com data e hora.
- **`docs/`**: Contém a documentação do projeto.

## 3. Arquivos Python e Fluxo de Execução

A execução é feita individualmente para cada tipo de análise, através dos scripts `run_...py`.

### 3.1. `core_processing.py`

Este é o módulo central e não é executado diretamente. Ele fornece a função `load_and_prepare_data()`, que é responsável por:
1.  **Carregar** os arquivos CSV das pastas `data/`.
2.  **Padronizar os Nomes das Colunas** de ambas as bases para um formato único, facilitando as comparações.
3.  **Processar os Dados do Brasil**:
    - Converte colunas de data.
    - Remove registros duplicados baseados no `id_sistema_local`, mantendo o mais recente pela `data_efetiva`.
    - Filtra para manter apenas os colaboradores com status "Ativo".
4.  **Mapear Valores**: Usa o arquivo `mapeamento_valores.xlsx` para traduzir os valores de campos como "Cargo", "Categoria", etc., da terminologia do Brasil para a da Espanha.
5.  **Retornar** dois DataFrames limpos e prontos para análise: um com os ativos do Brasil e outro com o histórico completo da Espanha.

### 3.2. `run_eve001.py`

-   **Propósito**: Identificar colaboradores que existem no Brasil mas não constam na base da Espanha.
-   **Lógica**:
    1.  Chama `load_and_prepare_data()`.
    2.  Aplica um filtro para ignorar expatriados espanhóis (`expaIn`).
    3.  Realiza uma junção `(left merge)` entre a base do Brasil (esquerda) e a da Espanha.
    4.  Filtra os registros onde os dados da Espanha são nulos, indicando um colaborador novo para o sistema espanhol.
    5.  Sugere o evento:
        - `eve001 - Novo Colaborador`: Se a data de admissão for recente (últimos 6 meses).
        - `VERIFICAR: eve003 ou eve023`: Se a admissão for mais antiga, sugerindo uma possível recontratação ou transferência que precisa de verificação manual.
-   **Saída**: Gera um arquivo Excel com os detalhes dos colaboradores e um arquivo TXT com as chapas separadas por evento (`EVE001` e `VERIFICAR`).

### 3.3. `run_eve012_013.py`

-   **Propósito**: Encontrar divergências de dados para colaboradores que existem em *ambas* as bases.
-   **Lógica**:
    1.  Chama `load_and_prepare_data()`.
    2.  Filtra a base da Espanha para considerar apenas os colaboradores "Activo".
    3.  Realiza uma junção `(inner merge)` para encontrar o conjunto de colaboradores comuns a ambas as bases.
    4.  Compara, linha a linha, os valores de colunas-chave (cargo, família, categoria, etc.).
    5.  Sugere o evento:
        - `eve013 - Mudança Contratual`: Se a divergência for no campo `tipo_contrato`.
        - `eve012 - Mudança de Dados`: Para todas as outras divergências.
-   **Saída**: Gera um Excel detalhando cada divergência encontrada e um TXT com as chapas agrupadas por evento (`EVE012` e `EVE013`).

### 3.4. `run_outros_eventos.py`

-   **Propósito**: Análise focada na divergência do campo "motivo do evento".
-   **Lógica**:
    1.  Similar ao `run_eve012_013`, faz um `inner merge` para encontrar colaboradores comuns.
    2.  Compara especificamente o campo `motivo_evento` entre as duas bases.
    3.  Reporta todos os casos onde os motivos são diferentes.
-   **Saída**: Gera um Excel com as divergências e um TXT com as chapas correspondentes.