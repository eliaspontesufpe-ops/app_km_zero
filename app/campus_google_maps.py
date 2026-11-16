"""Links oficiais Google Maps para locais fixos da UFRPE, sem pedir GPS ou chave API.

A pesquisa textual usa nome + contexto e deve ser conferida no Google Maps,
pois alguns prédios podem não estar individualmente indexados.
"""
from urllib.parse import urlencode
import webbrowser

CAMPUS_POINTS=(
    'CEGEN', 'RU', 'Reitoria', 'Biblioteca Central',
    'CEGOE', 'Biblioteca Setorial', 'CEAGRI II / DC', 'DEAGRI',
)
CONTEXT='UFRPE Campus Dois Irmãos Recife Pernambuco Brasil'

def maps_url(point_name=None):
    if point_name is not None and point_name not in CAMPUS_POINTS:
        raise ValueError('Ponto não reconhecido: '+str(point_name))
    query=(point_name+' '+CONTEXT) if point_name else 'Universidade Federal Rural de Pernambuco Campus Recife Dois Irmãos'
    return 'https://www.google.com/maps/search/?'+urlencode({'api':'1','query':query})

def open_maps(point_name=None):
    url=maps_url(point_name)
    try:
        from kivy.utils import platform
        if platform=='android':
            from jnius import autoclass
            Intent=autoclass('android.content.Intent')
            Uri=autoclass('android.net.Uri')
            PythonActivity=autoclass('org.kivy.android.PythonActivity')
            activity=PythonActivity.mActivity
            intent=Intent(Intent.ACTION_VIEW,Uri.parse(url))
            activity.startActivity(intent)
            return url
    except (ImportError,RuntimeError):
        pass
    webbrowser.open(url)
    return url
