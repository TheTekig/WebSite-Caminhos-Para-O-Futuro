(function () {
  "use strict";

  // --------------------- Menu mobile ---------------------
  const navToggle = document.getElementById("nav-toggle");
  const navLinks = document.getElementById("nav-links");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      const aberto = navLinks.classList.toggle("aberto");
      navToggle.setAttribute("aria-expanded", aberto ? "true" : "false");
    });
    navLinks.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", () => {
        navLinks.classList.remove("aberto");
        navToggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // --------------------- Contador regressivo ---------------------
  const countdown = document.getElementById("countdown");
  if (countdown) {
    const alvo = new Date(countdown.dataset.alvo).getTime();
    const elDias = countdown.querySelector('[data-cd="dias"]');
    const elHoras = countdown.querySelector('[data-cd="horas"]');
    const elMin = countdown.querySelector('[data-cd="min"]');
    const elSeg = countdown.querySelector('[data-cd="seg"]');
    const eyebrow = countdown.querySelector(".countdown-eyebrow");

    function pad(n) { return String(n).padStart(2, "0"); }

    function atualizar() {
      const agora = Date.now();
      const diff = alvo - agora;
      if (isNaN(alvo) || diff <= 0) {
        elDias.textContent = "00"; elHoras.textContent = "00";
        elMin.textContent = "00"; elSeg.textContent = "00";
        if (eyebrow) eyebrow.textContent = "O EVENTO JÁ COMEÇOU";
        return;
      }
      const dias = Math.floor(diff / 86400000);
      const horas = Math.floor((diff % 86400000) / 3600000);
      const min = Math.floor((diff % 3600000) / 60000);
      const seg = Math.floor((diff % 60000) / 1000);
      elDias.textContent = pad(dias);
      elHoras.textContent = pad(horas);
      elMin.textContent = pad(min);
      elSeg.textContent = pad(seg);
    }

    atualizar();
    setInterval(atualizar, 1000);
  }

  // --------------------- Animações de entrada (fade-in ao rolar) ---------------------
  const elementosReveal = document.querySelectorAll(".reveal");
  if (elementosReveal.length && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entradas) => {
        entradas.forEach((entrada) => {
          if (entrada.isIntersecting) {
            entrada.target.classList.add("visivel");
            observer.unobserve(entrada.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );
    elementosReveal.forEach((el) => observer.observe(el));
  } else {
    elementosReveal.forEach((el) => el.classList.add("visivel"));
  }

  // --------------------- Carrossel de palestrantes ---------------------
  const trilho = document.getElementById("carrossel-palestrantes");
  const btnPrev = document.getElementById("carrossel-prev");
  const btnNext = document.getElementById("carrossel-next");
  if (trilho && btnPrev && btnNext) {
    function passo() {
      const card = trilho.querySelector(".palestrante-card");
      if (!card) return 300;
      const estilo = getComputedStyle(trilho);
      const gap = parseFloat(estilo.gap || "24");
      return card.offsetWidth + gap;
    }
    btnPrev.addEventListener("click", () => trilho.scrollBy({ left: -passo(), behavior: "smooth" }));
    btnNext.addEventListener("click", () => trilho.scrollBy({ left: passo(), behavior: "smooth" }));
  }
})();
