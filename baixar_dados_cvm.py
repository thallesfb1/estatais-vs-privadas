import os
import pandas as pd
import requests  # type: ignore
from zipfile import ZipFile
from io import BytesIO

def baixar_dfp(ano):
    print(f"Baixando dados de {ano}...")
    url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
    
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
    except Exception as e:
        print(f"Erro ao baixar ano {ano}: {e}")
        return None, None, None
        
    try:
        z = ZipFile(BytesIO(r.content))
        
        # DRE consolidada
        dre = pd.read_csv(
            z.open(f"dfp_cia_aberta_DRE_con_{ano}.csv"),
            sep=";", encoding="latin1"
        )
        # Balanço Patrimonial
        bp = pd.read_csv(
            z.open(f"dfp_cia_aberta_BPA_con_{ano}.csv"),
            sep=";", encoding="latin1"
        )
        bpp = pd.read_csv(
            z.open(f"dfp_cia_aberta_BPP_con_{ano}.csv"),
            sep=";", encoding="latin1"
        )
        return dre, bp, bpp
    except Exception as e:
        print(f"Erro ao processar o arquivo ZIP de {ano}: {e}")
        return None, None, None

if __name__ == "__main__":
    # Criar pasta para salvar os resultados se desejar
    os.makedirs("dados_processados", exist_ok=True)
    
    # Baixar 10 anos de uma vez
    anos = range(2014, 2024)
    dados = {}
    
    for ano in anos:
        dre, bp, bpp = baixar_dfp(ano)
        if dre is not None and bp is not None and bpp is not None:
            dados[ano] = (dre, bp, bpp)
            # Opcional: salvar localmente em formato parquet ou csv para não precisar baixar de novo
            dre.to_csv(f"dados_processados/dfp_dre_{ano}.csv", index=False, sep=";")
            bp.to_csv(f"dados_processados/dfp_bp_{ano}.csv", index=False, sep=";")
            bpp.to_csv(f"dados_processados/dfp_bpp_{ano}.csv", index=False, sep=";")
            print(f"Dados de {ano} salvos com sucesso!")
        
    print("Processamento concluído!")
