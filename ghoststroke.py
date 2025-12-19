from plover.engine import StenoEngine
from plover.plugin import Plugin

class GhostStroke(Plugin):
    """
    Detects outlines containing FP that have no translation.
    If removing FP yields a valid dictionary entry, outputs that entry + '.'
    """
    def __init__(self, engine: StenoEngine) -> None:
        super().__init__(engine)
        self._engine = engine
        
    def start(self) -> None:
        self._engine.hook_connect('translated', self.on_translated)
        
    def stop(self) -> None:
        self._engine.hook_disconnect('translated', self.on_translated)
        
    def on_translated(self, old, new):
        """Hook fires after translation with old/new state."""
        if not new:
            return
            
        # Get the last translation
        last = new[-1]
        
        # Check if it's untranslated (raw steno shown)
        if last.english is None or not last.has_translation:
            strokes = last.strokes
            
            # Try FP recovery
            result = self.try_fp_recovery(strokes)
            if result:
                # Force a new translation by manipulating the state
                # We need to create a proper translation object
                from plover.translation import Translation
                
                # Create a new translation with our result
                new_translation = Translation(strokes, result + ".")
                new_translation.has_translation = True
                
                # Replace the last translation
                translations = list(new)
                translations[-1] = new_translation
                
                # Update the formatter
                self._engine.clear_translator_state()
                for t in translations:
                    self._engine.translator.translate_translation(t)
                    
    def try_fp_recovery(self, strokes):
        """Try to recover by removing FP from strokes."""
        new_strokes = []
        modified = False
        
        for stroke in strokes:
            # Work with the stroke keys
            keys = stroke.steno_keys if hasattr(stroke, 'steno_keys') else str(stroke)
            new_keys = keys.replace("FP", "")
            
            if new_keys != keys:
                modified = True
                
            if new_keys and new_keys != "-":
                new_strokes.append(new_keys)
            else:
                return None  # Don't handle empty strokes
                
        if not modified:
            return None
            
        # Convert back to stroke objects
        from plover.steno import Stroke
        stroke_objects = tuple(Stroke.from_steno(s) for s in new_strokes)
        
        # Try lookup
        entry = self._engine.dictionaries.lookup(stroke_objects)
        return entry