from plover.steno import Stroke
from plover.steno_dictionary import StenoDictionary

class GhostStrokeDictionary(StenoDictionary):
    """
    A virtual dictionary that intercepts FP-containing strokes
    and provides translations by removing FP.
    """
    
    def __init__(self):
        super().__init__()
        self.enabled = True
        self._dicts = None
        
    def set_dicts(self, dicts):
        """Store reference to other dictionaries for lookup."""
        self._dicts = dicts
        
    def _lookup(self, strokes):
        """
        Called when Plover looks up a stroke sequence.
        If it contains FP and has no translation, try without FP.
        """
        if not self._dicts:
            return None
            
        # Check if any stroke contains FP
        has_fp = any('F' in s.keys() and 'P' in s.keys() for s in strokes)
        if not has_fp:
            return None
            
        # Try removing FP from all strokes
        new_strokes = []
        modified = False
        
        for stroke in strokes:
            if 'F' in stroke.keys() and 'P' in stroke.keys():
                # Remove F and P
                keys = [k for k in stroke.keys() if k not in ('F', 'P')]
                if keys:
                    new_strokes.append(Stroke(keys))
                    modified = True
                else:
                    # Empty stroke, bail out
                    return None
            else:
                new_strokes.append(stroke)
                
        if not modified:
            return None
            
        # Look up the modified strokes in other dictionaries
        new_strokes_tuple = tuple(new_strokes)
        for d in self._dicts:
            if d == self:  # Skip self to avoid recursion
                continue
            result = d.lookup(new_strokes_tuple)
            if result is not None:
                # Found it! Add a period
                return result + "."
                
        return None
        
    def reverse_lookup(self, text):
        """Not needed for this plugin."""
        return []


class GhostStroke:
    """
    Extension that adds the ghost stroke dictionary to the stack.
    """
    def __init__(self, engine):
        self._engine = engine
        self._dict = None
        
    def start(self):
        """Add our virtual dictionary to the stack."""
        self._dict = GhostStrokeDictionary()
        
        # Add to dictionary stack
        dicts = self._engine.dictionaries
        self._dict.set_dicts(dicts.dicts)
        
        # Insert at high priority (near the top)
        dicts.set_dicts([self._dict] + dicts.dicts)
        
    def stop(self):
        """Remove our dictionary from the stack."""
        if self._dict:
            dicts = self._engine.dictionaries
            new_dicts = [d for d in dicts.dicts if d != self._dict]
            dicts.set_dicts(new_dicts)
            self._dict = None