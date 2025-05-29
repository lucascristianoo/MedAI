"""
Antes de realizar qualquer operação envolvendo o banco vetorial é necessário antes executar esse código
Pré-processamento para criação de embeddings para enviar para o banco vetorial
"""
import pandas as pd # Manipulação de dados em tabelas
import re # Regex para limpeza de texto
import unicodedata # Normalização de caracteres especiais/acentos
import os # Operações do sistema operacional
from tqdm import tqdm # Barra de progresso visual

# Paths de origem e destino dos dados
ANVISA_CSV_PATH = 'data/DADOS_ABERTOS_MEDICAMENTOS.csv'
OUTPUT_FILE = 'anvisa_medicamentos.csv'

def clean_text(text):
    """Limpa e normaliza texto, tirando acentos, caracteres especiais, espaços duplos e das bordas"""
    if pd.isna(text) or text == '':
        return ''
    
    # Remove acentos usando normalização Unicode
    text = unicodedata.normalize('NFD', str(text))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # Remove caracteres especiais mantendo apenas letras, números, espaços e pontuação básica
    text = re.sub(r'[^\w\s\-\.\,\(\)]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip() # Remove espaços duplos e das bordas
    
    return text

def categorize_therapeutic_class(classe):
    """Categoriza classe terapêutica em grupos principais para facilitar busca"""
    if pd.isna(classe):
        return 'Não Classificado'
    
    classe_lower = classe.lower()
    
    # Mapeamento de categorias com palavras-chave associadas
    categories = {
        'antibiotico': ['antibiotico', 'antimicrobiano', 'bactericida'],
        'analgesico': ['analgesico', 'dor', 'anti-inflamatorio'],
        'cardiovascular': ['cardiovascular', 'cardiaco', 'hipertensao', 'pressao'],
        'sistema_nervoso': ['neurologico', 'psiquiatrico', 'antidepressivo', 'ansiedade'],
        'gastrointestinal': ['gastrico', 'digestivo', 'estomago', 'intestinal'],
        'respiratorio': ['respiratorio', 'pulmonar', 'bronco', 'asma'],
        'endocrino': ['hormonio', 'diabetes', 'tiroide', 'endocrino'],
        'dermatologico': ['dermatologico', 'pele', 'topico'],
        'oftalmico': ['oftalmico', 'ocular', 'olho'],
        'vitaminas': ['vitamina', 'suplemento', 'mineral']
    }
    
    # Procura primeira categoria que contenha alguma palavra-chave
    for category, keywords in categories.items():
        if any(keyword in classe_lower for keyword in keywords):
            return category.replace('_', ' ').title()
    
    return 'Outros'

def process_anvisa_data():
    """Processa dados transformando em formato adequado para banco vetorial"""
    
    # 1. Carregar dados da ANVISA
    df_raw = pd.read_csv(
        ANVISA_CSV_PATH, 
        encoding='latin-1',
        sep=';', # Separador 
        on_bad_lines='skip', # Pula linhas problemáticas
        low_memory=False, # Carrega tudo na memória 
        dtype=str # campos string
    )
    
    # 2. Filtrar apenas registros válidos e ativos
    df_valid = df_raw[
        (df_raw['PRINCIPIO_ATIVO'].notna()) & # Deve ter princípio ativo
        (df_raw['PRINCIPIO_ATIVO'].str.strip() != '') & # Não pode ser vazio
        ((df_raw['SITUACAO_REGISTRO'].str.contains('VÁLIDO', na=False, case=False)) | # Registro válido
         (df_raw['SITUACAO_REGISTRO'].str.contains('ATIVO', na=False, case=False)))    # Ou ativo
    ].copy()
    
    # 3. Aplicar categorização terapêutica padronizada
    df_valid['categoria_terapeutica'] = df_valid['CLASSE_TERAPEUTICA'].apply(categorize_therapeutic_class)
    
    # 4. Agrupar por princípio ativo para evitar duplicações
    grouped = df_valid.groupby('PRINCIPIO_ATIVO').agg({ # pega sempre as primeiras
        'CLASSE_TERAPEUTICA': 'first', 
        'categoria_terapeutica': 'first', 
        'NOME_PRODUTO': lambda x: list(x.dropna().unique()), # Lista única 
        'EMPRESA_DETENTORA_REGISTRO': lambda x: list(x.dropna().unique()), # Lista única 
        'NUMERO_REGISTRO_PRODUTO': 'count' # Conta total
    }).reset_index()
    
    # 5. Criar dataset final estruturado para embeddings
    medicamentos_final = []
    
    for idx, row in tqdm(grouped.iterrows(), total=len(grouped), desc="Processando medicamentos"):
        
        # Limpar e padronizar nome do princípio ativo
        nome_limpo = clean_text(row['PRINCIPIO_ATIVO']).title()
        
        # Estruturar dados do medicamento
        medicamento = {
            # Identificação principal
            'principio_ativo_limpo': nome_limpo,
            'categoria_terapeutica': row['categoria_terapeutica'],
            
            # Métricas de mercado
            'total_produtos_registrados': row['NUMERO_REGISTRO_PRODUTO'],
            'produtos_principais': '; '.join(row['NOME_PRODUTO'][:3]), # Até 3 exemplos
            'empresas_principais': '; '.join(row['EMPRESA_DETENTORA_REGISTRO'][:3]), # Até 3 exemplos
            
            # Indicadores calculados para enriquecer contexto de busca
            'popularidade_mercado': 'alta' if row['NUMERO_REGISTRO_PRODUTO'] >= 10 
                                   else 'media' if row['NUMERO_REGISTRO_PRODUTO'] >= 5
                                   else 'baixa',
            
            'diversidade_formulacoes': 'alta' if len(row['NOME_PRODUTO']) >= 5
                                     else 'media' if len(row['NOME_PRODUTO']) >= 3
                                     else 'baixa'
        }
        
        # Criar textos estruturados para embeddings semânticos
        embedding_parts = [
            f"Medicamento: {nome_limpo}",
            f"Principio Ativo: {row['PRINCIPIO_ATIVO']}",
            f"Classe Terapeutica: {row['CLASSE_TERAPEUTICA']}",
            f"Categoria: {row['categoria_terapeutica']}",
            f"Produtos Comerciais: {'; '.join(row['NOME_PRODUTO'][:3])}",
            f"Total de Produtos: {row['NUMERO_REGISTRO_PRODUTO']}"
        ]
        
        # Texto completo para busca semântica detalhada
        medicamento['texto_completo_busca'] = ' | '.join(embedding_parts)
        
        # Texto resumido para exibição rápida
        medicamento['texto_resumo_busca'] = f"{nome_limpo} - {row['categoria_terapeutica']}"
        
        medicamentos_final.append(medicamento)
    
    return medicamentos_final

def save_anvisa_medicamentos(medicamentos):
    """Salva dataset processado em CSV pronto para uso pelo banco vetorial"""
    # Converter para DataFrame
    df_final = pd.DataFrame(medicamentos)
    
    # Salvar
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    return OUTPUT_FILE

def main():
    medicamentos = process_anvisa_data()
    save_anvisa_medicamentos(medicamentos)
    print("Processamento concluído!")

if __name__ == "__main__":
    main()