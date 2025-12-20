import os
from datetime import datetime

from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR
from plover.steno import Stroke
from plover.formatting import _Action

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

        # Hook translated event
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

        # Check if the last translation contains FP
        if not new:
            return
        
        last_translation = new[-1]
        stroke_str = '/'.join(s.rtfcre for s in last_translation.strokes)
        
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Received translation: {stroke_str}\n")
        self.f.flush()

        # Check if any stroke contains FP
        has_fp = any('FP' in s.rtfcre for s in last_translation.strokes)
        if not has_fp:
            return

        self.f.write(f"Found FP in translation\n")
        self.f.flush()

        # Get the last stroke and check if it has FP
        last_stroke = last_translation.strokes[-1].rtfcre
        if 'FP' not in last_stroke:
            return

        # Remove "FP" substring
        cleaned = last_stroke.replace('FP', '')
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
                # Undo the last translation
                self.engine.clear_translator_state()
                
                # Send the cleaned stroke
                new_stroke = Stroke.from_steno(cleaned)
                self.engine._machine_stroke_callback(new_stroke)
                
                # Add period
                period_stroke = Stroke.from_steno('TP-PL')
                self.engine._machine_stroke_callback(period_stroke)
                
                self.f.write(f"Sent corrected strokes\n")
                self.f.flush()
            finally:
                self._processing = False