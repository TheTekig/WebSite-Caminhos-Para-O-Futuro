(function () {

  "use strict";

  // --------------------- Elementos da página ---------------------

  const tbody = document.getElementById("tbody-inscritos");
  const busca = document.getElementById("busca-inscritos");

  const statTotal = document.getElementById("stat-total");
  const statDisponiveis = document.getElementById("stat-disponiveis");
  const statSorteados = document.getElementById("stat-sorteados");

  const listaVencedores = document.getElementById("lista-vencedores");
  const vencedoresVazio = document.getElementById("vencedores-vazio");

  const toast = document.getElementById("toast");

  // Tela de sorteio
  const overlay = document.getElementById("sorteio-overlay");
  const sorteioNome = document.getElementById("sorteio-nome");
  const sorteioEyebrow = document.getElementById("sorteio-eyebrow");
  const sorteioGlow = document.getElementById("sorteio-glow");
  const sorteioCta = document.getElementById("sorteio-cta");

  const btnAbrirSorteio = document.getElementById("btn-abrir-sorteio");
  const btnFecharSorteio = document.getElementById("btn-fechar-sorteio");
  const btnFecharSorteio2 = document.getElementById("btn-fechar-sorteio-2");
  const btnSortearOutro = document.getElementById("btn-sortear-outro");
  const btnResetar = document.getElementById("btn-resetar");

  // Importação CSV
  const btnEscolherCsv = document.getElementById("btn-escolher-csv");
  const inputCsv = document.getElementById("arquivo-csv");
  const resultadoImportacao = document.getElementById("resultado-importacao");


  // --------------------- Estado ---------------------

  let inscritos = [];
  let cicloTimer = null;


  // --------------------- Utilitários ---------------------

  function mostrarToast(msg, tipo) {
    toast.textContent = msg;
    toast.className = "toast mostrar" + (tipo === "erro" ? " erro" : "");

    setTimeout(() => {
      toast.className = "toast";
    }, 3200);
  }


  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  function formatarData(isoUtc) {
    if (!isoUtc) return "-";
    const data = new Date(isoUtc.endsWith("Z") ? isoUtc : isoUtc + "Z");
    if (isNaN(data.getTime())) return "-";
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  // Compatível com inscrições antigas: `extra` pode não existir ou vir vazio.
  function detalheDoPerfil(extra) {
    if (!extra) return "-";
    return extra.nome_empresa || extra.matricula || extra.matricula_siape || "-";
  }


  // --------------------- Tabela de inscritos ---------------------

  function renderTabela(filtro) {

    const termo = (filtro || "").trim().toLowerCase();

    const linhas = inscritos.filter((i) =>
      !termo ||
      i.nome.toLowerCase().includes(termo) ||
      i.email.toLowerCase().includes(termo)
    );

    if (!linhas.length) {

      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="vazio-estado">
            Nenhum inscrito encontrado.
          </td>
        </tr>
      `;

      return;
    }

    tbody.innerHTML = linhas.map((i) => `
      <tr>
        <td>${escapeHtml(i.nome)}</td>

        <td>${escapeHtml(i.email)}</td>

        <td>${escapeHtml(i.telefone)}</td>

        <td>${escapeHtml(i.cpf) || "-"}</td>

        <td>${escapeHtml((i.extra && i.extra.perfil) || "-")}</td>

        <td>${escapeHtml(detalheDoPerfil(i.extra))}</td>

        <td class="col-muted">${formatarData(i.criado_em)}</td>

        <td>
          ${
            i.sorteado
              ? '<span class="badge ganhou">Sorteado</span>'
              : "—"
          }
        </td>

        <td>
          <button
            class="link-excluir"
            data-id="${i.id}"
          >
            excluir
          </button>
        </td>
      </tr>
    `).join("");
  }


  // --------------------- Vencedores ---------------------

  function renderVencedores(vencedores) {

    if (!vencedores.length) {

      listaVencedores.innerHTML = `
        <p
          class="vazio-estado"
          id="vencedores-vazio"
        >
          Ninguém foi sorteado ainda.
        </p>
      `;

      return;
    }

    listaVencedores.innerHTML = vencedores.map((v) => `
      <div class="vencedor-item">

        <span class="pos">
          ${v.posicao_sorteio}
        </span>

        <span>
          ${escapeHtml(v.nome)}
        </span>

      </div>
    `).join("");
  }


  // --------------------- Estatísticas ---------------------

  function atualizarStats(stats) {

    statTotal.textContent = stats.total;
    statDisponiveis.textContent = stats.disponiveis;
    statSorteados.textContent = stats.sorteados;
  }


  // --------------------- Carregar inscritos ---------------------

  async function carregarInscritos() {

    try {

      const resp = await fetch("/api/inscricoes");

      if (resp.status === 401) {
        window.location.href = "/admin/login";
        return;
      }

      if (!resp.ok) {
        throw new Error("Não foi possível carregar os inscritos.");
      }

      const json = await resp.json();

      inscritos = json.inscricoes;

      atualizarStats(json.stats);
      renderTabela(busca.value);

    } catch (erro) {

      console.error("Erro ao carregar inscritos:", erro);

      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="vazio-estado">
            Erro ao carregar inscritos.
          </td>
        </tr>
      `;

      mostrarToast(
        "Erro ao carregar os inscritos.",
        "erro"
      );
    }
  }


  // --------------------- Carregar vencedores ---------------------

  async function carregarVencedores() {

    try {

      const resp = await fetch("/api/vencedores");

      if (resp.status === 401) {
        window.location.href = "/admin/login";
        return;
      }

      if (!resp.ok) {
        throw new Error("Não foi possível carregar os vencedores.");
      }

      const json = await resp.json();

      renderVencedores(json.vencedores);

    } catch (erro) {

      console.error("Erro ao carregar vencedores:", erro);

      renderVencedores([]);

    }
  }


  // --------------------- Busca ---------------------

  busca.addEventListener(
    "input",
    () => renderTabela(busca.value)
  );


  // --------------------- Excluir inscrição ---------------------

  tbody.addEventListener("click", async (e) => {

    const btn = e.target.closest(".link-excluir");

    if (!btn) {
      return;
    }

    if (!confirm("Remover este inscrito da lista?")) {
      return;
    }

    try {

      const resp = await fetch(
        `/api/inscricoes/${btn.dataset.id}`,
        {
          method: "DELETE"
        }
      );

      if (resp.status === 401) {
        window.location.href = "/admin/login";
        return;
      }

      if (resp.ok) {

        await carregarInscritos();

        mostrarToast(
          "Inscrito removido."
        );

      } else {

        mostrarToast(
          "Não foi possível remover o inscrito.",
          "erro"
        );
      }

    } catch (erro) {

      console.error(
        "Erro ao excluir inscrição:",
        erro
      );

      mostrarToast(
        "Erro ao remover o inscrito.",
        "erro"
      );
    }
  });


  // ============================================================
  // IMPORTAÇÃO CSV
  // ============================================================

  async function importarCsv(arquivo) {

    if (!arquivo) {
      return;
    }


    // Verifica extensão
    if (!arquivo.name.toLowerCase().endsWith(".csv")) {

      mostrarToast(
        "Selecione um arquivo CSV.",
        "erro"
      );

      inputCsv.value = "";

      return;
    }


    // Confirmação
    const confirmou = confirm(
      `Deseja importar o arquivo "${arquivo.name}"?`
    );

    if (!confirmou) {

      inputCsv.value = "";

      return;
    }


    // Cria FormData
    const formData = new FormData();

    formData.append(
      "arquivo",
      arquivo
    );


    // Mensagem de carregamento
    resultadoImportacao.innerHTML = `
      <div class="importacao-resultado">
        ⏳ Importando inscritos...
      </div>
    `;


    try {

      const resp = await fetch(
        "/api/inscricoes/importar",
        {
          method: "POST",
          body: formData,
        }
      );


      // Sessão expirada
      if (resp.status === 401) {

        window.location.href =
          "/admin/login";

        return;
      }


      const json = await resp.json();


      // Erro retornado pelo backend
      if (!resp.ok || !json.ok) {

        throw new Error(
          json.mensagem ||
          "Erro ao importar CSV."
        );
      }


      // ----------------------------------------------------------
      // Detalhes dos erros
      // ----------------------------------------------------------

      let detalhesErros = "";

      if (
        json.detalhes_erros &&
        json.detalhes_erros.length
      ) {

        detalhesErros = `
          <details>

            <summary>
              Ver erros da importação
            </summary>

            <ul>

              ${
                json.detalhes_erros
                  .map((item) => `
                    <li>

                      Linha ${item.linha}:
                      ${escapeHtml(item.erro)}

                      ${
                        item.email
                          ? ` — ${escapeHtml(item.email)}`
                          : ""
                      }

                    </li>
                  `)
                  .join("")
              }

            </ul>

          </details>
        `;
      }


      // ----------------------------------------------------------
      // Resultado
      // ----------------------------------------------------------

      resultadoImportacao.innerHTML = `
        <div class="importacao-resultado sucesso">

          <strong>
            ✅ Importação concluída!
          </strong>

          <div class="importacao-stats">

            <span>
              ✅ ${json.importados} importado(s)
            </span>

            <span>
              ⚠️ ${json.duplicados} duplicado(s)
            </span>

            <span>
              ❌ ${json.erros} erro(s)
            </span>

          </div>

          ${detalhesErros}

        </div>
      `;


      // Toast de sucesso
      mostrarToast(
        `${json.importados} inscrito(s) importado(s).`
      );


      // Limpa o input
      inputCsv.value = "";


      // Atualiza tabela e estatísticas
      await carregarInscritos();

      await carregarVencedores();


      // Remove mensagem depois de alguns segundos
      setTimeout(() => {

        if (resultadoImportacao) {
          resultadoImportacao.innerHTML = "";
        }

      }, 6000);


    } catch (erro) {

      console.error(
        "Erro ao importar CSV:",
        erro
      );


      resultadoImportacao.innerHTML = `
        <div class="importacao-resultado erro">

          ❌ ${escapeHtml(erro.message)}

        </div>
      `;


      mostrarToast(
        erro.message,
        "erro"
      );


      inputCsv.value = "";
    }
  }


  // --------------------- Eventos da importação ---------------------

  if (btnEscolherCsv && inputCsv) {

    btnEscolherCsv.addEventListener(
      "click",
      () => {
        inputCsv.click();
      }
    );


    inputCsv.addEventListener(
      "change",
      () => {

        const arquivo =
          inputCsv.files[0];

        if (arquivo) {
          importarCsv(arquivo);
        }

      }
    );

  }


  // ============================================================
  // TELA DE SORTEIO
  // ============================================================

  function abrirOverlay() {

    overlay.classList.add("ativo");

    sorteioCta.style.visibility =
      "hidden";

    sorteioGlow.classList.remove(
      "ativo"
    );

    sorteioNome.classList.remove(
      "revelado"
    );

    sorteioEyebrow.textContent =
      "Sorteando...";
  }


  function fecharOverlay() {

    overlay.classList.remove(
      "ativo"
    );

    if (cicloTimer) {
      clearTimeout(cicloTimer);
    }
  }


  function nomesParaCiclo() {

    const disponiveis =
      inscritos
        .filter((i) => !i.sorteado)
        .map((i) => i.nome);

    return disponiveis.length
      ? disponiveis
      : inscritos.map((i) => i.nome);
  }


  async function executarSorteio() {

    abrirOverlay();


    const nomes =
      nomesParaCiclo();


    if (!nomes.length) {

      sorteioNome.textContent =
        "Sem inscritos disponíveis";

      sorteioEyebrow.textContent =
        "";

      sorteioCta.style.visibility =
        "visible";

      return;
    }


    // ----------------------------------------------------------
    // Animação de suspense
    // ----------------------------------------------------------

    let intervalo = 60;

    const inicio = Date.now();

    const duracaoTotal = 2200;


    function ciclo() {

      sorteioNome.textContent =
        nomes[
          Math.floor(
            Math.random() *
            nomes.length
          )
        ];


      const decorrido =
        Date.now() - inicio;


      if (decorrido < duracaoTotal) {

        intervalo =
          60 +
          Math.pow(
            decorrido /
              duracaoTotal,
            3
          ) *
            260;


        cicloTimer =
          setTimeout(
            ciclo,
            intervalo
          );
      }
    }


    ciclo();


    // ----------------------------------------------------------
    // Sorteio real no servidor
    // ----------------------------------------------------------

    const [resp] =
      await Promise.all([

        fetch(
          "/api/sortear",
          {
            method: "POST"
          }
        ),

        new Promise((r) =>
          setTimeout(
            r,
            duracaoTotal
          )
        ),

      ]);


    if (cicloTimer) {
      clearTimeout(cicloTimer);
    }


    if (resp.status === 401) {

      window.location.href =
        "/admin/login";

      return;
    }


    const json =
      await resp.json();


    if (!resp.ok || !json.ok) {

      sorteioNome.textContent =
        "Sem inscritos disponíveis";

      sorteioEyebrow.textContent =
        "";

      sorteioCta.style.visibility =
        "visible";

      return;
    }


    // ----------------------------------------------------------
    // Revela vencedor
    // ----------------------------------------------------------

    sorteioNome.textContent =
      json.vencedor.nome;

    sorteioNome.classList.add(
      "revelado"
    );

    sorteioGlow.classList.add(
      "ativo"
    );

    sorteioEyebrow.textContent =
      "Vencedor do sorteio";

    sorteioCta.style.visibility =
      "visible";


    // Atualiza painel
    atualizarStats(
      json.stats
    );

    await carregarInscritos();

    await carregarVencedores();
  }


  // --------------------- Eventos do sorteio ---------------------

  btnAbrirSorteio.addEventListener(
    "click",
    executarSorteio
  );

  btnSortearOutro.addEventListener(
    "click",
    executarSorteio
  );

  btnFecharSorteio.addEventListener(
    "click",
    fecharOverlay
  );

  btnFecharSorteio2.addEventListener(
    "click",
    fecharOverlay
  );


  // --------------------- Resetar sorteio ---------------------

  btnResetar.addEventListener(
    "click",
    async () => {

      if (
        !confirm(
          "Isso vai reiniciar o sorteio e todos voltam a concorrer. Continuar?"
        )
      ) {
        return;
      }


      try {

        const resp =
          await fetch(
            "/api/sorteio/resetar",
            {
              method: "POST"
            }
          );


        if (resp.status === 401) {

          window.location.href =
            "/admin/login";

          return;
        }


        if (resp.ok) {

          await carregarInscritos();

          await carregarVencedores();

          mostrarToast(
            "Sorteio reiniciado."
          );

        } else {

          mostrarToast(
            "Não foi possível reiniciar o sorteio.",
            "erro"
          );
        }

      } catch (erro) {

        console.error(
          "Erro ao resetar sorteio:",
          erro
        );

        mostrarToast(
          "Erro ao reiniciar o sorteio.",
          "erro"
        );
      }
    }
  );


  // --------------------- Inicialização ---------------------

  carregarInscritos();

  carregarVencedores();

})();