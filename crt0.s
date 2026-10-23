; Bomb Yard NES - start-up code and NMI handler (ca65)
;
; The C code fills a small "VRAM update buffer" and the OAM shadow at $0200,
; then sets _nmi_ready. The NMI copies both to the PPU during vblank.
; Buffer format: [len, addr_hi, addr_lo, len bytes...]* 0

        .export     __STARTUP__ : absolute = 1
        .import     _main, copydata
        .importzp   c_sp
        .import     _nmi_ready, _ppu_ctrl, _ppu_mask, _frame_count, _vram_buf

PPUCTRL   = $2000
PPUMASK   = $2001
PPUSTATUS = $2002
OAMADDR   = $2003
PPUSCROLL = $2005
PPUADDR   = $2006
PPUDATA   = $2007
OAMDMA    = $4014

.segment "HEADER"
        .byte   "NES", $1A
        .byte   2               ; 2 x 16 KB PRG-ROM
        .byte   1               ; 1 x 8 KB CHR-ROM
        .byte   %00000001       ; mapper 0, vertical mirroring
        .byte   0
        .byte   0,0,0,0,0,0,0,0

.segment "STARTUP"
reset:
        sei
        cld
        ldx     #$40
        stx     $4017           ; no APU frame IRQ
        ldx     #$FF
        txs
        inx                     ; x = 0
        stx     PPUCTRL
        stx     PPUMASK
        stx     $4010           ; no DMC IRQ

        bit     PPUSTATUS
@vb1:   bit     PPUSTATUS
        bpl     @vb1

        lda     #0              ; clear RAM
@clr:   sta     $0000,x
        sta     $0100,x
        sta     $0300,x
        sta     $0400,x
        sta     $0500,x
        sta     $0600,x
        sta     $0700,x
        inx
        bne     @clr
        lda     #$FF            ; hide all sprites
@oam:   sta     $0200,x
        inx
        bne     @oam

@vb2:   bit     PPUSTATUS
        bpl     @vb2

        lda     #<$0800         ; C software stack grows down from $0800
        sta     c_sp
        lda     #>$0800
        sta     c_sp+1

        jsr     copydata        ; initialised C data -> RAM
        jmp     _main

nmi:
        pha
        txa
        pha
        tya
        pha

        lda     _nmi_ready
        beq     @skip

        lda     #0              ; sprites
        sta     OAMADDR
        lda     #$02
        sta     OAMDMA

        ldx     #0              ; background updates
@next:  ldy     _vram_buf,x
        beq     @done
        lda     PPUSTATUS
        lda     _vram_buf+1,x
        sta     PPUADDR
        lda     _vram_buf+2,x
        sta     PPUADDR
        inx
        inx
        inx
@copy:  lda     _vram_buf,x
        sta     PPUDATA
        inx
        dey
        bne     @copy
        beq     @next
@done:
        lda     #0
        sta     _nmi_ready
        lda     _ppu_ctrl
        sta     PPUCTRL
        lda     #0
        sta     PPUSCROLL
        sta     PPUSCROLL
        lda     _ppu_mask
        sta     PPUMASK
@skip:
        inc     _frame_count

        pla
        tay
        pla
        tax
        pla
irq:
        rti

.segment "VECTORS"
        .word   nmi, reset, irq

.segment "CHARS"
        .incbin "chr.bin"
