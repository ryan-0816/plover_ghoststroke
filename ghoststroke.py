from plover.steno import Stroke
from plover.engine import StenoEngine
from plover import log

class GhostStroke:
    """
    Extension that detects FP-containing strokes with no translation
    and outputs the translation without FP + period.
    """
    def __init__(self, engine: StenoEngine) -> None:
        self.engine = engine
        self._processing = False
        
    def start(self) -> None:
        try:
            log.info("GhostStroke: start() called")
            self.engine.hook_connect('translated', self.on_translated)
            log.info("GhostStroke: Started and hooked to 'translated'")
        except Exception as e:
            log.error(f"GhostStroke: Error in start(): {e}", exc_info=True)
        
    def stop(self) -> None:
        self.engine.hook_disconnect('translated', self.on_translated)
        log.info("GhostStroke: Stopped")
        
    def on_translated(self, old, new):
        """Called after translation with old and new states."""
        # Prevent recursive calls
        if self._processing:
            return
            
        if not new:
            return
            
        last = new[-1]
        
        # Debug logging
        log.debug(f"GhostStroke: last.english = {last.english}, last.rtfcre = {last.rtfcre}")
        
        # Check if the last translation is untranslated
        # When untranslated, english might be empty string or the raw stroke
        if last.english and last.english not in [''.join(last.rtfcre), '/'.join(last.rtfcre)]:
            log.debug(f"GhostStroke: Skipping - has translation: {last.english}")
            return
            
        # Get the strokes
        strokes = last.rtfcre
        
        # Check if any stroke contains both F and P
        has_fp = any('F' in s and 'P' in s for s in strokes)
        if not has_fp:
            log.debug(f"GhostStroke: No FP found in strokes: {strokes}")
            return
            
        log.info(f"GhostStroke: Found untranslated FP stroke: {strokes}")
            
        # Try removing FP from all strokes
        new_strokes = []
        modified = False
        
        for stroke_str in strokes:
            if 'F' in stroke_str and 'P' in stroke_str:
                # Remove F and P
                new_str = stroke_str.replace('F', '').replace('P', '')
                if not new_str or new_str == '-':
                    log.debug(f"GhostStroke: Empty stroke after removing FP")
                    return  # Empty stroke, can't handle
                new_strokes.append(new_str)
                modified = True
            else:
                new_strokes.append(stroke_str)
        
        if not modified:
            return
            
        log.info(f"GhostStroke: Trying lookup with: {new_strokes}")
            
        # Look up the modified strokes
        try:
            stroke_objs = tuple(Stroke.from_steno(s) for s in new_strokes)
            result = self.engine.dictionaries.lookup(stroke_objs)
            
            if result:
                log.info(f"GhostStroke: Found translation: {result}")
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
            else:
                log.debug(f"GhostStroke: No translation found for {new_strokes}")
                
        except Exception as e:
            # Log errors for debugging
            log.error(f"GhostStroke error: {e}", exc_info=True)