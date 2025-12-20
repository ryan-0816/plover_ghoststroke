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

        # Correct hook for Plover 4+
        self.engine.hook_connect('translated', self.on_translated)
        if self.f:
            self.f.write(f"[{datetime.now().strftime('%F %T')}] Hook connected to 'translated' on engine\n")
            self.f.flush()

    def stop(self) -> None:
        self.engine.hook_disconnect('translated', self.on_translated)
        if self.f:
            self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin stopped ===\n")
            self.f.close()
            self.f = None

    def on_translated(self, old, new):
        """Process Action objects and detect FP strokes."""
        if not self.f:
            return

        try:
            # Log hook firing
            self.f.write(f"[{datetime.now().strftime('%F %T')}] on_translated fired! new={new}\n")
            self.f.flush()

            for action in reversed(new):
                text = getattr(action, 'text', None)
                if not text:
                    continue

                self.f.write(f"[{datetime.now().strftime('%F %T')}] Processing action: {text}\n")
                self.f.flush()

                if self._processing:
                    self.f.write("Skipping: already processing\n")
                    self.f.flush()
                    continue

                # Check if both F and P are present
                if 'F' in text and 'P' in text:
                    self.f.write(f"Found FP in action: {text}\n")
                    self.f.flush()

                    # Remove F and P from text
                    new_text = text.replace('F', '').replace('P', '')
                    if not new_text.strip():
                        self.f.write(f"Cannot handle empty result after FP removal: {text}\n")
                        self.f.flush()
                        continue

                    # Lookup translation using the cleaned strokes
                    try:
                        stroke_objs = tuple(Stroke.from_steno(s) for s in new_text.split(' '))
                        result = self.engine.dictionaries.lookup(stroke_objs)
                    except Exception as e:
                        self.f.write(f"Error converting strokes: {e}\n")
                        self.f.flush()
                        continue

                    if result:
                        self.f.write(f"Found translation: {result}\n")
                        self.f.flush()
                        self._processing = True
                        try:
                            # Remove the original output
                            for _ in range(len(text)):
                                self.engine.output.send_backspaces(1)
                            # Send the translation
                            self.engine.output.send_string(result + '.')
                        finally:
                            self._processing = False
                    else:
                        self.f.write(f"No translation found for: {new_text}\n")
                        self.f.flush()

        except Exception as e:
            self.f.write(f"on_translated error: {e}\n")
            self.f.flush()
