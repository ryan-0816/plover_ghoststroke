import os
from datetime import datetime

from plover.steno import Stroke
from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR

class GhostStroke:
    fname = os.path.join(CONFIG_DIR, 'ghoststroke.txt')

    def __init__(self, engine: StenoEngine) -> None:
        super().__init__()
        self.engine: StenoEngine = engine
        self._processing = False
        self.f = None

    def start(self) -> None:
        # Ensure config directory exists
        os.makedirs(CONFIG_DIR, exist_ok=True)

        # Open log file
        try:
            self.f = open(self.fname, 'a', encoding='utf-8')
            self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin started ===\n")
            self.f.flush()
        except Exception as e:
            print(f"[GhostStroke] Failed to open log file: {e}")
            self.f = None

        # Hook translated event on engine (correct for Plover 4+)
        self.engine.hook_connect('translated', self.on_translated)
        if self.f:
            self.f.write(f"[{datetime.now().strftime('%F %T')}] Hook connected to 'translated' on engine\n")
            self.f.flush()

    def stop(self) -> None:
        # Disconnect hook
        self.engine.hook_disconnect('translated', self.on_translated)
        if self.f:
            self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin stopped ===\n")
            self.f.close()
            self.f = None

    def on_translated(self, old, new):
        """Called after translation; logs strokes and applies FP detection/replacement."""
        if not self.f:
            return

        try:
            # Minimal log to confirm hook firing
            self.f.write(f"[{datetime.now().strftime('%F %T')}] on_translated fired! new={new}\n")
            self.f.flush()

            for phrase in reversed(new):
                strokes = getattr(phrase, 'rtfcre', None)
                if not strokes:
                    continue

                self.f.write(f"[{datetime.now().strftime('%F %T')}] Received strokes: {strokes}\n")
                self.f.flush()

                if self._processing:
                    self.f.write("Skipping: already processing\n")
                    self.f.flush()
                    continue

                # Check for strokes containing both F and P
                has_fp = any('F' in s and 'P' in s for s in strokes)
                if not has_fp:
                    continue

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
                            continue
                        new_strokes.append(new_str)
                    else:
                        new_strokes.append(stroke_str)

                # Lookup translation
                stroke_objs = tuple(Stroke.from_steno(s) for s in new_strokes)
                result = self.engine.dictionaries.lookup(stroke_objs)

                if result:
                    self.f.write(f"Found translation: {result}\n")
                    self.f.flush()
                    self._processing = True
                    try:
                        # Remove untranslated output
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
