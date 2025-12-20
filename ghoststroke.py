import os
from datetime import datetime

from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR
from plover.steno import Stroke

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

        # Hook stroked event instead of translated
        self.engine.hook_connect('stroked', self.on_stroked)
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Hook connected to 'stroked'\n")
        self.f.flush()

    def stop(self) -> None:
        self.engine.hook_disconnect('stroked', self.on_stroked)
        self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin stopped ===\n")
        self.f.close()
        self.f = None

    def on_stroked(self, stroke: Stroke):
        if self._processing or not self.f:
            return

        # Get the stroke as a string
        stroke_str = stroke.rtfcre
        
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Received stroke: {stroke_str}\n")
        self.f.flush()

        # Detect exact "FP" substring
        if "FP" not in stroke_str:
            return

        self.f.write(f"Found FP in stroke: {stroke_str}\n")
        self.f.flush()

        # Remove "FP" substring
        cleaned = stroke_str.replace('FP', '')
        if not cleaned:
            self.f.write("Stroke empty after FP removal, skipping\n")
            self.f.flush()
            return

        try:
            # Lookup in dictionary using tuple of strings
            result = self.engine.dictionaries.lookup((cleaned,))
        except Exception as e:
            self.f.write(f"Error looking up cleaned stroke: {e}\n")
            self.f.flush()
            return

        if result:
            self.f.write(f"Translation found: {result}\n")
            self.f.flush()
            self._processing = True
            try:
                # Delete the original untranslated stroke output (TKPWAEUFP)
                self.engine.output.send_backspaces(len(stroke_str))
                self.f.write(f"Sent {len(stroke_str)} backspaces\n")
                self.f.flush()
                
                # Create a new stroke without FP and send it
                new_stroke = Stroke.from_steno(cleaned)
                self.engine._machine_stroke_callback(new_stroke)
                
                # Add a period stroke
                period_stroke = Stroke.from_steno('TP-PL')  # Standard period stroke, adjust if needed
                self.engine._machine_stroke_callback(period_stroke)
            finally:
                self._processing = False