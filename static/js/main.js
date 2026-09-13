(function () {
  "use strict";

  const form = document.getElementById("form-inscricao");
  const btnEnviar = document.getElementById("btn-enviar");
  const etapaForm = document.getElementById("etapa-formulario");
  const etapaConfirmacao = document.getElementById("etapa-confirmacao");
  const toast = document.getElementById("toast");

  function mostrarToast(msg, tipo) {
    toast.textContent = msg;
    toast.className = "toast mostrar" + (tipo === "erro" ? " erro" : "");
    setTimeout(() => { toast.className = "toast"; }, 3200);
  }

  function maskTelefone(v) {
    v = v.replace(/\D/g, "").slice(0, 11);
    if (v.length > 6) return v.replace(/(\d{2})(\d{5})(\d{0,4})/, "($1) $2-$3").replace(/-$/, "");
    if (v.length > 2) return v.replace(/(\d{2})(\d{0,5})/, "($1) $2");
    return v;
  }

  function maskCpf(v) {
    v = v.replace(/\D/g, "").slice(0, 11);
    return v
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  }

  const campoTelefone = document.getElementById("telefone");
  if (campoTelefone) {
    campoTelefone.addEventListener("input", (e) => {
      e.target.value = maskTelefone(e.target.value);
    });
  }

  const campoCpf = document.getElementById("cpf");
  if (campoCpf) {
    campoCpf.addEventListener("input", (e) => {
      e.target.value = maskCpf(e.target.value);
    });
  }

  // --------------------- Campo dinâmico de perfil ---------------------
  const perfilSelect = document.getElementById("perfil");
  const grupoCampoPerfil = document.getElementById("grupo-campo-perfil");
  const labelCampoPerfil = document.getElementById("label-campo-perfil");
  const inputCampoPerfil = document.getElementById("campo-perfil-input");
  const erroCampoPerfil = grupoCampoPerfil ? grupoCampoPerfil.querySelector(".erro-msg") : null;
  const perfilCamposDataEl = document.getElementById("perfil-campos-data");

  if (perfilSelect && grupoCampoPerfil && inputCampoPerfil) {
    let perfilCampos = {};
    try {
      perfilCampos = JSON.parse((perfilCamposDataEl && perfilCamposDataEl.textContent) || "{}");
    } catch (err) {
      perfilCampos = {};
    }

    function atualizarCampoPerfil() {
      const campo = perfilCampos[perfilSelect.value];
      inputCampoPerfil.value = "";
      if (erroCampoPerfil) erroCampoPerfil.textContent = "";
      inputCampoPerfil.classList.remove("invalido");

      if (!campo) {
        grupoCampoPerfil.hidden = true;
        inputCampoPerfil.required = false;
        inputCampoPerfil.name = "";
        return;
      }

      labelCampoPerfil.textContent = campo.label;
      inputCampoPerfil.placeholder = campo.label;
      inputCampoPerfil.name = campo.id;
      inputCampoPerfil.required = true;
      if (erroCampoPerfil) erroCampoPerfil.dataset.erroDe = campo.id;
      grupoCampoPerfil.hidden = false;
    }

    perfilSelect.addEventListener("change", atualizarCampoPerfil);
    atualizarCampoPerfil();
  }

  function limparErros() {
    form.querySelectorAll(".erro-msg").forEach((el) => (el.textContent = ""));
    form.querySelectorAll("input.invalido").forEach((el) => el.classList.remove("invalido"));
  }

  function mostrarErros(erros) {
    Object.entries(erros).forEach(([campo, msg]) => {
      const el = form.querySelector(`[data-erro-de="${campo}"]`);
      const input = form.querySelector(`[name="${campo}"]`);
      if (el) el.textContent = msg;
      if (input) input.classList.add("invalido");
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    limparErros();
    btnEnviar.disabled = true;
    btnEnviar.textContent = "Enviando...";

    try {
      const dados = new FormData(form);
      const resp = await fetch("/api/inscricao", { method: "POST", body: dados });
      const json = await resp.json();

      if (resp.ok && json.ok) {
        etapaForm.style.display = "none";
        etapaConfirmacao.style.display = "block";
      } else if (json.erros) {
        mostrarErros(json.erros);
        mostrarToast("Confira os campos destacados.", "erro");
      } else {
        mostrarToast("Não foi possível concluir a inscrição.", "erro");
      }
    } catch (err) {
      mostrarToast("Erro de conexão. Tente novamente.", "erro");
    } finally {
      btnEnviar.disabled = false;
      btnEnviar.textContent = "Confirmar inscrição";
    }
  });
})();
