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

        stroke_str = stroke.rtfcre
        
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Received stroke: {stroke_str}\n")
        self.f.flush()

        if "FP" not in stroke_str:
            return

        self.f.write(f"Found FP in stroke: {stroke_str}\n")
        self.f.flush()

        cleaned = stroke_str.replace('FP', '')
        if cleaned.endswith('-'):
            cleaned = cleaned[:-1]
        if not cleaned:
            self.f.write("Stroke empty after FP removal, skipping\n")
            self.f.flush()
            return

        try:
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
                # Use keyboard module to send backspaces and text
                from plover.oslayer import keyboardcontrol
                kb = keyboardcontrol.KeyboardEmulation()
                
                # The raw steno output is the stroke_str itself (e.g., "TKPWAEUFP")
                # We need to delete exactly that many characters
                backspace_count = len(stroke_str)
                self.f.write(f"Sending {backspace_count} backspaces for '{stroke_str}'\n")
                self.f.flush()
                
                kb.send_backspaces(backspace_count)
                
                # Send the translation with period and space
                kb.send_string(result + '. ')
                
                # Trigger capitalization for the next word by sending a capitalization stroke
                cap_stroke = Stroke.from_steno('KPA*')  # Standard cap next word stroke
                self.engine._machine_stroke_callback(cap_stroke)
                
                self.f.write(f"Sent via keyboard emulation: '{result}. ' + capitalization stroke\n")
                self.f.flush()
            finally:
                self._processing = False