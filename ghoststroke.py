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
        self._pending_undo = False

    def start(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.f = open(self.fname, 'a', encoding='utf-8')
        self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin started ===\n")
        self.f.flush()

        # Hook both stroked (before translation) and translated (after)
        self.engine.hook_connect('stroked', self.on_stroked)
        self.engine.hook_connect('translated', self.on_translated)
        
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Hooks connected\n")
        self.f.flush()

    def stop(self) -> None:
        self.engine.hook_disconnect('stroked', self.on_stroked)
        self.engine.hook_disconnect('translated', self.on_translated)
        
        self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin stopped ===\n")
        self.f.close()
        self.f = None

    def on_stroked(self, stroke: Stroke):
        """Check if we need to process this stroke"""
        if self._processing or not self.f:
            return

        stroke_str = stroke.rtfcre
        
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Stroked: {stroke_str}\n")
        self.f.flush()

        # Check if stroke contains FP
        if "FP" not in stroke_str:
            return

        self.f.write(f"Found FP in stroke: {stroke_str}\n")
        self.f.flush()

        cleaned = stroke_str.replace('FP', '')
        if cleaned.endswith('-'):
            cleaned = cleaned[:-1]
        if not cleaned:
            self.f.write("Stroke empty after FP removal\n")
            self.f.flush()
            return

        try:
            result = self.engine.dictionaries.lookup((cleaned,))
        except Exception as e:
            self.f.write(f"Error looking up cleaned stroke: {e}\n")
            self.f.flush()
            return

        if result:
            self.f.write(f"Translation found: {result}, marking for undo\n")
            self.f.flush()
            self._pending_undo = True

    def on_translated(self, old, new):
        """After translation occurs, undo and replace if needed"""
        if self._processing or not self.f or not self._pending_undo:
            return

        self._pending_undo = False
        
        if not new:
            return
            
        last_translation = new[-1]
        last_stroke = last_translation.strokes[-1].rtfcre
        
        if "FP" not in last_stroke:
            return

        self.f.write(f"[{datetime.now().strftime('%F %T')}] Translated with FP: {last_stroke}\n")
        self.f.flush()

        cleaned = last_stroke.replace('FP', '')
        if cleaned.endswith('-'):
            cleaned = cleaned[:-1]
        if not cleaned:
            return

        try:
            result = self.engine.dictionaries.lookup((cleaned,))
        except Exception as e:
            self.f.write(f"Error looking up: {e}\n")
            self.f.flush()
            return

        if result:
            self.f.write(f"Replacing with: {result}\n")
            self.f.flush()
            
            self._processing = True
            try:
                # Send undo stroke to remove the raw output
                self.engine._machine_stroke_callback(Stroke.from_steno('*'))
                
                # Send the cleaned stroke
                new_stroke = Stroke.from_steno(cleaned)
                self.engine._machine_stroke_callback(new_stroke)
                
                # Send period stroke
                period_stroke = Stroke.from_steno('TP-PL')
                self.engine._machine_stroke_callback(period_stroke)
                
                # Send capitalization stroke for next word
                cap_stroke = Stroke.from_steno('KPA*')
                self.engine._machine_stroke_callback(cap_stroke)
                
                self.f.write(f"Sent: undo + {cleaned} + period + cap\n")
                self.f.flush()
            finally:
                self._processing = False