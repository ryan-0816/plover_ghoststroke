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

        if ("FP" or "FRP") not in stroke_str:
            return

        self.f.write(f"Found FP in stroke: {stroke_str}\n")
        self.f.flush()

        # First check if the FULL chord (with FP) exists in dictionary
        try:
            full_result = self.engine.dictionaries.lookup((stroke_str,))
            if full_result:
                self.f.write(f"Full chord '{stroke_str}' found in dictionary: {full_result}, not processing\n")
                self.f.flush()
                return  # Don't process if full chord exists
        except Exception as e:
            self.f.write(f"Error looking up full chord: {e}\n")
            self.f.flush()

        self.f.write(f"Full chord '{stroke_str}' NOT in dictionary, processing...\n")
        self.f.flush()

        # Remove "FP" substring
        cleaned = stroke_str.replace('FP', '').replace('FRP', 'R')
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
            self.f.write(f"Translation found for cleaned stroke: {result}\n")
            self.f.flush()
            self._processing = True
            try:
                # Use keyboard module to send backspaces and text
                from plover.oslayer import keyboardcontrol
                kb = keyboardcontrol.KeyboardEmulation()
                
                # Send backspaces
                backspace_count = len(stroke_str)
                self.f.write(f"Sending {backspace_count} backspaces\n")
                self.f.flush()
                
                kb.send_backspaces(backspace_count)
                
                # Send the translation with period and space
                kb.send_string(result + '. ')
                
                # Trigger capitalization for the next word
                cap_stroke = Stroke.from_steno('KPA*')
                self.engine._machine_stroke_callback(cap_stroke)
                
                self.f.write(f"Sent: '{result}. ' + cap stroke\n")
                self.f.flush()
            finally:
                self._processing = False
        else:
            self.f.write(f"No translation found for cleaned stroke '{cleaned}', leaving raw steno\n")
            self.f.flush()