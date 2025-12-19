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
        self._engine.hook_connect('stroked', self.on_stroked)

    def stop(self) -> None:
        self._engine.hook_disconnect('stroked', self.on_stroked)

    def on_stroked(self, stroke):
        # Get the current strokes in the translator
        translator = self._engine.translator
        if not translator.translations:
            return
            
        last_state = translator.translations[-1]
        
        # Check if untranslated
        if last_state.word is None:
            strokes = tuple(last_state.rtfcre)
            
            # Check if already in dictionary (shouldn't be, but just in case)
            if self._engine.dictionaries.lookup(strokes):
                return
                
            # Try FP recovery
            result = self.try_fp_recovery(strokes)
            if result:
                # Send the result
                self._engine.send_string(result + ".")

    def try_fp_recovery(self, strokes):
        """Try to recover by removing FP from strokes."""
        new_strokes = []
        modified = False
        
        for stroke in strokes:
            new_stroke = stroke.replace("FP", "")
            if new_stroke != stroke:
                modified = True
            if new_stroke:
                new_strokes.append(new_stroke)
            else:
                # Empty stroke after removing FP
                new_strokes.append("-")
                
        if not modified:
            return None
            
        # Try lookup
        entry = self._engine.dictionaries.lookup(tuple(new_strokes))
        return entry