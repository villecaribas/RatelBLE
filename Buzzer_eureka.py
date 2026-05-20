from machine import Pin, PWM
import time

try:
    import _thread
except ImportError:
    _thread = None


MEGALOVANIA = (
    "D,D,D6,P,A,8P,G#,P,G,P,F,P,D,F,G,"
    "C,C,D6,P,A,8P,G#,P,G,P,F,P,D,F,G,"
    "B4,B4,D6,P,A,8P,G#,P,G,P,F,P,D,F,G,"
    "A#4,A#4,D6,P,A,8P,G#,P,G,P,F,P,D,F,G"
)

STARWARS = (
    "32P,32F#,32F#,32F#,8B.,8F#6.,32E6,32D#6,32C#6,8B6.,16F#6.,"
    "32E6,32D#6,32C#6,8B6.,16F#6.,32E6,32D#6,32E6,8C#6.,"
    "32F#,32F#,32F#,8B.,8F#6.,32E6,32D#6,32C#6,8B6.,16F#6.,"
    "32E6,32D#6,32C#6,8B6.,16F#6.,32E6,32D#6,32E6,8C#6"
)

IMPOSSIBLEMISSION = (
    "32D,32D#,32D,32D#,32D,32D#,32D,32D#,32D,32D,32D#,32E,32F,32F#,32G,"
    "G,8P,G,8P,A#,P,C7,P,G,8P,G,8P,F,P,F#,P,G,8P,G,8P,A#,P,C7,P,G,8P,G,8P,"
    "F,P,F#,P,A#,G,2D,32P,A#,G,2C#,32P,A#,G,2C,A#5,8C,2P,32P,A#5,G5,2F#,"
    "32P,A#5,G5,2F,32P,A#5,G5,2E,D#,8D"
)

musicas = {
    "megalovania": {
        "notes": MEGALOVANIA,
        "bpm": 120,
        "default_dur": 16,
        "default_oct": 5,
    },
    "starwars": {
        "notes": STARWARS,
        "bpm": 45,
        "default_dur": 4,
        "default_oct": 5,
    },
    "impossiblemission": {
        "notes": IMPOSSIBLEMISSION,
        "bpm": 95,
        "default_dur": 16,
        "default_oct": 6,
    },
}


class BuzzerPTK:
    DUTY = 30000
    SLICE_MS = 20
    NOTES = {
        "c": 262,
        "d": 294,
        "e": 330,
        "f": 349,
        "g": 392,
        "a": 440,
        "b": 494,
        "c#": 277,
        "d#": 311,
        "f#": 370,
        "g#": 415,
        "a#": 466,
    }

    def __init__(self, pin):
        self.pwm = PWM(Pin(pin))
        self.pwm.duty_u16(0)
        self._stop = True
        self._pid = 0

    def stop(self):
        self._stop = True
        self._pid += 1
        self.pwm.duty_u16(0)

    @staticmethod
    def _octave_freq(base, octave):
        if base == 0:
            return 0
        if octave >= 4:
            return base << (octave - 4)
        return base >> (4 - octave)

    def _alive(self, pid):
        return not self._stop and pid == self._pid

    def _sleep_ms(self, ms, pid):
        while ms > 0 and self._alive(pid):
            step = min(ms, self.SLICE_MS)
            time.sleep_ms(step)
            ms -= step
        return self._alive(pid)

    def _tone(self, freq, ms, pid):
        if not self._alive(pid):
            return False

        if freq:
            self.pwm.freq(freq)
            self.pwm.duty_u16(self.DUTY)
        else:
            self.pwm.duty_u16(0)

        ok = self._sleep_ms(ms, pid)

        if pid == self._pid:
            self.pwm.duty_u16(0)

        return ok

    def _run(self, notes_str, bpm, default_dur, default_oct, pid):
        whole_ms = 240000 // bpm

        try:
            for tok in notes_str.split(","):
                if not self._alive(pid):
                    break

                tok = tok.strip()
                if not tok:
                    continue

                dur = default_dur
                octv = default_oct
                freq = 0
                i = 0

                j = i
                while j < len(tok) and tok[j].isdigit():
                    j += 1
                if j > i:
                    dur = int(tok[i:j])
                    i = j

                if i < len(tok) and tok[i].lower() == "p":
                    i += 1
                else:
                    if i < len(tok):
                        if i + 1 < len(tok) and tok[i + 1] == "#":
                            key = tok[i:i + 2].lower()
                            i += 2
                        else:
                            key = tok[i].lower()
                            i += 1

                        base = self.NOTES.get(key, 0)

                        j = i
                        while j < len(tok) and tok[j].isdigit():
                            j += 1
                        if j > i:
                            octv = int(tok[i:j])
                            i = j

                        freq = self._octave_freq(base, octv)

                dotted = i < len(tok) and tok[i] == "."
                note_ms = whole_ms // dur
                if dotted:
                    note_ms = note_ms * 3 // 2

                if not self._tone(freq, note_ms, pid):
                    break
        finally:
            if pid == self._pid:
                self.pwm.duty_u16(0)
                self._stop = True

    def _resolve_song(self, notes, bpm, default_dur, default_oct):
        config = musicas.get(notes)
        if config is None:
            return notes, bpm, default_dur, default_oct

        return (
            config["notes"],
            config["bpm"],
            config["default_dur"],
            config["default_oct"],
        )

    def play(self, notes=MEGALOVANIA, bpm=120, default_dur=16, default_oct=5):
        notes, bpm, default_dur, default_oct = self._resolve_song(
            notes, bpm, default_dur, default_oct
        )

        self.stop()
        self._stop = False
        self._pid += 1
        pid = self._pid

        print(f"\033[1;36mTocando: {notes[:30]}{'...' if len(notes) > 30 else ''}\033[0m")

        args = (notes, bpm, default_dur, default_oct, pid)
        if _thread:
            try:
                _thread.start_new_thread(self._run, args)
                return
            except Exception:
                pass

        self._run(*args)



if __name__ == "__main__":
    buzzer = BuzzerPTK(pin=15)
    buzzer.play()
