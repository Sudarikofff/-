def notify_data_changed(widget):
    """Refresh application summaries after a durable write, not a draft edit."""
    root = widget
    while getattr(root, 'master', None) is not None:
        root = root.master
    root.event_generate('<<PersonnelDataChanged>>', when='tail')
