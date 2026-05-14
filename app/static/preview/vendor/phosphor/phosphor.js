// 로컬 자가호스팅 버전 — 외부 unpkg 대신 vendor/ 에서 직접 로드.
// 시흥가개 preview에서 실제 사용하는 weight 3종(regular/bold/fill)만 포함.
(function () {
  var head = document.getElementsByTagName("head")[0];
  ["regular", "bold", "fill"].forEach(function (weight) {
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.type = "text/css";
    link.href = "/preview/vendor/phosphor/" + weight + "/style.css";
    head.appendChild(link);
  });
})();
