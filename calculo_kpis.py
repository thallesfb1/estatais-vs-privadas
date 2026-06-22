import pandas as pd
from scipy import stats
import os

pd.options.display.float_format = '{:.2f}'.format

from empresas_selecionadas import (
    empresas_selecionadas,
    get_tipo, get_setor, get_evento
)

# ============================================================
# CONFIGURAÇÕES DE KPIs
# ============================================================

# Financeiro — True = maior é melhor, False = menor é melhor
kpis_config_financeiro = {
    'roe':               True,
    'margem_liquida':    True,
    'nim':               True,
    'indice_eficiencia': False,
    'alavancagem':       False,
    'pdd_ratio':         False,
}

# Energia — True = maior é melhor, False = menor é melhor
kpis_config_energia = {
    'roe':             True,
    'margem_liquida':  True,
    'margem_bruta':    True,
    'margem_ebitda':   True,
    'alavancagem':     False,
    'cobertura_juros': True,
}

# Petróleo — True = maior é melhor, False = menor é melhor
kpis_config_petroleo = {
    'roe':             True,
    'margem_liquida':  True,
    'margem_bruta':    True,
    'margem_ebitda':   True,
    'alavancagem':     False,
    'cobertura_juros': True,
}

# ============================================================
# FUNÇÕES AUXILIARES DE EXTRAÇÃO
# ============================================================

def extrair_lucro_liquido(dre_fin):
    """Tenta 3.09.01 primeiro, fallback para 3.11.01"""
    ll = dre_fin[dre_fin['codigo_conta'] == '3.09.01'][['empresa', 'valor']].rename(columns={'valor': 'lucro_liquido'})
    empresas_all         = dre_fin['empresa'].unique()
    empresas_encontradas = ll['empresa'].unique()
    empresas_faltando    = [e for e in empresas_all if e not in empresas_encontradas]
    if empresas_faltando:
        ll_fallback = dre_fin[
            (dre_fin['codigo_conta'] == '3.11.01') &
            (dre_fin['empresa'].isin(empresas_faltando))
        ][['empresa', 'valor']].rename(columns={'valor': 'lucro_liquido'})
        ll = pd.concat([ll, ll_fallback], ignore_index=True)
    return ll


def extrair_patrimonio_liquido(bpp_fin):
    """Tenta 2.08 primeiro, fallback para 2.07"""
    pl = bpp_fin[bpp_fin['codigo_conta'] == '2.08'][['empresa', 'valor']].rename(columns={'valor': 'patrimonio_liquido'})
    empresas_all         = bpp_fin['empresa'].unique()
    empresas_encontradas = pl['empresa'].unique()
    empresas_faltando    = [e for e in empresas_all if e not in empresas_encontradas]
    if empresas_faltando:
        pl_fallback = bpp_fin[
            (bpp_fin['codigo_conta'] == '2.07') &
            (bpp_fin['empresa'].isin(empresas_faltando))
        ][['empresa', 'valor']].rename(columns={'valor': 'patrimonio_liquido'})
        pl = pd.concat([pl, pl_fallback], ignore_index=True)
    return pl


def extrair_despesas_operacionais(dre_fin):
    """Extrai despesas de pessoal e administrativas com fallback por empresa"""
    empresas = dre_fin['empresa'].unique()
    linhas = []
    for empresa in empresas:
        df = dre_fin[dre_fin['empresa'] == empresa]
        # Despesas de Pessoal — tenta 3.04.02, fallback 3.04.03
        desp_pes = df[df['codigo_conta'] == '3.04.02']['valor'].sum()
        if desp_pes == 0:
            desp_pes = df[df['codigo_conta'] == '3.04.03']['valor'].sum()
        # Despesas Administrativas — tenta 3.04.03, fallback 3.04.04
        desp_adm = df[df['codigo_conta'] == '3.04.03']['valor'].sum()
        if desp_adm == 0:
            desp_adm = df[df['codigo_conta'] == '3.04.04']['valor'].sum()
        linhas.append({
            'empresa':      empresa,
            'desp_pessoal': desp_pes,
            'desp_admin':   desp_adm,
        })
    return pd.DataFrame(linhas)


def adicionar_metadados(kpis, ano, setor):
    """Adiciona setor, tipo, ano e eventos exógenos"""
    kpis['setor'] = kpis['empresa'].map(lambda x: get_setor(x))
    kpis['tipo']  = kpis['empresa'].map(lambda x: get_tipo(x, ano))
    kpis['ano']   = ano
    kpis['evento_exogeno']   = kpis['empresa'].map(lambda x: get_evento(x, ano)[0])
    kpis['descricao_evento'] = kpis['empresa'].map(lambda x: get_evento(x, ano)[1])
    # Forçar substituição de qualquer NaN/None por string vazia
    kpis['descricao_evento'] = kpis['descricao_evento'].apply(
        lambda x: '' if x is None or (isinstance(x, float) and pd.isna(x)) else str(x)
    )
    return kpis


# ============================================================
# KPIs FINANCEIRO
# ============================================================

def calcular_kpis_financeiro(dre, bpa, bpp, ano):
    """Calcula os 6 KPIs do setor financeiro para um ano"""
    dre_fin = dre[dre['setor'] == 'Financeiro']
    bpa_fin = bpa[bpa['setor'] == 'Financeiro']
    bpp_fin = bpp[bpp['setor'] == 'Financeiro']

    ll           = extrair_lucro_liquido(dre_fin)
    pl           = extrair_patrimonio_liquido(bpp_fin)
    desp_df      = extrair_despesas_operacionais(dre_fin)
    receita      = dre_fin[dre_fin['codigo_conta'] == '3.01'][['empresa', 'valor']].rename(columns={'valor': 'receita'})
    result_bruto = dre_fin[dre_fin['codigo_conta'] == '3.03'][['empresa', 'valor']].rename(columns={'valor': 'result_bruto'})
    rec_servicos = dre_fin[dre_fin['codigo_conta'] == '3.04.01'][['empresa', 'valor']].rename(columns={'valor': 'rec_servicos'})
    outras_rec   = dre_fin[dre_fin['codigo_conta'] == '3.04.05'][['empresa', 'valor']].rename(columns={'valor': 'outras_rec'})
    rec_int      = dre_fin[dre_fin['codigo_conta'] == '3.01'][['empresa', 'valor']].rename(columns={'valor': 'rec_intermediacao'})
    desp_int     = dre_fin[dre_fin['codigo_conta'] == '3.02'][['empresa', 'valor']].rename(columns={'valor': 'desp_intermediacao'})
    ativo_total  = bpa_fin[bpa_fin['codigo_conta'] == '1'][['empresa', 'valor']].rename(columns={'valor': 'ativo_total'})

    # Mapeamento de contas de PDD por banco
    contas_pdd = {
        'BCO BRASIL S.A.':                        ['3.02.02', '3.02.03'],
        'BRB BANCO DE BRASILIA S.A.':             ['3.02.02', '3.02.03'],
        'BANESTES S.A. - BCO EST ESPIRITO SANTO': ['3.02.02', '3.02.03'],
        'BCO BRADESCO S.A.':                      ['3.04.06.01'],
        'ITAU UNIBANCO HOLDING S.A.':             ['3.04.06.01'],
        'BCO SANTANDER (BRASIL) S.A.':            ['3.04.06.01', '3.04.06.03'],
        'BCO BTG PACTUAL S.A.':                   ['3.02.02'],
        'BCO ABC BRASIL S.A.':                    ['3.04.06.01'],
        'BCO PAN S.A.':                           ['3.02.02'],
    }
    linhas_pdd = []
    for empresa, contas in contas_pdd.items():
        pdd_total = dre_fin[
            (dre_fin['empresa'] == empresa) &
            (dre_fin['codigo_conta'].isin(contas))
        ]['valor'].sum()
        linhas_pdd.append({'empresa': empresa, 'pdd': pdd_total})
    pdd_df = pd.DataFrame(linhas_pdd)

    kpis = ll.merge(pl,           on='empresa')
    kpis = kpis.merge(desp_df,      on='empresa')
    kpis = kpis.merge(receita,      on='empresa')
    kpis = kpis.merge(result_bruto, on='empresa')
    kpis = kpis.merge(rec_servicos, on='empresa', how='left')
    kpis = kpis.merge(outras_rec,   on='empresa', how='left')
    kpis = kpis.merge(rec_int,      on='empresa')
    kpis = kpis.merge(desp_int,     on='empresa')
    kpis = kpis.merge(ativo_total,  on='empresa')
    kpis = kpis.merge(pdd_df,       on='empresa')
    kpis[['rec_servicos', 'outras_rec']] = kpis[['rec_servicos', 'outras_rec']].fillna(0)

    # Calcular KPIs
    kpis['roe']               = kpis['lucro_liquido'] / kpis['patrimonio_liquido']
    kpis['margem_liquida']    = kpis['lucro_liquido'] / kpis['receita']
    kpis['produto_bancario']  = kpis['result_bruto'] + kpis['rec_servicos'] + kpis['outras_rec']
    kpis['indice_eficiencia'] = (kpis['desp_pessoal'].abs() + kpis['desp_admin'].abs()) / kpis['produto_bancario'].abs()
    kpis['nim']               = (kpis['rec_intermediacao'] + kpis['desp_intermediacao']) / kpis['ativo_total']
    kpis['passivo_total']     = kpis['ativo_total'] - kpis['patrimonio_liquido']
    kpis['alavancagem']       = kpis['passivo_total'] / kpis['patrimonio_liquido']
    kpis['pdd_ratio']         = kpis['pdd'].abs() / kpis['receita'].abs()

    # Arredondar KPIs numéricos do setor financeiro
    cols_numericas = ['roe', 'margem_liquida', 'nim',
                      'indice_eficiencia', 'alavancagem', 'pdd_ratio']
    for col in cols_numericas:
        kpis[col] = pd.to_numeric(kpis[col], errors='coerce').round(4)

    kpis = adicionar_metadados(kpis, ano, 'Financeiro')

    return kpis[['empresa', 'setor', 'tipo', 'ano',
                 'roe', 'margem_liquida', 'nim',
                 'indice_eficiencia', 'alavancagem', 'pdd_ratio',
                 'evento_exogeno', 'descricao_evento']]


# ============================================================
# KPIs ENERGIA
# ============================================================

def calcular_kpis_energia(dre, bpa, bpp, ano):
    """Calcula os 6 KPIs do setor de Energia para um ano"""
    dre_en = dre[dre['setor'] == 'Energia']
    bpa_en = bpa[bpa['setor'] == 'Energia']
    bpp_en = bpp[bpp['setor'] == 'Energia']

    ll        = dre_en[dre_en['codigo_conta'] == '3.11.01'][['empresa', 'valor']].rename(columns={'valor': 'lucro_liquido'})
    receita   = dre_en[dre_en['codigo_conta'] == '3.01'][['empresa', 'valor']].rename(columns={'valor': 'receita'})
    res_bruto = dre_en[dre_en['codigo_conta'] == '3.03'][['empresa', 'valor']].rename(columns={'valor': 'resultado_bruto'})
    desp_fin  = dre_en[dre_en['codigo_conta'] == '3.06.02'][['empresa', 'valor']].rename(columns={'valor': 'desp_financeiras'})
    ebit      = dre_en[dre_en['codigo_conta'] == '3.05'][['empresa', 'valor']].rename(columns={'valor': 'ebit'})
    pl        = bpp_en[bpp_en['codigo_conta'] == '2.03'][['empresa', 'valor']].rename(columns={'valor': 'patrimonio_liquido'})
    div_cp    = bpp_en[bpp_en['codigo_conta'] == '2.01.04'][['empresa', 'valor']].rename(columns={'valor': 'div_circulante'})
    div_lp    = bpp_en[bpp_en['codigo_conta'] == '2.02.01'][['empresa', 'valor']].rename(columns={'valor': 'div_nao_circulante'})
    caixa     = bpa_en[bpa_en['codigo_conta'] == '1.01.01'][['empresa', 'valor']].rename(columns={'valor': 'caixa'})
    # Depreciação da DRE — conta 3.04.02.08 (só Eletrobras tem)
    depr      = dre_en[dre_en['codigo_conta'] == '3.04.02.08'][['empresa', 'valor']].rename(columns={'valor': 'depreciacao'})

    kpis = ll.merge(receita,   on='empresa')
    kpis = kpis.merge(res_bruto, on='empresa')
    kpis = kpis.merge(desp_fin,  on='empresa')
    kpis = kpis.merge(ebit,      on='empresa')
    kpis = kpis.merge(pl,        on='empresa')
    kpis = kpis.merge(div_cp,    on='empresa')
    kpis = kpis.merge(div_lp,    on='empresa')
    kpis = kpis.merge(caixa,     on='empresa')
    kpis = kpis.merge(depr,      on='empresa', how='left')
    kpis['depreciacao'] = kpis['depreciacao'].fillna(0)

    # Calcular KPIs
    kpis['roe']            = kpis['lucro_liquido'] / kpis['patrimonio_liquido']
    kpis['margem_liquida'] = kpis['lucro_liquido'] / kpis['receita']
    kpis['margem_bruta']   = kpis['resultado_bruto'] / kpis['receita']
    kpis['divida_bruta']   = kpis['div_circulante'] + kpis['div_nao_circulante']
    kpis['divida_liquida'] = kpis['divida_bruta'] - kpis['caixa']
    kpis['ebitda']         = kpis['ebit'] + kpis['depreciacao'].abs()
    kpis['margem_ebitda']  = kpis['ebitda'] / kpis['receita']
    kpis['alavancagem']    = kpis.apply(
        lambda r: r['divida_liquida'] / r['ebitda'] if r['ebitda'] > 0 else None, axis=1
    )
    kpis['cobertura_juros'] = kpis.apply(
        lambda r: r['ebit'] / abs(r['desp_financeiras']) if r['desp_financeiras'] != 0 else None, axis=1
    )

    # Arredondar KPIs numéricos do setor de energia
    cols_numericas = ['roe', 'margem_liquida', 'margem_bruta',
                      'margem_ebitda', 'alavancagem', 'cobertura_juros']
    for col in cols_numericas:
        kpis[col] = pd.to_numeric(kpis[col], errors='coerce').round(4)

    kpis = adicionar_metadados(kpis, ano, 'Energia')

    return kpis[['empresa', 'setor', 'tipo', 'ano',
                 'roe', 'margem_liquida', 'margem_bruta',
                 'margem_ebitda', 'alavancagem', 'cobertura_juros',
                 'evento_exogeno', 'descricao_evento']]


# ============================================================
# KPIs PETRÓLEO
# ============================================================

def calcular_kpis_petroleo(dre, bpa, bpp, ano):
    """
    Calcula os 6 KPIs do setor de Petróleo para um ano.
    Usa depreciação da DVA (conta 7.04.01) para calcular
    EBITDA corretamente, já que a DRE consolidada não
    reporta depreciação separada para todas as empresas.
    """
    dre_pet = dre[dre['setor'] == 'Petroleo']
    bpa_pet = bpa[bpa['setor'] == 'Petroleo']
    bpp_pet = bpp[bpp['setor'] == 'Petroleo']

    # Carregar DVA do ano para obter depreciação
    try:
        dva = pd.read_csv(
            f"DVA_tratado/dfp_dva_{ano}_filtrado.csv",
            sep=";",
            encoding="utf-8",
            keep_default_na=False
        )
        dva_pet  = dva[dva['empresa'].isin(dre_pet['empresa'].unique())]
        depr_dva = dva_pet[['empresa', 'valor']].rename(columns={'valor': 'depreciacao'})
    except:
        depr_dva = pd.DataFrame(columns=['empresa', 'depreciacao'])

    # --- DRE ---
    ll        = dre_pet[dre_pet['codigo_conta'] == '3.11.01'][['empresa', 'valor']].rename(columns={'valor': 'lucro_liquido'})
    receita   = dre_pet[dre_pet['codigo_conta'] == '3.01'][['empresa', 'valor']].rename(columns={'valor': 'receita'})
    res_bruto = dre_pet[dre_pet['codigo_conta'] == '3.03'][['empresa', 'valor']].rename(columns={'valor': 'resultado_bruto'})
    ebit      = dre_pet[dre_pet['codigo_conta'] == '3.05'][['empresa', 'valor']].rename(columns={'valor': 'ebit'})
    desp_fin  = dre_pet[dre_pet['codigo_conta'] == '3.06.02'][['empresa', 'valor']].rename(columns={'valor': 'desp_financeiras'})

    # --- BPP ---
    pl        = bpp_pet[bpp_pet['codigo_conta'] == '2.03'][['empresa', 'valor']].rename(columns={'valor': 'patrimonio_liquido'})
    div_cp    = bpp_pet[bpp_pet['codigo_conta'] == '2.01.04'][['empresa', 'valor']].rename(columns={'valor': 'div_circulante'})
    div_lp    = bpp_pet[bpp_pet['codigo_conta'] == '2.02.01'][['empresa', 'valor']].rename(columns={'valor': 'div_nao_circulante'})

    # --- BPA ---
    caixa     = bpa_pet[bpa_pet['codigo_conta'] == '1.01.01'][['empresa', 'valor']].rename(columns={'valor': 'caixa'})

    # --- Montar dataframe ---
    kpis = ll.merge(receita,   on='empresa')
    kpis = kpis.merge(res_bruto, on='empresa')
    kpis = kpis.merge(ebit,      on='empresa')
    kpis = kpis.merge(desp_fin,  on='empresa')
    kpis = kpis.merge(pl,        on='empresa')
    kpis = kpis.merge(div_cp,    on='empresa')
    kpis = kpis.merge(div_lp,    on='empresa')
    kpis = kpis.merge(caixa,     on='empresa')
    kpis = kpis.merge(depr_dva,  on='empresa', how='left')
    kpis['depreciacao'] = kpis['depreciacao'].fillna(0)

    # --- Calcular KPIs ---
    kpis['roe']            = kpis['lucro_liquido'] / kpis['patrimonio_liquido']
    kpis['margem_liquida'] = kpis['lucro_liquido'] / kpis['receita']
    kpis['margem_bruta']   = kpis['resultado_bruto'] / kpis['receita']
    kpis['divida_bruta']   = kpis['div_circulante'] + kpis['div_nao_circulante']
    kpis['divida_liquida'] = kpis['divida_bruta'] - kpis['caixa']
    kpis['ebitda']         = kpis['ebit'] + kpis['depreciacao'].abs()
    kpis['margem_ebitda']  = kpis.apply(
        lambda r: r['ebitda'] / r['receita'] if r['ebitda'] > 0 else None, axis=1
    )
    kpis['alavancagem']    = kpis.apply(
        lambda r: r['divida_liquida'] / r['ebitda'] if r['ebitda'] > 0 else None, axis=1
    )
    kpis['cobertura_juros'] = kpis.apply(
        lambda r: r['ebit'] / abs(r['desp_financeiras']) if r['desp_financeiras'] != 0 else None, axis=1
    )

    # Arredondar KPIs numéricos do setor de petróleo
    cols_numericas = ['roe', 'margem_liquida', 'margem_bruta',
                      'margem_ebitda', 'alavancagem', 'cobertura_juros']
    for col in cols_numericas:
        kpis[col] = pd.to_numeric(kpis[col], errors='coerce').round(4)

    kpis = adicionar_metadados(kpis, ano, 'Petroleo')

    return kpis[['empresa', 'setor', 'tipo', 'ano',
                 'roe', 'margem_liquida', 'margem_bruta',
                 'margem_ebitda', 'alavancagem', 'cobertura_juros',
                 'evento_exogeno', 'descricao_evento']]


# ============================================================
# Z-SCORE GENÉRICO
# ============================================================

def calcular_zscore(kpis, ano, setor, kpis_config):
    """Calcula Z-Score das estatais vs privados para um setor e ano"""
    privados = kpis[kpis['tipo'] == 'Privado']
    estatais = kpis[kpis['tipo'] == 'Estatal']

    linhas = []
    for estatal in estatais.itertuples():
        for kpi, maior_melhor in kpis_config.items():
            # Usar só privados com valor válido para esse KPI
            valores_privados = privados[kpi].dropna()
            media  = valores_privados.mean()
            desvio = valores_privados.std()
            valor  = getattr(estatal, kpi)

            if pd.isna(valor) or desvio == 0:
                zscore = None
                sinal  = 'Dado indisponível'
            else:
                zscore     = (valor - media) / desvio
                zscore_int = zscore if maior_melhor else -zscore
                if zscore_int > 0.5:
                    sinal = 'Acima da média'
                elif zscore_int < -1:
                    sinal = 'Alerta'
                elif zscore_int < -0.5:
                    sinal = 'Abaixo da média'
                else:
                    sinal = 'Na média'

            linhas.append({
                'ano':             ano,
                'setor':           setor,
                'empresa':         estatal.empresa,
                'kpi':             kpi,
                'valor':           round(valor, 4) if not pd.isna(valor) else None,
                'media_privados':  round(media,  4),
                'desvio_padrao':   round(desvio, 4),
                'zscore':          round(zscore, 4) if zscore is not None else None,
                'sinal':           sinal,
                'evento_exogeno':  estatal.evento_exogeno,
                'descricao_evento':estatal.descricao_evento,
            })

    return pd.DataFrame(linhas)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    os.makedirs("KPIs", exist_ok=True)

    kpis_fin_list    = []
    kpis_en_list     = []
    kpis_pet_list    = []
    zscores_fin_list = []
    zscores_en_list  = []
    zscores_pet_list = []

    for ano in range(2014, 2024):
        print(f"Calculando KPIs {ano}...")

        dre = pd.read_csv(f"DRE_tratado/dfp_dre_{ano}_filtrado.csv",             sep=";", encoding="utf-8", keep_default_na=False)
        bpa = pd.read_csv(f"Balanco_ativo_tratado/dfp_bp_{ano}_filtrado.csv",    sep=";", encoding="utf-8", keep_default_na=False)
        bpp = pd.read_csv(f"Balanco_passivo_tratado/dfp_bpp_{ano}_filtrado.csv", sep=";", encoding="utf-8", keep_default_na=False)

        # Financeiro
        kpis_fin = calcular_kpis_financeiro(dre, bpa, bpp, ano)
        kpis_fin_list.append(kpis_fin)
        zscores_fin_list.append(calcular_zscore(kpis_fin, ano, 'Financeiro', kpis_config_financeiro))

        # Energia
        kpis_en = calcular_kpis_energia(dre, bpa, bpp, ano)
        kpis_en_list.append(kpis_en)
        zscores_en_list.append(calcular_zscore(kpis_en, ano, 'Energia', kpis_config_energia))

        # Petróleo
        kpis_pet = calcular_kpis_petroleo(dre, bpa, bpp, ano)
        kpis_pet_list.append(kpis_pet)
        zscores_pet_list.append(calcular_zscore(kpis_pet, ano, 'Petroleo', kpis_config_petroleo))

        print(f"  Financeiro: {len(kpis_fin)} | Energia: {len(kpis_en)} | Petróleo: {len(kpis_pet)}")

    # Consolidar e salvar — na_rep='' garante string vazia em vez de NaN
    pd.concat(kpis_fin_list,    ignore_index=True).to_csv("KPIs/kpis_financeiro.csv",    index=False, sep=";", encoding="utf-8", na_rep='')
    pd.concat(kpis_en_list,     ignore_index=True).to_csv("KPIs/kpis_energia.csv",       index=False, sep=";", encoding="utf-8", na_rep='')
    pd.concat(kpis_pet_list,    ignore_index=True).to_csv("KPIs/kpis_petroleo.csv",      index=False, sep=";", encoding="utf-8", na_rep='')
    pd.concat(zscores_fin_list, ignore_index=True).to_csv("KPIs/zscores_financeiro.csv", index=False, sep=";", encoding="utf-8", na_rep='')
    pd.concat(zscores_en_list,  ignore_index=True).to_csv("KPIs/zscores_energia.csv",    index=False, sep=";", encoding="utf-8", na_rep='')
    pd.concat(zscores_pet_list, ignore_index=True).to_csv("KPIs/zscores_petroleo.csv",   index=False, sep=";", encoding="utf-8", na_rep='')

    print("\nConcluído!")
    kpis_pet_completo = pd.concat(kpis_pet_list, ignore_index=True)
    print(kpis_pet_completo.groupby(['ano', 'tipo']).size().reset_index(name='empresas'))