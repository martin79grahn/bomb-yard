/*
 * Bomb Yard for the NES (NROM, cc65)
 *
 * A port of the browser game: one player against two Krax monsters across
 * three levels, a one-minute timer, power-ups and background music.
 *
 * Screen: tile rows 0-3 are the HUD, rows 4-29 hold a 16 x 13 grid of
 * 16 x 16 pixel cells (one NES attribute quadrant per cell).
 */
#include "font.h"
#include "notes.h"

#pragma static-locals(on)

typedef unsigned char u8;
typedef signed char s8;
typedef unsigned int u16;

/* ---------- hardware ---------- */
#define PPUCTRL   (*(volatile u8*)0x2000)
#define PPUMASK   (*(volatile u8*)0x2001)
#define PPUSTATUS (*(volatile u8*)0x2002)
#define PPUADDR   (*(volatile u8*)0x2006)
#define PPUDATA   (*(volatile u8*)0x2007)
#define APU       ((volatile u8*)0x4000)
#define JOY1      (*(volatile u8*)0x4016)
#define OAM       ((u8*)0x0200)

#define BTN_A      0x80
#define BTN_B      0x40
#define BTN_SELECT 0x20
#define BTN_START  0x10
#define BTN_UP     0x08
#define BTN_DOWN   0x04
#define BTN_LEFT   0x02
#define BTN_RIGHT  0x01

/* shared with crt0.s */
u8 nmi_ready, ppu_ctrl, ppu_mask, frame_count;
u8 vram_buf[96];
static u8 vlen;

/* ---------- arena ---------- */
#define GW 16
#define GH 13
#define CELLS (GW * GH)
#define ARENA_Y 32            /* pixel y of the arena's top on screen */

#define FLOOR  0
#define CEMENT 1
#define STONE  2
#define TUFT   0x80           /* floor drawn with the tufted grass tiles */

#define IT_NONE 0
#define IT_SHOE 1
#define IT_FIRE 2
#define IT_BOMB 3

#define FUSE        180
#define FLAME_TIME  60
#define MAX_BOMBS   7
#define MAX_FLAMES  80
#define MAX_SPEEDUPS 4
#define ROUND_SECS  180         /* three minutes per level */
#define STRESS_SECS 20

/* RAM is tight (2 KB), so each cell packs several fields into one byte:
   cell:  bits 0-1 type, bits 2-3 item, bits 4-6 bomb index + 1, bit 7 tufted grass
   flame: bits 0-6 frames left to burn, bit 7 "needs redrawing" */
static u8 cell[CELLS];
static u8 flame[CELLS];
#define DQ 64
static u8 dirtyq[DQ];
static u8 dq_head, dq_tail;

#define TYPE(ci)        (cell[ci] & 3)
#define ITEM(ci)        ((cell[ci] >> 2) & 3)
#define SET_ITEM(ci, v) (cell[ci] = (cell[ci] & ~0x0C) | ((v) << 2))
#define BOMB(ci)        ((cell[ci] >> 4) & 7)
#define SET_BOMB(ci, v) (cell[ci] = (cell[ci] & ~0x70) | ((v) << 4))
#define FLAME(ci)       (flame[ci] & 0x7F)
static u8 flist[MAX_FLAMES];
static u8 fcount;
static u8 attr[64];

static u8 b_cell[MAX_BOMBS], b_fuse[MAX_BOMBS], b_range[MAX_BOMBS], b_used[MAX_BOMBS];

/* player */
static u8 px, py, pcx, pcy, pmoving, pdir, pleft, pfrac, pspeed, pups, pfire, pbombs, pactive;
static s8 pdx, pdy;
static u8 palive, pdeath, panim, pframe, ppending;

/* monsters */
#define NMON 2
static u8 mx[NMON], my[NMON], mcx[NMON], mcy[NMON], mmoving[NMON], mdir[NMON], mleft[NMON], mfrac[NMON];
static s8 mdx[NMON], mdy[NMON];
static u8 malive[NMON], mdeath[NMON], mwait[NMON], mbob[NMON];
static u8 mspeed;

static u8 level;              /* 0..2 */
static u8 debug;              /* debug mode: walk through walls */
static u8 burned;             /* the player died in a blast */
static u8 secs, subsec, time_up;
static u8 pad, pad_old, pad_new;
static u8 rng = 0x5A, rng2 = 0xC3;
static u8 i, j, k, t, c;      /* scratch */

/* directions: 0 left, 1 right, 2 up, 3 down */
static const s8 DX[4] = { -1, 1, 0, 0 };
static const s8 DY[4] = { 0, 0, -1, 1 };
static const s8 DSTEP[4] = { -1, 1, -GW, GW };
static const u8 BACK[4] = { 1, 0, 3, 2 };

/* bomber animation (frames are the top-left sprite tile of a 2 x 3 block) */
static const u8 ANIM_F[4][4] = { {8,10,12,10}, {8,10,12,10}, {4,6,4,6}, {0,2,0,2} };
static const u8 ANIM_FLIP[4][4] = { {0,0,0,0}, {1,1,1,1}, {0,0,0,1}, {0,0,0,1} };

/* ---------- palettes: background (4 x 4) then sprites (4 x 4), one set per level ---------- */
static const u8 PALETTES[3][32] = {
  { 0x2A,0x1A,0x0A,0x30,  0x2A,0x30,0x10,0x00,  0x2A,0x16,0x27,0x38,  0x2A,0x0F,0x30,0x27,
    0x2A,0x0F,0x30,0x16,  0x2A,0x0F,0x16,0x36,  0x2A,0x0F,0x30,0x27,  0x2A,0x0F,0x30,0x27 },
  { 0x38,0x27,0x17,0x30,  0x38,0x37,0x27,0x07,  0x38,0x16,0x27,0x30,  0x38,0x0F,0x30,0x16,
    0x38,0x0F,0x30,0x16,  0x38,0x0F,0x16,0x36,  0x38,0x0F,0x30,0x27,  0x38,0x0F,0x30,0x27 },
  { 0x01,0x11,0x21,0x30,  0x01,0x31,0x21,0x02,  0x01,0x16,0x27,0x38,  0x01,0x0F,0x30,0x27,
    0x01,0x0F,0x30,0x16,  0x01,0x0F,0x16,0x36,  0x01,0x0F,0x30,0x27,  0x01,0x0F,0x30,0x27 },
};
static const char* const LEVEL_NAME[3] = { "THE YARD", "SAND PIT", "FROST CAVE" };
static const u8 MONSTER_SPEED[3] = { 8, 10, 13 };   /* 1/16 px per frame: 0.5, 0.64, 0.8 */

/* ---------- helpers ---------- */
static u8 rand8(void) {
  rng ^= rng << 3; rng ^= rng >> 5; rng ^= rng2 << 1; rng2 ^= rng2 >> 1; rng2 ^= rng;
  return rng;
}

static void wait_frame(void) {
  vram_buf[vlen] = 0;
  nmi_ready = 1;
  while (nmi_ready) {}
  vlen = 0;
}

static void read_pad(void) {
  pad_old = pad;
  JOY1 = 1; JOY1 = 0;
  pad = 0;
  for (i = 0; i < 8; ++i) pad = (pad << 1) | (JOY1 & 1);
  pad_new = pad & ~pad_old;
}

static void ppu_off(void) { ppu_mask = 0; wait_frame(); PPUMASK = 0; }
static void ppu_on(void) { ppu_ctrl = 0x88; ppu_mask = 0x1E; wait_frame(); }

static void set_addr(u16 a) { PPUSTATUS; PPUADDR = a >> 8; PPUADDR = a & 0xFF; }

static void load_palette(void) {
  set_addr(0x3F00);
  for (i = 0; i < 32; ++i) PPUDATA = PALETTES[level][i];
}

/* write text straight to the nametable (rendering must be off) */
static void put_text(u8 x, u8 y, const char* s) {
  set_addr(0x2000 + (u16)y * 32 + x);
  while (*s) { PPUDATA = FONT_MAP[(u8)(*s) - 32]; ++s; }
}
static void put_text_centered(u8 y, const char* s) {
  for (i = 0; s[i]; ++i) {}
  put_text((32 - i) >> 1, y, s);
}

/* fill the whole screen with the dark HUD tile, palette 1 everywhere */
static void clear_screen(void) {
  set_addr(0x2000);
  for (i = 0; i < 30; ++i) for (j = 0; j < 32; ++j) PPUDATA = 0;
  for (i = 0; i < 64; ++i) { PPUDATA = 0x55; attr[i] = 0x55; }
}

/* queue text into the VRAM buffer (rendering on) */
static void vtext(u8 x, u8 y, const char* s) {
  u16 a = 0x2000 + (u16)y * 32 + x;
  u8 n = 0;
  while (s[n]) ++n;
  vram_buf[vlen++] = n;
  vram_buf[vlen++] = a >> 8;
  vram_buf[vlen++] = a & 0xFF;
  while (*s) { vram_buf[vlen++] = FONT_MAP[(u8)(*s) - 32]; ++s; }
}

/* ---------- sound ---------- */
static void sfx_place(void) { APU[4] = 0x86; APU[5] = 0x00; APU[6] = 0xE0; APU[7] = 0x08; }
static void sfx_pickup(void) { APU[4] = 0x45; APU[5] = 0xB9; APU[6] = 0xC0; APU[7] = 0x08; }
static void sfx_die(void) { APU[4] = 0x0A; APU[5] = 0x8B; APU[6] = 0x40; APU[7] = 0x09; }
static void sfx_boom(void) { APU[12] = 0x08; APU[14] = 0x0D; APU[15] = 0x18; }

/* music: square lead + triangle bass, a 16th note per step */
static const u8 LEAD[64] = {
  69,0,72,0,76,0,74,72, 69,0,67,0,69,0,0,0, 72,0,76,0,79,0,77,76, 74,0,72,0,74,0,0,0,
  69,0,72,0,76,0,79,0, 81,0,79,76,74,0,72,0, 74,0,72,0,69,0,67,0, 69,0,0,0,0,0,0,0 };
static const u8 BASS[16] = { 45,52,41,48,43,50,45,52, 45,52,41,48,43,50,45,45 };
static u8 mus_on, mus_step, mus_tick, lead_vol;

static void music_frame(void) {
  u8 n, shift, rate;
  if (!mus_on) return;
  if (lead_vol) { --lead_vol; APU[0] = 0xB0 | (lead_vol >> 1); }
  shift = level == 1 ? 2 : level == 2 ? 5 : 0;
  rate = 7 - level;
  if (secs <= STRESS_SECS) { ++shift; rate -= 2; }
  if (++mus_tick < rate) return;
  mus_tick = 0;
  n = LEAD[mus_step & 63];
  if (n) {
    n = n + shift - NOTE_LO;
    lead_vol = 10;
    APU[0] = 0xB5; APU[1] = 0x08;
    APU[2] = PULSE_PERIOD[n] & 0xFF; APU[3] = (PULSE_PERIOD[n] >> 8) | 0x08;
  }
  if ((mus_step & 1) == 0 || secs <= STRESS_SECS) {
    n = BASS[(mus_step >> 1) & 15] + shift - NOTE_LO;
    if (mus_step & 1) n += 12;                 /* driving off-beat when time is short */
    APU[8] = 0x18;
    APU[10] = TRI_PERIOD[n] & 0xFF; APU[11] = (TRI_PERIOD[n] >> 8) | 0x08;
  }
  ++mus_step;
}
static void music_stop(void) { mus_on = 0; APU[0] = 0x30; APU[8] = 0x80; APU[11] = 0; }

/* ---------- cell drawing ---------- */
static void mark(u8 ci) {
  if (flame[ci] & 0x80) return;
  if (((dq_tail + 1) & (DQ - 1)) == dq_head) return;   /* queue full: drop (very rare) */
  flame[ci] |= 0x80;
  dirtyq[dq_tail] = ci;
  dq_tail = (dq_tail + 1) & (DQ - 1);
}

/* tile + palette for a cell: base tile in t, palette in c */
static void cell_look(u8 ci) {
  if (FLAME(ci)) { t = 0x48; c = 2; }
  else if (BOMB(ci)) { t = 0x46; c = 3; }
  else if (ITEM(ci) == IT_SHOE) { t = 0x4A; c = 3; }
  else if (ITEM(ci) == IT_BOMB) { t = 0x4C; c = 3; }
  else if (ITEM(ci) == IT_FIRE) { t = 0x60; c = 3; }
  else if (TYPE(ci) == CEMENT) { t = 0x40; c = 1; }
  else if (TYPE(ci) == STONE) { t = 0x42; c = 1; }
  else { t = (cell[ci] & TUFT) ? 0x44 : 0; c = 0; }
}

static u8 attr_index(u8 cx, u8 cy) { return ((1 + (cy >> 1)) << 3) + (cx >> 1); }
static u8 set_attr(u8 cx, u8 cy, u8 pal) {
  u8 a = attr_index(cx, cy);
  u8 sh = ((cy & 1) ? 4 : 0) + ((cx & 1) ? 2 : 0);
  attr[a] = (attr[a] & ~(3 << sh)) | (pal << sh);
  return a;
}

/* draw one cell straight to the PPU (rendering off) */
static void draw_cell_direct(u8 ci) {
  u8 cx = ci & 15, cy = ci >> 4;
  u16 a = 0x2000 + (u16)(4 + cy * 2) * 32 + cx * 2;
  cell_look(ci);
  set_addr(a);
  if (t == 0) { PPUDATA = 0x44; PPUDATA = 0x44; set_addr(a + 32); PPUDATA = 0x44; PPUDATA = 0x44; }
  else { PPUDATA = t; PPUDATA = t + 1; set_addr(a + 32); PPUDATA = t + 16; PPUDATA = t + 17; }
  set_attr(cx, cy, c);
}

/* queue one cell into the VRAM buffer (rendering on) */
static void draw_cell_buffered(u8 ci) {
  u8 cx = ci & 15, cy = ci >> 4, a;
  u16 addr = 0x2000 + (u16)(4 + cy * 2) * 32 + cx * 2;
  cell_look(ci);
  if (t == 0) t = 0x44;
  vram_buf[vlen++] = 2; vram_buf[vlen++] = addr >> 8; vram_buf[vlen++] = addr & 0xFF;
  vram_buf[vlen++] = t; vram_buf[vlen++] = (t == 0x44 && !(cell[ci] & TUFT)) ? 0x44 : t + 1;
  addr += 32;
  vram_buf[vlen++] = 2; vram_buf[vlen++] = addr >> 8; vram_buf[vlen++] = addr & 0xFF;
  if (t == 0x44 && !(cell[ci] & TUFT)) { vram_buf[vlen++] = 0x44; vram_buf[vlen++] = 0x44; }
  else { vram_buf[vlen++] = t + 16; vram_buf[vlen++] = t + 17; }
  a = set_attr(cx, cy, c);
  vram_buf[vlen++] = 1; vram_buf[vlen++] = 0x23; vram_buf[vlen++] = 0xC0 + a;
  vram_buf[vlen++] = attr[a];
}

static void flush_dirty(void) {
  u8 n = 0;
  while (dq_head != dq_tail && n < 4) {
    k = dirtyq[dq_head];
    dq_head = (dq_head + 1) & (DQ - 1);
    flame[k] &= 0x7F;
    draw_cell_buffered(k);
    ++n;
  }
}

/* ---------- arena ---------- */
static u8 is_safe(u8 cx, u8 cy) {
  /* each corner and the cells next to it stay clear */
  u8 x = cx < GW / 2 ? cx : GW - 1 - cx;
  u8 y = cy < GH / 2 ? cy : GH - 1 - cy;
  return (x == 1 && y <= 3) || (y == 1 && x <= 3);
}

static void build_map(void) {
  u8 cx, cy;
  for (k = 0; k < CELLS; ++k) {
    cx = k & 15; cy = k >> 4;
    flame[k] = 0;
    if (cx == 0 || cy == 0 || cx == GW - 1 || cy == GH - 1 ||
        ((cx & 1) == 0 && (cy & 1) == 0 && cx < GW - 2 && cy < GH - 2)) cell[k] = CEMENT;
    else if (!is_safe(cx, cy) && rand8() < 154) cell[k] = STONE;
    else cell[k] = (rand8() < 64) ? (FLOOR | TUFT) : FLOOR;
  }
  dq_head = dq_tail = 0; fcount = 0;
  for (k = 0; k < MAX_BOMBS; ++k) b_used[k] = 0;
}

static u8 walkable(u8 ci) { return TYPE(ci) == FLOOR && !BOMB(ci); }

/* ---------- bombs and flames ---------- */
static void add_flame(u8 ci) {
  if (!FLAME(ci)) { if (fcount < MAX_FLAMES) flist[fcount++] = ci; else return; }
  flame[ci] = (flame[ci] & 0x80) | FLAME_TIME;
  SET_ITEM(ci, 0);
  mark(ci);
}

static void explode(u8 b);

static void blast_line(u8 start, u8 range, u8 d) {
  u8 ci = start, n;
  for (n = 0; n < range; ++n) {
    ci += DSTEP[d];
    if (TYPE(ci) == CEMENT) return;
    if (TYPE(ci) == STONE) {
      cell[ci] = FLOOR;
      add_flame(ci);
      t = rand8();
      SET_ITEM(ci, t < 85 ? IT_SHOE : t < 170 ? IT_FIRE : IT_BOMB);   /* shows when the fire is out */
      return;
    }
    add_flame(ci);
    if (BOMB(ci)) explode(BOMB(ci) - 1);
  }
}

static void explode(u8 b) {
  u8 ci = b_cell[b], r = b_range[b], d;
  if (!b_used[b]) return;
  b_used[b] = 0;
  SET_BOMB(ci, 0);
  if (pactive) --pactive;
  sfx_boom();
  add_flame(ci);
  for (d = 0; d < 4; ++d) blast_line(ci, r, d);
}

static void place_bomb(void) {
  u8 ci = pcy * GW + pcx;
  if (!palive || pactive >= pbombs || BOMB(ci)) return;
  for (k = 0; k < MAX_BOMBS; ++k) if (!b_used[k]) break;
  if (k == MAX_BOMBS) return;
  b_used[k] = 1; b_cell[k] = ci; b_fuse[k] = FUSE; b_range[k] = pfire;
  SET_BOMB(ci, k + 1);
  ++pactive;
  sfx_place();
  mark(ci);
}

static void update_bombs(void) {
  for (k = 0; k < MAX_BOMBS; ++k)
    if (b_used[k] && --b_fuse[k] == 0) explode(k);
  for (k = 0; k < fcount; ) {
    c = flist[k];
    if ((--flame[c] & 0x7F) == 0) {
      mark(c);
      flist[k] = flist[--fcount];
    } else ++k;
  }
}

/* ---------- player ---------- */
static u8 want_dir(void) {
  if (pad & BTN_LEFT) return 0;
  if (pad & BTN_RIGHT) return 1;
  if (pad & BTN_UP) return 2;
  if (pad & BTN_DOWN) return 3;
  return 0xFF;
}

static void try_step(u8 d) {
  u8 ci;
  if (d == 0xFF) { pframe = 0; panim = 0; return; }
  pdir = d;
  ci = pcy * GW + pcx + DSTEP[d];
  if (walkable(ci) || (debug && pcx + DX[d] >= 1 && pcx + DX[d] <= GW - 2 && pcy + DY[d] >= 1 && pcy + DY[d] <= GH - 2)) { pmoving = 1; pdx = DX[d]; pdy = DY[d]; pleft = 16; }
}

static void collect(void) {
  u8 ci = pcy * GW + pcx;
  t = ITEM(ci);
  if (!t) return;
  if (t == IT_SHOE && pups < MAX_SPEEDUPS) { ++pups; pspeed += 4; }
  if (t == IT_FIRE) ++pfire;
  if (t == IT_BOMB) ++pbombs;
  SET_ITEM(ci, 0);
  mark(ci);
  sfx_pickup();
}

static void update_player(void) {
  u8 s;
  if (!palive) { if (pdeath) --pdeath; return; }
  if (pad_new & (BTN_A | BTN_B)) ppending = 1;
  if (!pmoving) {
    if (ppending) { place_bomb(); ppending = 0; }
    try_step(want_dir());
  }
  if (pmoving) {
    pfrac += pspeed; s = pfrac >> 4; pfrac &= 15;
    if (s > pleft) s = pleft;
    px += pdx * (s8)s; py += pdy * (s8)s; pleft -= s;
    if (++panim >= 8) { panim = 0; pframe = (pframe + 1) & 3; }
    if (pleft == 0) {
      pmoving = 0; pcx = px >> 4; pcy = py >> 4;
      collect();
      if (ppending) { place_bomb(); ppending = 0; }
      try_step(want_dir());
    }
  }
}

/* ---------- monsters ---------- */
static u8 monster_pick(u8 m) {
  u8 open[4], n = 0, fwd = 0, d, ci = mcy[m] * GW + mcx[m], nc;
  for (d = 0; d < 4; ++d) {
    nc = ci + DSTEP[d];
    if (walkable(nc) && !FLAME(nc)) { open[n++] = d; if (d == mdir[m]) fwd = 1; }
  }
  if (!n) return 0xFF;
  if (fwd && rand8() < 180) return mdir[m];
  /* any open way except straight back, unless it's a dead end */
  for (d = 0; d < 8; ++d) {
    k = open[rand8() % n];
    if (k != BACK[mdir[m]] || n == 1) return k;
  }
  return open[0];
}

static void update_monster(u8 m) {
  u8 d, s;
  if (!malive[m]) { if (mdeath[m]) --mdeath[m]; return; }
  ++mbob[m];
  if (!mmoving[m]) {
    if (mwait[m]) { --mwait[m]; return; }
    d = monster_pick(m);
    if (d == 0xFF) { mwait[m] = 20; return; }
    mdir[m] = d; mdx[m] = DX[d]; mdy[m] = DY[d]; mmoving[m] = 1; mleft[m] = 16;
  }
  mfrac[m] += mspeed; s = mfrac[m] >> 4; mfrac[m] &= 15;
  if (s > mleft[m]) s = mleft[m];
  mx[m] += mdx[m] * (s8)s; my[m] += mdy[m] * (s8)s; mleft[m] -= s;
  if (mleft[m] == 0) {
    mmoving[m] = 0; mcx[m] = mx[m] >> 4; mcy[m] = my[m] >> 4;
    if (rand8() < 26) mwait[m] = 10 + (rand8() & 31);
  }
}

/* ---------- sprites ---------- */
static u8 oi;
static void spr(u8 x, u8 y, u8 tile, u8 a) {
  OAM[oi] = y - 1; OAM[oi + 1] = tile; OAM[oi + 2] = a; OAM[oi + 3] = x; oi += 4;
}

static void draw_sprites(void) {
  u8 f, fl, x, y, a, m;
  oi = 0;
  if (palive || (pdeath && (pdeath & 4))) {
    f = ANIM_F[pdir][pmoving ? pframe : 0];
    fl = ANIM_FLIP[pdir][pmoving ? pframe : 0];
    x = px; y = py + ARENA_Y - 8;
    a = fl ? 0x40 : 0x00;
    for (j = 0; j < 3; ++j) {
      spr(x, y + j * 8, f + j * 16 + (fl ? 1 : 0), a);
      spr(x + 8, y + j * 8, f + j * 16 + (fl ? 0 : 1), a);
    }
  }
  for (m = 0; m < NMON; ++m) {
    if (!malive[m] && !(mdeath[m] && (mdeath[m] & 4))) continue;
    x = mx[m]; y = my[m] + ARENA_Y - ((mmoving[m] && (mbob[m] & 8)) ? 1 : 0);
    fl = mdir[m] == 1;
    a = 0x02 | (fl ? 0x40 : 0);
    spr(x, y, fl ? 0x4F : 0x4E, a); spr(x + 8, y, fl ? 0x4E : 0x4F, a);
    spr(x, y + 8, fl ? 0x5F : 0x5E, a); spr(x + 8, y + 8, fl ? 0x5E : 0x5F, a);
  }
  do { OAM[oi] = 0xFF; oi += 4; } while (oi);
}

/* ---------- HUD ---------- */
static char hud[12];
static void hud_level(void) {
  hud[0] = 'L'; hud[1] = 'E'; hud[2] = 'V'; hud[3] = 'E'; hud[4] = 'L'; hud[5] = ' ';
  hud[6] = '1' + level; hud[7] = 0;
}
static void hud_time(void) {
  u8 show = !(secs <= 10 && (frame_count & 16));
  hud[0] = show ? '0' + secs / 60 : ' ';
  hud[1] = show ? ':' : ' ';
  hud[2] = show ? '0' + (secs % 60) / 10 : ' ';
  hud[3] = show ? '0' + secs % 10 : ' ';
  hud[4] = 0;
  vtext(14, 2, hud);
}
static void hud_krax(void) {
  hud[0] = 'K'; hud[1] = 'R'; hud[2] = 'A'; hud[3] = 'X'; hud[4] = ' ';
  hud[5] = '0' + (malive[0] ? 1 : 0) + (malive[1] ? 1 : 0); hud[6] = 0;
  vtext(24, 2, hud);
}

/* ---------- screens ---------- */
static void message_screen(const char* a, const char* b, const char* c2, u8 frames) {
  ppu_off();
  music_stop();
  clear_screen();
  if (a) put_text_centered(11, a);
  if (b) put_text_centered(14, b);
  if (c2) put_text_centered(17, c2);
  oi = 0; do { OAM[oi] = 0xFF; oi += 4; } while (oi);   /* no sprites on text screens */
  load_palette();
  ppu_on();
  pad = 0xFF;
  for (;;) {
    wait_frame();
    read_pad();
    if (frames) { if (--frames == 0) break; }
    else if (pad_new & BTN_START) break;
  }
}

static void start_level(u8 keep) {
  u8 m;
  ppu_off();
  build_map();
  clear_screen();
  for (k = 0; k < CELLS; ++k) draw_cell_direct(k);
  set_addr(0x23C0);
  for (k = 0; k < 64; ++k) PPUDATA = attr[k];
  hud_level();
  put_text(2, 2, hud);
  load_palette();

  pcx = 1; pcy = 1; px = 16; py = 16; pmoving = 0; pdir = 3; pframe = 0; panim = 0; pfrac = 0;
  palive = 1; pdeath = 0; pactive = 0; ppending = 0; burned = 0;
  if (!keep) { pspeed = 16; pups = 0; pfire = 1; pbombs = 1; }
  mspeed = MONSTER_SPEED[level];
  for (m = 0; m < NMON; ++m) {
    mcx[m] = GW - 2; mcy[m] = m ? 1 : GH - 2;
    mx[m] = mcx[m] * 16; my[m] = mcy[m] * 16;
    mmoving[m] = 0; mdir[m] = 0; mfrac[m] = 0; malive[m] = 1; mdeath[m] = 0; mwait[m] = 30; mbob[m] = 0;
  }
  secs = ROUND_SECS; subsec = 60; time_up = 0;
  draw_sprites();
  hud_time(); hud_krax();
  mus_on = 1; mus_step = 0; mus_tick = 0;
  ppu_on();
}

/* title: START begins, SELECT toggles debug mode */
static void title_screen(void) {
  ppu_off();
  music_stop();
  clear_screen();
  put_text_centered(9, "BOMB YARD");
  put_text_centered(13, "PRESS START");
  put_text_centered(16, "CLEAR 3 LEVELS OF KRAX");
  put_text_centered(22, "SELECT: DEBUG MODE");
  oi = 0; do { OAM[oi] = 0xFF; oi += 4; } while (oi);
  load_palette();
  ppu_on();
  pad = 0xFF;
  for (;;) {
    wait_frame();
    read_pad();
    if (pad_new & BTN_START) return;
    if (pad_new & BTN_SELECT) { debug ^= 1; vtext(11, 24, debug ? "DEBUG ON " : "         "); }
  }
}

/* ---------- main loop ---------- */
static u8 play_level(void) {   /* returns 1 when cleared, 0 when the player died */
  u8 m, kx, ky;
  for (;;) {
    wait_frame();
    read_pad();
    music_frame();

    if (pad_new & BTN_START) {           /* pause */
      music_stop();
      do { wait_frame(); read_pad(); } while (!(pad_new & BTN_START));
      mus_on = 1;
    }

    update_player();
    for (m = 0; m < NMON; ++m) update_monster(m);
    update_bombs();

    /* fire and monster contact */
    if (palive && FLAME(((py + 8) >> 4) * GW + ((px + 8) >> 4))) { palive = 0; pdeath = 60; burned = 1; sfx_die(); }
    for (m = 0; m < NMON; ++m) {
      if (!malive[m]) continue;
      if (FLAME(((my[m] + 8) >> 4) * GW + ((mx[m] + 8) >> 4))) {
        malive[m] = 0; mdeath[m] = 40; sfx_pickup(); hud_krax(); continue;
      }
      kx = px > mx[m] ? px - mx[m] : mx[m] - px;
      ky = py > my[m] ? py - my[m] : my[m] - py;
      if (palive && kx < 11 && ky < 11) { palive = 0; pdeath = 60; sfx_die(); }
    }

#ifdef TEST_CLEAR
    if (secs == 58) { malive[0] = malive[1] = 0; }   /* test build only: skip to the next level */
#endif
    /* the clock */
    if (palive && --subsec == 0) {
      subsec = 60;
      if (--secs == 0) { time_up = 1; palive = 0; pdeath = 60; sfx_die(); }
    }
    if (subsec == 60 || secs <= 10) hud_time();

    flush_dirty();
    draw_sprites();

    if (!palive && pdeath == 0) return 0;
    if (palive && !malive[0] && !malive[1] && !mdeath[0] && !mdeath[1]) return 1;
  }
}

void main(void) {
  APU[0x15] = 0x0F;      /* pulse 1+2, triangle, noise */
  ppu_ctrl = 0x88;
  PPUCTRL = 0x88;        /* NMI on; sprites from the second pattern table */

  for (;;) {
    level = 0;
    title_screen();
    rng ^= frame_count; rng2 ^= frame_count << 1;   /* seed from how long the title was up */
    if (!rng) rng = 1;

    message_screen("LEVEL 1", LEVEL_NAME[0], 0, 100);
    start_level(0);
    for (;;) {
      if (play_level()) {
        if (level == 2) {
          message_screen("CONGRATULATIONS!", "YOU CLEARED ALL 3 LEVELS", "YOU WIN!   PRESS START", 0);
          break;
        }
        ++level;
        message_screen("LEVEL CLEARED", "NEXT UP", LEVEL_NAME[level], 150);
        start_level(1);
      } else {
        message_screen(time_up ? "TIME UP" : burned ? "CAUGHT IN THE BLAST" : "THE KRAX GOT YOU", "TRY AGAIN", LEVEL_NAME[level], 120);
        start_level(1);
      }
    }
  }
}
