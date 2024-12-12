import streamlit as st
import pandas as pd
import io
from datetime import datetime
import base64

# Variáveis globais
df_composicoes = None
df_eap_padrao = None

# Inicializa variáveis de estado
if "etapa1_concluida" not in st.session_state:
    st.session_state["etapa1_concluida"] = False
if "etapa2_concluida" not in st.session_state:
    st.session_state["etapa2_concluida"] = False

if "processando_orcamento" not in st.session_state:
    st.session_state["processando_orcamento"] = False
if "processando_servicos" not in st.session_state:
    st.session_state["processando_servicos"] = False

# Função para comparar e retornar o código correspondente
def comparar_composicoes(desc_serv, df_composicoes):
    codigos_encontrados = set()

    for _, row in df_composicoes.iterrows():
        palavra = str(row['Palavra-Chave 1'])
        segundapalavra = str(row['Palavra-Chave 2'])
        terceirapalavra = str(row['Palavra-Chave 3'])

        if desc_serv == row['Descrição'] or (
                palavra in desc_serv and segundapalavra in desc_serv and terceirapalavra in desc_serv):
            codigo_float = float(row['Cód EAP Padrão'])
            codigo_str = '{:0>5.2f}'.format(codigo_float)
            codigos_encontrados.add(codigo_str)

    if codigos_encontrados:
        if len(codigos_encontrados) > 1:
            codigos_formatados = ','.join(codigos_encontrados)
            return f"CÓDIGOS ENCONTRADOS: {codigos_formatados}"
        else:
            return ','.join(codigos_encontrados)
    else:
        return "SERVIÇO NÃO ENCONTRADO"


def determinar_alocacao(cod_nivel2):
    if cod_nivel2.startswith('CÓDIGOS ENCONTRADOS') or cod_nivel2 == 'SERVIÇO NÃO ENCONTRADO':
        return 'MANUAL'
    else:
        return 'AUTOMÁTICA'


def formatar_codigo(row):
    codigo_str = str(row['Código'])  # Convertendo o valor para uma string
    if isinstance(row['Código'], str):
        if row['ID'] == 1:
            return f"{codigo_str.split('.')[0].zfill(2)}."
        elif row['ID'] == 2:
            return f"{codigo_str.split('.')[0].zfill(2)}.{codigo_str.split('.')[1].zfill(3)}."
        elif row['ID'] == 3:
            return f"{codigo_str.split('.')[0].zfill(2)}.{codigo_str.split('.')[1].zfill(3)}.{codigo_str.split('.')[2].zfill(3)}."
    return codigo_str  # Retorna o código original se não for uma string ou não precisar ser formatado



def abrir_eap_padrao():
    global mapa_descritivo, mapa_descritivo2, df_eap_padrao
    arquivo_eap = st.file_uploader("Selecione o arquivo EAP Padrão", type=["xlsx"], key="eap")
    if arquivo_eap:
        try:
            df_eap_padrao = pd.read_excel(arquivo_eap)
            # Convert 'CodNivel1' column to float with the specified format
            df_eap_padrao['CodNivel1'] = df_eap_padrao['CodNivel1'].apply(lambda x: '{:0>5.2f}'.format(float(x)))
            df_eap_padrao['CodNivel2'] = df_eap_padrao['CodNivel2'].apply(lambda x: '{:0>5.2f}'.format(float(x)))

            # Remover duplicatas do DataFrame df_eap_padrao
            df_eap_padrao.drop_duplicates(subset=['CodNivel1'])

            # Convertendo 'CodNivel1' do df_eap_padrao para string
            df_eap_padrao['CodNivel1'] = df_eap_padrao['CodNivel1'].astype(str)
            df_eap_padrao['CodNivel2'] = df_eap_padrao['CodNivel2'].astype(str)

            df_eap_padrao['CodNivel1'] = df_eap_padrao['CodNivel1'].str.rstrip('0').str.replace('.', '')

            # Criar um dicionário mapeando os códigos do DataFrame df_servicos_revisados aos descritivos correspondentes no DataFrame df_eap_padrao
            mapa_descritivo = df_eap_padrao.set_index('CodNivel1')['DescrNivel1'].to_dict()
            mapa_descritivo2 = df_eap_padrao.set_index('CodNivel2')['DescrNivel2'].to_dict()
            st.success("EAP Padrão importada com sucesso!")
            st.session_state["etapa1_concluida"] = True
            return df_eap_padrao
        except Exception as e:
            st.error("Erro ao importar a EAP Padrão!")

def abrir_arquivo_composicoes():
    global df_composicoes
    if st.session_state["etapa1_concluida"]:
        arquivo_composicoes = st.file_uploader("Selecione o arquivo de Composições", type=["xlsx"], key="composicoes")
        if arquivo_composicoes:
            try:
                df_composicoes = pd.read_excel(arquivo_composicoes)
                colunas_faltantes = []
                if 'Descrição' not in df_composicoes.columns:
                    colunas_faltantes.append('Descrição')
                if 'Palavra-Chave 1' not in df_composicoes.columns:
                    colunas_faltantes.append('Palavra-Chave 1')
                if 'Palavra-Chave 2' not in df_composicoes.columns:
                    colunas_faltantes.append('Palavra-Chave 2')
                if 'Palavra-Chave 3' not in df_composicoes.columns:
                    colunas_faltantes.append('Palavra-Chave 3')
                    raise ValueError("O arquivo selecionado não contém as seguintes colunas necessárias: {}".format(
                        ', '.join(colunas_faltantes)))
                # Convertendo todas as letras para maiúsculas
                df_composicoes = df_composicoes.map(lambda x: x.upper() if isinstance(x, str) else x)
                st.success("Arquivo de composições importado com sucesso!")
                st.session_state["etapa2_concluida"] = True
                return df_composicoes
            except ValueError as e:
                st.error("Erro ao importar o arquivo de composições!")

def abrir_arquivo_orcamento():
    if st.session_state["etapa2_concluida"]:
        arquivo_orcamento = st.file_uploader("Selecione o arquivo de orçamento (.xlsx)", type=["xlsx"])
        if arquivo_orcamento and not st.session_state["processando_orcamento"]:
            if st.button("Parar Processamento"):
                st.warning("Processamento interrompido pelo usuário!")
                return  # Sai da função imediatamente

            with st.spinner("Processando arquivo de orçamento..."):
                try:
                   df = pd.read_excel(arquivo_orcamento)

                   # Verificar colunas necessárias
                   colunas_necessarias = ['ID', 'Código', 'Descrição', 'Preço Total']
                   if not all(col in df.columns for col in colunas_necessarias):
                       st.error(f"O arquivo não possui as colunas necessárias: {', '.join(colunas_necessarias)}")
                       return

                   # Mapeamento de IDs
                   valores_unicos_id = df['ID'].unique()
                   if set(valores_unicos_id) == {3, 7, 11, 15}:
                       mapeamento_ids = {3: 1, 7: 2, 11: 3, 15: 4}
                       df['ID'] = df['ID'].map(mapeamento_ids)

                   # Criar colunas de níveis
                   df['Código Formatado'] = df.apply(formatar_codigo, axis=1)
                   df['Orc Nivel 1'] = df['Código Formatado'] + ' ' + df['Descrição']

                   df_filtrado1 = df[df['ID'].isin([2, 3, 4])]
                   df_filtrado1['Orc Nivel 2'] = df_filtrado1['Código Formatado'] + ' ' + df_filtrado1['Descrição']

                   df_filtrado2 = df_filtrado1[df_filtrado1['ID'].isin([3, 4])]
                   df_filtrado2['Orc Nivel 3'] = df_filtrado2['Código Formatado'] + ' ' + df_filtrado2['Descrição']

                   df_filtrado = df_filtrado2[df_filtrado2['ID'] == 4]
                   df_filtrado = df_filtrado[
                       ['ID', 'Código', 'Orc Nivel 1', 'Orc Nivel 2', 'Orc Nivel 3', 'Descrição', 'Preço Total']]
                   df_filtrado.rename(columns={'Descrição': 'Serviço'}, inplace=True)
                   df_filtrado['Serviço'] = df_filtrado['Serviço'].str.upper()

                   # Aplicar lógica de tipos
                   filtro_estimativas = df_filtrado['Serviço'].str.contains('ESTIMATIVA', case=False, na=False)
                   filtro_mao_de_obra = df_filtrado['Serviço'].str.contains('MÃO DE OBRA|MOP|MOE', case=False, na=False)

                   df_filtrado['Tipo'] = 'MAT | TERC | ADM'
                   df_filtrado.loc[filtro_estimativas, 'Tipo'] = 'EST'
                   df_filtrado.loc[filtro_mao_de_obra, 'Tipo'] = 'MO'

                   # Adicionar alocação
                   df_filtrado['CodNivel2'] = df_filtrado['Serviço'].apply(lambda x: comparar_composicoes(x, df_composicoes))
                   df_filtrado['Alocação'] = df_filtrado['CodNivel2'].apply(determinar_alocacao)

                   # Exportar resultado
                   output = io.BytesIO()
                   with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                       df_filtrado.to_excel(writer, index=False, sheet_name='Orcamento Tratado')
                   st.download_button("Baixar Orçamento Tratado", data=output.getvalue(), file_name="orcamento_tratado.xlsx",
                                      mime="application/vnd.ms-excel")

                   st.success("Arquivo de orçamento processado com sucesso!")
                   st.session_state["processando_orcamento"] = True

                except Exception as e:
                   st.error(f"Erro: {e}")


def abrir_arquivo_servicos():
    global df_eap_padrao
    # Upload do arquivo de serviços revisados
    if st.session_state["processando_orcamento"]:
        arquivo_servicos_revisados = st.file_uploader("Selecione o arquivo de serviços revisados (.xlsx)", type=["xlsx"])
        if arquivo_servicos_revisados and not st.session_state["processando_servicos"]:
            with st.spinner("Processando arquivo de serviços..."):
                try:
                    print("Iniciando função: abrir_arquivo_servicos")
                    df_servicos_revisados = pd.read_excel(arquivo_servicos_revisados)
                    # Converta a coluna 'CodNivel2' para float com o formato especificado
                    df_servicos_revisados['CodNivel2'] = df_servicos_revisados['CodNivel2'].apply(
                        lambda x: '{:0>5.2f}'.format(float(x)))
                    # Converter a coluna 'CodNivel2' para string
                    df_servicos_revisados['CodNivel2'] = df_servicos_revisados['CodNivel2'].astype(str)
                    # Extrair os dígitos antes do ponto da coluna 'CodNivel2'
                    df_servicos_revisados['Digitos_CodNivel2'] = df_servicos_revisados['CodNivel2'].str.split('.').str[0]
                    # Mapear os códigos da coluna 'Digitos_CodNivel2' no DataFrame df_servicos_revisados com os descritivos correspondentes no DataFrame df_eap_padrao
                    df_servicos_revisados['DescrNivel1'] = df_servicos_revisados['Digitos_CodNivel2'].map(mapa_descritivo)
                    df_servicos_revisados['DescrNivel2'] = df_servicos_revisados['CodNivel2'].map(mapa_descritivo2)
                    df_servicos_revisados['EAP Padrão Nivel 1'] = df_servicos_revisados['Digitos_CodNivel2'] + '.' + ' ' + \
                                                                  df_servicos_revisados['DescrNivel1']
                    df_servicos_revisados['EAP Padrão Nivel 2'] = df_servicos_revisados['CodNivel2'] + '.' + ' ' + \
                                                                  df_servicos_revisados['DescrNivel2']

                    # Criar um DataFrame com todos os códigos únicos de df_eap_padrao
                    codigos_unicos = df_eap_padrao['CodNivel2'].unique()
                    df_codigos_unicos = pd.DataFrame(codigos_unicos, columns=['CodNivel2'])

                    # Mesclar df_codigos_unicos com df_servicos_revisados
                    merged_df = df_codigos_unicos.merge(df_servicos_revisados, on='CodNivel2', how='left')

                    # Preencher valores nulos com 0 na coluna 'Preço Total'
                    merged_df['Preço Total'].fillna(0, inplace=True)

                    # Agrupar os dados e somar os valores do preço total por código e tipo
                    agrupado_df = merged_df.groupby(['CodNivel2', 'Tipo'])['Preço Total'].sum().reset_index()

                    # Criar o DataFrame final conforme solicitado
                    excecoes = ['05.04', '06.06', '07.10', '08.11', '09.10', '10.07', '11.08', '12.08', '13.07', '14.06',
                                '15.06', '16.07', '17.13', '18.05', '19.06', '20.05', '22.09', '23.16',
                                '24.07', '25.03', '27.03', '29.05']
                    tipos = ['MAT | TERC | ADM', 'MO', 'EST']
                    resultados = []

                    for codigo in codigos_unicos:
                        tipos = ['MAT | TERC | ADM', 'MO', 'EST']

                        if codigo.endswith('.00') and 'MO' in tipos:
                            tipos.remove('MO')
                        if codigo == '05.10' and 'MAT | TERC | ADM' in tipos:
                            tipos.remove('MAT | TERC | ADM')
                        if codigo in ['05.11', '05.12'] and 'MO' in tipos:
                            tipos.remove('MO')
                        if codigo in ['31.00', '32.00']:
                            tipos = ['EST']
                        if codigo >= '01.00' and codigo <= '04.42':
                            tipos = ['MAT | TERC | ADM', 'EST']
                        if codigo in excecoes:
                            tipos = ['MO', 'EST']

                        for tipo in tipos:
                            custo = agrupado_df[(agrupado_df['CodNivel2'] == codigo) & (agrupado_df['Tipo'] == tipo)][
                                'Preço Total'].sum()
                            resultados.append([codigo, tipo, custo])
                    df_resultado = pd.DataFrame(resultados, columns=['CodNivel2', 'Tipo', 'Custo'])
                    st.write("Resultado agrupado:")
                    st.dataframe(df_resultado)

                    # Botão para baixar o arquivo de resultado
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_resultado.to_excel(writer, index=False, sheet_name='Resultado')
                    st.download_button("Baixar Resultado", data=output.getvalue(), file_name="resultado_tratado.xlsx",
                                       mime="application/vnd.ms-excel")
                    st.success("Processamento concluído com sucesso!")
                    st.session_state["processando_servicos"] = True
                except Exception as e:
                    st.error(f"Erro: {e}")

# Função para converter imagem em Base64
def carregar_imagem_base64(caminho):
    with open(caminho, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Caminho correto da imagem
caminho_imagem = "imagens/logo-tatico-branco.png"  # Substitua pelo caminho correto

# Carrega a imagem em Base64
imagem_base64 = carregar_imagem_base64(caminho_imagem)

# Configuração inicial
st.set_page_config(page_title="Tratamento de Dados", page_icon="imagens/TATICO_logotipo_01_colorido simbolo.png", layout="centered")

# Estilos CSS customizados
custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');

        html, body, [class*="st-"] {
            font-family: 'Montserrat', sans-serif;
            background-color: #f5f7f9;
        }
        
        /* Container do título (azul) */
        .header-container {
            background-color: #2F318F; /* Azul */
            color: #FFFFFF; /* Texto branco */
            padding: 20px;
            text-align: left;
            font-size: 28px;
            font-weight: 700;
            border-radius: 8px 8px 0 0;
        }

        /* Estilo para os títulos menores */
        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 10px;
        }

        /* Container do uploader */
        .stFileUploader {
            border: 2px dashed #ccc;
            border-radius: 8px;
            padding: 10px !important;
            background-color: #f8f9fa;
        }
                /* Oculta o texto do file_uploader */
        .stFileUploader label {
            display: none; /* Oculta a label "Selecione o arquivo" */
        }

        .stFileUploader button {
            color: #2F318F;
            border-radius: 5px;
        }

        .stFileUploader button:hover {
            background-color: #c1c1e5;
            color: #2F318F;
            border-color: #2f318f;
        }
        /* Hover personalizado */
        .stDownloadButton > button:hover {
            color: #2F318F; /* Cor do texto no hover */
            border-color: #2F318F;
        }
        
    /* Hover personalizado para botões gerais */
    .stButton>button:hover {
        color: #2F318F; /* Cor do texto no hover */
        border-color: #2F318F;
    }
    </style>
"""

# Aplicar CSS
st.markdown(custom_css, unsafe_allow_html=True)


# HTML do cabeçalho
st.markdown(f"""
    <div style="display: flex; justify-content: space-between; 
                align-items: center; background-color: #2F318F; color: #FFFFFF; 
                padding: 20px; border-radius: 8px 8px 0 0;">
        <div style="font-size: 28px; font-weight: 700;">Tratamento de Dados - Orçamentos</div>
        <img src="data:image/png;base64,{imagem_base64}" alt="Logo" style="height: 70px;">
    </div>
""", unsafe_allow_html=True)

# Container branco englobando as seções
st.markdown("<div class='main-container'>", unsafe_allow_html=True)

# Seção 1
st.markdown("<div class='section-title'>1. Importar EAP Padrão</div>", unsafe_allow_html=True)
st.write("Selecione o arquivo EAP Padrão (.xlsx)")
abrir_eap_padrao()

# Seção 2
if st.session_state["etapa1_concluida"]:
    st.markdown("<div class='section-title'>2. Importar Composições</div>", unsafe_allow_html=True)
    st.write("Selecione o arquivo de Composições (.xlsx)")
    abrir_arquivo_composicoes()

# Seção 3
if st.session_state["etapa2_concluida"]:
    st.markdown("<div class='section-title'>3. Importar Orçamento</div>", unsafe_allow_html=True)
    st.write("Selecione o arquivo de orçamento (.xlsx)")
    abrir_arquivo_orcamento()

# Seção 4
if st.session_state["processando_orcamento"]:
    st.markdown("<div class='section-title'>4. Importar Serviços</div>", unsafe_allow_html=True)
    st.write("Selecione o arquivo de serviços revisados (.xlsx)")
    abrir_arquivo_servicos()

# Obter o ano atual
ano_atual = datetime.now().year

# Rodapé com a tag <footer>
rodape = f"""
    <footer style="text-align: center; padding: 10px; margin-top: 20px; 
                   font-size: 14px; color: #777;">
        © {ano_atual} - Tático Soluções. Todos os direitos reservados.
    </footer>
"""
st.markdown(rodape, unsafe_allow_html=True)
