"""Acquire a modal grab only after the window manager has mapped the dialog."""


def grab_when_visible(window):
    bindings = {}
    acquired = False

    def acquire(event=None):
        nonlocal acquired
        if acquired:
            return
        if event is not None and event.widget is not window:
            return
        if not window.winfo_exists() or not window.winfo_viewable():
            return
        window.grab_set()
        acquired = True
        for sequence, binding in bindings.items():
            window.unbind(sequence, binding)
        bindings.clear()

    # Mapping can be delayed arbitrarily by the window manager. A fixed timeout
    # does not guarantee that Tk will accept the grab.
    for sequence in ('<Map>', '<Visibility>'):
        bindings[sequence] = window.bind(sequence, acquire, add='+')
    window.after_idle(acquire)
