import pygame
import math

pygame.init()

WIDTH, HEIGHT = 1100, 680
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Braitenberg Vehicle 5 — Logic")

clock = pygame.time.Clock()
fps = 60

font_title = pygame.font.SysFont("consolas", 24, bold=True)
font_head = pygame.font.SysFont("consolas", 14, bold=True)
font_body = pygame.font.SysFont("consolas", 13)

BG = (15, 20, 35)
PANEL_BG = (25, 32, 52)
BORDER = (50, 70, 110)
WHITE = (230, 235, 245)
GREY = (120, 130, 150)
GREEN = (60, 210, 100)
RED = (220, 60, 60)
BLUE = (60, 130, 220)
YELLOW = (255, 210, 50)
PURPLE = (180, 80, 220)
ORANGE = (255, 150, 40)
DGREEN = (20, 60, 30)
DRED = (70, 20, 20)


# ════════════════════════════════════════════════════════════
# THRESHOLD DEVICE
#
# Basic electrical element:
#   - Has output  if  input  >= threshold   (fires)
#   - No output   if  input  <  threshold   (silent)
#   - Inhibition subtracts from input before comparison
# ════════════════════════════════════════════════════════════
class ThresholdDevice:
    def __init__(self, threshold):
        self.threshold = threshold
        self.output = 0  # 0 = no signal,  1 = signal

    def update(self, input_signal, inhibition=0):
        net = input_signal - inhibition
        self.output = 1 if net >= self.threshold else 0
        return self.output


# ════════════════════════════════════════════════════════════
# COUNTER  (built from threshold devices)
#
# Uses previous-state / next-state logic:
#
#   pulse_input  +  previous_state  →  next_state
#
# Each ThresholdDevice holds one count state (threshold = 2
# means it needs BOTH the pulse AND the carry from the
# previous state to advance).
#
# Counts:  0 → 1 → 2 → 3  then STOPS and fires "done".
# ════════════════════════════════════════════════════════════
class Counter:
    MAX = 4 # counts up to this number then stops

    def __init__(self):
        self.steps = [
            ThresholdDevice(1),  # step 1
            ThresholdDevice(2),  # step 2
            ThresholdDevice(2),  # step 3
            ThresholdDevice(2),  # step 4
        ]
        self.count = 0
        self.done = False
        self._prev_pulse = 0

    def update(self, pulse):
        rising = (pulse == 1) and (self._prev_pulse == 0)
        self._prev_pulse = pulse

        if self.done:
            return

        if rising:
            carry = 1
            for i, device in enumerate(self.steps):
                carry = device.update(carry + (1 if self.count > i else 0))

            self.count += 1
            if self.count >= self.MAX:
                self.done = True       #by making those two lines comment, the counter will not stop counting will count to infinity

    def reset(self):
        self.count = 0
        self.done = False
        self._prev_pulse = 0
        for d in self.steps:
            d.output = 0


# ════════════════════════════════════════════════════════════
# MEMORY  (reciprocal threshold devices — Chapter 5)
#
# Two threshold devices activate each other once a target is
# stored. They keep each other active (latched) until the
# strength decays to zero and the latch opens.
# ════════════════════════════════════════════════════════════
class Memory:
    def __init__(self, decay=0.15, capacity=100):
        self.active = False
        self.strength = 0.0
        self.capacity = capacity
        self.decay = decay
        self.pos = None  # last known position of target
        self.name = None  # name of remembered target

    def store(self, name, pos):
        self.active = True
        self.strength = self.capacity
        self.name = name
        self.pos = pos

    def update(self):
        if self.strength > 0:
            self.strength -= self.decay
        if self.strength <= 0:
            self.strength = 0.0
            self.active = False
            self.name = None
            self.pos = None

    def reset(self):
        self.active = False
        self.strength = 0.0
        self.name = None
        self.pos = None


# ════════════════════════════════════════════════════════════
# SENSOR
# ════════════════════════════════════════════════════════════
class Sensor:
    def __init__(self, detect_threshold=0.5):
        self.threshold = detect_threshold
        self.intensity = 0.0
        self.signal = 0

    def update(self, px, py, source_x, source_y):
        dx = source_x - px
        dy = source_y - py
        d2 = max(dx * dx + dy * dy, 100)
        self.intensity = min(15000 / d2, 5.0)
        self.signal = 1 if self.intensity >= self.threshold else 0
        return self.signal


# ════════════════════════════════════════════════════════════
# STIMULUS  (named light source)
# ════════════════════════════════════════════════════════════
class Stimulus:
    def __init__(self, x, y, color, name, radius=22):
        self.x, self.y = x, y
        self.color = color
        self.name = name
        self.radius = radius

    def pos(self):
        return (self.x, self.y)

    def move_to(self, p):
        self.x, self.y = p

    def draw(self, surface):
        glow = tuple(min(255, c + 50) for c in self.color)
        pygame.draw.circle(
            surface, glow, (int(self.x), int(self.y)), self.radius + 7, 3
        )
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius, 2)
        lbl = font_head.render(self.name, True, BG)
        surface.blit(
            lbl,
            (int(self.x) - lbl.get_width() // 2, int(self.y) - lbl.get_height() // 2),
        )
        tag = font_body.render("(drag)", True, GREY)
        surface.blit(
            tag, (int(self.x) - tag.get_width() // 2, int(self.y) + self.radius + 5)
        )


# ════════════════════════════════════════════════════════════
# VEHICLE FIVE
# ════════════════════════════════════════════════════════════
class VehicleFive:
    def __init__(self, x, y, radius=20, heading=0):
        self.x = x
        self.y = y
        self.radius = radius
        self.heading = heading

        sensor_angle = math.radians(30)
        sensor_dist = self.radius

        self._loff = (
            math.cos(+sensor_angle) * sensor_dist,
            math.sin(+sensor_angle) * sensor_dist,
        )
        self._roff = (
            math.cos(-sensor_angle) * sensor_dist,
            math.sin(-sensor_angle) * sensor_dist,
        )

        # One pair of sensors per good source + one pair for danger
        self.sensors_good = [Sensor(), Sensor(), Sensor(), Sensor()]  # L per Y1..Y4
        self.sensors_good_r = [Sensor(), Sensor(), Sensor(), Sensor()]  # R per Y1..Y4
        self.sensor_L_danger = Sensor()
        self.sensor_R_danger = Sensor()

        self.td_see_good = ThresholdDevice(1)
        self.td_see_danger = ThresholdDevice(1)
        self.td_both = ThresholdDevice(2)
        self.td_inhibit = ThresholdDevice(
            1
        )  # inhibited by danger → ngadalëson approach

        self.counter = Counter()
        self.memory = Memory()

        self.left_motor = 0.0
        self.right_motor = 0.0

        self.mode = "SEARCH"
        self.trail = []
        self.frozen = False

        self.out_good = 0
        self.out_danger = 0
        self.out_both = 0
        self.out_inhibit = 0

        # input values për panel vizual
        self.in_see_good = 0
        self.in_see_danger = 0
        self.in_both = 0
        self.in_inhibit = 0
        self.inh_inhibit = 0
        self.best_good_li = 0.0
        self.best_good_ri = 0.0
        self.best_src_name = None
        self.best_src_pos = None

    def _sensor_world_pos(self):
        ch = math.cos(self.heading)
        sh = math.sin(self.heading)
        lox, loy = self._loff
        rox, roy = self._roff
        lx = self.x + ch * lox - sh * loy
        ly = self.y + sh * lox + ch * loy
        rx = self.x + ch * rox - sh * roy
        ry = self.y + sh * rox + ch * roy
        return (lx, ly), (rx, ry)

    def update(self, good_srcs, danger_src, sim_w):
        lp, rp = self._sensor_world_pos()

        # Read sensors for each good source, keep best (strongest)
        best_li, best_ri, any_good_sig, sum_good_sig = 0.0, 0.0, 0, 0
        best_src_name, best_src_pos = None, None
        for i, src in enumerate(good_srcs):
            li = self.sensors_good[i].update(lp[0], lp[1], src.x, src.y)
            ri = self.sensors_good_r[i].update(rp[0], rp[1], src.x, src.y)
            combined = self.sensors_good[i].intensity + self.sensors_good_r[i].intensity
            if combined > best_li + best_ri:
                best_li = self.sensors_good[i].intensity
                best_ri = self.sensors_good_r[i].intensity
                best_src_name = src.name
                best_src_pos = src.pos()
            if li or ri:
                any_good_sig = 1
                sum_good_sig += 1
        self.best_good_li = best_li
        self.best_good_ri = best_ri
        self.best_src_name = best_src_name
        self.best_src_pos = best_src_pos

        sig_L_danger = self.sensor_L_danger.update(
            lp[0], lp[1], danger_src.x, danger_src.y
        )
        sig_R_danger = self.sensor_R_danger.update(
            rp[0], rp[1], danger_src.x, danger_src.y
        )

        danger_sig = max(sig_L_danger, sig_R_danger)
        out_good = self.td_see_good.update(any_good_sig)
        out_danger = self.td_see_danger.update(danger_sig)
        out_both = self.td_both.update(out_good + out_danger)
        out_inhibit = self.td_inhibit.update(out_good, inhibition=out_danger)

        self.out_good = out_good
        self.out_danger = out_danger
        self.out_both = out_both
        self.out_inhibit = out_inhibit

        # ruaj inputet për panel
        self.in_see_good = any_good_sig
        self.in_see_danger = danger_sig
        self.in_both = out_good + out_danger
        self.in_inhibit = out_good
        self.inh_inhibit = out_danger

        # Pa freeze — inhibitori trajton të kuqen
        self.frozen = False

        self.counter.update(out_good) #here u can change which ball will it count

        if self.counter.done:
            # Counted all yellow lights → stop completely
            self.mode = "COUNTER DONE — stopped"
            self.left_motor = 0.0
            self.right_motor = 0.0

        elif out_good:
            # out_inhibit=0 → ihibitory danger → slow down
            # out_inhibit=1 → with danger → normal speed
            speed = 0.35 if not out_inhibit else 1.0
            if not out_inhibit:
                self.mode = f"INHIBITED [{self.counter.count}/{Counter.MAX}]"
            else:
                self.mode = f"APPROACH  [{self.counter.count}/{Counter.MAX}]"
            # Crossed wiring: right sensor → left motor = attraction
            self.left_motor = speed * (1.0 + best_ri * 1.8)
            self.right_motor = speed * (1.0 + best_li * 1.8)
            # Store this target in memory
            if best_src_name:
                self.memory.store(best_src_name, best_src_pos)

        elif self.memory.active:
            # Yellow lost from sight — navigate toward remembered position
            mx, my = self.memory.pos
            dx, dy = mx - self.x, my - self.y
            target_angle = math.atan2(dy, dx)
            angle_diff = (target_angle - self.heading + math.pi) % (
                2 * math.pi
            ) - math.pi
            if angle_diff > 0:
                self.left_motor = 1.0
                self.right_motor = 1.4
            else:
                self.left_motor = 1.4
                self.right_motor = 1.0
            self.mode = f"MEMORY → {self.memory.name}  ({int(self.memory.strength)}%)"

        else:
            self.mode = "SEARCH"
            self.left_motor = 1.0
            self.right_motor = 1.35

        self.memory.update()

        fwd = (self.left_motor + self.right_motor) / 2
        turn = (self.right_motor - self.left_motor) * 0.03
        self.heading += turn
        self.x = (self.x + fwd * math.cos(self.heading)) % sim_w
        self.y = (self.y + fwd * math.sin(self.heading)) % HEIGHT

        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > 350:
            self.trail.pop(0)

    def draw(self, surface):
        if len(self.trail) > 2:
            for i in range(1, len(self.trail)):
                a = int(160 * i / len(self.trail))
                col = (a // 4, a // 3, a)
                pygame.draw.line(surface, col, self.trail[i - 1], self.trail[i], 1)

        if self.counter.done:
            body_col = PURPLE
        elif self.memory.active:
            body_col = ORANGE
        elif "INHIBITED" in self.mode:
            body_col = YELLOW
        else:
            body_col = BLUE
        pygame.draw.circle(surface, body_col, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius, 2)

        lp, rp = self._sensor_world_pos()
        pygame.draw.circle(surface, (255, 80, 80), (int(lp[0]), int(lp[1])), 5)
        pygame.draw.circle(surface, (255, 80, 80), (int(rp[0]), int(rp[1])), 5)

        nx = self.x + math.cos(self.heading) * self.radius
        ny = self.y + math.sin(self.heading) * self.radius
        pygame.draw.line(
            surface, WHITE, (int(self.x), int(self.y)), (int(nx), int(ny)), 2
        )


# ════════════════════════════════════════════════════════════
# UI HELPERS
# ════════════════════════════════════════════════════════════
def panel(surface, x, y, w, h, title=None):
    pygame.draw.rect(surface, PANEL_BG, (x, y, w, h), border_radius=8)
    pygame.draw.rect(surface, BORDER, (x, y, w, h), 2, border_radius=8)
    iy = y + 10
    if title:
        surface.blit(font_head.render(title, True, GREY), (x + 12, iy))
        iy += 22
    return iy


def signal_dot(surface, x, y, on):
    col = GREEN if on else (50, 55, 75)
    pygame.draw.circle(surface, col, (x, y), 8)
    pygame.draw.circle(surface, WHITE, (x, y), 8, 1)


def bar(surface, x, y, w, h, val, maxv, col):
    pygame.draw.rect(surface, (35, 40, 60), (x, y, w, h), border_radius=4)
    if maxv:
        pygame.draw.rect(surface, col, (x, y, int(w * val / maxv), h), border_radius=4)
    pygame.draw.rect(surface, BORDER, (x, y, w, h), 1, border_radius=4)


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
SIM_W = 700
PANEL_X = SIM_W + 16
PANEL_W = WIDTH - PANEL_X - 16

good_srcs = [
    Stimulus(200, 180, (255, 215, 0), "Y1"),
    Stimulus(500, 150, (255, 200, 50), "Y2"),
    Stimulus(350, 460, (255, 180, 0), "Y3"),
    Stimulus(130, 430, (255, 230, 80), "Y4"),
]
danger_src = Stimulus(560, 370, (210, 40, 40), "RED")

Counter.MAX = len(good_srcs)  # ndrysho len(good_srcs) me numrin qe deshiron p.sh: Counter.MAX = 2

vehicle = VehicleFive(100, 300)
running = True
dragging = None

while running:
    screen.fill(BG)
    pygame.draw.rect(screen, (20, 26, 42), (0, 0, SIM_W, HEIGHT))
    pygame.draw.rect(screen, BORDER, (0, 0, SIM_W, HEIGHT), 1)

    screen.blit(
        font_title.render("Braitenberg  Vehicle 5 — Logic", True, WHITE), (12, 10)
    )
    screen.blit(
        font_body.render(
            "Threshold devices · Counter (prev/next state) · Fear · Detection",
            True,
            GREY,
        ),
        (12, 42),
    )
    pygame.draw.line(screen, BORDER, (12, 62), (SIM_W - 12, 62), 1)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            vehicle.counter.reset()
            vehicle.memory.reset()
        if event.type == pygame.MOUSEBUTTONDOWN:
            dragging = None
            for s in good_srcs + [danger_src]:
                if math.hypot(event.pos[0] - s.x, event.pos[1] - s.y) < s.radius + 10:
                    dragging = s
        if event.type == pygame.MOUSEMOTION and dragging:
            dragging.move_to(event.pos)
        if event.type == pygame.MOUSEBUTTONUP:
            dragging = None

    for s in good_srcs:
        s.draw(screen)
    danger_src.draw(screen)
    vehicle.update(good_srcs, danger_src, SIM_W)
    vehicle.draw(screen)
    screen.blit(font_body.render("Press R to reset", True, GREY), (12, HEIGHT - 24))



    # ── RIGHT PANEL ───────────────────────────────────────
    # Mode       y=4   h=40  → ends  44
    # Threshold  y=47  h=190 → ends 237
    # Counter    y=240 h=96  → ends 336
    # Sensors    y=339 h=106 → ends 445
    # Motors     y=448 h=74  → ends 522
    # Memory     y=525 h=58  → ends 583
    # Legend     y=586 h=60  → ends 646

    # Mode
    iy = panel(screen, PANEL_X, 4, PANEL_W, 40)
    mc = (
        PURPLE
        if "DONE" in vehicle.mode
        else (
            GREEN
            if "APPROACH" in vehicle.mode
            else (
                ORANGE
                if "MEMORY" in vehicle.mode
                else YELLOW if "INHIBITED" in vehicle.mode else GREY
            )
        )
    )
    screen.blit(font_body.render("MODE:", True, GREY), (PANEL_X + 12, iy))
    screen.blit(font_head.render(vehicle.mode, True, mc), (PANEL_X + 12, iy + 15))

    # Threshold Devices  (header=32, 4×38=152, pad=6 → h=190)
    iy = panel(screen, PANEL_X, 47, PANEL_W, 190, "Threshold Devices")

    def td_row(y, name, inp, thresh, out, inhibition=None):
        # emri + output dot
        signal_dot(screen, PANEL_X + 14, y + 7, out)
        col = GREEN if out else WHITE
        screen.blit(font_body.render(name, True, col), (PANEL_X + 28, y))
        y += 16
        # rreshti i vlerave
        x = PANEL_X + 12
        # in
        screen.blit(font_body.render("in:", True, GREY), (x, y))
        x += 26
        ic = GREEN if inp >= thresh else (180, 60, 60)
        screen.blit(font_head.render(str(inp), True, ic), (x, y))
        x += 18
        # inhibicion (nëse ka)
        if inhibition is not None:
            screen.blit(font_body.render(" -inh:", True, GREY), (x, y))
            x += 44
            screen.blit(
                font_head.render(str(inhibition), True, RED if inhibition else GREY),
                (x, y),
            )
            x += 18
            net = inp - inhibition
            screen.blit(font_body.render(f" =net:{net}", True, GREY), (x, y))
            x += 58
        # threshold
        screen.blit(font_body.render(" t:", True, GREY), (x, y))
        x += 24
        screen.blit(font_head.render(str(thresh), True, WHITE), (x, y))
        x += 18
        # output
        arrow_col = GREEN if out else (100, 100, 120)
        screen.blit(font_body.render(" →", True, arrow_col), (x, y))
        x += 20
        screen.blit(
            font_head.render(str(out), True, GREEN if out else (180, 60, 60)), (x, y)
        )

    td_row(iy, "td_see_good   (sees yellow?)", vehicle.in_see_good, 1, vehicle.out_good)
    td_row(
        iy + 38,
        "td_see_danger (sees RED?)",
        vehicle.in_see_danger,
        1,
        vehicle.out_danger,
    )
    td_row(iy + 76, "td_both       (sees both?)", vehicle.in_both, 2, vehicle.out_both)
    td_row(
        iy + 114,
        "td_inhibit    (RED inhibon?)",
        vehicle.in_inhibit,
        1,
        vehicle.out_inhibit,
        inhibition=vehicle.inh_inhibit,
    )

    # Counter
    iy = panel(screen, PANEL_X, 240, PANEL_W, 96, f"Counter  MAX={Counter.MAX}")
    screen.blit(
        font_body.render("pulse + prev → next state", True, GREY), (PANEL_X + 12, iy)
    )
    iy += 18
    spacing = min(54, (PANEL_W - 24) // Counter.MAX)
    for i in range(Counter.MAX):
        filled = i < vehicle.counter.count
        col = YELLOW if filled else (45, 50, 72)
        cx = PANEL_X + 16 + i * spacing + spacing // 2
        pygame.draw.circle(screen, col, (cx, iy + 12), 11)
        pygame.draw.circle(screen, WHITE, (cx, iy + 12), 11, 2)
        t = font_body.render(str(i + 1), True, BG if filled else GREY)
        screen.blit(t, (cx - t.get_width() // 2, iy + 5))
    iy += 32
    count_col = PURPLE if vehicle.counter.done else WHITE
    status = (
        "DONE — stopped!"
        if vehicle.counter.done
        else f"count: {vehicle.counter.count} / {Counter.MAX}   (R=reset)"
    )
    screen.blit(font_body.render(status, True, count_col), (PANEL_X + 12, iy))

    # Sensors
    iy = panel(screen, PANEL_X, 339, PANEL_W, 106, "Sensor Signals")
    best_li = max(s.intensity for s in vehicle.sensors_good)
    best_ri = max(s.intensity for s in vehicle.sensors_good_r)
    for name, intens, sig, bcol in [
        ("L-yellow", best_li, 1 if best_li >= 0.5 else 0, YELLOW),
        ("R-yellow", best_ri, 1 if best_ri >= 0.5 else 0, YELLOW),
        (
            "L-danger",
            vehicle.sensor_L_danger.intensity,
            vehicle.sensor_L_danger.signal,
            RED,
        ),
        (
            "R-danger",
            vehicle.sensor_R_danger.intensity,
            vehicle.sensor_R_danger.signal,
            RED,
        ),
    ]:
        signal_dot(screen, PANEL_X + 14, iy + 7, sig)
        screen.blit(font_body.render(name, True, WHITE), (PANEL_X + 30, iy))
        bar(screen, PANEL_X + 112, iy + 1, PANEL_W - 124, 11, intens, 5, bcol)
        iy += 18

    # Motors
    iy = panel(screen, PANEL_X, 448, PANEL_W, 74, "Motors")
    screen.blit(font_body.render("Left :", True, GREY), (PANEL_X + 12, iy + 3))
    bar(
        screen,
        PANEL_X + 68,
        iy + 3,
        PANEL_W - 84,
        13,
        min(max(vehicle.left_motor, 0), 12),
        12,
        BLUE,
    )
    iy += 22
    screen.blit(font_body.render("Right:", True, GREY), (PANEL_X + 12, iy + 3))
    bar(
        screen,
        PANEL_X + 68,
        iy + 3,
        PANEL_W - 84,
        13,
        min(max(vehicle.right_motor, 0), 12),
        12,
        BLUE,
    )

    # Memory
    iy = panel(screen, PANEL_X, 525, PANEL_W, 58, "Memory  (reciprocal devices)")
    if vehicle.memory.active:
        screen.blit(
            font_head.render(f"Stored: {vehicle.memory.name}", True, ORANGE),
            (PANEL_X + 12, iy),
        )
        iy += 20
        screen.blit(font_body.render("str:", True, GREY), (PANEL_X + 12, iy + 2))
        bar(
            screen,
            PANEL_X + 50,
            iy + 2,
            PANEL_W - 62,
            13,
            vehicle.memory.strength,
            vehicle.memory.capacity,
            ORANGE,
        )
    else:
        screen.blit(
            font_body.render("— no memory stored —", True, GREY), (PANEL_X + 12, iy)
        )

    # Legend
    iy = panel(screen, PANEL_X, 586, PANEL_W, 60)
    for col, txt in [
        (BLUE, "search / approach"),
        (YELLOW, "INHIBITED — RED zbret sinjalin"),
        (ORANGE, "memory mode (navigating)"),
        (PURPLE, "DONE — counted all lights"),
    ]:
        pygame.draw.circle(screen, col, (PANEL_X + 14, iy + 6), 5)
        screen.blit(font_body.render(txt, True, WHITE), (PANEL_X + 26, iy))
        iy += 13

    pygame.display.flip()
    clock.tick(fps)

pygame.quit()
