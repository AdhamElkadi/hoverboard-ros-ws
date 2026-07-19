const rclnodejs = require('rclnodejs');

async function initROS() {
  await rclnodejs.init();
  const node = rclnodejs.createNode('eilik_eye_display');

  // ⚙️ CHANGE THESE TO MATCH YOUR ACTUAL CAMERA RESOLUTION
  const CAM_WIDTH = 640;
  const CAM_HEIGHT = 480;

  // ── EXISTING: Face tracking subscription (unchanged) ──
  node.createSubscription(
    'geometry_msgs/msg/PointStamped',
    '/face/center',
    (msg) => {
      const rawX = msg.point.x;
      const rawY = msg.point.y;

      let nx = -((rawX / CAM_WIDTH) * 2.0 - 1.0);
      let ny = ((rawY / CAM_HEIGHT) * 2.0 - 1.0);

      nx = isNaN(nx) ? 0 : Math.max(-1, Math.min(1, nx));
      ny = isNaN(ny) ? 0 : Math.max(-1, Math.min(1, ny));

      console.log(`Face: px(${rawX},${rawY}) → gaze(${nx.toFixed(2)}, ${ny.toFixed(2)})`);

      if (window.setEyeGaze) {
        window.setEyeGaze(nx, ny);
      }
    }
  );

  // ── NEW: Emotion command subscription ──
  node.createSubscription(
    'std_msgs/msg/String',
    '/eilik/command',
    (msg) => {
      const emotion = msg.data.toLowerCase().trim();
      console.log(`[Eilik] Emotion command received: "${emotion}"`);

      if (window.setEmotion) {
        const success = window.setEmotion(emotion);
        if (success) {
          console.log(`[Eilik] ✅ Emotion changed to: ${emotion}`);
        } else {
          console.warn(`[Eilik] ❌ Failed to set emotion: ${emotion}`);
        }
      } else {
        console.warn('[Eilik] window.setEmotion not available yet');
      }
    }
  );

  setInterval(() => {
    rclnodejs.spin(node);
  }, 33);
}

document.addEventListener('DOMContentLoaded', initROS);
