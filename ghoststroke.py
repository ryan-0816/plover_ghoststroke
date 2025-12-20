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
        self._original_callback = None

    def start(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.f = open(self.fname, 'a', encoding='utf-8')
        self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin started ===\n")
        self.f.flush()

        # Store the original callback and replace it with our wrapper
        self._original_callback = self.engine._machine_stroke_callback
        self.engine._machine_stroke_callback = self.stroke_wrapper
        
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Intercepting machine strokes\n")
        self.f.flush()

    def stop(self) -> None:
        # Restore the original callback
        if self._original_callback:
            self.engine._machine_stroke_callback = self._original_callback
        
        self.f.write(f"[{datetime.now().strftime('%F %T')}] === GhostStroke plugin stopped ===\n")
        self.f.close()
        self.f = None

    def stroke_wrapper(self, stroke: Stroke):
        """Wrapper that intercepts all strokes before they're processed"""
        if self._processing or not self.f:
            # Pass through during our own processing or if not ready
            return self._original_callback(stroke)

        stroke_str = stroke.rtfcre
        
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Intercepted stroke: {stroke_str}\n")
        self.f.flush()

        # Check if stroke contains FP
        if "FP" not in stroke_str:
            # Pass through normally
            return self._original_callback(stroke)

        self.f.write(f"Found FP in stroke: {stroke_str}\n")
        self.f.flush()

        cleaned = stroke_str.replace('FP', '')
        if cleaned.endswith('-'):
            cleaned = cleaned[:-1]
        if not cleaned:
            self.f.write("Stroke empty after FP removal, passing through\n")
            self.f.flush()
            return self._original_callback(stroke)

        try:
            result = self.engine.dictionaries.lookup((cleaned,))
        except Exception as e:
            self.f.write(f"Error looking up cleaned stroke: {e}, passing through\n")
            self.f.flush()
            return self._original_callback(stroke)

        if not result:
            self.f.write(f"No translation found, passing through\n")
            self.f.flush()
            return self._original_callback(stroke)

        # We found a translation! Don't process the original stroke
        self.f.write(f"Translation found: {result}, replacing stroke\n")
        self.f.flush()
        
        self._processing = True
        try:
            # Send the cleaned stroke instead
            new_stroke = Stroke.from_steno(cleaned)
            self._original_callback(new_stroke)
            
            # Send period stroke
            period_stroke = Stroke.from_steno('TP-PL')
            self._original_callback(period_stroke)
            
            # Send capitalization stroke for next word
            cap_stroke = Stroke.from_steno('KPA*')
            self._original_callback(cap_stroke)
            
            self.f.write(f"Sent replacement strokes: {cleaned} + TP-PL + KPA*\n")
            self.f.flush()
        finally:
            self._processing = False

        # Don't call the original callback with the FP stroke - we've replaced it
        return