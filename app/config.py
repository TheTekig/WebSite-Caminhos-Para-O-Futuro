"""
Configurações da aplicação.

Tudo que muda de evento para evento fica aqui. Em produção, troque
ADMIN_PASSWORD e SECRET_KEY por variáveis de ambiente (veja o README) em
vez de deixar hardcoded no código.
"""
import os

# --- Identidade do evento ---
EVENTO_NOME = os.getenv("EVENTO_NOME", "Caminhos para o Futuro")
EVENTO_TAGLINE = os.getenv("EVENTO_TAGLINE", "Sonhos que viram realidade")
EVENTO_DATA = os.getenv("EVENTO_DATA", "17 de setembro de 2026")
EVENTO_HORA = os.getenv("EVENTO_HORA", "10h30")
# Data/hora em ISO 8601 (usado pelo contador regressivo em JS)
EVENTO_DATETIME_ISO = os.getenv("EVENTO_DATETIME_ISO", "2026-09-17T10:30:00-03:00")
EVENTO_LOCAL = os.getenv("EVENTO_LOCAL", "Auditório IFES, Campus Colatina")
EVENTO_ENDERECO = os.getenv("EVENTO_ENDERECO", "IFES Campus Colatina, Colatina - ES")

# --- Acesso ao painel ADM ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SECRET_KEY = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao-por-algo-aleatorio")

# --- Banco de dados ---
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "sorteio.db"))

# --- Campos extras do formulário ---
# Para adicionar um novo campo ao formulário sem mexer no banco de dados,
# adicione um item aqui. type pode ser: "text", "email", "tel", "number"
CAMPOS_EXTRAS = [
    # {"id": "curso", "label": "Curso", "type": "text", "obrigatorio": False},
    {"id": "data_nascimento", "label": "Data de nascimento", "type": "date", "obrigatorio": True},
]

CPF_OBRIGATORIO = os.getenv("CPF_OBRIGATORIO", "false").lower() == "true"

# --- Perfil do inscrito ---
# Cada perfil pode exigir um campo específico adicional no formulário.
# O valor digitado nesse campo é salvo dentro do JSON `extra` da inscrição,
# junto com o próprio perfil escolhido (sem criar colunas novas no banco).
PERFIS_INSCRICAO = ["Empresário", "Servidor", "Estudante"]

PERFIL_CAMPOS = {
    "Empresário": {"id": "nome_empresa", "label": "Nome da empresa"},
    "Servidor": {"id": "matricula_siape", "label": "Matrícula / SIAPE"},
    "Estudante": {"id": "matricula", "label": "Matrícula"},
}

# --- Palestrantes ---
PALESTRANTES = [
    {
        "nome": "Rafael Furlanetti",
        "cargo": "Sócio-Diretor Institucional da XP Inc. e Presidente do Conselho de Administração da ANCORD",
        "bio": "Executivo com ampla trajetória no mercado financeiro, atua na condução estratégica da XP Inc. e na presidência do Conselho de Administração da ANCORD, contribuindo para o fortalecimento do mercado de capitais e da educação financeira no Brasil.",
        "foto": "/static/img/palestrantes/5.jpeg",
        "foto_hero": "/static/img/palestrantes/images.jpg",
        # Fotos extras que aparecem "espiando" atrás do card principal no Hero
        # (até 2 são usadas). Deixe vazio pra mostrar só o card principal.
        "fotos_hero_extra": ["/static/img/palestrantes/8.avif","/static/img/palestrantes/7.webp",],
    },
]

# --- Programação ---
PROGRAMACAO = [
    {"hora": "10h30", "titulo": "Abertura", "descricao": "Recepção e abertura oficial do Caminhos para o Futuro."},
    {"hora": "10h40", "titulo": "Palestra", "descricao": "Sonhos que viram realidade, com Rafael Furlanetti / XP Inc."},
    {"hora": "12h00", "titulo": "Encerramento", "descricao": "Considerações finais e networking."},
]

# --- Apoio / realização ---
PATROCINADORES = [
    {"nome": "Instituto Federal do Espírito Santo - Campus Colatina", "logo": "/static/img/patrocinadores/3.png"},
    {"nome": "XP Investimentos", "logo": "/static/img/patrocinadores/2.png"},
    {"nome": "ASSEDIC", "logo": "/static/img/patrocinadores/4.png"},
]
