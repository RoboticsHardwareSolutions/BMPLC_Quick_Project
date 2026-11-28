"""J-Link DLL dialog boxes off for every pylink.JLink in the process.

bmlab_toolkit.JLinkProgrammer never calls pylink's disable_dialog_boxes(), so on an unattended HIL host the J-Link DLL
pops up windows (firmware update offer, device selection, flash progress) that wait for someone to click them.
The commands go straight to the DLL and work before open(), so they are sent right after JLink() is created.
"""

from __future__ import annotations

import functools

import pylink

_patched = False


def disable_jlink_dialogs() -> None:
    """Patch pylink.JLink.__init__ to call disable_dialog_boxes(). Idempotent."""
    global _patched
    if _patched:
        return

    original_init = pylink.JLink.__init__

    @functools.wraps(original_init)
    def init_without_dialogs(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        try:
            self.disable_dialog_boxes()
        except Exception:  # an older DLL without these commands: keep working, with dialogs
            pass

    pylink.JLink.__init__ = init_without_dialogs
    _patched = True
