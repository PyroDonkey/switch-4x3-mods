"""Per-area view zoom for the 4:3 SMBW mod (v2): small rooms stay at the stock 15.5, wide world areas use 17, boss
arenas use their own table value, and everything that depends on the base follows it.

All addresses are flat-image offsets (== pchtxt addresses with offset_shift 0x100) for 1.2.1.

Mailbox words in the zero tail of .bss (last used byte of the image is 0x37D182C):
  0x037D1F00  effective base view height G for the current area (>= 15.5)
  0x037D1F10  box-cave marker (update)       0x037D1F14  box-cave marker (initialiser)
  0x037D1F18  reach-rule delta bits           0x037D1F1C  measured area width (debug)
  0x037D1F20  camera controller pointer (debug, x19)   0x037D1F28  camera subject pointer (debug, x20)

cave A  @0x02138800  hooked at 0x006C66DC (camera controller clamp block, x19 = controller): finds the current area record
        (table *(*0x37B2128+0x50), signed byte x19+0x10A), reads the area hash (+0x90) and bounds (+0x94 min x, +0xA0 max x),
        picks (G, delta) from the boss table, else from the width rule (width < 60 -> small room: 15.5 / 3.4444, else
        15.75 / 3.2778), stores G and delta, then runs the original instruction and the 16:9 reach rule with that delta.
cave B  @0x02138900  hooked at 0x002E2B30 (view height): s1 = max(15.5, G).
cave D/E             pipe display-box scaling k = 15.5 / G.
cave F1/F2 @0x02138D00/0x02138D20  hooked at 0x006C6358/0x006C6364 (controller view half-extents): height base s9 =
        max(15.5, G); width base = [0x2AEE9E8] * s9 / 15.5.
cave G  @0x02138A00  hooked at 0x006C6FD0 (fixed-position camera target): X = fixed X + eased offset; the offset is 0
        while fixed X moves (autoscroll, stock behaviour) and clamp(focus X - fixed X, +/- delta) in locked rooms.
        Replaces the old 006C6FD0-006C6FE4 lines (X = focus X unclamped), which let the player outrun autoscrolls.
  0x037D1F30  previous fixed X    0x037D1F34  autoscroll hold counter    0x037D1F38  current camera offset
cave H  @0x02138F00  hooked at 0x006C7BEC (side-lock X override, controller+0x29): X = locked X + clamp(normal X -
        locked X, +/- delta) instead of the locked X.
"""
import os, struct, sys
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

# Flat 1.2.1 image from nso_to_bin.py; game files stay outside the repo.
IMG = os.environ.get('SMBW_MAIN_BIN') or sys.exit('set SMBW_MAIN_BIN to the flat 1.2.1 image (nso_to_bin.py output)')
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
img = open(IMG, 'rb').read(0x2138650)
BSS = 0x37D1000
SLOT = 0x37D1F00
THRESH = 60.0
G_LARGE, D_LARGE = 15.75, (27.5556 - 15.75 * 4.0 / 3.0) / 2.0
G_SMALL, D_SMALL = 15.5, 3.4444444
# Boss rooms: (RootAreaHash, base view height G, reach delta). G = 20.6667 shows the full 16:9 width (27.56) at 4:3;
# with delta 0 the StopScroll-locked camera (cave H) stays exactly where the game locks it, like stock. Course152_Sub4
# also has the game's own zoom signal (17.5 blocks), which multiplies the base, so 20.6667 also gives the stock zoomed
# width. The delta must never exceed (27.5556 - G*4/3)/2, or cave H would pan the view past the 16:9 frame.
BOSS = [(607466214, 21.0, 0.0),                 # Course150_Sub4 Pipe-Rock Plateau Palace (user-confirmed at stock lock)
        (101336182, 20.6666667, 0.0),           # Course151_Sub2
        (1778226157, 20.6666667, 0.0),          # Course152_Sub4
        (1019598315, 20.6666667, 0.0)]          # Course153_Sub3
for _h, _g, _d in BOSS + [(0, G_LARGE, D_LARGE), (0, G_SMALL, D_SMALL)]:
    assert _d <= max(0.0, (27.5556 - _g * 4.0 / 3.0) / 2.0) + 1e-4, (_h, _g, _d)


def f32(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def b_(pc, t): return 0x14000000 | (((t - pc) >> 2) & 0x3FFFFFF)
def adrp(dst, pc, t):
    imm = ((t & ~0xFFF) - (pc & ~0xFFF)) >> 12
    return 0x90000000 | ((imm & 3) << 29) | (((imm >> 2) & 0x7FFFF) << 5) | dst
def adr(dst, pc, t):
    imm = t - pc
    return 0x10000000 | ((imm & 3) << 29) | (((imm >> 2) & 0x7FFFF) << 5) | dst
def ldr_x(rt, rn, off): return 0xF9400000 | ((off // 8) << 10) | (rn << 5) | rt
def ldr_w(rt, rn, off): return 0xB9400000 | ((off // 4) << 10) | (rn << 5) | rt
def str_w(rt, rn, off): return 0xB9000000 | ((off // 4) << 10) | (rn << 5) | rt
def str_x(rt, rn, off): return 0xF9000000 | ((off // 8) << 10) | (rn << 5) | rt
def ldr_s(rt, rn, off): return 0xBD400000 | ((off // 4) << 10) | (rn << 5) | rt
def str_s(rt, rn, off): return 0xBD000000 | ((off // 4) << 10) | (rn << 5) | rt
def ldr_s_lit(rt, pc, t): return 0x1C000000 | ((((t - pc) >> 2) & 0x7FFFF) << 5) | rt
def ldr_w_lit(rt, pc, t): return 0x18000000 | ((((t - pc) >> 2) & 0x7FFFF) << 5) | rt
def ldrsb_x(rt, rn, off): return 0x39800000 | (off << 10) | (rn << 5) | rt
def ldr_x_lsl3(rt, rn, rm): return 0xF8607800 | (rm << 16) | (rn << 5) | rt
def cbz_x(rt, pc, t): return 0xB4000000 | ((((t - pc) >> 2) & 0x7FFFF) << 5) | rt
def cbz_w(rt, pc, t): return 0x34000000 | ((((t - pc) >> 2) & 0x7FFFF) << 5) | rt
def bcond(c, pc, t): return 0x54000000 | ((((t - pc) >> 2) & 0x7FFFF) << 5) | c
EQ, NE, MI, GT, LE = 0, 1, 4, 12, 13
def cmn_x1(rn): return 0xB100041F | (rn << 5)
def cmp_w(rn, rm): return 0x6B00001F | (rm << 16) | (rn << 5)
def cmp_x(rn, rm): return 0xEB00001F | (rm << 16) | (rn << 5)
def add_x_imm(dst, rn, imm): return 0x91000000 | (imm << 10) | (rn << 5) | dst
def fmov_imm(dst, imm8): return 0x1E201000 | (imm8 << 13) | dst
def fmov_s_w(dst, rn): return 0x1E270000 | (rn << 5) | dst
def fmov_w_s(dst, rn): return 0x1E260000 | (rn << 5) | dst
def fadd_s(dst, rn, rm): return 0x1E202800 | (rm << 16) | (rn << 5) | dst
def fsub_s(dst, rn, rm): return 0x1E203800 | (rm << 16) | (rn << 5) | dst
def fmul_s(dst, rn, rm): return 0x1E200800 | (rm << 16) | (rn << 5) | dst
def fdiv_s(dst, rn, rm): return 0x1E201800 | (rm << 16) | (rn << 5) | dst
def fmax_s(dst, rn, rm): return 0x1E204800 | (rm << 16) | (rn << 5) | dst
def fmin_s(dst, rn, rm): return 0x1E205800 | (rm << 16) | (rn << 5) | dst
def fneg_s(dst, rn): return 0x1E214000 | (rn << 5) | dst
def fabs_s(dst, rn): return 0x1E20C000 | (rn << 5) | dst
def movz_w(dst, imm): return 0x52800000 | (imm << 5) | dst
def sub_w_imm(dst, rn, imm): return 0x51000000 | (imm << 10) | (rn << 5) | dst
def fcmp_s(rn, rm): return 0x1E202000 | (rm << 16) | (rn << 5)
def fcmp_zero_s(rn): return 0x1E202008 | (rn << 5)
def lsr_x32(dst, rn): return 0xD360FC00 | (rn << 5) | dst
def fmadd_s(dst, rn, rm, ra): return 0x1F000000 | (rm << 16) | (ra << 10) | (rn << 5) | dst
def bfi_x32(dst, rn): return 0xB3607C00 | (rn << 5) | dst
STR_X15_PUSH = 0xF81F0FEF      # str x15, [sp, #-16]!
LDR_X15_POP = 0xF84107EF       # ldr x15, [sp], #16
FMOV_05 = lambda dst: fmov_imm(dst, 0x60)
FMOV_155 = lambda dst: fmov_imm(dst, 0x2F)
FMOV_1 = lambda dst: fmov_imm(dst, 0x70)

words = []        # (address, word)


def emit(base, seq):
    for i, fn in enumerate(seq):
        words.append((base + 4 * i, fn(base + 4 * i)))
    return base + 4 * len(seq)


# ------------------------------------------------------------------ cave A
A = 0x2138800
N_CODE = 53
DATA = A + 4 * N_CODE                      # literals follow the code
L_THR, L_G17, L_D17, L_G155, L_D155 = DATA, DATA + 4, DATA + 8, DATA + 12, DATA + 16
TABLE = 0x2138E00                          # area table (hash, G, delta) in free cave space, up to 0x2138F00
lab = {}
seq_a = [
    lambda pc: STR_X15_PUSH,                                             # 0
    lambda pc: adrp(16, pc, 0x37B2000),                                  # 1
    lambda pc: ldr_x(16, 16, 0x128),                                     # 2
    lambda pc: cbz_x(16, pc, lab['small']),                              # 3
    lambda pc: ldr_x(16, 16, 0x50),                                      # 4
    lambda pc: cbz_x(16, pc, lab['small']),                              # 5
    lambda pc: ldr_w(17, 16, 0),                                         # 6
    lambda pc: cbz_w(17, pc, lab['small']),                              # 7
    lambda pc: ldrsb_x(17, 19, 0x10A),                                   # 8
    lambda pc: cmn_x1(17),                                               # 9
    lambda pc: bcond(EQ, pc, lab['small']),                              # 10
    lambda pc: ldr_x(16, 16, 8),                                         # 11
    lambda pc: ldr_x_lsl3(16, 16, 17),                                   # 12  x16 = area record
    lambda pc: ldr_w(15, 16, 0x90),                                      # 13  w15 = area hash
    lambda pc: ldr_s(16, 16, 0x94),                                      # 14  s16 = min x
    lambda pc: ldr_s(31, 16, 0xA0),                                      # 15  s31 = max x
    lambda pc: fsub_s(31, 31, 16),                                       # 16  s31 = width
    lambda pc: adrp(17, pc, BSS),                                        # 17
    lambda pc: str_s(31, 17, 0xF1C),                                     # 18  marker: width
    lambda pc: adr(16, pc, TABLE),                                       # 19  x16 = boss table
    lambda pc: ldr_w(17, 16, 0),                                         # 20  LOOP
    lambda pc: cbz_w(17, pc, lab['notab']),                              # 21
    lambda pc: cmp_w(17, 15),                                            # 22
    lambda pc: bcond(EQ, pc, lab['found']),                              # 23
    lambda pc: add_x_imm(16, 16, 12),                                    # 24
    lambda pc: b_(pc, lab['loop']),                                      # 25
    lambda pc: ldr_w(15, 16, 4),                                         # 26  FOUND: G bits
    lambda pc: ldr_w(17, 16, 8),                                         # 27  delta bits
    lambda pc: b_(pc, lab['store']),                                     # 28
    lambda pc: ldr_s_lit(16, pc, L_THR),                                 # 29  NOTAB
    lambda pc: fcmp_s(31, 16),                                           # 30
    lambda pc: bcond(MI, pc, lab['small']),                              # 31
    lambda pc: ldr_w_lit(15, pc, L_G17),                                 # 32  large world area
    lambda pc: ldr_w_lit(17, pc, L_D17),                                 # 33
    lambda pc: b_(pc, lab['store']),                                     # 34
    lambda pc: ldr_w_lit(15, pc, L_G155),                                # 35  SMALL room (or no area record)
    lambda pc: ldr_w_lit(17, pc, L_D155),                                # 36
    lambda pc: adrp(16, pc, BSS),                                        # 37  STORE
    lambda pc: str_w(15, 16, 0xF00),                                     # 38
    lambda pc: str_w(17, 16, 0xF18),                                     # 39
    lambda pc: str_x(19, 16, 0xF20),                                     # 40  debug: camera controller
    lambda pc: str_x(20, 16, 0xF28),                                     # 41  debug: camera subject
    lambda pc: struct.unpack_from('<I', img, 0x6C66DC)[0],               # 42  original: fsub s2, s7, s4
    lambda pc: fadd_s(7, 1, 3),                                          # 43
    lambda pc: FMOV_05(31),                                              # 44
    lambda pc: fmul_s(7, 7, 31),                                         # 45  s7 = centre
    lambda pc: fmov_s_w(31, 17),                                         # 46  s31 = delta
    lambda pc: fsub_s(16, 7, 31),                                        # 47
    lambda pc: fmin_s(1, 1, 16),                                         # 48
    lambda pc: fadd_s(16, 7, 31),                                        # 49
    lambda pc: fmax_s(3, 3, 16),                                         # 50
    lambda pc: LDR_X15_POP,                                              # 51
    lambda pc: b_(pc, 0x6C66E0),                                         # 52
]
assert len(seq_a) == N_CODE, len(seq_a)
lab.update({'small': A + 4 * 35, 'loop': A + 4 * 20, 'found': A + 4 * 26, 'notab': A + 4 * 29, 'store': A + 4 * 37})
emit(A, seq_a)
words += [(L_THR, f32(THRESH)), (L_G17, f32(G_LARGE)), (L_D17, f32(D_LARGE)), (L_G155, f32(G_SMALL)), (L_D155, f32(D_SMALL))]
assert L_D155 + 4 <= 0x2138900, hex(L_D155)
t = TABLE
for h, g, dl in BOSS:
    words += [(t, h), (t + 4, f32(g)), (t + 8, f32(dl))]
    t += 12
words += [(t, 0), (t + 4, 0), (t + 8, 0)]
assert t + 12 <= 0x2138F00, hex(t + 12)       # cave H starts at 0x2138F00

# ------------------------------------------------------------------ cave B (view height base)
B = 0x2138900
emit(B, [lambda pc: struct.unpack_from('<I', img, 0x2E2B30)[0],            # fmov s1, #15.5
         lambda pc: adrp(16, pc, BSS), lambda pc: ldr_s(16, 16, 0xF00),
         lambda pc: fmax_s(1, 1, 16), lambda pc: b_(pc, 0x2E2B34)])


# ------------------------------------------------------------------ caves D / E (pipe display box)
def box_cave(base, orig, ret, mark):
    seq = [
        lambda pc: orig,
        lambda pc: adrp(16, pc, BSS),
        lambda pc: ldr_s(16, 16, 0xF00),
        lambda pc: fcmp_zero_s(16),
        lambda pc: bcond(EQ, pc, base + 4 * 23),
        lambda pc: FMOV_155(17),
        lambda pc: fdiv_s(17, 17, 16),                         # s17 = k = 15.5 / G
        lambda pc: str_s(17, 16, mark),
        lambda pc: lsr_x32(10, 8),
        lambda pc: fmov_s_w(19, 10),
        lambda pc: lsr_x32(11, 9),
        lambda pc: fmov_s_w(20, 11),
        lambda pc: fadd_s(21, 19, 20),
        lambda pc: FMOV_05(22),
        lambda pc: fmul_s(21, 21, 22),
        lambda pc: fsub_s(23, 19, 21),
        lambda pc: fmadd_s(19, 23, 17, 21),
        lambda pc: fsub_s(23, 20, 21),
        lambda pc: fmadd_s(20, 23, 17, 21),
        lambda pc: fmov_w_s(10, 19),
        lambda pc: bfi_x32(8, 10),
        lambda pc: fmov_w_s(11, 20),
        lambda pc: bfi_x32(9, 11),
        lambda pc: b_(pc, ret),
    ]
    emit(base, seq)


box_cave(0x2138B00, struct.unpack_from('<I', img, 0x833B00)[0], 0x833B04, 0xF10)
box_cave(0x2138C00, struct.unpack_from('<I', img, 0x5E428C)[0], 0x5E4290, 0xF14)

# ------------------------------------------------------------------ cave F1 / F2 (controller view half-extents)
F1, F2 = 0x2138D00, 0x2138D20
emit(F1, [lambda pc: struct.unpack_from('<I', img, 0x6C6358)[0],           # fmov s9, #15.5
          lambda pc: adrp(16, pc, BSS), lambda pc: ldr_s(31, 16, 0xF00),
          lambda pc: fmax_s(9, 9, 31), lambda pc: b_(pc, 0x6C635C)])
emit(F2, [lambda pc: struct.unpack_from('<I', img, 0x6C6364)[0],           # ldr s8, [x9, #0x9e8]
          lambda pc: fmul_s(8, 8, 9),
          lambda pc: ldr_s_lit(31, pc, F2 + 20),
          lambda pc: fdiv_s(8, 8, 31),
          lambda pc: b_(pc, 0x6C6368),
          lambda pc: f32(15.5)])

# ------------------------------------------------------------------ cave G (fixed-position camera)
# When the camera subject holds a fixed position (subject+0x1B4, written only by the SetAutoScrollPos node: autoscrolls
# and scripted holds; StopScroll locks use the controller+0x29 override instead, see cave H) the game targets
# subject+0x194. Target X = fixed X + offset, where the offset (mailbox 0x037D1F38) eases at STEP per frame towards:
#   0                                         while fixed X is moving (autoscroll; held HOLD frames after it stops),
#                                             so the camera rides the scroll exactly like stock and never drifts back
#   clamp(focus X - fixed X, +/- delta)       once fixed X has been still for HOLD frames (stopped scroll, vertical
#                                             scroll): the 4:3 view pans inside the 16:9 frame
# A fixed-X jump of more than 1 block in one frame (new area, respawn, cut) or a different controller (x19 != the one
# cave A stored at 0x037D1F20) resets to offset 0 with a full hold, so the camera starts on the game's position.
# Mailbox: 0x037D1F30 previous fixed X, 0x037D1F34 autoscroll hold counter, 0x037D1F38 current offset.
# Only s0 (dead here: the original overwrites it on one path and both paths reload it), s31, x9, x10 and x17 are used.
G_CAVE = 0x2138A00
HOLD, EPS, STEP = 120, 0.002, 0.08


def clamp_delta():                    # s0 = clamp(s0, -delta, +delta), delta = mailbox 0xF18
    return [lambda pc: ldr_s(31, 17, 0xF18), lambda pc: fmin_s(0, 0, 31), lambda pc: fneg_s(31, 31),
            lambda pc: fmax_s(0, 0, 31)]


def follow():                         # s0 = clamp(focus X - fixed X, +/- delta)
    return [lambda pc: ldr_s(0, 19, 0x130), lambda pc: ldr_s(31, 20, 0x194), lambda pc: fsub_s(0, 0, 31)] + clamp_delta()


def assemble(base, items):
    """items: label strings or lambdas pc -> word (labels resolved through glab)."""
    pc = base
    for it in items:
        if isinstance(it, str):
            glab[it] = pc
        else:
            pc += 4
    seq = [it for it in items if not isinstance(it, str)]
    return emit(base, seq)


glab = {}
G_ITEMS = [
    lambda pc: ldr_w(10, 20, 0x198), lambda pc: str_w(10, 19, 0x140),                  # fixed Y
    lambda pc: ldr_w(10, 20, 0x19C), lambda pc: str_w(10, 19, 0x144),                  # fixed Z
    lambda pc: adrp(17, pc, BSS),
    lambda pc: ldr_s(31, 20, 0x194), lambda pc: ldr_s(0, 17, 0xF30), lambda pc: str_s(31, 17, 0xF30),
    lambda pc: ldr_x(10, 17, 0xF20), lambda pc: cmp_x(10, 19), lambda pc: bcond(NE, pc, glab['jump']),   # other controller
    lambda pc: fsub_s(0, 31, 0), lambda pc: fabs_s(0, 0),                              # s0 = |fixed X movement|
    lambda pc: ldr_w(9, 17, 0xF34),                                                    # w9 = hold counter
    lambda pc: FMOV_1(31), lambda pc: fcmp_s(0, 31), lambda pc: bcond(GT, pc, glab['jump']),
    lambda pc: ldr_s_lit(31, pc, glab['eps']), lambda pc: fcmp_s(0, 31), lambda pc: bcond(LE, pc, glab['still']),
    lambda pc: movz_w(9, HOLD), lambda pc: b_(pc, glab['desired']),                    # scrolling: restart hold
    'still',
    lambda pc: cbz_w(9, pc, glab['desired']), lambda pc: sub_w_imm(9, 9, 1),
    'desired',
    lambda pc: str_w(9, 17, 0xF34),
    lambda pc: cbz_w(9, pc, glab['locked']),
    lambda pc: fmov_s_w(0, 31), lambda pc: b_(pc, glab['step']),                       # autoscroll: desired 0
    'locked',
    *follow(),                                                                         # locked room: follow
    'step',
    lambda pc: ldr_s(31, 17, 0xF38), lambda pc: fsub_s(0, 0, 31),                      # s0 = desired - offset
    lambda pc: ldr_s_lit(31, pc, glab['stepv']), lambda pc: fmin_s(0, 0, 31), lambda pc: fneg_s(31, 31),
    lambda pc: fmax_s(0, 0, 31),
    lambda pc: ldr_s(31, 17, 0xF38), lambda pc: fadd_s(0, 0, 31),                      # offset += clamped step
    *clamp_delta(),
    lambda pc: b_(pc, glab['write']),
    'jump',                                                                            # new area / respawn / cut:
    lambda pc: movz_w(9, HOLD), lambda pc: str_w(9, 17, 0xF34),                        # ride the fixed X (hold) and
    lambda pc: fmov_s_w(0, 31),                                                        # start at offset 0; the pan
    'write',                                                                           # eases in after HOLD still frames
    lambda pc: str_s(0, 17, 0xF38),
    lambda pc: ldr_s(31, 20, 0x194), lambda pc: fadd_s(0, 0, 31), lambda pc: str_s(0, 19, 0x13C),   # target X
    lambda pc: b_(pc, 0x6C6FE8),
    'eps', lambda pc: f32(EPS),
    'stepv', lambda pc: f32(STEP),
]
G_END = assemble(G_CAVE, G_ITEMS)
assert G_END <= 0x2138B00, hex(G_END)
G_DATA = {glab['eps'], glab['stepv']}

# ------------------------------------------------------------------ cave H (side-locked camera X override)
# StopScroll with lockSide (e.g. Course021 Up 'n' Down with Puffy Lifts, the Wonder shaft) sets controller+0x29 and the
# final camera write replaces the normally computed X (s13, already limited by the area and the reach rule) with the
# locked X at controller+0x1A0 (branch at 0x006C6ADC -> 0x006C7BEC). Use locked X + clamp(s13 - locked X, +/- delta)
# instead, so the 4:3 view can pan to the edges of the 16:9 frame the lock was designed for.
# Only s9 (the output), s0 (overwritten at 0x006C6AF4 before any read), s31 and x17 are used.
H_CAVE = 0x2138F00
emit(H_CAVE, [lambda pc: ldr_s(9, 19, 0x1A0),                                           # locked X
              lambda pc: fsub_s(0, 13, 9),                                              # s0 = normal X - locked X
              lambda pc: adrp(17, pc, BSS), lambda pc: ldr_s(31, 17, 0xF18),
              lambda pc: fmin_s(0, 0, 31), lambda pc: fneg_s(31, 31), lambda pc: fmax_s(0, 0, 31),
              lambda pc: fadd_s(9, 9, 0),
              lambda pc: b_(pc, 0x6C6AE0)])

# ------------------------------------------------------------------ hooks
hooks = [(0x6C66DC, b_(0x6C66DC, A)), (0x2E2B30, b_(0x2E2B30, B)), (0x833B00, b_(0x833B00, 0x2138B00)),
         (0x5E428C, b_(0x5E428C, 0x2138C00)), (0x6C6358, b_(0x6C6358, F1)), (0x6C6364, b_(0x6C6364, F2)),
         (0x6C6FD0, b_(0x6C6FD0, G_CAVE)), (0x6C7BEC, b_(0x6C7BEC, H_CAVE))]
allw = sorted(hooks + words)
seen = set()
for a, w in allw:
    assert a not in seen, hex(a)
    seen.add(a)
data_addrs = {L_THR, L_G17, L_D17, L_G155, L_D155, F2 + 20} | {TABLE + 4 * i for i in range(3 * (len(BOSS) + 1))} | G_DATA
if __name__ == '__main__':
    for a, w in allw:
        dis = list(md.disasm(struct.pack('<I', w), a))
        if a in data_addrs or not dis:
            text = f"(data) 0x{w:08X} = {struct.unpack('<f', struct.pack('<I', w))[0]:.6g}"
        else:
            text = f"{dis[0].mnemonic} {dis[0].op_str}"
        print(f"{a:08X} {struct.pack('<I', w).hex().upper()}   {text}")
    if len(sys.argv) > 1:
        open(sys.argv[1], 'w').write('\n'.join(f"{a:08X} {struct.pack('<I', w).hex().upper()}" for a, w in allw) + '\n')
        print('wrote', sys.argv[1])
