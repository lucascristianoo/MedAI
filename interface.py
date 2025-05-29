"""
Interface Streamlit para Sistema de Recomendação de Medicamentos ANVISA
"""
import streamlit as st # criar aplicações web
import pandas as pd # Manipulação de dados
import json # Para parsing dos resultados JSON 
import plotly.express as px # criação de gráficos
from pathlib import Path # Para verificação de existência de arquivos
from dotenv import load_dotenv # carregar .env
import os # acessar ambiente do sistema
import requests # Para conectar com a API 
import time # Para simulação de progresso

# Carregar variáveis .env
load_dotenv()

# URL da API - detecta automaticamente se está rodando em Docker ou local
def get_api_url():
    """
    Detecta automaticamente se está rodando em Docker ou local
    Tenta conectar via nome do serviço Docker primeiro, depois localhost
    """
    # URLs para testar (ordem de prioridade)
    urls_to_try = [
        "http://medai-api:8000",  # Nome do serviço Docker
        "http://localhost:8000"   # Execução local
    ]
    
    for url in urls_to_try:
        try:
            # Testar conexão com timeout curto para não travar
            response = requests.get(f"{url}/", timeout=2)
            if response.status_code == 200:
                return url
        except:
            continue
    
    # Se nenhuma funcionar, usar localhost como padrão
    return "http://localhost:8000"

API_URL = get_api_url()

# Configuração da página Streamlit
st.set_page_config(
    page_title="Sistema MedAI", # Título na aba do navegador
    page_icon="💊", # Ícone na aba do navegador
    layout="wide" # Layout amplo
)

# CSS com animações
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .warning-box {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border: 2px solid #ffc107;
        padding: 1.2rem;
        border-radius: 15px;
        margin: 1rem 0;
        color: #856404;
        font-weight: 500;
        box-shadow: 0 4px 8px rgba(255, 193, 7, 0.2);
    }
    .warning-box h4 {
        color: #856404 !important;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    .warning-box ul {
        margin: 0;
        padding-left: 1.2rem;
    }
    .warning-box li {
        color: #856404 !important;
        margin-bottom: 0.3rem;
        font-weight: 500;
    }
    .status-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border: 2px solid #6c757d;
        border-radius: 15px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        box-shadow: 0 4px 8px rgba(108, 117, 125, 0.15);
        color: #495057;
    }
    .status-card h4 {
        color: #495057 !important;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    .status-card p {
        color: #495057 !important;
        margin: 0;
        font-weight: 500;
    }
    .success-card {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 2px solid #28a745;
        border-radius: 15px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        box-shadow: 0 4px 8px rgba(40, 167, 69, 0.2);
        color: #155724;
    }
    .success-card h4 {
        color: #155724 !important;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    .success-card p {
        color: #155724 !important;
        margin: 0;
        font-weight: 500;
    }
    .error-card {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border: 2px solid #dc3545;
        border-radius: 15px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        box-shadow: 0 4px 8px rgba(220, 53, 69, 0.2);
        color: #721c24;
    }
    .error-card h4 {
        color: #721c24 !important;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    .error-card p {
        color: #721c24 !important;
        margin: 0;
        font-weight: 500;
    }
    .loading-animation {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
    .spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #1f77b4;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .progress-step {
        background: #e9ecef;
        border-radius: 15px;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        border-left: 4px solid #007bff;
    }
    .progress-step.active {
        background: #cce5ff;
        border-left-color: #0056b3;
        font-weight: bold;
    }
    .progress-step.completed {
        background: #d4edda;
        border-left-color: #28a745;
    }
</style>
""", unsafe_allow_html=True)

def verificar_api():
    """Verifica se a API está funcionando e retorna status"""
    try:
        response = requests.get(f"{API_URL}/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, {"erro": f"API retornou status {response.status_code}"}
    except Exception as e:
        return False, {"erro": f"Não conseguiu conectar à API: {str(e)}"}

def verificar_configuracao_ia():
    """Verifica se a configuração de IA está funcionando"""
    try:
        response = requests.get(f"{API_URL}/configuracao", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, {"erro": f"Erro ao verificar configuração: {response.status_code}"}
    except Exception as e:
        return False, {"erro": f"Erro de conexão: {str(e)}"}

def mostrar_progresso_ia(etapas):
    """Mostra progresso das etapas da análise de IA"""
    progress_container = st.empty()
    
    for i, etapa in enumerate(etapas):
        progress_html = "<div style='margin: 1rem 0;'>"
        
        for j, step_name in enumerate(etapas):
            if j < i:
                class_name = "progress-step completed"
                icon = "✅"
            elif j == i:
                class_name = "progress-step active"
                icon = "🔄"
            else:
                class_name = "progress-step"
                icon = "⏳"
            
            progress_html += f"""
            <div class="{class_name}">
                {icon} {step_name}
            </div>
            """
        
        progress_html += "</div>"
        progress_container.markdown(progress_html, unsafe_allow_html=True)
        
        time.sleep(1)  # Simular tempo de processamento
    
    # Mostrar conclusão
    final_html = "<div style='margin: 1rem 0;'>"
    for step_name in etapas:
        final_html += f"""
        <div class="progress-step completed">
            ✅ {step_name}
        </div>
        """
    final_html += "</div>"
    progress_container.markdown(final_html, unsafe_allow_html=True)

# Header principal
st.markdown("""
<div class="main-header">
    <h1>🏥 Sistema de Medicamentos MedAI</h1>
    <p>Busca inteligente baseada em dados oficiais da ANVISA</p>
</div>
""", unsafe_allow_html=True)

# Sidebar - status e configurações
st.sidebar.title("⚙️ Status do Sistema")

# Configurações
top_k = st.sidebar.slider("Número de resultados", 3, 10, 5)

# Verificar status da API 
api_ok, status_data = verificar_api()
config_ok, config_data = verificar_configuracao_ia()

# Status do sistema
if api_ok and status_data.get("medicamentos_carregados", 0) > 0:
    st.sidebar.success("🟢 Sistema ativo")
    st.sidebar.info(f"📊 {status_data['medicamentos_carregados']} medicamentos")
else:
    st.sidebar.error("🔴 Sistema com problemas")
    if not api_ok:
        st.error(f"**❌ Erro:** {status_data.get('erro', 'API não encontrada')}")
        
        # Instruções específicas baseado no ambiente
        if "medai-api" in API_URL:
            st.info("**💡 Solução para Docker:** Verifique se ambos os containers estão rodando")
            st.code("docker-compose ps")
        else:
            st.info("**💡 Solução para Local:** Execute `python3 api.py` em outro terminal")
            st.code("python3 api.py")
        st.stop()

# Verificar configuração de IA
if config_ok:
    ia_status = config_data.get("ia_disponivel", False)
    if ia_status:
        st.sidebar.success("🤖 IA disponível")
    else:
        st.sidebar.warning("⚠️ IA não configurada")
        if config_data.get("problemas"):
            for problema in config_data["problemas"]:
                st.sidebar.error(f"• {problema}")
else:
    st.sidebar.error("❌ Erro ao verificar IA")

# Cria três abas principais para organizar as funcionalidades da aplicação
tab1, tab2, tab3 = st.tabs(["🔍 Busca por Sintomas", "💊 Busca Medicamento", "📈 Estatísticas"])

# TAB 1: BUSCA POR SINTOMAS
with tab1:
    st.header("🔍 Busca por Sintomas")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Formulário principal para entrada de sintomas do usuário
        with st.form("busca_sintomas"):
            sintomas = st.text_area(
                "Descreva os sintomas:",
                height=100, # Altura da caixa de texto
                placeholder="Ex: dores de cabeça intensas, náuseas, tontura...",
                help="Descreva seus sintomas de forma detalhada para obter melhores resultados"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                buscar = st.form_submit_button("🔍 Buscar", use_container_width=True)
            with col_btn2:
                buscar_ia = st.form_submit_button(
                    "🤖 Análise com IA", 
                    use_container_width=True,
                    disabled=not (config_ok and config_data.get("ia_disponivel", False))
                )
        
        # Processar busca simples
        if buscar and sintomas:
            # Busca rápida usando API
            with st.spinner("🔍 Buscando medicamentos..."):
                try:
                    # Chamar API 
                    response = requests.post(
                        f"{API_URL}/busca_simples",
                        json={"sintomas": sintomas, "top_k": top_k},
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        medicamentos = data.get("medicamentos", [])
                        
                        if "erro" in str(medicamentos): # Verificar se houve erro na busca
                            st.error(f"❌ Erro: {medicamentos}")
                        elif medicamentos:
                            st.success(f"✅ {len(medicamentos)} medicamentos encontrados")
                            
                            # Mostrar resultados para cada medicamento com score de similaridade
                            for i, med in enumerate(medicamentos, 1):
                                similarity = med.get('similaridade', 0) * 100
                                
                                # Cor baseada na similaridade
                                if similarity >= 80:
                                    similarity_color = "🟢"
                                elif similarity >= 60:
                                    similarity_color = "🟡"
                                else:
                                    similarity_color = "🔴"
                                
                                with st.expander(f"#{i} - {med.get('principio_ativo', 'N/A')} {similarity_color} ({similarity:.1f}%)"):
                                    col_med1, col_med2 = st.columns(2) # Duas colunas para informações
                                    
                                    with col_med1:
                                        st.write(f"**🏷️ Categoria:** {med.get('categoria_terapeutica', 'N/A')}")
                                        st.write(f"**📊 Popularidade:** {med.get('popularidade', 'N/A')}")
                                        st.write(f"**📦 Produtos:** {med.get('total_produtos', 'N/A')}")
                                    
                                    with col_med2:
                                        st.write(f"**🏢 Empresas:** {med.get('empresas_exemplo', 'N/A')}")
                                        st.write(f"**💊 Exemplos:** {med.get('produtos_exemplo', 'N/A')}")
                        else:
                            st.warning("⚠️ Nenhum medicamento encontrado para esses sintomas")
                    else:
                        st.error(f"❌ Erro na API: {response.status_code}")
                        
                except Exception as e:
                    st.error(f"❌ Erro de conexão: {e}")
        
        # Análise com IA
        elif buscar_ia and sintomas:
            if config_ok and config_data.get("ia_disponivel", False):
                # Container para progresso
                progress_container = st.container()
                result_container = st.container()
                
                with progress_container:
                    st.info("🤖 **Iniciando análise com Inteligência Artificial...**")
                    
                    # Etapas do progresso
                    etapas = [
                        "Inicializando agentes especializados",
                        "Analisando sintomas com banco vetorial",
                        "Consultando base de medicamentos ANVISA",
                        "Avaliando segurança e riscos",
                        "Buscando orientações médicas online",
                        "Gerando relatório final"
                    ]
                    
                    # Mostrar progresso simulado
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Fazer requisição para análise IA
                        response = requests.post(
                            f"{API_URL}/analisar_sintomas",
                            json={"descricao": sintomas},
                            timeout=180  # 3 minutos
                        )
                        
                        # Simular progresso enquanto processa
                        for i, etapa in enumerate(etapas):
                            progress_bar.progress((i + 1) / len(etapas))
                            status_text.text(f"🔄 {etapa}...")
                            time.sleep(0.5)
                        
                        if response.status_code == 200:
                            resultado_completo = response.json()
                            
                            progress_bar.progress(1.0)
                            status_text.text("✅ Análise concluída!")
                            
                            if resultado_completo["status"] == "sucesso":
                                with result_container:
                                    st.success("🎉 **Análise com IA concluída com sucesso!**")
                                    
                                    # Mostrar relatório completo
                                    with st.expander("📋 **Relatório Completo da Análise**", expanded=True):
                                        st.markdown("### 🤖 Análise dos Agentes IA")
                                        
                                        # Formatear melhor a saída
                                        analise_text = resultado_completo["analise"]
                                        
                                        # Tentar dividir em seções se possível
                                        if "Especialista em Medicamentos" in analise_text or "Analista de Segurança" in analise_text:
                                            st.markdown("#### 💊 Especialista em Medicamentos ANVISA")
                                            st.markdown("#### 🛡️ Analista de Segurança e Orientação Médica")
                                        
                                        st.markdown(analise_text)
                                    
                                    # Informações técnicas FORA do expander principal
                                    if "configuracao" in resultado_completo:
                                        with st.expander("🔧 **Informações Técnicas da Análise**"):
                                            st.json(resultado_completo["configuracao"])
                            else:
                                progress_bar.empty()
                                status_text.empty()
                                st.error(f"❌ **Erro na análise:** {resultado_completo.get('erro', 'Erro desconhecido')}")
                                
                                # Mostrar detalhes do erro se disponível 
                                if "tipo_erro" in resultado_completo:
                                    st.error(f"**🔍 Tipo de erro:** {resultado_completo['tipo_erro']}")
                                
                                # Dicas para resolver o problema
                                st.info("💡 **Dicas para resolver:**")
                                st.write("• Verifique se a GEMINI_API_KEY está configurada")
                                st.write("• Reinicie a API se necessário")
                                st.write("• Tente novamente em alguns segundos")
                        else:
                            progress_bar.empty()
                            status_text.empty()
                            st.error(f"❌ **Erro na análise:** Código {response.status_code}")
                            
                            # Tentar mostrar detalhes do erro
                            try:
                                error_detail = response.json()
                                st.error(f"**Detalhes:** {error_detail.get('detail', 'Sem detalhes')}")
                            except:
                                st.error("**Detalhes:** Não foi possível obter detalhes do erro")
                            
                    except requests.exceptions.Timeout:
                        progress_bar.empty()
                        status_text.empty()
                        st.error("⏰ **Timeout:** A análise demorou mais que o esperado. Tente novamente.")
                    except Exception as e:
                        progress_bar.empty()
                        status_text.empty()
                        st.error(f"❌ **Erro inesperado:** {e}")
            else:
                st.error("🤖 **IA não disponível.** Configure as chaves de API no arquivo .env")
        
        elif (buscar or buscar_ia) and not sintomas:
            st.warning("⚠️ Por favor, descreva os sintomas") # Aviso se tentar buscar sem sintomas
    
    with col2:
        # Avisos importantes para o usuário não deixar de consultar um médico
        st.markdown("""
        <div class="warning-box">
            <h4>⚠️ Avisos Importantes</h4>
            <ul>
                <li>Sistema apenas informativo</li>
                <li>Não substitui consulta médica</li>
                <li>Sempre consulte um profissional</li>
                <li>Não pratique automedicação</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Status da IA
        if config_ok:
            if config_data.get("ia_disponivel"):
                st.markdown("""
                <div class="success-card">
                    <h4>🤖 Inteligência Artificial Ativada</h4>
                    <p>✨ Análise avançada com agentes especializados pronta para uso!</p>
                    <p>🎯 Recomendações personalizadas • 🛡️ Análise de segurança • 🔗 Links para consultas</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="error-card">
                    <h4>🤖 IA Não Configurada</h4>
                    <p>⚠️ Configure as chaves de API para usar análise avançada</p>
                    <p>📝 Edite o arquivo .env com sua GEMINI_API_KEY</p>
                </div>
                """, unsafe_allow_html=True)

# TAB 2: BUSCA POR MEDICAMENTO - DETALHES COMPLETOS
with tab2:
    st.header("💊 Detalhes do Medicamento")

    # Campo de entrada de nome do medicamento
    nome_medicamento = st.text_input(
        "Digite o nome do medicamento:",
        placeholder="Ex: paracetamol, ibuprofeno, amoxicilina...",  # Exemplos para orientar usuário
        help="Digite o nome do princípio ativo ou nome comercial"
    )

    if st.button("🔍 Buscar Detalhes", use_container_width=True) and nome_medicamento:
        # Validação 
        if len(nome_medicamento.strip()) >= 3:
            with st.spinner("🔍 Buscando detalhes..."):
                try:
                    
                    response = requests.post(
                        f"{API_URL}/detalhes_medicamento",
                        json={"nome_medicamento": nome_medicamento},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()  # Convertendo a resposta para dicionário
                        
                        # Verificando erros ou a ausência de resultados
                        if "erro" in data:
                            st.error(f"❌ **Erro:** {data['erro']}")
                        elif "message" in data:
                            st.warning(f"⚠️ {data['message']}")  # Caso o medicamento não seja encontrado
                        else:
                            # Exibindo as informações detalhadas do medicamento
                            st.success(f"✅ **Medicamento encontrado:** {data.get('principio_ativo', 'N/A')}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"### 💊 {data.get('principio_ativo', 'N/A')}")
                                st.write(f"**🏷️ Categoria Terapêutica:** {data.get('categoria_terapeutica', 'N/A')}")
                                st.write(f"**📊 Popularidade:** {data.get('popularidade_mercado', 'N/A')}")
                                st.write(f"**📦 Produtos Disponíveis:** {data.get('total_produtos', 'N/A')}")
                            
                            with col2:
                                st.write(f"**🔄 Diversidade de Formulações:** {data.get('diversidade_formulacoes', 'N/A')}")
                                st.write(f"**🏢 Empresas Responsáveis:** {data.get('empresas_exemplo', 'N/A')}")
                            
                            with st.expander("📄 **Informações Completas**", expanded=True):
                                st.text_area(
                                    "Dados completos:",
                                    data.get('texto_completo', 'Informações não disponíveis'),
                                    height=200,
                                    disabled=True
                                )  # Exibindo todas as informações do medicamento
                    elif response.status_code == 404:
                        st.error("❌ **Medicamento não encontrado**")
                        st.info("💡 **Dica:** Tente usar o nome do princípio ativo ou verifique a grafia")
                    else:
                        st.error(f"❌ **Erro na API:** Código {response.status_code}")
                        
                except Exception as e:
                    st.error(f"❌ **Erro de conexão:** {e}")
        else:
            st.error("❌ **Nome do medicamento deve ter pelo menos 3 caracteres**")


# TAB 3: ESTATÍSTICAS
with tab3:
    st.header("📈 Estatísticas do Sistema")
    
    # Usar dados da API 
    try:
        # Buscar alguns medicamentos para gerar estatísticas básicas
        response = requests.post(
            f"{API_URL}/busca_simples",
            json={"sintomas": "medicamento", "top_k": 10},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            medicamentos = data.get("medicamentos", [])
            
            if medicamentos:
                # Converter para DataFrame para análise
                df_stats = pd.DataFrame(medicamentos)
                
                # Métricas principais baseadas na amostra
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "📊 Amostra Analisada", 
                        len(df_stats),
                        help="Número de medicamentos na amostra atual"
                    ) # Contagem da amostra
                
                with col2:
                    if 'categoria_terapeutica' in df_stats.columns:
                        st.metric(
                            "🏷️ Categorias", 
                            df_stats['categoria_terapeutica'].nunique(),
                            help="Número de categorias terapêuticas únicas"
                        ) # Categorias únicas na amostra
                    else:
                        st.metric("🏷️ Categorias", "N/A")
                
                with col3:
                    if 'total_produtos' in df_stats.columns:
                        total_produtos = pd.to_numeric(df_stats['total_produtos'], errors='coerce').sum()
                        st.metric(
                            "📦 Total Produtos", 
                            int(total_produtos) if not pd.isna(total_produtos) else 0,
                            help="Soma total de produtos registrados"
                        ) # Soma de produtos na amostra
                    else:
                        st.metric("📦 Total Produtos", "N/A")
                
                with col4:
                    if 'total_produtos' in df_stats.columns:
                        avg_products = pd.to_numeric(df_stats['total_produtos'], errors='coerce').mean()
                        st.metric(
                            "📊 Média Produtos", 
                            f"{avg_products:.1f}" if not pd.isna(avg_products) else "N/A",
                            help="Média de produtos por medicamento"
                        ) # Média de produtos por medicamento na amostra
                    else:
                        st.metric("📊 Média Produtos", "N/A")
                
                # Gráficos baseados na amostra
                col1, col2 = st.columns(2)
                
                with col1:
                    # Top categorias terapêuticas da amostra
                    if 'categoria_terapeutica' in df_stats.columns:
                        cat_counts = df_stats['categoria_terapeutica'].value_counts().head(5)
                        if not cat_counts.empty:
                            fig1 = px.bar(
                                x=cat_counts.values,
                                y=cat_counts.index,
                                orientation='h',
                                title="🏆 Top 5 Categorias na Amostra",
                                labels={'x': 'Quantidade', 'y': 'Categoria'}
                            )
                            fig1.update_layout(height=400)
                            st.plotly_chart(fig1, use_container_width=True)
                        else:
                            st.info("📊 Dados de categoria não disponíveis para gráfico")
                    else:
                        st.info("📊 Dados de categoria não disponíveis")
                
                with col2:
                    # Distribuição popularidade do mercado da amostra
                    if 'popularidade' in df_stats.columns:
                        pop_counts = df_stats['popularidade'].value_counts()
                        if not pop_counts.empty:
                            fig2 = px.pie(
                                values=pop_counts.values,
                                names=pop_counts.index,
                                title="📈 Distribuição por Popularidade na Amostra"
                            )
                            fig2.update_layout(height=400)
                            st.plotly_chart(fig2, use_container_width=True)
                        else:
                            st.info("📊 Dados de popularidade não disponíveis para gráfico")
                    else:
                        st.info("📊 Dados de popularidade não disponíveis")
                        
                st.info("📊 **Nota:** Estatísticas baseadas em amostra de medicamentos. Para dados completos, acesse a API diretamente.")
            else:
                st.warning("⚠️ Não foi possível carregar dados para estatísticas")
        else:
            st.error("❌ Erro ao carregar dados para estatísticas")
            
    except Exception as e:
        st.error(f"❌ Erro ao gerar estatísticas: {e}")
        st.info(f"💡 **Dica:** Verifique se a API está rodando em {API_URL}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <h4>🏥 Sistema de Medicamentos MedAI</h4>
    <p>Interface via API | Dados oficiais ANVISA | Apenas informativo</p>
    <p><small>⚠️ Este sistema não substitui orientação médica profissional</small></p>
</div>
""", unsafe_allow_html=True)