from plover.steno import Stroke
from plover.engine import StenoEngine

class GhostStroke:
    """
    Extension that detects FP-containing strokes with no translation
    and outputs the translation without FP + period.
    """
    def __init__(self, engine: StenoEngine) -> None:
        self.engine = engine
        self._processing = False
        
    def start(self) -> None:
        self.engine.hook_connect('translated', self.on_translated)
        
    def stop(self) -> None:
        self.engine.hook_disconnect('translated', self.on_translated)
        
    def on_translated(self, old, new):
        """Called after translation with old and new states."""
        # Prevent recursive calls
        if self._processing:
            return
            
        if not new:
            return
            
        last = new[-1]
        
        # Check if the last translation is untranslated
        # An untranslated stroke has english=None or is the raw stroke
        if last.english is not None and last.english:
            return
            
        # Get the strokes
        strokes = last.rtfcre
        
        # Check if any stroke contains both F and P
        has_fp = any('F' in s and 'P' in s for s in strokes)
        if not has_fp:
            return
            
        # Try removing FP from all strokes
        new_strokes = []
        modified = False
        
        for stroke_str in strokes:
            if 'F' in stroke_str and 'P' in stroke_str:
                # Remove F and P
                new_str = stroke_str.replace('F', '').replace('P', '')
                if not new_str or new_str == '-':
                    return  # Empty stroke, can't handle
                new_strokes.append(new_str)
                modified = True
            else:
                new_strokes.append(stroke_str)
        
        if not modified:
            return
            
        # Look up the modified strokes
        try:
            stroke_objs = tuple(Stroke.from_steno(s) for s in new_strokes)
            result = self.engine.dictionaries.lookup(stroke_objs)
            
            if result:
                # Found it! Output the result with a period
                self._processing = True
                try:
                    # Delete the untranslated stroke output first
                    for _ in range(len(strokes)):
                        self.engine.output.send_backspaces(1)
                    # Now send our translation
                    self.engine.output.send_string(result + '.')
                finally:
                    self._processing = False
                
        except Exception as e:
            # Log errors for debugging
            import traceback
            print(f"GhostStroke error: {e}")
            traceback.print_exc()