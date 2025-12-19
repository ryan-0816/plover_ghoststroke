import os
from plover.steno import Stroke
from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR

class GhostStroke:
    fname = os.path.join(CONFIG_DIR, 'ghoststroke.txt')
    
    def __init__(self, engine: StenoEngine) -> None:
        super().__init__()
        self.engine: StenoEngine = engine
        self._processing = False
    
    def start(self) -> None:
        self.engine.hook_connect('translated', self.on_translated)
        self.f = open(self.fname, 'a')
        self.f.write("=== GhostStroke plugin started ===\n")
        self.f.flush()
    
    def stop(self) -> None:
        self.engine.hook_disconnect('translated', self.on_translated)
        self.f.close()
    
    def on_translated(self, old, new):
        """Called after translation with old and new states."""
        # Prevent recursive calls
        if self._processing:
            return
            
        if not new:
            return
            
        last = new[-1]
        
        # Check if the last translation is untranslated
        if last.english:
            return
            
        # Get the strokes
        strokes = last.rtfcre
        
        # Check if any stroke contains both F and P
        has_fp = any('F' in s and 'P' in s for s in strokes)
        if not has_fp:
            return
            
        self.f.write(f"Found FP stroke: {strokes}\n")
        self.f.flush()
            
        # Try removing FP from all strokes
        new_strokes = []
        
        for stroke_str in strokes:
            if 'F' in stroke_str and 'P' in stroke_str:
                # Remove F and P
                new_str = stroke_str.replace('F', '').replace('P', '')
                if not new_str or new_str == '-':
                    return  # Empty stroke, can't handle
                new_strokes.append(new_str)
            else:
                new_strokes.append(stroke_str)
            
        # Lookup
        try:
            stroke_objs = tuple(Stroke.from_steno(s) for s in new_strokes)
            result = self.engine.dictionaries.lookup(stroke_objs)
            
            if result:
                self.f.write(f"Found translation: {result}\n")
                self.f.flush()
                
                self._processing = True
                try:
                    # Delete the untranslated stroke output
                    for _ in range(len(strokes)):
                        self.engine.output.send_backspaces(1)
                    # Send our translation
                    self.engine.output.send_string(result + '.')
                finally:
                    self._processing = False
        except Exception as e:
            self.f.write(f"Error: {e}\n")
            self.f.flush()