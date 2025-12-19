from plover.steno import Stroke

class GhostStroke:
    def __init__(self, engine):
        self.engine = engine
        self._processing = False
        # Try multiple ways to output
        print("=" * 50)
        print("GHOSTSTROKE __INIT__ CALLED")
        print("=" * 50)
        
    def start(self):
        print("=" * 50)
        print("GHOSTSTROKE START CALLED")
        print("=" * 50)
        self.engine.hook_connect('translated', self.on_translated)
        
    def stop(self):
        print("GHOSTSTROKE STOP CALLED")
        self.engine.hook_disconnect('translated', self.on_translated)
        
    def on_translated(self, old, new):
        """Called after translation."""
        if self._processing or not new:
            return
            
        last = new[-1]
        
        # Check if untranslated
        if last.english and last.english not in [''.join(last.rtfcre), '/'.join(last.rtfcre)]:
            return
            
        strokes = last.rtfcre
        
        # Check for FP
        has_fp = any('F' in s and 'P' in s for s in strokes)
        if not has_fp:
            return
            
        print(f"Found FP stroke: {strokes}")
            
        # Remove FP
        new_strokes = []
        for stroke_str in strokes:
            if 'F' in stroke_str and 'P' in stroke_str:
                new_str = stroke_str.replace('F', '').replace('P', '')
                if not new_str or new_str == '-':
                    return
                new_strokes.append(new_str)
            else:
                new_strokes.append(stroke_str)
            
        # Lookup
        try:
            stroke_objs = tuple(Stroke.from_steno(s) for s in new_strokes)
            result = self.engine.dictionaries.lookup(stroke_objs)
            
            if result:
                print(f"Found translation: {result}")
                self._processing = True
                try:
                    for _ in range(len(strokes)):
                        self.engine.output.send_backspaces(1)
                    self.engine.output.send_string(result + '.')
                finally:
                    self._processing = False
        except Exception as e:
            print(f"Error: {e}")