"""One table appearance for every application screen and compatibility widget."""
from tkinter import ttk
import theme

TABLE_STYLE = 'App.Treeview'


def configure_table_style(master):
    style = ttk.Style(master)
    if style.theme_use() != 'clam':
        style.theme_use('clam')
    style.configure(TABLE_STYLE, background=theme.CARD, fieldbackground=theme.CARD,
                    foreground=theme.TEXT, rowheight=36, font=('DejaVu Sans', 10),
                    borderwidth=0, relief='flat')
    style.configure(TABLE_STYLE + '.Heading', background='#E9EFEC', foreground=theme.TEXT,
                    font=('DejaVu Sans', 10, 'bold'), padding=(10, 10), relief='flat')
    style.map(TABLE_STYLE, background=[('selected', theme.TABLE_SELECTED)],
              foreground=[('selected', theme.TEXT)])
    style.map(TABLE_STYLE + '.Heading', background=[('active', '#DCE6E0')],
              foreground=[('active', theme.TEXT)])
    for orientation in ('Vertical', 'Horizontal'):
        name = f'App.{orientation}.TScrollbar'
        style.configure(name, background='#CBD8D0', troughcolor=theme.BACKGROUND,
                        bordercolor=theme.BORDER, arrowcolor=theme.TEXT_SECONDARY,
                        lightcolor='#CBD8D0', darkcolor='#CBD8D0', width=13, relief='flat')
        style.map(name, background=[('active', '#AABFB1'), ('pressed', theme.PRIMARY)])


class StyledTreeview(ttk.Treeview):
    def __init__(self, master, **kwargs):
        configure_table_style(master)
        kwargs['style'] = TABLE_STYLE
        kwargs.setdefault('selectmode', 'browse')
        super().__init__(master, **kwargs)
        self._stripe_job = None
        self.tag_configure('row_even', background=theme.CARD)
        self.tag_configure('row_odd', background='#F5F8F6')
        for tag, color in [('Просрочено', theme.DANGER), ('Сегодня', theme.WARNING),
                           ('Проверьте дату', theme.DANGER)]:
            self.tag_configure(tag, foreground=color)

    def insert(self, parent, index, iid=None, **kwargs):
        tags = tuple(kwargs.get('tags', ()))
        kwargs['tags'] = tuple(t for t in tags if t not in ('row_even', 'row_odd')) + (
            'row_even' if len(self.get_children(parent)) % 2 == 0 else 'row_odd',)
        return super().insert(parent, index, iid=iid, **kwargs)

    def move(self, item, parent, index):
        super().move(item, parent, index)
        if self._stripe_job is None:
            self._stripe_job = self.after_idle(self._restripe)

    def _restripe(self):
        self._stripe_job = None
        for index, item in enumerate(self.get_children()):
            tags = tuple(t for t in self.item(item, 'tags') if t not in ('row_even', 'row_odd'))
            self.item(item, tags=tags + ('row_even' if index % 2 == 0 else 'row_odd',))

    def destroy(self):
        if self._stripe_job is not None:
            self.after_cancel(self._stripe_job)
        super().destroy()
