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
        os.makedirs(CONFIG_DIR, exist_ok=True)

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
        """Process Action objects and detect FP strokes using original chord data."""
        if not self.f:
            return

        try:
            self.f.write(f"[{datetime.now().strftime('%F %T')}] on_translated fired! new={new}\n")
            self.f.flush()

            for action in reversed(new):
                # Use the original strokes (steno_list) instead of text
                strokes = getattr(action, 'steno_list', None)
                if not strokes:
                    continue

                # Convert each stroke object to its steno string
                stroke_strs = [s.steno for s in strokes]

                self.f.write(f"[{datetime.now().strftime('%F %T')}] Processing strokes: {stroke_strs}\n")
                self.f.flush()

                if self._processing:
                    self.f.write("Skipping: already processing\n")
                    self.f.flush()
                    continue

                # Check if any stroke contains both F and P
                has_fp = any('F' in s and 'P' in s for s in stroke_strs)
                if not has_fp:
                    continue

                self.f.write(f"Found FP stroke: {stroke_strs}\n")
                self.f.flush()

                # Remove F and P from strokes
                cleaned_strokes = []
                for s in stroke_strs:
                    if 'F' in s and 'P' in s:
                        cleaned = s.replace('F', '').replace('P', '')
                        if not cleaned.strip():
                            self.f.write(f"Cannot handle empty stroke after removal: {s}\n")
                            self.f.flush()
                            continue
                        cleaned_strokes.append(cleaned)
                    else:
                        cleaned_strokes.append(s)

                try:
                    # Convert cleaned steno strings to Stroke objects
                    stroke_objs = tuple(Stroke.from_steno(s) for s in cleaned_strokes)
                    result = self.engine.dictionaries.lookup(stroke_objs)
                except Exception as e:
                    self.f.write(f"Error converting strokes for lookup: {e}\n")
                    self.f.flush()
                    continue

                if result:
                    self.f.write(f"Found translation: {result}\n")
                    self.f.flush()
                    self._processing = True
                    try:
                        # Remove the untranslated output
                        for _ in range(len(stroke_strs)):
                            self.engine.output.send_backspaces(1)
                        # Send the correct translation
                        self.engine.output.send_string(result + '.')
                    finally:
                        self._processing = False
                else:
                    self.f.write(f"No translation found for cleaned strokes: {cleaned_strokes}\n")
                    self.f.flush()

        except Exception as e:
            self.f.write(f"on_translated error: {e}\n")
            self.f.flush()
