import requests
import pandas as pd
import os

# ============================================================
# ETL — DADOS MACROECONÔMICOS
# Fonte: API do Banco Central do Brasil (BCB/SGS)
# Série 433  → IPCA mensal
# Série 4390 → Selic média mensal
# ============================================================

def buscar_serie_bcb(codigo_serie, data_inicio, data_fim):
    """
    Busca uma série temporal do SGS (Sistema Gerenciador de Séries)
    do Banco Central do Brasil.
    Retorna um DataFrame com data e valor.
    """
    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados"
        f"?formato=json&dataInicial={data_inicio}&dataFinal={data_fim}"
    )
    r = requests.get(url, timeout=30)
    df = pd.DataFrame(r.json())
    df['data']  = pd.to_datetime(df['data'], dayfirst=True)
    df['valor'] = df['valor'].str.replace(',', '.').astype(float)
    return df


def calcular_macro_anual(ipca_mensal, selic_mensal):
    """
    Agrega os dados mensais para anual e calcula:
    - IPCA acumulado anual (produto dos fatores mensais)
    - Selic média mensal por ano
    - Selic anualizada (taxa mensal → anual)
    - Selic real (Selic nominal descontada do IPCA)
    """
    # IPCA acumulado anual — produto dos fatores mensais
    ipca_mensal['ano'] = ipca_mensal['data'].dt.year
    ipca_anual = (
        ipca_mensal.groupby('ano')['valor']
        .apply(lambda x: ((1 + x/100).prod() - 1) * 100)
        .reset_index()
        .rename(columns={'valor': 'ipca_anual'})
    )

    # Selic média mensal por ano
    selic_mensal['ano'] = selic_mensal['data'].dt.year
    selic_anual = (
        selic_mensal.groupby('ano')['valor']
        .mean()
        .reset_index()
        .rename(columns={'valor': 'selic_media'})
    )

    # Juntar e calcular derivados
    macro = ipca_anual.merge(selic_anual, on='ano')

    # Selic anualizada — converter taxa mensal para anual
    macro['selic_anual'] = ((1 + macro['selic_media']/100)**12 - 1) * 100

    # Selic real — retorno acima da inflação (Fórmula de Fisher)
    # Representa o custo de oportunidade real do capital
    macro['selic_real'] = (
        ((1 + macro['selic_anual']/100) / (1 + macro['ipca_anual']/100)) - 1
    ) * 100

    # Arredondar tudo para 2 casas
    for col in ['ipca_anual', 'selic_media', 'selic_anual', 'selic_real']:
        macro[col] = macro[col].round(2)

    return macro


if __name__ == "__main__":
    os.makedirs("Dados_macroeconomicos", exist_ok=True)

    print("Buscando IPCA (série 433)...")
    ipca = buscar_serie_bcb(433, '01/01/2014', '31/12/2023')

    print("Buscando Selic (série 4390)...")
    selic = buscar_serie_bcb(4390, '01/01/2014', '31/12/2023')

    print("Calculando agregações anuais...")
    macro = calcular_macro_anual(ipca, selic)

    # Salvar arquivo completo
    macro.to_csv(
        "Dados_macroeconomicos/macro_anual.csv",
        index=False,
        sep=";",
        encoding="utf-8"
    )

    print("\nConcluído!")
    print(macro[['ano', 'ipca_anual', 'selic_media', 'selic_anual', 'selic_real']].to_string(index=False))