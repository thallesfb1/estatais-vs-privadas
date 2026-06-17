# ============================================================
# EMPRESAS SELECIONADAS — FodaseEstatais2
# ============================================================

empresas_selecionadas = {
    # FINANCEIRO
    'BCO BRASIL S.A.':                                ('Financeiro', 'Estatal'),
    'ITAU UNIBANCO HOLDING S.A.':                     ('Financeiro', 'Privado'),
    'BCO BRADESCO S.A.':                              ('Financeiro', 'Privado'),
    'BCO SANTANDER (BRASIL) S.A.':                    ('Financeiro', 'Privado'),
    'BCO BTG PACTUAL S.A.':                           ('Financeiro', 'Privado'),
    'BCO ABC BRASIL S.A.':                            ('Financeiro', 'Privado'),
    'BCO PAN S.A.':                                   ('Financeiro', 'Privado'),

    # ENERGIA
    'CIA ENERGETICA DE MINAS GERAIS - CEMIG':         ('Energia', 'Estatal'),
    'CIA PARANAENSE DE ENERGIA - COPEL':              ('Energia', 'Estatal'),
    'CENTRAIS ELET BRAS S.A. - ELETROBRAS':           ('Energia', 'Estatal'),
    'ENGIE BRASIL ENERGIA S.A.':                      ('Energia', 'Privado'),
    'EQUATORIAL ENERGIA S.A.':                        ('Energia', 'Privado'),
    'CPFL ENERGIA S.A.':                              ('Energia', 'Privado'),
    'ENERGISA S.A.':                                  ('Energia', 'Privado'),
    'ALUPAR INVESTIMENTO S/A':                        ('Energia', 'Privado'),
    'NEOENERGIA S.A.':                                ('Energia', 'Privado'),

    # PETRÓLEO
    'PETROLEO BRASILEIRO S.A. PETROBRAS':             ('Petroleo', 'Estatal'),
    'PRIO S.A.':                                      ('Petroleo', 'Privado'),
}

# ============================================================
# TRANSIÇÕES — empresas que mudaram de tipo ao longo dos anos
# ============================================================

transicoes = {
    'CENTRAIS ELET BRAS S.A. - ELETROBRAS': {
        'ate_ano':     2021,
        'tipo_antes':  'Estatal',
        'tipo_depois': 'Privado',
    },
    'CIA PARANAENSE DE ENERGIA - COPEL': {
        'ate_ano':     2022,
        'tipo_antes':  'Estatal',
        'tipo_depois': 'Privado',
    },
}

# ============================================================
# EVENTOS EXÓGENOS
# ============================================================

eventos_exogenos = {
    ('CENTRAIS ELET BRAS S.A. - ELETROBRAS', 2014): 'Lei 12.783/2013 - Renovação tarifária',
    ('CENTRAIS ELET BRAS S.A. - ELETROBRAS', 2015): 'Lei 12.783/2013 - Renovação tarifária',
    ('CENTRAIS ELET BRAS S.A. - ELETROBRAS', 2022): 'Privatização Eletrobras - Renomeada para Axia Energia',
    ('CENTRAIS ELET BRAS S.A. - ELETROBRAS', 2023): 'Privatização Eletrobras - Renomeada para Axia Energia', # <- adicionar
    ('CIA PARANAENSE DE ENERGIA - COPEL',     2022): 'Privatização Copel',
    ('CIA PARANAENSE DE ENERGIA - COPEL',     2023): 'Privatização Copel',
}

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def get_tipo(empresa, ano):
    """Retorna o tipo correto da empresa para o ano dado"""
    if empresa in transicoes:
        t = transicoes[empresa]
        return t['tipo_antes'] if ano <= t['ate_ano'] else t['tipo_depois']
    return empresas_selecionadas[empresa][1]


def get_setor(empresa):
    """Retorna o setor da empresa"""
    return empresas_selecionadas[empresa][0]


def get_evento(empresa, ano):
    """Retorna (flag, descricao) do evento exógeno se houver"""
    chave = (empresa, ano)
    if chave in eventos_exogenos:
        return 1, eventos_exogenos[chave]
    return 0, ''