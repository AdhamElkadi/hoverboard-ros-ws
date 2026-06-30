/**
 * Love expression — heart eyes pulse + sparkles (works in scenes / manual hold).
 */
(function () {
  'use strict';

  const faceEl = document.getElementById('robotFace');
  if (!faceEl) return;

  function isLove() {
    return faceEl.getAttribute('data-emotion') === 'love';
  }

  function sync() {
    faceEl.classList.toggle('love-fx-on', isLove());
  }

  function onEmotionChange(emotion) {
    sync();
  }

  const observer = new MutationObserver(sync);
  observer.observe(faceEl, { attributes: true, attributeFilter: ['data-emotion'] });

  sync();

  window.EilikLove = Object.freeze({ onEmotionChange, sync });
})();
