const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1920,
    height: 1080,
    fullscreen: true,
    frame: false,           // Removes title bar and window borders
    transparent: false,     // Solid background (required for robot-screen CSS)
    backgroundColor: '#000000',
    webPreferences: {
      preload: path.join(__dirname, 'renderer.js'), // ROS bridge runs here
      contextIsolation: false, // Required for script.js to access window.RobotFace
      nodeIntegration: true    // Allows rclnodejs to run in renderer
    }
  });

  // Load local index.html directly - NO web server or URL needed
  win.loadFile(path.join(__dirname, 'index.html'));
  
  // Hide menu bar completely
  win.setMenuBarVisibility(false);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
