/**
 * Eilik-style reactions: pop on emotion change, laugh jiggle, wink pulse
 */
(function () {
  'use strict';

  const faceEl = document.getElementById('robotFace');
  if (!faceEl) return;

  let laughTimer = 0;
  let winkTimer = 0;

  function clearReact(cls) {
    faceEl.classList.remove(cls);
  }

  function pulse(cls, ms) {
    clearReact(cls);
    void faceEl.offsetWidth;
    faceEl.classList.add(cls);
    window.setTimeout(() => clearReact(cls), ms);
  }

  function onEmotionChange(emotion, prev) {
    if (emotion === prev) return;

    if (emotion === 'kiss') {
      reactKiss();
      if (window.EilikKiss) window.EilikKiss.onEmotionChange('kiss');
    } else if (window.EilikKiss) {
      window.EilikKiss.onEmotionChange(emotion);
    }

    if (emotion === 'love' && window.EilikLove) {
      window.EilikLove.onEmotionChange('love');
    } else if (window.EilikLove) {
      window.EilikLove.onEmotionChange(emotion);
    }

    if (
      (emotion === 'laugh' || emotion === 'excited') &&
      !faceEl.classList.contains('face--hold')
    ) {
      faceEl.classList.add('eilik-laugh-bounce');
      window.clearTimeout(laughTimer);
      laughTimer = window.setTimeout(() => {
        faceEl.classList.remove('eilik-laugh-bounce');
      }, 2400);
    } else {
      faceEl.classList.remove('eilik-laugh-bounce');
    }
  }

  function reactLaugh() {
    pulse('eilik-jiggle', 520);
    faceEl.classList.add('eilik-laugh-bounce');
    window.clearTimeout(laughTimer);
    laughTimer = window.setTimeout(() => {
      faceEl.classList.remove('eilik-laugh-bounce');
    }, 2000);
  }

  function reactConfused() {
    pulse('eilik-jiggle', 480);
  }

  function reactWink() {
    pulse('eilik-pop', 300);
  }

  function reactKiss() {
    pulse('eilik-pop', 360);
    if (window.EilikKiss) window.EilikKiss.launchHeart();
  }

  window.EilikFace = Object.freeze({
    onEmotionChange,
    reactLaugh,
    reactConfused,
    reactWink,
    reactKiss,
  });
})();
