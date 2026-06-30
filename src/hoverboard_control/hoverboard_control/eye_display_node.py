import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
import tkinter as tk
import cairo
import math
import threading
import random
import time

class EilikEyeDisplay(Node):
    def __init__(self):
        super().__init__('eilik_eye_display')
        
        # === DESIGN CONSTANTS (Matching eilik-face.css & SVG) ===
        self.W = 1920
        self.H = 1080
        self.COLOR_CYAN = (0.0, 0.91, 1.0, 1.0)      # #00e8ff RGBA
        self.COLOR_GLOW = (0.0, 0.66, 0.77, 1.0)     # #00a8c4 RGBA
        self.COLOR_BG = (0.0, 0.0, 0.0, 1.0)          # #000000
        
        # Scale factor to fit SVG viewBox (200x160) into screen
        self.SCALE = min(self.W / 200, self.H / 160) * 0.85 
        
        # Base positions from SVG coordinates
        self.L_CX = 56 * self.SCALE
        self.R_CX = 144 * self.SCALE
        self.EYE_CY = 72 * self.SCALE
        
        # Animation State
        self.target_nx, self.target_ny = 0.0, 0.0
        self.curr_nx, self.curr_ny = 0.0, 0.0
        self.smooth = 0.22  # Matches JS smoothFactor
        
        # Blink State
        self.blink_timer = 0
        self.next_blink = random.uniform(2500, 4500)
        self.is_blinking = False
        self.blink_progress = 0
        
        # Max translation distance for eyes
        self.MAX_MOVE_X = 30 * self.SCALE
        self.MAX_MOVE_Y = 20 * self.SCALE
        
        # === INIT TKINTER + CAIRO SURFACE ===
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.canvas = tk.Canvas(self.root, width=self.W, height=self.H, 
                                highlightthickness=0)
        self.canvas.pack()
        
        # Create Cairo surface for high-quality vector rendering
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.W, self.H)
        self.ctx = cairo.Context(self.surface)
        
        # ROS subscription
        self.sub = self.create_subscription(PointStamped, '/face/center', self.face_cb, 1)
        
        # Start 60fps render loop
        self.last_t = time.time()
        self._render_loop()
        self.get_logger().info("Native Eilik Display Ready (Cairo Vector)")

    def _draw_bean_eye(self, ctx, cx, cy, scale_y=1.0):
        """Draw exact Eilik bean shape with neon glow"""
        # Glow layers (true alpha transparency)
        glow_layers = [
            ((0.0, 0.78, 1.0, 0.1), 2.4),   # Outer halo
            ((0.0, 0.91, 1.0, 0.3), 1.7),   # Mid glow
            (self.COLOR_GLOW, 1.1)           # Inner bright glow
        ]
        
        for color, s in glow_layers:
            ctx.save()
            ctx.translate(cx, cy)
            ctx.scale(s, s * scale_y)
            ctx.translate(-cx, -cy)
            
            # Bean path matching SVG exactly
            ctx.move_to(38*self.SCALE, 72*self.SCALE)
            ctx.curve_to(56*self.SCALE, 54*self.SCALE, 74*self.SCALE, 54*self.SCALE, 
                        74*self.SCALE, 72*self.SCALE)
            ctx.curve_to(74*self.SCALE, 90*self.SCALE, 56*self.SCALE, 90*self.SCALE, 
                        38*self.SCALE, 72*self.SCALE)
            ctx.close_path()
            
            ctx.set_source_rgba(*color)
            ctx.fill()
            ctx.restore()
        
        # Main cyan eye body
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(1.0, scale_y)
        ctx.translate(-cx, -cy)
        
        ctx.move_to(38*self.SCALE, 72*self.SCALE)
        ctx.curve_to(56*self.SCALE, 54*self.SCALE, 74*self.SCALE, 54*self.SCALE, 
                    74*self.SCALE, 72*self.SCALE)
        ctx.curve_to(74*self.SCALE, 90*self.SCALE, 56*self.SCALE, 90*self.SCALE, 
                    38*self.SCALE, 72*self.SCALE)
        ctx.close_path()
        
        ctx.set_source_rgba(*self.COLOR_CYAN)
        ctx.fill()
        ctx.restore()

    def _draw_mouth(self, ctx):
        """Draw Eilik smile arc matching SVG stroke"""
        ctx.arc(100*self.SCALE, 120*self.SCALE, 30*self.SCALE, 
                math.radians(200), math.radians(340))
        ctx.set_line_width(max(2, int(8*self.SCALE)))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(*self.COLOR_CYAN)
        ctx.stroke()

    def face_cb(self, msg):
        """Thread-safe gaze update"""
        nx = -((msg.point.x / 640.0) * 2.0 - 1.0)
        ny = (msg.point.y / 480.0) * 2.0 - 1.0
        self.target_nx = max(-1, min(1, nx))
        self.target_ny = max(-1, min(1, ny))

    def _update_blink(self, dt_ms):
        """Squash eyes vertically for authentic Eilik blink"""
        self.blink_timer += dt_ms
        if not self.is_blinking and self.blink_timer > self.next_blink:
            self.is_blinking = True
            self.blink_progress = 0
            
        if self.is_blinking:
            self.blink_progress += dt_ms / 120.0
            scaleY = max(0.05, 1.0 - math.sin(self.blink_progress * math.pi))
            
            if self.blink_progress >= 1.0:
                self.is_blinking = False
                self.blink_timer = 0
                self.next_blink = random.uniform(2500, 4500)
                return 1.0  # Reset scale
            return scaleY
        return 1.0

    def _render_loop(self):
        """Main Cairo rendering loop on Tkinter main thread"""
        # Smooth interpolation
        self.curr_nx += (self.target_nx - self.curr_nx) * self.smooth
        self.curr_ny += (self.target_ny - self.curr_ny) * self.smooth
        
        # Calculate pixel translation
        dx = self.curr_nx * self.MAX_MOVE_X
        dy = self.curr_ny * self.MAX_MOVE_Y
        
        # Update blink
        now = time.time()
        dt_ms = (now - self.last_t) * 1000
        self.last_t = now
        scale_y = self._update_blink(dt_ms)
        
        # Clear canvas
        self.ctx.set_source_rgba(*self.COLOR_BG)
        self.ctx.paint()
        
        # Draw eyes with translation and blink squash
        self._draw_bean_eye(self.ctx, self.L_CX + dx, self.EYE_CY + dy, scale_y)
        self._draw_bean_eye(self.ctx, self.R_CX + dx, self.EYE_CY + dy, scale_y)
        
        # Draw static mouth
        self._draw_mouth(self.ctx)
        
        # Convert Cairo surface to Tkinter PhotoImage
        data = self.surface.get_data()
        photo = tk.PhotoImage(width=self.W, height=self.H, data=data)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo  # Prevent garbage collection
        
        # Schedule next frame (~16ms = 60fps)
        self.root.after(16, self._render_loop)
        try: 
            self.root.update_idletasks()
        except tk.TclError: 
            pass

def spin_thread(node):
    ex = rclpy.executors.SingleThreadedExecutor()
    ex.add_node(node)
    try: 
        ex.spin()
    finally: 
        ex.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = EilikEyeDisplay()
    t = threading.Thread(target=spin_thread, args=(node,), daemon=True)
    t.start()
    try: 
        node.root.mainloop()
    except KeyboardInterrupt: 
        pass
    finally: 
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
