/**
 * Kiss expression: heart launches from mouth (no one-eye wink).
 */
(function () {
  'use strict';

  const faceEl = document.getElementById('robotFace');
  const flyHeart = document.getElementById('kissHeartFly');
  if (!faceEl || !flyHeart) return;

  const CYCLE_MS = 2200;

  let loopId = null;

  function isKiss() {
    return faceEl.getAttribute('data-emotion') === 'kiss';
  }

  function launchHeart() {
    if (!isKiss()) return;
    flyHeart.classList.remove('kiss-heart--anim');
    void flyHeart.offsetWidth;
    flyHeart.classList.add('kiss-heart--anim');
  }

  function startLoop() {
    stopLoop();
    launchHeart();
    loopId = window.setInterval(launchHeart, CYCLE_MS);
  }

  function stopLoop() {
    if (loopId) {
      window.clearInterval(loopId);
      loopId = null;
    }
    flyHeart.classList.remove('kiss-heart--anim');
  }

  function onEmotionChange(emotion) {
    if (emotion === 'kiss') startLoop();
    else stopLoop();
  }

  const observer = new MutationObserver(() => {
    const emo = faceEl.getAttribute('data-emotion');
    if (emo === 'kiss' && !loopId) startLoop();
    else if (emo !== 'kiss' && loopId) stopLoop();
  });
  observer.observe(faceEl, { attributes: true, attributeFilter: ['data-emotion'] });

  if (isKiss()) startLoop();

  window.EilikKiss = Object.freeze({
    onEmotionChange,
    launchHeart,
    startLoop,
    stopLoop,
  });
})();
