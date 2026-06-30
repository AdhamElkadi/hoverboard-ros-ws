/**
 * Merged AI Robot Face — neon UI + RoboEyes movement + natural idle default
 */

(function () {
  'use strict';

  const EMOTIONS = Object.freeze([
    'angry',
    'confused',
    'danger',
    'excited',
    'happy',
    'kiss',
    'love',
    'laugh',
    'neutral',
    'sad',
    'sleepy',
    'smile',
    'surprised',
    'talking',
    'wink',
  ]);

  const MOOD_TO_EMOTION = Object.freeze({
    [ROBO_DEFAULT]: 'neutral',
    [ROBO_TIRED]: 'sad',
    [ROBO_ANGRY]: 'danger',
    [ROBO_HAPPY]: 'smile', /* mood+ uses smile with mouth */
  });

  const DEFAULT_EMOTION = 'neutral'; /* bean eyes — reference look */

  /** Default look-around: center, sides, corners, moods */
  const WANDER_SEQUENCE = Object.freeze([
    { gaze: [0, 0], emotion: 'neutral', pos: ROBO_DEFAULT, mood: ROBO_DEFAULT },
    { gaze: [-1, 0], emotion: 'wink', pos: ROBO_W },
    { gaze: [1, 0], emotion: 'surprised', pos: ROBO_E },
    { gaze: [0, -0.92], emotion: 'laugh', pos: ROBO_N },
    { gaze: [0, 0.92], emotion: 'sleepy', pos: ROBO_S, mood: ROBO_TIRED },
    { gaze: [-0.88, -0.88], emotion: 'confused', pos: ROBO_NW },
    { gaze: [0.88, -0.88], emotion: 'excited', pos: ROBO_NE },
    { gaze: [-0.88, 0.88], emotion: 'sad', pos: ROBO_SW },
    { gaze: [0.88, 0.88], emotion: 'kiss', pos: ROBO_SE },
    { gaze: [-0.55, 0], emotion: 'neutral', pos: ROBO_W },
    { gaze: [0.55, 0], emotion: 'talking', pos: ROBO_E },
    { gaze: [0, 0], emotion: 'neutral', pos: ROBO_DEFAULT, mood: ROBO_DEFAULT },
  ]);

  /** Expression keys A→Z order: 1–0 then Q U T Z */
  const KEY_MAP = Object.freeze({
    '1': 'angry',
    '2': 'confused',
    '3': 'danger',
    '4': 'excited',
    '5': 'happy',
    '6': 'kiss',
    l: 'love',
    L: 'love',
    '7': 'laugh',
    '8': 'neutral',
    '9': 'sad',
    '0': 'sleepy',
    q: 'smile',
    Q: 'smile',
    u: 'surprised',
    U: 'surprised',
    t: 'talking',
    T: 'talking',
    z: 'wink',
    Z: 'wink',
  });

  const faceEl = document.getElementById('robotFace');
  if (!faceEl) {
    console.error('[RobotFace] #robotFace not found.');
    return;
  }

  const robo = new RoboEyesDom(faceEl);
  let currentEmotion = DEFAULT_EMOTION;
  let mouseFollow = false;
  let autoPlayActive = false;
  let wanderActive = false;
  let wanderIndex = 0;
  let wanderStepAt = 0;
  let faceTrackActive = false;
  let autoDriveActive = false;
  let lastLookDir = 'center';
  let reactionRestoreTimer = null;
  const DEFAULT_IDLE_EMOTION = 'neutral';
  const REACTION_RESTORE_MS = 3200;

  const camVideo = document.getElementById('camFeed');
  const camStatus = document.getElementById('camStatus');
  const camPreview = document.getElementById('camPreview');
  const driveStatus = document.getElementById('driveStatus');

  const faceTracker =
    typeof FaceTracker !== 'undefined'
      ? new FaceTracker({
          video: camVideo,
          onGaze(nx, ny, found) {
            if (!faceTrackActive) return;
            if (found) applyGaze(nx, ny);
            else lookAtViewer();
          },
          onStatus(msg) {
            if (camStatus) camStatus.textContent = msg;
          },
          onActiveChange(on) {
            if (camPreview) camPreview.classList.toggle('cam-preview--live', on);
          },
        })
      : null;

  const obstacleDriver =
    typeof ObstacleDriver !== 'undefined'
      ? new ObstacleDriver({
          video: camVideo,
          onDrive(cmd) {
            if (!autoDriveActive) return;
            if (window.RobotSocket?.sendRobotDrive) {
              window.RobotSocket.sendRobotDrive(cmd);
            }
          },
          onStatus(msg) {
            if (driveStatus) driveStatus.textContent = msg;
          },
          onActiveChange(on) {
            if (camPreview) {
              camPreview.classList.toggle('cam-preview--drive', on);
              if (!on && !faceTrackActive) camPreview.classList.remove('cam-preview--live');
            }
          },
        })
      : null;

  function forceEyesOpen() {
    robo.setBlinkPaused(true);
    robo.setAutoblinker(false);
    faceEl.style.setProperty('--eye-open-l', '1');
    faceEl.style.setProperty('--eye-open-r', '1');
  }

  function syncEyeBlink() {
    faceEl.classList.toggle('auto-play-on', autoPlayActive);
    const robotDisplay =
      document.body.classList.contains('robot-screen') &&
      !document.body.classList.contains('has-panel');
    if (!autoPlayActive || robotDisplay) {
      forceEyesOpen();
      return;
    }
    robo.setBlinkPaused(false);
    robo.setAutoblinker(false);
    faceEl.style.setProperty('--eye-open-l', '1');
    faceEl.style.setProperty('--eye-open-r', '1');
  }

  function keepFaceAlive() {
    if (!autoPlayActive) return;
    robo.setBlinkPaused(false);
    robo.setAutoblinker(false);
  }

  function clearTransientMotion() {
    robo.setVFlicker(false, 0);
    robo.setHFlicker(false, 0);
    robo.laugh = false;
    robo.confused = false;
    robo.eyeLheightOffset = 0;
    robo.eyeRheightOffset = 0;
    faceEl.classList.remove('eilik-laugh-bounce');
  }

  /** Curiosity + CSS loops only during wander/auto — not while holding a manual emotion. */
  function syncMotionProfile() {
    const hasMotion =
      wanderActive || mouseFollow || faceTrackActive || !!robo.idle;
    const holdEmotion =
      !autoPlayActive &&
      !hasMotion &&
      currentEmotion &&
      currentEmotion !== 'neutral';

    faceEl.classList.toggle('face--hold', holdEmotion);
    robo.setCuriosity(autoPlayActive && wanderActive);

    if (holdEmotion) {
      clearTransientMotion();
      forceEyesOpen();
    }
  }

  function pauseAutoForManual() {
    if (!autoPlayActive) {
      syncMotionProfile();
      return false;
    }
    autoPlayActive = false;
    wanderActive = false;
    faceEl.classList.add('animations-paused');
    faceEl.classList.remove('auto-play-on');
    forceEyesOpen();
    syncMotionProfile();
    syncPanelToggles();
    return true;
  }

  function toggleIdleMode(on) {
    const next = on !== undefined ? !!on : !robo.idle;
    if (next) pauseAutoForManual();
    robo.setIdleMode(next, 2, 2);
    if (next) {
      robo.clearPupilGaze();
      wanderActive = false;
      mouseFollow = false;
      faceTrackActive = false;
      if (faceTracker) faceTracker.stop();
    } else if (autoPlayActive && !mouseFollow && !faceTrackActive) {
      setWanderMode(true);
    }
    syncMotionProfile();
    syncPanelToggles();
    return next;
  }

  function setEmotion(state) {
    let next = String(state).toLowerCase().trim();
    if (next === 'angry') next = 'danger';
    if (next === 'sad') robo.setMood(ROBO_DEFAULT);
    if (!EMOTIONS.includes(next)) {
      console.warn(`[RobotFace] Unknown emotion "${state}". Valid: ${EMOTIONS.join(', ')}`);
      return false;
    }
    if (next === currentEmotion) return true;

    const prev = currentEmotion;

    currentEmotion = next;
    faceEl.setAttribute('data-emotion', next);

    if (window.EilikMorph) window.EilikMorph.startMorph(prev, next);
    faceEl.setAttribute('aria-label', `Robot face — ${next}`);
    if (window.EilikFace) window.EilikFace.onEmotionChange(next, prev);

    if (autoPlayActive) keepFaceAlive();
    syncMotionProfile();
    syncEyeBlink();
    return true;
  }

  function getEmotion() {
    return currentEmotion;
  }

  function cycleEmotion(step = 1) {
    const i = EMOTIONS.indexOf(currentEmotion);
    return setEmotion(EMOTIONS[(i + step + EMOTIONS.length) % EMOTIONS.length]);
  }

  function setMood(mood) {
    robo.setMood(mood);
    syncEyeBlink();
    const linked = MOOD_TO_EMOTION[mood];
    if (linked && linked !== currentEmotion) {
      currentEmotion = linked;
      faceEl.setAttribute('data-emotion', linked);
      faceEl.setAttribute('aria-label', `AI assistant — ${linked}`);
    }
    return true;
  }

  function setPosition(dir) {
    robo.setPosition(dir);
  }

  function gazeLayoutScale() {
    return document.body.classList.contains('robot-screen') &&
      !document.body.classList.contains('has-panel')
      ? 1
      : 0.38;
  }

  function applyGaze(nx, ny) {
    const s = gazeLayoutScale();
    robo.setPupilGaze(nx, ny);
    robo.lookNormalized(nx * s, ny * s);
  }

  function lookAt(clientX, clientY) {
    const nx = (clientX / window.innerWidth - 0.5) * 2;
    const ny = (clientY / window.innerHeight - 0.5) * 2;
    applyGaze(
      Math.max(-1, Math.min(1, nx)),
      Math.max(-1, Math.min(1, ny))
    );
  }

  function lookAtViewer() {
    lastLookDir = 'center';
    applyGaze(0, 0);
    robo.setPosition(ROBO_DEFAULT);
  }

  function getDisplayState() {
    let mode = 'none';
    if (robo.idle) mode = 'idle';
    else if (wanderActive) mode = 'wander';
    else if (mouseFollow) mode = 'mouse';
    else if (faceTrackActive) mode = 'camera';
    return {
      emotion: currentEmotion || 'neutral',
      mode,
      look: lastLookDir,
      autoPlay: autoPlayActive,
      idle: !!robo.idle,
    };
  }

  function restoreDisplayState(s) {
    if (!s) return false;
    const mode = s.mode || 'none';
    const emo = String(s.emotion || 'neutral').toLowerCase();

    autoPlayActive = !!s.autoPlay;
    faceEl.classList.toggle('animations-paused', !autoPlayActive);
    faceEl.classList.toggle('auto-play-on', autoPlayActive);

    faceTrackActive = false;
    if (faceTracker) faceTracker.stop();
    mouseFollow = false;
    wanderActive = false;
    robo.setIdleMode(false);

    if (mode === 'idle' || s.idle) {
      toggleIdleMode(true);
    } else {
      toggleIdleMode(false);
      if (mode === 'wander') setWanderMode(true);
      else if (mode === 'mouse') setMouseFollow(true);
      else if (mode === 'camera') setFaceTrack(true);
      else {
        setWanderMode(false);
        syncPanelToggles();
      }
    }

    setEmotion(emo === 'angry' ? 'danger' : emo);

    const look = String(s.look || 'center').toLowerCase();
    lastLookDir = look;
    const map = {
      n: ROBO_N,
      s: ROBO_S,
      e: ROBO_E,
      w: ROBO_W,
      center: ROBO_DEFAULT,
    };
    if (look === 'center') lookAtViewer();
    else if (map[look] !== undefined) {
      robo.setPosition(map[look]);
      robo.clearPupilGaze();
    }

    syncMotionProfile();
    syncPanelToggles();
    syncEyeBlink();
    return true;
  }

  /** Default Eilik look: two round cyan eyes, centered, no mouth */
  function resetToNormal() {
    robo.setVFlicker(false, 0);
    robo.setHFlicker(false, 0);
    robo.laugh = false;
    robo.confused = false;
    robo.setCyclops(false);
    faceEl.classList.remove('eilik-laugh-bounce', 'cyclops');

    robo.setMood(ROBO_DEFAULT);
    robo.clearPupilGaze();
    lookAtViewer();

    const prev = currentEmotion;
    currentEmotion = '';
    setEmotion('neutral');
    faceEl.setAttribute('aria-label', 'Robot face — normal (dome eyes)');
    if (window.EilikFace && prev !== 'neutral') {
      window.EilikFace.onEmotionChange('neutral', prev);
    }
    syncMotionProfile();
    syncEyeBlink();
    syncPanelToggles();
    return true;
  }

  function wanderGoToStep(index) {
    const step = WANDER_SEQUENCE[index % WANDER_SEQUENCE.length];
    applyGaze(step.gaze[0], step.gaze[1]);
    if (step.pos !== undefined) robo.setPosition(step.pos);
    if (step.emotion) setEmotion(step.emotion);
    if (step.mood !== undefined) robo.setMood(step.mood);
    else if (step.emotion === 'happy' || step.emotion === 'smile') robo.setMood(ROBO_HAPPY);
    else if (step.emotion === 'sleepy') robo.setMood(ROBO_TIRED);
    else if (step.emotion === 'angry' || step.emotion === 'danger') robo.setMood(ROBO_ANGRY);
    else robo.setMood(ROBO_DEFAULT);
    syncEyeBlink();
  }

  function wanderNext() {
    wanderIndex = (wanderIndex + 1) % WANDER_SEQUENCE.length;
    wanderGoToStep(wanderIndex);
    wanderStepAt = performance.now() + 1800 + Math.random() * 1200;
  }

  function wanderTick() {
    if (!wanderActive || mouseFollow || faceTrackActive || robo.idle) return;
    if (performance.now() >= wanderStepAt) wanderNext();
  }

  async function setFaceTrack(on) {
    if (!faceTracker) {
      if (camStatus) camStatus.textContent = 'Face track module not loaded.';
      return false;
    }
    if (on) {
      if (autoDriveActive) await setAutoDrive(false);
      const ok = await faceTracker.start();
      if (!ok) return false;
      pauseAutoForManual();
      faceTrackActive = true;
      wanderActive = false;
      mouseFollow = false;
      robo.setIdleMode(false);
      robo.setMood(ROBO_DEFAULT);
      syncEyeBlink();
    } else {
      if (faceTracker) faceTracker.stop();
      faceTrackActive = false;
      lookAtViewer();
      if (autoPlayActive) setWanderMode(true);
    }
    syncMotionProfile();
    syncPanelToggles();
    return true;
  }

  async function toggleFaceTrack() {
    return setFaceTrack(!faceTrackActive);
  }

  async function setAutoDrive(on) {
    if (!obstacleDriver) {
      if (driveStatus) driveStatus.textContent = 'Obstacle drive module not loaded.';
      return false;
    }
    if (on) {
      if (faceTrackActive) await setFaceTrack(false);
      wanderActive = false;
      mouseFollow = false;
      robo.setIdleMode(false);
      const ok = await obstacleDriver.start();
      if (!ok) return false;
      autoDriveActive = true;
      if (camPreview) camPreview.classList.add('cam-preview--live', 'cam-preview--drive');
      setEmotion('neutral');
    } else {
      autoDriveActive = false;
      obstacleDriver.stop();
      if (camPreview) camPreview.classList.remove('cam-preview--drive');
    }
    syncMotionProfile();
    syncPanelToggles();
    return true;
  }

  async function toggleAutoDrive() {
    return setAutoDrive(!autoDriveActive);
  }

  function setWanderMode(on) {
    wanderActive = !!on;
    if (wanderActive) {
      faceTrackActive = false;
      autoDriveActive = false;
      if (faceTracker) faceTracker.stop();
      if (obstacleDriver) obstacleDriver.stop();
      mouseFollow = false;
      robo.setIdleMode(false);
      wanderGoToStep(wanderIndex);
      wanderStepAt = performance.now() + 2000;
    }
    syncMotionProfile();
    syncPanelToggles();
  }

  /** Stop/start all automatic animation (wander, blink, idle, breathe, etc.) */
  function setAutoPlay(on, opts = {}) {
    const soft = !!opts.soft;
    autoPlayActive = !!on;
    faceEl.classList.toggle('animations-paused', !autoPlayActive);
    faceEl.classList.toggle('auto-play-on', autoPlayActive);
    faceEl.classList.remove('eilik-laugh-bounce');

    if (autoPlayActive) {
      syncEyeBlink();
      keepFaceAlive();
      setWanderMode(true);
    } else if (soft) {
      wanderActive = false;
      forceEyesOpen();
    } else {
      wanderActive = false;
      mouseFollow = false;
      faceTrackActive = false;
      autoDriveActive = false;
      if (faceTracker) faceTracker.stop();
      if (obstacleDriver) obstacleDriver.stop();
      robo.setIdleMode(false);
      resetToNormal();
      forceEyesOpen();
    }
    syncMotionProfile();
    syncPanelToggles();
    return autoPlayActive;
  }

  function toggleAutoPlay() {
    return setAutoPlay(!autoPlayActive);
  }

  function clearReactionRestore() {
    if (reactionRestoreTimer) {
      clearTimeout(reactionRestoreTimer);
      reactionRestoreTimer = null;
    }
  }

  /** Default calm face — idle mode, neutral expression, looking at viewer. */
  function restoreNaturalDefault() {
    clearReactionRestore();
    faceEl.classList.remove('eilik-laugh-bounce', 'eilik-jiggle', 'eilik-pop');
    enterNaturalIdle();
    if (currentEmotion !== DEFAULT_IDLE_EMOTION) {
      setEmotion(DEFAULT_IDLE_EMOTION);
    }
  }

  function scheduleReactionRestore(ms = REACTION_RESTORE_MS) {
    clearReactionRestore();
    reactionRestoreTimer = setTimeout(() => {
      reactionRestoreTimer = null;
      restoreNaturalDefault();
    }, Math.max(800, ms));
  }

  /** Default calm face — no wander shuffle, gentle idle motion only. */
  function enterNaturalIdle() {
    autoPlayActive = false;
    wanderActive = false;
    mouseFollow = false;
    faceTrackActive = false;
    autoDriveActive = false;
    if (faceTracker) faceTracker.stop();
    if (obstacleDriver) obstacleDriver.stop();
    faceEl.classList.remove('auto-play-on');
    faceEl.classList.remove('animations-paused');
    robo.setIdleMode(true, 2, 2);
    robo.clearPupilGaze();
    lookAtViewer();
    syncMotionProfile();
    syncPanelToggles();
    forceEyesOpen();
  }

  function isAutoPlayActive() {
    return autoPlayActive;
  }

  function setMouseFollow(on) {
    mouseFollow = !!on;
    if (mouseFollow) {
      pauseAutoForManual();
      faceTrackActive = false;
      autoDriveActive = false;
      if (faceTracker) faceTracker.stop();
      if (obstacleDriver) obstacleDriver.stop();
      wanderActive = false;
      robo.setIdleMode(false);
    } else {
      lookAtViewer();
      robo.clearPupilGaze();
      if (autoPlayActive && !wanderActive) setWanderMode(true);
    }
    syncMotionProfile();
    syncPanelToggles();
  }

  function syncPanelToggles() {
    const btnAuto = document.querySelector('[data-action="auto-play"]');
    if (btnAuto) {
      btnAuto.classList.toggle('active', autoPlayActive);
      btnAuto.textContent = autoPlayActive ? 'Stop Auto' : 'Start Auto';
    }
    document.querySelector('[data-action="follow"]')?.classList.toggle('active', mouseFollow);
    document.querySelector('[data-action="wander"]')?.classList.toggle('active', wanderActive);
    document.querySelector('[data-action="facetrack"]')?.classList.toggle('active', faceTrackActive);
    document.querySelector('[data-action="autodrive"]')?.classList.toggle('active', autoDriveActive);
    document.querySelector('[data-action="idle"]')?.classList.toggle('active', robo.idle);
  }

  function init() {
    const params = new URLSearchParams(window.location.search);
    const wantsPanel =
      params.has('panel') ||
      params.has('controls') ||
      /\/controls\.html$/i.test(window.location.pathname || '');
    if (wantsPanel) {
      document.body.classList.add('has-panel');
      document.body.classList.remove('robot-screen');
    } else {
      document.body.classList.add('robot-screen');
      document.body.classList.remove('has-panel');
    }
    if (params.has('round') || params.has('circle')) {
      document.body.classList.add('round-screen');
    }

    const svgFace = document.querySelector('.eilik-face');
    if (svgFace) {
      const fullBleed =
        document.body.classList.contains('robot-screen') &&
        !document.body.classList.contains('has-panel');
      svgFace.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    }

    robo.begin(60);
    robo.setSmoothness(0.24);
    const onResize = () => robo.updateScreenShiftLimits?.();
    window.addEventListener('resize', onResize);
    robo.setMood(ROBO_DEFAULT);
    const isJarvis = params.has('jarvis') || params.has('mega');
    enterNaturalIdle();
    setEmotion(DEFAULT_IDLE_EMOTION);
    syncEyeBlink();
    syncMotionProfile();

    setInterval(wanderTick, 120);

    document.addEventListener('keydown', (e) => {
      const emoKey = KEY_MAP[e.key];
      if (emoKey) {
        setEmotion(emoKey);
        if (emoKey === 'confused') {
          robo.anim_confused();
          if (window.EilikFace) window.EilikFace.reactConfused();
        }
        if (emoKey === 'laugh') {
          robo.anim_laugh();
          if (window.EilikFace) window.EilikFace.reactLaugh();
        }
        if (emoKey === 'wink' && window.EilikFace) window.EilikFace.reactWink();
        if (emoKey === 'kiss' && window.EilikFace) window.EilikFace.reactKiss();
      }

      if (e.key === 'ArrowRight') cycleEmotion(1);
      if (e.key === 'ArrowLeft') cycleEmotion(-1);

      if (e.key === 'w' || e.key === 'W') robo.setPosition(ROBO_N);
      if (e.key === 's' || e.key === 'S') robo.setPosition(ROBO_S);
      if (e.key === 'a' || e.key === 'A') robo.setPosition(ROBO_W);
      if (e.key === 'd' || e.key === 'D') robo.setPosition(ROBO_E);

      if ((e.key === 'b' || e.key === 'B') && !robo.blinkPaused) robo.blink();
      if (e.key === 'm' || e.key === 'M') setMouseFollow(!mouseFollow);
      if (e.key === 'f' || e.key === 'F') toggleFaceTrack();
      if (e.key === 'o' || e.key === 'O') setWanderMode(!wanderActive);
      if (e.key === 'p' || e.key === 'P') toggleAutoPlay();
      if (e.key === 'i' || e.key === 'I') toggleIdleMode();
      if (e.key === 'n' || e.key === 'N') wanderNext();
      if (e.key === 'r' || e.key === 'R') resetToNormal();
    });

    document.addEventListener('mousemove', (e) => {
      if (mouseFollow) lookAt(e.clientX, e.clientY);
    });

    bindPanel();
    console.info(
      '[RobotFace] Emotions A→Z: 1 angry, 2 confused, 3 danger, 4 excited, 5 happy, 6 kiss, 7 laugh, 8 neutral, 9 sad, 0 sleepy, Q smile, U surprised, T talk, Z wink. P=auto, R=normal.'
    );
  }

  function bindPanel() {
    const panel = document.getElementById('roboPanel');
    if (!panel) return;

    panel.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      const action = btn.dataset.action;

      if (
        action?.startsWith('emo-') ||
        action === 'wander' ||
        action === 'idle' ||
        action === 'follow' ||
        action === 'facetrack' ||
        action?.startsWith('look-') ||
        action === 'confused' ||
        action === 'laugh' ||
        action === 'blink'
      ) {
        pauseAutoForManual();
      }

      if (action === 'blink' && !robo.blinkPaused) robo.blink();
      if (action === 'confused') {
        robo.anim_confused();
        setEmotion('confused');
        if (window.EilikFace) window.EilikFace.reactConfused();
      }
      if (action === 'laugh') {
        robo.anim_laugh();
        setEmotion('laugh');
        if (window.EilikFace) window.EilikFace.reactLaugh();
      }
      if (action === 'center' || action === 'normal') resetToNormal();
      if (action === 'auto-play') toggleAutoPlay();
      if (action === 'wander') setWanderMode(!wanderActive);
      if (action === 'idle') toggleIdleMode(!robo.idle);
      if (action === 'follow') setMouseFollow(!mouseFollow);
      if (action === 'facetrack') toggleFaceTrack();
      if (action === 'autodrive') toggleAutoDrive();
      if (action === 'cyclops') {
        robo.setCyclops(!robo.cyclops);
        btn.classList.toggle('active', robo.cyclops);
      }
      if (action?.startsWith('look-')) {
        const map = {
          'look-n': ROBO_N,
          'look-e': ROBO_E,
          'look-s': ROBO_S,
          'look-w': ROBO_W,
        };
        if (map[action] !== undefined) {
          wanderActive = false;
          mouseFollow = false;
          faceTrackActive = false;
          if (faceTracker) faceTracker.stop();
          const dirMap = {
            'look-n': 'n',
            'look-e': 'e',
            'look-s': 's',
            'look-w': 'w',
          };
          lastLookDir = dirMap[action] || 'center';
          robo.setPosition(map[action]);
          syncPanelToggles();
        }
      }
      if (action?.startsWith('mood-')) {
        const moods = {
          'mood-default': ROBO_DEFAULT,
          'mood-happy': ROBO_HAPPY,
          'mood-tired': ROBO_TIRED,
          'mood-angry': ROBO_ANGRY,
        };
        if (moods[action] !== undefined) setMood(moods[action]);
      }
      if (action?.startsWith('emo-')) {
        let emo = action.replace('emo-', '');
        if (emo === 'angry') emo = 'danger';
        wanderActive = false;
        mouseFollow = false;
        if (faceTracker) faceTracker.stop();
        setEmotion(emo);
        keepFaceAlive();
        syncPanelToggles();
        if (emo === 'wink' && window.EilikFace) window.EilikFace.reactWink();
        if (emo === 'laugh' && window.EilikFace) window.EilikFace.reactLaugh();
        if (emo === 'kiss' && window.EilikFace) window.EilikFace.reactKiss();
      }
    });

    syncPanelToggles();
  }

  const RobotFace = Object.freeze({
    setEmotion,
    restoreNaturalDefault,
    scheduleReactionRestore,
    getEmotion,
    getDisplayState,
    restoreDisplayState,
    cycleEmotion,
    setMood,
    setPosition,
    lookAt,
    lookAtViewer,
    resetToNormal,
    setMouseFollow,
    setWanderMode,
    toggleIdleMode,
    setAutoPlay,
    toggleAutoPlay,
    pauseAutoForManual,
    enterNaturalIdle,
    isAutoPlayActive,
    setFaceTrack,
    toggleFaceTrack,
    setAutoDrive,
    toggleAutoDrive,
    wanderNext,
    faceTracker,
    obstacleDriver,
    robo,
    EMOTIONS,
    WANDER_SEQUENCE,
  });

  window.setEmotion = setEmotion;
  window.RobotFace = RobotFace;
  window.robo = robo;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
