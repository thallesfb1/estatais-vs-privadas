import os
from empresas_selecionadas import empresas_selecionadas
import pandas as pd

pd.options.display.float_format = '{:,.0f}'.format

def processar_balanco(ano):
    print(f"Processando {ano}...")
    
    # Ler
    df = pd.read_csv(
        f"Balanco_ativo_bruto/dfp_bp_{ano}.csv",
        encoding='utf-8', sep=";"
    )
    
    # Limpar e renomear — igual seu código atual
    df = df.drop(columns=['GRUPO_DFP', 'MOEDA'])
    df = df.rename(columns={
        'CNPJ_CIA':       'cnpj',
        'DT_REFER':       'data_referencia',
        'VERSAO':         'versao',
        'DENOM_CIA':      'empresa',
        'CD_CVM':         'codigo_cvm',
        'ESCALA_MOEDA':   'escala',
        'ORDEM_EXERC':    'exercicio',
        'DT_FIM_EXERC':   'data_fim_exercicio',
        'CD_CONTA':       'codigo_conta',
        'DS_CONTA':       'descricao_conta',
        'VL_CONTA':       'valor',
        'ST_CONTA_FIXA':  'conta_fixa',
    })
    nomes_padronizados = {
    'EQUATORIAL S.A.': 'EQUATORIAL ENERGIA S.A.',
    'AXIA ENERGIA S.A.': 'CENTRAIS ELET BRAS S.A. - ELETROBRAS'
    }
    df['empresa'] = df['empresa'].replace(nomes_padronizados)
    
    # Filtrar só exercício atual
    df['exercicio'] = df['exercicio'].map({'ÚLTIMO': 'atual', 'PENÚLTIMO': 'anterior'})
    df = df[df['exercicio'] == 'atual']
    df = df.drop(columns=['exercicio', 'versao'])
    
    # Filtrar empresas e adicionar setor/tipo
    df = df[df['empresa'].isin(empresas_selecionadas.keys())].copy()
    df['setor'] = df['empresa'].map(lambda x: empresas_selecionadas[x][0]) # type: ignore
    df['tipo']  = df['empresa'].map(lambda x: empresas_selecionadas[x][1]) # type: ignore
    
    # Salvar individualmente
    
    df.to_csv(f"Balanco_ativo_tratado/dfp_bp_{ano}_filtrado.csv", index=False, encoding='utf-8', sep=";")
    
    print(f"  {ano}: {df['empresa'].nunique()} empresas, {len(df)} linhas salvas.")
    return df


# Rodar para todos os anos e juntar tudo num único dataset
todos_anos = []

for ano in range(2014, 2024):
    df_ano = processar_balanco(ano)
    todos_anos.append(df_ano)

# Dataset consolidado com todos os anos
balanco_completo = pd.concat(todos_anos, ignore_index=True)
balanco_completo.to_csv("Balanco_ativo_tratado/dfp_bp_completo.csv", index=False, encoding='utf-8', sep=";")

print(f"\nConcluído! Total: {len(balanco_completo)} linhas, {balanco_completo['empresa'].nunique()} empresas.")