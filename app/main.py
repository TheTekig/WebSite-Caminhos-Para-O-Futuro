import csv
import io
import json
import re
import secrets
import unicodedata
from datetime import date, datetime

from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import config, database

app = FastAPI(title=f"Sorteio — {config.EVENTO_NOME}")
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, same_site="lax")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalizar_data(valor: str) -> tuple[str | None, str | None]:
    """Valida uma data e devolve sempre no formato ISO (YYYY-MM-DD), não
    importa se ela chegou nesse formato (input type="date" do site) ou em
    formato brasileiro DD/MM/YYYY (comum em CSV exportado de planilha).
    Retorna (valor_normalizado, None) se for válida, ou (None, mensagem_de_erro)."""
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            data_valor = datetime.strptime(valor, formato).date()
        except ValueError:
            continue
        if data_valor > date.today():
            return None, "Não pode ser uma data no futuro."
        if data_valor.year < 1900:
            return None, "Data muito antiga, confira o ano."
        return data_valor.isoformat(), None
    return None, "Data inválida."


@app.on_event("startup")
def _startup():
    database.init_db()


def _base_ctx(**extra):
    ctx = {
        "evento_nome": config.EVENTO_NOME,
        "evento_tagline": config.EVENTO_TAGLINE,
        "evento_data": config.EVENTO_DATA,
        "evento_hora": config.EVENTO_HORA,
        "evento_datetime_iso": config.EVENTO_DATETIME_ISO,
        "evento_local": config.EVENTO_LOCAL,
        "evento_endereco": config.EVENTO_ENDERECO,
        "palestrantes": config.PALESTRANTES,
        "programacao": config.PROGRAMACAO,
        "patrocinadores": config.PATROCINADORES,
    }
    ctx.update(extra)
    return ctx


# ---------------------------------------------------------------------------
# Página pública: landing + formulário de inscrição
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def pagina_inscricao(request: Request):
    return templates.TemplateResponse(request, "index.html", _base_ctx(
        campos_extras=config.CAMPOS_EXTRAS,
        cpf_obrigatorio=config.CPF_OBRIGATORIO,
        perfis_inscricao=config.PERFIS_INSCRICAO,
        perfil_campos_json=json.dumps(config.PERFIL_CAMPOS, ensure_ascii=False),
    ))


@app.post("/api/inscricao")
async def criar_inscricao(request: Request):
    form = await request.form()
    nome = (form.get("nome") or "").strip()
    email = (form.get("email") or "").strip()
    telefone = (form.get("telefone") or "").strip()
    cpf = (form.get("cpf") or "").strip()

    erros = {}
    if len(nome) < 3:
        erros["nome"] = "Digite seu nome completo."
    if not EMAIL_RE.match(email):
        erros["email"] = "E-mail inválido."
    if len(re.sub(r"\D", "", telefone)) < 10:
        erros["telefone"] = "Telefone inválido. Inclua o DDD."
    if config.CPF_OBRIGATORIO and len(re.sub(r"\D", "", cpf)) != 11:
        erros["cpf"] = "CPF inválido."

    perfil = (form.get("perfil") or "").strip()
    if perfil not in config.PERFIS_INSCRICAO:
        erros["perfil"] = "Selecione um perfil válido."

    extra = {}
    if perfil in config.PERFIL_CAMPOS:
        campo_perfil = config.PERFIL_CAMPOS[perfil]
        valor_campo = (form.get(campo_perfil["id"]) or "").strip()
        if not valor_campo:
            erros[campo_perfil["id"]] = f"{campo_perfil['label']} é obrigatório."
        else:
            extra["perfil"] = perfil
            extra[campo_perfil["id"]] = valor_campo

    for campo in config.CAMPOS_EXTRAS:
        valor = (form.get(campo["id"]) or "").strip()
        if campo.get("obrigatorio") and not valor:
            erros[campo["id"]] = f"{campo['label']} é obrigatório."
        elif valor and campo.get("type") == "date":
            valor_norm, erro_data = normalizar_data(valor)
            if erro_data:
                erros[campo["id"]] = erro_data
            else:
                valor = valor_norm
        extra[campo["id"]] = valor

    if erros:
        return JSONResponse({"ok": False, "erros": erros}, status_code=400)

    if database.email_ja_existe(email):
        return JSONResponse(
            {"ok": False, "erros": {"email": "Esse e-mail já está inscrito."}},
            status_code=409,
        )

    inscricao_id = database.criar_inscricao(nome, email, telefone, cpf, extra)
    return JSONResponse({"ok": True, "id": inscricao_id})


# ---------------------------------------------------------------------------
# Autenticação simples do ADM (senha única, via sessão assinada)
# ---------------------------------------------------------------------------

def exigir_admin_pagina(request: Request):
    """Para rotas HTML: redireciona para o login se não estiver autenticado."""
    if not request.session.get("admin_ok"):
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    return True


def exigir_admin_api(request: Request):
    """Para rotas de API (chamadas via fetch): responde 401 em JSON."""
    if not request.session.get("admin_ok"):
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return True


@app.get("/admin/login", response_class=HTMLResponse)
def login_form(request: Request, erro: str | None = None):
    if request.session.get("admin_ok"):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(request, "admin_login.html", _base_ctx(erro=erro))


@app.post("/admin/login")
def login_submit(request: Request, senha: str = Form(...)):
    if secrets.compare_digest(senha, config.ADMIN_PASSWORD):
        request.session["admin_ok"] = True
        return RedirectResponse("/admin", status_code=303)
    return RedirectResponse("/admin/login?erro=1", status_code=303)


@app.post("/admin/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


# ---------------------------------------------------------------------------
# Painel ADM: lista de inscritos + tela de sorteio
# ---------------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, _=Depends(exigir_admin_pagina)):
    stats = database.contar_inscricoes()
    return templates.TemplateResponse(request, "admin.html", _base_ctx(
        stats=stats,
        campos_extras=config.CAMPOS_EXTRAS,
    ))


@app.get("/api/inscricoes")
def api_listar_inscricoes(request: Request, _=Depends(exigir_admin_api)):
    return {"inscricoes": database.listar_inscricoes(), "stats": database.contar_inscricoes()}


@app.post("/api/sortear")
def api_sortear(request: Request, excluir_ja_sorteados: bool = True, _=Depends(exigir_admin_api)):
    vencedor = database.sortear_vencedor(excluir_ja_sorteados=excluir_ja_sorteados)
    if not vencedor:
        return JSONResponse({"ok": False, "mensagem": "Não há mais inscritos disponíveis para sortear."}, status_code=400)
    return {"ok": True, "vencedor": vencedor, "stats": database.contar_inscricoes()}


@app.get("/api/vencedores")
def api_vencedores(request: Request, _=Depends(exigir_admin_api)):
    return {"vencedores": database.listar_vencedores()}


@app.post("/api/sorteio/resetar")
def api_resetar_sorteio(request: Request, _=Depends(exigir_admin_api)):
    database.resetar_sorteio()
    return {"ok": True, "stats": database.contar_inscricoes()}


@app.delete("/api/inscricoes/{inscricao_id}")
def api_excluir_inscricao(inscricao_id: int, request: Request, _=Depends(exigir_admin_api)):
    database.excluir_inscricao(inscricao_id)
    return {"ok": True}


@app.get("/api/inscricoes/exportar")
def exportar_csv(request: Request, _=Depends(exigir_admin_api)):
    inscricoes = database.listar_inscricoes()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    colunas_extras = [campo["label"] for campo in config.CAMPOS_EXTRAS]
    writer.writerow(
        ["Nome", "E-mail", "Telefone", "CPF", "Perfil", "Empresa/Matrícula"] + colunas_extras +
        ["Sorteado", "Posição no sorteio", "Inscrito em (UTC)"]
    )
    for i in inscricoes:
        extra = i.get("extra", {})
        perfil = extra.get("perfil", "")
        campo_perfil = config.PERFIL_CAMPOS.get(perfil)
        detalhe_perfil = extra.get(campo_perfil["id"], "") if campo_perfil else ""
        valores_extras = [extra.get(campo["id"], "") for campo in config.CAMPOS_EXTRAS]
        writer.writerow(
            [i["nome"], i["email"], i["telefone"], i["cpf"], perfil, detalhe_perfil] + valores_extras + [
                "Sim" if i["sorteado"] else "Não",
                i["posicao_sorteio"] or "",
                i["criado_em"],
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inscritos.csv"},
    )

@app.post("/api/inscricoes/importar")
async def importar_csv(
    request: Request,
    arquivo: UploadFile = File(...),
    _=Depends(exigir_admin_api),
):
    if not arquivo.filename:
        return JSONResponse(
            {
                "ok": False,
                "mensagem": "Nenhum arquivo foi enviado."
            },
            status_code=400,
        )

    if not arquivo.filename.lower().endswith(".csv"):
        return JSONResponse(
            {
                "ok": False,
                "mensagem": "O arquivo precisa estar no formato CSV."
            },
            status_code=400,
        )

    # Limite de segurança: 5 MB
    conteudo = await arquivo.read()

    if len(conteudo) > 5 * 1024 * 1024:
        return JSONResponse(
            {
                "ok": False,
                "mensagem": "O arquivo CSV é muito grande. Limite de 5 MB."
            },
            status_code=400,
        )

    # Tenta UTF-8 com BOM, UTF-8 normal e, por último, Windows-1252
    texto = None

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            texto = conteudo.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if texto is None:
        return JSONResponse(
            {
                "ok": False,
                "mensagem": "Não foi possível ler o arquivo. Verifique a codificação do CSV."
            },
            status_code=400,
        )

    try:
        # Detecta automaticamente , ou ;
        primeira_linha = texto.splitlines()[0] if texto.splitlines() else ""

        if ";" in primeira_linha and "," not in primeira_linha:
            delimitador = ";"
        else:
            delimitador = ","

        reader = csv.DictReader(
            io.StringIO(texto),
            delimiter=delimitador,
        )

        if not reader.fieldnames:
            return JSONResponse(
                {
                    "ok": False,
                    "mensagem": "O CSV não possui cabeçalho."
                },
                status_code=400,
            )

        def normalizar_cabecalho(valor):
            valor = (valor or "").strip().lower()

            valor = unicodedata.normalize("NFKD", valor)
            valor = "".join(
                c for c in valor
                if not unicodedata.combining(c)
            )

            return valor

        # Mapeia os nomes das colunas
        colunas = {
            normalizar_cabecalho(coluna): coluna
            for coluna in reader.fieldnames
        }

        # Aceita algumas variações dos nomes
        def encontrar_coluna(*nomes):
            for nome in nomes:
                chave = normalizar_cabecalho(nome)

                if chave in colunas:
                    return colunas[chave]

            return None

        coluna_nome = encontrar_coluna(
            "nome",
            "nome completo",
        )

        coluna_email = encontrar_coluna(
            "email",
            "e-mail",
        )

        coluna_telefone = encontrar_coluna(
            "telefone",
            "telefone / whatsapp",
            "whatsapp",
        )

        coluna_cpf = encontrar_coluna(
            "cpf",
        )

        if not coluna_nome or not coluna_email or not coluna_telefone:
            return JSONResponse(
                {
                    "ok": False,
                    "mensagem": (
                        "O CSV precisa possuir pelo menos as colunas: "
                        "Nome, E-mail e Telefone."
                    ),
                    "colunas_recebidas": reader.fieldnames,
                },
                status_code=400,
            )

        importados = 0
        duplicados = 0
        erros = []

        emails_do_csv = set()

        for numero_linha, row in enumerate(reader, start=2):
            nome = (row.get(coluna_nome) or "").strip()
            email = (row.get(coluna_email) or "").strip().lower()
            telefone = (row.get(coluna_telefone) or "").strip()

            cpf = ""

            if coluna_cpf:
                cpf = (row.get(coluna_cpf) or "").strip()

            # Valida nome
            if len(nome) < 3:
                erros.append(
                    {
                        "linha": numero_linha,
                        "email": email,
                        "erro": "Nome inválido.",
                    }
                )
                continue

            # Valida e-mail
            if not EMAIL_RE.match(email):
                erros.append(
                    {
                        "linha": numero_linha,
                        "email": email,
                        "erro": "E-mail inválido.",
                    }
                )
                continue

            # Valida telefone
            if len(re.sub(r"\D", "", telefone)) < 10:
                erros.append(
                    {
                        "linha": numero_linha,
                        "email": email,
                        "erro": "Telefone inválido.",
                    }
                )
                continue

            # Valida CPF se obrigatório
            if config.CPF_OBRIGATORIO:
                if len(re.sub(r"\D", "", cpf)) != 11:
                    erros.append(
                        {
                            "linha": numero_linha,
                            "email": email,
                            "erro": "CPF inválido.",
                        }
                    )
                    continue

            # Evita duplicados dentro do próprio CSV
            if email in emails_do_csv:
                duplicados += 1
                continue

            emails_do_csv.add(email)

            # Evita duplicado que já existe no banco
            if database.email_ja_existe(email):
                duplicados += 1
                continue

            # Campos extras
            extra = {}

            for campo in config.CAMPOS_EXTRAS:
                coluna_extra = encontrar_coluna(
                    campo["id"],
                    campo["label"],
                )

                valor = ""

                if coluna_extra:
                    valor = (row.get(coluna_extra) or "").strip()

                if campo.get("obrigatorio") and not valor:
                    erros.append(
                        {
                            "linha": numero_linha,
                            "email": email,
                            "erro": f"{campo['label']} é obrigatório.",
                        }
                    )

                    break

                if valor and campo.get("type") == "date":
                    valor_norm, erro_data = normalizar_data(valor)
                    if erro_data:
                        erros.append(
                            {
                                "linha": numero_linha,
                                "email": email,
                                "erro": f"{campo['label']}: {erro_data}",
                            }
                        )

                        break

                    valor = valor_norm

                extra[campo["id"]] = valor

            else:
                database.criar_inscricao(
                    nome,
                    email,
                    telefone,
                    cpf,
                    extra,
                )

                importados += 1

        return {
            "ok": True,
            "mensagem": "Importação concluída.",
            "importados": importados,
            "duplicados": duplicados,
            "erros": len(erros),
            "detalhes_erros": erros,
            "stats": database.contar_inscricoes(),
        }

    except csv.Error as e:
        return JSONResponse(
            {
                "ok": False,
                "mensagem": f"Erro ao processar o CSV: {str(e)}",
            },
            status_code=400,
        )

    except Exception as e:
        return JSONResponse(
            {
                "ok": False,
                "mensagem": f"Erro inesperado ao importar CSV: {str(e)}",
            },
            status_code=500,
        )