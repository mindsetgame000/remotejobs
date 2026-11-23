/* Remote Jobs Hub: apply page and search page. */
(function () {
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  var params = new URLSearchParams(location.search);

  /* ---------- Apply page: /apply/?j=<job-slug> ---------- */
  var box = document.getElementById('applyBox');
  if (box) {
    var slug = params.get('j') || '';
    fetch('/data/apply.json').then(function (r) { return r.json(); }).then(function (map) {
      var job = map[slug];
      var go = document.getElementById('go');
      if (!job || !/^https?:\/\//i.test(job[2])) {
        document.getElementById('aTitle').textContent = 'This job is no longer available';
        go.textContent = 'See current jobs'; go.href = '/jobs/'; go.removeAttribute('target');
        return;
      }
      var host = '';
      try { host = new URL(job[2]).hostname; } catch (e) {}
      document.getElementById('aTitle').textContent = 'Apply for ' + job[0];
      document.getElementById('aCo').textContent = job[1];
      document.getElementById('aHost').innerHTML = 'You are leaving this site to apply on <strong>' + esc(host) + '</strong>.';
      document.getElementById('back').href = '/job/' + encodeURIComponent(slug) + '/';
      go.href = job[2];
      var n = parseInt(box.getAttribute('data-wait') || '0', 10);
      if (n > 0) {
        var label = go.innerHTML;
        go.classList.add('disabled');
        go.addEventListener('click', function (e) { if (n > 0) e.preventDefault(); });
        go.textContent = 'Continue in ' + n + 's';
        var t = setInterval(function () {
          n--;
          if (n <= 0) { clearInterval(t); go.classList.remove('disabled'); go.innerHTML = label; }
          else go.textContent = 'Continue in ' + n + 's';
        }, 1000);
      }
    });
  }

  /* ---------- Search page: /search/?q=... ---------- */
  var results = document.getElementById('sResults');
  if (results) {
    var q = (params.get('q') || '').trim();
    var input = document.getElementById('q');
    if (input) input.value = q;
    var count = document.getElementById('sCount');
    if (!q) { count.textContent = 'Type a job title, skill or company above.'; return; }
    fetch('/data/search.json').then(function (r) { return r.json(); }).then(function (all) {
      var words = q.toLowerCase().split(/\s+/).filter(Boolean);
      var hits = all.filter(function (j) {
        var hay = (j.t + ' ' + j.c + ' ' + j.l).toLowerCase();
        return words.every(function (w) { return hay.indexOf(w) !== -1; });
      });
      count.textContent = hits.length + ' jobs for "' + q + '"';
      var shown = 0;
      function more() {
        results.insertAdjacentHTML('beforeend', hits.slice(shown, shown + 30).map(function (j) {
          return '<a class="job" href="' + esc(j.u) + '"><span class="ph">' + esc((j.c || '?').charAt(0).toUpperCase()) + '</span>' +
            '<div class="job-main"><div class="job-title">' + esc(j.t) + '</div><div class="job-co">' + esc(j.c) + '</div>' +
            '<div class="tags"><span class="tag green">' + esc(j.l) + '</span>' + (j.ty ? '<span class="tag">' + esc(j.ty) + '</span>' : '') +
            '</div></div><div class="job-side">' + esc(j.d) + '<br><span class="apply">View job &rarr;</span></div></a>';
        }).join(''));
        shown += 30;
        btn.hidden = shown >= hits.length;
      }
      var btn = document.createElement('button');
      btn.className = 'btn'; btn.textContent = 'Load more';
      btn.addEventListener('click', more);
      results.insertAdjacentElement('afterend', btn);
      more();
    });
  }
})();
