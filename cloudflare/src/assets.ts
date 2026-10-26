// Arquivos estáticos servidos pelo próprio Worker (CSP: tudo 'self', sem script inline).
export const ESTILO = `
:root{--fundo:#f5f7fb;--cartao:#fff;--texto:#1f2937;--suave:#5b6676;--borda:#e2e7ef;--acento:#3f6fb0;--ok:#2f8a5b;--aviso:#a4701a;--erro:#b3382c}
@media (prefers-color-scheme:dark){:root{--fundo:#12161d;--cartao:#1a2029;--texto:#e6eaf0;--suave:#9aa6b6;--borda:#2a3340;--acento:#7ba4e0;--ok:#5fc08f;--aviso:#e0b15b;--erro:#e5857b}}
*{box-sizing:border-box}body{margin:0;background:var(--fundo);color:var(--texto);font:16px/1.6 "Segoe UI",system-ui,sans-serif}
a{color:var(--acento)}h1{font-size:1.9rem;line-height:1.2}h2{font-size:1.25rem;margin-top:1.6em}
.topo{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:12px max(16px,calc((100vw - 900px)/2));border-bottom:1px solid var(--borda)}
.marca{display:flex;align-items:center;gap:8px;font-weight:700;color:var(--texto);text-decoration:none}.ponto{width:12px;height:12px;border-radius:50%;background:var(--ok)}
nav{display:flex;gap:16px;align-items:center;flex-wrap:wrap}nav a{text-decoration:none;color:var(--suave)}
.link{background:none;border:0;color:var(--suave);cursor:pointer;font:inherit;padding:0}
main,footer{max-width:900px;margin:0 auto;padding:16px}footer{color:var(--suave);font-size:.9rem;border-top:1px solid var(--borda);margin-top:32px}
.lead{font-size:1.1rem;color:var(--suave)}.nota{color:var(--suave);font-size:.92rem}
.grade{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}
.cartao{background:var(--cartao);border:1px solid var(--borda);border-radius:14px;padding:18px}.cartao h2{margin-top:0}
.botao{display:inline-block;padding:10px 20px;border-radius:12px;background:var(--acento);color:#fff;text-decoration:none;font-weight:600;border:0;cursor:pointer;font:inherit;font-weight:600}
.botao.claro{background:var(--cartao);color:var(--texto);border:1px solid var(--borda)}.botao.perigo{background:var(--erro)}
.form{display:grid;gap:14px;max-width:520px}.form label{display:grid;gap:4px}.form input:not([type=checkbox]):not([type=radio]){padding:10px;border-radius:8px;border:1px solid var(--borda);background:var(--cartao);color:var(--texto);font:inherit}
.check{display:flex!important;gap:8px;align-items:flex-start}.msg{min-height:1.4em;color:var(--suave)}.msg.erro{color:var(--erro)}.msg.ok,.ok{color:var(--ok)}
.aviso{background:color-mix(in srgb,var(--aviso) 14%,transparent);border-left:4px solid var(--aviso);padding:8px 14px;border-radius:6px}
.questao{background:var(--cartao);border:1px solid var(--borda);border-radius:12px;margin:0 0 14px;padding:14px 16px}.questao legend{font-weight:600;padding:0 6px}.num{color:var(--acento)}
.opcao{display:flex;gap:10px;align-items:flex-start;padding:6px 4px;cursor:pointer}.opcao input{margin-top:6px}
.termo{text-decoration:underline dotted;cursor:help}.barra{display:flex;justify-content:space-between;align-items:center;position:sticky;bottom:0;background:var(--fundo);padding:10px 0;border-top:1px solid var(--borda)}
.nota-grande{font-size:3rem;font-weight:700;margin:.2em 0}.nota-grande small{font-size:1rem;color:var(--suave)}
.temas{list-style:none;padding:0;display:grid;gap:8px}.tema{display:grid;grid-template-columns:1.4fr 1fr 1.2fr;gap:10px;align-items:center}
.barra-tema{height:8px;background:var(--borda);border-radius:99px;overflow:hidden}.barra-tema i{display:block;height:100%;background:var(--ok)}.tema.revisar i{background:var(--aviso)}.tema.refazer i{background:var(--erro)}
.erradas li{margin-bottom:16px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--borda)}
dl{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px}dt{color:var(--suave)}dd{margin:0}
.folha{background:#fff;color:#1f2937;border:2px solid #3f6fb0;border-radius:6px;padding:40px 48px;text-align:center;max-width:900px;margin:12px auto}
.folha .nome{font-size:2.2rem;font-weight:700;margin:.2em 0;border-bottom:1px solid #ccd5e3;display:inline-block;padding:0 24px}.folha .sup,.folha .sub,.folha .meta,.folha .codigo{color:#5b6676}.folha .aviso-fixo{font-size:.8rem;color:#5b6676;margin-top:24px}
.folha .temas-cert{list-style:none;padding:0;color:#374151;font-size:.95rem}.acoes{max-width:900px;margin:16px auto}
@media print{.topo,footer,.nao-imprimir{display:none!important}body{background:#fff}.folha{border:2px solid #3f6fb0;margin:0;max-width:none}@page{size:A4 landscape;margin:12mm}}
@media (max-width:600px){.tema{grid-template-columns:1fr}.folha{padding:24px 16px}}
`;

export const FORMULARIO_JS = `
(function () {
  function falar(el, texto, erro) { if (!el) return; el.textContent = texto; el.className = "msg " + (erro ? "erro" : "ok"); }
  document.querySelectorAll("form[data-api]").forEach(function (f) {
    f.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var msg = f.querySelector(".msg");
      var dados = {};
      new FormData(f).forEach(function (v, k) { dados[k] = v; });
      f.querySelectorAll("input[type=checkbox]").forEach(function (c) { dados[c.name] = c.checked; });
      var botao = f.querySelector("button[type=submit]");
      if (botao) botao.disabled = true;
      falar(msg, "Enviando…", false);
      fetch(f.getAttribute("data-api"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(dados), credentials: "same-origin" })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (x) {
          if (x.ok && x.j.redirect) { location.href = x.j.redirect; return; }
          falar(msg, x.j.mensagem || x.j.erro || (x.ok ? "Pronto." : "Algo deu errado."), !x.ok);
          if (botao) botao.disabled = !x.ok ? false : botao.disabled;
        })
        .catch(function () { falar(msg, "Sem conexão. Tente de novo.", true); if (botao) botao.disabled = false; });
    });
  });
  var sair = document.querySelector("[data-sair]");
  if (sair) sair.addEventListener("click", function () {
    fetch("/api/sair", { method: "POST", credentials: "same-origin" }).then(function () { location.href = "/"; });
  });
})();
`;

export const PROVA_JS = `
(function () {
  var f = document.getElementById("prova");
  if (!f) return;
  var total = Number(f.getAttribute("data-total"));
  var contagem = document.getElementById("contagem");
  var msg = f.querySelector(".msg");
  function respondidas() { return f.querySelectorAll("input[type=radio]:checked").length; }
  f.addEventListener("change", function () { contagem.textContent = respondidas() + " de " + total + " respondidas"; });
  f.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var faltam = total - respondidas();
    if (faltam > 0 && !confirm("Faltam " + faltam + " questões. Questões em branco contam como erradas. Entregar mesmo assim?")) return;
    var respostas = {};
    f.querySelectorAll("fieldset.questao").forEach(function (q) {
      var marcada = q.querySelector("input[type=radio]:checked");
      respostas[q.getAttribute("data-id")] = marcada ? Number(marcada.value) : null;
    });
    var botao = f.querySelector("button[type=submit]");
    botao.disabled = true;
    msg.textContent = "Corrigindo…";
    fetch("/api/prova/" + f.getAttribute("data-id") + "/entregar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ respostas: respostas }), credentials: "same-origin" })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (x) {
        if (x.ok && x.j.redirect) { location.href = x.j.redirect; return; }
        msg.textContent = x.j.erro || "Não foi possível entregar.";
        msg.className = "msg erro";
        botao.disabled = false;
      })
      .catch(function () { msg.textContent = "Sem conexão. Suas respostas continuam na tela; tente de novo."; msg.className = "msg erro"; botao.disabled = false; });
  });
})();
`;
