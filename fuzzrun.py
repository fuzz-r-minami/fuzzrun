import json
import os
import sys
import time
import pygame
import numpy

SCR_W = 160
SCR_H = 128
CHIP_W = 16
CHIP_H = 16
MAP_W = int(SCR_W / CHIP_W)
MAP_H = int(SCR_H / CHIP_H)
XY = numpy.indices((SCR_W, SCR_H)).swapaxes(0, 2).swapaxes(0, 1)
UV = XY / (SCR_W, SCR_H) - 0.5

# initialize
pygame.display.init()
pygame.mouse.set_visible(False)
pygame.mixer.pre_init(44100, 16, 2, 1024 * 4)
pygame.mixer.init()
pygame.mixer.set_num_channels(8)

g_display_info = pygame.display.Info()
g_srf_display = pygame.display.set_mode((SCR_W * 4, SCR_H * 4), pygame.FULLSCREEN if os.name == 'posix' else 0)
g_srf_screen = pygame.Surface((SCR_W, SCR_H))
g_img_char = pygame.image.load('char.png')
g_img_bg = pygame.image.load('stage.png')
g_img_title = pygame.image.load('title.png')
g_img_over = pygame.image.load('over.png')
g_snd_ping = pygame.mixer.Sound('ping.wav')
g_snd_pong = pygame.mixer.Sound('pong.wav')
g_time = 0.0
g_bgm_volume = 0.0 if len(sys.argv) > 1 and sys.argv[1] == '--nobgm' else 1.0

def col_ray_aabb(in_ray_pos, in_ray_vel, in_aabb_min, in_aabb_max):
    if in_ray_vel.length_squared() == 0:
        return False, 0.0

    unit = pygame.math.Vector2((1.0 / in_ray_vel.x) if in_ray_vel.x != 0 else float('inf'),
                               (1.0 / in_ray_vel.y) if in_ray_vel.y != 0 else float('inf'))
    t1 = (in_aabb_min.x - in_ray_pos.x) * unit.x
    t2 = (in_aabb_max.x - in_ray_pos.x) * unit.x
    t3 = (in_aabb_min.y - in_ray_pos.y) * unit.y
    t4 = (in_aabb_max.y - in_ray_pos.y) * unit.y
    tmin = max(min(t1, t2), min(t3, t4))
    tmax = min(max(t1, t2), max(t3, t4))

    if tmax < 0.0:
        return False, tmax
    elif tmin > tmax:
        return False, tmax
    else:
        return True, tmin

def col_aabb_aabb(in_a_min, in_a_max, in_a_vel, in_b_min, in_b_max, in_b_vel):
    p = (in_a_max + in_a_min) * 0.5
    r = (in_a_max - in_a_min) * 0.5
    aabb_min = in_b_min - r
    aabb_max = in_b_max + r
    v = in_a_vel - in_b_vel

    res, t = col_ray_aabb(p, v, aabb_min, aabb_max)
    if res == False:
        return False, t, pygame.math.Vector2()

    pos = p + v * t
    n = pygame.math.Vector2(0, 0)
    if pos.x <= aabb_min.x:
        n.x = -1.0
    elif pos.x >= aabb_max.x:
        n.x = 1.0
    if pos.y <= aabb_min.y:
        n.y = -1.0
    elif pos.y >= aabb_max.y:
        n.y = 1.0

    return True, t, n


class Camera:
    def __init__(self):
        self.pos = pygame.math.Vector2(0, 0)

    def update(self):
        self.pos = g_player.pos + pygame.math.Vector2(Player.WIDTH / 2, Player.HEIGHT / 2) + pygame.math.Vector2(64, 0) - pygame.math.Vector2(SCR_W / 2, SCR_H / 2)
        self.pos.x = min(max(0, self.pos.x), (len(g_stage.data['chips']) - 1) * CHIP_W * MAP_W)
        self.pos.y = 0
        self.pos.x = int(self.pos.x)

    def relpos(self, pos):
        relpos = pos - self.pos
        relpos.x = int(relpos.x)
        relpos.y = int(relpos.y)
        return pos - self.pos


class State:
    def __init__(self, state=0):
        self._state = state
        self._time = time.time()

    def change(self, state):
        self._state = state
        self._time = time.time()

    def get_state(self):
        return self._state

    def get_time(self):
        return time.time() - self._time


class Stage:
    WATER_FLOOR = [
        (0, (1120, 128, 16, 8, 0, 8)),
        (200, (1120, 136, 16, 8, 0, 8)),
        (400, (1120, 144, 16, 8, 0, 8)),
        (600, (1120, 152, 16, 8, 0, 8)),
        (800, (1120, 152, 16, 8, 0, 8)),
    ]
    ANIMATION_OBJECTS = {
        2: [
            (  0, (1136, 128, 24, 48, 0, 0)),
            (100, (1160, 128, 24, 48, 0, 0)),
            (200, (1184, 128, 24, 48, 0, 0)),
            (300, (1160, 128, 24, 48, 0, 0)),
            (400, (1136, 128, 24, 48, 0, 0)),
        ],
        3: [
            (0, (1120, 192, 16, 16, 0, 0)),
            (1800, (1120, 208, 16, 16, 0, 0)),
            (2400, (1120, 192, 16, 16, 0, 0)),
            (2700, (1120, 176, 16, 16, 0, 0)),
            (2800, (1120, 192, 16, 16, 0, 0)),
            (2900, (1120, 176, 16, 16, 0, 0)),
            (3000, (1120, 192, 16, 16, 0, 0)),
        ],
        4: [
            (0, (1136, 176, 24, 16, 0, -8)),
            (200, (1136, 192, 24, 16, 0, -8)),
            (400, (1136, 176, 24, 16, 0, -8)),
            (600, (1136, 208, 24, 16, 0, -8)),
            (800, (1136, 176, 24, 16, 0, -8)),
        ],
        5: [
            (0, (1160, 176, 24, 16, 4, 0)),
            (100, (1160, 192, 24, 16, 4, 0)),
            (200, (1160, 176, 24, 16, 4, 0)),
            (400, (1160, 192, 24, 16, 4, 0)),
            (500, (1160, 176, 24, 16, 4, 0)),
            (600, (1160, 192, 24, 16, 4, 0)),
            (700, (1160, 176, 24, 16, 4, 0)),
            (800, (1160, 192, 24, 16, 4, 0)),
            (900, (1160, 208, 24, 16, 4, 0)),
            (1900, (1160, 208, 24, 16, 4, 0)),
        ],
        6: [
            (0, (1184, 176, 48, 16, 0, 0)),
            (5000, (1184, 192, 48, 16, 0, 0)),
            (5200, (1184, 208, 48, 16, 0, 0)),
            (6000, (1184, 224, 48, 16, 0, 0)),
            (11000, (1184, 240, 48, 16, 0, 0)),
            (11200, (1184, 176, 48, 16, 0, 0)),
        ],
        7: [
            (000, (1216, 176, 16, 16, 0, 0)),
            (200, (1216, 192, 16, 16, 0, 0)),
            (400, (1216, 208, 16, 16, 0, 0)),
            (800, (1216, 208, 16, 16, 0, 0)),
        ],
        8: [
            (000, (1232, 128, 24, 32, 0, 0)),
            (200, (1256, 128, 24, 32, 0, 0)),
            (400, (1232, 128, 24, 32, 0, 0)),
        ],
        9: [
            (000, (1280, 128, 40, 32, -8, 0)),
            (150, (1320, 128, 40, 32, -8, 0)),
            (300, (1360, 128, 40, 32, -8, 0)),
            (450, (1400, 128, 40, 32, -8, 0)),
            (600, (1440, 128, 40, 32, -8, 0)),
            (750, (1480, 128, 40, 32, -8, 0)),
            (900, (1520, 128, 40, 32, -8, 0)),
            (1050, (1560, 128, 40, 32, -8, 0)),
            (1200, (1560, 128, 40, 32, -8, 0)),
        ],
        10: [
            (0, (1232, 160, 24, 40, -8, -8)),
            (1000, (1256, 160, 24, 40, -8, -8)),
            (1400, (1232, 160, 24, 40, -8, -8)),
        ],
        11: [
            (0, (1232, 200, 24, 32,-8, 0)),
            (2000, (1256, 200, 24, 32,-8, 0)),
            (3000, (1232, 200, 24, 32,-8, 0)),
        ],
        12: [
            (0, (1280, 160, 24, 32, 4, 0)),
            (200, (1304, 160, 24, 32, 4, 0)),
            (400, (1328, 160, 24, 32, 4, 0)),
            (600, (1304, 160, 24, 32, 4, 0)),
            (800, (1280, 160, 24, 32, 4, 0)),
        ],
        13: [
            (000, (1352, 160, 24, 32, -8, 0)),
            (200, (1376, 160, 24, 32, -8, 0)),
            (1200, (1352, 160, 24, 32, -8, 0)),
            (1400, (1400, 160, 24, 32, -8, 0)),
            (2400, (1352, 160, 24, 32, -8, 0)),
            (2600, (1424, 160, 24, 32, -8, 0)),
            (3600, (1352, 160, 24, 32, -8, 0)),
            (3800, (1448, 160, 24, 32, -8, 0)),
            (4800, (1352, 160, 24, 32, -8, 0)),
        ],
        14: [
            (000, (1280, 192, 32, 32, 0, 0)),
            (200, (1312, 192, 32, 32, 0, 0)),
            (400, (1280, 192, 32, 32, 0, 0)),
        ],
        15: [
            (0000, (1168, 224, 16, 16, 0, 0)),
            (1000, (1168, 240, 16, 16, 0, 0)),
            (1400, (1168, 224, 16, 16, 0, 0)),
        ],
        16: [
            (0000, (1472, 160, 24, 32,-10, 0)),
            (1000, (1496, 160, 24, 32,-10, 0)),
            (2000, (1520, 160, 24, 32,-10, 0)),
            (2200, (1544, 160, 24, 32,-10, 0)),
            (2400, (1472, 160, 24, 32,-10, 0)),
        ],
        17: [
            (000, (1472, 192, 32, 32, -4, 0)),
            (200, (1440, 192, 32, 32, -4, 0)),
            (400, (1408, 192, 32, 32, -4, 0)),
            (600, (1376, 192, 32, 32, -4, 0)),
            (800, (1344, 192, 32, 32, -4, 0)),
            (1000, (1344, 224, 32, 32, -4, 0)),
            (1200, (1376, 224, 32, 32, -4, 0)),
            (1400, (1408, 224, 32, 32, -4, 0)),
            (1600, (1440, 224, 32, 32, -4, 0)),
            (1800, (1472, 224, 32, 32, -4, 0)),
            (2000, (1440, 224, 32, 32, -4, 0)),
            (2200, (1408, 224, 32, 32, -4, 0)),
            (2400, (1376, 224, 32, 32, -4, 0)),
            (2600, (1344, 224, 32, 32, -4, 0)),
            (2800, (1344, 192, 32, 32, -4, 0)),
            (3000, (1376, 192, 32, 32, -4, 0)),
            (3200, (1408, 192, 32, 32, -4, 0)),
            (3400, (1440, 192, 32, 32, -4, 0)),
            (3600, (1472, 192, 32, 32, -4, 0)),
        ],
        18: [
            (0000, (1136, 224, 16, 16, 6, 0)),
            (4000, (1136, 224, 16, 16, 6, 0)),
            (4200, (1120, 224, 16, 16, 6, 0)),
            (4400, (1136, 224, 16, 16, 6, 0)),
            (4600, (1120, 224, 16, 16, 6, 0)),
            (4800, (1136, 224, 16, 16, 6, 0)),
            (5000, (1120, 224, 16, 16, 6, 0)),
            (5200, (1136, 224, 16, 16, 6, 0)),
            (5400, (1120, 224, 16, 16, 6, 0)),
            (5600, (1136, 224, 16, 16, 6, 0)),
            (5800, (1120, 224, 16, 16, 6, 0)),
            (6000, (1152, 224, 16, 16, 6, 0)),
            (12000, (1136, 224, 16, 16, 6, 0)),
        ],
        19: [
            (0, (1136, 240, 8, 16, 0, 8)),
            (6000, (1128, 240, 8, 16, 0, 8)),
            (10000, (1128, 240, 8, 16, 0, 8)),
            (10200, (1120, 240, 8, 16, 0, 8)),
            (10400, (1128, 240, 8, 16, 0, 8)),
            (10600, (1120, 240, 8, 16, 0, 8)),
            (10800, (1128, 240, 8, 16, 0, 8)),
            (11000, (1120, 240, 8, 16, 0, 8)),
            (11200, (1128, 240, 8, 16, 0, 8)),
            (11400, (1120, 240, 8, 16, 0, 8)),
            (11600, (1128, 240, 8, 16, 0, 8)),
            (11800, (1120, 240, 8, 16, 0, 8)),
            (12000, (1136, 240, 8, 16, 0, 8)),
        ],
        20: [
            (0, (1160, 240, 8, 16, 0, 8)),
            (6000, (1152, 240, 8, 16, 0, 8)),
            (10000, (1152, 240, 8, 16, 0, 8)),
            (10200, (1144, 240, 8, 16, 0, 8)),
            (10400, (1152, 240, 8, 16, 0, 8)),
            (10600, (1144, 240, 8, 16, 0, 8)),
            (10800, (1152, 240, 8, 16, 0, 8)),
            (11000, (1144, 240, 8, 16, 0, 8)),
            (11200, (1152, 240, 8, 16, 0, 8)),
            (11400, (1144, 240, 8, 16, 0, 8)),
            (11600, (1152, 240, 8, 16, 0, 8)),
            (11800, (1144, 240, 8, 16, 0, 8)),
            (12000, (1160, 240, 8, 16, 0, 8)),
        ],
        21: [
            (0000, (1536, 192, 16, 32, 2,-2)),

            (2000, (1504, 192, 16, 32, 2,-2)),
            (2200, (1552, 192, 16, 32, 2, -2)),
            (2400, (1504, 192, 16, 32, 2, -2)),
            (2600, (1552, 192, 16, 32, 2,-2)),
            (2800, (1504, 192, 16, 32, 2, -2)),
            (3000, (1552, 192, 16, 32, 2, -2)),
            (3200, (1504, 192, 16, 32, 2,-2)),
            (3400, (1552, 192, 16, 32, 2,-2)),

            (5400, (1504, 192, 16, 32, 2,-2)),
            (5600, (1520, 192, 16, 32, 2, -2)),
            (5800, (1504, 192, 16, 32, 2,-2)),
            (6000, (1520, 192, 16, 32, 2, -2)),
            (6200, (1504, 192, 16, 32, 2, -2)),
            (6400, (1520, 192, 16, 32, 2, -2)),
            (6600, (1504, 192, 16, 32, 2, -2)),
            (6800, (1520, 192, 16, 32, 2,-2)),

            (8800, (1504, 192, 16, 32, 2, -2)),
            (9000, (1536, 192, 16, 32, 2, -2)),
            (9200, (1504, 192, 16, 32, 2, -2)),
            (9400, (1536, 192, 16, 32, 2, -2)),
            (9600, (1504, 192, 16, 32, 2, -2)),
            (9800, (1536, 192, 16, 32, 2, -2)),
            (10000, (1504, 192, 16, 32,2, -2)),
            (10200, (1536, 192, 16, 32,2, -2)),
        ],
        22: [
            (000, (1568, 160, 24, 32, 0, 0)),
            (150, (1568, 192, 24, 32, 0, 0)),
            (300, (1568, 160, 24, 32, 0, 0)),
        ],
        23: [
            (000, (1600, 128, 32, 32, 0, 0)),
            (200, (1600, 160, 32, 32, 0, 0)),
            (400, (1600, 192, 32, 32, 0, 0)),
            (600, (1600, 224, 32, 32, 0, 0)),

            (800, (1664, 128, 32, 32, 0, 0)),
            (1000, (1664, 160, 32, 32, 0, 0)),
            (1200, (1664, 192, 32, 32, 0, 0)),
            (1400, (1664, 224, 32, 32, 0, 0)),

            (1600, (1728, 128, 32, 32, 0, 0)),
            (1800, (1728, 160, 32, 32, 0, 0)),
            (2000, (1728, 192, 32, 32, 0, 0)),
            (2200, (1728, 224, 32, 32, 0, 0)),

            (2400, (1792, 128, 32, 32, 0, 0)),
            (2600, (1792, 160, 32, 32, 0, 0)),
            (2800, (1792, 192, 32, 32, 0, 0)),
            (3000, (1792, 224, 32, 32, 0, 0)),

            (3200, (1856, 128, 32, 32, 0, 0)),
            (3400, (1856, 160, 32, 32, 0, 0)),
            (3600, (1856, 192, 32, 32, 0, 0)),
            (3800, (1856, 224, 32, 32, 0, 0)),

            (4000, (1920, 128, 32, 32, 0, 0)),
            (4200, (1920, 160, 32, 32, 0, 0)),
            (4400, (1920, 192, 32, 32, 0, 0)),
            (4600, (1920, 224, 32, 32, 0, 0)),
        ],

        24: [
            (000, (1632, 128, 32, 32, 0, 0)),
            (200, (1632, 160, 32, 32, 0, 0)),
            (400, (1632, 192, 32, 32, 0, 0)),
            (600, (1632, 224, 32, 32, 0, 0)),

            (800, (1696, 128, 32, 32, 0, 0)),
            (1000, (1696, 160, 32, 32, 0, 0)),
            (1200, (1696, 192, 32, 32, 0, 0)),
            (1400, (1696, 224, 32, 32, 0, 0)),

            (1600, (1760, 128, 32, 32, 0, 0)),
            (1800, (1760, 160, 32, 32, 0, 0)),
            (2000, (1760, 192, 32, 32, 0, 0)),
            (2200, (1760, 224, 32, 32, 0, 0)),

            (2400, (1824, 128, 32, 32, 0, 0)),
            (2600, (1824, 160, 32, 32, 0, 0)),
            (2800, (1824, 192, 32, 32, 0, 0)),
            (3000, (1824, 224, 32, 32, 0, 0)),

            (3200, (1888, 128, 32, 32, 0, 0)),
            (3400, (1888, 160, 32, 32, 0, 0)),
            (3600, (1888, 192, 32, 32, 0, 0)),
            (3800, (1888, 224, 32, 32, 0, 0)),

            (4000, (1952, 128, 32, 32, 0, 0)),
            (4200, (1952, 160, 32, 32, 0, 0)),
            (4400, (1952, 192, 32, 32, 0, 0)),
            (4600, (1952, 224, 32, 32, 0, 0)),
        ],
    }

    def __init__(self):
        self.data = json.load(open('stage.json', 'r'))

    def draw(self):
        g_srf_screen.blit(g_img_bg, (0, 0), (g_camera.pos.x / 4, SCR_H, SCR_W, SCR_H))
        g_srf_screen.blit(g_img_bg, (0, 0), (g_camera.pos.x, 0, SCR_W, SCR_H))

    def draw_obj(self, overlay):
        if overlay:
            iw = int(SCR_W / CHIP_W) + 1
            iy = int(SCR_H / CHIP_H) - 1
            for ix in range(0, iw):
                fx = ix * CHIP_W + int(g_camera.pos.x / CHIP_W) * CHIP_W
                fy = iy * CHIP_H + int(g_camera.pos.y / CHIP_H) * CHIP_H
                animation = Stage.WATER_FLOOR
                loop_t = animation[-1][0]
                msec = int(g_time * 1000) % loop_t
                for i in range(0, len(animation) - 1):
                    begin_t = animation[i][0]
                    end_t = animation[i + 1][0]
                    if end_t < msec or begin_t > msec:
                        continue
                    else:
                        x, y, w, h, ofs_x, ofs_y = animation[i][1]
                        pos = g_camera.relpos((fx + ofs_x, fy + ofs_y))
                        g_srf_screen.blit(g_img_bg, pos, (x, y, w, h))
                        break

        iw = int(SCR_W / CHIP_W) + 1
        ih = int(SCR_H / CHIP_H)
        for iy in range(0, ih):
            for ix in range(-1, iw):
                fx = ix * CHIP_W + int(g_camera.pos.x / CHIP_W) * CHIP_W
                fy = iy * CHIP_H + int(g_camera.pos.y / CHIP_H) * CHIP_H
                c = self.chip(fx, fy)
                if overlay:
                    c -= 100
                    if c < 0:
                        continue
                elif c < 2 or c >= 100:
                    continue
                animation = Stage.ANIMATION_OBJECTS[c]
                loop_t = animation[-1][0]
                msec = int(g_time * 1000) % loop_t
                for i in range(0, len(animation) - 1):
                    begin_t = animation[i][0]
                    end_t = animation[i + 1][0]
                    if end_t < msec or begin_t > msec:
                        continue
                    else:
                        x, y, w, h, ofs_x, ofs_y = animation[i][1]
                        pos = g_camera.relpos((fx + ofs_x, fy + ofs_y))
                        g_srf_screen.blit(g_img_bg, pos, (x, y, w, h))
                        break

    def chip(self, x, y):
        i = int(x / SCR_W)
        if i < 0 or i >= len(self.data['chips']):
            return 0
        ix = int((x % SCR_W) / CHIP_W)
        iy = int((y % SCR_H) / CHIP_H)
        return self.map(i)[iy * MAP_W + ix]

    def map(self, i):
        return self.data['chips'][i]

class Player:
    STATE_RUN = 0
    STATE_CROUCH = 1
    STATE_JUMP = 2
    STATE_DEAD = 3
    MAX_VEL_X = 96
    HEIGHT = 32
    WIDTH = 24

    def __init__(self):
        self.reset()

    def reset(self):
        self.pos = pygame.math.Vector2(0, 0)
        self.vel = pygame.math.Vector2(0, 0)
        self.state = State(Player.STATE_RUN)

    def update(self, dt):
        if self.state.get_state() == Player.STATE_DEAD:
            self.pos.y = SCR_H - min(self.state.get_time() * (Player.HEIGHT + 4), (Player.HEIGHT + 4))
            return

        land = False

        l = int((self.pos.x - abs(self.vel.x) * dt) / 16)
        r = int((self.pos.x + Player.WIDTH + abs(self.vel.x) * dt) / 16)
        u = int((self.pos.y - abs(self.vel.y) * dt) / 16)
        d = int((self.pos.y + Player.HEIGHT + abs(self.vel.y) * dt) / 16)

        rest_t = dt
        while rest_t > 0:
            char_aabb_min = self.pos + (Player.WIDTH / 2 - 4, 0)
            char_aabb_max = self.pos + (Player.WIDTH / 2 + 4, Player.HEIGHT - 1)
            first_hit = False
            first_t = dt
            first_n = pygame.math.Vector2(0, 0)
            for y in range(u, d + 1):
                for x in range(l, r + 1):
                    c = g_stage.chip(x * 16, y * 16)
                    if c == 1:
                        chip_aabb_min = pygame.math.Vector2(x * CHIP_W, y * CHIP_H)
                        chip_aabb_max = chip_aabb_min + (CHIP_W, CHIP_H)
                        chip_aabb_vel = pygame.math.Vector2(0, 0)
                        hit, t, n = col_aabb_aabb(char_aabb_min, char_aabb_max, self.vel * rest_t, chip_aabb_min, chip_aabb_max, chip_aabb_vel)
                        if hit and t >= 0 and (t * rest_t) < first_t:
                            first_hit = True
                            first_t = t * rest_t
                            first_n = n
            if not first_hit:
                self.pos += self.vel * rest_t
                break
            else:
                rest_t -= first_t
                self.pos += self.vel * first_t + first_n * 0.0001
                self.vel -= first_n * first_n.dot(self.vel)
                if first_n.y < 0:
                    land = True

        if not land:
            if self.state.get_state() != Player.STATE_JUMP:
                self.state.change(Player.STATE_JUMP)
        else:
            if self.state.get_state() == Player.STATE_JUMP:
                self.state.change(Player.STATE_RUN)

        self.vel.y += 128 * dt

        [
            self._on_update_run,
            self._on_update_crouch,
            self._on_update_jump
        ][self.state.get_state()]()

    def draw(self):
        [
            self._on_draw_run,
            self._on_draw_crouch,
            self._on_draw_jump,
            self._on_draw_dead
        ][self.state.get_state()]()

    def _on_update_run(self):
        if pygame.mouse.get_pressed()[0] != 0:
            self.state.change(Player.STATE_CROUCH)
        else:
            self.vel.x += 128 * dt
            if self.vel.x * self.vel.x > Player.MAX_VEL_X * Player.MAX_VEL_X:
                self.vel.x = -Player.MAX_VEL_X if self.vel.x < 0.0 else Player.MAX_VEL_X

    def _on_update_crouch(self):
        if pygame.mouse.get_pressed()[0] == 0:
            self.vel.y = -64 * min(self.state.get_time() * 2 + 0.125, 2)
            self.state.change(Player.STATE_JUMP)
        else:
            sign = 1 if self.vel.x >= 0 else -1
            mag = self.vel.x * 0.75 * dt
            if abs(mag) > abs(self.vel.x):
                mag = self.vel.x
            self.vel.x -= mag
            if abs(self.vel.x) < 16:
                self.vel.x = sign * 16

    def _on_update_jump(self):
        if self.state.get_time() > 1:
            self.state.change(Player.STATE_RUN)

    def _on_draw_run(self):
        body_pos = g_camera.relpos(self.pos)
        g_srf_screen.blit(g_img_char, body_pos, (24 * (int(g_time * 1000 / 100) % 2), 0, 24, 32))
        head_pos = body_pos
        head_pos[0] += 4
        head_pos[1] += 2 - (int(g_time * 1000 / 100) % 2)
        g_srf_screen.blit(g_img_char, head_pos, (16 * (int(g_time * 1000 / 400) % 8), 32, 16, 16))

    def _on_draw_crouch(self):
        body_pos = g_camera.relpos(self.pos)
        g_srf_screen.blit(g_img_char, body_pos, (48, 0, 24, 32))
        head_pos = pygame.math.Vector2(body_pos.x, body_pos.y)
        head_pos[0] += 4
        head_pos[1] += 4
        g_srf_screen.blit(g_img_char, head_pos, (16 * (int(g_time * 1000 / 400) % 8), 32, 16, 16))
        #if self.state.get_time() > 0.25 and 0 == (int(g_time * 1000 / 50) % 2):
        #    g_srf_screen.blit(g_img_char, body_pos, (96, 0, 24, 32))

    def _on_draw_jump(self):
        body_pos = g_camera.relpos(self.pos)
        g_srf_screen.blit(g_img_char, body_pos, (24, 0, 24, 32))
        head_pos = body_pos
        head_pos[0] += 4
        head_pos[1] += 1
        g_srf_screen.blit(g_img_char, head_pos, (16 * (int(g_time * 1000 / 400) % 8), 32, 16, 16))

    def _on_draw_dead(self):
        g_srf_screen.blit(g_img_char, g_camera.relpos(self.pos), (72, 0, 24, 32))
        g_srf_screen.blit(g_img_over, (SCR_W / 2 - g_img_over.get_width() / 2, SCR_H / 2 - g_img_over.get_height()))

g_camera = Camera()
g_player = Player()
g_stage = Stage()


class SceneGame:
    def __init__(self):
        g_player.reset()
        pygame.mixer.music.load('bgm.wav')
        pygame.mixer.music.set_volume(g_bgm_volume)
        pygame.mixer.music.play(loops=-1)

    def update(self, dt):
        g_player.update(dt)
        g_camera.update()

        if g_player.state.get_state() == Player.STATE_DEAD:
            if g_player.state.get_time() > 6:
                return False
        elif g_player.pos.y > SCR_H:
            g_player.state.change(Player.STATE_DEAD)
            pygame.mixer.music.load('gameover.wav')
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play(0)
            # pygame.mixer.music.stop()

        # pygame.surfarray.blit_array(g_srf_screen, bg_plasma())
        g_stage.draw()
        g_stage.draw_obj(False)
        g_player.draw()
        g_stage.draw_obj(True)
        return True

class SceneTitle:
    def __init__(self):
        self.mouse_pressed = False
        pass

    def update(self, dt):
        pygame.surfarray.blit_array(g_srf_screen, bg_plasma())
        g_srf_screen.blit(g_img_title, (0, 0))
        if not self.mouse_pressed:
            if pygame.mouse.get_pressed()[0] != 0:
                self.mouse_pressed = True
            return True
        elif pygame.mouse.get_pressed()[0] == 0:
            return False

def bg_rgb_noise():
    return numpy.random.randint(256, size=(SCR_W, SCR_H, 3))


def bg_plasma():
    buf = numpy.zeros((SCR_W, SCR_H, 3), dtype=int)
    x = UV[..., 0]
    y = UV[..., 1]
    cx = x + 0.5 * numpy.sin(g_time / 2.0)
    cy = y + 0.5 * numpy.cos(g_time / 3.0)
    v = numpy.sin(x * 5 + g_time) + numpy.sin(
        5 * (x * numpy.sin(g_time / 2) + y * numpy.cos(g_time / 3)) + g_time) + numpy.sin(
        numpy.sqrt(100 * (cx * cx + cy * cy) + 1) + g_time)
    buf[..., 0] = (numpy.sin(v * numpy.pi * numpy.sin(g_time * 0.1)) + 1.0) * 128
    buf[..., 1] = (numpy.sin(v * numpy.pi * numpy.cos(g_time * 0.14)) + 1.0) * 128
    buf[..., 2] = (numpy.sin(v * numpy.pi * numpy.sin(g_time * 0.13)) + 1.0) * 128
    return buf



# mainloop
scene = SceneTitle()
shutdown = False
begin_time = time.time()
while not shutdown:
    t = time.time() - begin_time

    dt = t - g_time
    if dt < 0.008:
        continue

    g_time = t

    for e in pygame.event.get():
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == 27):
            shutdown = True
            continue
        if e.type == pygame.MOUSEBUTTONDOWN:
            # ピン
            g_snd_ping.play(loops=-1)
            g_snd_ping.fadeout(1000)
            pass
        if e.type == pygame.MOUSEBUTTONUP:
            # ポン
            g_snd_ping.stop()
            g_snd_pong.play(loops=-1)
            g_snd_pong.fadeout(1500)
            pass

    if scene.update(dt) == False:
        if isinstance(scene, SceneTitle):
            scene = SceneGame()
        else:
            scene = SceneTitle()

    g_srf_display.blit(pygame.transform.scale(g_srf_screen,
                       (g_srf_display.get_width(), g_srf_display.get_height())), (0, 0))
    pygame.display.update()

pygame.quit()
