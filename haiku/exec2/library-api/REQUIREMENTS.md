# Dependências do Projeto

## Produção

### FastAPI (0.104.1)
Framework web moderno para Python. Cria APIs REST com validação automática.
- Documentação automática com Swagger UI
- Type hints nativos
- Performance otimizada

### Uvicorn (0.24.0)
Servidor ASGI para executar a aplicação FastAPI.
- Suporta async/await
- Hot reload automático
- Produção-ready

### SQLAlchemy (2.0.23)
ORM (Object-Relational Mapping) para Python. Abstrai operações de banco de dados.
- Suporta múltiplos bancos (SQLite, PostgreSQL, MySQL, etc)
- Query builder poderoso
- Type hints completos

### Pydantic (2.5.0)
Validação de dados e serialização usando type hints.
- Validação em tempo de execução
- Serialização JSON automática
- Mensagens de erro detalhadas

### Pydantic Settings (2.1.0)
Gerenciamento de configuração com Pydantic.
- Lê variáveis de ambiente
- Validação de config
- Suporte a .env files

### python-jose[cryptography] (3.3.0)
Implementação de JWT (JSON Web Tokens) para autenticação.
- Criptografia assimétrica
- Algoritmo HS256 para tokens
- Validação de assinatura

### passlib[bcrypt] (1.7.4)
Hash seguro de senhas.
- Algoritmo bcrypt (adaptativo)
- Resistente a ataques por força bruta
- Salt automático

### python-multipart (0.0.6)
Suporte a multipart/form-data no FastAPI.
- Necessário para upload de files
- Parsing de forms

## Desenvolvimento e Testes

### pytest (7.4.3)
Framework de testes para Python.
- Descoberta automática de testes
- Fixtures poderosas
- Relatórios detalhados

### pytest-asyncio (0.21.1)
Plugin para rodar testes async com pytest.
- Suporta async/await nos testes
- Integração com event loop

### httpx (0.25.1)
Cliente HTTP moderno e assíncrono.
- Used pelo TestClient do FastAPI
- Suporta requests sync e async
- Type hints completos

## Versões Recomendadas

Python 3.9 ou superior (recomendado 3.11+)

```bash
python --version
# Python 3.9.x ou superior
```

## Instalação

### 1. Criar ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 2. Atualizar pip
```bash
pip install --upgrade pip
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

## Verificar Instalação

```bash
# Verificar que tudo foi instalado
pip list | grep -E "fastapi|uvicorn|sqlalchemy|pydantic|python-jose|passlib"

# Testar importações
python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
python -c "import sqlalchemy; print(f'SQLAlchemy {sqlalchemy.__version__}')"
```

## Comandos Úteis

### Atualizar dependências
```bash
pip install --upgrade -r requirements.txt
```

### Gerar requirements.txt atualizado
```bash
pip freeze > requirements.txt
```

### Desinstalar tudo
```bash
pip uninstall -r requirements.txt -y
```

### Verificar vulnerabilidades
```bash
pip install safety
safety check
```

## Notas de Compatibilidade

### FastAPI
- Requer Starlette 0.27.0+
- Requer Pydantic 2.0+

### SQLAlchemy
- Versão 2.0 usa novo style API
- Mudanças na forma de criar engines e sessions

### Pydantic
- Versão 2.0 quebra compatibilidade com v1
- Use `from_attributes = True` em `Config` para ORM models

## Produção vs Desenvolvimento

### Para Produção
Substitua uvicorn por:
```bash
pip install gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

### Para Desenvolvimento
Use o arquivo requirements.txt que inclui pytest e dependências de teste.

Para remover dependências de teste em produção:
```bash
pip install -r requirements.txt --ignore-installed --no-cache-dir
```

## Troubleshooting

### Erro: "No module named 'app'"
```bash
# Certifique-se de estar no diretório correto
cd library-api
# Ative o ambiente virtual
source venv/bin/activate
```

### Erro: "Permission denied" ao instalar
```bash
# Use --user flag
pip install --user -r requirements.txt
```

### Erro: "version conflict"
```bash
# Limpe cache e reinstale
pip cache purge
pip install -r requirements.txt --force-reinstall
```
