"""Minimal headless libretro frontend for testing: step frames, press buttons,
grab screenshots, read memory and save states."""
import ctypes as C
import numpy as np

# libretro joypad ids
B, Y, SELECT, START, UP, DOWN, LEFT, RIGHT, A, X, L, R = range(12)

MEM_SAVE_RAM, MEM_RTC, MEM_SYSTEM_RAM, MEM_VIDEO_RAM = 0, 1, 2, 3


class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p), ("size", C.c_size_t), ("meta", C.c_char_p)]


class Variable(C.Structure):
    _fields_ = [("key", C.c_char_p), ("value", C.c_char_p)]


ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
AUDIO_BATCH = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL = C.CFUNCTYPE(None)
STATE = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


class Core:
    def __init__(self, core_path, rom_path, variables=None):
        self.lib = C.CDLL(core_path)
        self.fmt = 0                      # 0 = 0RGB1555, 1 = XRGB8888, 2 = RGB565
        self.frame = None
        self.buttons = [0, 0]             # bitmask per port, bit n = joypad id n
        self.variables = {k.encode(): C.c_char_p(v.encode()) for k, v in (variables or {}).items()}
        self.audio = None                 # set to a list to collect stereo int16 samples
        self._cbs = [ENV(self._env), VIDEO(self._video), AUDIO(self._sample),
                     AUDIO_BATCH(self._batch), POLL(lambda: None), STATE(self._state)]
        L = self.lib
        L.retro_set_environment(self._cbs[0])
        L.retro_set_video_refresh(self._cbs[1])
        L.retro_set_audio_sample(self._cbs[2])
        L.retro_set_audio_sample_batch(self._cbs[3])
        L.retro_set_input_poll(self._cbs[4])
        L.retro_set_input_state(self._cbs[5])
        L.retro_init()
        self.rom = open(rom_path, "rb").read()
        self._rombuf = C.create_string_buffer(self.rom, len(self.rom))
        info = GameInfo(rom_path.encode(), C.cast(self._rombuf, C.c_void_p), len(self.rom), None)
        L.retro_load_game.restype = C.c_bool
        if not L.retro_load_game(C.byref(info)):
            raise RuntimeError("retro_load_game failed")
        L.retro_get_memory_data.restype = C.c_void_p
        L.retro_get_memory_size.restype = C.c_size_t
        L.retro_serialize_size.restype = C.c_size_t
        L.retro_serialize.restype = C.c_bool
        L.retro_unserialize.restype = C.c_bool

    def _env(self, cmd, data):
        cmd &= 0xFFFF
        if cmd == 10:                     # SET_PIXEL_FORMAT
            self.fmt = C.cast(data, C.POINTER(C.c_int))[0]
            return True
        if cmd == 3:                      # GET_CAN_DUPE
            C.cast(data, C.POINTER(C.c_bool))[0] = True
            return True
        if cmd == 15:                     # GET_VARIABLE
            v = C.cast(data, C.POINTER(Variable))[0]
            if v.key in self.variables:
                C.cast(data, C.POINTER(Variable))[0].value = self.variables[v.key]
                return True
            return False
        return False

    def _video(self, data, w, h, pitch):
        if not data:
            return
        if self.fmt == 1:
            a = np.ctypeslib.as_array(C.cast(data, C.POINTER(C.c_uint8)), (h * pitch,))
            a = a.reshape(h, pitch)[:, :w * 4].reshape(h, w, 4)
            self.frame = a[:, :, [2, 1, 0]].copy()
        else:
            a = np.ctypeslib.as_array(C.cast(data, C.POINTER(C.c_uint16)), (h * pitch // 2,))
            a = a.reshape(h, pitch // 2)[:, :w].astype(np.uint32)
            if self.fmt == 2:
                r, g, b = (a >> 11) & 31, (a >> 5) & 63, a & 31
                self.frame = np.dstack([r * 255 // 31, g * 255 // 63, b * 255 // 31]).astype(np.uint8)
            else:
                r, g, b = (a >> 10) & 31, (a >> 5) & 31, a & 31
                self.frame = (np.dstack([r, g, b]) * 255 // 31).astype(np.uint8)

    def _sample(self, l, r):
        if self.audio is not None:
            self.audio.append(np.array([l, r], np.int16))

    def _batch(self, data, frames):
        if self.audio is not None and data:
            self.audio.append(np.ctypeslib.as_array(C.cast(data, C.POINTER(C.c_int16)), (frames * 2,)).copy())
        return frames

    def sample_rate(self):
        class Timing(C.Structure):
            _fields_ = [("fps", C.c_double), ("rate", C.c_double)]

        class Geometry(C.Structure):
            _fields_ = [("bw", C.c_uint), ("bh", C.c_uint), ("mw", C.c_uint), ("mh", C.c_uint), ("ar", C.c_float)]

        class AVInfo(C.Structure):
            _fields_ = [("geometry", Geometry), ("timing", Timing)]
        info = AVInfo()
        self.lib.retro_get_system_av_info(C.byref(info))
        return info.timing.rate

    def save_wav(self, path):
        import wave
        data = np.concatenate(self.audio).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(int(round(self.sample_rate())))
            w.writeframes(data.tobytes())

    def _state(self, port, device, index, id_):
        if port < 2 and device == 1:
            return (self.buttons[port] >> id_) & 1
        return 0

    def run(self, frames=1, *pressed, port=0):
        mask = 0
        for b in pressed:
            mask |= 1 << b
        self.buttons[port] = mask
        for _ in range(frames):
            self.lib.retro_run()
        self.buttons[port] = 0
        return self.frame

    def tap(self, *pressed, port=0, hold=3, after=5):
        self.run(hold, *pressed, port=port)
        return self.run(after)

    def memory(self, kind=MEM_SYSTEM_RAM):
        p = self.lib.retro_get_memory_data(kind)
        n = self.lib.retro_get_memory_size(kind)
        return bytes(C.string_at(p, n)) if p and n else b""

    def save_state(self):
        n = self.lib.retro_serialize_size()
        buf = C.create_string_buffer(n)
        assert self.lib.retro_serialize(buf, n)
        return buf.raw

    def load_state(self, s):
        assert self.lib.retro_unserialize(C.create_string_buffer(s, len(s)), len(s))

    def screenshot(self, path):
        from PIL import Image
        Image.fromarray(self.frame).save(path)


HOOK = C.CFUNCTYPE(None, C.c_uint32, C.c_uint32, C.c_uint32, C.c_uint32)


class Tracer:
    """Hooks into the patched FCEUmm core (rt_* symbols): callbacks on CPU reads/writes
    at or above given addresses, and a per-PC execution counter."""

    def __init__(self, core):
        self.lib = core.lib
        self.hook_ptr = C.c_void_p.in_dll(self.lib, "rt_hook")
        self.read_min = C.c_uint32.in_dll(self.lib, "rt_read_min")
        self.write_min = C.c_uint32.in_dll(self.lib, "rt_write_min")
        self.count = C.c_int.in_dll(self.lib, "rt_count_pcs")
        self.hits = (C.c_uint32 * 0x80000).in_dll(self.lib, "rt_pc_hits")
        self.events = []
        self._cb = HOOK(lambda pc, a, v, k: self.events.append((pc, a, v, k)))

    def start(self, read_min=0x10000, write_min=0x10000):
        self.events = []
        self.read_min.value = read_min
        self.write_min.value = write_min
        self.hook_ptr.value = C.cast(self._cb, C.c_void_p).value

    def stop(self):
        self.hook_ptr.value = None
        return self.events

    def count_pcs(self, on=True):
        if on:
            C.memset(self.hits, 0, C.sizeof(self.hits))
        self.count.value = int(on)

    def pc_hits(self):
        return np.ctypeslib.as_array(self.hits).copy()


def poke(core, addr, value, kind=MEM_SYSTEM_RAM):
    p = core.lib.retro_get_memory_data(kind)
    C.cast(p, C.POINTER(C.c_uint8))[addr] = value


class MDRam:
    """Read Genesis work RAM (0xFF0000-0xFFFFFF) from Genesis Plus GX, which stores it
    as little-endian 16-bit words, using the addresses in SGDK's out/symbol.txt."""

    def __init__(self, core, symbol_file="out/symbol.txt"):
        self.core = core
        self.sym = {}
        for line in open(symbol_file):
            parts = line.split()
            if len(parts) == 3:
                self.sym[parts[2]] = int(parts[0], 16) & 0xFFFF

    def byte(self, addr):
        ram = self.core.memory()
        return ram[addr ^ 1]

    def read(self, addr, n):
        ram = self.core.memory()
        return bytes(ram[(addr + i) ^ 1] for i in range(n))

    def s16(self, addr):
        v = int.from_bytes(self.read(addr, 2), "big")
        return v - 0x10000 if v & 0x8000 else v

    def s32(self, addr):
        v = int.from_bytes(self.read(addr, 4), "big")
        return v - (1 << 32) if v & 0x80000000 else v

    def addr(self, name):
        return self.sym[name]
