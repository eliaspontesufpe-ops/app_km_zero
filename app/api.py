import json
import ssl
import certifi
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

class APIError(Exception):
    pass

class API:
    def __init__(self, base_url):
        self.base_url=base_url.rstrip('/')
        self.token=''

    def call(self, path, method='GET', data=None):
        headers={'Accept':'application/json'}
        if self.token:headers['Authorization']='Bearer '+self.token
        raw=None
        if data is not None:
            headers['Content-Type']='application/json'
            raw=json.dumps(data,ensure_ascii=False).encode('utf-8')
        req=Request(self.base_url+'/api'+path,data=raw,headers=headers,method=method)
        try:
            with urlopen(req,timeout=90,context=ssl.create_default_context(cafile=certifi.where())) as res:
                return json.loads(res.read().decode('utf-8'))
        except HTTPError as e:
            try:body=json.loads(e.read().decode('utf-8'))
            except Exception:body={}
            raise APIError(body.get('erro','Erro HTTP '+str(e.code))) from e
        except (URLError,TimeoutError,OSError) as e:
            raise APIError('Não foi possível acessar a API: '+str(e)) from e
