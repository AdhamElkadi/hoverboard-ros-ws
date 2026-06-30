const rclnodejs = require('rclnodejs');

async function initROS() {
  await rclnodejs.init();
  const node = rclnodejs.createNode('eilik_eye_display');
  
  // ️ CHANGE THESE TO MATCH YOUR ACTUAL CAMERA RESOLUTION
  const CAM_WIDTH = 640;
  const CAM_HEIGHT = 480; 
  
  node.createSubscription(
    'geometry_msgs/msg/PointStamped',
    '/face/center',
    (msg) => {
      const rawX = msg.point.x;
      const rawY = msg.point.y;
      
      // Convert PIXELS → NORMALIZED GAZE (-1 to 1)
      let nx = -((rawX / CAM_WIDTH) * 2.0 - 1.0);
      let ny = ((rawY / CAM_HEIGHT) * 2.0 - 1.0);
      
      // SAFETY CLAMP: Prevent squash/NaN issues
      nx = isNaN(nx) ? 0 : Math.max(-1, Math.min(1, nx));
      ny = isNaN(ny) ? 0 : Math.max(-1, Math.min(1, ny));
      
      // DEBUG LOG: Check console in Electron DevTools (Ctrl+Shift+I)
      console.log(`Face: px(${rawX},${rawY}) → gaze(${nx.toFixed(2)}, ${ny.toFixed(2)})`);
      
      if (window.setEyeGaze) {
        window.setEyeGaze(nx, ny);
      }
    }
  );
  
  setInterval(() => {
    rclnodejs.spin(node);
  }, 33);
}

document.addEventListener('DOMContentLoaded', initROS);
