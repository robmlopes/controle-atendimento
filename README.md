# Sistema de Controle de Atendimento e Agendamento Multi-Nicho

Sistema web de autoatendimento e agendamento para negócios de serviços (barbearias, manicures, cabeleireiros, dentistas, clínicas, consultórios, etc.).

Desenvolvido seguindo os princípios de **AI-First Software Engineering (AIF)** e **Loop Engineering Governance**, com arquitetura hexagonal pura, contratos formais verificados por fuzzing e isolamento multitenant estrito.

---

## 🚀 Como Iniciar Rapidamente

### No Windows (com WSL)
Basta dar um duplo clique no arquivo:
```cmd
iniciar.bat
```
Ele configura as dependências automaticamente, solicita a criação do primeiro negócio/dono (se for a primeira execução) e abre o navegador em `http://localhost:8000`.

### No Linux / WSL (Terminal)
```bash
sh scripts/iniciar.sh
```

Ou diretamente com `uvicorn`:
```bash
. .venv/bin/activate
export CONTROLE_DB=app.db
uvicorn --factory web.app:default_app --host 127.0.0.1 --port 8000
```

---

## 💼 Funcionalidades Principais

### 1. Painel do Dono da Agenda (`/painel`)
- **Autenticação Segura**: login com e-mail e senha criptografada via Argon2id, proteção contra força bruta e sessões com cookies seguros.
- **Link Personalizado de Acesso**: caixa destacada com a URL pública do negócio (ex.: `http://localhost:8000/n/minha-barbearia`) com botão interativo **"Copiar link"** e atalho para abrir a página pública.
- **Personalização da URL (`/negocio`)**: o dono pode alterar o endereço (slug) a qualquer momento com validação de formato e garantia de que nenhum outro negócio use a mesma URL.
- **Visão Geral do que está Cadastrado**:
  - Lista de **Profissionais** ativos com serviços vinculados e horários de atendimento semanais.
  - Lista de **Serviços** cadastrados com duração (em minutos) e preço formatado.
  - **Próximos Agendamentos** dos próximos 14 dias com atalho direto para conversar com o cliente via WhatsApp (`wa.me`).
- **Gestão de Profissionais e Escalas (`/profissionais`)**:
  - Cadastro de múltiplos profissionais por estabelecimento.
  - Definição da grade semanal de disponibilidade (ex.: Segunda a Sexta, 08:00 às 18:00).
  - Bloqueios de dias inteiros ou intervalos pontuais (folgas, feriados, pausas).
  - Seleção de quais serviços cada profissional está apto a executar.
- **Gestão de Serviços (`/servicos`)**:
  - Criação de serviços com nome, duração em minutos e preço opcional.
  - Visualização de quais profissionais realizam cada serviço.

### 2. Autoatendimento pelo Cliente (Sem Login)
- **Acesso pelo Link Personalizado**: o cliente entra em `/n/{slug}` direto pelo celular ou computador sem precisar criar conta ou fazer login.
- **Escolha Guiada**:
  1. Seleciona o profissional desejado ou o serviço pretendido.
  2. Escolhe a data no calendário (janela de até 30 dias).
  3. Visualiza **apenas os horários realmente livres**, calculados dinamicamente com base na duração do serviço selecionado.
- **Confirmação Instantânea**:
  - Informa apenas **Nome** e **WhatsApp**.
  - O agendamento é confirmado imediatamente na hora.
  - Tela de sucesso com link direto para o WhatsApp do estabelecimento (`wa.me`) com mensagem pronta contendo profissional, serviço, data e hora.
- **Link Privado de Comprovante (`/agendamento/{token}`)**:
  - Link exclusivo com token aleatório de alta entropia.
  - Permite que o cliente consulte os detalhes a qualquer momento ou realize o **cancelamento** com 1 clique (o que libera o horário imediatamente na agenda).

---

## 🛡️ Engenharia e Confiabilidade

- **Zero Agendamento Duplo (Zero Double-Booking)**: gravação atômica em transação SQLite `BEGIN IMMEDIATE`, verificando colisão com agendamentos confirmados no mesmo milissegundo antes da inserção. Em caso de colisão, o concorrente recebe HTTP 409 com mensagem amigável e redirecionamento.
- **Proteção Contra Spam**: limite máximo de 3 agendamentos ativos confirmados por número de WhatsApp no mesmo estabelecimento.
- **Segurança Web**:
  - Proteção CSRF com tokens em formulários autenticados e cookies double-submit para formulários públicos anônimos.
  - Cabeçalhos `Referrer-Policy: no-referrer` e `Cache-Control: no-store` para impedir vazamento de tokens privados em links externos (como `wa.me`).
  - Prevenção de XSS com escape automático em todos os templates Jinja2.

---

## 🏗️ Arquitetura do Código

```
├── domain/            # Regras de negócio puras (sem I/O, sem datetime, @contract)
│   ├── models.py      # Entidades imutáveis: Business, Professional, Service, Booking...
│   ├── slots.py       # Algoritmo puro de cálculo de horários vagos (free_slots)
│   ├── auth.py        # Validações puras de credenciais, sessões e rate limit
│   ├── panel.py       # Validações e formatações de formulários administrativos
│   └── public.py      # Normalização de telefone (E.164), slugs e limites
│
├── ports/             # Protocolos/Interfaces (typing.Protocol)
│   ├── catalog.py     # Portas de leitura e escrita do catálogo
│   ├── booking.py     # Portas de leitura e reserva atômica de horários
│   ├── admin.py       # Operações administrativas com isolamento por business_id
│   ├── auth.py        # Donos, sessões, hashers e tentativas de login
│   ├── agenda.py      # Visão consolidada da agenda
│   └── clock.py       # Porta de relógio do sistema
│
├── adapters/          # Implementações concretas de infraestrutura
│   ├── sqlite_db.py   # Gerenciador de conexão SQLite e migrações idempotentes
│   ├── sqlite_*.py    # Adaptadores SQLite de cada porta
│   ├── argon_hasher.py# Hashing seguro de senhas com Argon2id
│   └── system_clock.py# Relógio real (fuso America/Sao_Paulo) e gerador de tokens
│
├── web/               # Camada HTTP e apresentação (FastAPI + Jinja2)
│   ├── app.py         # Configuração da aplicação e injeção de dependências
│   ├── guard.py       # Proteção de sessão, multi-tenant e CSRF
│   ├── panel*.py      # Rotas administrativas (/painel, /profissionais, /servicos, /negocio)
│   ├── public*.py     # Rotas públicas (/n/{slug}, /n/{slug}/agendar, /agendamento/{token})
│   └── templates/     # Templates HTML server-side renderizados
│
└── tests/             # Testes automatizados (76 testes passando)
    ├── test_domain_*.py    # Testes unitários e fuzzing com Hypothesis
    ├── test_sqlite_*.py    # Testes de concorrência e persistência real
    ├── test_web_auth.py    # Testes de autenticação, força bruta e CSRF
    ├── test_web_panel.py   # Testes de isolamento multitenant e telas do painel
    └── test_web_public.py  # Testes de ponta a ponta do cliente público
```

---

## 🧪 Testes e Verificação de Qualidade

Para rodar toda a suíte de verificação do AIF (Ruff, Intents, AST Lints, Mypy Strict, Hypothesis Fuzzing e Pytest):
```bash
. .venv/bin/activate
aif check --json
```

Para rodar apenas os testes do pytest:
```bash
pytest -q
```
Resultado atual: **76 testes passando com 100% de sucesso**.
