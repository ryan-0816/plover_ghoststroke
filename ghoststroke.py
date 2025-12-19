import logging
from plover.engine import StenoEngine
from plover.plugin import Plugin

# Set up logger
logger = logging.getLogger('ghoststroke')
logger.setLevel(logging.DEBUG)

# Create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class GhostStroke(Plugin):
    """
    Detects outlines containing FP that have no translation.
    If removing FP yields a valid dictionary entry, outputs that entry + '.'
    """

    def __init__(self, engine: StenoEngine) -> None:
        super().__init__(engine)
        self._engine = engine
        logger.info("GhostStroke plugin initialized")

    def start(self) -> None:
        logger.info("GhostStroke plugin starting")
        self._engine.hook_connect('stroked', self.on_stroked)
        logger.info("Connected to 'stroked' hook")

    def stop(self) -> None:
        logger.info("GhostStroke plugin stopping")
        self._engine.hook_disconnect('stroked', self.on_stroked)

    def on_stroked(self, stroke):
        logger.debug(f"Stroke received: {stroke}")
        
        # Get the translator state
        translator = self._engine.translator
        logger.debug(f"Translator state: {translator}")
        logger.debug(f"Translator has {len(translator.translations)} translations")
        
        if not translator.translations:
            logger.debug("No translations, returning")
            return
            
        # Get the last translation state
        last_state = translator.translations[-1]
        logger.debug(f"Last state: {last_state}")
        logger.debug(f"Last state rtfcre: {last_state.rtfcre}")
        logger.debug(f"Last state word: {last_state.word}")
        logger.debug(f"Last state english: {last_state.english}")
        logger.debug(f"Last state is_translation: {last_state.is_translation}")
        
        # Check if untranslated
        if last_state.word is None and last_state.english is None:
            logger.info(f"Untranslated stroke detected: {last_state.rtfcre}")
            
            strokes = tuple(last_state.rtfcre)
            logger.debug(f"Strokes as tuple: {strokes}")
            
            # Check if already in dictionary (shouldn't be, but just in case)
            dict_lookup = self._engine.dictionaries.lookup(strokes)
            logger.debug(f"Direct dictionary lookup: {dict_lookup}")
            
            if dict_lookup:
                logger.info("Stroke already has a dictionary entry, skipping")
                return
                
            # Try FP recovery
            logger.info("Attempting FP recovery")
            result = self.try_fp_recovery(strokes)
            logger.debug(f"Recovery result: {result}")
            
            if result:
                logger.info(f"Successfully recovered: {result}")
                # Send the result
                self._engine.send_string(result + ".")
                logger.info(f"Sent: {result + '.'}")
            else:
                logger.info("No FP recovery possible")
        else:
            logger.debug("Stroke was translated, ignoring")

    def try_fp_recovery(self, strokes):
        """Try to recover by removing FP from strokes."""
        logger.debug(f"Original strokes for recovery: {strokes}")
        
        new_strokes = []
        modified = False
        
        for i, stroke in enumerate(strokes):
            logger.debug(f"Processing stroke {i}: {stroke}")
            new_stroke = stroke.replace("FP", "")
            if new_stroke != stroke:
                modified = True
                logger.debug(f"Modified stroke {i}: '{stroke}' -> '{new_stroke}'")
            
            # Handle empty strokes
            if not new_stroke:
                new_stroke = "-"
                logger.debug(f"Stroke {i} became empty, using '-'")
                
            new_strokes.append(new_stroke)
                
        if not modified:
            logger.debug("No FP found in strokes")
            return None
            
        new_strokes_tuple = tuple(new_strokes)
        logger.debug(f"Modified strokes: {new_strokes_tuple}")
        
        # Try lookup
        entry = self._engine.dictionaries.lookup(new_strokes_tuple)
        logger.debug(f"Dictionary lookup result: {entry}")
        
        return entry