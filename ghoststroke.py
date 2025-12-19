from plover.engine import StenoEngine


class GhostStroke:
    """
    Detects outlines containing FP that have no translation.
    If removing FP yields a valid dictionary entry, outputs that entry + '.'
    """

    def __init__(self, engine: StenoEngine) -> None:
        self.engine = engine

    def start(self) -> None:
        self.engine.hook_connect('translated', self.on_translation)

    def stop(self) -> None:
        self.engine.hook_disconnect('translated', self.on_translation)

    def on_translation(self, old, new) -> None:
        # find the most recent real output attempt
        for action in reversed(new):
            if action.text and not action.text.isspace():
                strokes = action.rtfcre
                break
        else:
            return

        outline = tuple(strokes)

        # if it already translated, we do nothing
        if self.engine.dictionaries.lookup(outline) is not None:
            return

        # attempt FP recovery
        recovered = self.try_fp_recovery(outline)
        if recovered is not None:
            self.engine.send_string(recovered + ".")

    def try_fp_recovery(self, outline):
        """
        If the outline contains FP, remove it and retry dictionary lookup.
        """
        new_outline = []

        fp_found = False
        for stroke in outline:
            if "FP" in stroke:
                stripped = stroke.replace("FP", "")
                if stripped != stroke:
                    fp_found = True
                new_outline.append(stripped)
            else:
                new_outline.append(stroke)

        if not fp_found:
            return None

        new_outline = tuple(new_outline)

        entry = self.engine.dictionaries.lookup(new_outline)
        if entry is None:
            return None

        return entry
