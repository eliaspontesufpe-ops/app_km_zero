"""Componentes de autenticação do VôLanchar — versão 0.7.2.

Ícones PNG alinhados por BoxLayout (em vez de desenhos em coordenadas
instáveis). Os formulários continuam sendo controles Kivy funcionais.
"""
import os
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.graphics import Color, RoundedRectangle, Line

INK = (.215, .085, .040, 1)
ORANGE = (.946, .27, .012, 1)
CREAM = (1, .977, .950, 1)
MUTED = (.52, .43, .39, 1)
WHITE = (1, 1, 1, 1)
BORDER = (.84, .74, .67, 1)
PALE = (1, .93, .87, 1)

ICON_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'ui_icons')


def icon_path(name):
    return os.path.join(ICON_DIR, name + '.png')


def rounded(widget, color, radius=18, border=None):
    """Desenha fundo e borda do tamanho exato do componente."""
    with widget.canvas.before:
        Color(*color)
        bg = RoundedRectangle(pos=widget.pos, size=widget.size,
                              radius=[dp(radius)])
        outline = None
        if border is not None:
            Color(*border)
            outline = Line(rounded_rectangle=(widget.x, widget.y, widget.width,
                                              widget.height, dp(radius)), width=dp(1.2))

    def update(w, *_):
        bg.pos, bg.size = w.pos, w.size
        if outline is not None:
            outline.rounded_rectangle = (w.x, w.y, w.width, w.height, dp(radius))
    widget.bind(pos=update, size=update)


def text(value, font=15, weight=False, color=INK, height=30, align='left'):
    w = Label(text=value, color=color, bold=weight, font_size=dp(font),
              size_hint_y=None, height=dp(height), halign=align,
              valign='middle', shorten=False)
    w.bind(size=lambda inst, _: setattr(inst, 'text_size', (inst.width, None)))
    return w


class VoLancharAuthButton(ButtonBehavior, BoxLayout):
    """Botão completo: ícone e texto participam do mesmo clique."""
    def __init__(self, value, callback, solid=True, height=52, icon=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=dp(height),
                         padding=[dp(18), 0, dp(18), 0], spacing=dp(10), **kwargs)
        rounded(self, ORANGE if solid else WHITE, 17, None if solid else BORDER)
        # Ícone à esquerda, texto centralizado com espaço equivalente à direita.
        if icon:
            # Google: logotipo à esquerda. Ação principal: seta à direita.
            self.add_widget(Image(source=icon_path(icon), fit_mode='contain',
                                  size_hint_x=None, width=dp(28)) if icon != 'arrow'
                            else Label(text='', size_hint_x=None, width=dp(28)))
        self.add_widget(Label(text=value, bold=True, font_size=dp(15),
                              color=WHITE if solid else INK,
                              halign='center', valign='middle'))
        if icon:
            self.add_widget(Image(source=icon_path('arrow'), fit_mode='contain',
                                  size_hint_x=None, width=dp(28)) if icon == 'arrow'
                            else Label(text='', size_hint_x=None, width=dp(28)))
        self.bind(on_release=lambda *_: callback())


def button(value, callback, solid=True, height=52, icon=None):
    # Google usa o logotipo colorido, em arquivo PNG local (sem fonte externa).
    if icon is None and 'Google' in value:
        icon = 'google'
    return VoLancharAuthButton(value, callback, solid, height, icon=icon)


class Entry(BoxLayout):
    """Campo com ícone centralizado verticalmente e mostrar/ocultar senha."""
    def __init__(self, hint, icon='user', password=False, **kwargs):
        super().__init__(orientation='horizontal', spacing=dp(10),
                         padding=[dp(13), dp(4), dp(10), dp(4)],
                         size_hint_y=None, height=dp(56), **kwargs)
        rounded(self, WHITE, 14, BORDER)
        self.add_widget(Image(source=icon_path(icon), fit_mode='contain',
                              size_hint_x=None, width=dp(24)))
        self.editor = TextInput(hint_text=hint, password=password, multiline=False,
                                font_size=dp(13), foreground_color=INK,
                                cursor_color=ORANGE, hint_text_color=MUTED,
                                background_normal='', background_active='',
                                background_color=(0, 0, 0, 0),
                                padding=[dp(2), dp(13), 0, 0], size_hint_x=1)
        self.add_widget(self.editor)
        if password:
            toggle = Button(text='Mostrar', color=ORANGE, font_size=dp(12), bold=True,
                            background_normal='', background_down='',
                            background_color=(0, 0, 0, 0),
                            size_hint_x=None, width=dp(62))
            def flip(btn):
                self.editor.password = not self.editor.password
                btn.text = 'Mostrar' if self.editor.password else 'Ocultar'
            toggle.bind(on_release=flip)
            self.add_widget(toggle)


def make_auth_page(title, subtitle, register=False):
    """Retorna root, cartão e conteúdo rolável para tablets/celulares."""
    root = BoxLayout(orientation='vertical')
    with root.canvas.before:
        Color(*CREAM)
        bg = RoundedRectangle(pos=root.pos, size=root.size, radius=[0])
    root.bind(pos=lambda w, _: setattr(bg, 'pos', w.pos),
              size=lambda w, _: setattr(bg, 'size', w.size))
    scroll = ScrollView(do_scroll_x=False, bar_width=dp(2),
                        scroll_type=['content', 'bars'])
    content = BoxLayout(orientation='vertical', spacing=dp(13),
                        padding=[dp(22), dp(14), dp(22), dp(25)],
                        size_hint_y=None)
    content.bind(minimum_height=content.setter('height'))
    scroll.add_widget(content)
    root.add_widget(scroll)

    brand = Image(
        source=os.path.join(
            os.path.dirname(__file__),
            'assets',
            'logo_volanchar.png'
        ),
        fit_mode='contain',
        size_hint_y=None,
        height=dp(155 if not register else 115)
    )
    content.add_widget(brand)

    content.add_widget(text(title, 25 if not register else 27,
                            True, INK, 43, 'center'))
    content.add_widget(text(subtitle, 13, False, MUTED, 40, 'center'))

    card = BoxLayout(orientation='vertical', spacing=dp(10),
                     padding=[dp(16), dp(19), dp(16), dp(18)], size_hint_y=None)
    card.bind(minimum_height=card.setter('height'))
    rounded(card, WHITE, 22)
    content.add_widget(card)
    return root, card, content


def field(card, label, hint, icon='user', password=False):
    card.add_widget(text(label, 12, True, INK, 23))
    entry = Entry(hint, icon, password)
    card.add_widget(entry)
    return entry.editor
