import customtkinter as ctk
import theme
from ui.widgets.modal import grab_when_visible
from personnel_fields import PERSONAL, MILITARY, display_date
from database.profile_repository import ProfileRepository
from database.discipline_repository import DisciplineRepository
from database.service_history_repository import ServiceHistoryRepository
from ui.personnel.personnel_form import PersonnelForm
from ui.discipline.discipline_view import DisciplineView
from ui.widgets.record_editor import CollectionPanel, button


class PersonnelCard(ctk.CTkToplevel):
    SECTIONS=('Личные данные','Военная служба','Дисциплина','Семья','Образование','Личный транспорт','Кредиты')

    def __init__(self,parent,personnel_repository,reference_repository,personnel_id,initial_section='Личные данные'):
        super().__init__(parent)
        self.personnel_repository,self.reference_repository=personnel_repository,reference_repository
        self.personnel_id=personnel_id
        self.profile=ProfileRepository(); self.discipline_repository=DisciplineRepository()
        self.service_history_repository=ServiceHistoryRepository()
        self.title('Личное дело военнослужащего'); self.geometry('1200x820'); self.minsize(1050,680)
        self.configure(fg_color=theme.BACKGROUND)
        self.transient(parent.winfo_toplevel()); grab_when_visible(self)
        self.header=ctk.CTkFrame(self,fg_color=theme.CARD,corner_radius=0); self.header.pack(fill='x')
        body=ctk.CTkFrame(self,fg_color='transparent'); body.pack(fill='both',expand=True,padx=20,pady=20)
        nav=ctk.CTkFrame(body,fg_color=theme.CARD,width=190)
        nav.pack(side='left',fill='y',padx=(0,16)); nav.pack_propagate(False)
        ctk.CTkLabel(nav,text='ЛИЧНОЕ ДЕЛО',text_color=theme.TEXT_SECONDARY,font=theme.SMALL_FONT).pack(anchor='w',padx=16,pady=(18,14))
        self.nav={}
        for name in self.SECTIONS:
            b=ctk.CTkButton(nav,text=name,anchor='w',height=42,fg_color='transparent',text_color=theme.TEXT,
                            hover_color=theme.TABLE_SELECTED,command=lambda n=name:self.show_section(n))
            b.pack(fill='x',padx=8,pady=3); self.nav[name]=b
        self.content=ctk.CTkFrame(body,fg_color='transparent'); self.content.pack(side='left',fill='both',expand=True)
        self.owner_page = parent
        self.protocol("WM_DELETE_WINDOW", self.close_card)
        self.section=initial_section; self.refresh_header(); self.show_section(initial_section)

    def refresh_header(self):
        self.personnel=dict(self.personnel_repository.get_by_id(self.personnel_id))
        for w in self.header.winfo_children(): w.destroy()
        left=ctk.CTkFrame(self.header,fg_color='transparent'); left.pack(side='left',fill='both',expand=True,padx=24,pady=18)
        ctk.CTkLabel(left,text=self.personnel['full_name'],font=theme.TITLE_FONT,text_color=theme.TEXT,wraplength=780,justify='left').pack(anchor='w')
        description='  ·  '.join(str(self.personnel.get(k) or '—') for k in ('rank_name','position_name','unit_name'))
        ctk.CTkLabel(left,text=description,text_color=theme.TEXT_SECONDARY,wraplength=780,justify='left').pack(anchor='w')
        stats=self.discipline_repository.get_personnel_statistics(self.personnel_id)
        ctk.CTkLabel(left,text=f"Личный номер: {self.personnel.get('personal_number') or '—'}   ·   Поощрения: {stats['rewards']}   ·   Активные взыскания: {stats['active_penalties']}",
                     font=theme.SMALL_FONT,text_color=theme.PRIMARY,wraplength=800,justify='left').pack(anchor='w',pady=(6,0))
        right=ctk.CTkFrame(self.header,fg_color='transparent'); right.pack(side='right',padx=24,pady=16)
        button(right,'Сохранить в Word',self.export_word,True,width=165).pack(pady=(8,0))

    def export_word(self):
        from tkinter import filedialog, messagebox
        import re
        from personnel_document import export_personnel
        name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', self.personnel['full_name'])[:100]
        path = filedialog.asksaveasfilename(parent=self, title='Сохранить сведения в Word',
                    initialfile=f'{name}.docx', defaultextension='.docx', filetypes=[('Документ Word', '*.docx')])
        if not path:
            return
        try:
            export_personnel(path, self.personnel_repository.get_by_id(self.personnel_id), self.profile,
                             self.discipline_repository.get_personnel_history(self.personnel_id),
                             self.service_history_repository.get_by_personnel(self.personnel_id))
        except Exception as error:
            messagebox.showerror('Не удалось сохранить документ', str(error), parent=self)
            return
        messagebox.showinfo('Документ сохранён', f'Сведения сохранены в Word:\n{path}', parent=self)

    def show_section(self,name):
        self.section=name
        for w in self.content.winfo_children(): w.destroy()
        for n,b in self.nav.items(): b.configure(fg_color=theme.PRIMARY if n==name else 'transparent',text_color='white' if n==name else theme.TEXT)
        ctk.CTkLabel(self.content,text=name,font=theme.SUBTITLE_FONT,text_color=theme.TEXT).pack(anchor='w',pady=(0,12))
        if name=='Личные данные': self.detail_page(self.content,PERSONAL)
        elif name=='Военная служба': self.service_page()
        elif name=='Дисциплина':
            DisciplineView(self.content,self.discipline_repository,self.personnel_repository,self.reference_repository,
                           personnel_id=self.personnel_id,on_changed=self.refresh_header).pack(fill='both',expand=True)
        else:
            table={'Семья':'family_members','Образование':'education_records','Личный транспорт':'personal_vehicles','Кредиты':'personal_loans'}[name]
            CollectionPanel(self.content,self.profile,table,self.personnel_id,self.refresh_header).pack(fill='both',expand=True)

    def detail_page(self,parent,fields):
        button(parent,'Редактировать раздел',lambda:self.edit_fields(fields),width=185).pack(anchor='w',pady=(0,12))
        scroll=ctk.CTkScrollableFrame(parent,fg_color='transparent'); scroll.pack(fill='both',expand=True)
        card=None
        for f in fields:
            if card is None or f.group:
                card=ctk.CTkFrame(scroll,fg_color=theme.CARD,border_width=1,border_color=theme.BORDER); card.pack(fill='x',pady=(0,14))
                ctk.CTkLabel(card,text=f.group or 'Сведения',font=theme.HEADER_FONT,text_color=theme.PRIMARY).pack(anchor='w',padx=18,pady=(14,10))
            row=ctk.CTkFrame(card,fg_color='transparent'); row.pack(fill='x',padx=18,pady=(0,10)); row.grid_columnconfigure(1,weight=1)
            ctk.CTkLabel(row,text=f.label,width=260,anchor='w',justify='left',wraplength=250,
                         text_color=theme.TEXT_SECONDARY).grid(row=0,column=0,sticky='nw',padx=(0,12))
            value=self.personnel.get(f.key)
            if f.kind=='date': value=display_date(value)
            label=ctk.CTkLabel(row,text=str(value) if value else 'Не указано',anchor='w',justify='left',wraplength=480,
                               text_color=theme.TEXT if value else theme.PLACEHOLDER)
            label.grid(row=0,column=1,sticky='ew')
            row.bind('<Configure>',lambda e,l=label:l.configure(wraplength=max(150,e.width-280)))

    def service_page(self):
        details=ctk.CTkFrame(self.content,fg_color=theme.CARD)
        details.pack(fill='both',expand=True)
        p=self.personnel
        text=f"Личный номер: {p.get('personal_number') or '—'}\nЗвание: {p.get('rank_name') or '—'} · присвоено {display_date(p.get('rank_date')) or '—'}\nДолжность: {p.get('position_name') or '—'} · назначен {display_date(p.get('position_date')) or '—'}"
        ctk.CTkLabel(details,text=text,justify='left',text_color=theme.TEXT,wraplength=800).pack(anchor='w',padx=12,pady=(8,12))
        self.detail_page(details,MILITARY)

    def edit_fields(self,fields):
        self.edit_basic()

    def edit_basic(self):
        def saved():
            self.refresh_header(); self.show_section(self.section)
        PersonnelForm(self,repository=self.personnel_repository,reference_repository=self.reference_repository,
                      on_saved=saved,personnel=self.personnel,initial_section=self.section)


    def close_card(self):
        owner = self.owner_page
        self.destroy()
        if owner.winfo_exists() and hasattr(owner, 'refresh'):
            owner.refresh()
