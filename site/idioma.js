// Alterna português/inglês. A escolha fica só neste navegador (localStorage), sem rastreio.
(function () {
  var html = document.documentElement;
  function aplicar(lang) {
    html.lang = lang;
    document.title = lang === "en" ? "TempCPU — CPU temperature" : "TempCPU — temperatura do processador";
    try { localStorage.setItem("idioma", lang); } catch (e) {}
  }
  var salvo = null;
  try { salvo = localStorage.getItem("idioma"); } catch (e) {}
  var inicial = salvo || ((navigator.language || "pt").toLowerCase().indexOf("pt") === 0 ? "pt-BR" : "en");
  aplicar(inicial);
  document.getElementById("idioma").addEventListener("click", function () {
    aplicar(html.lang === "en" ? "pt-BR" : "en");
  });
})();
