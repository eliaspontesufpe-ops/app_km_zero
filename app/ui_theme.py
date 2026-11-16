"""Componentes Kivy reutilizáveis da identidade visual VôLanchar.

A interface é construída por widgets interativos, sem colocar cartazes na tela.
"""
from pathlib import Path
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

ORANGE=(.946,.27,.012,1)
DARK=(.215,.085,.04,1)
CREAM=(1,.977,.95,1)
WHITE=(1,1,1,1)
MUTED=(.48,.39,.35,1)
BORDER=(.88,.79,.73,1)
PALE=(1,.925,.87,1)
ICON_DIR=Path(__file__).parent/'assets'/'ui_icons'


def surface(widget, bg=WHITE, radius=20, outline=None):
    with widget.canvas.before:
        Color(*bg)
        rect=RoundedRectangle(pos=widget.pos,size=widget.size,radius=[dp(radius)])
        line=None
        if outline:
            Color(*outline)
            line=Line(rounded_rectangle=(widget.x,widget.y,widget.width,widget.height,dp(radius)),width=dp(1.1))
    def resize(w,*_):
        rect.pos=w.pos;rect.size=w.size
        if line:line.rounded_rectangle=(w.x,w.y,w.width,w.height,dp(radius))
    widget.bind(pos=resize,size=resize)
    return rect


def caption(text, size=14, bold=False, color=DARK, height=30, align='left'):
    label=Label(text=text,color=color,bold=bold,font_size=dp(size),size_hint_y=None,
                height=dp(height),halign=align,valign='middle',markup=False)
    label.bind(size=lambda w,_:setattr(w,'text_size',(w.width,None)))
    return label

class FriendlyButton(ButtonBehavior,BoxLayout):
    """Botão acessível: ícone, texto e toda a superfície são clicáveis."""
    def __init__(self,label,action=None,kind='primary',height=48,icon=None,**kwargs):
        super().__init__(orientation='horizontal',size_hint_y=None,height=dp(height),
                         padding=[dp(13),0,dp(13),0],spacing=dp(7),**kwargs)
        bg={'primary':ORANGE,'dark':DARK,'light':WHITE,'soft':PALE,'danger':(.77,.22,.16,1)}.get(kind,ORANGE)
        outline=BORDER if kind in ('light','soft') else None
        surface(self,bg,17,outline)
        fg=WHITE if kind in ('primary','dark','danger') else DARK
        if icon:
            p=ICON_DIR/(icon+'.png')
            if kind in ('primary','dark','danger') and (ICON_DIR/(icon+'_white.png')).is_file():
                p=ICON_DIR/(icon+'_white.png')
            if p.is_file():
                self.add_widget(Image(source=str(p),fit_mode='contain',size_hint_x=None,width=dp(19)))
                self.add_widget(Label(text=label,color=fg,bold=True,font_size=dp(12),halign='center',valign='middle'))
            else:
                self.add_widget(Label(text=label,color=fg,bold=True,font_size=dp(12),halign='center',valign='middle'))
        else:
            self.add_widget(Label(text=label,color=fg,bold=True,font_size=dp(12),halign='center',valign='middle'))
        if action:self.bind(on_release=lambda *_:action())

class NavButton(ButtonBehavior,BoxLayout):
    def __init__(self,name,callback,active=False,icon=None,**kwargs):
        super().__init__(orientation='vertical',spacing=dp(1),padding=[dp(3),dp(4)],**kwargs)
        fg=ORANGE if active else MUTED
        icon=icon or {'Início':'home','Mapa':'map','Vitrine':'products','Pedidos':'orders','Perfil':'profile'}.get(name)
        if icon and (ICON_DIR/(icon+'.png')).is_file():
            self.add_widget(Image(source=str(ICON_DIR/(icon+'.png')),fit_mode='contain',size_hint_y=.6))
        else:
            # Ícone textual pequeno, legível inclusive sem fonte de emoji.
            marks={'Início':'⌂','Mapa':'●','Vitrine':'▣','Pedidos':'≡','Perfil':'○'}
            self.add_widget(Label(text=marks.get(name,'•'),font_size=dp(21),color=fg,size_hint_y=.6))
        self.add_widget(Label(text=name,font_size=dp(10),bold=active,color=fg,size_hint_y=.4))
        self.bind(on_release=lambda *_:callback())

class FriendlyField(BoxLayout):
    def __init__(self,hint,password=False,**kwargs):
        super().__init__(orientation='horizontal',size_hint_y=None,height=dp(49),
                         padding=[dp(12),dp(5)],**kwargs)
        surface(self,WHITE,13,BORDER)
        self.editor=TextInput(hint_text=hint,multiline=False,password=password,
                              font_size=dp(14),foreground_color=DARK,hint_text_color=MUTED,
                              cursor_color=ORANGE,background_normal='',background_active='',
                              background_color=(0,0,0,0),padding=[dp(2),dp(10),dp(2),0])
        self.add_widget(self.editor)


def section(parent,title,subtitle=''):
    widget=BoxLayout(orientation='vertical',spacing=dp(6),padding=[dp(14),dp(11)],size_hint_y=None)
    widget.bind(minimum_height=widget.setter('height'))
    surface(widget,WHITE,21)
    widget.add_widget(caption(title,17,True,DARK,29))
    if subtitle:widget.add_widget(caption(subtitle,12,False,MUTED,33))
    parent.add_widget(widget)
    return widget
