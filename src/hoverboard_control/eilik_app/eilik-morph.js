/**
 * True SVG path morph between expressions (flubber)
 */
(function () {
  'use strict';

  const faceEl = document.getElementById('robotFace');
  const eyeL = document.getElementById('eyeLMorph');
  const eyeR = document.getElementById('eyeRMorph');
  const mouthEl = document.getElementById('mouthMorph');

  if (!faceEl || !eyeL || !eyeR || !mouthEl) return;

  const MORPH_MS = 520;
  const EASE = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

  function oval(cx, cy, rx, ry) {
    return `M ${cx - rx} ${cy} A ${rx} ${ry} 0 1 1 ${cx + rx} ${cy} A ${rx} ${ry} 0 1 1 ${cx - rx} ${cy} Z`;
  }

  const DOT = 'M 100 118 L 100.01 118 Z';

  /** Primary eye + mouth paths per emotion */
  const PATHS = {
    neutral: {
      l: oval(56, 72, 24, 28),
      r: oval(144, 72, 24, 28),
      m: DOT,
      mouthStroke: false,
    },
    smile: {
      l: 'M 28 82 L 84 82 C 84 82 84 48 56 46 C 28 48 28 82 28 82 Z',
      r: 'M 116 82 L 172 82 C 172 82 172 48 144 46 C 116 48 116 82 116 82 Z',
      m: 'M 58 106 Q 100 126 142 106',
      mouthStroke: true,
    },
    happy: {
      l: 'M 34 84 Q 68 52 102 84 L 98 76 Q 68 58 38 76 Z',
      r: 'M 98 84 Q 132 52 166 84 L 162 76 Q 132 58 102 76 Z',
      m: 'M 72 122 Q 100 138 128 122',
      mouthStroke: true,
    },
    laugh: {
      l: 'M 32 62 Q 68 80 104 62 L 100 68 Q 68 54 36 68 Z',
      r: 'M 96 62 Q 132 80 168 62 L 164 68 Q 132 54 100 68 Z',
      m: 'M 36 108 Q 100 98 164 108 Q 168 122 100 158 Q 32 122 36 108 Z',
      mouthStroke: false,
    },
    wink: {
      l: 'M 26 72 C 26 58 42 52 56 54 C 70 52 86 58 86 72 C 86 75 70 78 56 77 C 42 78 26 75 26 72 Z',
      r: 'M 108 66 L 132 76 L 108 86 Z',
      m: 'M 72 128 Q 86 122 100 128 Q 114 134 128 128',
      mouthStroke: true,
    },
    sad: {
      l: 'M 34 84 H 86 A 8 8 0 0 0 90 76 V 50 L 30 66 V 76 A 8 8 0 0 0 34 84 Z',
      r: 'M 166 84 H 114 A 8 8 0 0 1 110 76 V 50 L 170 66 V 76 A 8 8 0 0 1 166 84 Z',
      m: DOT,
      mouthStroke: false,
    },
    danger: {
      l: 'M 28 52 L 82 66 C 94 90 62 96 30 86 C 14 70 28 52 28 52 Z',
      r: 'M 172 52 L 118 66 C 106 90 138 96 170 86 C 186 70 172 52 172 52 Z',
      m: DOT,
      mouthStroke: false,
    },
    angry: {
      l: 'M 28 52 L 82 66 C 94 90 62 96 30 86 C 14 70 28 52 28 52 Z',
      r: 'M 172 52 L 118 66 C 106 90 138 96 170 86 C 186 70 172 52 172 52 Z',
      m: DOT,
      mouthStroke: false,
    },
    surprised: {
      l: oval(56, 72, 26, 30),
      r: oval(144, 72, 26, 30),
      m: oval(100, 126, 12, 10),
      mouthStroke: false,
    },
    kiss: {
      l: 'M 28 82 L 84 82 C 84 82 90 48 62 46 C 34 48 28 82 28 82 Z',
      r: 'M 116 82 L 172 82 C 172 82 166 48 138 46 C 110 48 116 82 116 82 Z',
      m: 'M 92 122 C 88 114 96 110 104 118 C 108 124 104 130 96 128 C 88 126 88 120 92 122 Z',
      mouthStroke: false,
    },
    love: {
      l: 'M 68 82 C 68 68 52 62 52 74 C 52 62 36 68 36 82 C 36 96 68 108 68 108 C 68 108 100 96 100 82 C 100 68 84 62 84 74 C 84 62 68 68 68 82 Z',
      r: 'M 132 82 C 132 68 116 62 116 74 C 116 62 100 68 100 82 C 100 96 132 108 132 108 C 132 108 164 96 164 82 C 164 68 148 62 148 74 C 148 62 132 68 132 82 Z',
      m: 'M 100 132 C 88 118 72 124 100 142 C 128 124 112 118 100 132 Z',
      mouthStroke: false,
    },
    confused: {
      l: 'M 48 68 A 22 22 0 1 1 92 68 A 22 22 0 1 1 48 68 Z',
      r: 'M 108 66 L 132 76 L 108 86 Z',
      m: 'M 72 128 Q 86 122 100 128 Q 114 134 128 128',
      mouthStroke: true,
    },
    sleepy: {
      l: 'M 28 82 L 84 82 C 84 82 84 48 56 46 C 28 48 28 82 28 82 Z',
      r: 'M 116 82 L 172 82 C 172 82 172 48 144 46 C 116 48 116 82 116 82 Z',
      m: 'M 78 128 L 122 128',
      mouthStroke: true,
    },
    talking: {
      l: oval(56, 72, 24, 28),
      r: oval(144, 72, 24, 28),
      m: oval(100, 126, 14, 11),
      mouthStroke: false,
    },
    excited: {
      l: 'M 34 84 Q 68 52 102 84 L 98 76 Q 68 58 38 76 Z',
      r: 'M 98 84 Q 132 52 166 84 L 162 76 Q 132 58 102 76 Z',
      m: 'M 58 116 H 142 V 134 H 58 Z',
      mouthStroke: false,
    },
  };

  let currentEmotion = 'neutral';
  let animId = 0;
  let morphGen = 0;

  function applyMouthStyle(target) {
    if (target.mouthStroke) {
      mouthEl.setAttribute('fill', 'none');
      mouthEl.setAttribute('stroke', 'currentColor');
      mouthEl.setAttribute('stroke-width', '11');
      mouthEl.setAttribute('stroke-linecap', 'round');
      mouthEl.setAttribute('stroke-linejoin', 'round');
    } else {
      mouthEl.setAttribute('fill', 'currentColor');
      mouthEl.removeAttribute('stroke');
      mouthEl.removeAttribute('stroke-width');
    }
  }

  function interpolatePath(from, to) {
    if (typeof flubber !== 'undefined' && flubber.interpolate) {
      try {
        return flubber.interpolate(from, to, { maxSegmentLength: 2 });
      } catch (e) {
        console.warn('[EilikMorph]', e);
      }
    }
    return (t) => (t < 0.5 ? from : to);
  }

  function runMorph(from, to, ms, onDone) {
    const gen = ++morphGen;
    cancelAnimationFrame(animId);

    const iL = interpolatePath(from.l, to.l);
    const iR = interpolatePath(from.r, to.r);
    const iM = interpolatePath(from.m, to.m);
    const t0 = performance.now();

    applyMouthStyle(to);

    function frame(now) {
      if (gen !== morphGen) return;
      const t = Math.min(1, (now - t0) / ms);
      const e = EASE(t);
      eyeL.setAttribute('d', iL(e));
      eyeR.setAttribute('d', iR(e));
      mouthEl.setAttribute('d', iM(e));
      if (t < 1) {
        animId = requestAnimationFrame(frame);
      } else if (onDone) {
        onDone();
      }
    }
    animId = requestAnimationFrame(frame);
  }

  function getPaths(emo) {
    return PATHS[emo] || PATHS.neutral;
  }

  function morphTo(emotion, prevEmotion) {
    const next = PATHS[emotion] ? emotion : 'neutral';
    const from = getPaths(prevEmotion || currentEmotion);
    const to = getPaths(next);

    faceEl.classList.add('eilik-morphing', 'eilik-morph-on');
    runMorph(from, to, MORPH_MS, () => {
      faceEl.classList.remove('eilik-morphing');
      currentEmotion = next;
    });
    return true;
  }

  function init() {
    const n = PATHS.neutral;
    eyeL.setAttribute('d', n.l);
    eyeR.setAttribute('d', n.r);
    mouthEl.setAttribute('d', n.m);
    applyMouthStyle(n);
    faceEl.classList.add('eilik-morph-on');
    currentEmotion = 'neutral';
  }

  function startMorph(fromEmo, toEmo) {
    if (!toEmo || toEmo === fromEmo) return;
    morphTo(toEmo, fromEmo);
  }

  init();

  window.EilikMorph = Object.freeze({
    morphTo,
    startMorph,
    getPaths,
    MORPH_MS,
  });
})();
