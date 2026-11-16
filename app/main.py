"""VôLanchar Android — interface Kivy conectada a uma API MySQL."""
import os
import base64
import re
import threading
import webbrowser
from urllib.parse import quote

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.switch import Switch
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image, AsyncImage
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse, Rectangle


from api import API, APIError
from ui_theme import FriendlyButton, NavButton, FriendlyField, surface, section, caption, PALE as THEME_PALE, \
    BORDER as THEME_BORDER

ORANGE = (.91, .29, .015, 1)
YELLOW = (1, .82, .22, 1)
BROWN = (.25, .10, .045, 1)
CREAM = (1, .975, .949, 1)
WHITE = (1, 1, 1, 1)
GREEN = (.10, .52, .31, 1)
GRAY = (.43, .39, .36, 1)
LIGHT = (1, .92, .80, 1)
PALE = (1, .947, .891, 1)
MUTED = (.65, .58, .52, 1)


def money(c):
    return 'R$ ' + f'{c / 100:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


class VectorIcon(Widget):

    def __init__(self, kind='user', tint=WHITE, **kwargs):
        super().__init__(**kwargs)
        self.kind = kind
        self.tint = tint
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        x, y = self.pos;
        w, h = self.size
        if w <= 0 or h <= 0: return
        side = min(w, h, dp(23));
        a = x + (w - side) / 2;
        b = y + (h - side) / 2
        sw = max(dp(1.5), side * .085)
        with self.canvas:
            Color(*self.tint)
            if self.kind == 'user':
                Ellipse(pos=(a + side * .35, b + side * .50), size=(side * .30, side * .30))
                Line(ellipse=(a + side * .16, b + side * .04, side * .68, side * .40, 0, 180), width=sw)
            elif self.kind == 'cart':
                Line(points=[a + side * .08, b + side * .78, a + side * .23, b + side * .78, a + side * .36,
                             b + side * .29, a + side * .82, b + side * .29, a + side * .91, b + side * .68,
                             a + side * .28, b + side * .68], width=sw, cap='round', joint='round')
                Ellipse(pos=(a + side * .34, b + side * .11), size=(side * .12, side * .12))
                Ellipse(pos=(a + side * .73, b + side * .11), size=(side * .12, side * .12))
            elif self.kind == 'pin':
                Line(ellipse=(a + side * .19, b + side * .31, side * .62, side * .62, 0, 360), width=sw)
                Line(points=[a + side * .21, b + side * .50, a + side * .50, b + side * .06, a + side * .79,
                             b + side * .50], width=sw, cap='round', joint='round')
                Ellipse(pos=(a + side * .41, b + side * .61), size=(side * .18, side * .18))
            elif self.kind == 'mail':
                Line(rounded_rectangle=(a + side * .13, b + side * .24, side * .74, side * .54, side * .05), width=sw)
                Line(points=[a + side * .15, b + side * .72, a + side * .50, b + side * .48, a + side * .85,
                             b + side * .72], width=sw)
            elif self.kind == 'phone':
                Line(rounded_rectangle=(a + side * .29, b + side * .10, side * .42, side * .80, side * .08), width=sw)
                Ellipse(pos=(a + side * .46, b + side * .17), size=(side * .08, side * .08))
            elif self.kind == 'camera':
                Line(rounded_rectangle=(a + side * .12, b + side * .20, side * .76, side * .54, side * .07), width=sw)
                Line(rectangle=(a + side * .28, b + side * .74, side * .24, side * .09), width=sw)
                Line(circle=(a + side * .50, b + side * .47, side * .16), width=sw)
            elif self.kind == 'menu':
                for yy in (.26, .5, .74): Line(points=[a + side * .15, b + side * yy, a + side * .85, b + side * yy],
                                               width=sw, cap='round')
            elif self.kind == 'bag':
                Line(rounded_rectangle=(a + side * .16, b + side * .13, side * .68, side * .63, side * .08), width=sw)
                Line(points=[a + side * .31, b + side * .66, a + side * .31, b + side * .84, a + side * .69,
                             b + side * .84, a + side * .69, b + side * .66], width=sw)
            elif self.kind == 'lock':
                Line(rounded_rectangle=(a + side * .22, b + side * .12, side * .56, side * .49, side * .07), width=sw)
                Line(ellipse=(a + side * .31, b + side * .45, side * .38, side * .43, 0, 180), width=sw)
            else:
                Line(rounded_rectangle=(a + side * .14, b + side * .18, side * .72, side * .62, side * .09), width=sw)
                Line(points=[a + side * .30, b + side * .48, a + side * .46, b + side * .32, a + side * .72,
                             b + side * .63], width=sw)


class VoLanchar(App):
    title = 'VôLanchar'

    # Espaços reais reservados às barras do Android (valores em pixels Kivy).
    safe_top = NumericProperty(0)
    safe_bottom = NumericProperty(0)

    def on_start(self):
        # A janela Android só fornece os insets depois da primeira disposição da tela.
        if platform == 'android':
            Clock.schedule_once(self._update_android_safe_area, 0)
            Clock.schedule_once(self._update_android_safe_area, 0.3)
            Clock.schedule_once(self._update_android_safe_area, 1.0)
            Window.bind(size=lambda *_: Clock.schedule_once(self._update_android_safe_area, 0))

    def _update_android_safe_area(self, *_):
        """Mantém todo o app dentro das barras de status e navegação do Android.

        Em Android 15+ (target 35/36), a janela pode ser edge-to-edge.
        O Android fornece os espaços ocupados pelas barras em pixels físicos;
        os tamanhos dos widgets Kivy também são em pixels físicos.
        """
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            Activity = autoclass('org.kivy.android.PythonActivity')
            activity = Activity.mActivity
            if activity is None:
                return
            decor = activity.getWindow().getDecorView()
            insets = decor.getRootWindowInsets()
            if insets is None:
                return
            try:
                InsetsType = autoclass('android.view.WindowInsets$Type')
                mask = InsetsType.systemBars() | InsetsType.displayCutout()
                bars = insets.getInsets(mask)
                top = max(0, int(bars.top))
                bottom = max(0, int(bars.bottom))
            except Exception:
                # Fallback para dispositivos Android mais antigos.
                top = max(0, int(insets.getSystemWindowInsetTop()))
                bottom = max(0, int(insets.getSystemWindowInsetBottom()))
            self.safe_top = top
            self.safe_bottom = bottom
            self._safe_top_spacer.height = top
            self._safe_bottom_spacer.height = bottom
        except Exception as exc:
            print('VôLanchar: não foi possível ler as barras do Android:', exc)

    def build(self):
        icon_path = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'icone_volanchar.png'
        )

        if os.path.isfile(icon_path):
            self.icon = icon_path
            Window.set_icon(icon_path)

        Window.clearcolor = CREAM
        # Tamanho de referência para teste no computador: Android, 393 × 852.
        if platform in ('win', 'linux', 'macosx'):
            Window.size = (393, 852)
            Window.minimum_width = 345
            Window.minimum_height = 650
        # Endereço interno. Para APK físico, configure VOLANCHAR_API_URL no arquivo app/config.py.
        # Android nunca usa 127.0.0.1 para acessar o Flask no computador.
        from config import VOLANCHAR_API_URL
        self.api = API(os.getenv('VOLANCHAR_API', VOLANCHAR_API_URL))
        self.google_id_token = None
        self._google_waiting = False
        self.user = None
        self.mode = 'buyer'
        self.points = []
        self.offers = []
        self.cart = {}
        self.selected_seller = None
        self.product_ids = []
        self.registration_visible = False
        self._store_data = None
        self.profile_photo = None
        self.product_photo = None
        self.root_manager = ScreenManager()
        self._history = []
        self._navigating_back = False
        Window.bind(on_keyboard=self._handle_android_back)
        # A área segura envolve o ScreenManager inteiro. Assim todas as telas,
        # inclusive login/cadastro e abas, respeitam as barras do tablet.
        safe_root = BoxLayout(orientation='vertical', spacing=0)
        self._safe_top_spacer = Widget(size_hint_y=None, height=0)
        self._safe_bottom_spacer = Widget(size_hint_y=None, height=0)
        safe_root.add_widget(self._safe_top_spacer)
        safe_root.add_widget(self.root_manager)
        safe_root.add_widget(self._safe_bottom_spacer)
        self.show('Acesso', self.access_screen)
        return safe_root

    def _handle_android_back(self, window, key, *args):
        if key not in (27, 1001):
            return False
        if self.root_manager.current == 'Acesso':
            return False
        self.go_back()
        return True

    def go_back(self):
        """Voltar contextual: no máximo dois passos até o Início, sem pilha de abas."""
        current = self.root_manager.current
        if not self.user:
            # Telas de autenticação retornam ao login, sem visitar formulários antigos.
            if current != 'Acesso':
                self.show('Acesso', self.access_screen)
            return
        # Telas secundárias retornam à aba a que pertencem.
        # Ações de compra preservam o carrinho e voltam à vitrine.
        if current == 'Carrinho':
            self.open_offers()
        elif current in ('Produtos', 'Loja'):
            self.show('Inicio', self.home_screen)
        elif current in ('Recuperar', 'Redefinir senha', 'Alterar senha'):
            self.open_profile()
        elif current in ('Google cadastro', 'Cadastro', 'Escolha de perfil'):
            self.show('Inicio', self.home_screen)
        elif current != 'Inicio':
            # Mapa, Vitrine, Pedidos e Perfil são destinos principais.
            self.show('Inicio', self.home_screen)
        else:
            # Já está no destino inicial: não retorna a páginas antigas.
            self.alert('Você já está na tela inicial.')
        self._history.clear()

    def request(self, path, method='GET', data=None, done=None, on_error=None):
        # Uma indicação discreta de atividade evita cliques repetidos enquanto a API responde.
        self._pending_requests = getattr(self, '_pending_requests', 0) + 1
        self._set_loading(True)

        def worker():
            try:
                result = self.api.call(path, method, data)

                def succeed(_):
                    self._set_loading(False)
                    if done: done(result)

                Clock.schedule_once(succeed, 0)
            except APIError as e:
                msg = str(e)

                def failed(_):
                    self._set_loading(False)
                    (on_error or self.alert)(msg)

                Clock.schedule_once(failed, 0)
            except Exception as e:
                msg = str(e)
                Clock.schedule_once(
                    lambda _: (self._set_loading(False), (on_error or self.alert)('Erro inesperado: ' + msg)), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _set_loading(self, show):
        if show:
            if getattr(self, '_loading_popup', None): return
            panel = BoxLayout(orientation='vertical', padding=dp(18))
            panel.add_widget(Label(text='Carregando...\nAguarde a resposta do VôLanchar.', color=WHITE,
                                   halign='center', valign='middle'))
            popup = Popup(title='VôLanchar', content=panel, size_hint=(.77, .23),
                          auto_dismiss=False, separator_color=ORANGE)
            self._loading_popup = popup
            popup.open()
        else:
            self._pending_requests = max(0, getattr(self, '_pending_requests', 1) - 1)
            if self._pending_requests == 0 and getattr(self, '_loading_popup', None):
                self._loading_popup.dismiss()
                self._loading_popup = None

    def alert(self, msg):
        pane = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(14))
        label = Label(text=msg, color=WHITE, halign='center', valign='middle')
        label.bind(size=lambda x, y: setattr(x, 'text_size', (x.width, None)))
        pane.add_widget(label)
        btn = self.button('OK');
        pane.add_widget(btn)
        popup = Popup(title='VôLanchar', content=pane, size_hint=(.86, .35))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def label(self, text, size=17, bold=False, height=45, color=BROWN):
        l = Label(text=text, font_size=dp(size), bold=bold, color=color, size_hint_y=None, height=dp(height),
                  halign='left', valign='middle')
        l.bind(size=lambda instance, _: setattr(instance, 'text_size', (instance.width, None)))
        return l

    def button(self, text, action=None, color=ORANGE, height=48, icon=None):
        # Normaliza pictogramas para evitar quadrados vazios no Android/Windows.
        icon_map = {'🛒': 'cart', '📍': 'pin', '📷': 'camera', '🍔': 'bag', '🍟': 'menu', '👤': 'user', '📋': 'menu'}
        for emoji, kind in icon_map.items():
            if emoji in text:
                text = text.replace(emoji, '').strip()
                icon = icon or kind
        b = Button(text=text, background_normal='', background_down='', background_color=(0, 0, 0, 0),
                   color=WHITE, bold=True, font_size=dp(14), size_hint_y=None, height=dp(height))
        with b.canvas.before:
            Color(*color)
            rect = RoundedRectangle(pos=b.pos, size=b.size, radius=[dp(18)])
        b.bind(pos=lambda w, _: setattr(rect, 'pos', w.pos), size=lambda w, _: setattr(rect, 'size', w.size))
        if icon:
            glyph = VectorIcon(kind=icon, tint=WHITE, size_hint=(None, None), size=(dp(24), dp(24)))
            b.add_widget(glyph)

            def place_icon(*_):
                glyph.pos = (b.x + dp(15), b.center_y - glyph.height / 2)

            b.bind(pos=place_icon, size=place_icon)
            b.text = '     ' + text
            place_icon()
        if action: b.bind(on_release=lambda _: action())
        return b

    def input(self, hint, password=False):
        return TextInput(hint_text=hint, multiline=False, password=password, font_size=dp(15),
                         size_hint_y=None, height=dp(45), padding=[dp(12), dp(10)],
                         background_normal='', background_active='', background_color=WHITE,
                         foreground_color=BROWN, cursor_color=ORANGE,
                         hint_text_color=MUTED)

    def panel(self, parent, title, subtitle=''):
        return section(parent, title, subtitle)

    def page(self, title, back=None):
        """Cabeçalho consistente, retorno em cada tela e navegação inferior fixa."""
        wrapper = BoxLayout(orientation='vertical', spacing=0)
        with wrapper.canvas.before:
            Color(*CREAM)
            bg = Rectangle(pos=wrapper.pos, size=wrapper.size)
        wrapper.bind(pos=lambda w, _: setattr(bg, 'pos', w.pos),
                     size=lambda w, _: setattr(bg, 'size', w.size))

        header = FloatLayout(
            size_hint_y=None,
            height=dp(78)
        )

        # Botão Voltar fixo à esquerda
        if title != 'Acesso':
            back_btn = FriendlyButton(
                'Voltar',
                back or self.go_back,
                kind='soft',
                height=39,
                icon='back'
            )
            back_btn.size_hint = (None, None)
            back_btn.size = (dp(92), dp(39))
            # Espaçamento de 14 dp da borda esquerda.
            back_btn.pos_hint = {'center_y': 0.5}
            header.add_widget(back_btn)

            def position_back_button(*_):
                back_btn.x = header.x + dp(14)

            header.bind(pos=position_back_button, size=position_back_button)
            Clock.schedule_once(lambda _dt: position_back_button(), 0)

        # Logo centralizada
        logo_path = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'logo_volanchar.png'
        )

        brand = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(dp(180), dp(73)),
            pos_hint={
                'center_x': 0.5,
                'center_y': 0.5
            },
            spacing=dp(1)
        )

        logo = Image(
            source=logo_path,
            fit_mode='contain',
            size_hint_y=None,
            height=dp(49)
        )

        brand.add_widget(logo)

        screen_title = Label(
            text=title,
            font_size=dp(11),
            color=GRAY,
            size_hint_y=None,
            height=dp(20),
            halign='center',
            valign='middle'
        )

        screen_title.bind(
            size=lambda instance, _: setattr(
                instance, 'text_size',
                instance.size
            )
        )

        brand.add_widget(screen_title)
        header.add_widget(brand)

        wrapper.add_widget(header)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(orientation='vertical', padding=[dp(15), dp(9), dp(15), dp(14)],
                            spacing=dp(9), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        scroll.add_widget(content)
        self._page_scroll = scroll
        wrapper.add_widget(scroll)
        if self.user:
            nav = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60),
                            spacing=0, padding=[dp(5), dp(2), dp(5), dp(3)])
            surface(nav, WHITE, 15)
            # Cada perfil acessa suas funções principais com ícones próprios.
            if self.mode == 'seller':
                items = [
                    ('Início', lambda: self.show('Inicio', self.home_screen), 'home'),
                    ('Minha loja', self.open_store, 'store'),
                    ('Cardápio', self.open_products, 'products'),
                    ('Vendas', self.open_orders, 'orders'),
                    ('Perfil', self.open_profile, 'profile'),
                ]
                current = {
                    'Ponto de venda': 'Minha loja',
                    'Meu cardápio': 'Cardápio',
                    'Pedidos': 'Vendas',
                    'Detalhes do pedido': 'Vendas',
                    'Meu perfil': 'Perfil',
                }.get(title, title)
            else:
                items = [
                    ('Início', lambda: self.show('Inicio', self.home_screen), 'home'),
                    ('Mapa', self.open_map, 'map'),
                    ('Vitrine', self.open_offers, 'products'),
                    ('Pedidos', self.open_orders, 'orders'),
                    ('Perfil', self.open_profile, 'profile'),
                ]
                current = {
                    'Ofertas': 'Vitrine',
                    'Carrinho': 'Vitrine',
                    'Detalhes do pedido': 'Pedidos',
                    'Meu perfil': 'Perfil',
                }.get(title, title)
            for name, callback, icon_name in items:
                nav.add_widget(NavButton(name, callback, active=current == name, icon=icon_name))
            wrapper.add_widget(nav)
        return wrapper, content

    def show(self, name, constructor):
        current = self.root_manager.current if self.root_manager.screens else ''
        current_builder = getattr(self, '_current_builder', None)
        # Não guarde o estado da mesma tela quando filtros ou quantidades recarregarem.
        if (not self._navigating_back and current and current != name
                and current_builder is not None and current not in
                ('Inicio', 'Mapa', 'Ofertas', 'Pedidos', 'Perfil')):
            self._history.append((current, current_builder))
            self._history = self._history[-12:]
        if name == 'Acesso':
            self._history.clear()
        if self.root_manager.has_screen(name):
            self.root_manager.remove_widget(self.root_manager.get_screen(name))
        screen = Screen(name=name)
        screen.add_widget(constructor())
        self.root_manager.add_widget(screen)
        self.root_manager.current = name
        self._current_builder = constructor

    def _auth_shell(self, title, subtitle, register=False):
        """Cabeçalho ilustrado, hierarquia visual e formulário rolável no Android."""
        outer = BoxLayout(orientation='vertical', spacing=0)
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=[dp(20), dp(12), dp(20), dp(22)],
                            size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        scroll.add_widget(content)
        outer.add_widget(scroll)
        # Faixa ilustrativa do campus; é decoração, não um botão do aplicativo.
        background_path = os.path.join(os.path.dirname(__file__), 'assets', 'campus_banner.jpg')
        if os.path.isfile(background_path):
            hero = FloatLayout(size_hint_y=None, height=dp(130 if not register else 96))
            hero.add_widget(Image(source=background_path, fit_mode='cover', size_hint=(1, 1)))
            content.add_widget(hero)
        identity = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(73), spacing=dp(2))
        identity.add_widget(self.label('VôLanchar', 31, True, dp(44), ORANGE))
        identity.add_widget(self.label('O lanche pertim. O bucho chein.', 13, True, dp(24), BROWN))
        content.add_widget(identity)
        card = BoxLayout(orientation='vertical', spacing=dp(9), padding=[dp(18), dp(17)], size_hint_y=None)
        card.bind(minimum_height=card.setter('height'))
        with card.canvas.before:
            Color(*WHITE)
            surface = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(24)])
        card.bind(pos=lambda w, _: setattr(surface, 'pos', w.pos), size=lambda w, _: setattr(surface, 'size', w.size))
        card.add_widget(self.label(title, 21, True, dp(37)))
        card.add_widget(self.label(subtitle, 13, False, dp(41), GRAY))
        content.add_widget(card)
        return outer, card, content

    def hint(self, parent, text):
        parent.add_widget(self.label(text, 12, True, dp(21), BROWN))

    def secondary_button(self, text, action):
        return self.button(text, action, color=BROWN, height=43)

    def access_screen(self):
        """Login reconstruído com componentes visuais reais e responsivos."""
        from auth_ui import make_auth_page, field, button, text, ORANGE, MUTED
        outer, card, content = make_auth_page('Que bom ter você aqui!',
                                              'Entre para comprar ou vender lanches na UFRPE.')
        self.login_identifier = field(card, 'E-mail ou telefone',
                                      'E-mail ou (81) 99999-9999', 'mail')
        self.login_password = field(card, 'Senha', 'Digite sua senha', 'lock', True)
        card.add_widget(button('Entrar no VôLanchar', self.sign_in, icon='arrow'))
        card.add_widget(button('Continuar com Google', self.google_sign_in, solid=False))
        recover = self.button('Esqueceu sua senha?', lambda: self.show('Recuperar', self.forgot_screen),
                              color=WHITE, height=40)
        recover.color = ORANGE
        card.add_widget(recover)
        content.add_widget(text('Ainda não tem uma conta?', 13, False, MUTED, 26, 'center'))
        content.add_widget(button('Criar minha conta',
                                  lambda: self.show('Cadastro', self.register_screen), solid=False))
        content.add_widget(text('O lanche pertim. O bucho chein.', 12, True, MUTED, 25, 'center'))
        return outer

    def forgot_screen(self):
        outer, card, content = self._auth_shell('Esqueceu sua senha?',
                                                'Vamos enviar um código para seu e-mail cadastrado.')
        self.hint(card, 'E-mail cadastrado')
        self.reset_email = self.input('seuemail@exemplo.com')
        card.add_widget(self.reset_email)
        card.add_widget(self.button('Enviar código', self.send_reset_code, icon='lock'))
        card.add_widget(
            self.label('O código expira em 15 minutos. Verifique também o spam.', 11, height=36, color=GRAY))
        content.add_widget(self.secondary_button('Voltar para entrar', lambda: self.show('Acesso', self.access_screen)))
        return outer

    def send_reset_code(self):
        email = self.reset_email.text.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            self.alert('Informe o e-mail cadastrado.');
            return
        self.request('/senha/solicitar', 'POST', {'email': email},
                     lambda _: self.show('NovaSenha', self.reset_password_screen))

    def reset_password_screen(self):
        outer, card, content = self._auth_shell('Recuperar acesso', 'Digite o código enviado ao seu e-mail.')
        self.hint(card, 'Código de 8 dígitos')
        self.reset_code = self.input('Código recebido');
        card.add_widget(self.reset_code)
        self.hint(card, 'Nova senha')
        self.reset_new = self.input('Mínimo de 8 caracteres', True);
        card.add_widget(self.reset_new)
        self.hint(card, 'Repita a nova senha')
        self.reset_confirm = self.input('Confirme a nova senha', True);
        card.add_widget(self.reset_confirm)
        card.add_widget(self.button('Redefinir senha', self.confirm_reset, icon='lock'))
        content.add_widget(self.secondary_button('Voltar para entrar', lambda: self.show('Acesso', self.access_screen)))
        return outer

    def confirm_reset(self):
        pwd = self.reset_new.text
        if not re.fullmatch(r'[0-9]{8}', self.reset_code.text.strip()):
            self.alert('Informe o código de 8 dígitos.');
            return
        if len(pwd) < 8: self.alert('A nova senha deve ter no mínimo 8 caracteres.');return
        if pwd != self.reset_confirm.text: self.alert('As senhas não coincidem.');return
        email = self.reset_email.text.strip().lower()
        data = {'email': email, 'codigo': self.reset_code.text.strip(), 'nova_senha': pwd}

        def done(_):
            self.show('Acesso', self.access_screen)
            self.alert('Senha redefinida! Entre com sua nova senha.')

        self.request('/senha/redefinir', 'POST', data, done)

    def register_screen(self):
        """Cadastro com a mesma identidade visual e os campos reais da API."""
        from auth_ui import make_auth_page, field, button, text, MUTED
        outer, card, content = make_auth_page('Criar conta',
                                              'Preencha seus dados para começar.', register=True)
        self.name_input = field(card, 'Nome completo', 'Seu nome completo', 'user')
        self.email_input = field(card, 'E-mail', 'seu@email.com', 'mail')
        self.phone_input = field(card, 'WhatsApp com DDD', 'Ex.: 81999998888', 'phone')
        self.phone_input.input_filter = 'int'
        self.pw_input = field(card, 'Senha', 'Mínimo de 8 caracteres', 'lock', True)
        card.add_widget(button('Criar conta  →', self.sign_up))
        content.add_widget(text('Já tem uma conta?', 13, False, MUTED, 24, 'center'))
        content.add_widget(button('Voltar para entrar',
                                  lambda: self.show('Acesso', self.access_screen), solid=False))
        return outer

    def _display_phone(self, value):
        """Mostra apenas DDD e telefone, sem máscara nem DDI, durante a edição."""
        digits = re.sub(r'\D', '', str(value or ''))
        if len(digits) == 13 and digits.startswith('55'):
            digits = digits[2:]
        return digits

    def _normalize_phone(self, value):
        """Valida celular brasileiro (DDD + 9 dígitos) antes de enviar à API."""
        digits = self._display_phone(value)
        if not re.fullmatch(r'[1-9][0-9]9[0-9]{8}', digits):
            return None
        return '55' + digits

    # Login Google via Google Play Services (fluxo legado do protótipo Kivy).
    # A interface é atualizada sempre pela thread do Kivy.
    def google_sign_in(self):
        if platform != 'android':
            self.alert('O login com Google deve ser testado na APK Android.');
            return
        if self._google_waiting: return
        try:
            from google_config import GOOGLE_WEB_CLIENT_ID
            client_id = GOOGLE_WEB_CLIENT_ID.strip()
            if (not re.fullmatch(r'[0-9]+-[a-zA-Z0-9_-]+\.apps\.googleusercontent\.com', client_id)
                    or 'COLE_AQUI' in client_id.upper()):
                self.alert('Configure o Client ID Web em google_config.py antes de compilar.');
                return
            from jnius import autoclass
            from android import activity
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            SignInOptions = autoclass('com.google.android.gms.auth.api.signin.GoogleSignInOptions')
            Builder = autoclass('com.google.android.gms.auth.api.signin.GoogleSignInOptions$Builder')
            SignIn = autoclass('com.google.android.gms.auth.api.signin.GoogleSignIn')
            options = Builder(SignInOptions.DEFAULT_SIGN_IN).requestEmail().requestIdToken(client_id).build()
            self._google_client = SignIn.getClient(PythonActivity.mActivity, options)
            activity.bind(on_activity_result=self._google_activity_result)
            self._google_waiting = True
            PythonActivity.mActivity.startActivityForResult(self._google_client.getSignInIntent(), 7607)
        except Exception as exc:
            self._google_waiting = False
            try:
                from android import activity
                activity.unbind(on_activity_result=self._google_activity_result)
            except Exception:
                pass
            self.alert('Não foi possível abrir o login Google: ' + type(exc).__name__)

    def _google_activity_result(self, request_code, result_code, intent):
        if request_code != 7607: return
        # O callback Android pode chegar fora da thread principal do Kivy.
        Clock.schedule_once(lambda _dt: self._handle_google_result(result_code, intent), 0)

    def _google_error_message(self, exc):
        # Nunca imprimir o ID token nem credenciais nos alertas.
        description = str(exc)
        match = re.search(r'(?:statusCode|ApiException|status)\s*[:= ]\s*(\d+)', description, re.I)
        if not match:
            match = re.search(r'(?<!\d)(10|12500|12501|12502)(?!\d)', description)
        if match:
            code = match.group(1)
            explanation = {'10': 'Configuração OAuth: confira pacote, SHA-1 e Client ID Web.',
                           '12500': 'Falha de autenticação: confira o Google Cloud e a conta.',
                           '12501': 'O login foi cancelado.',
                           '12502': 'Já existe uma tentativa de login em andamento.'}.get(code,
                                                                                          'Verifique as configurações OAuth.')
            return 'Google retornou código ' + code + '. ' + explanation
        return 'Não foi possível autenticar com o Google (' + type(exc).__name__ + '). Consulte o Logcat.'

    def _handle_google_result(self, result_code, intent):
        self._google_waiting = False
        try:
            from android import activity
            activity.unbind(on_activity_result=self._google_activity_result)
        except Exception:
            pass
        if intent is None:
            self.alert('Login Google cancelado ou sem resposta do Android.');
            return
        try:
            from jnius import autoclass, cast
            SignIn = autoclass('com.google.android.gms.auth.api.signin.GoogleSignIn')
            task = SignIn.getSignedInAccountFromIntent(intent)
            try:
                account = cast('com.google.android.gms.auth.api.signin.GoogleSignInAccount', task.getResult())
            except Exception as exc:
                self.alert(self._google_error_message(exc));
                return
            token = account.getIdToken() if account else None
            if not token:
                self.alert('O Google não forneceu o token de identificação. Confira o Client ID Web.');
                return
            self.google_id_token = str(token)
            self.request('/google/entrar', 'POST', {'id_token': self.google_id_token}, self._google_result)
        except Exception as exc:
            self.alert(self._google_error_message(exc))

    def _google_result(self, data):
        etapa = data.get('etapa')
        if etapa in ('cadastro', 'vincular'):
            self.google_stage = etapa
            self.google_name = data.get('nome', '')
            self.google_email = data.get('email', '')
            self.show('GoogleCompletar', self.google_complete_screen)
        else:
            self.google_id_token = None
            self._logged_in(data)

    def google_complete_screen(self):
        is_link = getattr(self, 'google_stage', 'cadastro') == 'vincular'
        title = 'Vincular conta existente' if is_link else 'Concluir cadastro Google'
        subtitle = ('Sua conta já existe. Informe a senha para vincular o Google.' if is_link
                    else 'Informe seu WhatsApp e crie uma senha para o perfil e a segurança da conta.')
        outer, card, content = self._auth_shell(title, subtitle, register=True)
        card.add_widget(self.label(self.google_email, 12, height=dp(28), color=GRAY))
        if is_link:
            self.google_password = self.input('Senha atual do VôLanchar', True)
            card.add_widget(self.google_password)
        else:
            self.hint(card, 'Nome completo')
            self.google_user_name = self.input('Seu nome')
            self.google_user_name.text = self.google_name
            card.add_widget(self.google_user_name)
            self.hint(card, 'WhatsApp • DDD 81')
            self.google_phone = self.input('DDD + celular: 81999998888')
            self.google_phone.input_filter = 'int'
            card.add_widget(self.google_phone)
            self.hint(card, 'Crie uma senha para o VôLanchar')
            self.google_password = self.input('Mínimo de 8 caracteres', True)
            card.add_widget(self.google_password)
        card.add_widget(self.button('Vincular e entrar' if is_link else 'Concluir e entrar', self.google_complete))
        content.add_widget(self.secondary_button('Voltar ao login', lambda: self.show('Acesso', self.access_screen)))
        return outer

    def google_complete(self):
        if not self.google_id_token:
            self.alert('Repita o login com Google.');
            return
        payload = {'id_token': self.google_id_token, 'senha': self.google_password.text}
        if getattr(self, 'google_stage', 'cadastro') == 'cadastro':
            phone = self._normalize_phone(self.google_phone.text)
            if not phone: self.alert('Informe 11 dígitos: DDD + celular (ex.: 81999998888).');return
            if len(self.google_user_name.text.strip()) < 2: self.alert('Informe seu nome.');return
            payload.update({'nome': self.google_user_name.text.strip(), 'telefone': phone})
        if len(payload['senha']) < 8:
            self.alert('Informe uma senha de pelo menos 8 caracteres.');
            return
        self.request('/google/entrar', 'POST', payload, self._google_result)

    def _logged_in(self, result):
        self.api.token = result['token'];
        self.user = result['usuario'];
        self.mode = 'buyer'
        self.registration_visible = False
        self.show('Escolha de perfil', self.mode_screen)

    def sign_in(self):
        identifier = self.login_identifier.text.strip()
        password = self.login_password.text
        if not identifier:
            self.alert('Informe seu e-mail ou telefone para entrar.');
            return
        if not password:
            self.alert('Informe sua senha para entrar.');
            return
        self._authenticate('/entrar', {'identificador': identifier, 'senha': password})

    def sign_up(self):
        if getattr(self, '_signup_pending', False): return
        nome = self.name_input.text.strip();
        email = self.email_input.text.strip()
        phone = self._normalize_phone(self.phone_input.text)
        password = self.pw_input.text
        if len(nome) < 2: self.alert('Informe seu nome completo.');return
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email): self.alert('Informe um e-mail válido.');return
        if not phone: self.alert('Informe 11 dígitos: DDD + celular (ex.: 81999998888).');return
        if len(password) < 8: self.alert('A senha deve ter pelo menos 8 caracteres.');return
        self._signup_pending = True
        self.request('/registrar', 'POST', {'nome': nome, 'email': email, 'telefone': phone, 'senha': password},
                     lambda result: (setattr(self, '_signup_pending', False), self._logged_in(result)),
                     on_error=lambda msg: (setattr(self, '_signup_pending', False), self.alert(msg)))

    def _authenticate(self, endpoint, data):
        self.request(endpoint, 'POST', data, self._logged_in)

    def mode_screen(self):
        box, c = self.page('Escolha de perfil', lambda: self.show('Inicio', self.home_screen))
        c.add_widget(self.label('Como quer aproveitar o campus?', 21, True, dp(54)))
        c.add_widget(self.label('Use a mesma conta para comprar ou vender. Escolha seu espaço.',
                                12, height=dp(38), color=GRAY))
        for title, summary, mode, icon in (
                ('Comprador', 'Descubra lanches e faça sua solicitação.', 'buyer', 'cart'),
                ('Vendedor', 'Monte a vitrine da sua loja e gerencie os pedidos.', 'seller', 'bag')):
            block = self.panel(c, title, summary)
            row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
            row.add_widget(VectorIcon(kind=icon, tint=ORANGE, size_hint_x=None, width=dp(35)))
            row.add_widget(FriendlyButton('Continuar como ' + title,
                                          lambda m=mode: self.choose_mode(m),
                                          kind='primary' if mode == 'buyer' else 'dark'))
            block.add_widget(row)
        return box

    def choose_mode(self, mode):
        self.mode = mode
        self.show('Inicio', self.home_screen)

    def home_screen(self):
        box, c = self.page('Início')
        name = (self.user or {}).get('nome', '').split(' ')[0]
        c.add_widget(self.label('Oi, ' + name + '!', 24, True, dp(46)))
        c.add_widget(self.label('O lanche pertim. O bucho chein.', 12, height=dp(24), color=GRAY))
        mode = 'Comprando' if self.mode == 'buyer' else 'Vendendo'
        profile = self.panel(c, 'Seu modo: ' + mode)
        profile.add_widget(FriendlyButton('Trocar perfil',
                                          lambda: self.show('Escolha de perfil', self.mode_screen), kind='soft',
                                          height=41, icon='profile'))
        if self.mode == 'buyer':
            hero = self.panel(c, 'Bateu a fome?', 'Escolha um lanche ou continue seu pedido.')
            hero.add_widget(FriendlyButton('Ver meu carrinho',
                                           lambda: self.show('Carrinho', self.cart_screen), kind='primary', icon='cart',
                                           height=44))
            # Vitrine, Mapa, Pedidos e Perfil já estão acessíveis no menu inferior.
        else:
            state = self.panel(c, 'Vendendo agora', 'Ative sua loja para aparecer na vitrine.')
            line = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48))
            self.home_status = self.label('Buscando disponibilidade...', 12, height=48, color=GRAY)
            line.add_widget(self.home_status)
            self.home_switch = Switch(active=False, size_hint=(None, None), size=(dp(68), dp(47)))
            self.home_switch.disabled = True
            line.add_widget(self.home_switch)
            state.add_widget(line)
            self.request('/minha-loja', done=self._load_home_store)
            store = self.panel(c, 'Gerenciar vendas')
            actions = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(44), spacing=dp(8))
            actions.add_widget(FriendlyButton('Minha loja', self.open_store, icon='store', height=44))
            actions.add_widget(FriendlyButton('Cardápio', self.open_products, kind='dark', icon='products', height=44))
            store.add_widget(actions)
        c.add_widget(FriendlyButton('Sair da conta', self.logout, kind='soft', icon='logout', height=42))
        return box

    def _load_home_store(self, data):
        loja = data.get('loja') or {}
        self._store_data = loja
        self.home_switch.active = bool(loja.get('vendendo'))
        self.home_switch.disabled = False
        self.home_status.text = 'Disponível agora' if loja.get('vendendo') else 'Pausado • fora das buscas'
        self.home_switch.bind(active=self._change_home_status)

    def _change_home_status(self, widget, active):
        loja = self._store_data or {}
        if not loja.get('id_ponto') or not loja.get('whatsapp'):
            widget.unbind(active=self._change_home_status)
            widget.active = False
            widget.bind(active=self._change_home_status)
            self.alert('Configure primeiro o ponto de venda e o WhatsApp em Meu ponto de venda.');
            return
        widget.disabled = True
        payload = {'id_ponto': loja['id_ponto'], 'whatsapp': loja['whatsapp'], 'vendendo': bool(active)}

        def done(_):
            widget.disabled = False
            self._store_data['vendendo'] = int(active)
            self.home_status.text = 'Disponível agora' if active else 'Pausado • fora das buscas'

        def failed(msg):
            widget.unbind(active=self._change_home_status)
            widget.active = not active
            widget.bind(active=self._change_home_status)
            widget.disabled = False
            self.alert(msg)

        self.request('/minha-loja', 'POST', payload, done, on_error=failed)

    def switch_mode(self):
        self.mode = 'seller' if self.mode == 'buyer' else 'buyer'
        self.cart = {};
        self.selected_seller = None
        self.show('Inicio', self.home_screen)

    def logout(self):
        self.api.token = '';
        self.user = None;
        self.cart = {};
        self.mode = 'buyer'
        self.google_id_token = None
        self.registration_visible = False
        self.show('Acesso', self.access_screen)

    def load_points(self, cb):
        def done(d):
            self.points = d.get('pontos', [])
            cb()

        self.request('/pontos', done=done)

    def open_map(self):
        # A tela do mapa não depende de o banco já conter os nove pontos.
        self.show('Mapa', self.map_screen)

        # Atualização leve da lista de IDs existentes para filtragem de ofertas.
        def fetch():
            try:
                data = self.api.call('/pontos')
                Clock.schedule_once(lambda _: setattr(self, 'points', data.get('pontos', [])), 0)
            except Exception:
                pass  # O usuário ainda pode abrir o Google Maps e visualizar os locais.

        threading.Thread(target=fetch, daemon=True).start()

    def open_google_maps(self, point_name=None):
        from campus_google_maps import open_maps
        try:
            open_maps(point_name)
        except Exception as error:
            self.alert('Não foi possível abrir o Google Maps: ' + str(error))

    def choose_campus_point(self, point_name):
        # Escolher um local oferece ações distintas: mapa externo e ofertas internas.
        pane = BoxLayout(orientation='vertical', padding=dp(17), spacing=dp(12))
        pane.add_widget(self.label(point_name, 18, True, dp(37)))
        pane.add_widget(self.label('Escolha o que deseja consultar.', 12, height=dp(32), color=GRAY))
        popup = Popup(title='Ponto fixo de venda', content=pane, size_hint=(.88, None), height=dp(255))
        buttons = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        buttons.add_widget(
            FriendlyButton('Google Maps', lambda: (popup.dismiss(), self.open_google_maps(point_name)), icon='map',
                           height=45))
        buttons.add_widget(
            FriendlyButton('Ver ofertas', lambda: (popup.dismiss(), self.open_offers_by_point(point_name)), kind='dark',
                           icon='products', height=45))
        pane.add_widget(buttons)
        pane.add_widget(FriendlyButton('Cancelar', lambda: popup.dismiss(), kind='soft', height=40))
        popup.open()

    def open_offers_by_point(self, point_name):
        self.offer_term = ''
        # O botão do mapa funciona mesmo antes de cadastrar pontos novos no servidor.
        point = next((p for p in self.points if p.get('nome', '').casefold() == point_name.casefold()), None)
        if not point:
            self._show_missing_point_offers(point_name)
            return
        self.request('/ofertas?ponto=' + str(point['id']), done=lambda d: self.draw_offers(d.get('ofertas', [])))

    def _show_missing_point_offers(self, point_name):
        box, c = self.page('Vitrine', self.go_back)
        c.add_widget(self.label('Lanches em ' + point_name, 20, True, dp(53)))
        panel = self.panel(c, 'Ainda não há ofertas vinculadas a este ponto',
                           'Ainda não há vendedores vinculados a este local. Explore outros pontos disponíveis.')
        panel.add_widget(
            FriendlyButton('Explorar toda a vitrine', self.open_offers, kind='soft', icon='products', height=43))
        self.show('Ofertas', lambda: box)

    def map_screen(self):
        box, c = self.page('Mapa', self.go_back)
        c.add_widget(self.label('Mapa do Campus Recife', 21, True, dp(43)))
        c.add_widget(self.label('Locais fixos da UFRPE, sem GPS e sem localização pessoal.',
                                12, height=dp(37), color=GRAY))
        from campus_embedded_map import CAMPUS_POINTS, kivy_map_widget, show_android_google_map
        from google_maps_config import GOOGLE_MAPS_API_KEY
        try:
            # O mapa permanece na própria tela, com controles de zoom sobrepostos.
            map_container = FloatLayout(size_hint_y=None, height=dp(430))
            mapa = kivy_map_widget(on_point=self.open_offers_by_point)
            mapa.size_hint = (1, 1)
            mapa.pos_hint = {'x': 0, 'y': 0}
            map_container.add_widget(mapa)

            # O MapView recebe o tamanho definitivo apenas após o layout.
            # Centralizar depois evita abrir deslocado, fora dos nove pontos.
            # O ajuste acontece uma única vez; o usuário continua livre para
            # arrastar e usar zoom, sem o mapa voltar sozinho ao centro.
            def centralizar_mapa_inicial(_dt):
                mapa.zoom = 15
                mapa.center_on(-8.015663617171184, -34.9476168239989)

            Clock.schedule_once(centralizar_mapa_inicial, 0.2)

            # Os controles ficam dentro do mapa, sem abrir uma janela separada.
            for simbolo, direcao, topo in (('+', 1, 0.98), ('−', -1, 0.85)):
                botao = Button(
                    text=simbolo,
                    font_size=dp(25),
                    bold=True,
                    size_hint=(None, None),
                    size=(dp(44), dp(44)),
                    pos_hint={'right': 0.98, 'top': topo},
                    background_normal='',
                    background_down='',
                    background_color=ORANGE,
                    color=WHITE,
                )
                botao.bind(
                    on_release=lambda _btn, step=direcao: setattr(
                        mapa, 'zoom', max(12, min(19, mapa.zoom + step))
                    )
                )
                map_container.add_widget(botao)

            c.add_widget(map_container)
            c.add_widget(self.label(
                'Arraste o mapa ou use + e − para ajustar o zoom.',
                11, height=dp(30), color=GRAY
            ))
        except ImportError:
            panel = self.panel(c, 'Mapa interativo',
                               'Para ver o mapa dentro do app, instale: python -m pip install kivy_garden.mapview')
        if platform == 'android' and GOOGLE_MAPS_API_KEY:
            c.add_widget(FriendlyButton('Ver Google Maps dentro do VôLanchar',
                                        lambda: show_android_google_map(GOOGLE_MAPS_API_KEY), icon='map', height=45))
        elif platform == 'android':
            c.add_widget(self.label('Google Maps: configure a chave em google_maps_config.py.',
                                    11, height=dp(35), color=GRAY))
        c.add_widget(self.label('Escolha um dos nove pontos fixos', 16, True, dp(37)))
        for index in range(0, len(CAMPUS_POINTS), 2):
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(7))
            for name in CAMPUS_POINTS[index:index + 2]:
                row.add_widget(FriendlyButton(name,
                                              lambda n=name: self.open_offers_by_point(n), kind='soft', icon='map',
                                              height=48))
            c.add_widget(row)
        c.add_widget(self.label('Toque em um marcador para consultar as ofertas disponíveis.',
                                11, height=dp(50), color=GRAY))
        return box

    def open_store(self):
        self.load_points(lambda: self.show('Loja', self.store_screen))

    def store_screen(self):
        box, c = self.page('Ponto de venda', lambda: self.show('Inicio', self.home_screen))
        block = self.panel(c, 'Onde tu vai vender hoje?',
                           'Escolha o ponto da UFRPE e avise quando tiver lanche disponível.')
        c = block
        choices = {p['nome']: p['id'] for p in self.points}
        self.hint(c, 'Nome do estabelecimento')
        self.store_name = self.input('Ex.: Cantina da Ana')
        c.add_widget(self.store_name)
        self.point_spinner = Spinner(text='Escolha um ponto', values=list(choices), size_hint_y=None, height=dp(46),
                                     background_normal='', background_down='', background_color=(0, 0, 0, 0),
                                     color=BROWN)
        surface(self.point_spinner, THEME_PALE, 15, THEME_BORDER)
        c.add_widget(self.point_spinner)
        self.hint(c, 'WhatsApp para receber os pedidos')
        self.store_phone = self.input('DDD + celular: 81999998888')
        self.store_phone.input_filter = 'int'
        c.add_widget(self.store_phone)
        line = BoxLayout(size_hint_y=None, height=dp(52))
        line.add_widget(self.label('Disponível agora • Vendendo', 16));
        self.sell_checkbox = CheckBox(active=False, color=ORANGE);
        line.add_widget(self.sell_checkbox)
        c.add_widget(line)

        def fill(d):
            loja = d['loja'] or {}
            old = loja.get('whatsapp', '')
            self.store_name.text = loja.get('nome_estabelecimento', '')
            self.store_phone.text = self._display_phone(old)
            self.sell_checkbox.active = bool(loja.get('vendendo'))
            for p in self.points:
                if p['id'] == loja.get('id_ponto'): self.point_spinner.text = p['nome']

        self.request('/minha-loja', done=fill)
        c.add_widget(self.label('Marque Disponível agora e SALVE para aparecer nas buscas.', 13, height=60, color=GRAY))

        def save():
            pid = choices.get(self.point_spinner.text)
            if not pid: self.alert('Escolha um ponto.');return
            phone = self._normalize_phone(self.store_phone.text)
            if not phone: self.alert('Informe 11 dígitos: DDD + celular (ex.: 81999998888).');return
            self.request('/minha-loja', 'POST',
                         {'id_ponto': pid, 'whatsapp': phone, 'vendendo': self.sell_checkbox.active,
                          'nome_estabelecimento': self.store_name.text.strip()},
                         lambda d: self.alert('Loja, ponto e disponibilidade atualizados!'))

        c.add_widget(self.button('Salvar ponto e disponibilidade', save))
        return box

    def open_products(self):
        self.request('/minha-loja', done=lambda d: self.draw_products(d['produtos']))

    def draw_products(self, products):
        self.products = products
        self.show('Produtos', self.products_screen)

    def products_screen(self):
        box, c = self.page('Meu cardápio', self.go_back)
        c.add_widget(self.label('Seu cardápio', 24, True, dp(52)))
        c.add_widget(
            self.label('Organize seus lanches e mantenha as ofertas atualizadas.', 12, height=dp(40), color=GRAY))
        card = self.panel(c, 'Adicionar ou editar produto', 'Informe nome, descrição, preço e foto opcional.')
        self.hint(card, 'Nome do lanche')
        self.prod_name = self.input('Ex.: Bolo de chocolate');
        card.add_widget(self.prod_name)
        self.hint(card, 'Descrição')
        self.prod_desc = self.input('Ex.: Fatia de bolo caseiro');
        card.add_widget(self.prod_desc)
        self.hint(card, 'Preço em reais')
        self.prod_price = self.input('Ex.: 5,50');
        card.add_widget(self.prod_price)
        self.editing_id = None
        self.product_photo = None
        card.add_widget(
            FriendlyButton('Escolher foto do produto', lambda: self.pick_photo('product'), kind='soft', icon='camera',
                           height=42))
        self.photo_notice = self.label('JPG ou PNG • A foto é opcional.', 12, height=dp(30), color=GRAY)
        card.add_widget(self.photo_notice)
        card.add_widget(FriendlyButton('Salvar produto', self.save_product, icon='check', height=42))
        c.add_widget(self.label('Produtos cadastrados', 19, True, dp(44)))
        if not self.products:
            empty = self.panel(c, 'Nenhum produto cadastrado', 'Comece adicionando um lanche no formulário acima.')
        for p in self.products:
            state = 'Disponível na vitrine' if p.get('disponivel') else 'Pausado • fora das ofertas'
            item = self.panel(c, p['nome'] + ' • ' + money(p['preco_centavos']), state)
            if p.get('foto_url'):
                item.add_widget(AsyncImage(source=self.api.base_url + p['foto_url'],
                                           size_hint_y=None, height=dp(140), fit_mode='contain'))
            else:
                hint = BoxLayout(size_hint_y=None, height=dp(58))
                surface(hint, THEME_PALE, 13)
                hint.add_widget(self.label('Produto sem foto', 12, height=58, color=GRAY))
                item.add_widget(hint)
            actions = BoxLayout(size_hint_y=None, height=dp(43), spacing=dp(6))
            actions.add_widget(FriendlyButton('Editar', lambda item=p: self.start_edit(item), height=42, icon='edit'))
            actions.add_widget(FriendlyButton('Pausar' if p['disponivel'] else 'Ativar',
                                              lambda item=p: self.toggle_product(item), kind='dark', height=42,
                                              icon='pause' if p['disponivel'] else 'check'))
            actions.add_widget(FriendlyButton('Excluir', lambda item=p: self.delete_product(item),
                                              kind='danger', height=42, icon='trash'))
            item.add_widget(actions)
        return box

    def start_edit(self, p):
        self.editing_id = p['id'];
        self.product_photo = None;
        self.prod_name.text = p['nome'];
        self.prod_desc.text = p['descricao'];
        self.prod_price.text = str(p['preco_centavos'] / 100)
        if getattr(self, '_page_scroll', None):
            self._page_scroll.scroll_y = 1
        self.alert('Editando ' + p['nome'] + '. Altere os campos e toque em Salvar produto.')

    def save_product(self):
        try:
            price = round(float(self.prod_price.text.replace(',', '.')) * 100)
        except ValueError:
            self.alert('Preço inválido.');return
        data = {'nome': self.prod_name.text.strip(), 'descricao': self.prod_desc.text.strip(), 'preco_centavos': price}
        pid = self.editing_id

        def saved(d):
            product_id = pid or d.get('id')
            if self.product_photo and product_id:
                self.upload_photo('product', product_id, self.product_photo, lambda: self.open_products())
            else:
                self.open_products()

        self.request('/produtos/' + str(pid) if pid else '/produtos', 'PATCH' if pid else 'POST', data, saved)

    def toggle_product(self, p):
        self.request('/produtos/' + str(p['id']), 'PATCH', {'disponivel': not p['disponivel']},
                     lambda d: self.open_products())

    def delete_product(self, p):
        pane = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(9))
        pane.add_widget(Label(text='Retirar "' + p['nome'] + '" do cardápio?', color=WHITE, halign='center'))
        popup = Popup(title='Excluir produto', content=pane, size_hint=(.85, .35))

        def confirm():
            popup.dismiss()
            self.request('/produtos/' + str(p['id']), 'DELETE', done=lambda d: self.open_products(),
                         on_error=lambda e: self.alert(
                             'Não foi possível excluir o produto: ' + e + '\nConfirme se o backend novo foi implantado.'))

        pane.add_widget(self.button('Confirmar exclusão', confirm))
        pane.add_widget(self.button('Cancelar', popup.dismiss, color=BROWN))
        popup.open()

    def open_offers(self):
        self.load_points(lambda: self.request('/ofertas', done=lambda d: self.draw_offers(d['ofertas'])))

    def draw_offers(self, offers):
        self.offers = offers;self.show('Ofertas', self.offers_screen)

    def offers_screen(self):
        box, c = self.page('Vitrine', self.go_back)
        c.add_widget(self.label('O que tem de bom por aqui?', 23, True, dp(46)))
        sellers = {p['vendedor_id']: (p.get('estabelecimento') or p['vendedor'], p['ponto']) for p in self.offers}
        c.add_widget(self.label(f'{len(self.offers)} produto(s) • {len(sellers)} vendedor(es) disponível(is)',
                                12, height=dp(33), color=GRAY))
        filter_card = self.panel(c, 'Encontre seu lanche')
        line = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(7))
        self.offer_search = self.input('Buscar produto')
        self.offer_search.text = getattr(self, 'offer_term', '')
        line.add_widget(self.offer_search)
        search_btn = FriendlyButton('Buscar', self.search_offers, icon='search', height=46)
        search_btn.size_hint_x = None
        search_btn.width = dp(117)
        line.add_widget(search_btn)
        filter_card.add_widget(line)
        filter_line = BoxLayout(size_hint_y=None, height=dp(43), spacing=dp(7))
        self.offer_spinner = Spinner(text='Todos os pontos',
                                     values=['Todos os pontos'] + [p['nome'] for p in self.points],
                                     size_hint_y=None, height=dp(43), background_normal='', background_down='',
                                     background_color=(0, 0, 0, 0), color=BROWN)
        surface(self.offer_spinner, THEME_PALE, 15, THEME_BORDER)
        filter_line.add_widget(self.offer_spinner)
        filter_btn = FriendlyButton('Filtrar', self.filter_offers, kind='dark', height=43, icon='filter')
        filter_btn.size_hint_x = None
        filter_btn.width = dp(110)
        filter_line.add_widget(filter_btn)
        filter_card.add_widget(filter_line)
        term = getattr(self, 'offer_term', '').strip().casefold()
        filtered = [p for p in self.offers if term in p['nome'].casefold()]
        for p in filtered:
            # Foto opcional à direita. Sem foto, toda a largura é dos dados.
            block = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8),
                              padding=[dp(13), dp(11), dp(13), dp(11)])
            block.bind(minimum_height=block.setter('height'))
            surface(block, WHITE, 21)
            detail = BoxLayout(orientation='horizontal', size_hint_y=None,
                               height=dp(95) if p.get('foto_url') else dp(74), spacing=dp(10))
            info = BoxLayout(orientation='vertical', spacing=dp(2))
            info.add_widget(self.label(p['nome'], 16, True, dp(29), BROWN))
            info.add_widget(self.label((p.get('estabelecimento') or p['vendedor']), 12, False, dp(23), GRAY))
            info.add_widget(self.label(p['ponto'], 11, False, dp(22), GRAY))
            detail.add_widget(info)
            if p.get('foto_url'):
                image_url = p['foto_url']
                if image_url.startswith('/'):
                    image_url = self.api.base_url + image_url
                photo = AsyncImage(source=image_url, size_hint=(None, 1),
                                   width=dp(104), fit_mode='contain')
                detail.add_widget(photo)
            block.add_widget(detail)
            bottom = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(43), spacing=dp(8))
            bottom.add_widget(self.label(money(p['preco_centavos']), 18, True, height=43, color=ORANGE))
            add = FriendlyButton('Adicionar', lambda offer=p: self.add_cart(offer), height=43, icon='cart')
            add.size_hint_x = None
            add.width = dp(135)
            bottom.add_widget(add)
            block.add_widget(bottom)
            c.add_widget(block)
        if not filtered:
            empty = self.panel(c, 'Nenhum lanche encontrado', 'Experimente outro termo ou ponto de venda.')
            empty.add_widget(FriendlyButton('Limpar busca', lambda: self._reset_offer_search(), kind='soft'))
        c.add_widget(
            FriendlyButton('Ver carrinho', lambda: self.show('Carrinho', self.cart_screen), kind='dark', icon='cart',
                           height=42))
        return box

    def _reset_offer_search(self):
        self.offer_term = ''
        self.open_offers()

    def search_offers(self):
        self.offer_term = self.offer_search.text.strip()
        self.show('Ofertas', self.offers_screen)

    def filter_offers(self):
        name = self.offer_spinner.text
        id_ = next((p['id'] for p in self.points if p['nome'] == name), None)
        self.request('/ofertas' + ('?ponto=' + str(id_) if id_ else ''), done=lambda d: self.draw_offers(d['ofertas']))

    def add_cart(self, p):
        if self.selected_seller is not None and self.selected_seller != p['vendedor_id']:
            self.alert('Cada pedido pertence a um vendedor. Finalize ou limpe o carrinho atual.');
            return
        self.selected_seller = p['vendedor_id']
        entry = self.cart.setdefault(p['id'], {'item': p, 'quantidade': 0})
        entry['quantidade'] += 1
        self.alert('Adicionado ao carrinho!')

    def cart_screen(self):
        box, c = self.page('Carrinho', self.go_back)
        c.add_widget(self.label('Seu pedido', 24, True, dp(44)))
        c.add_widget(self.label('Confira os produtos e quantidades antes de concluir.', 12, height=dp(39), color=GRAY))
        if not self.cart:
            empty = self.panel(c, 'Seu carrinho está vazio', 'Escolha um lanche na vitrine para começar.')
            empty.add_widget(FriendlyButton('Encontrar lanches', self.open_offers))
            return box
        for pid, entry in list(self.cart.items()):
            p = entry['item'];
            q = entry['quantidade']
            card = self.panel(c, p['nome'], money(p['preco_centavos']) + ' cada')
            row = BoxLayout(size_hint_y=None, height=dp(49), spacing=dp(8))
            row.add_widget(FriendlyButton('−', lambda i=pid: self.adjust_cart(i, -1), kind='soft', height=43))
            row.add_widget(self.label(str(q) + ' un.', 15, True, height=45))
            row.add_widget(FriendlyButton('+', lambda i=pid: self.adjust_cart(i, 1), height=43))
            card.add_widget(row)
            card.add_widget(self.label('Subtotal: ' + money(q * p['preco_centavos']), 14, True, dp(36), ORANGE))
        total = sum(e['quantidade'] * e['item']['preco_centavos'] for e in self.cart.values())
        summary = self.panel(c, 'Resumo do pedido', 'Retirada no ponto de venda do vendedor.')
        summary.add_widget(self.label('Total: ' + money(total), 23, True, dp(48), ORANGE))
        local = next(iter(self.cart.values()))['item'].get('ponto', 'Ponto do vendedor')
        summary.add_widget(self.label('Local: ' + local, 13, height=dp(47), color=GRAY))
        c.add_widget(FriendlyButton('Finalizar pelo WhatsApp', self.checkout,
                                    icon='whatsapp', height=52))
        c.add_widget(
            self.label('Registramos a solicitação e abrimos a conversa. Você precisa enviar a mensagem ao vendedor.',
                       11, color=GRAY, height=dp(53)))
        return box

    def adjust_cart(self, pid, delta):
        self.cart[pid]['quantidade'] += delta
        if self.cart[pid]['quantidade'] <= 0: del self.cart[pid]
        if not self.cart: self.selected_seller = None
        self.show('Carrinho', self.cart_screen)

    def _open_seller_conversation(self, whatsapp, message):
        """Abre a conversa; não afirma que a mensagem foi enviada."""
        phone = re.sub(r'\D', '', str(whatsapp or ''))
        if len(phone) not in (12, 13) or not phone.startswith('55'):
            return False
        url = 'https://wa.me/' + phone + '?text=' + quote(message or '')
        try:
            if platform == 'android':
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                activity.startActivity(intent)
            else:
                if not webbrowser.open(url):
                    return False
            return True
        except Exception:
            return False

    def _retry_seller_contact(self):
        pending = getattr(self, '_pending_seller_contact', None)
        if not pending:
            self.alert('Não há uma conversa pendente nesta sessão.')
            return
        if self._open_seller_conversation(pending['whatsapp'], pending['mensagem']):
            self.alert('Conversa aberta. Envie a mensagem no WhatsApp para o vendedor receber a solicitação.')
        else:
            self.alert('Não foi possível abrir o WhatsApp. Verifique se há um navegador ou WhatsApp instalado.')

    def checkout(self):
        """Registra uma única vez; em seguida abre o contato com o vendedor."""
        if getattr(self, '_checkout_pending', False): return
        if not self.cart:
            self.alert('Adicione produtos primeiro.');
            return
        self._checkout_pending = True
        items = [{'id_produto': pid, 'quantidade': e['quantidade']} for pid, e in self.cart.items()]

        def done(result):
            self._checkout_pending = False
            pedido_id = result['id_pedido']
            self._pending_seller_contact = {
                'id_pedido': pedido_id,
                'whatsapp': result.get('whatsapp', ''),
                'mensagem': result.get('mensagem', ''),
            }
            # Não repetir POST ao tentar reabrir a conversa.
            self.cart = {}
            self.selected_seller = None
            self.show('Inicio', self.home_screen)
            if self._open_seller_conversation(result.get('whatsapp'), result.get('mensagem')):
                # "Encaminhamento tentado" não significa que a mensagem foi enviada.
                self.request('/pedidos/' + str(pedido_id) + '/encaminhado', 'POST', {}, lambda _: None,
                             on_error=lambda _: None)
                self.alert('Solicitação nº ' + str(
                    pedido_id) + ' registrada. Envie a mensagem no WhatsApp para avisar o vendedor. O pedido ainda não está confirmado.')
            else:
                self.alert('Solicitação nº ' + str(
                    pedido_id) + ' registrada, mas não foi possível abrir o WhatsApp. Use "Retomar contato" na tela de Pedidos.')

        def failed(message):
            self._checkout_pending = False
            self.alert(message)

        self.request('/pedidos', 'POST', {'itens': items}, done, on_error=failed)

    def open_profile(self):
        self.request('/perfil', done=lambda d: self.draw_profile(d['usuario']))

    def draw_profile(self, user):
        self.profile_data = user
        self.show('Perfil', self.profile_screen)

    def profile_screen(self):
        box, c = self.page('Meu perfil', lambda: self.show('Inicio', self.home_screen))
        c.add_widget(self.label('Minha conta', 24, True, dp(52)))
        card = self.panel(c, 'Seus dados', 'Atualize suas informações quando quiser.')
        if self.profile_data.get('foto_url'):
            card.add_widget(
                AsyncImage(source=self.api.base_url + self.profile_data['foto_url'], size_hint_y=None, height=dp(110)))
        self.profile_photo = None
        card.add_widget(
            self.button('Escolher foto de perfil', lambda: self.pick_photo('profile'), color=BROWN, height=42))
        self.profile_photo_notice = self.label('Foto opcional', 12, height=dp(25), color=GRAY)
        card.add_widget(self.profile_photo_notice)
        self.hint(card, 'Nome')
        self.profile_name = self.input('Nome completo');
        self.profile_name.text = self.profile_data.get('nome', '');
        card.add_widget(self.profile_name)
        self.hint(card, 'E-mail')
        self.profile_email = self.input('E-mail');
        self.profile_email.text = self.profile_data.get('email', '');
        card.add_widget(self.profile_email)
        self.hint(card, 'Celular • DDD 81')
        self.profile_phone = self.input('DDD + celular: 81999998888')
        self.profile_phone.input_filter = 'int'
        self.profile_phone.text = self._display_phone(self.profile_data.get('telefone', ''))
        card.add_widget(self.profile_phone)
        self.hint(card, 'Senha atual (para alterar os dados)')
        self.profile_password = self.input('Confirme a senha atual', True);
        card.add_widget(self.profile_password)
        card.add_widget(self.button('Salvar alterações', self.save_profile, icon='check'))
        pw_card = self.panel(c, 'Segurança da conta', 'Troque sua senha sem alterar seus outros dados.')
        pw_card.add_widget(
            self.button('Alterar minha senha', lambda: self.show('AlterarSenha', self.change_password_screen),
                        color=BROWN, icon='lock'))
        photo_card = self.panel(c, 'Conta e privacidade', 'Excluir é definitivo e remove os pedidos relacionados.')
        photo_card.add_widget(
            self.button('Excluir minha conta', self.confirm_delete_account, color=(.75, .18, .15, 1), icon='trash'))
        return box

    def change_password_screen(self):
        box, c = self.page('Alterar senha', self.open_profile)
        card = self.panel(c, 'Proteja sua conta', 'Sua sessão será encerrada depois da alteração.')
        self.hint(card, 'Senha atual')
        self.current_password = self.input('Digite sua senha atual', True);
        card.add_widget(self.current_password)
        self.hint(card, 'Nova senha')
        self.new_password = self.input('Mínimo de 8 caracteres', True);
        card.add_widget(self.new_password)
        self.hint(card, 'Confirme a nova senha')
        self.confirm_password = self.input('Repita a nova senha', True);
        card.add_widget(self.confirm_password)
        card.add_widget(self.button('Salvar nova senha', self.save_new_password, icon='lock'))
        return box

    def save_new_password(self):
        old = self.current_password.text
        new = self.new_password.text
        if not old: self.alert('Informe sua senha atual.');return
        if len(new) < 8: self.alert('A nova senha deve ter ao menos 8 caracteres.');return
        if new != self.confirm_password.text: self.alert('As novas senhas não coincidem.');return
        if old == new: self.alert('Escolha uma senha diferente da atual.');return

        def done(_):
            self.logout()
            self.alert('Senha alterada! Entre novamente com a nova senha.')

        self.request('/perfil/senha', 'POST', {'senha_atual': old, 'nova_senha': new}, done)

    def save_profile(self):
        phone = self._normalize_phone(self.profile_phone.text)
        if not phone: self.alert('Celular inválido. Informe 11 dígitos com DDD.');return
        if not self.profile_password.text: self.alert('Digite sua senha atual para confirmar.');return
        data = {'nome': self.profile_name.text.strip(), 'email': self.profile_email.text.strip(), 'telefone': phone,
                'senha_atual': self.profile_password.text}

        def saved(d):
            self.user = d['usuario']
            if self.profile_photo:
                self.upload_photo('profile', None, self.profile_photo, lambda: self.open_profile())
            else:
                self.open_profile()

        self.request('/perfil', 'PATCH', data, saved)

    def confirm_delete_account(self):
        box = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        box.add_widget(self.label('Excluir conta e pedidos relacionados? Não é possível desfazer.', 15, height=dp(110),
                                  color=WHITE))
        pwd = self.input('Digite sua senha para confirmar', True);
        box.add_widget(pwd)
        popup = Popup(title='Confirmar exclusão', content=box, size_hint=(.9, .43))

        def execute():
            if not pwd.text: self.alert('Digite a senha.');return
            popup.dismiss()
            self.request('/perfil', 'DELETE', {'senha_atual': pwd.text}, lambda _: self.logout())

        box.add_widget(self.button('Sim, excluir definitivamente', execute, color=(.75, .18, .15, 1)))
        box.add_widget(self.secondary_button('Cancelar', popup.dismiss))
        popup.open()

    def pick_photo(self, kind):
        """Abre galeria Android ou arquivos locais, inclusive URLs content://."""

        def accepted(paths):
            if not paths: return
            path = str(paths[0])

            def worker():
                try:
                    if path.startswith('content://') and platform == 'android':
                        from jnius import autoclass
                        Activity = autoclass('org.kivy.android.PythonActivity')
                        Uri = autoclass('android.net.Uri')
                        resolver = Activity.mActivity.getContentResolver()
                        stream = resolver.openInputStream(Uri.parse(path))
                        if stream is None: raise ValueError('A foto não pôde ser aberta.')
                        try:
                            content = bytearray()
                            # Em algumas versões do PyJNIus, bytearray funciona como Java byte[].
                            # Fallback por byte, também fora da thread da interface.
                            try:
                                buffer = bytearray(8192)
                                while len(content) <= 1_500_000:
                                    read_count = stream.read(buffer)
                                    if read_count < 0: break
                                    if read_count == 0: continue
                                    content.extend(buffer[:read_count])
                            except (TypeError, AttributeError):
                                stream.close()
                                stream = resolver.openInputStream(Uri.parse(path))
                                content = bytearray()
                                while len(content) <= 1_500_000:
                                    byte = stream.read()
                                    if byte < 0: break
                                    content.append(byte & 255)
                            photo = bytes(content)
                        finally:
                            stream.close()
                    else:
                        with open(path, 'rb') as handle:
                            photo = handle.read(1_500_001)
                    if not (photo.startswith(b'\xff\xd8\xff') or photo.startswith(b'\x89PNG\r\n\x1a\n')):
                        raise ValueError('Escolha uma foto JPG ou PNG.')
                    # Fotos de celular geralmente têm mais de 1,5 MB; compactar antes de enviar.
                    # Pillow é incluído nas dependências do APK e pode ser instalado no PyCharm.
                    if len(photo) > 1_500_000:
                        try:
                            from PIL import Image as PILImage, ImageOps
                            from io import BytesIO
                            original = PILImage.open(BytesIO(photo))
                            original = ImageOps.exif_transpose(original).convert('RGB')
                            original.thumbnail((1080, 1080))
                            stream = BytesIO()
                            original.save(stream, format='JPEG', quality=78, optimize=True)
                            photo = stream.getvalue()
                        except ImportError:
                            raise ValueError('Foto acima de 1,5 MB. Instale Pillow para reduzir automaticamente.')
                        except Exception:
                            raise ValueError('Não foi possível reduzir a foto. Escolha outra imagem JPG/PNG.')
                    if len(photo) > 1_500_000:
                        raise ValueError('Foto acima de 1,5 MB mesmo após compressão.')

                    def apply(_):
                        if kind == 'profile':
                            self.profile_photo = photo
                            self.profile_photo_notice.text = 'Foto selecionada (' + str(len(photo) // 1024) + ' KB)'
                        else:
                            self.product_photo = photo
                            self.photo_notice.text = 'Foto selecionada e pronta para enviar (' + str(
                                len(photo) // 1024) + ' KB)'

                    Clock.schedule_once(apply, 0)
                except Exception as exc:
                    msg = str(exc)
                    Clock.schedule_once(lambda _: self.alert(msg), 0)

            threading.Thread(target=worker, daemon=True).start()

        if platform == 'android':
            try:
                from plyer import filechooser
                filechooser.open_file(on_selection=lambda paths: Clock.schedule_once(lambda _: accepted(paths)))
            except Exception as exc:
                self.alert('Não foi possível abrir a galeria: ' + str(exc))
        else:
            # No Windows, use o seletor nativo, sem mostrar pastas técnicas do Kivy.
            # Não é necessário instalar bibliotecas adicionais: tkinter acompanha o Python.
            if os.name == 'nt':
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    window = tk.Tk()
                    window.withdraw()
                    window.attributes('-topmost', True)
                    try:
                        from pathlib import Path
                        pictures = Path.home() / 'Pictures'
                        start_folder = pictures if pictures.is_dir() else Path.home()
                        path = filedialog.askopenfilename(
                            parent=window,
                            title='Escolha uma foto do VôLanchar',
                            initialdir=str(start_folder),
                            filetypes=[('Imagens JPG e PNG', '*.jpg *.jpeg *.png'),
                                       ('Todos os arquivos', '*.*')],
                        )
                    finally:
                        window.destroy()
                    if path:
                        accepted([path])
                    return
                except Exception as exc:
                    print('Seletor de fotos do Windows indisponível:', exc)

            # Alternativa para Linux/macOS ou caso o diálogo nativo falhe.
            from pathlib import Path
            options = [Path.home() / 'Pictures', Path.home() / 'Imagens',
                       Path.home() / 'Downloads', Path.home()]
            start_folder = next((x for x in options if x.is_dir()), Path.home())
            layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
            chooser = FileChooserListView(filters=['*.jpg', '*.jpeg', '*.png'],
                                          path=str(start_folder))
            layout.add_widget(chooser)
            actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
            popup = Popup(title='Escolher foto JPG ou PNG', content=layout, size_hint=(.94, .86))

            def select():
                selected = list(chooser.selection)
                if not selected:
                    self.alert('Selecione uma foto antes de continuar.')
                    return
                popup.dismiss()
                accepted(selected)

            actions.add_widget(self.button('Usar esta foto', select))
            actions.add_widget(self.button('Cancelar', popup.dismiss, color=BROWN))
            layout.add_widget(actions)
            popup.open()

    def upload_photo(self, kind, product_id, photo, done):
        endpoint = '/perfil/foto' if kind == 'profile' else '/produtos/' + str(product_id) + '/foto'
        self.request(endpoint, 'POST', {'imagem_base64': base64.b64encode(photo).decode('ascii')},
                     lambda _: done(),
                     on_error=lambda error: self.alert(
                         'O produto foi salvo, mas a FOTO NÃO foi enviada. ' + error + '\nVerifique a API e a migração do banco antes de tentar de novo.'))

    def open_orders(self):
        self.request('/pedidos', done=lambda d: self.draw_orders(d['pedidos']))

    def draw_orders(self, orders):
        self.orders = orders;self.show('Pedidos', self.orders_screen)

    def contact_seller_for_order(self, order_id):
        """Busca contato do pedido; exige backend 0.8.4 no Render."""
        pending = getattr(self, '_pending_seller_contact', None)
        if pending and str(pending['id_pedido']) == str(order_id):
            self._retry_seller_contact()
            return

        def got(data):
            self._pending_seller_contact = {'id_pedido': order_id,
                                            'whatsapp': data['whatsapp'], 'mensagem': data['mensagem']}
            self._retry_seller_contact()

        self.request('/pedidos/' + str(order_id) + '/contato', done=got,
                     on_error=lambda err: self.alert('Não foi possível recuperar o contato: ' + str(err) +
                                                     '\nÉ necessário atualizar a API para esta funcionalidade.'))

    def orders_screen(self):
        is_seller = self.mode == 'seller'
        box, c = self.page('Vendas' if is_seller else 'Pedidos', self.go_back)
        c.add_widget(self.label('Vendas recebidas' if is_seller else 'Minhas compras',
                                23, True, dp(44)))
        c.add_widget(self.label('Pedidos do mais antigo para o mais recente.',
                                12, height=dp(38), color=GRAY))

        # A API devolve compras e vendas do usuário: a visualização depende do perfil.
        order_type = 'venda' if is_seller else 'compra'
        visible_orders = [order for order in self.orders if order.get('tipo') == order_type]

        if not is_seller and getattr(self, '_pending_seller_contact', None):
            c.add_widget(FriendlyButton('Retomar contato do último pedido',
                                        self._retry_seller_contact,
                                        icon='whatsapp', height=44))
        if not visible_orders:
            if is_seller:
                self.panel(c, 'Nenhuma venda por enquanto',
                           'Os pedidos recebidos dos compradores aparecerão aqui.')
            else:
                block = self.panel(c, 'Nenhuma compra por enquanto',
                                   'Seus pedidos aparecerão aqui.')
                block.add_widget(FriendlyButton('Explorar lanches', self.open_offers))

        for order in sorted(visible_orders,
                            key=lambda value: int(value.get('numero_exibicao', value['id']))):
            label = 'Venda' if is_seller else 'Compra'
            numero = order.get('numero_exibicao', order['id'])
            block = self.panel(c, f'{label} {numero} • {money(order["valor_centavos"])}',
                               order['outra_pessoa'])
            statuses = {'INICIADO': 'Solicitação registrada',
                        'ENCAMINHAMENTO_TENTADO': 'Contato aberto (envio não confirmado)',
                        'ATENDIDO': 'Vendedor informou atendimento',
                        'CONCLUIDO': 'Pedido concluído pelo comprador'}
            block.add_widget(self.label(
                statuses.get(order['status'], str(order['status']).replace('_', ' ').capitalize()),
                12, height=dp(36), color=GRAY))
            actions = BoxLayout(orientation='horizontal', size_hint_y=None,
                                height=dp(43), spacing=dp(7))
            actions.add_widget(FriendlyButton('Ver pedido',
                                              lambda pid=order['id']: self.open_order_detail(pid),
                                              icon='orders', kind='soft', height=43))
            if not is_seller:
                actions.add_widget(FriendlyButton('WhatsApp',
                                                  lambda pid=order['id']: self.contact_seller_for_order(pid),
                                                  icon='whatsapp', height=43))
            block.add_widget(actions)
        return box

    def open_order_detail(self, pedido_id):
        '''Detalhes sempre obtidos da API; não confiar em dados de cartões locais.'''
        self.request('/pedidos/' + str(pedido_id), done=lambda d: self.draw_order_detail(d['pedido']),
                     on_error=lambda err: self.alert('Não foi possível carregar o pedido: ' + str(err) +
                                                     '\nO servidor precisa estar atualizado para mostrar os detalhes.'))

    def draw_order_detail(self, pedido):
        self._detail_order = pedido
        self.show('Detalhes do pedido', self.order_detail_screen)

    def _change_order_status(self, endpoint, confirm_text):
        p = self._detail_order

        def saved(_):
            self.alert(confirm_text)
            self.open_order_detail(p['id'])

        self.request('/pedidos/' + str(p['id']) + '/' + endpoint, 'POST', {}, saved)

    def _review_order(self):
        '''Nota opcional somente em pedido concluído; nunca simular avaliação salva.'''
        p = self._detail_order
        layout = BoxLayout(orientation='vertical', padding=dp(13), spacing=dp(8))
        layout.add_widget(self.label('Como foi sua compra?', 17, True, 37))
        layout.add_widget(self.label('Nota de 1 a 5 estrelas', 13, height=dp(29), color=GRAY))
        rating = Spinner(text='5 estrelas',
                         values=('1 estrela', '2 estrelas', '3 estrelas', '4 estrelas', '5 estrelas'),
                         size_hint_y=None, height=dp(44), background_color=ORANGE, color=WHITE)
        layout.add_widget(rating)
        layout.add_widget(self.label('Comentário para o vendedor (opcional)', 12, height=dp(30), color=GRAY))
        comment = TextInput(hint_text='Conte como foi sua experiência...', multiline=True,
                            size_hint_y=None, height=dp(102), font_size=dp(14))
        layout.add_widget(comment)
        actions = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        modal = Popup(title='Avaliar pedido', content=layout, size_hint=(.93, .6))

        def send():
            modal.dismiss()
            self.request('/pedidos/' + str(p['id']) + '/avaliacao', 'POST',
                         {'nota': int(rating.text.split()[0]), 'comentario': comment.text.strip()},
                         done=lambda _: self.open_order_detail(p['id']))

        actions.add_widget(FriendlyButton('Enviar avaliação', send, height=45))
        actions.add_widget(FriendlyButton('Cancelar', modal.dismiss, kind='soft', height=45))
        layout.add_widget(actions)
        modal.open()

    def order_detail_screen(self):
        p = self._detail_order
        box, c = self.page('Detalhes do pedido', lambda: self.open_orders())
        c.add_widget(
            self.label(('Compra ' if p['tipo'] == 'compra' else 'Venda ') + str(p.get('numero_exibicao', p['id'])), 23,
                       True, dp(46)))
        card = self.panel(c, 'Resumo do pedido',
                          ('Comprador: ' + p.get('comprador_nome', '') if p['tipo'] == 'venda'
                           else 'Vendedor: ' + p.get('vendedor_nome', '')))
        card.add_widget(self.label('Situação: ' + str(p['status']).replace('_', ' ').capitalize(),
                                   13, height=dp(35), color=GRAY))
        if p.get('ponto'):
            card.add_widget(self.label('Retirada: ' + p['ponto'], 13, height=dp(35), color=GRAY))
        for item in p.get('itens', []):
            name = str(item['nome'])
            qty = int(item['quantidade'])
            sub = int(item['subtotal_centavos'])
            card.add_widget(self.label(f'{qty}x {name} — {money(sub)}', 13, height=dp(39)))
            card.add_widget(self.label('   Unitário: ' + money(int(item['preco_unitario_centavos'])),
                                       11, height=dp(26), color=GRAY))
        card.add_widget(self.label('Total: ' + money(int(p['valor_centavos'])), 19, True, dp(46), ORANGE))
        status = p['status']
        if p['tipo'] == 'venda' and status in ('INICIADO', 'ENCAMINHAMENTO_TENTADO'):
            card.add_widget(FriendlyButton('Marcar pedido como atendido',
                                           lambda: self._change_order_status('atendido',
                                                                             'Pedido marcado como atendido. Aguarde a confirmação do comprador.'),
                                           height=48, icon='orders'))
        if p['tipo'] == 'compra':
            if status == 'ATENDIDO':
                card.add_widget(FriendlyButton('Confirmar que recebi o pedido',
                                               lambda: self._change_order_status('concluir',
                                                                                 'Pedido concluído. Obrigado por confirmar!'),
                                               height=48, icon='orders'))
            if status == 'CONCLUIDO' and not p.get('avaliacao'):
                card.add_widget(FriendlyButton('Avaliar compra', self._review_order, height=46, icon='user'))
            if status not in ('CONCLUIDO',):
                card.add_widget(FriendlyButton('Falar com o vendedor',
                                               lambda: self.contact_seller_for_order(p['id']), icon='whatsapp',
                                               height=46))
        review = p.get('avaliacao')
        if review:
            card.add_widget(self.label('Avaliação: ' + str(review['nota']) + ' de 5 estrelas',
                                       15, True, dp(38), ORANGE))
            if review.get('comentario'):
                card.add_widget(self.label('Comentário: ' + review['comentario'], 12, height=dp(64), color=GRAY))
        return box


if __name__ == '__main__':
    VoLanchar().run()


