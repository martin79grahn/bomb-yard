/*
 * Bomb Yard for the Mega Drive: the NES game's rules, redrawn and rescored.
 *
 * Screen (320 x 224): the 16 x 13 arena of 16-pixel cells sits between two HUD panels, under
 * a band with the level and the clock. Plane B holds the floor, walls and HUD; plane A the
 * bombs, flames and power-ups (see-through elsewhere) and the message boxes; the bombers
 * and Krax are sprites.
 */
#include <genesis.h>
#include "gen/gfx.h"
#include "resources.h"

/* ---------- screen layout ---------- */
#define AX 4                  /* arena's left edge, in tiles */
#define AY 2                  /* arena's top edge, in tiles */
#define TB TILE_USER_INDEX

/* ---------- arena ---------- */
#define GW 16
#define GH 13
#define CELLS (GW * GH)

#define FLOOR  0
#define CEMENT 1
#define STONE  2
#define TUFT   0x80           /* with a shoe item: the extra life */
#define HAS_BOMB 0x10
#define RUBBLE   0x20         /* a stone that was just blasted: while it burns it still stops other blasts,
                                 but it can't hurt */

#define IT_SHOE 1
#define IT_FIRE 2
#define IT_BOMB 3

#define FUSE        180
#define FLAME_TIME  32
#define FLAME_LOW   12        /* the blast thins out for its last frames */
#define MAX_BOMBS   40
#define MAX_SPEEDUPS 4
#define POOL_LIFE   1           /* 1 player only; bombs, fire and shoes: opt_items each */
#define POOL_PEN    2           /* penetrator bombs */
#define POOL_REM    2           /* remote controls */
#define ROUND_SECS  120         /* two minutes per level */
#define STRESS_SECS 20

#define TYPE(ci)        (cell[ci] & 3)
#define ITEM(ci)        ((cell[ci] >> 2) & 3)
#define IS_LIFE(ci)     (ITEM(ci) == IT_SHOE && (cell[ci] & TUFT))
/* the penetrator bomb: a bomb item with its own bit */
#define PEN             0x40
#define IS_PEN(ci)      (ITEM(ci) == IT_BOMB && (cell[ci] & PEN))
/* the remote control: a fire item with the same bit */
#define IS_REM(ci)      (ITEM(ci) == IT_FIRE && (cell[ci] & PEN))
#define SET_ITEM(ci, v) (cell[ci] = (cell[ci] & ~(0x0C | PEN)) | ((v) << 2))
#define BOMB(ci)        (cell[ci] & HAS_BOMB)
#define FLAME(ci)       (flame[ci])
#define HOT(ci)         (FLAME(ci) && !(cell[ci] & RUBBLE))   /* fire that kills */

static u8 cell[CELLS];
static u8 flame[CELLS];
static u8 bfire[CELLS];       /* burning only with the boss's own fire, which can't hurt it */
static u8 fowner;             /* whose bomb the flames being added come from */

static u8 b_cell[MAX_BOMBS], b_fuse[MAX_BOMBS], b_range[MAX_BOMBS], b_used[MAX_BOMBS], b_owner[MAX_BOMBS], b_pen[MAX_BOMBS];
static u8 b_rem[MAX_BOMBS];   /* a remote bomb: no fuse, its owner sets it off */

/* buttons, as the NES code had them */
#define K_UP    BUTTON_UP
#define K_DOWN  BUTTON_DOWN
#define K_LEFT  BUTTON_LEFT
#define K_RIGHT BUTTON_RIGHT
#define K_BOMB  (BUTTON_A | BUTTON_B | BUTTON_C)
#define K_REMOTE BUTTON_B      /* with the remote: B sets the bombs off, A and C drop them */
#define K_START BUTTON_START

/* players: index 0 is pad 1, index 1 is pad 2 (2 players) or the boss */
#define NPL 2
static u8 px[NPL], py[NPL], pcx[NPL], pcy[NPL], pmoving[NPL], pdir[NPL], pleft[NPL], pfrac[NPL];
static u8 pspeed[NPL], pups[NPL], pfire[NPL], pbombs[NPL], pactive[NPL];
static u8 ppen[NPL];            /* has the penetrator: blasts go through stone. Lost on dying */
static u8 prem[NPL];            /* has the remote: B sets off their bombs. Lost on dying */
static s8 pdx[NPL], pdy[NPL];
static u8 pbuf[NPL], pbuft[NPL];
static u8 palive[NPL], pdeath[NPL], panim[NPL], pframe[NPL], ppending[NPL], pburned[NPL];
static u8 pl, nplayers, wins[NPL];

static u8 opt_level, opt_monsters, opt_wins, opt_lives;
static u8 opt_items = 5;        /* power-ups of each kind per arena, 1..7 */
/* the four characters to play as; their colours are PAL_SPRITES[0..3], then each level's boss
   and its angry look */
#define PAL_BOSS(lv)  (4 + (lv) * 2)
#define PAL_ANGRY(lv) (5 + (lv) * 2)
static const char* const CHAR_NAME[4] = { "BIT ", "RUBY", "SKY ", "NOVA" };
static u8 opt_char[2] = { 0, 1 };
static const u8 WIN_CHOICES[3] = { 3, 5, 10 };
static u8 lives, win_target;

/* a boss waits after every level, tougher each time: hits to beat, hits before it gets angry
   (then one more bomb and 5 faster), bombs, blast, speed and frames between its bombs */
static const u8 BOSS_HP[6]     = { 3,  4,  4,  5,  6,  7 };
static const u8 BOSS_ANGRY[6]  = { 2,  2,  2,  3,  3,  4 };
static const u8 BOSS_BOMBS[6]  = { 2,  2,  3,  3,  3,  4 };
static const u8 BOSS_FIRE_R[6] = { 5,  5,  6,  6,  7,  7 };
static const u8 BOSS_SPEED[6]  = { 14, 15, 15, 16, 17, 18 };
static const u8 BOSS_REST[6]   = { 30, 26, 22, 18, 14, 12 };
static u8 boss, bhits, binv, bwait, vb_cell, vb_on;

#define NMON 2
static u8 mx[NMON], my[NMON], mcx[NMON], mcy[NMON], mmoving[NMON], mdir[NMON], mleft[NMON], mfrac[NMON];
static s8 mdx[NMON], mdy[NMON];
static u8 malive[NMON], mdeath[NMON], mwait[NMON], mbob[NMON];
static u8 mspeed;

static u8 level, debug, secs, subsec, time_up;   /* debug: walk through walls and never die */
static u8 rush;                 /* boss rush: only the five bosses, one after another (1 player) */
static u16 pad, pad_old, pad_new, pad2, pad2_old, pad2_new;
static u8 rng = 0x5A, rng2 = 0xC3;
static u16 frame_count;

#define R_DIED    0
#define R_CLEARED 1
#define R_P1      2
#define R_P2      3
#define R_DRAW    4

static const s8 DX[4] = { -1, 1, 0, 0 };
static const s8 DY[4] = { 0, 0, -1, 1 };
static const s8 DSTEP[4] = { -1, 1, -GW, GW };
static const u16 DBTN[4] = { K_LEFT, K_RIGHT, K_UP, K_DOWN };
static const u8 BACK[4] = { 1, 0, 3, 2 };

#define LEVELS 6
#define MON_SPR (level == SEA ? S_FISH : S_KRAX)   /* fish in the Deep Sea, Krax elsewhere */
#define SEA    5                /* the Deep Sea: fish instead of Krax, and a shark for a boss */
static const char* const LEVEL_NAME[LEVELS] = { "THE YARD", "SAND PIT", "FROST CAVE", "LAVA PEAK", "CLOUD NINE", "DEEP SEA" };
static const u8 MONSTER_SPEED[LEVELS] = { 8, 10, 13, 14, 15, 16 };
static const char* const LEVEL_NUM[LEVELS] = { "LEVEL 1", "LEVEL 2", "LEVEL 3", "LEVEL 4", "LEVEL 5", "LEVEL 6" };
static const char* const BOSS_TAKES[LEVELS] = { "IT TAKES 3 HITS", "IT TAKES 4 HITS", "IT TAKES 4 HITS", "IT TAKES 5 HITS", "IT TAKES 6 HITS", "IT TAKES 7 HITS" };
static const u8 LEVEL_PAL[LEVELS] = { 0, 1, 2, 4, 5, 6 };   /* PAL_ARENA index; 3 is the boss */

/* ---------- helpers ---------- */
static u8 rand8(void) {
    rng ^= rng << 3; rng ^= rng >> 5; rng ^= rng2 << 1; rng2 ^= rng2 >> 1; rng2 ^= rng;
    return rng;
}

static void read_pads(void) {
    pad_old = pad; pad2_old = pad2;
    pad = JOY_readJoypad(JOY_1);
    pad2 = JOY_readJoypad(JOY_2);
    pad_new = pad & ~pad_old;
    pad2_new = pad2 & ~pad2_old;
}

static void frame(void) {
    SYS_doVBlankProcess();
    read_pads();
    ++frame_count;
}

/* ---------- sound ---------- */
static const u8* cur_song;
static void music(const u8* song) {
    if (song == cur_song && XGM2_isPlaying()) return;
    cur_song = song;
    XGM2_setMusicTempo(60);
    XGM2_play(song);
}
static void music_stop(void) { XGM2_stop(); cur_song = NULL; }
static void jingle(const u8* song) { cur_song = NULL; XGM2_setMusicTempo(60); XGM2_play(song); }

#define SFX(name, ch) XGM2_playPCM(name, sizeof(name), ch)
static void sfx_boom(void)    { SFX(snd_boom, SOUND_PCM_CH1); }
static void sfx_place(void)   { SFX(snd_place, SOUND_PCM_CH2); }
static void sfx_pickup(void)  { SFX(snd_pickup, SOUND_PCM_CH2); }
static void sfx_heart(void)   { SFX(snd_heart, SOUND_PCM_CH2); }
static void sfx_die(void)     { SFX(snd_die, SOUND_PCM_CH3); }
static void sfx_bosshit(void) { SFX(snd_bosshit, SOUND_PCM_CH3); }
static void sfx_tick(void)    { SFX(snd_tick, SOUND_PCM_CH3); }
static void sfx_menu(void)    { SFX(snd_menu, SOUND_PCM_CH3); }
static void sfx_select(void)  { SFX(snd_select, SOUND_PCM_CH3); }

/* ---------- text and boxes ---------- */
static u16 font_tile(char ch, u8 yellow) {
    u8 c = (u8)ch;
    if (c < 32 || c >= 128) c = 32;
    return TB + (yellow ? T_FONT_Y : T_FONT) + FONT_MAP[c - 32];
}
static void text(VDPPlane plane, u16 x, u16 y, const char* s, u8 yellow) {
    u16 prio = plane == BG_A ? 1 : 0;
    while (*s) { VDP_setTileMapXY(plane, TILE_ATTR_FULL(PAL0, prio, 0, 0, font_tile(*s, yellow)), x++, y); ++s; }
}
static u16 str_len(const char* s) { u16 n = 0; while (s[n]) ++n; return n; }
static void text_c(VDPPlane plane, u16 y, const char* s, u8 yellow) {
    text(plane, AX + 16 - (str_len(s) >> 1), y, s, yellow);
}
static char* put_num(char* s, u8 v) {
    if (v >= 10) { *s++ = '0' + v / 10; v %= 10; }
    *s++ = '0' + v;
    *s = 0;
    return s;
}

/* a message box on plane A, w x h tiles, its top left at (x, y) */
static void box(u16 x, u16 y, u16 w, u16 h) {
    u16 i, j, t;
    for (j = 0; j < h; ++j)
        for (i = 0; i < w; ++i) {
            t = (j == 0 ? 0 : j == h - 1 ? 6 : 3) + (i == 0 ? 0 : i == w - 1 ? 2 : 1);
            VDP_setTileMapXY(BG_A, TILE_ATTR_FULL(PAL0, 1, 0, 0, TB + T_BOX + t), x + i, y + j);
        }
}
static void clear_plane_a(void) { VDP_clearPlane(BG_A, TRUE); }

/* ---------- cell drawing ---------- */
static u8 flame_phase;

static u8 is_block(u8 ci) { return TYPE(ci) != FLOOR; }

/* plane B: floor (with the shadows of the blocks above and to the left), wall or stone */
static void draw_ground(u8 ci) {
    u8 cx = ci & 15, cy = ci >> 4, s;
    u16 x = AX + cx * 2, y = AY + cy * 2;
    const u16* f;
    if (TYPE(ci) != FLOOR) f = TYPE(ci) == CEMENT ? WALL_T : STONE_T;
    else {
        s = (cy && is_block(ci - GW) ? 1 : 0) | (cx && is_block(ci - 1) ? 2 : 0);
        f = &FLOOR_T[((((cx * 7 + cy * 3) >> 1) & 1) * 4 + s) * 4];
    }
    VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL0, 0, 0, 0, TB + f[0]), x, y);
    VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL0, 0, 0, 0, TB + f[1]), x + 1, y);
    VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL0, 0, 0, 0, TB + f[2]), x, y + 1);
    VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL0, 0, 0, 0, TB + f[3]), x + 1, y + 1);
}

static u8 bomb_at(u8 ci) {
    u8 b;
    for (b = 0; b < MAX_BOMBS; ++b) if (b_used[b] && b_cell[b] == ci) return b;
    return 0;
}

/* plane A: a flame piece, a bomb, a power-up or nothing */
static void draw_obj(u8 ci) {
    u8 cx = ci & 15, cy = ci >> 4, sides, fz;
    u16 x = AX + cx * 2, y = AY + cy * 2, t, attr;
    if (FLAME(ci)) {
        sides = (FLAME(ci - 1) ? 1 : 0) | (FLAME(ci + 1) ? 2 : 0) | (FLAME(ci - GW) ? 4 : 0) | (FLAME(ci + GW) ? 8 : 0);
        t = T_FLAME + (((FLAME(ci) < FLAME_LOW ? 2 : 0) + flame_phase) * 16 + sides) * 4;
    } else if (BOMB(ci)) {
        fz = bomb_at(ci);
        if (b_rem[fz]) t = T_RBOMB + ((frame_count >> 5) & 1) * 4;   /* its lamp blinks */
        else {
            fz = b_fuse[fz];
            t = T_BOMB + (((frame_count >> 3) & 1) + (fz < 60 && ((fz / 5) & 1) ? 2 : 0)) * 4;
        }
    } else if (TYPE(ci) != FLOOR || !ITEM(ci)) {
        VDP_setTileMapXY(BG_A, 0, x, y); VDP_setTileMapXY(BG_A, 0, x + 1, y);
        VDP_setTileMapXY(BG_A, 0, x, y + 1); VDP_setTileMapXY(BG_A, 0, x + 1, y + 1);
        return;
    } else if (IS_LIFE(ci)) t = T_ITEM_LIFE;
    else if (IS_PEN(ci)) t = T_ITEM_PEN;
    else if (IS_REM(ci)) t = T_ITEM_REM;
    else if (ITEM(ci) == IT_SHOE) t = T_ITEM_SHOE;
    else if (ITEM(ci) == IT_FIRE) t = T_ITEM_FIRE;
    else t = T_ITEM_BOMB;
    attr = TILE_ATTR_FULL(PAL1, 0, 0, 0, TB + t);
    VDP_setTileMapXY(BG_A, attr, x, y);
    VDP_setTileMapXY(BG_A, attr + 1, x + 1, y);
    VDP_setTileMapXY(BG_A, attr + 2, x, y + 1);
    VDP_setTileMapXY(BG_A, attr + 3, x + 1, y + 1);
}

/* ---------- arena ---------- */
static u8 is_safe(u8 cx, u8 cy) {
    u8 x = cx < GW / 2 ? cx : GW - 1 - cx;
    u8 y = cy < GH / 2 ? cy : GH - 1 - cy;
    return (x == 1 && y <= 3) || (y == 1 && x <= 3);
}

static void hide_items(u8 it, u8 n) {
    u16 tries = 1000;
    u8 ci;
    while (n && --tries) {
        ci = rand8();
        if (ci >= CELLS || TYPE(ci) != STONE || ITEM(ci)) continue;
        SET_ITEM(ci, it & 3);
        if (it & 0x20) cell[ci] |= TUFT;
        cell[ci] |= it & PEN;
        --n;
    }
}

static void build_map(void) {
    u8 cx, cy;
    u16 k;
    for (k = 0; k < CELLS; ++k) {
        cx = k & 15; cy = k >> 4;
        flame[k] = 0;
        if (cx == 0 || cy == 0 || cx == GW - 1 || cy == GH - 1 ||
            ((cx & 1) == 0 && (cy & 1) == 0 && cx < GW - 2 && cy < GH - 2)) cell[k] = CEMENT;
        else if (!is_safe(cx, cy) && rand8() < (boss ? 90 : 154)) cell[k] = STONE;
        else cell[k] = FLOOR;
    }
    for (k = 0; k < MAX_BOMBS; ++k) b_used[k] = 0;
    if (nplayers == 1) hide_items(IT_SHOE | 0x20, POOL_LIFE);
    hide_items(IT_BOMB | PEN, POOL_PEN);
    hide_items(IT_FIRE | PEN, POOL_REM);
    hide_items(IT_BOMB, opt_items);
    hide_items(IT_FIRE, opt_items);
    hide_items(IT_SHOE, opt_items);
}

static u8 walkable(u8 ci) { return TYPE(ci) == FLOOR && !BOMB(ci); }

/* ---------- HUD ---------- */
static char hud[16];

static void hud_time(void) {
    u8 show = !(secs <= 10 && (frame_count & 16));
    hud[0] = show ? '0' + secs / 60 : ' ';
    hud[1] = show ? ':' : ' ';
    hud[2] = show ? '0' + (secs % 60) / 10 : ' ';
    hud[3] = show ? '0' + secs % 10 : ' ';
    hud[4] = 0;
    text(BG_B, 32, 0, hud, secs <= STRESS_SECS);
}

/* a 16x16 icon on plane B from four tiles in TL, TR, BL, BR order */
static void icon(u16 x, u16 y, u16 pal, u16 t0, u16 t1, u16 t2, u16 t3) {
    VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(pal, 0, 0, 0, TB + t0), x, y);
    VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(pal, 0, 0, 0, TB + t1), x + 1, y);
    VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(pal, 0, 0, 0, TB + t2), x, y + 1);
    VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(pal, 0, 0, 0, TB + t3), x + 1, y + 1);
}
static void item_icon(u16 x, u16 y, u16 t) { icon(x, y, PAL1, t, t + 1, t + 2, t + 3); }

/* a number under an icon, centred in the 4-tile panel */
static void hud_num(u16 x, u16 y, u8 v) {
    hud[0] = ' ';
    put_num(hud + 1, v);
    if (v < 10) { hud[2] = ' '; hud[3] = 0; }
    text(BG_B, x, y, hud, 0);
}

static void hud_stats(u8 p) {
    u16 x = p ? 36 : 0;
    item_icon(x + 1, 5, ppen[p] ? T_ITEM_PEN : T_ITEM_BOMB);   /* the penetrator shows in place of the bomb */
    hud_num(x, 7, pbombs[p]);
    hud_num(x, 11, pfire[p]);
    hud_num(x, 15, pups[p]);
    if (prem[p]) item_icon(x + 1, 25, T_ITEM_REM);   /* the remote, while you hold it */
    else { VDP_setTileMapXY(BG_B, 0, x + 1, 25); VDP_setTileMapXY(BG_B, 0, x + 2, 25);
           VDP_setTileMapXY(BG_B, 0, x + 1, 26); VDP_setTileMapXY(BG_B, 0, x + 2, 26); }
}
static void hud_lives(void) { hud_num(0, 19, lives); }
static void hud_krax(void) { hud_num(36, 7, (malive[0] ? 1 : 0) + (malive[1] ? 1 : 0)); }
static void hud_boss(void) { hud_num(36, 8, BOSS_HP[level] - bhits); }
static void hud_wins(u8 p) {
    char* s = hud;
    *s++ = ' ';
    s = put_num(s, wins[p]); *s++ = '/'; put_num(s, win_target);
    text(BG_B, p ? 36 : 0, 23, hud, 1);
}

static void draw_hud(void) {
    u16 y;
    VDP_clearPlane(BG_B, TRUE);
    for (y = AY; y < 28; ++y) {
        VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL0, 0, 0, 0, TB + T_PANEL_L), AX - 1, y);
        VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL0, 0, 0, 0, TB + T_PANEL_R), AX + 32, y);
    }
    if (nplayers == 1) {
        if (boss) text(BG_B, 4, 0, "BOSS FIGHT", 1);
        else {
            text(BG_B, 4, 0, "LEVEL", 1);
            hud[0] = '1' + level; hud[1] = 0; text(BG_B, 10, 0, hud, 1);
            text(BG_B, 12, 0, LEVEL_NAME[level], 0);
        }
        if (debug) text(BG_B, 25, 0, "DEBUG", 1);
    } else {
        text(BG_B, 4, 0, LEVEL_NAME[level], 1);
        text(BG_B, 17, 0, "FIRST TO", 0);
        hud[0] = ' '; put_num(hud + 1, win_target); text(BG_B, 25, 0, hud, 1);
    }
    /* left panel: player 1 */
    text(BG_B, 0, 3, CHAR_NAME[opt_char[0]], 1);
    item_icon(1, 5, T_ITEM_BOMB);
    item_icon(1, 9, T_ITEM_FIRE);
    item_icon(1, 13, T_ITEM_SHOE);
    hud_stats(0);
    if (nplayers == 1) {
        item_icon(1, 17, T_ITEM_LIFE);
        hud_lives();
        if (boss) {
            text(BG_B, 36, 3, "BOSS", 1);
            if (level == SEA) icon(37, 5, PAL3, S_SHARK, S_SHARK + 3, S_SHARK + 1, S_SHARK + 4);   /* the shark's head */
            else icon(37, 5, PAL3, S_BOSS, S_BOSS + 3, S_BOSS + 1, S_BOSS + 4);
            hud_boss();
        } else {
            text(BG_B, 36, 3, level == SEA ? "FISH" : "KRAX", 1);
            icon(37, 4, PAL2, MON_SPR, MON_SPR + 2, MON_SPR + 1, MON_SPR + 3);
            hud_krax();
        }
    } else {
        text(BG_B, 36, 3, CHAR_NAME[opt_char[1]], 1);
        item_icon(37, 5, T_ITEM_BOMB);
        item_icon(37, 9, T_ITEM_FIRE);
        item_icon(37, 13, T_ITEM_SHOE);
        hud_stats(1);
        text(BG_B, 0, 21, "WINS", 0); text(BG_B, 36, 21, "WINS", 0);
        hud_wins(0); hud_wins(1);
        if (opt_monsters) { icon(37, 17, PAL2, MON_SPR, MON_SPR + 2, MON_SPR + 1, MON_SPR + 3); }
    }
}

/* ---------- bombs and flames ---------- */
static void redraw_around(u8 ci) {
    if (FLAME(ci - 1)) draw_obj(ci - 1);
    if (FLAME(ci + 1)) draw_obj(ci + 1);
    if (FLAME(ci - GW)) draw_obj(ci - GW);
    if (FLAME(ci + GW)) draw_obj(ci + GW);
}

static void add_flame(u8 ci) {
    if (boss && fowner == 1) { if (!FLAME(ci)) bfire[ci] = 1; }
    else bfire[ci] = 0;
    if (!FLAME(ci)) SET_ITEM(ci, 0);
    flame[ci] = FLAME_TIME;
    draw_obj(ci);
    redraw_around(ci);
}

static u8 bpen;                  /* the bomb going off is a penetrator */
static void blast_line(u8 start, u8 range, u8 d) {
    u8 ci = start, n, t;
    for (n = 0; n < range; ++n) {
        ci += DSTEP[d];
        if (TYPE(ci) == CEMENT) return;
        if (TYPE(ci) == STONE) {
            t = cell[ci] & (TUFT | PEN | 0x0C);
            cell[ci] = FLOOR;
            draw_ground(ci);
            if (TYPE(ci + 1) == FLOOR) draw_ground(ci + 1);       /* its shadows go too */
            if (TYPE(ci + GW) == FLOOR) draw_ground(ci + GW);
            add_flame(ci);
            cell[ci] |= t | RUBBLE;
            if (bpen) continue;                 /* a penetrator blasts on through the stone */
            return;
        }
        if ((cell[ci] & RUBBLE) && FLAME(ci) && !bpen) { add_flame(ci); return; }   /* burning rubble stops it too */
        add_flame(ci);
        if (BOMB(ci)) b_fuse[bomb_at(ci)] = 1;
    }
}

static void explode(u8 b) {
    u8 ci = b_cell[b], r = b_range[b], d, o = b_owner[b];
    if (!b_used[b]) return;
    b_used[b] = 0;
    cell[ci] &= ~HAS_BOMB;
    if (pactive[o]) --pactive[o];
    fowner = o; bpen = b_pen[b];
    sfx_boom();
    add_flame(ci);
    for (d = 0; d < 4; ++d) blast_line(ci, r, d);
}

static void place_bomb(void) {
    u8 ci = pcy[pl] * GW + pcx[pl], k;
    if (!palive[pl] || pactive[pl] >= pbombs[pl] || BOMB(ci)) return;
    for (k = 0; k < MAX_BOMBS; ++k) if (!b_used[k]) break;
    if (k == MAX_BOMBS) return;
    b_used[k] = 1; b_cell[k] = ci; b_fuse[k] = FUSE; b_range[k] = pfire[pl]; b_owner[k] = pl; b_pen[k] = ppen[pl]; b_rem[k] = prem[pl];
    cell[ci] |= HAS_BOMB;
    ++pactive[pl];
    sfx_place();
    draw_obj(ci);
}

/* the remote: player p's bombs go off on the next fuse tick */
static void set_off(u8 p) {
    u8 k;
    for (k = 0; k < MAX_BOMBS; ++k) if (b_used[k] && b_owner[k] == p && b_rem[k]) b_fuse[k] = 1;
}

static void update_bombs(void) {
    u16 c;
    u8 k, flick = (frame_count & 3) == 0;
    if (flick) flame_phase ^= 1;
    for (k = 0; k < MAX_BOMBS; ++k)
        if (b_used[k]) {
            if ((!b_rem[k] || b_fuse[k] == 1) && --b_fuse[k] == 0) explode(k);   /* remote: only when set off */
            else if ((frame_count & 7) == 0 || (b_fuse[k] < 60 && b_fuse[k] % 5 == 0)) draw_obj(b_cell[k]);
        }
    for (c = 0; c < CELLS; ++c)
        if (flame[c]) {
            if (--flame[c] == 0) { cell[c] &= ~RUBBLE; draw_obj(c); redraw_around(c); }
            else if (flick || flame[c] == FLAME_LOW - 1) draw_obj(c);
        }
}

/* ---------- players ---------- */
static u8 can_go(u8 d) {
    u8 nx = pcx[pl] + DX[d], ny = pcy[pl] + DY[d];
    return walkable(pcy[pl] * GW + pcx[pl] + DSTEP[d])
        || (debug && nplayers == 1 && nx >= 1 && nx <= GW - 2 && ny >= 1 && ny <= GH - 2);
}

static u8 want_dir(void) {
    u16 p = pl ? pad2 : pad;
    u8 d;
    if (pbuft[pl] && can_go(pbuf[pl])) return pbuf[pl];
    for (d = 0; d < 4; ++d) if ((p & DBTN[d]) && d != pdir[pl] && can_go(d)) return d;
    for (d = 0; d < 4; ++d) if (p & DBTN[d]) return d;
    return 0xFF;
}

static void try_step(u8 d) {
    if (d == 0xFF) { pframe[pl] = 0; panim[pl] = 0; return; }
    pdir[pl] = d;
    if (can_go(d)) {
        pmoving[pl] = 1; pdx[pl] = DX[d]; pdy[pl] = DY[d]; pleft[pl] = 16;
        if (d == pbuf[pl]) pbuft[pl] = 0;
    }
}

static void steer(void) {
    u8 d = pbuf[pl];
    if (!pbuft[pl] || d == pdir[pl]) return;
    if (DX[d] == -pdx[pl] && DY[d] == -pdy[pl]) {
        pcx[pl] += pdx[pl]; pcy[pl] += pdy[pl];
        pdx[pl] = DX[d]; pdy[pl] = DY[d]; pleft[pl] = 16 - pleft[pl];
        pdir[pl] = d; pbuft[pl] = 0;
    } else if (pleft[pl] >= 11 && can_go(d)) {
        px[pl] = pcx[pl] << 4; py[pl] = pcy[pl] << 4;
        pdx[pl] = DX[d]; pdy[pl] = DY[d]; pleft[pl] = 16;
        pdir[pl] = d; pbuft[pl] = 0;
    }
}

static void collect(void) {
    u8 ci = pcy[pl] * GW + pcx[pl], t = ITEM(ci);
    if (!t || (pl && boss)) return;
    if (IS_LIFE(ci)) {
        if (lives < 99) ++lives;
        SET_ITEM(ci, 0); cell[ci] &= ~TUFT;
        draw_obj(ci);
        sfx_heart();
        hud_lives();
        return;
    }
    if (IS_PEN(ci)) ppen[pl] = 1;
    else if (IS_REM(ci)) prem[pl] = 1;
    else if (t == IT_SHOE && pups[pl] < MAX_SPEEDUPS) { ++pups[pl]; pspeed[pl] += 4; }
    else if (t == IT_FIRE && pfire[pl] < 99) ++pfire[pl];
    else if (t == IT_BOMB && pbombs[pl] < 99) ++pbombs[pl];
    SET_ITEM(ci, 0);
    draw_obj(ci);
    sfx_pickup();
    hud_stats(pl);
}

static void update_player(void) {
    u8 s, k;
    u16 n;
    if (!palive[pl]) { if (pdeath[pl]) --pdeath[pl]; return; }
    n = pl ? pad2_new : pad_new;
    if (prem[pl] && (n & K_REMOTE)) set_off(pl);
    else if (n & K_BOMB) ppending[pl] = 1;
    if (pbuft[pl]) --pbuft[pl];
    for (k = 0; k < 4; ++k) if (n & DBTN[k]) { pbuf[pl] = k; pbuft[pl] = 14; }
    if (pmoving[pl]) steer();
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

static void kill_player(u8 p) {
    if (debug && nplayers == 1) return;         /* debug mode: immortal */
    palive[p] = 0; pdeath[p] = 60; ppen[p] = 0; sfx_die();
    if (prem[p]) {                              /* the remote is lost: its bombs tick again */
        u8 k;
        prem[p] = 0;
        for (k = 0; k < MAX_BOMBS; ++k) if (b_used[k] && b_owner[k] == p && b_rem[k]) { b_rem[k] = 0; draw_obj(b_cell[k]); }
    }
}

/* ---------- the boss ---------- */
static u8 reaches(u8 b, u8 r, u8 ci) {
    u8 d, n, x;
    if (b == ci) return 1;
    for (d = 0; d < 4; ++d) {
        x = b;
        for (n = 0; n < r; ++n) {
            x += DSTEP[d];
            if (TYPE(x) != FLOOR) break;
            if (x == ci) return 1;
        }
    }
    return 0;
}

static u8 in_danger(u8 ci) {
    u8 b;
    if (FLAME(ci)) return 1;
    if (vb_on && reaches(vb_cell, pfire[1], ci)) return 1;
    for (b = 0; b < MAX_BOMBS; ++b)
        if (b_used[b] && reaches(b_cell[b], b_range[b], ci)) return 1;
    return 0;
}

static u8 boss_safe(u8 ci) { return walkable(ci) && !in_danger(ci); }

static u8 escape_dir(void) {
    u8 d, n, x, s, ci = pcy[1] * GW + pcx[1];
    for (d = 0; d < 4; ++d) {
        x = ci;
        for (n = 0; n < 5; ++n) {
            x += DSTEP[d];
            if (!walkable(x) || FLAME(x)) break;
            if (!in_danger(x)) return d;
            for (s = 0; s < 4; ++s)
                if ((s >> 1) != (d >> 1) && boss_safe(x + DSTEP[s])) return d;
        }
    }
    return 0xFF;
}

static u8 boss_think(void) {
    u8 ci = pcy[1] * GW + pcx[1], d, best = 0xFF, want;
    s8 dx, dy;
    vb_on = 0;
    if (in_danger(ci)) return escape_dir();
    dx = (s8)(pcx[0] - pcx[1]); dy = (s8)(pcy[0] - pcy[1]);
    if ((dx < 0 ? -dx : dx) > (dy < 0 ? -dy : dy)) want = dx < 0 ? 0 : 1;
    else want = dy < 0 ? 2 : 3;
    if (!bwait && pactive[1] < pbombs[1] &&
        ((palive[0] && reaches(ci, pfire[1], pcy[0] * GW + pcx[0])) ||
         TYPE(ci + DSTEP[want]) == STONE || rand8() < 6)) {
        vb_cell = ci; vb_on = 1;
        d = escape_dir();
        if (d != 0xFF) { place_bomb(); bwait = BOSS_REST[level]; return d; }
        vb_on = 0;
    }
    if (boss_safe(ci + DSTEP[want]) && rand8() < 200) return want;
    for (d = 0; d < 4; ++d)
        if (boss_safe(ci + DSTEP[d]) && (d != BACK[pdir[1]] || best == 0xFF) && (best == 0xFF || rand8() < 100)) best = d;
    return best;
}

static void update_boss(void) {
    u8 d, s;
    pl = 1;
    if (!palive[1]) { if (pdeath[1]) --pdeath[1]; return; }
    if (binv) --binv;
    if (bwait) --bwait;
    if (!pmoving[1]) {
        d = boss_think();
        if (d == 0xFF) { pframe[1] = 0; return; }
        pdir[1] = d; pdx[1] = DX[d]; pdy[1] = DY[d]; pmoving[1] = 1; pleft[1] = 16;
    }
    pfrac[1] += pspeed[1]; s = pfrac[1] >> 4; pfrac[1] &= 15;
    if (s > pleft[1]) s = pleft[1];
    px[1] += pdx[1] * (s8)s; py[1] += pdy[1] * (s8)s; pleft[1] -= s;
    if (++panim[1] >= 8) { panim[1] = 0; pframe[1] = (pframe[1] + 1) & 3; }
    if (pleft[1] == 0) { pmoving[1] = 0; pcx[1] = px[1] >> 4; pcy[1] = py[1] >> 4; }
}

static void hit_boss(void) {
    ++bhits; binv = 90; sfx_bosshit();
    if (bhits == BOSS_ANGRY[level]) {
        pspeed[1] = BOSS_SPEED[level] + 5; pbombs[1] = BOSS_BOMBS[level] + 1;
        PAL_setPalette(PAL3, PAL_SPRITES[PAL_ANGRY(level)], DMA);
    }
    if (bhits >= BOSS_HP[level]) { palive[1] = 0; pdeath[1] = 60; }
    hud_boss();
}

/* ---------- monsters ---------- */
static u8 monster_pick(u8 m) {
    u8 open[4], n = 0, fwd = 0, d, ci = mcy[m] * GW + mcx[m], nc, k;
    for (d = 0; d < 4; ++d) {
        nc = ci + DSTEP[d];
        if (walkable(nc) && !FLAME(nc)) { open[n++] = d; if (d == mdir[m]) fwd = 1; }
    }
    if (!n) return 0xFF;
    if (fwd && rand8() < 180) return mdir[m];
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
static u8 nspr;
static void spr(s16 x, s16 y, u8 size, u16 attr) {
    VDP_setSpriteFull(nspr, x, y, size, attr, nspr + 1);
    ++nspr;
}
static void spr_end(void) {
    if (!nspr) { VDP_setSpriteFull(0, -32, -32, SPRITE_SIZE(1, 1), 0, 0); nspr = 1; }
    else VDP_setSpriteLink(nspr - 1, 0);
    VDP_updateSprites(nspr, DMA_QUEUE);
    nspr = 0;
}

/* bomber frames: direction down 0, up 1, left 2 (right is left flipped); walk cycle */
static const u8 DIR_ROW[4] = { 2, 2, 1, 0 };
static const u8 WALK[4] = { 1, 0, 2, 0 };

static u8 shark_fl;              /* the shark faces right */

static void draw_bomber(u8 p) {
    u8 f, flip;
    u16 base, pal;
    if (!palive[p] && !(pdeath[p] & 4)) return;
    if (p && boss && palive[1] && (binv & 4)) return;
    if (p && boss && level == SEA) {            /* the shark: 4 x 3 tiles, tail swinging as it swims */
        if (pdir[1] < 2) shark_fl = pdir[1];
        f = pmoving[1] ? ((frame_count >> 3) & 1) : 0;
        spr(AX * 8 + px[1] - 8, AY * 8 + py[1] - 4, SPRITE_SIZE(4, 3),
            TILE_ATTR_FULL(PAL3, 0, 0, shark_fl, TB + S_SHARK + f * 12));
        return;
    }
    f = pmoving[p] ? WALK[pframe[p]] : 0;
    flip = pdir[p] == 1;
    base = (p && boss) ? S_BOSS : S_BOMBER;
    pal = p ? PAL3 : PAL2;
    spr(AX * 8 + px[p], AY * 8 + py[p] - 8, SPRITE_SIZE(2, 3),
        TILE_ATTR_FULL(pal, 0, 0, flip, TB + base + (DIR_ROW[pdir[p]] * 3 + f) * 6));
}

static void draw_sprites(void) {
    u8 m, f;
    /* the lower one on screen is in front */
    if (py[1] > py[0]) { draw_bomber(1); draw_bomber(0); }
    else { draw_bomber(0); draw_bomber(1); }
    for (m = 0; m < NMON; ++m) {
        if (!malive[m] && !(mdeath[m] & 4)) continue;
        f = mmoving[m] ? 1 + ((mbob[m] >> 3) & 1) : 0;
        spr(AX * 8 + mx[m], AY * 8 + my[m], SPRITE_SIZE(2, 2),
            TILE_ATTR_FULL(PAL2, 0, 0, mdir[m] == 1, TB + MON_SPR + f * 4));
    }
    spr_end();
}
static void hide_sprites(void) { nspr = 0; spr_end(); }

/* ---------- messages ---------- */
static u8 confetti;
static s16 cf_x[32], cf_y[32];

static void confetti_frame(void) {
    u8 k;
    nspr = 0;
    for (k = 0; k < 32; ++k) {
        cf_y[k] += 1 + (k & 1);
        if ((frame_count & 3) == 0) cf_x[k] += (k & 2) ? 1 : -1;
        if (cf_y[k] > 224) cf_y[k] = -8;
        spr(cf_x[k], cf_y[k], SPRITE_SIZE(1, 1), TILE_ATTR_FULL(PAL1, 1, 0, 0, TB + S_CONFETTI + k % 6));
    }
    spr_end();
}

/* a box over the arena with up to three lines; waits `frames` or for START (0) */
static void message(const char* a, const char* b, const char* c, u16 frames) {
    u8 k;
    box(AX + 2, 10, 28, 9);
    if (a) text_c(BG_A, 12, a, 1);
    if (b) text_c(BG_A, 14, b, 0);
    if (c) text_c(BG_A, 16, c, 0);
    if (confetti) for (k = 0; k < 32; ++k) { cf_x[k] = rand8() + 32; cf_y[k] = -(s16)(rand8() % 224); }
    pad = pad2 = 0xFFFF;
    for (;;) {
        frame();
        if (confetti) confetti_frame();
        if (frames) { if (--frames == 0) break; }
        else if ((pad_new | pad2_new) & K_START) break;
    }
    confetti = 0;
    clear_plane_a();
}

/* ---------- levels ---------- */
static void reset_player(u8 p, u8 cx, u8 cy, u8 keep) {
    pcx[p] = cx; pcy[p] = cy; px[p] = cx * 16; py[p] = cy * 16;
    pmoving[p] = 0; pdir[p] = 3; pframe[p] = 0; panim[p] = 0; pfrac[p] = 0; pbuft[p] = 0;
    palive[p] = 1; pdeath[p] = 0; pactive[p] = 0; ppending[p] = 0; pburned[p] = 0;
    if (!keep) { pspeed[p] = 16; pups[p] = 0; pfire[p] = 1; pbombs[p] = 1; ppen[p] = 0; prem[p] = 0; }
}

static const u8* level_song(void) {
    if (boss) return xgm_boss;
    switch (level) {
    case 0: return xgm_yard;
    case 1: return xgm_sand;
    case 2: return xgm_frost;
    case 3: return xgm_lava;
    case 4: return xgm_cloud;
    default: return xgm_sea;
    }
}

static void start_level(u8 keep) {
    u8 m;
    u16 k;
    SYS_disableInts();
    VDP_setEnable(FALSE);
    build_map();
    PAL_setPalette(PAL0, PAL_ARENA[LEVEL_PAL[level]], CPU);   /* the boss fights in its level's colours */
    PAL_setPalette(PAL2, PAL_SPRITES[opt_char[0]], CPU);
    PAL_setPalette(PAL3, PAL_SPRITES[boss ? PAL_BOSS(level) : opt_char[1]], CPU);
    clear_plane_a();
    reset_player(0, 1, 1, keep);
    palive[1] = 0; pdeath[1] = 0; py[1] = 0;
    if (nplayers == 2) reset_player(1, GW - 2, GH - 2, 0);
    if (boss) {
        reset_player(1, GW - 2, GH - 2, 0);
        pfire[1] = BOSS_FIRE_R[level]; pbombs[1] = BOSS_BOMBS[level]; pspeed[1] = BOSS_SPEED[level];
        bhits = 0; binv = 0; bwait = 90;
    }
    mspeed = MONSTER_SPEED[level];
    for (m = 0; m < NMON; ++m) {
        mcx[m] = (nplayers == 2 && !m) ? 1 : GW - 2; mcy[m] = m ? 1 : GH - 2;
        mx[m] = mcx[m] * 16; my[m] = mcy[m] * 16;
        mmoving[m] = 0; mdir[m] = 0; mfrac[m] = 0; mdeath[m] = 0; mwait[m] = 30; mbob[m] = 0;
        malive[m] = (nplayers == 1 && !boss) || (nplayers == 2 && opt_monsters);
    }
    secs = ROUND_SECS; subsec = 60; time_up = 0;
    draw_hud();
    for (k = 0; k < CELLS; ++k) draw_ground(k);
    hud_time();
    draw_sprites();
    VDP_setEnable(TRUE);
    SYS_enableInts();
    music(level_song());
}

static u8 play_level(void) {
    u8 m, kx, ky;
    for (;;) {
        frame();
        if ((pad_new | pad2_new) & K_START) {            /* pause */
            XGM2_pause();
            text(BG_A, AX + 13, 14, "PAUSE", 1);
            do { frame(); } while (!((pad_new | pad2_new) & K_START));
            for (kx = 0; kx < GW; ++kx) draw_obj(6 * GW + kx);     /* the row under the word */
            XGM2_resume();
        }

        for (pl = 0; pl < nplayers; ++pl) update_player();
        if (boss) update_boss();
        for (m = 0; m < NMON; ++m) update_monster(m);
        update_bombs();

        for (pl = 0; pl < nplayers; ++pl)
            if (palive[pl] && HOT(((py[pl] + 8) >> 4) * GW + ((px[pl] + 8) >> 4))) { pburned[pl] = 1; kill_player(pl); }
        kx = ((py[1] + 8) >> 4) * GW + ((px[1] + 8) >> 4);
        if (boss && palive[1] && !binv && HOT(kx) && !bfire[kx]) hit_boss();   /* its own fire can't hurt it */
        for (m = 0; m < NMON; ++m) {
            if (!malive[m]) continue;
            if (HOT(((my[m] + 8) >> 4) * GW + ((mx[m] + 8) >> 4))) {
                malive[m] = 0; mdeath[m] = 40; sfx_pickup(); if (nplayers == 1) hud_krax(); continue;
            }
            for (pl = 0; pl < nplayers; ++pl) {
                kx = px[pl] > mx[m] ? px[pl] - mx[m] : mx[m] - px[pl];
                ky = py[pl] > my[m] ? py[pl] - my[m] : my[m] - py[pl];
                if (palive[pl] && kx < 11 && ky < 11) kill_player(pl);
            }
        }
#ifdef TEST_CLEAR
        if (secs == ROUND_SECS - 2) { malive[0] = malive[1] = 0; }
#endif
        if ((palive[0] || palive[1]) && secs && --subsec == 0) {   /* stops at zero (debug mode lives on) */
            subsec = 60;
            if (--secs == 0) {
                time_up = 1;
                for (pl = 0; pl < nplayers; ++pl) if (palive[pl]) kill_player(pl);
            }
            if (secs == STRESS_SECS) XGM2_setMusicTempo(72);   /* hurry up */
            if (secs <= STRESS_SECS && secs) sfx_tick();
        }
        if (subsec == 60 || secs <= 10) hud_time();

        draw_sprites();

        if (nplayers == 1) {
            if (!palive[0] && pdeath[0] == 0) return R_DIED;
            if (palive[0] && !malive[0] && !malive[1] && !mdeath[0] && !mdeath[1] && !palive[1] && !pdeath[1]) return R_CLEARED;
        } else if (!pdeath[0] && !pdeath[1] && palive[0] + palive[1] <= 1) {
            return palive[0] ? R_P1 : palive[1] ? R_P2 : R_DRAW;
        }
    }
}

static const char* death_reason(void) {
    return time_up ? "TIME UP" : pburned[0] ? "CAUGHT IN THE BLAST" : level == SEA ? "A FISH GOT YOU" : "THE KRAX GOT YOU";
}

static void solo_game(void) {
    char next[20];
    level = 0; boss = rush;                     /* boss rush starts straight at the first boss */
    lives = WIN_CHOICES[opt_lives];
    start_level(0);
    if (rush) message("BOSS RUSH", BOSS_TAKES[0], "GET READY!", 100);
    else message("LEVEL 1", LEVEL_NAME[0], "GET READY!", 100);
    for (;;) {
        if (play_level() == R_CLEARED) {
            hide_sprites();
            if (boss && level == LEVELS - 1) {
                confetti = 1;
                jingle(xgm_victory);
                message("CONGRATULATIONS!", "YOU BEAT EVERY BOSS", "YOU WIN!  PRESS START", 0);
                boss = 0;
                return;
            }
            jingle(xgm_clear);
            if (!boss) {
                message("LEVEL CLEARED", "NEXT UP", "THE BOSS", 150);
                boss = 1;
            } else {
                message("BOSS DEFEATED", rush ? "NEXT BOSS" : "NEXT UP", LEVEL_NAME[level + 1], 150);
                boss = rush;
                ++level;
            }
            start_level(1);
            message(boss ? "BOSS FIGHT" : LEVEL_NUM[level],
                    boss ? BOSS_TAKES[level] : LEVEL_NAME[level], "GET READY!", 90);
        } else {
            hide_sprites();
            if (lives) --lives;
            hud_lives();
            if (!lives) {
                jingle(xgm_gameover);
                message(death_reason(), "GAME OVER", "PRESS START", 0);
                boss = 0;
                return;
            }
            music_stop();
            next[0] = 0;
            {
                char* s = next;
                put_num(s, lives);
                s = next + str_len(next);
                s[0] = ' '; s[1] = 'L'; s[2] = 'I'; s[3] = 'V'; s[4] = 'E'; s[5] = lives == 1 ? ' ' : 'S';
                s[6] = ' '; s[7] = 'L'; s[8] = 'E'; s[9] = 'F'; s[10] = 'T'; s[11] = 0;
            }
            message(death_reason(), "TRY AGAIN", next, 120);
            start_level(1);
        }
    }
}

static char score[20];
static void make_score(void) {
    char* s = score;
    *s++ = 'S'; *s++ = 'C'; *s++ = 'O'; *s++ = 'R'; *s++ = 'E'; *s++ = ' ';
    s = put_num(s, wins[0]); *s++ = '-'; put_num(s, wins[1]);
}

static void versus_game(void) {
    u8 r, w;
    level = opt_level; boss = 0;
    wins[0] = wins[1] = 0;
    start_level(0);
    message(LEVEL_NAME[level], opt_monsters ? "WATCH OUT FOR THE KRAX" : "BLAST YOUR FRIEND!", "GET READY!", 100);
    for (;;) {
        r = play_level();
        hide_sprites();
        if (r == R_DRAW) {
            make_score();
            music_stop();
            message(time_up ? "TIME UP" : "DRAW", "NOBODY SCORES", score, 120);
            start_level(0);
            continue;
        }
        w = r - R_P1;
        ++wins[w];
        hud_wins(w);
        make_score();
        if (wins[w] >= win_target) {
            confetti = 1;
            jingle(xgm_victory);
            message(w ? "PLAYER 2 WINS THE MATCH!" : "PLAYER 1 WINS THE MATCH!", score, "PRESS START", 0);
            return;
        }
        jingle(xgm_clear);
        message(w ? "PLAYER 2 WINS THE ROUND" : "PLAYER 1 WINS THE ROUND", score, 0, 150);
        start_level(0);
    }
}

/* ---------- title and options ---------- */
static void title_backdrop(void) {
    u16 k;
    SYS_disableInts();
    VDP_setEnable(FALSE);
    nplayers = nplayers ? nplayers : 1;
    boss = 0; level = 0;
    {   /* a fresh arena behind the menu */
        u8 n = nplayers;
        nplayers = 2;
        build_map();
        nplayers = n;
    }
    for (k = 0; k < CELLS; ++k) flame[k] = 0;
    PAL_setPalette(PAL0, PAL_ARENA[0], CPU);
    PAL_setPalette(PAL2, PAL_SPRITES[opt_char[0]], CPU);
    PAL_setPalette(PAL3, PAL_SPRITES[opt_char[1]], CPU);
    VDP_clearPlane(BG_B, TRUE);
    clear_plane_a();
    for (k = 0; k < CELLS; ++k) draw_ground(k);
    for (k = 0; k < CELLS; ++k) draw_obj(k);
    VDP_setEnable(TRUE);
    SYS_enableInts();
}

static void draw_logo(void) {
    u16 x, y;
    for (y = 0; y < LOGO_H; ++y)
        for (x = 0; x < LOGO_W; ++x) {
            u16 t = LOGO_MAP[y * LOGO_W + x];
            VDP_setTileMapXY(BG_A, t ? TILE_ATTR_FULL(PAL1, 1, 0, 0, TB + t) : 0, 2 + x, 2 + y);
        }
}

static void title_choice(void) {
    text(BG_A, 14, 13, nplayers == 1 && !rush ? ">" : " ", 1);
    text(BG_A, 14, 15, nplayers == 2 ? ">" : " ", 1);
    text(BG_A, 14, 17, rush ? ">" : " ", 1);
    text(BG_A, 10, 19, rush ? " BEAT ALL SIX BOSSES " : nplayers == 1 ? "6 LEVELS AND 6 BOSSES" : " BLAST YOUR FRIEND!  ", 0);
}

static void title_screen(void) {
    u8 walk = 0;
    s16 kx = -16;
    title_backdrop();
    draw_logo();
    box(8, 11, 24, 13);
    text(BG_A, 16, 13, "1 PLAYER", 0);
    text(BG_A, 16, 15, "2 PLAYERS", 0);
    text(BG_A, 16, 17, "BOSS RUSH", 0);
    text(BG_A, 13, 21, "PRESS START", 1);
    text(BG_A, 2, 26, "C: DEBUG MODE", 0);
    text(BG_A, 25, 26, "MGRAHN 2026", 0);
    title_choice();
    if (debug) text(BG_A, 16, 22, "DEBUG ON", 0);
    music(xgm_title);
    pad = pad2 = 0xFFFF;
    for (;;) {
        frame();
        /* a Krax chases a bomber along the bottom of the box */
        ++walk; kx += 1;
        if (kx > 330) kx = -48;
        nspr = 0;
        spr(kx + 24, 184, SPRITE_SIZE(2, 3), TILE_ATTR_FULL(PAL2, 0, 0, 1, TB + S_BOMBER + (2 * 3 + WALK[(walk >> 3) & 3]) * 6));
        spr(kx - 4, 192, SPRITE_SIZE(2, 2), TILE_ATTR_FULL(PAL2, 0, 0, 1, TB + S_KRAX + (1 + ((walk >> 3) & 1)) * 4));
        spr_end();
        if (pad_new & K_START) { sfx_select(); return; }
        if (pad_new & (K_UP | K_DOWN)) {         /* 1 player, 2 players, boss rush */
            u8 t = rush ? 2 : nplayers - 1;
            t = (pad_new & K_DOWN) ? (t == 2 ? 0 : t + 1) : (t ? t - 1 : 2);
            rush = t == 2; nplayers = t == 1 ? 2 : 1;
            title_choice(); sfx_menu();
        }
        if (pad_new & BUTTON_C) { debug ^= 1; text(BG_A, 16, 22, debug ? "DEBUG ON" : "        ", 0); sfx_menu(); }
    }
}

static const char* const LEVEL_PAD[LEVELS] = { "THE YARD  ", "SAND PIT  ", "FROST CAVE", "LAVA PEAK ", "CLOUD NINE", "DEEP SEA  " };
static u8 opt_row;

/* the chosen characters stand next to their names */
static void options_sprites(void) {
    u8 p;
    nspr = 0;
    for (p = 0; p < nplayers; ++p)
        spr(p ? 256 : 228, (nplayers == 1 ? 15 : 17 + p * 2) * 8 - 12, SPRITE_SIZE(2, 3),
            TILE_ATTR_FULL(p ? PAL3 : PAL2, 1, 0, 0, TB + S_BOMBER));
    spr_end();
}

static const char* const DIGIT[8] = { "0", "1", "2", "3", "4", "5", "6", "7" };

static void options_draw(void) {
    u8 r;
    if (nplayers == 1) {
        for (r = 0; r < 4; ++r) text(BG_A, 10, 11 + r * 2, opt_row == r ? ">" : " ", 1);
        text(BG_A, 22, 11, opt_lives == 0 ? "3 " : opt_lives == 1 ? "5 " : "10", 1);
        text(BG_A, 22, 13, DIGIT[opt_items], 1);
        text(BG_A, 22, 15, CHAR_NAME[opt_char[0]], 1);
        text(BG_A, 22, 17, debug ? "ON " : "OFF", 1);
        return;
    }
    for (r = 0; r < 6; ++r) text(BG_A, 10, 9 + r * 2, opt_row == r ? ">" : " ", 1);
    text(BG_A, 22, 9, LEVEL_PAD[opt_level], 1);
    text(BG_A, 22, 11, opt_monsters ? "ON " : "OFF", 1);
    text(BG_A, 22, 13, opt_wins == 0 ? "3 " : opt_wins == 1 ? "5 " : "10", 1);
    text(BG_A, 22, 15, DIGIT[opt_items], 1);
    text(BG_A, 22, 17, CHAR_NAME[opt_char[0]], 1);
    text(BG_A, 22, 19, CHAR_NAME[opt_char[1]], 1);
}

/* 1..7 power-ups of each kind, wrapping (step 1 forward, 2 back) */
static void next_items(u8 step) {
    opt_items = step == 1 ? (opt_items == 7 ? 1 : opt_items + 1) : (opt_items == 1 ? 7 : opt_items - 1);
}

/* the next character for player p (step 1 forward, 3 back), never the other player's */
static void next_char(u8 p, u8 step) {
    do opt_char[p] = (opt_char[p] + step) & 3;
    while (nplayers == 2 && opt_char[p] == opt_char[p ^ 1]);
    PAL_setPalette(p ? PAL3 : PAL2, PAL_SPRITES[opt_char[p]], DMA);
}

static u8 options_screen(void) {
    u8 rows = nplayers == 1 ? 4 : 6, t;
    clear_plane_a();
    box(6, 5, 28, 20);
    text_c(BG_A, 7, rush ? "BOSS RUSH OPTIONS" : nplayers == 1 ? "1 PLAYER OPTIONS" : "2 PLAYER OPTIONS", 1);
    if (nplayers == 1) {
        text(BG_A, 12, 11, "LIVES", 0); text(BG_A, 12, 13, "ITEMS", 0); text(BG_A, 12, 15, "PLAYER", 0);
        text(BG_A, 12, 17, "DEBUG", 0);         /* walk through walls and never die */
    }
    else {
        text(BG_A, 12, 9, "LEVEL", 0);
        text(BG_A, 12, 11, "MONSTERS", 0);
        text(BG_A, 12, 13, "WINS", 0);
        text(BG_A, 12, 15, "ITEMS", 0);
        text(BG_A, 12, 17, "P1", 0);
        text(BG_A, 12, 19, "P2", 0);
        if (opt_char[0] == opt_char[1]) next_char(1, 1);
    }
    text(BG_A, 10, 21, "UP/DOWN  CHOOSE", 0);
    text(BG_A, 10, 22, "LEFT/RIGHT  CHANGE", 0);
    text(BG_A, 10, 23, "START PLAY  B BACK", 0);
    opt_row = 0;
    options_draw();
    options_sprites();
    pad = pad2 = 0xFFFF;
    for (;;) {
        frame();
        if (pad_new & K_START) { win_target = WIN_CHOICES[opt_wins]; sfx_select(); return 1; }
        if (pad_new & BUTTON_B) { sfx_menu(); return 0; }
        if (pad_new & K_UP) opt_row = opt_row ? opt_row - 1 : rows - 1;
        else if (pad_new & K_DOWN) opt_row = opt_row == rows - 1 ? 0 : opt_row + 1;
        else if (pad_new & (K_LEFT | K_RIGHT | BUTTON_A | BUTTON_C)) {
            t = (pad_new & K_LEFT) ? 2 : 1;
            if (nplayers == 1) {
                if (opt_row == 0) opt_lives = (opt_lives + t) % 3;
                else if (opt_row == 1) next_items(t);
                else if (opt_row == 2) next_char(0, t == 2 ? 3 : 1);
                else debug ^= 1;
            }
            else if (opt_row == 0) { opt_level = (opt_level + (t == 2 ? LEVELS - 1 : 1)) % LEVELS; PAL_setPalette(PAL0, PAL_ARENA[LEVEL_PAL[opt_level]], DMA); }
            else if (opt_row == 1) opt_monsters ^= 1;
            else if (opt_row == 2) opt_wins = (opt_wins + t) % 3;
            else if (opt_row == 3) next_items(t);
            else next_char(opt_row - 4, t == 2 ? 3 : 1);
        } else continue;
        sfx_menu();
        options_draw();
    }
}

int main(bool hard) {
    (void)hard;
    VDP_setScreenWidth320();
    VDP_setPlaneSize(64, 32, TRUE);
    VDP_setBackgroundColor(0);
    VDP_loadTileData(GFX_TILES, TB, NTILES, DMA);
    PAL_setPalette(PAL1, PAL_ITEMS, CPU);
    PAL_setPalette(PAL2, PAL_SPRITES[0], CPU);
    XGM2_loadDriver(TRUE);
    nplayers = 1;
    for (;;) {
        title_screen();
        rng ^= frame_count; rng2 ^= frame_count >> 3;
        if (!rng) rng = 1;
        if (options_screen()) {
            if (nplayers == 1) solo_game();
            else versus_game();
        }
    }
    return 0;
}
