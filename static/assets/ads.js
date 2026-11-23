/* Adsterra Social Bar / Popunder.
   Paste ONLY the script address (the src="..." part) between the quotes. Leave empty to turn it off. */
var SOCIAL_BAR_SRC = '';

(function () {
  if (!SOCIAL_BAR_SRC) return;
  var s = document.createElement('script');
  s.src = SOCIAL_BAR_SRC;
  s.async = true;
  document.body.appendChild(s);
})();
