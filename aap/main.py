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
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
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

ORANGE=(1,.396,0,1)
YELLOW=(1,.82,.22,1)
BROWN=(.25,.10,.045,1)
CREAM=(1,.976,.929,1)
WHITE=(1,1,1,1)
GREEN=(.10,.52,.31,1)
GRAY=(.43,.39,.36,1)
LIGHT=(1,.92,.80,1)
PALE=(1,.96,.88,1)
MUTED=(.65,.58,.52,1)


def money(c):
    return 'R$ '+f'{c/100:,.2f}'.replace(',','X').replace('.',',').replace('X','.')

class VectorIcon(Widget):
    """Ícones geométricos desenhados pelo Kivy: não dependem de emojis/fontes."""
    def __init__(self, kind='user', tint=WHITE, **kwargs):
        super().__init__(**kwargs)
        self.kind=kind
        self.tint=tint
        self.bind(pos=self.redraw,size=self.redraw)
        self.redraw()

    def redraw(self,*_):
        self.canvas.clear()
        x,y=self.pos; w,h=self.size
        if w<=0 or h<=0:return
        side=min(w,h,dp(23)); a=x+(w-side)/2; b=y+(h-side)/2
        sw=max(dp(1.5),side*.085)
        with self.canvas:
            Color(*self.tint)
            if self.kind=='user':
                Ellipse(pos=(a+side*.35,b+side*.50),size=(side*.30,side*.30))
                Line(ellipse=(a+side*.16,b+side*.04,side*.68,side*.40,0,180),width=sw)
            elif self.kind=='cart':
                Line(points=[a+side*.08,b+side*.78,a+side*.23,b+side*.78,a+side*.36,b+side*.29,a+side*.82,b+side*.29,a+side*.91,b+side*.68,a+side*.28,b+side*.68],width=sw,cap='round',joint='round')
                Ellipse(pos=(a+side*.34,b+side*.11),size=(side*.12,side*.12))
                Ellipse(pos=(a+side*.73,b+side*.11),size=(side*.12,side*.12))
            elif self.kind=='pin':
                Line(ellipse=(a+side*.19,b+side*.31,side*.62,side*.62,0,360),width=sw)
                Line(points=[a+side*.21,b+side*.50,a+side*.50,b+side*.06,a+side*.79,b+side*.50],width=sw,cap='round',joint='round')
                Ellipse(pos=(a+side*.41,b+side*.61),size=(side*.18,side*.18))
            elif self.kind=='camera':
                Line(rounded_rectangle=(a+side*.12,b+side*.20,side*.76,side*.54,side*.07),width=sw)
                Line(rectangle=(a+side*.28,b+side*.74,side*.24,side*.09),width=sw)
                Line(circle=(a+side*.50,b+side*.47,side*.16),width=sw)
            elif self.kind=='menu':
                for yy in (.26,.5,.74):Line(points=[a+side*.15,b+side*yy,a+side*.85,b+side*yy],width=sw,cap='round')
            elif self.kind=='bag':
                Line(rounded_rectangle=(a+side*.16,b+side*.13,side*.68,side*.63,side*.08),width=sw)
                Line(points=[a+side*.31,b+side*.66,a+side*.31,b+side*.84,a+side*.69,b+side*.84,a+side*.69,b+side*.66],width=sw)
            elif self.kind=='lock':
                Line(rounded_rectangle=(a+side*.22,b+side*.12,side*.56,side*.49,side*.07),width=sw)
                Line(ellipse=(a+side*.31,b+side*.45,side*.38,side*.43,0,180),width=sw)
            else:
                Line(rounded_rectangle=(a+side*.14,b+side*.18,side*.72,side*.62,side*.09),width=sw)
                Line(points=[a+side*.30,b+side*.48,a+side*.46,b+side*.32,a+side*.72,b+side*.63],width=sw)

class VoLanchar(App):
    title='VôLanchar'
    def build(self):
        Window.clearcolor=CREAM
        # Tamanho de referência para teste no computador: Android, 393 × 852.
        if platform in ('win','linux','macosx'):
            Window.size=(393,852)
            Window.minimum_width=345
            Window.minimum_height=650
        # Endereço interno. Para APK físico, configure VOLANCHAR_API_URL no arquivo app/config.py.
        # Android nunca usa 127.0.0.1 para acessar o Flask no computador.
        from config import VOLANCHAR_API_URL
        self.api=API(os.getenv('VOLANCHAR_API', VOLANCHAR_API_URL))
        self.google_id_token=None
        self._google_waiting=False
        self.user=None
        self.mode='buyer'
        self.points=[]
        self.offers=[]
        self.cart={}
        self.selected_seller=None
        self.product_ids=[]
        self.registration_visible=False
        self._store_data=None
        self.profile_photo=None
        self.product_photo=None
        self.root_manager=ScreenManager()
        self.show('Acesso',self.access_screen)
        return self.root_manager

    def request(self,path,method='GET',data=None,done=None,on_error=None):
        def worker():
            try:
                result=self.api.call(path,method,data)
                if done:Clock.schedule_once(lambda dt:done(result),0)
            except APIError as e:
                msg=str(e)
                Clock.schedule_once(lambda dt:on_error(msg) if on_error else self.alert(msg),0)
            except Exception as e:
                Clock.schedule_once(lambda dt:self.alert('Erro inesperado: '+str(e)),0)
        threading.Thread(target=worker,daemon=True).start()

    def alert(self,msg):
        pane=BoxLayout(orientation='vertical',padding=dp(18),spacing=dp(14))
        label=Label(text=msg,color=WHITE,halign='center',valign='middle')
        label.bind(size=lambda x,y:setattr(x,'text_size',(x.width,None)))
        pane.add_widget(label)
        btn=self.button('OK');pane.add_widget(btn)
        popup=Popup(title='VôLanchar',content=pane,size_hint=(.86,.35))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def label(self,text,size=17,bold=False,height=45,color=BROWN):
        l=Label(text=text,font_size=dp(size),bold=bold,color=color,size_hint_y=None,height=dp(height),halign='left',valign='middle')
        l.bind(size=lambda instance,_:setattr(instance,'text_size',(instance.width,None)))
        return l

    def button(self,text,action=None,color=ORANGE,height=48,icon=None):
        # Normaliza pictogramas para evitar quadrados vazios no Android/Windows.
        icon_map={'🛒':'cart','📍':'pin','📷':'camera','🍔':'bag','🍟':'menu','👤':'user','📋':'menu'}
        for emoji,kind in icon_map.items():
            if emoji in text:
                text=text.replace(emoji,'').strip()
                icon=icon or kind
        b=Button(text=text,background_normal='',background_down='',background_color=(0,0,0,0),
                 color=WHITE,bold=True,font_size=dp(14),size_hint_y=None,height=dp(height))
        with b.canvas.before:
            Color(*color)
            rect=RoundedRectangle(pos=b.pos,size=b.size,radius=[dp(18)])
        b.bind(pos=lambda w,_:setattr(rect,'pos',w.pos),size=lambda w,_:setattr(rect,'size',w.size))
        if icon:
            glyph=VectorIcon(kind=icon,tint=WHITE,size_hint=(None,None),size=(dp(24),dp(24)))
            b.add_widget(glyph)
            def place_icon(*_):
                glyph.pos=(b.x+dp(15),b.center_y-glyph.height/2)
            b.bind(pos=place_icon,size=place_icon)
            b.text='     '+text
            place_icon()
        if action:b.bind(on_release=lambda _:action())
        return b

    def input(self,hint,password=False):
        return TextInput(hint_text=hint,multiline=False,password=password,font_size=dp(15),
                         size_hint_y=None,height=dp(45),padding=[dp(12),dp(10)],
                         background_normal='',background_active='',background_color=WHITE,
                         foreground_color=BROWN,cursor_color=ORANGE)

    def panel(self,parent,title,subtitle=''):
        pane=BoxLayout(orientation='vertical',spacing=dp(6),padding=dp(13),size_hint_y=None)
        pane.bind(minimum_height=pane.setter('height'))
        with pane.canvas.before:
            Color(1,1,1,1)
            rect=RoundedRectangle(pos=pane.pos,size=pane.size,radius=[dp(18)])
        pane.bind(pos=lambda w,_:setattr(rect,'pos',w.pos),size=lambda w,_:setattr(rect,'size',w.size))
        pane.add_widget(self.label(title,18,True,38))
        if subtitle:pane.add_widget(self.label(subtitle,13,False,42,GRAY))
        parent.add_widget(pane)
        return pane

    def page(self,title,back=None):
        wrapper=BoxLayout(orientation='vertical',spacing=dp(8))
        head=BoxLayout(size_hint_y=None,height=dp(55),spacing=dp(8),padding=[dp(10),0])
        if back:
            back_btn=self.button('‹',back,color=BROWN,height=46)
            back_btn.size_hint_x=None;back_btn.width=dp(49)
            head.add_widget(back_btn)
        head.add_widget(self.label('VôLanchar',21,True,54,ORANGE))
        wrapper.add_widget(head)
        scroll=ScrollView()
        content=BoxLayout(orientation='vertical',padding=dp(18),spacing=dp(12),size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        scroll.add_widget(content)
        wrapper.add_widget(scroll)
        banner=BoxLayout(size_hint_y=None,height=dp(4))
        with banner.canvas.before:
            Color(*ORANGE)
            highlight=RoundedRectangle(pos=banner.pos,size=banner.size,radius=[dp(2)])
        banner.bind(pos=lambda w,_:setattr(highlight,'pos',w.pos),size=lambda w,_:setattr(highlight,'size',w.size))
        wrapper.add_widget(banner)
        return wrapper,content

    def show(self,name,constructor):
        if self.root_manager.has_screen(name):self.root_manager.remove_widget(self.root_manager.get_screen(name))
        screen=Screen(name=name)
        screen.add_widget(constructor())
        self.root_manager.add_widget(screen)
        self.root_manager.current=name

    def _auth_shell(self, title, subtitle, register=False):
        # Formulários compactos: cartão com altura do conteúdo, nunca elástico.
        # O espaço restante é mantido ABAIXO do formulário, não dentro dele.
        outer=BoxLayout(orientation='vertical',padding=[dp(22),dp(10),dp(22),dp(14)],spacing=0)
        content=BoxLayout(orientation='vertical',spacing=dp(7),size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        outer.add_widget(content)
        logo_path=os.path.join(os.path.dirname(__file__),'assets','logo_original.jpg')
        if os.path.isfile(logo_path):
            image=Image(source=logo_path,size_hint_y=None,
                        height=dp(83 if not register else 62),fit_mode='contain')
            content.add_widget(image)
        content.add_widget(self.label('VôLanchar',25,True,dp(35),ORANGE))
        content.add_widget(self.label('O lanche pertim. O bucho chein.',12,True,dp(23),BROWN))
        card=BoxLayout(orientation='vertical',spacing=dp(3),
                       padding=[dp(13),dp(10)],size_hint_y=None)
        card.bind(minimum_height=card.setter('height'))
        with card.canvas.before:
            Color(*WHITE)
            rect=RoundedRectangle(pos=card.pos,size=card.size,radius=[dp(20)])
        card.bind(pos=lambda w,_:setattr(rect,'pos',w.pos),
                  size=lambda w,_:setattr(rect,'size',w.size))
        card.add_widget(self.label(title,18,True,dp(30)))
        card.add_widget(self.label(subtitle,11,False,dp(35),GRAY))
        content.add_widget(card)
        # Sem ScrollView e sem espaçador acima do login.
        from kivy.uix.widget import Widget
        outer.add_widget(Widget())
        return outer,card,content

    def hint(self, parent, text):
        parent.add_widget(self.label(text,12,True,dp(21),BROWN))

    def secondary_button(self,text,action):
        return self.button(text,action,color=BROWN,height=43)

    def access_screen(self):
        # Tela exclusiva para LOGIN; nenhum campo do cadastro é reaproveitado.
        outer,card,content=self._auth_shell('Que bom te ver de novo!', 'Entre para encontrar ou vender lanches na UFRPE.')
        self.hint(card,'E-mail ou telefone')
        self.login_identifier=self.input('seuemail@exemplo.com ou (81) 99999-9999')
        card.add_widget(self.login_identifier)
        self.hint(card,'Senha')
        self.login_password=self.input('Digite sua senha',True)
        card.add_widget(self.login_password)
        card.add_widget(self.button('Entrar no VôLanchar',self.sign_in))
        card.add_widget(self.button('Continuar com Google',self.google_sign_in,color=BROWN,height=46))
        card.add_widget(self.button('Esqueci minha senha',lambda:self.show('Recuperar',self.forgot_screen),color=BROWN,height=37,icon='lock'))
        content.add_widget(self.label('Ainda não tem uma conta?',13,True,dp(25)))
        content.add_widget(self.secondary_button('Criar minha conta',lambda:self.show('Cadastro',self.register_screen)))
        content.add_widget(self.label('Feito para a UFRPE • Recife',11,height=dp(23),color=GRAY))
        return outer

    def forgot_screen(self):
        outer,card,content=self._auth_shell('Esqueceu sua senha?', 'Vamos enviar um código para seu e-mail cadastrado.')
        self.hint(card,'E-mail cadastrado')
        self.reset_email=self.input('seuemail@exemplo.com')
        card.add_widget(self.reset_email)
        card.add_widget(self.button('Enviar código',self.send_reset_code,icon='lock'))
        card.add_widget(self.label('O código expira em 15 minutos. Verifique também o spam.',11,height=36,color=GRAY))
        content.add_widget(self.secondary_button('Voltar para entrar',lambda:self.show('Acesso',self.access_screen)))
        return outer

    def send_reset_code(self):
        email=self.reset_email.text.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
            self.alert('Informe o e-mail cadastrado.');return
        self.request('/senha/solicitar','POST',{'email':email},
                     lambda _:self.show('NovaSenha',self.reset_password_screen))

    def reset_password_screen(self):
        outer,card,content=self._auth_shell('Recuperar acesso', 'Digite o código enviado ao seu e-mail.')
        self.hint(card,'Código de 8 dígitos')
        self.reset_code=self.input('Código recebido');card.add_widget(self.reset_code)
        self.hint(card,'Nova senha')
        self.reset_new=self.input('Mínimo de 8 caracteres',True);card.add_widget(self.reset_new)
        self.hint(card,'Repita a nova senha')
        self.reset_confirm=self.input('Confirme a nova senha',True);card.add_widget(self.reset_confirm)
        card.add_widget(self.button('Redefinir senha',self.confirm_reset,icon='lock'))
        content.add_widget(self.secondary_button('Voltar para entrar',lambda:self.show('Acesso',self.access_screen)))
        return outer

    def confirm_reset(self):
        pwd=self.reset_new.text
        if not re.fullmatch(r'[0-9]{8}',self.reset_code.text.strip()):
            self.alert('Informe o código de 8 dígitos.');return
        if len(pwd)<8:self.alert('A nova senha deve ter no mínimo 8 caracteres.');return
        if pwd!=self.reset_confirm.text:self.alert('As senhas não coincidem.');return
        email=self.reset_email.text.strip().lower()
        data={'email':email,'codigo':self.reset_code.text.strip(),'nova_senha':pwd}
        def done(_):
            self.show('Acesso',self.access_screen)
            self.alert('Senha redefinida! Entre com sua nova senha.')
        self.request('/senha/redefinir','POST',data,done)

    def register_screen(self):
        outer,card,content=self._auth_shell('Bora criar sua conta?', 'Uma conta para comprar e vender.',register=True)
        self.hint(card,'Nome completo')
        self.name_input=self.input('Como podemos chamar você?');card.add_widget(self.name_input)
        self.hint(card,'E-mail')
        self.email_input=self.input('voce@exemplo.com');card.add_widget(self.email_input)
        self.hint(card,'WhatsApp • DDD 81')
        self.phone_input=self.input('(81) 99999-9999');card.add_widget(self.phone_input)
        self.phone_input.bind(text=self._phone_mask)
        self.hint(card,'Senha')
        self.pw_input=self.input('Mínimo de 8 caracteres',True);card.add_widget(self.pw_input)
        card.add_widget(self.button('Criar conta',self.sign_up))
        content.add_widget(self.label('Já tem uma conta?',13,True,dp(23)))
        content.add_widget(self.secondary_button('Voltar para entrar',lambda:self.show('Acesso',self.access_screen)))
        return outer

    def _phone_mask(self,widget,value):
        # Aceita 81 + nove dígitos locais; o prefixo (81) é exibido automaticamente.
        digits=re.sub(r'\D','',value)
        if digits.startswith('55') and len(digits)>11:digits=digits[2:]
        if digits.startswith('81'):digits=digits[2:]
        local=digits[:9]
        mask='(81) '
        if local:mask+=local[:5]
        if len(local)>5:mask+='-'+local[5:]
        if widget.text!=mask:
            widget.text=mask
            widget.cursor=(len(mask),0)

    def _normalize_phone(self,value):
        digits=re.sub(r'\D','',value)
        if digits.startswith('55') and len(digits)==13:digits=digits[2:]
        if not re.fullmatch(r'81[0-9]{9}',digits) or digits[2]!='9':
            return None
        return '55'+digits  # A API e o WhatsApp continuam usando DDI internamente.

    # Login Google via Google Play Services (fluxo legado para o protótipo Kivy).
    # Em produção, migrar para Android Credential Manager.
    def google_sign_in(self):
        if platform != 'android':
            self.alert('O login com Google é testado no aplicativo Android.');return
        if self._google_waiting:return
        try:
            from google_config import GOOGLE_WEB_CLIENT_ID
            if not GOOGLE_WEB_CLIENT_ID.endswith('.apps.googleusercontent.com'):
                self.alert('Configure GOOGLE_WEB_CLIENT_ID em google_config.py antes de compilar.');return
            from jnius import autoclass
            from android import activity
            PythonActivity=autoclass('org.kivy.android.PythonActivity')
            SignInOptions=autoclass('com.google.android.gms.auth.api.signin.GoogleSignInOptions')
            Builder=autoclass('com.google.android.gms.auth.api.signin.GoogleSignInOptions$Builder')
            SignIn=autoclass('com.google.android.gms.auth.api.signin.GoogleSignIn')
            options=Builder(SignInOptions.DEFAULT_SIGN_IN).requestEmail().requestIdToken(GOOGLE_WEB_CLIENT_ID).build()
            self._google_client=SignIn.getClient(PythonActivity.mActivity,options)
            activity.bind(on_activity_result=self._google_activity_result)
            self._google_waiting=True
            PythonActivity.mActivity.startActivityForResult(self._google_client.getSignInIntent(),7607)
        except Exception as exc:
            self._google_waiting=False
            self.alert('Não foi possível abrir o Google: '+str(exc))

    def _google_activity_result(self,request_code,result_code,intent):
        if request_code != 7607:return
        self._google_waiting=False
        try:
            from android import activity
            activity.unbind(on_activity_result=self._google_activity_result)
            if intent is None:
                self.alert('Login Google cancelado.');return
            from jnius import autoclass, cast
            SignIn=autoclass('com.google.android.gms.auth.api.signin.GoogleSignIn')
            task=SignIn.getSignedInAccountFromIntent(intent)
            account=cast('com.google.android.gms.auth.api.signin.GoogleSignInAccount',task.getResult())
            token=account.getIdToken() if account else None
            if not token:
                self.alert('O Google não forneceu um token de identificação.');return
            self.google_id_token=str(token)
            self.request('/google/entrar','POST',{'id_token':self.google_id_token},self._google_result)
        except Exception as exc:
            self.alert('Não foi possível concluir o acesso Google: '+str(exc))

    def _google_result(self,data):
        etapa=data.get('etapa')
        if etapa in ('cadastro','vincular'):
            self.google_stage=etapa
            self.google_name=data.get('nome','')
            self.google_email=data.get('email','')
            self.show('GoogleCompletar',self.google_complete_screen)
        else:
            self.google_id_token=None
            self._logged_in(data)

    def google_complete_screen(self):
        is_link=getattr(self,'google_stage','cadastro')=='vincular'
        title='Vincular conta existente' if is_link else 'Concluir cadastro Google'
        subtitle=('Sua conta já existe. Informe a senha para vincular o Google.' if is_link
                  else 'Informe seu WhatsApp e crie uma senha para o perfil e a segurança da conta.')
        outer,card,content=self._auth_shell(title,subtitle,register=True)
        card.add_widget(self.label(self.google_email,12,height=dp(28),color=GRAY))
        if is_link:
            self.google_password=self.input('Senha atual do VôLanchar',True)
            card.add_widget(self.google_password)
        else:
            self.hint(card,'Nome completo')
            self.google_user_name=self.input('Seu nome')
            self.google_user_name.text=self.google_name
            card.add_widget(self.google_user_name)
            self.hint(card,'WhatsApp • DDD 81')
            self.google_phone=self.input('(81) 99999-9999')
            self.google_phone.bind(text=self._phone_mask)
            card.add_widget(self.google_phone)
            self.hint(card,'Crie uma senha para o VôLanchar')
            self.google_password=self.input('Mínimo de 8 caracteres',True)
            card.add_widget(self.google_password)
        card.add_widget(self.button('Vincular e entrar' if is_link else 'Concluir e entrar',self.google_complete))
        content.add_widget(self.secondary_button('Voltar ao login',lambda:self.show('Acesso',self.access_screen)))
        return outer

    def google_complete(self):
        if not self.google_id_token:
            self.alert('Repita o login com Google.');return
        payload={'id_token':self.google_id_token,'senha':self.google_password.text}
        if getattr(self,'google_stage','cadastro')=='cadastro':
            phone=self._normalize_phone(self.google_phone.text)
            if not phone:self.alert('Informe WhatsApp válido no formato (81) 99999-9999.');return
            if len(self.google_user_name.text.strip())<2:self.alert('Informe seu nome.');return
            payload.update({'nome':self.google_user_name.text.strip(),'telefone':phone})
        if len(payload['senha'])<8:
            self.alert('Informe uma senha de pelo menos 8 caracteres.');return
        self.request('/google/entrar','POST',payload,self._google_result)

    def _logged_in(self,result):
        self.api.token=result['token'];self.user=result['usuario'];self.mode='buyer'
        self.registration_visible=False
        self.show('Inicio',self.home_screen)

    def sign_in(self):
        identifier=self.login_identifier.text.strip()
        password=self.login_password.text
        if not identifier or not password:
            self.alert('Preencha o e-mail ou telefone e a senha.');return
        self._authenticate('/entrar',{'identificador':identifier,'senha':password})

    def sign_up(self):
        nome=self.name_input.text.strip();email=self.email_input.text.strip()
        phone=self._normalize_phone(self.phone_input.text)
        password=self.pw_input.text
        if len(nome)<2:self.alert('Informe seu nome completo.');return
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):self.alert('Informe um e-mail válido.');return
        if not phone:self.alert('Informe um celular de Recife no formato (81) 99999-9999.');return
        if len(password)<8:self.alert('A senha deve ter pelo menos 8 caracteres.');return
        self._authenticate('/registrar',{'nome':nome,'email':email,'telefone':phone,'senha':password})

    def _authenticate(self,endpoint,data):
        self.request(endpoint,'POST',data,self._logged_in)

    def home_screen(self):
        box,c=self.page('Início')
        c.add_widget(self.label('Oi, '+(self.user or {}).get('nome','').split(' ')[0]+'!',25,True,57))
        c.add_widget(self.label('Bateu aquela fome? O VôLanchar resolve!',14,height=38,color=GRAY))
        active='Comprando' if self.mode=='buyer' else 'Vendendo'
        pane=self.panel(c,'Seu espaço • '+active, 'Alterne entre comprar e vender sem sair da conta.')
        pane.add_widget(self.button('Mudar para '+('vendedor' if self.mode=='buyer' else 'comprador'),self.switch_mode,color=BROWN,height=46))
        if self.mode=='buyer':
            hero=self.panel(c,'Tem lanche pertim!','Encontre os vendedores disponíveis agora no campus.')
            hero.add_widget(self.button('Explorar lanches',self.open_offers))
            c.add_widget(self.button('🛒  Meu carrinho',lambda:self.show('Carrinho',self.cart_screen),color=BROWN))
        else:
            state=self.panel(c,'Vendendo agora','Ative a chavinha para aparecer nas buscas de compradores.')
            line=BoxLayout(orientation='horizontal',size_hint_y=None,height=dp(54),spacing=dp(6))
            self.home_status=self.label('Carregando status...',14,height=52,color=GRAY)
            line.add_widget(self.home_status)
            self.home_switch=Switch(active=False,size_hint=(None,None),size=(dp(74),dp(50)))
            self.home_switch.disabled=True
            line.add_widget(self.home_switch)
            state.add_widget(line)
            self.request('/minha-loja',done=self._load_home_store)
            state.add_widget(self.label('Configure seu ponto e WhatsApp antes de ativar.',12,height=47,color=GRAY))
            c.add_widget(self.button('📍  Meu ponto de venda',self.open_store))
            c.add_widget(self.button('🍟  Gerenciar cardápio',self.open_products,color=BROWN))
        c.add_widget(self.button('👤  Meu perfil',self.open_profile,color=BROWN))
        c.add_widget(self.button('Minhas solicitações',self.open_orders,color=BROWN))
        c.add_widget(self.button('Sair da conta',self.logout,color=GRAY,height=45))
        return box

    def _load_home_store(self,data):
        loja=data.get('loja') or {}
        self._store_data=loja
        self.home_switch.active=bool(loja.get('vendendo'))
        self.home_switch.disabled=False
        self.home_status.text='Disponível agora' if loja.get('vendendo') else 'Pausado • fora das buscas'
        self.home_switch.bind(active=self._change_home_status)

    def _change_home_status(self,widget,active):
        loja=self._store_data or {}
        if not loja.get('id_ponto') or not loja.get('whatsapp'):
            widget.unbind(active=self._change_home_status)
            widget.active=False
            widget.bind(active=self._change_home_status)
            self.alert('Configure primeiro o ponto de venda e o WhatsApp em Meu ponto de venda.');return
        widget.disabled=True
        payload={'id_ponto':loja['id_ponto'],'whatsapp':loja['whatsapp'],'vendendo':bool(active)}
        def done(_):
            widget.disabled=False
            self._store_data['vendendo']=int(active)
            self.home_status.text='Disponível agora' if active else 'Pausado • fora das buscas'
        def failed(msg):
            widget.unbind(active=self._change_home_status)
            widget.active=not active
            widget.bind(active=self._change_home_status)
            widget.disabled=False
            self.alert(msg)
        self.request('/minha-loja','POST',payload,done,on_error=failed)

    def switch_mode(self):
        self.mode='seller' if self.mode=='buyer' else 'buyer'
        self.cart={};self.selected_seller=None
        self.show('Inicio',self.home_screen)

    def logout(self):
        self.api.token='';self.user=None;self.cart={};self.mode='buyer'
        self.google_id_token=None
        self.registration_visible=False
        self.show('Acesso',self.access_screen)

    def load_points(self,cb):
        def done(d):self.points=d['pontos'];cb()
        self.request('/pontos',done=done)

    def open_store(self):self.load_points(lambda:self.show('Loja',self.store_screen))

    def store_screen(self):
        box,c=self.page('Ponto de venda',lambda:self.show('Inicio',self.home_screen))
        block=self.panel(c,'Onde tu vai vender hoje?', 'Escolha o ponto da UFRPE e avise quando tiver lanche disponível.')
        c=block
        choices={p['nome']:p['id'] for p in self.points}
        self.point_spinner=Spinner(text='Escolha um ponto',values=list(choices),size_hint_y=None,height=dp(52))
        c.add_widget(self.point_spinner)
        self.hint(c,'WhatsApp para receber os pedidos')
        self.store_phone=self.input('(81) 99999-9999');c.add_widget(self.store_phone)
        self.store_phone.bind(text=self._phone_mask)
        line=BoxLayout(size_hint_y=None,height=dp(52))
        line.add_widget(self.label('Disponível agora • Vendendo',16));self.sell_checkbox=CheckBox(active=False,color=ORANGE);line.add_widget(self.sell_checkbox)
        c.add_widget(line)
        def fill(d):
            loja=d['loja'] or {}
            old=loja.get('whatsapp','')
            self.store_phone.text=old if old else '(81) '
            self.sell_checkbox.active=bool(loja.get('vendendo'))
            for p in self.points:
                if p['id']==loja.get('id_ponto'):self.point_spinner.text=p['nome']
        self.request('/minha-loja',done=fill)
        c.add_widget(self.label('Marque Disponível agora e SALVE para aparecer nas buscas.',13,height=60,color=GRAY))
        def save():
            pid=choices.get(self.point_spinner.text)
            if not pid:self.alert('Escolha um ponto.');return
            phone=self._normalize_phone(self.store_phone.text)
            if not phone:self.alert('Informe um WhatsApp válido: (81) 99999-9999.');return
            self.request('/minha-loja','POST',{'id_ponto':pid,'whatsapp':phone,'vendendo':self.sell_checkbox.active},lambda d:self.alert('Ponto e disponibilidade atualizados!'))
        c.add_widget(self.button('Salvar ponto e disponibilidade',save))
        return box

    def open_products(self):self.request('/minha-loja',done=lambda d:self.draw_products(d['produtos']))

    def draw_products(self,products):
        self.products=products
        self.show('Produtos',self.products_screen)

    def products_screen(self):
        box,c=self.page('Meu cardápio',lambda:self.show('Inicio',self.home_screen))
        c.add_widget(self.label('Meu cardápio',24,True,58))
        card=self.panel(c,'Adicionar ou editar lanche', 'Descreva o lanche e informe o preço para a comunidade.')
        c_form=c
        c=card
        self.prod_name=self.input('Nome do produto');c.add_widget(self.prod_name)
        self.prod_desc=self.input('Descrição');c.add_widget(self.prod_desc)
        self.prod_price=self.input('Preço em reais (ex.: 5,50)');c.add_widget(self.prod_price)
        self.editing_id=None
        self.product_photo=None
        c.add_widget(self.button('📷  Escolher foto (opcional)',lambda:self.pick_photo('product'),color=BROWN,height=42))
        self.photo_notice=self.label('Sem foto selecionada',12,height=dp(26),color=GRAY)
        c.add_widget(self.photo_notice)
        c.add_widget(self.button('Salvar produto',self.save_product))
        c=c_form
        c.add_widget(self.label('Seus produtos',20,True,54))
        for p in self.products:
            product_card=self.panel(c,''+p['nome']+' • '+money(p['preco_centavos']), 'Ativo no cardápio' if p['disponivel'] else 'Pausado')
            c_product=c
            c=product_card
            if p.get('foto_url'):
                c.add_widget(AsyncImage(source=self.api.base_url+p['foto_url'],size_hint_y=None,height=dp(115)))
            row=BoxLayout(size_hint_y=None,height=dp(46),spacing=dp(5))
            row.add_widget(self.button('Editar',lambda p=p:self.start_edit(p),height=44))
            row.add_widget(self.button('Pausar' if p['disponivel'] else 'Ativar',lambda p=p:self.toggle_product(p),color=BROWN,height=44))
            row.add_widget(self.button('Excluir',lambda p=p:self.delete_product(p),color=GRAY,height=44))
            c.add_widget(row)
            c=c_product
        return box

    def start_edit(self,p):
        self.editing_id=p['id'];self.product_photo=None;self.prod_name.text=p['nome'];self.prod_desc.text=p['descricao'];self.prod_price.text=str(p['preco_centavos']/100)
        self.alert('Editando '+p['nome']+'. Altere os campos e toque em Salvar produto.')

    def save_product(self):
        try:price=round(float(self.prod_price.text.replace(',','.'))*100)
        except ValueError:self.alert('Preço inválido.');return
        data={'nome':self.prod_name.text.strip(),'descricao':self.prod_desc.text.strip(),'preco_centavos':price}
        pid=self.editing_id
        def saved(d):
            product_id=pid or d.get('id')
            if self.product_photo and product_id:
                self.upload_photo('product',product_id,self.product_photo,lambda:self.open_products())
            else:self.open_products()
        self.request('/produtos/'+str(pid) if pid else '/produtos','PATCH' if pid else 'POST',data,saved)

    def toggle_product(self,p):self.request('/produtos/'+str(p['id']),'PATCH',{'disponivel':not p['disponivel']},lambda d:self.open_products())
    def delete_product(self,p):self.request('/produtos/'+str(p['id']),'DELETE',done=lambda d:self.open_products())

    def open_offers(self):self.load_points(lambda:self.request('/ofertas',done=lambda d:self.draw_offers(d['ofertas'])))
    def draw_offers(self,offers):self.offers=offers;self.show('Ofertas',self.offers_screen)

    def offers_screen(self):
        box,c=self.page('Lanches por bloco',lambda:self.show('Inicio',self.home_screen))
        c.add_widget(self.label('Tem lanche pertim!',22,True,64))
        c.add_widget(self.label('●  Disponíveis agora',17,True,46,color=GREEN))
        sellers={}
        for offer in self.offers:
            sellers[offer['vendedor_id']]=(offer['vendedor'],offer['ponto'])
        if not sellers:
            c.add_widget(self.label('Nenhum vendedor disponível agora com produtos ativos.',14,height=70,color=GRAY))
        for name,point in sellers.values():
            self.panel(c,''+name,'Disponível agora  •  '+point)
        c.add_widget(self.label('Produtos disponíveis',17,True,48))
        self.offer_spinner=Spinner(text='Todos os pontos',values=['Todos os pontos']+[p['nome'] for p in self.points],size_hint_y=None,height=dp(52))
        c.add_widget(self.offer_spinner)
        c.add_widget(self.button('Filtrar',self.filter_offers,color=BROWN))
        for p in self.offers:
            item=self.panel(c,p['nome']+'  •  '+money(p['preco_centavos']),'Disponível agora  •  '+p['vendedor']+'  •  '+p['ponto'])
            if p.get('foto_url'):
                item.add_widget(AsyncImage(source=self.api.base_url+p['foto_url'],size_hint_y=None,height=dp(140)))
            item.add_widget(self.button('Adicionar ao carrinho',lambda p=p:self.add_cart(p),height=42))
        if not self.offers:c.add_widget(self.label('Ative Disponível agora no modo vendedor, salve o ponto e confira se o produto está ativo.',13,height=85,color=GRAY))
        c.add_widget(self.button('Ver carrinho',lambda:self.show('Carrinho',self.cart_screen),color=BROWN))
        return box

    def filter_offers(self):
        name=self.offer_spinner.text
        id_=next((p['id'] for p in self.points if p['nome']==name),None)
        self.request('/ofertas'+('?ponto='+str(id_) if id_ else ''),done=lambda d:self.draw_offers(d['ofertas']))

    def add_cart(self,p):
        if self.selected_seller is not None and self.selected_seller!=p['vendedor_id']:
            self.alert('Cada pedido pertence a um vendedor. Finalize ou limpe o carrinho atual.');return
        self.selected_seller=p['vendedor_id']
        entry=self.cart.setdefault(p['id'],{'item':p,'quantidade':0})
        entry['quantidade']+=1
        self.alert('Adicionado ao carrinho!')

    def cart_screen(self):
        box,c=self.page('Meu carrinho',lambda:self.show('Inicio',self.home_screen))
        c.add_widget(self.label('Seu pedido',24,True,64))
        if not self.cart:
            empty=self.panel(c,'Seu carrinho está vazio', 'Que tal encontrar um lanche pertim?')
            empty.add_widget(self.button('Encontrar lanches',self.open_offers))
        for pid,entry in list(self.cart.items()):
            p=entry['item'];q=entry['quantidade']
            card=self.panel(c,f"{q}×  {p['nome']}",money(p['preco_centavos']*q))
            parent=c
            c=card
            row=BoxLayout(size_hint_y=None,height=dp(42),spacing=dp(8))
            row.add_widget(self.button('−',lambda pid=pid:self.adjust_cart(pid,-1),color=BROWN,height=42))
            row.add_widget(self.button('+',lambda pid=pid:self.adjust_cart(pid,1),height=42))
            c.add_widget(row)
            c=parent
        total=sum(e['quantidade']*e['item']['preco_centavos'] for e in self.cart.values())
        c.add_widget(self.label('Total: '+money(total),22,True,65))
        c.add_widget(self.label('O registro da solicitação não confirma a compra.',14,color=GRAY,height=62))
        c.add_widget(self.button('Registrar e abrir WhatsApp',self.checkout,color=GREEN))
        c.add_widget(self.button('Continuar comprando',self.open_offers,color=BROWN))
        return box

    def adjust_cart(self,pid,delta):
        self.cart[pid]['quantidade']+=delta
        if self.cart[pid]['quantidade']<=0:del self.cart[pid]
        if not self.cart:self.selected_seller=None
        self.show('Carrinho',self.cart_screen)

    def checkout(self):
        if not self.cart:self.alert('Adicione produtos primeiro.');return
        items=[{'id_produto':pid,'quantidade':e['quantidade']} for pid,e in self.cart.items()]
        def done(d):
            url='https://wa.me/'+re.sub(r'\D','',d['whatsapp'])+'?text='+quote(d['mensagem'])
            self.request('/pedidos/'+str(d['id_pedido'])+'/encaminhado','POST',{},lambda _:None)
            webbrowser.open(url)
            self.cart={};self.selected_seller=None
            self.alert('Solicitação nº '+str(d['id_pedido'])+' registrada. Confirme diretamente com o vendedor no WhatsApp.')
        self.request('/pedidos','POST',{'itens':items},done)

    def open_profile(self):
        self.request('/perfil',done=lambda d:self.draw_profile(d['usuario']))

    def draw_profile(self,user):
        self.profile_data=user
        self.show('Perfil',self.profile_screen)

    def profile_screen(self):
        box,c=self.page('Meu perfil',lambda:self.show('Inicio',self.home_screen))
        c.add_widget(self.label('Minha conta',24,True,dp(52)))
        card=self.panel(c,'Seus dados', 'Atualize suas informações quando quiser.')
        if self.profile_data.get('foto_url'):
            card.add_widget(AsyncImage(source=self.api.base_url+self.profile_data['foto_url'],size_hint_y=None,height=dp(110)))
        self.profile_photo=None
        card.add_widget(self.button('📷  Escolher foto de perfil',lambda:self.pick_photo('profile'),color=BROWN,height=42))
        self.profile_photo_notice=self.label('Foto opcional',12,height=dp(25),color=GRAY)
        card.add_widget(self.profile_photo_notice)
        self.hint(card,'Nome')
        self.profile_name=self.input('Nome completo');self.profile_name.text=self.profile_data.get('nome','');card.add_widget(self.profile_name)
        self.hint(card,'E-mail')
        self.profile_email=self.input('E-mail');self.profile_email.text=self.profile_data.get('email','');card.add_widget(self.profile_email)
        self.hint(card,'Celular • DDD 81')
        self.profile_phone=self.input('(81) 99999-9999');self.profile_phone.text=self.profile_data.get('telefone','');card.add_widget(self.profile_phone)
        self.profile_phone.bind(text=self._phone_mask)
        self.hint(card,'Senha atual (para alterar os dados)')
        self.profile_password=self.input('Confirme a senha atual',True);card.add_widget(self.profile_password)
        card.add_widget(self.button('Salvar alterações',self.save_profile))
        pw_card=self.panel(c,'Segurança da conta','Troque sua senha sem alterar seus outros dados.')
        pw_card.add_widget(self.button('Alterar minha senha',lambda:self.show('AlterarSenha',self.change_password_screen),color=BROWN,icon='lock'))
        photo_card=self.panel(c,'Conta e privacidade','Excluir é definitivo e remove os pedidos relacionados.')
        photo_card.add_widget(self.button('Excluir minha conta',self.confirm_delete_account,color=(.75,.18,.15,1)))
        return box

    def change_password_screen(self):
        box,c=self.page('Alterar senha',self.open_profile)
        card=self.panel(c,'Proteja sua conta','Sua sessão será encerrada depois da alteração.')
        self.hint(card,'Senha atual')
        self.current_password=self.input('Digite sua senha atual',True);card.add_widget(self.current_password)
        self.hint(card,'Nova senha')
        self.new_password=self.input('Mínimo de 8 caracteres',True);card.add_widget(self.new_password)
        self.hint(card,'Confirme a nova senha')
        self.confirm_password=self.input('Repita a nova senha',True);card.add_widget(self.confirm_password)
        card.add_widget(self.button('Salvar nova senha',self.save_new_password,icon='lock'))
        return box

    def save_new_password(self):
        old=self.current_password.text
        new=self.new_password.text
        if not old:self.alert('Informe sua senha atual.');return
        if len(new)<8:self.alert('A nova senha deve ter ao menos 8 caracteres.');return
        if new!=self.confirm_password.text:self.alert('As novas senhas não coincidem.');return
        if old==new:self.alert('Escolha uma senha diferente da atual.');return
        def done(_):
            self.logout()
            self.alert('Senha alterada! Entre novamente com a nova senha.')
        self.request('/perfil/senha','POST',{'senha_atual':old,'nova_senha':new},done)

    def save_profile(self):
        phone=self._normalize_phone(self.profile_phone.text)
        if not phone:self.alert('Celular inválido. Use (81) 99999-9999.');return
        if not self.profile_password.text:self.alert('Digite sua senha atual para confirmar.');return
        data={'nome':self.profile_name.text.strip(),'email':self.profile_email.text.strip(),'telefone':phone,'senha_atual':self.profile_password.text}
        def saved(d):
            self.user=d['usuario']
            if self.profile_photo:
                self.upload_photo('profile',None,self.profile_photo,lambda:self.open_profile())
            else:self.open_profile()
        self.request('/perfil','PATCH',data,saved)

    def confirm_delete_account(self):
        box=BoxLayout(orientation='vertical',padding=dp(14),spacing=dp(10))
        box.add_widget(self.label('Excluir conta e pedidos relacionados? Não é possível desfazer.',15,height=dp(110)))
        pwd=self.input('Digite sua senha para confirmar',True);box.add_widget(pwd)
        popup=Popup(title='Confirmar exclusão',content=box,size_hint=(.9,.43))
        def execute():
            if not pwd.text:self.alert('Digite a senha.');return
            popup.dismiss()
            self.request('/perfil','DELETE',{'senha_atual':pwd.text},lambda _:self.logout())
        box.add_widget(self.button('Sim, excluir definitivamente',execute,color=(.75,.18,.15,1)))
        box.add_widget(self.secondary_button('Cancelar',popup.dismiss))
        popup.open()

    def pick_photo(self,kind):
        def accepted(paths):
            if not paths:return
            try:
                path=paths[0]
                with open(path,'rb') as f: photo=f.read(1_500_001)
                if len(photo)>1_500_000:raise ValueError('Foto muito grande (máximo 1,5 MB).')
                if not (photo.startswith(b'\xff\xd8\xff') or photo.startswith(b'\x89PNG\r\n\x1a\n')):
                    raise ValueError('Escolha uma imagem JPG ou PNG.')
                if kind=='profile':
                    self.profile_photo=photo;self.profile_photo_notice.text='Foto escolhida: '+os.path.basename(path)
                else:
                    self.product_photo=photo;self.photo_notice.text='Foto escolhida: '+os.path.basename(path)
            except Exception as e:self.alert(str(e))
        if platform=='android':
            try:
                from plyer import filechooser
                filechooser.open_file(on_selection=lambda paths:Clock.schedule_once(lambda _:accepted(paths)))
            except Exception as e:self.alert('Não foi possível abrir a galeria: '+str(e))
        else:
            layout=BoxLayout(orientation='vertical')
            chooser=FileChooserListView(filters=['*.jpg','*.jpeg','*.png'],path=os.path.expanduser('~'))
            layout.add_widget(chooser)
            popup=Popup(title='Escolha uma foto JPG ou PNG',content=layout,size_hint=(.94,.86))
            def select():
                paths=chooser.selection
                popup.dismiss()
                accepted(paths)
            layout.add_widget(self.button('Usar esta foto',select))
            popup.open()

    def upload_photo(self,kind,product_id,photo,done):
        endpoint='/perfil/foto' if kind=='profile' else '/produtos/'+str(product_id)+'/foto'
        self.request(endpoint,'POST',{'imagem_base64':base64.b64encode(photo).decode('ascii')},lambda _:done())

    def open_orders(self):self.request('/pedidos',done=lambda d:self.draw_orders(d['pedidos']))
    def draw_orders(self,orders):self.orders=orders;self.show('Pedidos',self.orders_screen)
    def orders_screen(self):
        box,c=self.page('Solicitações',lambda:self.show('Inicio',self.home_screen))
        c.add_widget(self.label('Histórico de solicitações',21,True,70))
        if not self.orders:c.add_widget(self.label('Nenhuma solicitação registrada.',16))
        for p in self.orders:
            self.panel(c,f"Pedido #{p['id']} • {money(p['valor_centavos'])}",p['outra_pessoa']+' • '+p['tipo']+' • '+p['status'])
        return box

if __name__=='__main__':
    VoLanchar().run()
