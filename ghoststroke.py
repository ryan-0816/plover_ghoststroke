import os
from plover.steno import Stroke
from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR

class GhostStroke:
    # Use a simple log path first for testing
    fname = os.path.join(CONFIG_DIR, 'ghoststroke.txt')

    def __init__(self, engine: StenoEngine) -> None:
        super().__init__()
        self.engine: StenoEngine = engine
        self._processing = False
        self.f = None

    def start(self) -> None:
        # Make sure the config directory exists
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            self.f = open(self.fname, 'a', encoding='utf-8')
            self.f.write("=== GhostStroke plugin started ===\n")
            self.f.write(f"Logging to: {self.fname}\n")
            self.f.flush()
        except Exception as e:
            print(f"[GhostStroke] Failed to open log file: {e}")
            self.f = None

        self.engine.hook_connect('translated', self.on_translated)
        if self.f:
            self.f.write("Hook connected to 'translated'\n")
            self.f.flush()

    def stop(self) -> None:
        self.engine.hook_disconnect('translated', self.on_translated)
        if self.f:
            self.f.write("=== GhostStroke plugin stopped ===\n")
            self.f.close()
            self.f = None

    def on_translated(self, old, new):
        if not self.f:
            return

        try:
            self.f.write(f"on_translated called: old={old}, new={new}\n")
            self.f.flush()

            if self._processing:
                self.f.write("Skipping: already processing\n")
                self.f.flush()
                return

            if not new:
                self.f.write("Skipping: new is empty\n")
                self.f.flush()
                return

            last = new[-1]

            # Only process untranslated strokes
            if last.english:
                self.f.write("Skipping: last translation is not empty\n")
                self.f.flush()
                return

            strokes = last.rtfcre  # list of stroke strings

            # Check if any stroke contains both F and P
            has_fp = any('F' in s and 'P' in s for s in strokes)
            if not has_fp:
                self.f.write(f"No FP strokes found: {strokes}\n")
                self.f.flush()
                return

            self.f.write(f"Found FP stroke: {strokes}\n")
            self.f.flush()

            # Remove F and P from strokes
            new_strokes = []
            for stroke_str in strokes:
                if 'F' in stroke_str and 'P' in stroke_str:
                    new_str = stroke_str.replace('F', '').replace('P', '')
                    if not new_str or new_str == '-':
                        self.f.write(f"Cannot handle empty stroke after removal: {stroke_str}\n")
                        self.f.flush()
                        return
                    new_strokes.append(new_str)
                else:
                    new_strokes.append(stroke_str)

            # Lookup in dictionaries
            stroke_objs = tuple(Stroke.from_steno(s) for s in new_strokes)
            result = self.engine.dictionaries.lookup(stroke_objs)

            if result:
                self.f.write(f"Found translation: {result}\n")
                self.f.flush()
                self._processing = True
                try:
                    # Remove the untranslated stroke output
                    for _ in range(len(strokes)):
                        self.engine.output.send_backspaces(1)
                    # Send our translation
                    self.engine.output.send_string(result + '.')
                finally:
                    self._processing = False
            else:
                self.f.write(f"No translation found for: {new_strokes}\n")
                self.f.flush()

        except Exception as e:
            self.f.write(f"on_translated error: {e}\n")
            self.f.flush()
