FROM python:3.12-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Instalar UV 
RUN pip install uv

WORKDIR /app

# Copiar requirements primeiro
COPY requirements.txt .

# Instalar dependências usando UV 
RUN uv pip install --system -r requirements.txt

# Copiar código da aplicação
COPY . .

# Processar dados se existir o arquivo na pasta data
RUN if [ -f "data/DADOS_ABERTOS_MEDICAMENTOS.csv" ]; then \
        echo "Processando dados da ANVISA..." && \
        python limpeza.py; \
    else \
        echo "Dados serão processados em runtime"; \
    fi

EXPOSE 8000 8501

CMD ["python", "api.py"]