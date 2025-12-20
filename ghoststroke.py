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
        self.f.write(f"[{datetime.now().strftime('%F %T')}] Hooks connected\n")
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

        # Check for FP or FRP
        if "FP" not in stroke_str and "FRP" not in stroke_str:
            return

        self.f.write(f"Found FP/FRP in stroke: {stroke_str}\n")
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

        # Remove "FP" or "FRP" substring
        cleaned_last = stroke_str.replace('FRP', 'R').replace('FP', '')
        if cleaned_last.endswith('-'):
            cleaned_last = cleaned_last[:-1]
        if not cleaned_last:
            self.f.write("Stroke empty after FP removal, skipping\n")
            self.f.flush()
            return

        # Get recent translations to look back
        translator_state = self.engine._translator.get_state()
        translations = translator_state.translations if translator_state else []
        
        self.f.write(f"Looking back through {len(translations)} recent translations\n")
        self.f.flush()

        # Try to find the longest matching multi-stroke word
        best_match = None
        best_strokes = None
        best_backspace_count = 0
        
        # Try looking back up to 5 strokes
        for lookback in range(1, min(6, len(translations) + 1)):
            # Get the last N translations
            recent_translations = translations[-lookback:] if lookback <= len(translations) else []
            
            # Build the stroke sequence
            stroke_sequence = []
            total_output = ""
            
            for trans in recent_translations:
                for s in trans.strokes:
                    stroke_sequence.append(s.rtfcre)
                # Accumulate the output text
                if hasattr(trans, 'english'):
                    total_output += trans.english or ""
            
            # Replace the last stroke with the cleaned version
            if stroke_sequence:
                stroke_sequence[-1] = cleaned_last
                stroke_tuple = tuple(stroke_sequence)
                
                self.f.write(f"Trying stroke sequence (lookback={lookback}): {stroke_tuple}\n")
                self.f.flush()
                
                try:
                    result = self.engine.dictionaries.lookup(stroke_tuple)
                    if result:
                        self.f.write(f"Found match: {result} for {stroke_tuple}\n")
                        self.f.flush()
                        # Calculate total output length to backspace
                        backspace_count = len(total_output) + len(stroke_str)  # Include the current raw stroke
                        best_match = result
                        best_strokes = stroke_tuple
                        best_backspace_count = backspace_count
                        # Keep looking for longer matches
                except Exception as e:
                    self.f.write(f"Lookup error for {stroke_tuple}: {e}\n")
                    self.f.flush()
        
        # If no multi-stroke match found, try single stroke
        if not best_match:
            try:
                result = self.engine.dictionaries.lookup((cleaned_last,))
                if result:
                    self.f.write(f"Single stroke translation found: {result}\n")
                    self.f.flush()
                    best_match = result
                    best_strokes = (cleaned_last,)
                    best_backspace_count = len(stroke_str)
            except Exception as e:
                self.f.write(f"Error looking up single cleaned stroke: {e}\n")
                self.f.flush()

        if best_match:
            self.f.write(f"Best match: '{best_match}' from strokes {best_strokes}, backspacing {best_backspace_count}\n")
            self.f.flush()
            
            self._processing = True
            try:
                from plover.oslayer import keyboardcontrol
                kb = keyboardcontrol.KeyboardEmulation()
                
                # Send backspaces
                kb.send_backspaces(best_backspace_count)
                
                # Send the word
                kb.send_string(best_match)
                
                # Send period stroke (TP-PL) for proper formatting
                period_stroke = Stroke.from_steno('TP-PL')
                self.engine._machine_stroke_callback(period_stroke)
                
                self.f.write(f"Sent: '{best_match}' + TP-PL\n")
                self.f.flush()
            finally:
                self._processing = False
        else:
            self.f.write(f"No translation found for any combination, leaving raw steno\n")
            self.f.flush()