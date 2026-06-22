import pandas as pd
import requests
from zipfile import ZipFile
from io import BytesIO
import os

# ============================================================
# ETL — DVA (Demonstração do Valor Adicionado)
# Extrai a depreciação (conta 7.04.01) das empresas
# de petróleo para uso no cálculo do EBITDA
# ============================================================

from empresas_selecionadas import empresas_selecionadas

# Padronizar nomes de empresas que mudaram ao longo dos anos
nomes_padronizados = {
    # Equatorial mudou de nome em 2020
    'EQUATORIAL S.A.':               'EQUATORIAL ENERGIA S.A.',
    # Eletrobras renomeada para Axia após privatização em 2022
    'AXIA ENERGIA S.A.':             'CENTRAIS ELET BRAS S.A. - ELETROBRAS',
    # 3R Petroleum renomeada para Brava Energia em 2020
    '3R PETROLEUM ÓLEO E GÁS S.A.':  'BRAVA ENERGIA S.A.',
    # Empresas com encoding quebrado nos arquivos CVM
    'ENAUTA PARTICIPAÃÃES S.A.':    'ENAUTA PARTICIPAÇÕES S.A.',
    '3R PETROLEUM ÃLEO E GÃS S.A.': 'BRAVA ENERGIA S.A.',
    'PETRORECÃNCAVO S.A.':           'PETRORECÔNCAVO S.A.',
}

def processar_dva(ano):
    """
    Baixa e processa a DVA consolidada de um ano.
    Extrai apenas a conta 7.04.01 (Depreciação, Amortização e Exaustão)
    para as empresas selecionadas.
    """
    print(f"Processando DVA {ano}...")

    # Baixar ZIP do ano direto da CVM
    url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
    except Exception as e:
        print(f"  Erro ao baixar {ano}: {e}")
        return None

    # Abrir ZIP e ler DVA consolidada
    z    = ZipFile(BytesIO(r.content))
    dva  = pd.read_csv(
        z.open(f"dfp_cia_aberta_DVA_con_{ano}.csv"),
        sep=";",
        encoding="latin1",
        dtype={'CD_CVM': str, 'CNPJ_CIA': str, 'CD_CONTA': str, 'VERSAO': int}
    )

    # Remover colunas desnecessárias
    dva = dva.drop(columns=['GRUPO_DFP', 'MOEDA'])

    # Renomear colunas para padrão do projeto
    dva = dva.rename(columns={
        'CNPJ_CIA':      'cnpj',
        'DT_REFER':      'data_referencia',
        'VERSAO':        'versao',
        'DENOM_CIA':     'empresa',
        'CD_CVM':        'codigo_cvm',
        'ESCALA_MOEDA':  'escala',
        'ORDEM_EXERC':   'exercicio',
        'DT_INI_EXERC':  'data_inicio_exercicio',
        'DT_FIM_EXERC':  'data_fim_exercicio',
        'CD_CONTA':      'codigo_conta',
        'DS_CONTA':      'descricao_conta',
        'VL_CONTA':      'valor',
        'ST_CONTA_FIXA': 'conta_fixa',
    })

    # Padronizar nomes de empresas
    dva['empresa'] = dva['empresa'].replace(nomes_padronizados)

    # Filtrar só exercício atual (com str.contains por encoding quebrado)
    dva = dva[
        dva['exercicio'].str.contains('LTIMO') &
        ~dva['exercicio'].str.contains('PEN')
    ]

    # Desduplicar — manter só versão mais recente
    dva = (
        dva.sort_values('versao', ascending=False)
           .drop_duplicates(subset=['cnpj', 'codigo_conta', 'data_fim_exercicio'])
           .reset_index(drop=True)
    )

    # Filtrar só empresas selecionadas
    dva = dva[dva['empresa'].isin(empresas_selecionadas.keys())].copy()

    # Filtrar só a conta de depreciação
    dva = dva[dva['codigo_conta'] == '7.04.01']

    # Normalizar escala monetária para milhares
    dva['valor'] = dva.apply(
        lambda r: r['valor'] * 1000 if r['escala'] == 'MIL' else r['valor'],
        axis=1
    )
    
    # DEPOIS — dividir por 1000 para converter para milhares
    # igualando à escala da DRE
    dva['valor'] = dva.apply(
        lambda r: r['valor'] / 1000 if r['escala'] == 'MIL' else r['valor'],
        axis=1
    )

    # Remover colunas não necessárias
    dva = dva.drop(columns=['exercicio', 'versao', 'escala'])

    print(f"  {ano}: {dva['empresa'].nunique()} empresas, {len(dva)} linhas salvas.")
    return dva


if __name__ == "__main__":
    # Criar pasta de saída
    os.makedirs("DVA_tratado", exist_ok=True)

    todos_anos = []

    for ano in range(2014, 2024):
        df = processar_dva(ano)
        if df is not None:
            # Salvar arquivo individual por ano
            df.to_csv(
                f"DVA_tratado/dfp_dva_{ano}_filtrado.csv",
                index=False,
                sep=";",
                encoding="utf-8",
                na_rep=''
            )
            todos_anos.append(df)

    # Salvar arquivo consolidado com todos os anos
    dva_completo = pd.concat(todos_anos, ignore_index=True)
    dva_completo.to_csv(
        "DVA_tratado/dfp_dva_completo.csv",
        index=False,
        sep=";",
        encoding="utf-8",
        na_rep=''
    )

    print(f"\nConcluído!")
    print(f"Total: {len(dva_completo)} linhas, {dva_completo['empresa'].nunique()} empresas")
    print(dva_completo.groupby('empresa')['data_fim_exercicio'].count().reset_index(name='anos'))