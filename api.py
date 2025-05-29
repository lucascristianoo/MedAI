# api.py - API, localmente executado antes da interface

from fastapi import FastAPI, HTTPException # Para gerenciar o FastAPI
from pydantic import BaseModel, Field # Para validação
from contextlib import asynccontextmanager # Para execução
import json # Manipular json
import os # Acessar variáveis de ambiente
from pathlib import Path # Validar paths
import logging # Para logs detalhados
import traceback # Para debug de erros

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from vector_database import initialize_database # Acessar banco vetorial faiss
    import vector_database # Importar módulo completo para acessar variável global
    from agentes import executar_analise_sintomas # Acessar função dos agentes 
    logger.info("Módulos importados com sucesso")
except Exception as e:
    logger.error(f"Erro ao importar módulos: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")

# Modelos Pydantic para validação de entrada
class SintomasInput(BaseModel):
    descricao: str = Field(..., min_length=10, max_length=500, description="Descrição dos sintomas")

class MedicamentoInput(BaseModel):
    nome_medicamento: str = Field(..., min_length=3, max_length=100, description="Nome do medicamento")

class BuscaSimplesInput(BaseModel):
    sintomas: str = Field(..., min_length=5, max_length=300, description="Sintomas para busca simples")
    top_k: int = Field(default=5, ge=1, le=10, description="Número de resultados")

sistema_inicializado = False
erro_inicializacao = None

# Funções auxiliares para chamadas diretas ao banco vetorial 
def converter_tipos_python(obj):
    """Converte tipos numpy para Python para serialização JSON"""
    try:
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: converter_tipos_python(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [converter_tipos_python(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    except Exception as e:
        logger.error(f"Erro ao converter tipos: {e}")
        return obj

def buscar_medicamentos_direto(sintomas: str, top_k: int = 5):
    """Busca medicamentos diretamente no banco vetorial"""
    try:
        if not vector_database.vector_db:
            return {"erro": "Banco vetorial não inicializado"}
        
        if not sintomas or len(sintomas.strip()) < 5:
            return {"erro": "Descrição de sintomas muito curta"}
        
        logger.info(f"Buscando medicamentos para: {sintomas[:50]}...")
        resultados = vector_database.vector_db.search_medicamentos(sintomas, top_k)
        
        if not resultados:
            return {"message": "Nenhum medicamento encontrado"}
        
        # Converter tipos numpy para tipos Python 
        resultados_convertidos = converter_tipos_python(resultados)
        logger.info(f"Encontrados {len(resultados)} medicamentos")
        return resultados_convertidos
        
    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        return {"erro": f"Erro na busca: {str(e)}"}

def obter_detalhes_direto(nome_medicamento: str):
    """Obtém detalhes do medicamento diretamente do banco vetorial"""
    try:
        if not vector_database.vector_db:
            return {"erro": "Banco vetorial não inicializado"}
        
        logger.info(f"Buscando detalhes para: {nome_medicamento}")
        detalhes = vector_database.vector_db.get_medicamento_detalhes(nome_medicamento)
        
        if not detalhes:
            return {"message": f"Medicamento '{nome_medicamento}' não encontrado"}
        
        # Converter tipos numpy para tipos Python 
        detalhes_convertidos = converter_tipos_python(detalhes)
        return detalhes_convertidos
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes: {e}")
        return {"erro": f"Erro ao buscar detalhes: {str(e)}"}

def verificar_configuracao_api():
    """Verifica configurações necessárias para API funcionar"""
    try:
        config = {
            "gemini_api_key": bool(os.getenv('GEMINI_API_KEY')),
            "serper_api_key": bool(os.getenv('SERPER_API_KEY')),
            "model_name": os.getenv('MODEL_NAME', 'gemini/gemini-2.0-flash'),
            "banco_vetorial": bool(vector_database.vector_db),
            "arquivo_csv": Path("anvisa_medicamentos.csv").exists()
        }
        logger.info(f"Configuração verificada: {config}")
        return config
    except Exception as e:
        logger.error(f"Erro ao verificar configuração: {e}")
        return {"erro": str(e)}

# O verificar_sistem verifica se o arquivo de dados processados existe e inicializa o banco vetorial FAISS se ainda não foi feito.
def verificar_sistema():
    global sistema_inicializado, erro_inicializacao
    
    if sistema_inicializado:
        logger.info("Sistema já inicializado")
        return True
    
    try:
        logger.info("Iniciando verificação do sistema...")
        
        # Verificar arquivo CSV
        if not Path("anvisa_medicamentos.csv").exists():
            erro_msg = "Arquivo anvisa_medicamentos.csv não encontrado. Execute: python limpeza.py"
            logger.error(f"ERRO: {erro_msg}")
            erro_inicializacao = erro_msg
            raise HTTPException(status_code=500, detail=erro_msg)
        
        logger.info("Arquivo CSV encontrado")
        
        # Inicializar banco vetorial
        logger.info("Inicializando banco vetorial...")
        initialize_database("anvisa_medicamentos.csv")
        logger.info("Função initialize_database executada")
        
        # Verificar se banco foi realmente inicializado
        if vector_database.vector_db is None:
            erro_msg = "vector_db ainda é None após inicialização"
            logger.error(f"ERRO: {erro_msg}")
            erro_inicializacao = erro_msg
            raise Exception(erro_msg)
        
        if not hasattr(vector_database.vector_db, 'df'):
            erro_msg = "vector_db não possui atributo 'df'"
            logger.error(f"ERRO: {erro_msg}")
            erro_inicializacao = erro_msg
            raise Exception(erro_msg)
            
        if vector_database.vector_db.df is None:
            erro_msg = "vector_db.df é None"
            logger.error(f"ERRO: {erro_msg}")
            erro_inicializacao = erro_msg
            raise Exception(erro_msg)
            
        medicamentos_count = len(vector_database.vector_db.df)
        logger.info(f"Banco vetorial inicializado com {medicamentos_count} medicamentos")
        sistema_inicializado = True
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        erro_msg = f"Erro ao inicializar sistema: {str(e)}"
        logger.error(f"ERRO: {erro_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        erro_inicializacao = erro_msg
        raise HTTPException(status_code=500, detail=erro_msg)

# Durante o startup, ele inicializa todo o sistema e carrega o banco vetorial na memória para garantir que as buscas funcionem.
@asynccontextmanager
async def lifespan(app):
    # Código executado na inicialização da API
    logger.info("Iniciando API MedAI...")
    
    try:
        verificar_sistema()
        
        if vector_database.vector_db and hasattr(vector_database.vector_db, 'df') and vector_database.vector_db.df is not None:
            medicamentos_count = len(vector_database.vector_db.df)
            logger.info(f"Sistema inicializado com sucesso! {medicamentos_count} medicamentos carregados")
        else:
            logger.warning("Sistema inicializado mas banco vetorial não carregou corretamente")
            
    except Exception as e:
        logger.error(f"Erro crítico na inicialização: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Não vamos impedir o startup, mas vamos logar o erro
    
    logger.info("API pronta para receber requisições")
    yield  # A aplicação roda aqui
    
    logger.info("Sistema finalizado")

# Criação da aplicação FastAPI
app = FastAPI(
    title="MedAI API",
    description="Sistema de Recomendação de Medicamentos ANVISA",
    version="1.0.0",
    lifespan=lifespan
)

# O endpoint root serve como ponto de verificação para confirmar que a API está funcionando corretamente.
@app.get("/")
async def root():
    return {
        "message": "MedAI API está funcionando!",
        "status": "ativo",
        "sistema_inicializado": sistema_inicializado,
        "erro_inicializacao": erro_inicializacao,
        "endpoints": [
            "GET /docs - Documentação Swagger",
            "POST /analisar_sintomas - Análise completa com IA",
            "POST /detalhes_medicamento - Detalhes de medicamento específico",
            "POST /busca_simples - Busca rápida por sintomas",
            "GET /status - Status do sistema",
            "GET /configuracao - Verificar configurações"
        ]
    }

# O busca_simples uma busca rápida e direta por medicamentos baseada em sintomas descritos pelo usuário.
@app.post("/busca_simples")
async def busca_simples_endpoint(dados: BuscaSimplesInput):
    try:
        if not sistema_inicializado:
            if erro_inicializacao:
                raise HTTPException(status_code=500, detail=f"Sistema não inicializado: {erro_inicializacao}")
            else:
                # Tentar inicializar novamente
                verificar_sistema()
        
        medicamentos = buscar_medicamentos_direto(dados.sintomas, dados.top_k)
        
        if "erro" in medicamentos:
            raise HTTPException(status_code=400, detail=medicamentos["erro"])
        
        return {
            "status": "sucesso",
            "sintomas": dados.sintomas,
            "total_encontrados": len(medicamentos) if isinstance(medicamentos, list) else 0,
            "medicamentos": medicamentos
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint busca_simples: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# O analisar_sintomas executa uma análise completa e inteligente dos sintomas usando agentes de IA especializados.
@app.post("/analisar_sintomas")
async def analisar_sintomas_endpoint(sintomas: SintomasInput):
    try:
        if not sistema_inicializado:
            if erro_inicializacao:
                raise HTTPException(status_code=500, detail=f"Sistema não inicializado: {erro_inicializacao}")
            else:
                verificar_sistema()
        
        # Verificar se as configurações necessárias estão disponíveis
        config = verificar_configuracao_api()
        if not config.get("gemini_api_key"):
            raise HTTPException(
                status_code=400, 
                detail="GEMINI_API_KEY não configurada. Configure no arquivo .env"
            )
        
        logger.info(f"Iniciando análise IA para: {sintomas.descricao[:50]}...")
        resultado = executar_analise_sintomas(sintomas.descricao)

        if resultado["status"] == "erro":
            if "API" in resultado.get("erro", ""):
                raise HTTPException(
                    status_code=500, 
                    detail=f"Erro de configuração de IA: {resultado['erro']}"
                )
            else:
                raise HTTPException(status_code=400, detail=resultado["erro"])
        
        logger.info("Análise IA concluída com sucesso")
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint analisar_sintomas: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno na análise de IA: {str(e)}"
        )

# O detalhes_medicamento busca informações detalhadas e completas sobre um medicamento específico pelo seu nome.
@app.post("/detalhes_medicamento")
async def detalhes_medicamento_endpoint(medicamento: MedicamentoInput):
    try:
        if not sistema_inicializado:
            if erro_inicializacao:
                raise HTTPException(status_code=500, detail=f"Sistema não inicializado: {erro_inicializacao}")
            else:
                verificar_sistema()

        data = obter_detalhes_direto(medicamento.nome_medicamento)
        
        if "erro" in data:
            raise HTTPException(status_code=404, detail=data["erro"])
        if "message" in data:
            return {"message": data["message"]}
        
        return data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint detalhes_medicamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    
# O status fornece informações em tempo real sobre o estado operacional do sistema
@app.get("/status")
async def status():
    try:
        # Verificação do estado do sistema
        medicamentos_count = 0
        banco_status = "não inicializado"
        
        if sistema_inicializado and vector_database.vector_db:
            if hasattr(vector_database.vector_db, 'df') and vector_database.vector_db.df is not None:
                medicamentos_count = len(vector_database.vector_db.df)
                banco_status = "inicializado"
            else:
                banco_status = "erro - df não existe"
        else:
            banco_status = "erro - vector_db é None"
        
        return {
            "sistema": "ativo",
            "medicamentos_carregados": medicamentos_count,
            "banco_vetorial": banco_status,
            "sistema_inicializado": sistema_inicializado,
            "erro_inicializacao": erro_inicializacao
        }
    except Exception as e:
        logger.error(f"Erro no endpoint status: {e}")
        return {
            "sistema": "erro",
            "erro": str(e),
            "banco_vetorial": "erro na verificação"
        }

# endpoint para verificar configurações
@app.get("/configuracao")
async def configuracao():
    """Endpoint para verificar se todas as configurações necessárias estão disponíveis"""
    try:
        config = verificar_configuracao_api()
        
        # Verificar problemas comuns, que estavam acontecendo durante os testes
        problemas = []
        if not config.get("arquivo_csv"):
            problemas.append("Arquivo CSV não encontrado. Execute: python limpeza.py")
        if not config.get("gemini_api_key"):
            problemas.append("GEMINI_API_KEY não configurada no .env")
        if not config.get("banco_vetorial"):
            problemas.append("Banco vetorial não inicializado")
        
        return {
            "configuracao": config,
            "status": "ok" if not problemas else "problemas_encontrados",
            "problemas": problemas,
            "ia_disponivel": config.get("gemini_api_key") and config.get("banco_vetorial"),
            "sistema_inicializado": sistema_inicializado,
            "erro_inicializacao": erro_inicializacao
        }
        
    except Exception as e:
        logger.error(f"Erro no endpoint configuracao: {e}")
        return {
            "status": "erro",
            "erro": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)