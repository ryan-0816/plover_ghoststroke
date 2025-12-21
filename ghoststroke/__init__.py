"""
Plover GhostStroke Plugin

A Plover extension that automatically adds periods to words by using FP or FRP 
in strokes. When a stroke contains FP/FRP and is not found in the dictionary, 
the plugin removes the FP/FRP, looks up the cleaned stroke, and outputs the 
word with a period.

Example:
  TKPWAEUFP (not in dictionary) → removes FP → looks up TKPWAEU → outputs "gay."
  PHOR/PWEUFPD → looks up PHOR/PWEUD → outputs "morbid."
"""

__version__ = '0.1.0'

from plover_ghoststroke.ghoststroke import GhostStroke

__all__ = ['GhostStroke']