/*
 * Bomb Yard for the NES (NROM, cc65)
 *
 * A port of the browser game. 1 player: clear the two Krax monsters across
 * three levels, three minutes on the clock each. 2 players: blast each other
 * (second player on controller 2); an options screen picks the level, Krax
 * on/off and the wins needed (3, 5 or 10).
 * Each level has its own music: jungle bongos in The Yard, an oriental tune in
 * the Sand Pit and slow, echoing ambience in the Frost Cave.
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
#define JOY2      (*(volatile u8*)0x4017)
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
#define MAX_FIRE    9
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
/* the extra life (1 player only): a shoe item with the tuft bit set, since the item field is
   full; the tuft only matters for empty floor */
#define IS_LIFE(ci)     (ITEM(ci) == IT_SHOE && (cell[ci] & TUFT))
#define SET_ITEM(ci, v) (cell[ci] = (cell[ci] & ~0x0C) | ((v) << 2))
#define BOMB(ci)        ((cell[ci] >> 4) & 7)
#define SET_BOMB(ci, v) (cell[ci] = (cell[ci] & ~0x70) | ((v) << 4))
#define FLAME(ci)       (flame[ci] & 0x7F)
static u8 flist[MAX_FLAMES];
static u8 fcount;
static u8 attr[64];

static u8 b_cell[MAX_BOMBS], b_fuse[MAX_BOMBS], b_range[MAX_BOMBS], b_used[MAX_BOMBS], b_owner[MAX_BOMBS];

/* players: index 0 is controller 1, index 1 is controller 2 (2-player mode only) */
#define NPL 2
static u8 px[NPL], py[NPL], pcx[NPL], pcy[NPL], pmoving[NPL], pdir[NPL], pleft[NPL], pfrac[NPL];
static u8 pspeed[NPL], pups[NPL], pfire[NPL], pbombs[NPL], pactive[NPL];
static s8 pdx[NPL], pdy[NPL];
static u8 palive[NPL], pdeath[NPL], panim[NPL], pframe[NPL], ppending[NPL], pburned[NPL];
static u8 pl;                 /* the player being updated */
static u8 nplayers;           /* 1 = vs the Krax, 2 = versus */
static u8 wins[NPL];

/* 2-player options, kept from match to match */
static u8 opt_level;          /* arena look and Krax speed, 0..2 */
static u8 opt_monsters;       /* Krax roam the arena too */
static u8 opt_wins;           /* index into WIN_CHOICES */
static const u8 WIN_CHOICES[3] = { 3, 5, 10 };   /* also the choices of lives */
static u8 opt_lives;          /* 1 player: index into WIN_CHOICES */
static u8 lives;              /* 1 player: lives left */
static u8 win_target;         /* rounds needed to win the match */

/* monsters */
#define NMON 2
static u8 mx[NMON], my[NMON], mcx[NMON], mcy[NMON], mmoving[NMON], mdir[NMON], mleft[NMON], mfrac[NMON];
static s8 mdx[NMON], mdy[NMON];
static u8 malive[NMON], mdeath[NMON], mwait[NMON], mbob[NMON];
static u8 mspeed;

static u8 level;              /* 0..2 */
static u8 debug;              /* debug mode: walk through walls (1 player) */
static u8 secs, subsec, time_up;
static u8 pad, pad_old, pad_new, pad2, pad2_old, pad2_new;
static u8 rng = 0x5A, rng2 = 0xC3;
static u8 i, j, k, t, c;      /* scratch */

/* what play_level() ended with */
#define R_DIED    0
#define R_CLEARED 1
#define R_P1      2
#define R_P2      3
#define R_DRAW    4

/* directions: 0 left, 1 right, 2 up, 3 down */
static const s8 DX[4] = { -1, 1, 0, 0 };
static const s8 DY[4] = { 0, 0, -1, 1 };
static const s8 DSTEP[4] = { -1, 1, -GW, GW };
static const u8 BACK[4] = { 1, 0, 3, 2 };

/* bomber animation (frames are the top-left sprite tile of a 2 x 3 block) */
static const u8 ANIM_F[4][4] = { {8,10,12,10}, {8,10,12,10}, {4,6,4,6}, {0,2,0,2} };
static const u8 ANIM_FLIP[4][4] = { {0,0,0,0}, {1,1,1,1}, {0,0,0,1}, {0,0,0,1} };

/* ---------- palettes: background (4 x 4) then sprites (4 x 4), one set per level ----------
   sprite palette 0 is player 1 (white), 1 is player 2 (red), 2 the Krax */
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

/* both controllers; pad/pad_new are controller 1, pad2/pad2_new controller 2 */
static void read_pad(void) {
  pad_old = pad; pad2_old = pad2;
  JOY1 = 1; JOY1 = 0;
  pad = 0; pad2 = 0;
  for (i = 0; i < 8; ++i) { pad = (pad << 1) | (JOY1 & 1); pad2 = (pad2 << 1) | (JOY2 & 1); }
  pad_new = pad & ~pad_old;
  pad2_new = pad2 & ~pad2_old;
}

static void ppu_off(void) { ppu_mask = 0; wait_frame(); PPUMASK = 0; }
static void ppu_on(void) { ppu_ctrl = 0x88; ppu_mask = 0x1E; wait_frame(); }

static void set_addr(u16 a) { PPUSTATUS; PPUADDR = a >> 8; PPUADDR = a & 0xFF; }

/* rendering must be off. Writing in vblank and pointing the PPU back at $0000 afterwards
   keeps the palette colours from showing up as streaks on screen while they are written */
static void load_palette(void) {
  const u8* p = PALETTES[level];
  wait_frame();
  set_addr(0x3F00);
  for (i = 0; i < 32; ++i) PPUDATA = p[i];
  set_addr(0x0000);
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

static void hide_sprites(void) { k = 0; do { OAM[k] = 0xFF; k += 4; } while (k); }

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

/* ---------- sound effects (pulse 2 and noise) ---------- */
static u8 boom_t;         /* frames left of an explosion; drums wait for it */
static void sfx_place(void) { APU[4] = 0x86; APU[5] = 0x00; APU[6] = 0xE0; APU[7] = 0x08; }
static void sfx_pickup(void) { APU[4] = 0x45; APU[5] = 0xB9; APU[6] = 0xC0; APU[7] = 0x08; }
static void sfx_die(void) { APU[4] = 0x0A; APU[5] = 0x8B; APU[6] = 0x40; APU[7] = 0x09; }
/* envelope decay over about half a second; the length counter must not cut it first */
static void sfx_boom(void) { APU[12] = 0x08; APU[14] = 0x0D; APU[15] = 0x08; boom_t = 40; }

/* ---------- music ----------
   One song per level, each a 64-step loop on a 16th-note grid.
   LEAD (pulse 1) and TRI (triangle): a MIDI note starts a note, 0 lets the last one
   ring, 1 cuts it. TRI notes with L added are held until the next note; the rest are
   short hits (bongos in the jungle song, which also bend down in pitch).
   DRUM (noise) is a 16-step loop of the drum codes below. */
#define L 0x80
#define DUM 1                 /* low drum */
#define TEK 2                 /* slap */
#define SHK 3                 /* shaker */
#define WND 4                 /* wind */

static const u8 LEAD[3][64] = {
  /* The Yard: marimba-like calls in A minor pentatonic over the bongos */
  { 81,0,0,79, 0,76,0,0, 79,0,76,0, 74,0,0,0,   76,0,0,74, 0,72,0,0, 74,0,72,0, 69,0,0,0,
    69,0,72,0, 74,0,76,0, 79,0,0,76, 0,79,81,0, 84,0,0,81, 0,79,0,76, 79,0,76,0, 74,72,69,0 },
  /* Sand Pit: a reedy tune in D hijaz (D Eb F# G A Bb C) */
  { 74,0,0,75, 74,0,72,0, 70,0,72,0, 69,0,0,0,  66,0,67,0, 69,0,70,69, 67,0,66,0, 63,0,62,0,
    62,0,66,0, 67,0,69,0, 70,0,69,70, 72,0,70,69, 67,69,67,66, 63,0,66,0, 62,0,0,0, 0,0,1,0 },
  /* Frost Cave: sparse bells in E minor, each answered by its own echo */
  { 76,0,0,0, 83,0,0,0, 81,0,0,0, 0,0,0,0,      79,0,0,0, 78,0,0,0, 74,0,0,0, 0,0,0,0,
    76,0,0,0, 83,0,0,0, 88,0,0,0, 86,0,0,0,     83,0,0,0, 81,0,79,0, 78,0,0,0, 0,0,0,0 },
};
static const u8 TRI[3][64] = {
  /* bongos: low log drum (45), high (67) and low (60) bongo, a fill at the end */
  { 45,0,67,67, 60,0,67,0, 45,0,67,60, 67,60,60,0,  45,0,67,67, 60,0,67,0, 45,67,60,67, 60,67,60,60,
    45,0,67,67, 60,0,67,0, 45,0,67,60, 67,60,60,0,  45,67,67,60, 60,67,60,67, 72,72,67,67, 60,60,45,45 },
  /* a droning D bass that leans on Eb */
  { 38+L,0,0,0, 0,0,38+L,0, 0,0,38+L,0, 0,0,0,0,  39+L,0,0,0, 0,0,39+L,0, 0,0,38+L,0, 0,0,0,0,
    38+L,0,0,0, 0,0,38+L,0, 0,0,38+L,0, 0,0,0,0,  43+L,0,0,0, 0,0,39+L,0, 0,0,38+L,0, 0,0,38+L,0 },
  /* long, slow bass notes: E B C G E B D A */
  { 40+L,0,0,0, 0,0,0,0, 47+L,0,0,0, 0,0,0,0,  36+L,0,0,0, 0,0,0,0, 43+L,0,0,0, 0,0,0,0,
    40+L,0,0,0, 0,0,0,0, 47+L,0,0,0, 0,0,0,0,  38+L,0,0,0, 0,0,0,0, 45+L,0,0,0, 0,0,0,0 },
};
static const u8 DRUM[3][16] = {
  { DUM,SHK,SHK,SHK, TEK,SHK,DUM,SHK, DUM,SHK,SHK,DUM, TEK,SHK,SHK,SHK },   /* jungle groove */
  { DUM,0,TEK,0, SHK,0,TEK,0, DUM,0,SHK,0, TEK,0,SHK,0 },                   /* maqsum: dum tek - tek dum - tek - */
  { WND,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0 },                                 /* a breath of wind */
};
/* per song:              Yard  Sand  Frost */
static const u8 SONG_RATE[3]  = { 7,    8,    11 };     /* frames per step */
static const u8 LEAD_DUTY[3]  = { 0x40, 0x00, 0x80 };   /* 25%, 12.5% (reedy), 50% */
static const u8 LEAD_VOL[3]   = { 11,   9,    7 };
static const u8 LEAD_DECAY[3] = { 1,    5,    6 };      /* frames per volume step */
static const u8 LEAD_FLOOR[3] = { 0,    4,    0 };
static const u8 TRI_SHORT[3]  = { 16,   24,   24 };     /* short-note length, 1/240 s */
static const u8 TRI_BEND[3]   = { 7,    0,    0 };      /* bongo pitch drop per frame */
static const u8 VIBRATO[3]    = { 0,    1,    0 };
static const u8 ECHO[3]       = { 0,    0,    1 };
/* drum kit:                 -    DUM   TEK   SHK   WND */
static const u8 DRUM_PER[5] = { 0, 0x0C, 0x04, 0x00, 0x06 };
static const u8 DRUM_VOL[5] = { 0, 12,   9,    3,    3 };
static const u8 DRUM_DEC[5] = { 0, 1,    1,    1,    16 };

static u8 mus_on, mus_step, mus_tick;
static u8 lead_vol, lead_tick, lead_age;
static u16 lead_per, tri_per;
static u8 tri_bend;
static u8 noise_vol, noise_dec, noise_tick;
static void sfx_tick(void) {
  if (boom_t) return;
  noise_vol = 5; noise_dec = 1; noise_tick = 0;
  APU[12] = 0x35; APU[14] = 0x03; APU[15] = 0x08;
}

static void play_lead(u8 n, u8 vol) {
  lead_per = PULSE_PERIOD[n - NOTE_LO];
  lead_vol = vol; lead_tick = 0; lead_age = 0;
  APU[0] = LEAD_DUTY[level] | 0x30 | vol; APU[1] = 0x08;
  APU[2] = lead_per & 0xFF; APU[3] = (lead_per >> 8) | 0x08;
}

static void music_frame(void) {
  u8 n, s, rate, shift, lo;
  if (boom_t) --boom_t;
  if (!mus_on) return;

  /* lead: fade, and a gentle vibrato on held notes in the Sand Pit */
  if (lead_vol) {
    if (++lead_tick >= LEAD_DECAY[level]) { lead_tick = 0; if (lead_vol > LEAD_FLOOR[level]) --lead_vol; }
    ++lead_age;
    APU[0] = LEAD_DUTY[level] | 0x30 | lead_vol;
    lo = lead_per & 0xFF;
    if (VIBRATO[level] && lead_age > 10 && lo > 4 && lo < 250) APU[2] = (lead_age & 8) ? lo + 3 : lo - 3;
  }
  /* bongo pitch bend */
  if (tri_bend) {
    --tri_bend;
    n = tri_per >> 8;
    tri_per += TRI_BEND[level];
    APU[10] = tri_per & 0xFF;
    if ((tri_per >> 8) != n) APU[11] = (tri_per >> 8) | 0x08;
  }
  /* drum fade */
  if (noise_vol && !boom_t) {
    if (++noise_tick >= noise_dec) { noise_tick = 0; --noise_vol; }
    APU[12] = 0x30 | noise_vol;
  }

  rate = SONG_RATE[level]; shift = 0;
  if (secs <= STRESS_SECS) { shift = 1; rate -= 2; }    /* faster and a step higher when time is short */
  if (++mus_tick < rate) return;
  mus_tick = 0;
  s = mus_step & 63;

  n = LEAD[level][s];
  if (n == 1) { lead_vol = 0; APU[0] = 0x30; }
  else if (n) play_lead(n + shift, LEAD_VOL[level]);
  else if (ECHO[level] && (n = LEAD[level][(s - 2) & 63]) > 1) play_lead(n + shift, 3);

  n = TRI[level][s];
  if (n == 1) { APU[8] = 0x80; APU[11] = 0; tri_bend = 0; }
  else if (n) {
    tri_per = TRI_PERIOD[(n & 0x7F) + shift - NOTE_LO];
    APU[8] = (n & L) ? 0xFF : TRI_SHORT[level];
    APU[10] = tri_per & 0xFF; APU[11] = (tri_per >> 8) | 0x08;
    tri_bend = (n & L) ? 0 : (TRI_BEND[level] ? 6 : 0);
  }

  n = DRUM[level][s & 15];
  if (n && !boom_t) {
    noise_vol = DRUM_VOL[n]; noise_dec = DRUM_DEC[n]; noise_tick = 0;
    APU[12] = 0x30 | noise_vol; APU[14] = DRUM_PER[n]; APU[15] = 0x08;
  }
  if (secs <= STRESS_SECS && (s & 3) == 2) sfx_tick();   /* clock tick between the beats */
  ++mus_step;
}
static void music_start(void) { mus_on = 1; mus_step = 0; mus_tick = 0; }
static void music_stop(void) {
  mus_on = 0; lead_vol = 0; tri_bend = 0; noise_vol = 0;
  APU[0] = 0x30; APU[8] = 0x80; APU[11] = 0;
  if (!boom_t) APU[12] = 0x30;
}

/* win jingle on pulse 1, played while a message screen is up */
static const u8 WIN_TUNE[6] = { 67, 72, 76, 79, 76, 79 };
static u8 jingle_pos, jingle_tick;   /* jingle_pos 0 = silent */
static void jingle_frame(void) {
  u8 n;
  if (!jingle_pos) return;
  if (jingle_tick) { --jingle_tick; return; }
  jingle_tick = 7;
  if (jingle_pos > sizeof(WIN_TUNE)) { APU[0] = 0x30; jingle_pos = 0; return; }
  n = WIN_TUNE[jingle_pos - 1] - NOTE_LO;
  APU[0] = 0xB8; APU[1] = 0x08;
  APU[2] = PULSE_PERIOD[n] & 0xFF; APU[3] = (PULSE_PERIOD[n] >> 8) | 0x08;
  ++jingle_pos;
}

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
  else if (IS_LIFE(ci)) { t = 0x2C; c = 3; }
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

/* up to 4 cells a frame (15 bytes each), fewer when HUD text already used the buffer,
   so the NMI copy always fits in vblank */
static void flush_dirty(void) {
  u8 n = 0;
  while (dq_head != dq_tail && n < 4 && vlen <= 52) {
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

/* write v (0..99) at s as 1 or 2 digits, return the position after it */
static char* put_num(char* s, u8 v) {
  if (v >= 10) { *s++ = '0' + v / 10; v %= 10; }
  *s++ = '0' + v;
  return s;
}

/* ---------- HUD ----------
   1 player:  row 1 level and DEBUG, row 2 stats, clock and Krax left
   2 players: row 1 both players' stats (and Krax left), row 2 rounds won and the clock */
static char hud[12];
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
  vtext(nplayers == 2 ? 13 : 25, nplayers == 2 ? 1 : 2, hud);
}
/* "B1 F1 S0": bombs, blast range (fire) and speed-ups of player p */
static void hud_stats(u8 p) {
  hud[0] = 'B'; hud[1] = '0' + pbombs[p]; hud[2] = ' ';
  hud[3] = 'F'; hud[4] = '0' + pfire[p]; hud[5] = ' ';
  hud[6] = 'S'; hud[7] = '0' + pups[p]; hud[8] = 0;
  vtext(p ? 23 : 1, nplayers == 2 ? 1 : 2, hud);
}
/* 1 player: "LIVES 3" */
static void hud_lives(void) {
  char* s = hud;
  *s++ = 'L'; *s++ = 'I'; *s++ = 'V'; *s++ = 'E'; *s++ = 'S'; *s++ = ' ';
  s = put_num(s, lives); *s++ = ' '; *s = 0;
  vtext(11, 1, hud);
}
/* "P1 2/5": rounds won of rounds needed (rendering off) */
static void hud_wins(u8 p) {
  char* s = hud;
  *s++ = 'P'; *s++ = '1' + p; *s++ = ' ';
  s = put_num(s, wins[p]); *s++ = '/'; s = put_num(s, win_target); *s = 0;
  put_text(p ? 23 : 1, 2, hud);
}

/* ---------- bombs and flames ---------- */
static void add_flame(u8 ci) {
  if (!FLAME(ci)) { if (fcount < MAX_FLAMES) flist[fcount++] = ci; else return; }
  flame[ci] = (flame[ci] & 0x80) | FLAME_TIME;
  SET_ITEM(ci, 0);
  mark(ci);
}

static void blast_line(u8 start, u8 range, u8 d) {
  u8 ci = start, n;
  for (n = 0; n < range; ++n) {
    ci += DSTEP[d];
    if (TYPE(ci) == CEMENT) return;
    if (TYPE(ci) == STONE) {
      cell[ci] = FLOOR;
      add_flame(ci);
      t = rand8();
      if (nplayers == 1 && t < 12) { SET_ITEM(ci, IT_SHOE); cell[ci] |= TUFT; }   /* an extra life, now and then */
      else SET_ITEM(ci, t < 92 ? IT_SHOE : t < 174 ? IT_FIRE : IT_BOMB);   /* shows when the fire is out */
      return;
    }
    add_flame(ci);
    /* chain reaction: the other bomb goes off on its next fuse tick (this frame or the next).
       No recursion, because static locals would be overwritten by a nested call. */
    if (BOMB(ci)) b_fuse[BOMB(ci) - 1] = 1;
  }
}

static void explode(u8 b) {
  u8 ci = b_cell[b], r = b_range[b], d, o = b_owner[b];
  if (!b_used[b]) return;
  b_used[b] = 0;
  SET_BOMB(ci, 0);
  if (pactive[o]) --pactive[o];
  sfx_boom();
  add_flame(ci);
  for (d = 0; d < 4; ++d) blast_line(ci, r, d);
}

static void place_bomb(void) {
  u8 ci = pcy[pl] * GW + pcx[pl];
  if (!palive[pl] || pactive[pl] >= pbombs[pl] || BOMB(ci)) return;
  for (k = 0; k < MAX_BOMBS; ++k) if (!b_used[k]) break;
  if (k == MAX_BOMBS) return;
  b_used[k] = 1; b_cell[k] = ci; b_fuse[k] = FUSE; b_range[k] = pfire[pl]; b_owner[k] = pl;
  SET_BOMB(ci, k + 1);
  ++pactive[pl];
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

/* ---------- players ---------- */
static u8 want_dir(void) {
  u8 p = pl ? pad2 : pad;
  if (p & BTN_LEFT) return 0;
  if (p & BTN_RIGHT) return 1;
  if (p & BTN_UP) return 2;
  if (p & BTN_DOWN) return 3;
  return 0xFF;
}

static void try_step(u8 d) {
  u8 ci, nx, ny;
  if (d == 0xFF) { pframe[pl] = 0; panim[pl] = 0; return; }
  pdir[pl] = d;
  ci = pcy[pl] * GW + pcx[pl] + DSTEP[d];
  nx = pcx[pl] + DX[d]; ny = pcy[pl] + DY[d];
  if (walkable(ci) || (debug && nplayers == 1 && nx >= 1 && nx <= GW - 2 && ny >= 1 && ny <= GH - 2)) {
    pmoving[pl] = 1; pdx[pl] = DX[d]; pdy[pl] = DY[d]; pleft[pl] = 16;
  }
}

static void collect(void) {
  u8 ci = pcy[pl] * GW + pcx[pl];
  t = ITEM(ci);
  if (!t) return;
  if (IS_LIFE(ci)) {
    if (lives < 99) ++lives;
    SET_ITEM(ci, 0);
    mark(ci);
    jingle_pos = 1; jingle_tick = 0;               /* the win jingle, short and happy */
    hud_lives();
    return;
  }
  if (t == IT_SHOE && pups[pl] < MAX_SPEEDUPS) { ++pups[pl]; pspeed[pl] += 4; }
  if (t == IT_FIRE && pfire[pl] < MAX_FIRE) ++pfire[pl];
  if (t == IT_BOMB && pbombs[pl] < MAX_BOMBS) ++pbombs[pl];
  SET_ITEM(ci, 0);
  mark(ci);
  sfx_pickup();
  hud_stats(pl);
}

static void update_player(void) {
  u8 s;
  if (!palive[pl]) { if (pdeath[pl]) --pdeath[pl]; return; }
  if ((pl ? pad2_new : pad_new) & (BTN_A | BTN_B)) ppending[pl] = 1;
  if (!pmoving[pl]) {
    if (ppending[pl]) { place_bomb(); ppending[pl] = 0; }
    try_step(want_dir());
  }
  if (pmoving[pl]) {
    pfrac[pl] += pspeed[pl]; s = pfrac[pl] >> 4; pfrac[pl] &= 15;
    if (s > pleft[pl]) s = pleft[pl];
    px[pl] += pdx[pl] * (s8)s; py[pl] += pdy[pl] * (s8)s; pleft[pl] -= s;
    if (++panim[pl] >= 8) { panim[pl] = 0; pframe[pl] = (pframe[pl] + 1) & 3; }
    if (pleft[pl] == 0) {
      pmoving[pl] = 0; pcx[pl] = px[pl] >> 4; pcy[pl] = py[pl] >> 4;
      collect();
      if (ppending[pl]) { place_bomb(); ppending[pl] = 0; }
      try_step(want_dir());
    }
  }
}

static void kill_player(u8 p) { palive[p] = 0; pdeath[p] = 60; sfx_die(); }

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
  u8 f, fl, x, y, a, m, p;
  oi = 0;
  for (p = 0; p < nplayers; ++p) {
    if (!palive[p] && !(pdeath[p] & 4)) continue;
    f = ANIM_F[pdir[p]][pmoving[p] ? pframe[p] : 0];
    fl = ANIM_FLIP[pdir[p]][pmoving[p] ? pframe[p] : 0];
    x = px[p]; y = py[p] + ARENA_Y - 8;
    a = p | (fl ? 0x40 : 0x00);            /* palette 0 white, palette 1 red */
    for (j = 0; j < 3; ++j) {
      spr(x, y + j * 8, f + j * 16 + (fl ? 1 : 0), a);
      spr(x + 8, y + j * 8, f + j * 16 + (fl ? 0 : 1), a);
    }
  }
  for (m = 0; m < NMON; ++m) {
    if (!malive[m] && !(mdeath[m] & 4)) continue;
    x = mx[m]; y = my[m] + ARENA_Y - ((mmoving[m] && (mbob[m] & 8)) ? 1 : 0);
    fl = mdir[m] == 1;
    a = 0x02 | (fl ? 0x40 : 0);
    spr(x, y, fl ? 0x4F : 0x4E, a); spr(x + 8, y, fl ? 0x4E : 0x4F, a);
    spr(x, y + 8, fl ? 0x5F : 0x5E, a); spr(x + 8, y + 8, fl ? 0x5E : 0x5F, a);
  }
  do { OAM[oi] = 0xFF; oi += 4; } while (oi);
}

/* ---------- screens ---------- */
static u8 confetti;           /* falling confetti on the next message screen */

static void confetti_init(void) {
  for (k = 0; k < 32; ++k) {
    OAM[k * 4] = rand8() % 232;
    OAM[k * 4 + 1] = 0x30 + (k & 1);
    OAM[k * 4 + 2] = (k >> 1) & 3;
    OAM[k * 4 + 3] = rand8();
  }
}
static void confetti_frame(void) {
  for (k = 0; k < 32; ++k) {
    c = k * 4;
    OAM[c] += 1 + (k & 1);
    if (OAM[c] >= 232) OAM[c] = 0;
    if ((frame_count & 3) == 0) OAM[c + 3] += (k & 2) ? 1 : 0xFF;
  }
}

static void message_screen(const char* a, const char* b, const char* c2, u8 frames) {
  ppu_off();
  music_stop();
  clear_screen();
  if (a) put_text_centered(11, a);
  if (b) put_text_centered(14, b);
  if (c2) put_text_centered(17, c2);
  hide_sprites();
  if (confetti) confetti_init();
  load_palette();
  ppu_on();
  pad = 0xFF; pad2 = 0xFF;
  for (;;) {
    wait_frame();
    read_pad();
    jingle_frame();
    if (confetti) confetti_frame();
    if (frames) { if (--frames == 0) break; }
    else if ((pad_new | pad2_new) & BTN_START) break;
  }
  confetti = 0;
}

static void reset_player(u8 p, u8 cx, u8 cy, u8 keep) {
  pcx[p] = cx; pcy[p] = cy; px[p] = cx * 16; py[p] = cy * 16;
  pmoving[p] = 0; pdir[p] = 3; pframe[p] = 0; panim[p] = 0; pfrac[p] = 0;
  palive[p] = 1; pdeath[p] = 0; pactive[p] = 0; ppending[p] = 0; pburned[p] = 0;
  if (!keep) { pspeed[p] = 16; pups[p] = 0; pfire[p] = 1; pbombs[p] = 1; }
}

static void start_level(u8 keep) {
  u8 m;
  ppu_off();
  build_map();
  clear_screen();
  for (k = 0; k < CELLS; ++k) draw_cell_direct(k);
  set_addr(0x23C0);
  for (k = 0; k < 64; ++k) PPUDATA = attr[k];

  reset_player(0, 1, 1, keep);
  palive[1] = 0; pdeath[1] = 0;
  if (nplayers == 2) {
    reset_player(1, GW - 2, GH - 2, 0);
    hud_wins(0); hud_wins(1);
  } else {
    put_text(1, 1, "LEVEL");
    hud[0] = '1' + level; hud[1] = 0; put_text(7, 1, hud);
    if (debug) put_text(26, 1, "DEBUG");
    hud_lives();
  }
  load_palette();

  mspeed = MONSTER_SPEED[level];
  for (m = 0; m < NMON; ++m) {
    /* 1 player: the two far corners. 2 players: the two corners nobody starts in */
    mcx[m] = (nplayers == 2 && !m) ? 1 : GW - 2; mcy[m] = m ? 1 : GH - 2;
    mx[m] = mcx[m] * 16; my[m] = mcy[m] * 16;
    mmoving[m] = 0; mdir[m] = 0; mfrac[m] = 0; mdeath[m] = 0; mwait[m] = 30; mbob[m] = 0;
    malive[m] = nplayers == 1 || opt_monsters;
  }
  secs = ROUND_SECS; subsec = 60; time_up = 0;
  draw_sprites();
  hud_time(); hud_stats(0);
  if (nplayers == 2) hud_stats(1);
  if (malive[0]) hud_krax();
  music_start();
  ppu_on();
}

/* title: up/down picks 1 or 2 players, SELECT toggles debug mode, START begins */
static void title_draw_choice(void) {
  vtext(10, 13, nplayers == 1 ? ">" : " ");
  vtext(10, 15, nplayers == 2 ? ">" : " ");
  vtext(4, 19, nplayers == 1 ? " CLEAR 3 LEVELS OF KRAX " : "   BLAST YOUR FRIEND!   ");
}
static void title_screen(void) {
  ppu_off();
  music_stop();
  clear_screen();
  put_text_centered(8, "BOMB YARD");
  put_text(12, 13, "1 PLAYER");
  put_text(12, 15, "2 PLAYERS");
  put_text_centered(22, "SELECT: DEBUG MODE");
  put_text_centered(26, "PRESS START");
  hide_sprites();
  load_palette();
  if (!nplayers) nplayers = 1;
  title_draw_choice();
  if (debug) vtext(11, 24, "DEBUG ON");
  ppu_on();
  pad = 0xFF; pad2 = 0xFF;
  for (;;) {
    wait_frame();
    read_pad();
    if (pad_new & BTN_START) return;
    if (pad_new & (BTN_UP | BTN_DOWN)) { nplayers = 3 - nplayers; title_draw_choice(); }
    if (pad_new & BTN_SELECT) { debug ^= 1; vtext(11, 24, debug ? "DEBUG ON" : "        "); }
  }
}

/* ---------- main loop ---------- */
static u8 play_level(void) {
  u8 m, kx, ky;
  for (;;) {
    wait_frame();
    read_pad();
    music_frame();

    if ((pad_new | pad2_new) & BTN_START) {           /* pause */
      music_stop();
      do { wait_frame(); read_pad(); } while (!((pad_new | pad2_new) & BTN_START));
      mus_on = 1;
    }

    for (pl = 0; pl < nplayers; ++pl) update_player();
    for (m = 0; m < NMON; ++m) update_monster(m);
    update_bombs();

    /* fire and monster contact */
    for (pl = 0; pl < nplayers; ++pl)
      if (palive[pl] && FLAME(((py[pl] + 8) >> 4) * GW + ((px[pl] + 8) >> 4))) { pburned[pl] = 1; kill_player(pl); }
    for (m = 0; m < NMON; ++m) {
      if (!malive[m]) continue;
      if (FLAME(((my[m] + 8) >> 4) * GW + ((mx[m] + 8) >> 4))) {
        malive[m] = 0; mdeath[m] = 40; sfx_pickup(); hud_krax(); continue;
      }
      for (pl = 0; pl < nplayers; ++pl) {
        kx = px[pl] > mx[m] ? px[pl] - mx[m] : mx[m] - px[pl];
        ky = py[pl] > my[m] ? py[pl] - my[m] : my[m] - py[pl];
        if (palive[pl] && kx < 11 && ky < 11) kill_player(pl);
      }
    }

#ifdef TEST_CLEAR
    if (secs == ROUND_SECS - 2) { malive[0] = malive[1] = 0; }   /* test build only: skip to the next level */
#endif
    /* the clock: at zero the round is lost (1 player) or a draw (2 players) */
    if ((palive[0] || palive[1]) && --subsec == 0) {
      subsec = 60;
      if (--secs == 0) {
        time_up = 1;
        for (pl = 0; pl < nplayers; ++pl) if (palive[pl]) kill_player(pl);
      }
    }
    if (subsec == 60 || secs <= 10) hud_time();

    flush_dirty();
    draw_sprites();

    if (nplayers == 1) {
      if (!palive[0] && pdeath[0] == 0) return R_DIED;
      if (palive[0] && !malive[0] && !malive[1] && !mdeath[0] && !mdeath[1]) return R_CLEARED;
    } else if (!pdeath[0] && !pdeath[1] && palive[0] + palive[1] <= 1) {
      return palive[0] ? R_P1 : palive[1] ? R_P2 : R_DRAW;
    }
  }
}

static void solo_game(void) {
  level = 0;
  lives = WIN_CHOICES[opt_lives];
  message_screen("LEVEL 1", LEVEL_NAME[0], 0, 100);
  start_level(0);
  for (;;) {
    if (play_level() == R_CLEARED) {
      jingle_pos = 1; jingle_tick = 0;
      if (level == 2) {
        confetti = 1;
        message_screen("CONGRATULATIONS!", "YOU CLEARED ALL 3 LEVELS", "YOU WIN!   PRESS START", 0);
        return;
      }
      ++level;
      message_screen("LEVEL CLEARED", "NEXT UP", LEVEL_NAME[level], 150);
      start_level(1);
    } else {
      if (lives) --lives;
      if (!lives) {
        message_screen(time_up ? "TIME UP" : pburned[0] ? "CAUGHT IN THE BLAST" : "THE KRAX GOT YOU", "GAME OVER", "PRESS START", 0);
        return;
      }
      message_screen(time_up ? "TIME UP" : pburned[0] ? "CAUGHT IN THE BLAST" : "THE KRAX GOT YOU", "TRY AGAIN", LEVEL_NAME[level], 120);
      start_level(1);
    }
  }
}

/* ---------- 2 players ---------- */
static const char* const LEVEL_PAD[3] = { "THE YARD  ", "SAND PIT  ", "FROST CAVE" };
static u8 opt_row;

/* the level's colours, so the options screen previews the chosen arena */
static void queue_palette(void) {
  vram_buf[vlen++] = 32; vram_buf[vlen++] = 0x3F; vram_buf[vlen++] = 0x00;
  for (i = 0; i < 32; ++i) vram_buf[vlen++] = PALETTES[level][i];
}
static void options_draw(void) {
  if (nplayers == 1) {
    vtext(5, 13, ">");
    vtext(17, 13, opt_lives == 0 ? "3 " : opt_lives == 1 ? "5 " : "10");
    return;
  }
  vtext(5, 11, opt_row == 0 ? ">" : " ");
  vtext(5, 13, opt_row == 1 ? ">" : " ");
  vtext(5, 15, opt_row == 2 ? ">" : " ");
  vtext(17, 11, LEVEL_PAD[opt_level]);
  vtext(17, 13, opt_monsters ? "ON " : "OFF");
  vtext(17, 15, opt_wins == 0 ? "3 " : opt_wins == 1 ? "5 " : "10");
}
/* up/down picks a row, left/right (or A) changes it; returns 1 for START, 0 for B (back).
   1 player: lives. 2 players: level, monsters and wins. */
static u8 options_screen(void) {
  u8 rows = nplayers == 1 ? 1 : 3;
  ppu_off();
  music_stop();
  clear_screen();
  level = nplayers == 1 ? 0 : opt_level;
  if (nplayers == 1) {
    put_text_centered(6, "1 PLAYER OPTIONS");
    put_text(7, 13, "LIVES");
  } else {
    put_text_centered(6, "2 PLAYER OPTIONS");
    put_text(7, 11, "LEVEL");
    put_text(7, 13, "MONSTERS");
    put_text(7, 15, "WINS");
  }
  put_text_centered(19, "UP/DOWN: CHOOSE");
  put_text_centered(21, "LEFT/RIGHT: CHANGE");
  put_text_centered(24, "START: PLAY   B: BACK");
  hide_sprites();
  load_palette();
  opt_row = 0;
  options_draw();
  ppu_on();
  pad = 0xFF; pad2 = 0xFF;
  for (;;) {
    wait_frame();
    read_pad();
    if (pad_new & BTN_START) { win_target = WIN_CHOICES[opt_wins]; return 1; }
    if (pad_new & BTN_B) return 0;
    if (pad_new & BTN_UP) opt_row = opt_row ? opt_row - 1 : rows - 1;
    else if (pad_new & BTN_DOWN) opt_row = opt_row == rows - 1 ? 0 : opt_row + 1;
    else if (pad_new & (BTN_LEFT | BTN_RIGHT | BTN_A)) {
      t = (pad_new & BTN_LEFT) ? 2 : 1;          /* +2 mod 3 steps back */
      if (nplayers == 1) opt_lives = (opt_lives + t) % 3;
      else if (opt_row == 0) { opt_level = (opt_level + t) % 3; level = opt_level; queue_palette(); }
      else if (opt_row == 1) opt_monsters ^= 1;
      else opt_wins = (opt_wins + t) % 3;
    } else continue;
    options_draw();
  }
}

static char score[18];
static void make_score(void) {
  char* s = score;
  *s++ = 'S'; *s++ = 'C'; *s++ = 'O'; *s++ = 'R'; *s++ = 'E'; *s++ = ' ';
  s = put_num(s, wins[0]); *s++ = '-'; s = put_num(s, wins[1]); *s = 0;
}

static void versus_game(void) {
  u8 r, w;
  char* s = score;
  level = opt_level;
  wins[0] = wins[1] = 0;
  *s++ = 'F'; *s++ = 'I'; *s++ = 'R'; *s++ = 'S'; *s++ = 'T'; *s++ = ' '; *s++ = 'T'; *s++ = 'O'; *s++ = ' ';
  s = put_num(s, win_target);
  *s++ = ' '; *s++ = 'W'; *s++ = 'I'; *s++ = 'N'; *s++ = 'S'; *s = 0;
  message_screen(LEVEL_NAME[level], score, opt_monsters ? "WATCH OUT FOR THE KRAX" : "P2 USES CONTROLLER 2", 120);
  for (;;) {
    start_level(0);
    r = play_level();
    if (r == R_DRAW) {
      make_score();
      message_screen(time_up ? "TIME UP" : "DRAW", "NOBODY SCORES", score, 120);
      continue;
    }
    w = r - R_P1;
    ++wins[w];
    make_score();
    jingle_pos = 1; jingle_tick = 0;
    if (wins[w] >= win_target) {
      confetti = 1;
      message_screen(w ? "PLAYER 2 WINS THE MATCH!" : "PLAYER 1 WINS THE MATCH!", score, "PRESS START", 0);
      return;
    }
    message_screen(w ? "PLAYER 2 WINS THE ROUND" : "PLAYER 1 WINS THE ROUND", score, 0, 120);
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
    if (options_screen()) {
      if (nplayers == 1) solo_game();
      else versus_game();
    }
  }
}
