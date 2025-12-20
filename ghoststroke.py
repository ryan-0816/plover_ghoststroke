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
        self.f = open(self.fname, 'a', encoding='utf-8')
        self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin started ===\n")
        self.f.flush()
        self.engine.hook_connect('translated', self.on_translated)
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Hook connected to 'translated'\n")
        self.f.flush()

    def stop(self) -> None:
        self.engine.hook_disconnect('translated', self.on_translated)
        self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin stopped ===\n")
        self.f.close()
        self.f = None

    def on_translated(self, old, new):
        if self._processing or not self.f:
            return

        for action in new:
            text = getattr(action, 'text', '')
            if not text:
                continue

            self.f.write(f"[{datetime.now().strftime('%F %T')}] Processing action: {text}\n")
            self.f.flush()

            # Detect exact "FP" substring in the chord
            if "FP" not in text:
                continue

            self.f.write(f"Found exact FP in chord: {text}\n")
            self.f.flush()

            # Remove the exact substring "FP"
            cleaned = text.replace('FP', '')
            if not cleaned:
                self.f.write("Chord empty after FP removal, skipping\n")
                self.f.flush()
                continue

            try:
                stroke_obj = Stroke.from_steno(cleaned)
                result = self.engine.dictionaries.lookup((stroke_obj,))
            except Exception as e:
                self.f.write(f"Error converting strokes for lookup: {e}\n")
                self.f.flush()
                continue

            if result:
                self.f.write(f"Translation found: {result}\n")
                self.f.flush()
                self._processing = True
                try:
                    # Remove original untranslated output
                    for _ in range(len(text)):
                        self.engine.output.send_backspaces(1)
                    # Send the translation
                    self.engine.output.send_string(result + '.')
                finally:
                    self._processing = False
