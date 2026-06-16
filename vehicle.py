import pygame
import math

pygame.init()

WIDTH, HEIGHT = 820, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Braitenberg Vehicle 5 - Logic")

clock = pygame.time.Clock()
fps = 60
font = pygame.font.SysFont("consolas", 13)
font_bold = pygame.font.SysFont("consolas", 14, bold=True)


# ============================================================
# THRESHOLD DEVICE  (Figure 9)
#
# Becomes active when:  activation - inhibition >= threshold
# Negative threshold means active by default (no input needed).
# An inhibitory connection subtracts 1 from net activation.
# ============================================================
class ThresholdDevice:
    def __init__(self, threshold):
        self.threshold = threshold
        self.active = False
        self.net = 0

    def update(self, activation, inhibition=0):
        self.net = activation - inhibition
        self.active = self.net >= self.threshold
        return self.active


# ============================================================
# LOGIC GATES  (Figure 9 — three configurations)
#
#  OR  gate : threshold = 1  → active if ANY input is 1
#  AND gate : threshold = 2  → active only if BOTH inputs are 1
#  NOT gate : threshold = 0  → active by default;
#             inhibited (silenced) when its input is 1
# ============================================================
class OrGate(ThresholdDevice):
    """OR: active when at least one input fires (threshold=1)."""
    def __init__(self):
        super().__init__(threshold=1)

    def update(self, a, b):
        return super().update(activation=(1 if a else 0) + (1 if b else 0))


class AndGate(ThresholdDevice):
    """AND: active only when both inputs fire (threshold=2)."""
    def __init__(self):
        super().__init__(threshold=2)

    def update(self, a, b):
        return super().update(activation=(1 if a else 0) + (1 if b else 0))


class NotGate(ThresholdDevice):
    """NOT: active by default (threshold=0); inhibited when input fires."""
    def __init__(self):
        super().__init__(threshold=0)

    def update(self, a):
        return super().update(activation=0, inhibition=1 if a else 0)


# ============================================================
# COUNTER NETWORK  (Figure 10b)
#
# Emits one pulse for every 3rd input pulse.
# Uses three threshold devices in a chain with feedback:
#
#   input ──► [TD1, t=1] ──► [TD2, t=2] ──► [TD3, t=2] ──► output
#                                 ▲                │
#                                 └────────────────┘  (feedback)
#
# TD2 needs (TD1 + feedback from TD3) ≥ 2 to fire.
# TD3 needs (TD2 + self-latch) ≥ 2 to fire (one-cycle latch).
# On every 3rd rising edge the output fires once then resets.
# ============================================================
class CounterNetwork:
    def __init__(self):
        self.td1 = ThresholdDevice(1)
        self.td2 = ThresholdDevice(2)
        self.td3 = ThresholdDevice(2)
        self._state = 0          # counts 0 → 1 → 2 → fire
        self._prev_signal = False
        self.output = False
        self.count = 0           # shown in HUD

    def update(self, signal):
        rising_edge = signal and not self._prev_signal
        self._prev_signal = signal

        self.output = False
        if rising_edge:
            self._state += 1
            self.count = self._state
            # TD1 always passes the rising edge
            self.td1.update(1)
            # TD2 fires on 2nd state (needs TD1 + 1 carry)
            self.td2.update(self._state if self._state >= 2 else 0)
            # TD3 fires when state reaches 3 (output pulse)
            if self._state >= 3:
                self.td3.update(2)   # threshold=2 met
                self.output = True
                self._state = 0      # reset counter
            else:
                self.td3.update(0)
        return self.output


# ============================================================
# MEMORY DEVICE  (Chapter 5 — reciprocal threshold devices)
#
# Once a target is stored, the two devices keep each other
# active (reciprocal activation).  Strength decays over time
# when the target is no longer seen; at zero the latch opens.
# ============================================================
class MemoryDevice:
    def __init__(self, decay=0.18, max_strength=100):
        self.active = False
        self.strength = 0
        self.max_strength = max_strength
        self.decay = decay
        self.name = None
        self.pos = None

    def store(self, name, pos):
        self.active = True
        self.strength = self.max_strength
        self.name = name
        self.pos = pos

    def update(self):
        if self.strength > 0:
            self.strength -= self.decay
        if self.strength <= 0:
            self.strength = 0
            self.active = False
            self.name = None
            self.pos = None


# ============================================================
# STIMULUS  (named target — "proper noun" of Chapter 5)
# ============================================================
class Stimulus:
    def __init__(self, x, y, color, name, radius=18):
        self.x = x
        self.y = y
        self.color = color
        self.name = name
        self.radius = radius

    def pos(self):
        return (self.x, self.y)

    def move_to(self, pos):
        self.x, self.y = pos

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)
        lbl = font_bold.render(self.name, True, (0, 0, 0))
        surface.blit(lbl, (int(self.x) - lbl.get_width()//2, int(self.y) - self.radius - 18))


# ============================================================
# VEHICLE 5
# ============================================================
class Vehicle:
    def __init__(self, x, y, radius=20, heading=0):
        self.x = x
        self.y = y
        self.radius = radius
        self.heading = heading

        self.sensor_offset = math.radians(30)
        self.sensor_dist = self.radius

        self.left_motor = 0.0
        self.right_motor = 0.0

        # --- Figure 9: Logic Gates ---
        self.or_gate = OrGate()    # approach any detected target
        self.and_gate = AndGate()  # both targets visible → compare
        self.not_gate = NotGate()  # too-close inhibition

        # --- Figure 10b: Counter ---
        self.counter = CounterNetwork()
        self.third_pulse = False

        # --- Memory ---
        self.memory = MemoryDevice()

        # --- State ---
        self.mode = "SEARCH"

    # ----------------------------------------------------------
    def _sensors(self):
        a = self.sensor_offset
        d = self.sensor_dist
        ch = math.cos(self.heading)
        sh = math.sin(self.heading)

        def world(lx, ly):
            return (self.x + ch*lx - sh*ly,
                    self.y + sh*lx + ch*ly)

        left  = world( math.cos(+a)*d,  math.sin(+a)*d)
        right = world( math.cos(-a)*d,  math.sin(-a)*d)
        return left, right

    def _intensity(self, px, py, sx, sy):
        d2 = max((sx-px)**2 + (sy-py)**2, 100)
        return min(15000 / d2, 5.0)

    def _source_intensity(self, source):
        lp, rp = self._sensors()
        li = self._intensity(lp[0], lp[1], source.x, source.y)
        ri = self._intensity(rp[0], rp[1], source.x, source.y)
        return li + ri, li, ri

    # ----------------------------------------------------------
    def update(self, sources):
        DETECT_THRESH = 0.5   # minimum total intensity to "see" a source
        CLOSE_THRESH  = 3.5   # total intensity that triggers NOT-inhibition

        # Evaluate each named source
        evals = []
        for s in sources:
            total, li, ri = self._source_intensity(s)
            evals.append({
                "source": s,
                "total": total,
                "li": li,
                "ri": ri,
                "seen": total >= DETECT_THRESH,
            })
        evals.sort(key=lambda e: e["total"], reverse=True)

        seen_y1 = any(e["seen"] and e["source"].name == "Y1" for e in evals)
        seen_y2 = any(e["seen"] and e["source"].name == "Y2" for e in evals)
        any_seen = evals[0]["seen"] if evals else False
        too_close = evals[0]["total"] >= CLOSE_THRESH if evals else False

        # ---- Figure 9: Logic Gates ----
        or_active  = self.or_gate.update(seen_y1, seen_y2)
        and_active = self.and_gate.update(seen_y1, seen_y2)
        not_active = self.not_gate.update(too_close)   # False = inhibited

        # ---- Figure 10b: Counter (every 3rd detection event) ----
        self.third_pulse = self.counter.update(or_active)

        # ---- Behavior ----
        if or_active:
            best = evals[0]
            s = best["source"]
            li, ri = best["li"], best["ri"]

            # Memory: store the best seen named target
            self.memory.store(s.name, s.pos())

            if self.third_pulse:
                # Every 3rd detection → spin (counting behaviour, Figure 10b)
                self.mode = "COUNT_3RD_PULSE"
                self.left_motor  =  2.0
                self.right_motor = -2.0

            elif and_active:
                # Both Y1 and Y2 visible → compare, approach the stronger
                self.mode = "AND: COMPARE Y1 vs Y2"
                self.left_motor  = 1.0 + ri * 1.8
                self.right_motor = 1.0 + li * 1.8

            else:
                # Only one target visible
                self.mode = f"OR: APPROACH {s.name}"
                self.left_motor  = 1.0 + ri * 1.8
                self.right_motor = 1.0 + li * 1.8

            # NOT gate: inhibit motors when too close
            if not not_active:
                self.left_motor  *= 0.3
                self.right_motor *= 0.3
                self.mode = "NOT: TOO CLOSE (inhibit)"

        elif self.memory.active:
            self.mode = f"MEMORY: seeking {self.memory.name}"
            lp, rp = self._sensors()
            mx, my = self.memory.pos
            li = self._intensity(lp[0], lp[1], mx, my)
            ri = self._intensity(rp[0], rp[1], mx, my)
            self.left_motor  = 1.0 + ri
            self.right_motor = 1.0 + li

        else:
            self.mode = "SEARCH"
            self.left_motor  = 1.0
            self.right_motor = 1.35

        self.memory.update()

        fwd  = (self.left_motor + self.right_motor) / 2
        turn = (self.right_motor - self.left_motor) * 0.03
        self.heading += turn
        self.x = (self.x + fwd * math.cos(self.heading)) % WIDTH
        self.y = (self.y + fwd * math.sin(self.heading)) % HEIGHT

        # Store gate states for drawing
        self._or_active  = or_active
        self._and_active = and_active
        self._not_active = not_active

    # ----------------------------------------------------------
    def draw(self, surface):
        # Body
        pygame.draw.circle(surface, (30, 80, 220), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0),     (int(self.x), int(self.y)), self.radius, 2)

        # Sensors
        lp, rp = self._sensors()
        pygame.draw.circle(surface, (220, 50, 50), (int(lp[0]), int(lp[1])), 5)
        pygame.draw.circle(surface, (220, 50, 50), (int(rp[0]), int(rp[1])), 5)

        # Heading arrow
        nx = self.x + math.cos(self.heading) * self.radius
        ny = self.y + math.sin(self.heading) * self.radius
        pygame.draw.line(surface, (0, 0, 0), (int(self.x), int(self.y)), (int(nx), int(ny)), 2)

        # ---- HUD (left panel) ----
        mode_colors = {
            "SEARCH":                   (100, 100, 100),
            "NOT: TOO CLOSE (inhibit)": (200,  30,  30),
            "COUNT_3RD_PULSE":          (160,   0, 200),
        }
        mc = mode_colors.get(self.mode,
             (0, 140, 0) if "OR" in self.mode or "AND" in self.mode or "MEMORY" in self.mode
             else (0, 0, 0))

        y = 10
        surface.blit(font_bold.render(f"MODE: {self.mode}", True, mc), (10, y)); y += 22

        # Gate display
        def gc(active): return (0, 170, 0) if active else (190, 40, 40)

        surface.blit(font_bold.render("── Figure 9: Logic Gates ──", True, (30,30,30)), (10, y)); y += 18
        surface.blit(font.render(f"OR  (thresh=1) : {'ACTIVE' if self._or_active  else 'off'}", True, gc(self._or_active)),  (10, y)); y += 17
        surface.blit(font.render(f"AND (thresh=2) : {'ACTIVE' if self._and_active else 'off'}", True, gc(self._and_active)), (10, y)); y += 17
        surface.blit(font.render(f"NOT (thresh=0) : {'ACTIVE' if self._not_active else 'INHIBITED'}", True, gc(self._not_active)), (10, y)); y += 22

        surface.blit(font_bold.render("── Figure 10b: Counter ──", True, (30,30,30)), (10, y)); y += 18
        surface.blit(font.render(f"Pulses : {self.counter.count}/3", True, (0,0,0)), (10, y)); y += 17
        pulse_col = (160, 0, 200) if self.third_pulse else (0, 0, 0)
        surface.blit(font.render(f"Output : {'*** FIRE ***' if self.third_pulse else 'waiting'}", True, pulse_col), (10, y)); y += 22

        surface.blit(font_bold.render("── Memory ──", True, (30,30,30)), (10, y)); y += 18
        if self.memory.active:
            surface.blit(font.render(f"Stored : {self.memory.name}", True, (160, 110, 0)), (10, y)); y += 17
        else:
            surface.blit(font.render("Stored : none", True, (130, 130, 130)), (10, y)); y += 17

        # Memory bar
        bar_w = 190
        pygame.draw.rect(surface, (0,0,0), (10, y, bar_w, 12), 2)
        fill = int(bar_w * self.memory.strength / self.memory.max_strength)
        pygame.draw.rect(surface, (255, 200, 0), (11, y+1, fill, 10))
        surface.blit(font.render(f"{self.memory.strength:.0f}%", True, (0,0,0)), (10+bar_w+6, y-1)); y += 22

        surface.blit(font.render(f"L={self.left_motor:.2f}  R={self.right_motor:.2f}", True, (0,0,0)), (10, y)); y += 17

        # Memory target ring
        if self.memory.pos:
            pygame.draw.circle(surface, (220, 150, 0), (int(self.memory.pos[0]), int(self.memory.pos[1])), 28, 2)


# ============================================================
# Draw Figure 9 diagram on right panel
# ============================================================
def draw_figure9_diagram(surface, or_active, and_active, not_active, x0, y0):
    def circle(cx, cy, r, active, label, thresh):
        col = (0, 200, 0) if active else (220, 220, 220)
        pygame.draw.circle(surface, col, (cx, cy), r)
        pygame.draw.circle(surface, (0,0,0), (cx, cy), r, 2)
        t = font.render(str(thresh), True, (0,0,0))
        surface.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))
        if label:
            l = font.render(label, True, (0,0,0))
            surface.blit(l, (cx - l.get_width()//2 - 18, cy - 6))

    def line(ax, ay, bx, by, col=(80,80,80)):
        pygame.draw.line(surface, col, (ax, ay), (bx, by), 2)

    def inhibit_line(ax, ay, bx, by):
        pygame.draw.line(surface, (200,0,0), (ax,ay), (bx,by), 2)
        pygame.draw.rect(surface, (200,0,0), (bx-4, by-4, 8, 8))

    r = 18
    surface.blit(font_bold.render("Figure 9", True, (0,0,0)), (x0, y0)); y0 += 20

    # OR gate: A,B → C (thresh=1)
    ax, ay = x0+20, y0+20
    bx, by = x0+20, y0+55
    cx, cy = x0+80, y0+38

    line(ax, ay, cx-r, cy)
    line(bx, by, cx-r, cy)
    circle(ax, ay, r, True, "A", "")
    circle(bx, by, r, True, "B", "")
    circle(cx, cy, r, or_active, "C", 1)
    surface.blit(font.render("OR", True, (0,100,0)), (cx+r+4, cy-6))
    y0 += 90

    # AND gate: D,E,F → G (thresh=2)
    dx, dy = x0+20, y0+10
    ex, ey = x0+20, y0+40
    fx, fy = x0+20, y0+70
    gx, gy = x0+80, y0+40

    line(dx, dy, gx-r, gy)
    line(ex, ey, gx-r, gy)
    line(fx, fy, gx-r, gy)
    circle(dx, dy, r, True, "D", "")
    circle(ex, ey, r, True, "E", "")
    circle(fx, fy, r, True, "F", "")
    circle(gx, gy, r, and_active, "G", 2)
    surface.blit(font.render("AND", True, (0,0,160)), (gx+r+4, gy-6))
    y0 += 110

    # NOT gate: H → I (thresh=-1 / inhibitory)
    hx, hy = x0+20, y0+20
    ix, iy = x0+80, y0+20

    inhibit_line(hx+r, hy, ix-r, iy)
    circle(hx, hy, r, True, "H", "")
    circle(ix, iy, r, not_active, "I", -1)
    surface.blit(font.render("NOT", True, (160,0,0)), (ix+r+4, iy-6))


# ============================================================
# Draw Figure 10b counter diagram on right panel
# ============================================================
def draw_counter_diagram(surface, counter, x0, y0):
    r = 18

    def circle(cx, cy, active, thresh):
        col = (0, 200, 0) if active else (220, 220, 220)
        pygame.draw.circle(surface, col, (cx, cy), r)
        pygame.draw.circle(surface, (0,0,0), (cx, cy), r, 2)
        t = font.render(str(thresh), True, (0,0,0))
        surface.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))

    surface.blit(font_bold.render("Figure 10b", True, (0,0,0)), (x0, y0)); y0 += 20

    td1x, td1y = x0+25,  y0+50
    td2x, td2y = x0+80,  y0+50
    td3x, td3y = x0+135, y0+50

    # Input arrow
    pygame.draw.line(surface, (80,80,80), (x0, td1y), (td1x-r, td1y), 2)
    surface.blit(font.render("in", True, (0,0,0)), (x0-2, td1y-14))

    # Chain
    pygame.draw.line(surface, (80,80,80), (td1x+r, td1y), (td2x-r, td2y), 2)
    pygame.draw.line(surface, (80,80,80), (td2x+r, td2y), (td3x-r, td3y), 2)

    # Feedback arc: TD3 back to TD2
    fb_pts = [
        (td3x, td3y-r),
        (td3x, y0+10),
        (td2x, y0+10),
        (td2x, td2y-r),
    ]
    pygame.draw.lines(surface, (0,80,200), False, fb_pts, 2)
    surface.blit(font.render("fb", True, (0,80,200)), (td2x+8, y0+2))

    # Output arrow
    pygame.draw.line(surface, (80,80,80), (td3x+r, td3y), (td3x+r+25, td3y), 2)
    surface.blit(font.render("out", True, (0,0,0)), (td3x+r+4, td3y-14))

    # Circles
    circle(td1x, td1y, counter.td1.active, 1)
    circle(td2x, td2y, counter.td2.active, 2)
    circle(td3x, td3y, counter.td3.active, 2)

    # State indicator
    y0 += 90
    surface.blit(font.render(f"count = {counter.count}/3", True, (0,0,0)), (x0, y0))
    if counter.output:
        surface.blit(font_bold.render("OUTPUT!", True, (160,0,200)), (x0+90, y0))


# ============================================================
# SETUP
# ============================================================
sources = [
    Stimulus(260, 260, (255, 220, 0), "Y1"),
    Stimulus(460, 400, (255, 180, 0), "Y2"),
]
vehicle = Vehicle(120, 120, radius=20)

PANEL_X = 540   # right panel x start
SEP_X   = 530   # divider

running = True
dragging = None

while running:
    screen.fill((245, 245, 245))

    # Divider
    pygame.draw.line(screen, (180,180,180), (SEP_X, 0), (SEP_X, HEIGHT), 1)
    screen.blit(font_bold.render("Simulation", True, (0,0,0)), (210, HEIGHT-22))
    screen.blit(font_bold.render("Diagrams", True, (0,0,0)),   (PANEL_X+40, HEIGHT-22))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            dragging = None
            for s in sources:
                dx = event.pos[0] - s.x
                dy = event.pos[1] - s.y
                if math.hypot(dx, dy) < s.radius + 10:
                    dragging = s
        if event.type == pygame.MOUSEMOTION and dragging:
            dragging.move_to(event.pos)
        if event.type == pygame.MOUSEBUTTONUP:
            dragging = None

    # Draw simulation area sources & vehicle
    for s in sources:
        s.draw(screen)

    vehicle.update(sources)
    vehicle.draw(screen)

    # Draw Figure 9 and Figure 10b diagrams in right panel
    draw_figure9_diagram(screen,
                         vehicle._or_active,
                         vehicle._and_active,
                         vehicle._not_active,
                         x0=PANEL_X, y0=10)

    draw_counter_diagram(screen, vehicle.counter, x0=PANEL_X, y0=370)

    pygame.display.flip()
    clock.tick(fps)

pygame.quit()
