"""Mapa do VôLanchar com nove pontos fixos e sem GPS.
No Windows usa OpenStreetMap; no Android o Google WebView exige chave própria.
"""
import json

CAMPUS_LAT = -8.01417
CAMPUS_LON = -34.95109
CAMPUS_POINTS = ('CEGEN', 'RU', 'Reitoria', 'Biblioteca Central',
                 'CEGOE', 'Biblioteca Setorial', 'CEAGRI II / DC', 'DEAGRI', 'DMV')
POINT_COORDS = {
    'CEGEN': (-8.015940795970486, -34.95023555261174),
    'RU': (-8.01417, -34.95109),
    'Reitoria': (-8.014058868291098, -34.95032404532747),
    'Biblioteca Central': (-8.013742354595077, -34.948375075510754),
    'CEGOE': (-8.017384184547446, -34.949841247793266),
    'Biblioteca Setorial': (-8.016168835960743, -34.94908820016383),
    'CEAGRI II / DC': (-8.017584879745215, -34.944143647731174),
    'DEAGRI': (-8.017433270582826, -34.94520262873954),
    'DMV': (-8.015346237863117, -34.94916785770348),
}
# Os nove locais são pontos de venda.
EXTRA_REFERENCE_POINTS = {}


def kivy_map_widget(on_point=None):
    """Mapa OSM interno. O clique chama on_point(nome) para abrir ofertas."""
    from kivy_garden.mapview import MapView, MapMarker
    from kivy.metrics import dp
    from kivy.uix.popup import Popup
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label

    mv = MapView(zoom=15, lat=-8.0155, lon=-34.9486,
                 size_hint_y=None, height=dp(350))

    def open_point(name, reference=False):
        box = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        box.add_widget(Label(text=name + (' (referência)' if reference else ''),
                             size_hint_y=None, height=dp(48)))
        popup = Popup(title='Local no campus', content=box,
                      size_hint=(.85, None), height=dp(195))
        if reference or on_point is None:
            btn = Button(text='Fechar', size_hint_y=None, height=dp(44))
            btn.bind(on_release=lambda *_: popup.dismiss())
        else:
            btn = Button(text='Ver ofertas', size_hint_y=None, height=dp(44))
            def go(*_):
                popup.dismiss()
                on_point(name)
            btn.bind(on_release=go)
        box.add_widget(btn)
        popup.open()

    for name, (lat, lon) in POINT_COORDS.items():
        marker = MapMarker(lat=lat, lon=lon)
        marker.bind(on_release=lambda marker, n=name: open_point(n))
        mv.add_marker(marker)
    return mv


def google_map_html(api_key):
    """Mapa interno WebView, com coordenadas fixas, sem buscas automáticas."""
    if not api_key or not api_key.strip():
        raise ValueError('Configure a chave do Google Maps.')
    points = [{'name': n, 'lat': lat, 'lng': lon, 'reference': n in EXTRA_REFERENCE_POINTS}
              for n, (lat, lon) in {**POINT_COORDS, **EXTRA_REFERENCE_POINTS}.items()]
    template = '''<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body,#map{height:100%;margin:0;font-family:Arial}
.note{position:absolute;left:8px;right:8px;bottom:10px;background:#fff8f1;padding:10px;border-radius:10px}</style>
</head><body><div id="map"></div><div id="status" class="note">Pontos fixos da UFRPE; sem GPS.</div>
<script>
const points = __POINTS__;
async function initMap() {
 const {Map,InfoWindow}=await google.maps.importLibrary('maps');
 const {AdvancedMarkerElement,PinElement}=await google.maps.importLibrary('marker');
 const map=new Map(document.getElementById('map'),{center:{lat:-8.0155,lng:-34.9486},zoom:15,
   mapId:'DEMO_MAP_ID',mapTypeControl:false,streetViewControl:false});
 const info=new InfoWindow();
 for (const p of points) {
   const marker=new AdvancedMarkerElement({map,position:{lat:p.lat,lng:p.lng},title:p.name,
     content:(new PinElement({background:'#ef4b00',borderColor:'#3a180b',glyphColor:'#fff'})).element});
   marker.addListener('click',()=>{
     const el=document.createElement('div');
     el.textContent=p.name+(p.reference?' (referência, sem ofertas)':' — consulte as ofertas na lista');
     info.setContent(el);info.open(map,marker);
   });
 }
 document.getElementById('status').textContent=points.length+
   ' pontos fixos posicionados no campus.';
}
window.gm_authFailure=()=>document.getElementById('status').textContent='Erro na configuração do Google Maps.';
</script><script async src="https://maps.googleapis.com/maps/api/js?key=__KEY__&callback=initMap&v=weekly"></script>
</body></html>'''
    from urllib.parse import quote
    return template.replace('__POINTS__', json.dumps(points, ensure_ascii=False)).replace('__KEY__',quote(api_key,safe=''))



def show_android_google_map(api_key):
    """Abre WebView sobre a Activity do próprio VôLanchar (sem navegador externo).
    Retorna True quando o componente foi solicitado. Testar no APK Android.
    """
    from kivy.utils import platform
    if platform!='android':return False
    from android.runnable import run_on_ui_thread
    from jnius import autoclass, PythonJavaClass, java_method
    from kivy.metrics import dp
    import weakref
    Activity=autoclass('org.kivy.android.PythonActivity')
    WebView=autoclass('android.webkit.WebView')
    LinearLayout=autoclass('android.widget.LinearLayout')
    FrameLayout=autoclass('android.widget.FrameLayout')
    View=autoclass('android.view.View')
    Button=autoclass('android.widget.Button')
    ColorAndroid=autoclass('android.graphics.Color')
    activity=Activity.mActivity
    html=google_map_html(api_key)
    holder={}

    class CloseListener(PythonJavaClass):
        __javainterfaces__=['android/view/View$OnClickListener']
        __javacontext__='app'
        @java_method('(Landroid/view/View;)V')
        def onClick(self,v):
            parent=holder.get('parent')
            view=holder.get('view')
            if parent is not None and view is not None:parent.removeView(view)

    @run_on_ui_thread
    def show():
        parent=activity.getWindow().getDecorView().findViewById(16908290)
        container=LinearLayout(activity)
        container.setOrientation(1)
        container.setBackgroundColor(ColorAndroid.WHITE)
        close=Button(activity)
        close.setText('‹ Voltar ao VôLanchar')
        close.setTextColor(ColorAndroid.WHITE)
        close.setBackgroundColor(ColorAndroid.rgb(239,75,0))
        listener=CloseListener()
        holder.update({'parent':parent,'view':container,'listener':listener})
        close.setOnClickListener(listener)
        container.addView(close,LinearLayout.LayoutParams(-1,int(dp(55))))
        browser=WebView(activity)
        settings=browser.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        # Não habilitar geolocalização no WebView.
        container.addView(browser,LinearLayout.LayoutParams(-1,-1))
        browser.loadDataWithBaseURL('https://volanchar-api.onrender.com/',html,'text/html','utf-8',None)
        parent.addView(container,FrameLayout.LayoutParams(-1,-1))
        holder['browser']=browser
    # Referência viva ao listener e overlay enquanto o mapa estiver aberto.
    global _ANDROID_MAP_HOLDER
    _ANDROID_MAP_HOLDER=holder
    show()
    return True
