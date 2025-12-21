import os
from datetime import datetime

from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR
from plover.steno import Stroke

class GhostStroke:
    fname = os.path.join(CONFIG_DIR, 'ghoststroke.txt')
    
    # Define ghoststroke configurations here
    # Format: (pattern_to_remove, replacement, stroke_to_add)
    GHOSTSTROKES = [
        ('FRP', 'R', 'TP-PL'),  # FRP -> R + period
        ('FP', '', 'TP-PL'),     # FP -> nothing + period
    ]

    def __init__(self, engine: StenoEngine) -> None:
        super().__init__()
        self.engine: StenoEngine = engine
        self._processing = False
        self.f = None

    def start(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.f = open(self.fname, 'a', encoding='utf-8')
        self.f.write(f"[{datetime.now().strftime('%F %T')}] GhostStroke plugin started\n")
        self.f.flush()
        self.engine.hook_connect('stroked', self.on_stroked)

    def stop(self) -> None:
        self.engine.hook_disconnect('stroked', self.on_stroked)
        if self.f:
            self.f.write(f"[{datetime.now().strftime('%F %T')}] GhostStroke plugin stopped\n")
            self.f.close()
            self.f = None

    def find_ghoststroke(self, stroke_str):
        """Check if stroke contains any ghoststroke pattern and return the config."""
        for pattern, replacement, addition in self.GHOSTSTROKES:
            if pattern in stroke_str:
                return pattern, replacement, addition
        return None, None, None

    def clean_stroke(self, stroke_str, pattern, replacement):
        """Remove pattern and replace with replacement, clean up trailing dash."""
        cleaned = stroke_str.replace(pattern, replacement)
        if cleaned.endswith('-'):
            cleaned = cleaned[:-1]
        return cleaned

    def lookup_best_match(self, cleaned_last, stroke_str):
        """Look back through translations to find the longest matching word."""
        translator_state = self.engine._translator.get_state()
        translations = translator_state.translations if translator_state else []
        
        best_match = None
        best_strokes = None
        best_backspace_count = 0
        original_output = ""
        
        # Try looking back up to 5 strokes for multi-stroke words
        for lookback in range(1, min(6, len(translations) + 1)):
            recent_translations = translations[-lookback:] if lookback <= len(translations) else []
            
            stroke_sequence = []
            total_output = ""
            
            for trans in recent_translations:
                for s in trans.strokes:
                    stroke_sequence.append(s.rtfcre)
                if hasattr(trans, 'english'):
                    total_output += trans.english or ""
            
            if stroke_sequence:
                stroke_sequence[-1] = cleaned_last
                stroke_tuple = tuple(stroke_sequence)
                
                try:
                    result = self.engine.dictionaries.lookup(stroke_tuple)
                    if result:
                        backspace_count = len(total_output) + len(stroke_str)
                        best_match = result
                        best_strokes = stroke_tuple
                        best_backspace_count = backspace_count
                        original_output = total_output
                except Exception:
                    pass
        
        # If no multi-stroke match found, try single stroke
        if not best_match:
            try:
                result = self.engine.dictionaries.lookup((cleaned_last,))
                if result:
                    best_match = result
                    best_strokes = (cleaned_last,)
                    best_backspace_count = len(stroke_str)
                    original_output = ""
            except Exception:
                pass
        
        return best_match, best_strokes, best_backspace_count, original_output

    def should_capitalize(self, original_output, best_match):
        """Determine if the output should be capitalized based on original output."""
        if original_output and original_output[0].isupper():
            return True
        if not original_output and best_match and best_match[0].isupper():
            return True
        return False

    def apply_capitalization(self, word):
        """Capitalize the first letter of a word."""
        if word:
            return word[0].upper() + word[1:] if len(word) > 1 else word.upper()
        return word

    def on_stroked(self, stroke: Stroke):
        if self._processing or not self.f:
            return

        stroke_str = stroke.rtfcre
        
        # Check if stroke contains any ghoststroke pattern
        pattern, replacement, addition_stroke = self.find_ghoststroke(stroke_str)
        if not pattern:
            return

        # Check if the FULL chord (with ghoststroke) exists in dictionary
        try:
            full_result = self.engine.dictionaries.lookup((stroke_str,))
            if full_result:
                return  # Don't process if full chord exists
        except Exception:
            pass

        # Clean the stroke by removing ghoststroke pattern
        cleaned_last = self.clean_stroke(stroke_str, pattern, replacement)
        if not cleaned_last:
            return

        # Find the best matching translation
        best_match, best_strokes, best_backspace_count, original_output = self.lookup_best_match(
            cleaned_last, stroke_str
        )

        if best_match:
            # Apply capitalization if needed
            output_word = best_match
            if self.should_capitalize(original_output, best_match):
                output_word = self.apply_capitalization(output_word)
            
            self._processing = True
            try:
                from plover.oslayer import keyboardcontrol
                kb = keyboardcontrol.KeyboardEmulation()
                
                # Send backspaces to delete raw steno
                kb.send_backspaces(best_backspace_count)
                
                # Send the translated word (with capitalization if needed)
                kb.send_string(output_word)
                
                # Send the additional stroke (e.g., period)
                if addition_stroke:
                    addition = Stroke.from_steno(addition_stroke)
                    self.engine._machine_stroke_callback(addition)
                
                self.f.write(f"[{datetime.now().strftime('%F %T')}] {stroke_str} -> {output_word} + {addition_stroke}\n")
                self.f.flush()
            finally:
                self._processing = False