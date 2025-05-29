"""
Módulo de agentes CrewAI para recomendação de medicamentos
Usa dados processados do banco vetorial FAISS para análise inteligente
"""
import json # conversão de dicts JSON 
import os # usar os para usar o .env
from dotenv import load_dotenv # Carregar .env
from crewai import Agent, Task, Crew, Process, LLM # Usado para a criação dos agentes
from crewai.tools import tool # Decorador para criar ferramentas custom para os agentes
from crewai_tools import SerperDevTool # Ferramenta para busca web via API Serper
import vector_database # Importa o banco vetorial do código vector_database

# Carrega .env (chaves de API, configurações)
load_dotenv()
llm = LLM(
    model=os.getenv('MODEL_NAME', 'gemini/gemini-2.0-flash'),
    api_key=os.getenv('GEMINI_API_KEY')
)


@tool
def search_medicamentos_anvisa(descricao_sintomas: str, top_k: int = 5) -> str:
    """Busca medicamentos da ANVISA baseado na descrição de sintomas usando busca vetorial"""
    try:
        # Verificar se banco vetorial foi inicializado antes de usar
        if not vector_database.vector_db:
            return json.dumps({"erro": "Banco vetorial não inicializado"})
        
        # Validar entrada: descrição deve ter pelo menos 5 caracteres para busca efetiva
        if not descricao_sintomas or len(descricao_sintomas.strip()) < 5:
            return json.dumps({"erro": "Descrição de sintomas muito curta"})
        
        # Buscar medicamentos usando similaridade semântica no banco vetorial FAISS
        resultados = vector_database.vector_db.search_medicamentos(descricao_sintomas, top_k)
        
        # Verificar se encontrou resultados
        if not resultados:
            return json.dumps({"message": "Nenhum medicamento encontrado"})
        
        # Retornar resultados como JSON string para o agente processar
        return json.dumps(resultados, ensure_ascii=False, indent=2)
        
    except Exception as e:
        # Capturar e retornar erros como JSON 
        return json.dumps({"erro": f"Erro na busca: {str(e)}"})

@tool
def get_detalhes_medicamento(nome_medicamento: str) -> str:
    """Busca informações detalhadas sobre um medicamento específico no banco vetorial"""
    try:
        # Verificar se banco vetorial está disponível
        if not vector_database.vector_db:
            return json.dumps({"erro": "Banco vetorial não inicializado"})
        
        # Buscar detalhes completos no banco vetorial usando busca textual
        detalhes = vector_database.vector_db.get_medicamento_detalhes(nome_medicamento)
        
        # Verificar se medicamento foi encontrado
        if not detalhes:
            return json.dumps({"message": f"Medicamento '{nome_medicamento}' não encontrado"})
        
        # Retornar detalhes como JSON string
        return json.dumps(detalhes, ensure_ascii=False, indent=2)
        
    except Exception as e:
        # Tratamento de erros com retorno estruturado
        return json.dumps({"erro": f"Erro ao buscar detalhes: {str(e)}"})

def verificar_configuracao_agentes():
    """Verifica se todas as configurações necessárias estão disponíveis"""
    config_status = {
        "gemini_api_key": bool(os.getenv('GEMINI_API_KEY')),
        "serper_api_key": bool(os.getenv('SERPER_API_KEY')),
        "banco_vetorial": bool(vector_database.vector_db),
        "model_name": os.getenv('MODEL_NAME', 'gemini/gemini-2.0-flash')
    }
    
    return config_status

"""
O Agente Especialista em Medicamentos é responsável por encontrar medicamentos adequados aos sintomas descritos.
Ele tem acesso às ferramentas de busca vetorial e detalhamento de medicamentos. Sua função é identificar medicamentos registrados na ANVISA que possam ser relevantes para os sintomas apresentados, considerando similaridade semântica, categoria terapêutica e disponibilidade no mercado brasileiro.
"""
agente_medicamentos = Agent(
    role="Especialista em Medicamentos ANVISA",
    goal="Identificar medicamentos adequados baseado em sintomas usando dados oficiais da ANVISA",
    verbose=False,
    memory=True,
    backstory="""Você é um farmacêutico clínico com acesso aos dados oficiais da ANVISA. 
    Analisa medicamentos registrados no Brasil e suas indicações, priorizando sempre a segurança do paciente.
    Você classifica o nível de risco dos medicamentos e determina se requerem receita médica.""",
    tools=[search_medicamentos_anvisa, get_detalhes_medicamento],
    llm=llm
)

"""
O Agente Analista de Segurança é responsável por avaliar os riscos e a segurança dos medicamentos recomendados.
Ele utiliza ferramentas de busca web para pesquisar informações atualizadas sobre contraindicações, efeitos 
colaterais e orientações de segurança.
"""
agente_seguranca = Agent(
    role="Analista de Segurança e Orientação Médica",
    goal="Avaliar segurança das recomendações e fornecer orientações sobre quando consultar médicos",
    verbose=False,
    memory=True,
    backstory="""Você é um especialista em farmacovigilância e telemedicina. Avalia riscos de medicamentos,
    determina quando é essencial buscar orientação médica profissional e conhece plataformas de consulta online.
    Você tem conhecimento sobre as principais plataformas de telemedicina no Brasil e pode recomendar
    especialistas adequados baseado no tipo de medicamento e nível de risco.""",
    tools=[SerperDevTool(api_key=os.getenv('SERPER_API_KEY'))] if os.getenv('SERPER_API_KEY') else [],
    llm=llm
)

def executar_analise_sintomas(sintomas):
    """Análise completa de sintomas com recomendação de medicamentos e consultas médicas"""
    try:
        # Verificar se banco vetorial está inicializado
        if not vector_database.vector_db:
            return {"status": "erro", "erro": "Banco vetorial não inicializado"}
        
        # Verificar configurações dos agentes
        config = verificar_configuracao_agentes()
        if not config["gemini_api_key"]:
            return {"status": "erro", "erro": "GEMINI_API_KEY não configurada"}
        
        """
        A Tarefa de Busca de Medicamentos é executada pelo agente especialista utilizando o banco vetorial para encontrar medicamentos similares aos sintomas descritos,  considerando scores de confiança, categorias terapêuticas apropriadas e disponibilidade no mercado brasileiro. O agente deve usar tanto a busca semântica quanto a busca detalhada para fornecer recomendações fundamentadas nos dados da ANVISA que estão no banco vetorial
        """
        task_medicamentos = Task(
            description=f"""
            Analise os sintomas: "{sintomas}"
            
            INSTRUÇÕES DETALHADAS:
            1. Use search_medicamentos_anvisa para encontrar medicamentos adequados (top 5)
            2. Para cada medicamento encontrado, avalie:
               - Similaridade com os sintomas (scores > 0.7 são excelentes)
               - Categoria terapêutica e adequação
               - Popularidade no mercado brasileiro
               - Use get_detalhes_medicamento para medicamentos mais promissores
            
            3. Classifique o NÍVEL DE RISCO de cada medicamento:
               - BAIXO: Medicamentos OTC, analgésicos simples, vitaminas
               - MÉDIO: Antibióticos, anti-inflamatórios, medicamentos respiratórios
               - ALTO: Cardiovasculares, neurológicos, endócrinos
            
            4. Determine se REQUER RECEITA MÉDICA:
               - Antibióticos, cardiovasculares, neurológicos, endócrinos = RECEITA OBRIGATÓRIA
               - Analgésicos, antigripais simples = SEM RECEITA
            """,
            expected_output="""
            Lista de 3-5 medicamentos recomendados com:
            - Nome do princípio ativo
            - Categoria terapêutica  
            - Score de confiança (% de similaridade)
            - Nível de risco (BAIXO/MÉDIO/ALTO)
            - Requer receita: SIM/NÃO
            - Justificativa baseada nos sintomas
            - Informações de disponibilidade
            """,
            agent=agente_medicamentos
        )
        
        """
        A Tarefa de Análise de Segurança é executada pelo agente de segurança dependendo dos resultados da busca de medicamentos e tem como objetivo avaliar os riscos associados às recomendações, urgência, necessidade de receita e o especialista que ele deve procurar. O agente utiliza a tool busca web para encontrar informações atualizadas sobre contraindicações, efeitos colaterais e orientações de segurança, determinando também o nível de urgência para consulta médica e fornecendo disclaimers apropriados sobre automedicação.
        """
        task_seguranca = Task(
            description=f"""
            Com base na análise do Especialista em Medicamentos, conduza análise completa de segurança
            e forneça orientações sobre consultas médicas online.
            
            ANÁLISE DE SEGURANÇA:
            1. Revise os medicamentos recomendados e seus níveis de risco
            2. Determine urgência para consulta médica baseado em:
               - Medicamentos de alto risco recomendados
               - Sintomas descritos: "{sintomas}"
               - Necessidade de receita médica
            
            BUSCA DE LINKS PARA CONSULTAS MÉDICAS:
            3. Use busca web para encontrar:
               - Plataformas de telemedicina adequadas (Doctoralia, Consulta do Bem, etc.)
               - Especialistas recomendados baseado na categoria dos medicamentos
               - Links diretos para agendamento online
            
            4. Especialidades a considerar:
               - Medicamentos cardiovasculares → Cardiologista
               - Medicamentos neurológicos → Neurologista  
               - Medicamentos gastrointestinais → Gastroenterologista
               - Medicamentos gerais → Clínico Geral
            
            URGÊNCIA DA CONSULTA:
            - URGENTE: Medicamentos de alto risco, sintomas preocupantes  
            - RECOMENDADA: Medicamentos que requerem receita
            - OPCIONAL: Medicamentos de baixo risco
            """,
            expected_output="""
            Análise de segurança completa:
            - Avaliação de risco para cada medicamento
            - Nível de urgência (URGENTE/RECOMENDADA/OPCIONAL)
            - Especialista recomendado
            - Links para consulta médica online (2-3 opções)
            - Orientações de segurança
            - Disclaimers sobre automedicação
            """,
            agent=agente_seguranca,
            context=[task_medicamentos]
        )
        
        """
        O Crew têm execução sequencial, onde primeiro o especialista em medicamentos busca e analisa opções terapêuticas,
        e em seguida o analista de segurança avalia os riscos e fornece orientações de segurança.
        """
        crew = Crew(
            agents=[agente_medicamentos, agente_seguranca],
            tasks=[task_medicamentos, task_seguranca],
            verbose=False,
            process=Process.sequential
        )
        resultado = crew.kickoff()
        # Capturar e retornar em caso de sucesso
        return {
            "status": "sucesso",
            "sintomas": sintomas,
            "analise": str(resultado),
            "configuracao": config
        }
    except Exception as e:
        # Capturar e retornar erros de forma estruturada
        return {
            "status": "erro",
            "erro": str(e),
            "tipo_erro": type(e).__name__
        }