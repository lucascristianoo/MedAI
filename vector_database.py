"""
Módulo do banco vetorial FAISS, usando csv do limpeza.py
"""
import pandas as pd # Para carregar CSV e manipular dataFrame
import numpy as np # Conversões para FAISS (dtype=np.float32)
import faiss # Banco vetorial que vamos usar localmente
from sentence_transformers import SentenceTransformer # Para carregar modelo e gerar embeddings

class AnvisaVectorDB:
    """gerenciar banco vetorial"""
    
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2') # Modelo escolhido
        self.df = None # dados do CSV
        self.embeddings = None # armazena embeddings dos medicamentos
        self.index = None # índice FAISS 
        self.processado = None # dataFrame para geração de embeddings
        
    def load_data(self, csv_path):
        """Carrega dados do CSV processado e cria banco vetorial completo"""
        self.df = pd.read_csv(csv_path)
        
        # Criar converte cada linha em dicionário para embeddings
        self.processado = pd.DataFrame(columns=['processado'])
        self.processado['processado'] = self.df.apply(lambda row: {
            "principio_ativo": str(row.get('principio_ativo_limpo', '')), # Nome limpo sem acentos/caracteres especiais
            "categoria_terapeutica": str(row.get('categoria_terapeutica', '')), # Categoria padronizada (antibiotico, analgesico, etc)
            "texto_busca": str(row.get('texto_completo_busca', '')),
            "popularidade": str(row.get('popularidade_mercado', '')), # baseado em qtd produtos
            "total_produtos": str(row.get('total_produtos_registrados', 0)) 
        }, axis=1)
        
        # Gerar embeddings 384 dim
        self.embeddings = self.model.encode(self.processado['processado'].tolist())
        
        # Cria índice para busca
        dim = self.embeddings.shape[1] # dim
        self.index = faiss.IndexFlatL2(dim) # Índice Flat L2 
        self.index.add(np.array(self.embeddings, dtype=np.float32)) # Adiciona todos os vetores ao índice
        
    def search_medicamentos(self, sintomas, top_k=5):
        """Busca medicamentos usando similaridade"""
        if not sintomas or not sintomas.strip():
            return []
        
        # Gerar vetor da consulta 
        query_vector = self.model.encode([sintomas])[0]
        query_vector_np = np.array([query_vector], dtype=np.float32) # Converte para formato compatível com FAISS np.float32
        
        # Buscar no índice vetorial - encontra medicamentos mais similares aos sintomas
        distances, indices = self.index.search(query_vector_np, top_k) # Retorna distâncias e índices dos top_k mais similares
        
        # Montar resultados com informações detalhadas
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx >= 0 and idx < len(self.df): # Verifica se índice é válido
                row = self.df.iloc[idx] 
                results.append({
                    "indice": int(idx), # Posição no dataFrame
                    "distancia": float(dist), # Distância euclidiana (menor = mais similar)
                    "similaridade": float(1 / (1 + dist)), # distância baixa = similaridade alta
                    "principio_ativo": row.get('principio_ativo_limpo', ''), # Nome limpo do medicamento
                    "categoria_terapeutica": row.get('categoria_terapeutica', ''), # Categoria padronizada
                    "popularidade": row.get('popularidade_mercado', ''), # Popularidade no mercado
                    "total_produtos": row.get('total_produtos_registrados', 0), # Qtd produtos registrados
                    "texto_busca": row.get('texto_resumo_busca', ''), # Versão resumida para exibição
                    "produtos_exemplo": row.get('produtos_principais', ''), # Exemplos de nomes comerciais
                    "empresas_exemplo": row.get('empresas_principais', '') # Exemplos de fabricantes
                })
        
        return results # Lista ordenada por similaridade (mais similar primeiro)
    
    def get_medicamento_detalhes(self, nome_medicamento):
        """Busca detalhes completos de um medicamento específico pelo nome"""
        # Validação de entrada
        if not nome_medicamento:
            return None
            
        # Buscar no dataframe usando busca textual flexível
        mask = self.df['principio_ativo_limpo'].str.contains(
            nome_medicamento, case=False, na=False # case=False = ignora maiúscula/minúscula, na=False = ignora valores nulos
        )
        
        matches = self.df[mask] # Filtra DataFrame usando máscara booleana
        if matches.empty: # Se não encontrou nada
            return None
            
        # Retornar informações detalhadas do primeiro match encontrado
        med = matches.iloc[0] 
        return {
            "principio_ativo": med.get('principio_ativo_limpo', ''), # Nome padronizado
            "categoria_terapeutica": med.get('categoria_terapeutica', ''), # Categoria terapêutica
            "popularidade_mercado": med.get('popularidade_mercado', ''), # Nível de popularidade
            "total_produtos": med.get('total_produtos_registrados', 0), # Total de produtos registrados
            "diversidade_formulacoes": med.get('diversidade_formulacoes', ''), # Diversidade de apresentações
            "produtos_exemplo": med.get('produtos_principais', ''), # Exemplos de nomes comerciais
            "empresas_exemplo": med.get('empresas_principais', ''), # Exemplos de fabricantes
            "texto_completo": med.get('texto_completo_busca', '') # Texto completo com todas as informações
        }

# Instância global para facilitar uso em outros módulos 
vector_db = None

def initialize_database(csv_path):
    """Inicializa o banco vetorial global a partir do CSV processado"""
    global vector_db
    vector_db = AnvisaVectorDB() # Cria nova instância da classe
    vector_db.load_data(csv_path) # Carrega dados e constrói índice vetorial