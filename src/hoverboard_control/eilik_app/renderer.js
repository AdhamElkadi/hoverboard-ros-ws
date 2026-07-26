const rclnodejs = require('rclnodejs');

async function initROS() {
  await rclnodejs.init();
  const node = rclnodejs.createNode('eilik_eye_display');

  const CAM_WIDTH = 640;
  const CAM_HEIGHT = 480;

  // EXISTING: eyes follow the face
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
      if (window.setEyeGaze) window.setEyeGaze(nx, ny);
    }
  );

  // NEW: change expression when a command arrives
  node.createSubscription(
    'std_msgs/msg/String',
    '/eilik/command',
    (msg) => {
      const emotion = msg.data.toLowerCase().trim();
      console.log(`[Eilik] Emotion command: ${emotion}`);
      if (window.setEmotion) window.setEmotion(emotion);
    }
  );

  setInterval(() => {
    rclnodejs.spin(node);
  }, 33);
}

document.addEventListener('DOMContentLoaded', initROS);
