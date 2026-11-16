"""API Flask do VôLanchar com autenticação, ofertas, pedidos e fotos persistentes."""
import base64
import binascii
import datetime as dt
import hashlib
import hmac
import os
import re
import secrets
import smtplib
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from io import BytesIO

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request, send_file, abort
from werkzeug.exceptions import HTTPException
import mysql.connector
import certifi

load_dotenv(Path(__file__).with_name('.env'))
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2_500_000

def connection():
    config = {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "volanchar"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "volanchar"),
        "autocommit": False,
    }

    if os.getenv("MYSQL_USE_TLS", "false").lower() == "true":
        config.update({
            "ssl_ca": certifi.where(),
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
        })

    return mysql.connector.connect(**config)

def rows(cur):
    return cur.fetchall()

def answer(data, status=200):
    return jsonify(data), status

def fail(msg,status=400):
    return answer({'erro':msg},status)

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 260000)
    return salt.hex(),digest.hex()

def secure_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

def logged(fn):
    @wraps(fn)
    def inner(*args,**kwargs):
        raw=request.headers.get('Authorization','')
        if not raw.startswith('Bearer '): return fail('Entre na sua conta.',401)
        db=connection()
        try:
            cur=db.cursor(dictionary=True)
            cur.execute('SELECT u.id,u.nome,u.email,u.telefone FROM tokens t JOIN usuarios u ON u.id=t.id_usuario WHERE t.token_hash=%s AND t.expira_em>UTC_TIMESTAMP()', (secure_token(raw[7:]),))
            user=cur.fetchone()
            if not user: db.close();return fail('Sessão expirada.',401)
            g.db=db;g.user=user
            return fn(*args,**kwargs)
        finally:
            db.close()
    return inner

@app.errorhandler(Exception)
def general_error(e):
    if isinstance(e, HTTPException):return e
    app.logger.exception('Falha inesperada')
    return fail('Não foi possível concluir a operação.',500)

@app.get('/api/health')
def health():
    return answer({'ok':True,'nome':'VôLanchar API'})

@app.post('/api/registrar')
def register():
    d=request.get_json(silent=True) or {}
    nome=str(d.get('nome','')).strip();email=str(d.get('email','')).strip().lower();senha=str(d.get('senha','')); telefone=re.sub(r'\D','',str(d.get('telefone','')))
    if len(nome)<2 or len(nome)>100: return fail('Informe seu nome.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>190:return fail('E-mail inválido.')
    if not 8<=len(senha)<=256:return fail('Senha precisa ter ao menos 8 caracteres.')
    if not re.fullmatch(r'55819[0-9]{8}',telefone):return fail('Informe WhatsApp de Recife: (81) 99999-9999.')
    salt,digest=hash_password(senha)
    db=connection()
    try:
        cur=db.cursor(dictionary=True)
        try:
            cur.execute('SELECT id FROM usuarios WHERE telefone=%s LIMIT 1',(telefone,))
            if cur.fetchone():return fail('Telefone já cadastrado.',409)
            cur.execute('INSERT INTO usuarios (nome,email,telefone,senha_salt,senha_hash) VALUES (%s,%s,%s,%s,%s)',(nome,email,telefone,salt,digest))
            cur.execute('INSERT INTO vendedores (id_usuario) VALUES (%s)',(cur.lastrowid,))
            db.commit()
        except mysql.connector.IntegrityError:
            db.rollback();return fail('E-mail já cadastrado.',409)
    finally:db.close()
    return login_internal(email,senha)

def login_internal(identificador,senha):
    db=connection()
    try:
        cur=db.cursor(dictionary=True)
        ident=str(identificador).strip().lower()
        digits=re.sub(r'\D','',ident)
        if '@' in ident:
            cur.execute('SELECT * FROM usuarios WHERE email=%s',(ident,))
        elif re.fullmatch(r'(?:55)?81[0-9]{9}',digits):
            if digits.startswith('55'):digits=digits[2:]
            cur.execute('SELECT * FROM usuarios WHERE telefone IN (%s,%s,%s) LIMIT 2',('55'+digits,digits,digits[2:]))
            matches=cur.fetchall()
            if len(matches)>1:return fail('Mais de uma conta usa este telefone. Entre com seu e-mail.',409)
            u=matches[0] if matches else None
        else:
            cur.execute('SELECT * FROM usuarios WHERE email=%s',(ident,))
        if '@' in ident or not re.fullmatch(r'(?:55)?81[0-9]{9}',digits):
            u=cur.fetchone()
        if not u:
            hash_password(senha,b'0'*16)
            return fail('E-mail ou senha inválidos.',401)
        _,digest=hash_password(senha,bytes.fromhex(u['senha_salt']))
        if not hmac.compare_digest(digest,u['senha_hash']):return fail('E-mail ou senha inválidos.',401)
        token=secrets.token_urlsafe(32)
        expiry=dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=7)
        cur.execute('INSERT INTO tokens (token_hash,id_usuario,expira_em) VALUES (%s,%s,%s)',(secure_token(token),u['id'],expiry.replace(tzinfo=None)))
        db.commit()
        return answer({'token':token,'usuario':{'id':u['id'],'nome':u['nome'],'email':u['email']}})
    finally:db.close()

def issue_session(db,cur,user):
    token=secrets.token_urlsafe(32)
    expiry=dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=7)
    cur.execute('INSERT INTO tokens (token_hash,id_usuario,expira_em) VALUES (%s,%s,%s)',
                (secure_token(token),user['id'],expiry.replace(tzinfo=None)))
    db.commit()
    return answer({'token':token,'usuario':{'id':user['id'],'nome':user['nome'],'email':user['email']}})


def checked_google_identity(raw_token):
    client_id=(os.getenv('GOOGLE_CLIENT_ID') or os.getenv('GOOGLE_WEB_CLIENT_ID') or '').strip()
    if not client_id:return None,'Login Google não configurado no servidor.'
    if not isinstance(raw_token,str) or not 50<len(raw_token)<10000:
        return None,'Token do Google inválido.'
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        claims=id_token.verify_oauth2_token(raw_token,google_requests.Request(),client_id)
    except Exception:
        app.logger.warning('Token Google inválido ou falha na validação',exc_info=True)
        return None,'Não foi possível validar a conta Google.'
    if not claims.get('email_verified') or not claims.get('sub') or not claims.get('email'):
        return None,'A conta Google precisa ter e-mail verificado.'
    return {'sub':str(claims['sub']),'email':str(claims['email']).lower(),
            'nome':str(claims.get('name') or '').strip()[:100]},None


@app.post('/api/google/entrar')
def google_login():
    d=request.get_json(silent=True) or {}
    identity,error=checked_google_identity(d.get('id_token'))
    if error:return fail(error,401 if 'Token' in error or 'validar' in error else 503)
    subject,email=identity['sub'],identity['email']
    db=connection()
    try:
        cur=db.cursor(dictionary=True)
        cur.execute("""SELECT u.id,u.nome,u.email FROM google_contas gc
            JOIN usuarios u ON u.id=gc.id_usuario WHERE gc.google_sub=%s""",(subject,))
        linked=cur.fetchone()
        if linked:return issue_session(db,cur,linked)
        cur.execute('SELECT id,nome,email,senha_salt,senha_hash FROM usuarios WHERE email=%s',(email,))
        user=cur.fetchone()
        if user:
            password=str(d.get('senha',''))
            if not password:
                return answer({'etapa':'vincular','email':email,'nome':identity['nome']})
            _,digest=hash_password(password,bytes.fromhex(user['senha_salt']))
            if not hmac.compare_digest(digest,user['senha_hash']):
                return fail('Senha do VôLanchar incorreta. Use sua senha atual.',401)
            try:
                cur.execute('INSERT INTO google_contas (google_sub,id_usuario) VALUES (%s,%s)',(subject,user['id']))
                return issue_session(db,cur,user)
            except mysql.connector.IntegrityError:
                db.rollback()
                return fail('Esta conta já está vinculada a outro login Google.',409)

        nome=str(d.get('nome','')).strip()
        telefone=re.sub(r'\D','',str(d.get('telefone','')))
        password=str(d.get('senha',''))
        if not nome and not telefone and not password:
            return answer({'etapa':'cadastro','nome':identity['nome'],'email':email})
        if not 2<=len(nome)<=100:return fail('Informe seu nome completo.')
        if not re.fullmatch(r'55819[0-9]{8}',telefone):return fail('Informe WhatsApp no formato (81) 99999-9999.')
        if not 8<=len(password)<=256:return fail('Crie uma senha com no mínimo 8 caracteres.')
        salt,digest=hash_password(password)
        try:
            cur.execute('INSERT INTO usuarios (nome,email,telefone,senha_salt,senha_hash) VALUES (%s,%s,%s,%s,%s)',
                        (nome,email,telefone,salt,digest))
            user_id=cur.lastrowid
            cur.execute('INSERT INTO vendedores (id_usuario) VALUES (%s)',(user_id,))
            cur.execute('INSERT INTO google_contas (google_sub,id_usuario) VALUES (%s,%s)',(subject,user_id))
            return issue_session(db,cur,{'id':user_id,'nome':nome,'email':email})
        except mysql.connector.IntegrityError:
            db.rollback()
            return fail('E-mail ou telefone já cadastrado. Entre com sua conta existente.',409)
    finally:
        db.close()


@app.post('/api/entrar')
def login():
    d=request.get_json(silent=True) or {}
    return login_internal(str(d.get('identificador') or d.get('email','')).strip(),str(d.get('senha','')))

def recovery_hash(email,code):
    # Nunca armazenamos o código de recuperação em texto claro.
    secret=os.getenv('APP_SECRET','')
    return hmac.new(secret.encode('utf-8'),(email+':'+code).encode('utf-8'),hashlib.sha256).hexdigest()


def send_recovery_email(email,code):
    host=os.getenv('SMTP_HOST','').strip()
    sender=os.getenv('SMTP_FROM','').strip()
    user=os.getenv('SMTP_USER','').strip()
    password=os.getenv('SMTP_PASSWORD','')
    if not host or not sender:
        raise RuntimeError('SMTP não configurado: preencha SMTP_HOST e SMTP_FROM no backend/.env.')
    msg=EmailMessage()
    msg['Subject']='VôLanchar — Código para redefinir sua senha'
    msg['From']=sender
    msg['To']=email
    msg.set_content('Seu código de recuperação do VôLanchar é: '+code+'\n\nVálido por 15 minutos. Se não solicitou, ignore este e-mail.')
    port=int(os.getenv('SMTP_PORT','587'))
    if port==465:
        with smtplib.SMTP_SSL(host,port,timeout=15) as smtp:
            if user:smtp.login(user,password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host,port,timeout=15) as smtp:
            smtp.starttls()
            if user:smtp.login(user,password)
            smtp.send_message(msg)


@app.post('/api/senha/solicitar')
def request_reset_password():
    d=request.get_json(silent=True) or {}
    email=str(d.get('email','')).strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):return fail('Informe um e-mail válido.')
    if not os.getenv('SMTP_HOST') or not os.getenv('SMTP_FROM'):
        return fail('Recuperação por e-mail indisponível: configure o SMTP no servidor.',503)
    if len(os.getenv('APP_SECRET',''))<24:
        return fail('Recuperação indisponível: configure APP_SECRET seguro no servidor.',503)
    # Resposta idêntica para e-mails conhecidos e desconhecidos: evita revelar contas.
    generic={'mensagem':'Se o e-mail estiver cadastrado, você receberá um código de recuperação.'}
    db=connection()
    try:
        cur=db.cursor(dictionary=True)
        cur.execute('SELECT id FROM usuarios WHERE email=%s',(email,))
        user=cur.fetchone()
        if not user:return answer(generic)
        uid=user['id']
        cur.execute('SELECT criado_em FROM recuperacao_senhas WHERE id_usuario=%s',(uid,))
        previous=cur.fetchone()
        if previous and (dt.datetime.utcnow()-previous['criado_em']).total_seconds()<60:
            return answer(generic)
        code=f'{secrets.randbelow(100_000_000):08d}'
        digest=recovery_hash(email,code)
        expiry=dt.datetime.utcnow()+dt.timedelta(minutes=15)
        cur.execute('''INSERT INTO recuperacao_senhas
            (id_usuario,codigo_hash,expira_em,tentativas,criado_em)
            VALUES (%s,%s,%s,0,UTC_TIMESTAMP())
            ON DUPLICATE KEY UPDATE codigo_hash=VALUES(codigo_hash), expira_em=VALUES(expira_em),
              tentativas=0, criado_em=UTC_TIMESTAMP()''',(uid,digest,expiry))
        try:
            send_recovery_email(email,code)
        except Exception:
            db.rollback()
            app.logger.exception('Falha no envio de e-mail de recuperação')
            return fail('Não foi possível enviar o e-mail agora. Verifique o SMTP.',503)
        db.commit()
        return answer(generic)
    finally:db.close()


@app.post('/api/senha/redefinir')
def reset_password():
    d=request.get_json(silent=True) or {}
    email=str(d.get('email','')).strip().lower()
    code=str(d.get('codigo','')).strip()
    new=str(d.get('nova_senha',''))
    if not re.fullmatch(r'[0-9]{8}',code):return fail('Código inválido ou expirado.',400)
    if not 8<=len(new)<=256:return fail('A senha deve ter de 8 a 256 caracteres.')
    db=connection()
    try:
        cur=db.cursor(dictionary=True)
        cur.execute('''SELECT u.id,r.codigo_hash,r.tentativas,r.expira_em
          FROM usuarios u JOIN recuperacao_senhas r ON r.id_usuario=u.id
          WHERE u.email=%s FOR UPDATE''',(email,))
        record=cur.fetchone()
        if not record:return fail('Código inválido ou expirado.',400)
        if record['tentativas']>=5 or record['expira_em']<=dt.datetime.utcnow():
            return fail('Código inválido ou expirado.',400)
        valid=hmac.compare_digest(record['codigo_hash'],recovery_hash(email,code))
        if not valid:
            cur.execute('UPDATE recuperacao_senhas SET tentativas=tentativas+1 WHERE id_usuario=%s',(record['id'],))
            db.commit()
            return fail('Código inválido ou expirado.',400)
        salt,digest=hash_password(new)
        cur.execute('UPDATE usuarios SET senha_salt=%s,senha_hash=%s WHERE id=%s',(salt,digest,record['id']))
        cur.execute('DELETE FROM tokens WHERE id_usuario=%s',(record['id'],))
        cur.execute('DELETE FROM recuperacao_senhas WHERE id_usuario=%s',(record['id'],))
        db.commit()
        return answer({'ok':True})
    finally:db.close()


@app.post('/api/perfil/senha')
@logged
def change_password():
    d=request.get_json(silent=True) or {}
    current=str(d.get('senha_atual',''))
    new=str(d.get('nova_senha',''))
    if not 8<=len(new)<=256:return fail('A nova senha deve ter de 8 a 256 caracteres.')
    if current==new:return fail('Escolha uma senha diferente da atual.')
    cur=g.db.cursor(dictionary=True)
    cur.execute('SELECT senha_salt,senha_hash FROM usuarios WHERE id=%s FOR UPDATE',(g.user['id'],))
    record=cur.fetchone()
    _,check=hash_password(current,bytes.fromhex(record['senha_salt']))
    if not hmac.compare_digest(record['senha_hash'],check):return fail('Senha atual incorreta.',401)
    salt,digest=hash_password(new)
    cur.execute('UPDATE usuarios SET senha_salt=%s,senha_hash=%s WHERE id=%s',(salt,digest,g.user['id']))
    cur.execute('DELETE FROM tokens WHERE id_usuario=%s',(g.user['id'],))
    g.db.commit()
    return answer({'ok':True,'mensagem':'Senha alterada. Entre novamente.'})


PONTOS_CAMPUS = (
    'CEGEN',
    'RU',
    'Reitoria',
    'Biblioteca Central',
    'CEGOE',
    'Biblioteca Setorial',
    'CEAGRI II / DC',
    'DEAGRI',
    'DMV',
)

@app.get('/api/pontos')
def points():
    db=connection()
    try:
        cur=db.cursor(dictionary=True)
        # O catálogo oficial é definido pelo campus Recife; pontos antigos permanecem
        # preservados no banco, mas não são oferecidos para novas configurações.
        cur.execute('SELECT id,nome FROM pontos WHERE nome IN ('+
                    ','.join(['%s']*len(PONTOS_CAMPUS))+') ORDER BY nome', PONTOS_CAMPUS)
        return answer({'pontos':rows(cur)})
    finally:db.close()

@app.get('/api/ofertas')
def offers():
    point=request.args.get('ponto')
    db=connection()
    try:
        cur=db.cursor(dictionary=True)
        sql='''SELECT u.id AS vendedor_id,u.nome AS vendedor,
                   COALESCE(NULLIF(nl.nome,''),u.nome) AS estabelecimento,
                   v.whatsapp,p.nome AS ponto,
                  pr.id AS id,pr.nome,pr.descricao,pr.preco_centavos,
                  v.vendendo AS disponivel_agora
               FROM vendedores v JOIN usuarios u ON u.id=v.id_usuario
               LEFT JOIN nomes_lojas nl ON nl.id_usuario=v.id_usuario
               JOIN pontos p ON p.id=v.id_ponto
               JOIN produtos pr ON pr.id_vendedor=u.id
               WHERE v.vendendo=1 AND pr.disponivel=1 AND pr.excluido_em IS NULL'''
        sql+=' AND p.nome IN ('+','.join(['%s']*len(PONTOS_CAMPUS))+')'
        args=tuple(PONTOS_CAMPUS)
        if point:
            if not point.isdigit():return fail('Ponto inválido.')
            sql+=' AND p.id=%s';args=args+(int(point),)
        cur.execute(sql+' ORDER BY p.nome,u.nome,pr.nome',args)
        result=rows(cur)
        for item in result:item['foto_url']=photo_url('produto',item['id'],db)
        return answer({'ofertas':result})
    finally:db.close()

@app.get('/api/minha-loja')
@logged
def store():
    cur=g.db.cursor(dictionary=True)
    cur.execute('SELECT id_ponto,whatsapp,vendendo FROM vendedores WHERE id_usuario=%s',(g.user['id'],))
    loja=cur.fetchone()
    cur.execute('SELECT nome FROM nomes_lojas WHERE id_usuario=%s',(g.user['id'],))
    nome_loja=cur.fetchone()
    if loja is not None:
        loja['nome_estabelecimento']=nome_loja['nome'] if nome_loja else ''
    cur.execute('SELECT id,nome,descricao,preco_centavos,disponivel FROM produtos WHERE id_vendedor=%s AND excluido_em IS NULL ORDER BY id DESC',(g.user['id'],))
    products=rows(cur)
    for p in products:p['foto_url']=photo_url('produto',p['id'],g.db)
    return answer({'loja':loja,'produtos':products})

@app.post('/api/minha-loja')
@logged
def set_store():
    d=request.get_json(silent=True) or {}
    pid=d.get('id_ponto');phone=re.sub(r'\D','',str(d.get('whatsapp','')))
    nome_estabelecimento=str(d.get('nome_estabelecimento','')).strip()[:120]
    if not str(pid).isdigit():return fail('Escolha um ponto de venda.')
    if not 10<=len(phone)<=15:return fail('Informe o WhatsApp completo com DDI.')
    cur=g.db.cursor()
    cur.execute('SELECT id FROM pontos WHERE id=%s',(pid,))
    if not cur.fetchone():return fail('Ponto inexistente.')
    cur.execute('UPDATE vendedores SET id_ponto=%s,whatsapp=%s,vendendo=%s WHERE id_usuario=%s',(pid,phone,int(bool(d.get('vendendo'))),g.user['id']))
    if 'nome_estabelecimento' in d:
        cur.execute('''INSERT INTO nomes_lojas (id_usuario,nome) VALUES (%s,%s)
            ON DUPLICATE KEY UPDATE nome=VALUES(nome)''',(g.user['id'],nome_estabelecimento))
    g.db.commit();return answer({'ok':True})

@app.post('/api/produtos')
@logged
def add_product():
    d=request.get_json(silent=True) or {}
    nome=str(d.get('nome','')).strip();descricao=str(d.get('descricao','')).strip()
    try:preco=int(d.get('preco_centavos'))
    except (ValueError,TypeError):return fail('Preço inválido.')
    if not nome or len(nome)>120 or len(descricao)>240 or not 0<preco<=100000000:return fail('Confira nome e preço.')
    cur=g.db.cursor();cur.execute('INSERT INTO produtos (id_vendedor,nome,descricao,preco_centavos) VALUES (%s,%s,%s,%s)',(g.user['id'],nome,descricao,preco))
    g.db.commit();return answer({'id':cur.lastrowid},201)

@app.patch('/api/produtos/<int:pid>')
@logged
def edit_product(pid):
    d=request.get_json(silent=True) or {}
    cur=g.db.cursor(dictionary=True)
    cur.execute('SELECT * FROM produtos WHERE id=%s AND id_vendedor=%s AND excluido_em IS NULL',(pid,g.user['id']))
    old=cur.fetchone()
    if not old:return fail('Produto não encontrado.',404)
    nome=str(d.get('nome',old['nome'])).strip();desc=str(d.get('descricao',old['descricao'])).strip()
    try:preco=int(d.get('preco_centavos',old['preco_centavos']))
    except (ValueError,TypeError):return fail('Preço inválido.')
    available=int(bool(d.get('disponivel',old['disponivel'])))
    if not nome or len(nome)>120 or len(desc)>240 or not 0<preco<=100000000:return fail('Dados inválidos.')
    cur.execute('UPDATE produtos SET nome=%s,descricao=%s,preco_centavos=%s,disponivel=%s WHERE id=%s',(nome,desc,preco,available,pid))
    g.db.commit();return answer({'ok':True})

@app.delete('/api/produtos/<int:pid>')
@logged
def delete_product(pid):
    """Exclusão lógica: preserva o histórico de pedidos e retira da loja/vitrine."""
    cur=g.db.cursor()
    cur.execute("""UPDATE produtos SET disponivel=0,excluido_em=UTC_TIMESTAMP()
        WHERE id=%s AND id_vendedor=%s AND excluido_em IS NULL""",(pid,g.user['id']))
    if cur.rowcount==0:
        # Repetir a exclusão retorna sucesso somente se o item já pertenceu à conta.
        cur.execute('SELECT id FROM produtos WHERE id=%s AND id_vendedor=%s',
                    (pid,g.user['id']))
        if not cur.fetchone():return fail('Produto não encontrado.',404)
    g.db.commit()
    return answer({'ok':True})

@app.post('/api/pedidos')
@logged
def checkout():
    d=request.get_json(silent=True) or {}; items=d.get('itens')
    if not isinstance(items,list) or not 1<=len(items)<=30:return fail('Inclua produtos no pedido.')
    normalized={}
    try:
        for item in items:
            pid=int(item['id_produto']);q=int(item['quantidade'])
            if q<1 or q>99 or pid in normalized:return fail('Itens inválidos ou repetidos.')
            normalized[pid]=q
    except (ValueError,TypeError,KeyError):return fail('Itens inválidos.')
    db=g.db;cur=db.cursor(dictionary=True)
    try:
        ids=list(normalized)
        marks=','.join(['%s']*len(ids))
        cur.execute(f'''SELECT pr.id,pr.nome,pr.preco_centavos,pr.id_vendedor,u.nome AS vendedor,
                   v.whatsapp,p.nome AS ponto FROM produtos pr JOIN vendedores v ON v.id_usuario=pr.id_vendedor
                   JOIN usuarios u ON u.id=pr.id_vendedor JOIN pontos p ON p.id=v.id_ponto
                   WHERE pr.id IN ({marks}) AND pr.disponivel=1 AND pr.excluido_em IS NULL AND v.vendendo=1 FOR UPDATE''',tuple(ids))
        products=cur.fetchall()
        if len(products)!=len(ids):return fail('Há produtos indisponíveis. Atualize o carrinho.')
        sellers={p['id_vendedor'] for p in products}
        if len(sellers)!=1:return fail('Cada pedido deve conter produtos de um só vendedor.')
        seller=products[0];total=sum(p['preco_centavos']*normalized[p['id']] for p in products)
        if seller['id_vendedor']==g.user['id']:return fail('Não é possível pedir para si mesmo.')
        if not seller['whatsapp']:return fail('O vendedor ainda não cadastrou WhatsApp.')
        cur.execute('INSERT INTO pedidos(id_comprador,id_vendedor,valor_centavos) VALUES (%s,%s,%s)',(g.user['id'],seller['id_vendedor'],total))
        pedido_id=cur.lastrowid
        lines=[]
        for p in products:
            q=normalized[p['id']];part=p['preco_centavos']*q
            cur.execute('INSERT INTO itens_pedido(id_pedido,id_produto,quantidade,preco_unitario_centavos,subtotal_centavos) VALUES (%s,%s,%s,%s,%s)',(pedido_id,p['id'],q,p['preco_centavos'],part))
            lines.append(f"{q}x {p['nome']} - R$ {part/100:.2f}")
        db.commit()
        msg=f"Olá! Fiz uma solicitação no VôLanchar (nº {pedido_id}):\n"+'\n'.join(lines)+f"\nTotal: R$ {total/100:.2f}\nRetirada: {seller['ponto']}\nPodemos confirmar?"
        return answer({'id_pedido':pedido_id,'mensagem':msg,'whatsapp':seller['whatsapp'],'total_centavos':total},201)
    except Exception:
        db.rollback();raise

@app.post('/api/pedidos/<int:pid>/encaminhado')
@logged
def forwarded(pid):
    cur=g.db.cursor();cur.execute('UPDATE pedidos SET status=%s WHERE id=%s AND id_comprador=%s AND status=%s',('ENCAMINHAMENTO_TENTADO',pid,g.user['id'],'INICIADO'))
    g.db.commit();return answer({'ok':cur.rowcount>0})

@app.get('/api/pedidos')
@logged
def orders():
    '''Numeração amigável por conta, independente da chave interna do banco.

    A numeração é crescente por ordem de criação e estável com novos pedidos.
    O limite de 100 retorna os pedidos recentes sem redefinir a numeração.
    '''
    cur=g.db.cursor(dictionary=True)
    cur.execute('''SELECT * FROM (
        SELECT p.id,p.valor_centavos,p.status,p.criado_em,u.nome AS outra_pessoa,
        CASE WHEN p.id_comprador=%s THEN 'compra' ELSE 'venda' END AS tipo,
        ROW_NUMBER() OVER (ORDER BY p.id ASC) AS numero_exibicao
        FROM pedidos p
        JOIN usuarios u ON u.id=CASE WHEN p.id_comprador=%s THEN p.id_vendedor ELSE p.id_comprador END
        WHERE p.id_comprador=%s OR p.id_vendedor=%s
    ) numerados ORDER BY id DESC LIMIT 100''',
       (g.user['id'],g.user['id'],g.user['id'],g.user['id']))
    result=rows(cur)
    for record in result:
        record['criado_em']=record['criado_em'].isoformat() if record.get('criado_em') else None
        record['numero_exibicao']=int(record['numero_exibicao'])
    result.sort(key=lambda record:int(record['numero_exibicao']))
    return answer({'pedidos':result})


@app.get('/api/pedidos/<int:pid>')
@logged
def order_details(pid):
    '''Somente comprador ou vendedor podem consultar itens e avaliação.'''
    cur=g.db.cursor(dictionary=True)
    cur.execute('''SELECT p.id,p.id_comprador,p.id_vendedor,p.status,p.valor_centavos,p.criado_em,
        c.nome AS comprador_nome,v.nome AS vendedor_nome,
        po.nome AS ponto
        FROM pedidos p
        JOIN usuarios c ON c.id=p.id_comprador
        JOIN usuarios v ON v.id=p.id_vendedor
        LEFT JOIN vendedores ve ON ve.id_usuario=p.id_vendedor
        LEFT JOIN pontos po ON po.id=ve.id_ponto
        WHERE p.id=%s AND (p.id_comprador=%s OR p.id_vendedor=%s)''',
        (pid,g.user['id'],g.user['id']))
    pedido=cur.fetchone()
    if not pedido:return fail('Pedido não encontrado ou sem permissão.',404)
    cur.execute('''SELECT i.id_produto,pr.nome, i.quantidade,
        i.preco_unitario_centavos,i.subtotal_centavos
        FROM itens_pedido i JOIN produtos pr ON pr.id=i.id_produto
        WHERE i.id_pedido=%s ORDER BY i.id_produto''',(pid,))
    itens=cur.fetchall()
    cur.execute('''SELECT nota,comentario,criado_em FROM avaliacoes_pedidos
        WHERE id_pedido=%s''',(pid,))
    avaliacao=cur.fetchone()
    if avaliacao and avaliacao.get('criado_em'):
        avaliacao['criado_em']=avaliacao['criado_em'].isoformat()
    if pedido.get('criado_em'):pedido['criado_em']=pedido['criado_em'].isoformat()
    cur.execute('''SELECT COUNT(*) AS numero FROM pedidos WHERE id<=%s
        AND (id_comprador=%s OR id_vendedor=%s)''',
        (pid,g.user['id'],g.user['id']))
    pedido['numero_exibicao']=int(cur.fetchone()['numero'])
    pedido['tipo']='compra' if pedido['id_comprador']==g.user['id'] else 'venda'
    pedido['itens']=itens
    pedido['avaliacao']=avaliacao
    return answer({'pedido':pedido})


@app.post('/api/pedidos/<int:pid>/atendido')
@logged
def mark_attended(pid):
    '''Vendedor informa que atendeu; ainda não é conclusão pelo comprador.'''
    cur=g.db.cursor(dictionary=True)
    cur.execute('SELECT id_vendedor,status FROM pedidos WHERE id=%s FOR UPDATE',(pid,))
    pedido=cur.fetchone()
    if not pedido or pedido['id_vendedor']!=g.user['id']:
        return fail('Pedido não encontrado ou sem permissão.',404)
    if pedido['status']=='ATENDIDO':return answer({'ok':True,'status':'ATENDIDO'})
    if pedido['status']=='CONCLUIDO':return fail('Pedido já concluído.',409)
    if pedido['status'] not in ('INICIADO','ENCAMINHAMENTO_TENTADO'):
        return fail('Este pedido não pode ser marcado como atendido.',409)
    cur.execute('UPDATE pedidos SET status=%s WHERE id=%s',('ATENDIDO',pid))
    g.db.commit()
    return answer({'ok':True,'status':'ATENDIDO'})


@app.post('/api/pedidos/<int:pid>/concluir')
@logged
def confirm_received(pid):
    '''Apenas o comprador confirma o recebimento e finaliza o pedido.'''
    cur=g.db.cursor(dictionary=True)
    cur.execute('SELECT id_comprador,status FROM pedidos WHERE id=%s FOR UPDATE',(pid,))
    pedido=cur.fetchone()
    if not pedido or pedido['id_comprador']!=g.user['id']:
        return fail('Pedido não encontrado ou sem permissão.',404)
    if pedido['status']=='CONCLUIDO':return answer({'ok':True,'status':'CONCLUIDO'})
    if pedido['status']!='ATENDIDO':
        return fail('O vendedor precisa marcar o pedido como atendido antes da confirmação.',409)
    cur.execute('UPDATE pedidos SET status=%s WHERE id=%s',('CONCLUIDO',pid))
    g.db.commit()
    return answer({'ok':True,'status':'CONCLUIDO'})


@app.post('/api/pedidos/<int:pid>/avaliacao')
@logged
def rate_order(pid):
    '''Uma avaliação de 1 a 5 estrelas por pedido concluído, opcional.'''
    data=request.get_json(silent=True) or {}
    try:
        nota=int(data.get('nota'))
    except (ValueError,TypeError):return fail('Escolha uma nota de 1 a 5.',400)
    comentario=str(data.get('comentario') or '').strip()
    if not 1<=nota<=5:return fail('Escolha uma nota de 1 a 5.',400)
    if len(comentario)>500:return fail('Comentário deve ter até 500 caracteres.',400)
    cur=g.db.cursor(dictionary=True)
    cur.execute('SELECT id_comprador,status FROM pedidos WHERE id=%s',(pid,))
    pedido=cur.fetchone()
    if not pedido or pedido['id_comprador']!=g.user['id']:
        return fail('Pedido não encontrado ou sem permissão.',404)
    if pedido['status']!='CONCLUIDO':
        return fail('A avaliação só fica disponível após a conclusão do pedido.',409)
    try:
        cur.execute('''INSERT INTO avaliacoes_pedidos(id_pedido,id_comprador,nota,comentario)
            VALUES (%s,%s,%s,%s)''',(pid,g.user['id'],nota,comentario))
        g.db.commit()
    except mysql.connector.IntegrityError:
        g.db.rollback()
        return fail('Este pedido já foi avaliado.',409)
    return answer({'ok':True,'nota':nota},201)


@app.get('/api/pedidos/<int:pid>/contato')
@logged
def order_contact(pid):
    """Reabrir WhatsApp sem criar outro pedido; só comprador do pedido."""
    cur=g.db.cursor(dictionary=True)
    cur.execute('''SELECT p.id, p.valor_centavos, v.whatsapp, po.nome AS ponto
        FROM pedidos p
        JOIN vendedores v ON v.id_usuario=p.id_vendedor
        LEFT JOIN pontos po ON po.id=v.id_ponto
        WHERE p.id=%s AND p.id_comprador=%s''', (pid,g.user['id']))
    order=cur.fetchone()
    if not order:return fail('Solicitação não encontrada.',404)
    if not order['whatsapp']:return fail('O vendedor ainda não informou um WhatsApp.',409)
    cur.execute('''SELECT i.quantidade, i.subtotal_centavos, pr.nome
        FROM itens_pedido i JOIN produtos pr ON pr.id=i.id_produto
        WHERE i.id_pedido=%s ORDER BY i.id_produto''',(pid,))
    lines=[f"{i['quantidade']}x {i['nome']} - R$ {i['subtotal_centavos']/100:.2f}"
           for i in cur.fetchall()]
    msg=(f"Olá! Gostaria de confirmar minha solicitação VôLanchar nº {pid}:\n"+
         '\n'.join(lines)+f"\nTotal: R$ {order['valor_centavos']/100:.2f}\n"+
         f"Retirada: {order['ponto'] or 'combinar com vendedor'}\nPodemos confirmar?")
    return answer({'id_pedido':pid, 'whatsapp':order['whatsapp'], 'mensagem':msg})


# Imagens no banco compatível com MySQL/TiDB. O sistema de arquivos do Render Free
# não é persistente; antes de ativar, aplicar backend/migracao.sql.
def photo_url(kind,item_id,db=None):
    own_connection=db is None
    db=db or connection()
    try:
        cur=db.cursor()
        cur.execute('SELECT 1 FROM fotos WHERE tipo=%s AND id_item=%s LIMIT 1',
                    (kind,int(item_id)))
        return f'/api/fotos/{kind}/{int(item_id)}' if cur.fetchone() else None
    finally:
        if own_connection:db.close()

def save_photo(kind,item_id):
    data=request.get_json(silent=True) or {}
    try: image=base64.b64decode(data.get('imagem_base64',''),validate=True)
    except (binascii.Error,ValueError):return fail('Imagem inválida.')
    if not image or len(image)>1_500_000:
        return fail('A imagem deve ter no máximo 1,5 MB.',413)
    is_png=image.startswith(b'\x89PNG\r\n\x1a\n')
    is_jpeg=image.startswith(b'\xff\xd8\xff')
    if not (is_png or is_jpeg):return fail('Envie imagem JPG ou PNG.')
    mime='image/png' if is_png else 'image/jpeg'
    db=connection()
    try:
        cur=db.cursor()
        cur.execute('''INSERT INTO fotos (tipo,id_item,mime,conteudo)
            VALUES (%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE mime=VALUES(mime),conteudo=VALUES(conteudo)''',
            (kind,int(item_id),mime,image))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally: db.close()
    return answer({'ok':True,'foto_url':f'/api/fotos/{kind}/{int(item_id)}'})

@app.get('/api/fotos/<kind>/<int:item_id>')
def show_photo(kind,item_id):
    if kind not in ('perfil','produto'):abort(404)
    db=connection()
    try:
        cur=db.cursor(dictionary=True)
        cur.execute('SELECT mime,conteudo FROM fotos WHERE tipo=%s AND id_item=%s',
                    (kind,item_id))
        entry=cur.fetchone()
    finally:db.close()
    if not entry:abort(404)
    return send_file(BytesIO(bytes(entry['conteudo'])),mimetype=entry['mime'],max_age=120)

@app.get('/api/perfil')
@logged
def profile():
    u=g.user
    return answer({'usuario':{'id':u['id'],'nome':u['nome'],'email':u['email'],
       'telefone':u['telefone'],'foto_url':photo_url('perfil',u['id'],g.db)}})

@app.patch('/api/perfil')
@logged
def update_profile():
    d=request.get_json(silent=True) or {}
    nome=str(d.get('nome','')).strip()
    email=str(d.get('email','')).strip().lower()
    telefone=re.sub(r'\D','',str(d.get('telefone','')))
    passwd=str(d.get('senha_atual',''))
    if not 2<=len(nome)<=100:return fail('Informe seu nome completo.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>190:return fail('E-mail inválido.')
    if not re.fullmatch(r'55819[0-9]{8}',telefone):return fail('Celular inválido.')
    cur=g.db.cursor(dictionary=True)
    cur.execute('SELECT senha_salt,senha_hash FROM usuarios WHERE id=%s',(g.user['id'],))
    old=cur.fetchone()
    _,digest=hash_password(passwd,bytes.fromhex(old['senha_salt']))
    if not hmac.compare_digest(digest,old['senha_hash']):return fail('Senha atual incorreta.',401)
    cur.execute('SELECT id FROM usuarios WHERE telefone=%s AND id<>%s LIMIT 1',(telefone,g.user['id']))
    if cur.fetchone():return fail('Telefone já cadastrado.',409)
    try:
        cur.execute('UPDATE usuarios SET nome=%s,email=%s,telefone=%s WHERE id=%s',
            (nome,email,telefone,g.user['id']))
        g.db.commit()
    except mysql.connector.IntegrityError:
        g.db.rollback();return fail('E-mail ou telefone já cadastrado.',409)
    return answer({'usuario':{'id':g.user['id'],'nome':nome,'email':email,'telefone':telefone}})

@app.post('/api/perfil/foto')
@logged
def update_profile_photo():
    return save_photo('perfil',g.user['id'])

@app.post('/api/produtos/<int:pid>/foto')
@logged
def update_product_photo(pid):
    cur=g.db.cursor();cur.execute('SELECT id FROM produtos WHERE id=%s AND id_vendedor=%s',(pid,g.user['id']))
    if not cur.fetchone():return fail('Produto não encontrado.',404)
    return save_photo('produto',pid)

@app.delete('/api/perfil')
@logged
def delete_profile():
    d=request.get_json(silent=True) or {}
    passwd=str(d.get('senha_atual',''))
    uid=g.user['id'];db=g.db;cur=db.cursor(dictionary=True)
    cur.execute('SELECT senha_salt,senha_hash FROM usuarios WHERE id=%s',(uid,))
    u=cur.fetchone()
    _,digest=hash_password(passwd,bytes.fromhex(u['senha_salt']))
    if not hmac.compare_digest(digest,u['senha_hash']):return fail('Senha incorreta.',401)
    try:
        # As chaves estrangeiras dos pedidos exigem excluir primeiro os itens.
        cur.execute("""SELECT DISTINCT p.id FROM pedidos p WHERE
          p.id_comprador=%s OR p.id_vendedor=%s OR EXISTS
          (SELECT 1 FROM itens_pedido i JOIN produtos pr ON pr.id=i.id_produto
           WHERE i.id_pedido=p.id AND pr.id_vendedor=%s)""",(uid,uid,uid))
        order_ids=[r['id'] for r in cur.fetchall()]
        if order_ids:
            markers=','.join(['%s']*len(order_ids))
            cur.execute(f'DELETE FROM itens_pedido WHERE id_pedido IN ({markers})',tuple(order_ids))
            cur.execute(f'DELETE FROM pedidos WHERE id IN ({markers})',tuple(order_ids))
        cur.execute('SELECT id FROM produtos WHERE id_vendedor=%s',(uid,))
        product_ids=[row['id'] for row in cur.fetchall()]
        # Excluir fotos na mesma transação, evitando dados órfãos após remoção da conta.
        cur.execute('DELETE FROM fotos WHERE tipo=%s AND id_item=%s',('perfil',uid))
        if product_ids:
            placeholders=','.join(['%s']*len(product_ids))
            cur.execute('DELETE FROM fotos WHERE tipo=%s AND id_item IN ('+placeholders+')',
                        ('produto',*product_ids))
        cur.execute('DELETE FROM produtos WHERE id_vendedor=%s',(uid,))
        cur.execute('DELETE FROM usuarios WHERE id=%s',(uid,))
        db.commit()
    except Exception:
        db.rollback();raise
    return answer({'ok':True})

if __name__=='__main__':
    app.run(host=os.getenv('FLASK_HOST','0.0.0.0'),port=int(os.getenv('FLASK_PORT','5000')),debug=False)
