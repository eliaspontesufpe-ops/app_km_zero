#!/usr/bin/env python3
"""VôLanchar / 0KM — MVP local, construído somente com a biblioteca padrão."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("VOLANCHAR_DB", BASE_DIR / "volanchar.db"))
HOST = os.environ.get("VOLANCHAR_HOST", "127.0.0.1")
PORT = int(os.environ.get("VOLANCHAR_PORT", "8000"))
SESSION_TTL = 60 * 60 * 24 * 7
SESSIONS: dict[str, tuple[int, float]] = {}
SESSIONS_LOCK = threading.Lock()

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 salt TEXT NOT NULL,
 password_hash TEXT NOT NULL,
 mode TEXT NOT NULL DEFAULT 'buyer' CHECK(mode IN ('buyer','seller')),
 whatsapp TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS points (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE,
 description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS presence (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 point_id INTEGER REFERENCES points(id),
 selling INTEGER NOT NULL DEFAULT 0 CHECK(selling IN (0,1)),
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 name TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
 available INTEGER NOT NULL DEFAULT 1 CHECK(available IN (0,1)),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

INDEX_HTML = r'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#174c37"><title>VôLanchar · 0KM</title>
<style>
:root{--green:#174c37;--lime:#c9ed69;--paper:#f6f5ef;--ink:#17231d;--muted:#68736c;--white:#fff;--line:#e4e8df;--red:#a5342b;--shadow:0 10px 32px #123b2410}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}button,input,select,textarea{font:inherit}button{cursor:pointer}.top{position:sticky;top:0;z-index:4;background:var(--green);color:white;padding:14px max(18px,calc((100% - 1120px)/2));display:flex;align-items:center;justify-content:space-between;gap:12px}.brand{font-weight:850;font-size:1.1rem;letter-spacing:-.04em}.brand span{color:var(--lime)}.topright{display:flex;align-items:center;gap:10px}.top select,.top button{border:1px solid #ffffff55;border-radius:12px;background:#ffffff12;color:white;padding:9px 12px}.top select option{color:#17231d}.top button{font-weight:700}.wrap{max-width:1120px;margin:auto;padding:28px 18px 56px}.welcome{background:var(--green);color:white;border-radius:24px;padding:30px;display:flex;justify-content:space-between;align-items:center;gap:20px;box-shadow:var(--shadow)}.welcome h1{font-size:clamp(1.7rem,4vw,2.7rem);line-height:1.05;margin:6px 0 12px;letter-spacing:-.045em}.welcome p{max-width:560px;color:#d2e0d6;margin:0}.pill{display:inline-flex;align-items:center;gap:7px;background:#ffffff19;border-radius:99px;padding:7px 11px;font-size:.83rem;font-weight:700}.dot{width:9px;height:9px;border-radius:50%;background:var(--lime)}.layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:22px;margin-top:22px}.section{background:var(--white);border:1px solid var(--line);border-radius:20px;padding:22px;box-shadow:var(--shadow);margin-bottom:18px}.section h2{font-size:1.2rem;margin:0 0 5px;letter-spacing:-.025em}.sub{color:var(--muted);font-size:.92rem;margin:0 0 18px}.toolbar{display:flex;gap:10px;align-items:end;flex-wrap:wrap}.field{display:flex;flex-direction:column;gap:6px;min-width:0;flex:1}.field label{font-size:.85rem;font-weight:700}.field input,.field select,.field textarea{border:1px solid #d8ded6;border-radius:11px;padding:11px 12px;background:white;color:var(--ink);width:100%}.field textarea{min-height:72px;resize:vertical}.btn{border:0;border-radius:11px;padding:11px 15px;font-weight:750;background:var(--green);color:white}.btn:hover{filter:brightness(1.08)}.btn.lime{background:var(--lime);color:#173422}.btn.ghost{background:#edf2eb;color:var(--green)}.btn.danger{background:#f9e7e3;color:var(--red)}.btn.small{padding:7px 10px;font-size:.87rem}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:13px}.card{border:1px solid var(--line);border-radius:16px;padding:16px;background:#fff}.cardhead{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.card h3{margin:0 0 3px;font-size:1.05rem}.muted{color:var(--muted);font-size:.9rem}.status{display:inline-block;background:#eef8d7;color:#3b6416;border-radius:99px;padding:4px 9px;font-size:.76rem;font-weight:800;white-space:nowrap}.product{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 0;border-top:1px solid var(--line)}.product:first-of-type{margin-top:10px}.price{font-weight:800}.row{display:flex;align-items:center;justify-content:space-between;gap:10px}.cartline{padding:10px 0;border-bottom:1px solid var(--line)}.qty{display:flex;gap:8px;align-items:center}.qty button{width:28px;height:28px;border:0;border-radius:8px;background:#edf2eb;color:var(--green);font-weight:900}.cart-total{font-size:1.15rem;font-weight:850;padding:14px 0}.empty{padding:22px;border:1px dashed #cad4c8;border-radius:14px;color:var(--muted);text-align:center}.auth{max-width:480px;margin:42px auto}.tabs{display:flex;background:#eef2eb;border-radius:12px;padding:4px;margin-bottom:18px}.tabs button{width:50%;border:0;background:transparent;border-radius:9px;padding:9px;font-weight:750;color:var(--muted)}.tabs button.active{background:white;color:var(--green);box-shadow:0 1px 4px #0001}.formgrid{display:grid;gap:13px}.notice{display:none;border-radius:12px;padding:12px 14px;margin-bottom:16px}.notice.show{display:block}.notice.error{background:#fae8e5;color:#872920}.notice.ok{background:#eaf4de;color:#315b1d}.switch{display:flex;align-items:center;gap:10px;font-weight:750}.switch input{width:20px;height:20px;accent-color:var(--green)}.seller-tools{display:grid;grid-template-columns:1fr 1fr;gap:18px}.footer{text-align:center;color:var(--muted);font-size:.82rem;padding:12px}.hidden{display:none!important}.loading{color:var(--muted);padding:20px;text-align:center}
@media(max-width:780px){.layout{grid-template-columns:1fr}.seller-tools{grid-template-columns:1fr}.welcome{padding:23px;align-items:flex-start;flex-direction:column}.top{flex-wrap:wrap}.wrap{padding-top:18px}.section{padding:18px}}
</style></head><body><header class="top"><div class="brand">VôLanchar <span>· 0KM</span></div><div class="topright" id="userbar" hidden><span id="who"></span><select id="mode" aria-label="Modo de uso"><option value="buyer">Modo comprador</option><option value="seller">Modo vendedor</option></select><button id="logout">Sair</button></div></header>
<main class="wrap"><div id="notice" class="notice"></div><section id="auth" class="auth section"><div class="pill" style="background:#edf5e3;color:#315b1d"><span class="dot"></span> Conexão local, no campus</div><h1 style="margin:12px 0 6px">O que vai ser hoje?</h1><p class="sub">Encontre quem está vendendo por perto ou publique seus produtos no campus.</p><div class="tabs"><button id="tabLogin" class="active">Entrar</button><button id="tabRegister">Criar conta</button></div><form id="authform" class="formgrid"><div class="field hidden" id="namewrap"><label for="name">Seu nome</label><input id="name" autocomplete="name" maxlength="80"></div><div class="field"><label for="email">E-mail</label><input id="email" type="email" autocomplete="email" required maxlength="254"></div><div class="field"><label for="password">Senha</label><input id="password" type="password" autocomplete="current-password" required minlength="8"></div><button class="btn" id="authsubmit">Entrar</button><p class="muted" style="margin:0">A senha é protegida e os dados ficam salvos neste aplicativo.</p></form></section>
<div id="app" class="hidden"><section class="welcome"><div><span class="pill"><span class="dot"></span><span id="heroMode">COMPRADOR</span></span><h1 id="heroTitle">Tem alguém vendendo por perto.</h1><p id="heroText">Escolha um ponto do campus, encontre opções disponíveis e combine o pedido direto com o vendedor.</p></div><button class="btn lime" id="jumpAction">Explorar vendedores</button></section>
<div class="layout"><div><section id="discover" class="section"><h2>Explore o campus</h2><p class="sub">Escolha um ponto para encontrar vendedores disponíveis agora.</p><div class="toolbar"><div class="field"><label for="pointFilter">Ponto ou bloco</label><select id="pointFilter"></select></div><button class="btn ghost" id="refresh">Atualizar</button></div><div id="sellers" class="cards" style="margin-top:17px"><div class="loading">Carregando ofertas…</div></div></section>
<section id="sellerPanel" class="section hidden"><h2>Seu ponto de venda</h2><p class="sub">Defina onde está e atualize sua presença para compradores.</p><div class="seller-tools"><div class="formgrid"><div class="field"><label for="sellerPoint">Ponto ou bloco</label><select id="sellerPoint"></select></div><div class="field"><label for="whatsapp">WhatsApp com código do país</label><input id="whatsapp" type="tel" placeholder="5511999999999" maxlength="20"><span class="muted">Somente números, incluindo DDI. Ex.: 55 + DDD + número.</span></div><label class="switch"><input id="selling" type="checkbox"> Vendendo agora</label><button id="savePresence" class="btn">Salvar presença</button></div><div><h3 style="margin:0 0 8px">Adicionar produto</h3><form id="productForm" class="formgrid"><div class="field"><label for="pname">Nome</label><input id="pname" maxlength="100" required></div><div class="field"><label for="pdesc">Descrição (opcional)</label><input id="pdesc" maxlength="240"></div><div class="field"><label for="pprice">Preço (R$)</label><input id="pprice" type="number" min="0" step="0.01" required></div><button class="btn lime">Adicionar produto</button></form></div></div><h3 style="margin:22px 0 4px">Seu cardápio</h3><div id="myProducts"></div></section>
</div><aside><section class="section"><h2>Seu pedido</h2><p class="sub" id="cartHint">Adicione produtos de um vendedor para começar.</p><div id="cart"><div class="empty">Seu carrinho está vazio.</div></div><button class="btn" id="checkout" style="width:100%;background:#168447" disabled>Finalizar pelo WhatsApp</button><p class="muted" style="font-size:.8rem;margin:10px 0 0">O pedido será enviado como mensagem; pagamento e entrega são combinados diretamente.</p></section><section class="section"><h2>Como funciona</h2><p class="muted" style="margin-bottom:0">O vendedor ativa “Vendendo agora” e informa seu ponto. Você escolhe os produtos, confere o total estimado e envia o pedido pelo WhatsApp.</p></section></aside></div></div><footer class="footer">MVP VôLanchar / 0KM · presença e catálogo em tempo real no campus</footer></main>
<script>
const $=s=>document.querySelector(s);let user=null,points=[],sellerCache=[],cart={seller:null,items:[]},register=false;
function toast(msg,type='ok'){const n=$('#notice');n.textContent=msg;n.className='notice show '+type;setTimeout(()=>n.classList.remove('show'),4000)}
async function api(url,opts={}){const r=await fetch(url,{...opts,headers:{'Content-Type':'application/json',...(opts.headers||{})}});let d={};try{d=await r.json()}catch{}if(!r.ok)throw Error(d.error||'Ocorreu um erro.');return d}
const money=c=>(c/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
function showApp(){ $('#auth').classList.add('hidden');$('#app').classList.remove('hidden');$('#userbar').hidden=false;$('#who').textContent=user.name;$('#mode').value=user.mode;$('#sellerPanel').classList.toggle('hidden',user.mode!=='seller');$('#heroMode').textContent=user.mode==='seller'?'VENDEDOR':'COMPRADOR';$('#heroTitle').textContent=user.mode==='seller'?'Sua oferta, no mapa do campus.':'Tem alguém vendendo por perto.';$('#heroText').textContent=user.mode==='seller'?'Escolha seu ponto, publique o cardápio e ative sua presença quando estiver vendendo.':'Escolha um ponto do campus, encontre opções disponíveis e combine o pedido direto com o vendedor.';$('#jumpAction').textContent=user.mode==='seller'?'Gerenciar minha oferta':'Explorar vendedores';loadAll()}
function showAuth(){user=null;$('#auth').classList.remove('hidden');$('#app').classList.add('hidden');$('#userbar').hidden=true}
function updateAuthForm(){register=$('#tabRegister').classList.contains('active');$('#namewrap').classList.toggle('hidden',!register);$('#name').required=register;$('#password').autocomplete=register?'new-password':'current-password';$('#authsubmit').textContent=register?'Criar conta':'Entrar'}
$('#tabLogin').onclick=()=>{$('#tabLogin').classList.add('active');$('#tabRegister').classList.remove('active');updateAuthForm()};$('#tabRegister').onclick=()=>{$('#tabRegister').classList.add('active');$('#tabLogin').classList.remove('active');updateAuthForm()};
$('#authform').onsubmit=async e=>{e.preventDefault();try{const body={email:$('#email').value.trim(),password:$('#password').value};if(register)body.name=$('#name').value.trim();const d=await api(register?'/api/register':'/api/login',{method:'POST',body:JSON.stringify(body)});user=d.user;toast(register?'Conta criada. Bem-vindo!':'Login realizado.');showApp()}catch(e){toast(e.message,'error')}};
$('#logout').onclick=async()=>{await api('/api/logout',{method:'POST',body:'{}'});cart={seller:null,items:[]};showAuth()};
$('#mode').onchange=async()=>{try{const d=await api('/api/mode',{method:'POST',body:JSON.stringify({mode:$('#mode').value})});user=d.user;cart={seller:null,items:[]};showApp();toast('Modo atualizado.')}catch(e){toast(e.message,'error')}};
$('#jumpAction').onclick=()=>document.getElementById(user.mode==='seller'?'sellerPanel':'discover').scrollIntoView({behavior:'smooth'});
async function loadPoints(){const d=await api('/api/points');points=d.points;for(const id of ['pointFilter','sellerPoint']){const s=$('#'+id),old=s.value;s.innerHTML='<option value="">Todos os pontos</option>'+points.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');if(id==='sellerPoint')s.innerHTML='<option value="">Selecione um ponto</option>'+points.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');if([...s.options].some(o=>o.value===old))s.value=old}}
function esc(x){return String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function loadAll(){try{await loadPoints();await Promise.all([loadSellers(),user.mode==='seller'?loadMyProfile():Promise.resolve()])}catch(e){toast(e.message,'error')}}
$('#pointFilter').onchange=loadSellers;$('#refresh').onclick=loadSellers;
async function loadSellers(){const box=$('#sellers');box.innerHTML='<div class="loading">Buscando vendedores…</div>';try{const d=await api('/api/sellers'+($('#pointFilter').value?'?point='+encodeURIComponent($('#pointFilter').value):''));sellerCache=d.sellers;if(!d.sellers.length){box.innerHTML='<div class="empty" style="grid-column:1/-1">Nenhum vendedor disponível neste ponto agora. Tente outro local ou volte mais tarde.</div>';return}box.innerHTML=d.sellers.map(s=>`<article class="card"><div class="cardhead"><div><h3>${esc(s.name)}</h3><div class="muted">📍 ${esc(s.point_name)}</div></div><span class="status">Vendendo agora</span></div>${s.products.map(p=>`<div class="product"><div><div><b>${esc(p.name)}</b></div>${p.description?`<div class="muted">${esc(p.description)}</div>`:''}<div class="price">${money(p.price_cents)}</div></div><button class="btn small" onclick="addItem(${s.id},${p.id})">Adicionar</button></div>`).join('')||'<p class="muted">Sem produtos disponíveis no momento.</p>'}</article>`).join('')}catch(e){box.innerHTML='<div class="empty">Não foi possível carregar vendedores.</div>';toast(e.message,'error')}}
window.addItem=(sid,pid)=>{const seller=sellerCache.find(s=>s.id===sid),product=seller?.products.find(p=>p.id===pid);if(!seller||!product)return;if(cart.seller&&cart.seller.id!==sid){if(!confirm('Seu carrinho já tem itens de outro vendedor. Limpar e começar um novo pedido?'))return;cart.items=[]}cart.seller={id:sid,name:seller.name,point:seller.point_name};const it=cart.items.find(x=>x.id===pid);if(it)it.qty++;else cart.items.push({id:product.id,name:product.name,price:product.price_cents,qty:1});renderCart()};
function renderCart(){const c=$('#cart');$('#cartHint').textContent=cart.seller?`Pedido para ${cart.seller.name} · ${cart.seller.point}`:'Adicione produtos de um vendedor para começar.';if(!cart.items.length){c.innerHTML='<div class="empty">Seu carrinho está vazio.</div>';$('#checkout').disabled=true;return}c.innerHTML=cart.items.map(x=>`<div class="cartline"><div class="row"><b>${esc(x.name)}</b><span class="price">${money(x.price*x.qty)}</span></div><div class="row" style="margin-top:7px"><span class="muted">${money(x.price)} cada</span><div class="qty"><button onclick="qty(${x.id},-1)">−</button><b>${x.qty}</b><button onclick="qty(${x.id},1)">+</button></div></div></div>`).join('')+`<div class="row cart-total"><span>Total estimado</span><span>${money(cart.items.reduce((a,x)=>a+x.price*x.qty,0))}</span></div>`;$('#checkout').disabled=false}
window.qty=(id,delta)=>{const x=cart.items.find(y=>y.id===id);if(x){x.qty+=delta;if(x.qty<=0)cart.items=cart.items.filter(y=>y.id!==id);if(!cart.items.length)cart.seller=null;renderCart()}};
$('#checkout').onclick=async()=>{if(!cart.seller||!cart.items.length)return;try{const d=await api('/api/seller/'+cart.seller.id);const seller=d.seller;if(!seller.whatsapp)throw Error('Este vendedor ainda não cadastrou o WhatsApp.');for(const item of cart.items){const live=seller.products.find(p=>p.id===item.id);if(!live)throw Error(`“${item.name}” não está mais disponível. Atualize o catálogo e revise o pedido.`);item.price=live.price_cents;item.name=live.name}const total=cart.items.reduce((a,x)=>a+x.price*x.qty,0);const lines=cart.items.map(x=>`- ${x.qty}x ${x.name} — ${money(x.price*x.qty)}`);const text=`Olá! Quero fazer este pedido pelo VôLanchar/0KM:\n${lines.join('\n')}\nTotal estimado: ${money(total)}\nPonto/bloco de referência: ${seller.point_name}`;window.open(`https://wa.me/${seller.whatsapp}?text=${encodeURIComponent(text)}`,'_blank','noopener');}catch(e){toast(e.message,'error')}};
async function loadMyProfile(){try{const d=await api('/api/my-profile');$('#sellerPoint').value=d.presence.point_id||'';$('#selling').checked=!!d.presence.selling;$('#whatsapp').value=d.whatsapp||'';$('#myProducts').innerHTML=d.products.length?d.products.map(p=>`<div class="product"><div><b>${esc(p.name)}</b><div class="muted">${money(p.price_cents)} · ${p.available?'Disponível':'Pausado'}</div></div><div style="display:flex;gap:7px"><button class="btn ghost small" onclick="toggleProduct(${p.id},${p.available?0:1})">${p.available?'Pausar':'Reativar'}</button><button class="btn danger small" onclick="deleteProduct(${p.id})">Excluir</button></div></div>`).join(''):'<div class="empty">Você ainda não cadastrou produtos.</div>'}catch(e){toast(e.message,'error')}}
$('#savePresence').onclick=async()=>{try{const d=await api('/api/presence',{method:'POST',body:JSON.stringify({point_id:$('#sellerPoint').value||null,selling:$('#selling').checked,whatsapp:$('#whatsapp').value.trim()})});toast(d.message);await Promise.all([loadMyProfile(),loadSellers()])}catch(e){toast(e.message,'error')}};
$('#productForm').onsubmit=async e=>{e.preventDefault();try{const price=Math.round(Number($('#pprice').value)*100);await api('/api/products',{method:'POST',body:JSON.stringify({name:$('#pname').value.trim(),description:$('#pdesc').value.trim(),price_cents:price})});e.target.reset();toast('Produto adicionado.');await Promise.all([loadMyProfile(),loadSellers()])}catch(e){toast(e.message,'error')}};
window.toggleProduct=async(id,available)=>{try{await api('/api/products/'+id,{method:'PATCH',body:JSON.stringify({available:!!available})});await Promise.all([loadMyProfile(),loadSellers()]);toast('Disponibilidade atualizada.')}catch(e){toast(e.message,'error')}};
window.deleteProduct=async id=>{if(!confirm('Excluir este produto?'))return;try{await api('/api/products/'+id,{method:'DELETE',body:'{}'});await Promise.all([loadMyProfile(),loadSellers()]);toast('Produto excluído.')}catch(e){toast(e.message,'error')}};
(async()=>{try{const d=await api('/api/me');user=d.user;showApp()}catch{showAuth()}})();
</script></body></html>'''


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript(SCHEMA)
        if db.execute("SELECT COUNT(*) FROM points").fetchone()[0] == 0:
            # Pontos demonstrativos: substitua pelos pontos oficiais do campus.
            db.executemany("INSERT INTO points(name,description) VALUES(?,?)", [
                ("Entrada principal", "Ponto de referência demonstrativo"),
                ("Biblioteca", "Ponto de referência demonstrativo"),
                ("Centro de convivência", "Ponto de referência demonstrativo"),
                ("Bloco de aulas", "Ponto de referência demonstrativo"),
                ("Restaurante universitário", "Ponto de referência demonstrativo"),
            ])


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return salt.hex(), digest.hex()


def valid_email(email: str) -> bool:
    return len(email) <= 254 and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) is not None


def money_cents(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("Preço inválido.")
    try:
        val = float(value)
    except (TypeError, ValueError):
        raise ValueError("Informe um preço válido em centavos.")
    if not val.is_integer() or val < 0 or val > 100_000_000:
        raise ValueError("O preço deve estar entre R$ 0,00 e R$ 1.000.000,00.")
    return int(val)


class AppHandler(BaseHTTPRequestHandler):
    server_version = "VoLancharMVP/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        if os.environ.get("VOLANCHAR_LOG", "1") == "1":
            super().log_message(fmt, *args)

    def send_json(self, code: int, data: dict, extra_headers: dict[str, str] | None = None) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
        if extra_headers:
            for k, v in extra_headers.items(): self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 50_000: raise ValueError("Requisição muito grande.")
        if not length: return {}
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict): raise ValueError("Formato de requisição inválido.")
        return data

    def current_user(self) -> sqlite3.Row | None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get("vl_session")
        if not morsel: return None
        token = morsel.value
        with SESSIONS_LOCK:
            entry = SESSIONS.get(token)
            if not entry: return None
            uid, expiry = entry
            if expiry < time.time():
                SESSIONS.pop(token, None)
                return None
        with connect() as db:
            return db.execute("SELECT id,name,email,mode,whatsapp FROM users WHERE id=?", (uid,)).fetchone()

    def require_user(self) -> sqlite3.Row:
        user = self.current_user()
        if not user: raise PermissionError("Entre na sua conta para continuar.")
        return user

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/":
                raw = INDEX_HTML.encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.send_header("X-Content-Type-Options", "nosniff"); self.send_header("Referrer-Policy", "strict-origin-when-cross-origin"); self.end_headers(); self.wfile.write(raw); return
            if path == "/api/me":
                user = self.current_user()
                if not user: self.send_json(401, {"error":"Sessão não autenticada."}); return
                self.send_json(200, {"user":dict(user)}); return
            if path == "/api/points":
                with connect() as db: points = [dict(x) for x in db.execute("SELECT id,name,description FROM points ORDER BY name")]
                self.send_json(200, {"points":points}); return
            if path == "/api/sellers":
                q = parse_qs(parsed.query); point = q.get("point", [""])[0]
                with connect() as db:
                    sql = "SELECT u.id,u.name,p.name AS point_name FROM users u JOIN presence pr ON pr.user_id=u.id JOIN points p ON p.id=pr.point_id WHERE pr.selling=1"
                    params: list[object] = []
                    if point:
                        if not point.isdigit(): self.send_json(400,{"error":"Ponto inválido."}); return
                        sql += " AND p.id=?"; params.append(int(point))
                    sql += " ORDER BY p.name,u.name"
                    sellers=[]
                    for row in db.execute(sql,params):
                        products=[dict(x) for x in db.execute("SELECT id,name,description,price_cents,available FROM products WHERE seller_id=? AND available=1 ORDER BY name",(row["id"],))]
                        sellers.append({**dict(row),"products":products})
                self.send_json(200,{"sellers":sellers}); return
            match = re.fullmatch(r"/api/seller/(\d+)", path)
            if match:
                with connect() as db:
                    row=db.execute("SELECT u.id,u.name,u.whatsapp,pr.selling,pr.point_id,p.name AS point_name FROM users u JOIN presence pr ON pr.user_id=u.id JOIN points p ON p.id=pr.point_id WHERE u.id=?",(int(match.group(1)),)).fetchone()
                    if not row or not row["selling"]: self.send_json(404,{"error":"Vendedor não está disponível."}); return
                    products=[dict(x) for x in db.execute("SELECT id,name,price_cents FROM products WHERE seller_id=? AND available=1 ORDER BY id",(int(match.group(1)),))]
                self.send_json(200,{"seller":{**dict(row),"products":products}}); return
            if path == "/api/my-profile":
                user=self.require_user()
                if user["mode"]!="seller": self.send_json(403,{"error":"Ative o modo vendedor."}); return
                with connect() as db:
                    presence=db.execute("SELECT point_id,selling FROM presence WHERE user_id=?",(user["id"],)).fetchone()
                    products=[dict(x) for x in db.execute("SELECT id,name,description,price_cents,available FROM products WHERE seller_id=? ORDER BY name",(user["id"],))]
                self.send_json(200,{"presence":dict(presence) if presence else {"point_id":None,"selling":0},"products":products,"whatsapp":user["whatsapp"]}); return
            self.send_json(404,{"error":"Página não encontrada."})
        except PermissionError as e: self.send_json(401,{"error":str(e)})
        except Exception as e:
            print("GET error:",repr(e)); self.send_json(500,{"error":"Não foi possível concluir a solicitação."})

    def do_POST(self) -> None:
        path=urlparse(self.path).path
        try:
            data=self.read_json()
            if path == "/api/register":
                name=str(data.get("name","")).strip(); email=str(data.get("email","")).strip().lower(); password=str(data.get("password",""))
                if not name or len(name)>80: self.send_json(400,{"error":"Informe um nome com até 80 caracteres."}); return
                if not valid_email(email): self.send_json(400,{"error":"Informe um e-mail válido."}); return
                if len(password)<8 or len(password)>256: self.send_json(400,{"error":"A senha deve ter pelo menos 8 caracteres."}); return
                salt,digest=hash_password(password)
                try:
                    with connect() as db:
                        cur=db.execute("INSERT INTO users(name,email,salt,password_hash) VALUES(?,?,?,?)",(name,email,salt,digest)); uid=cur.lastrowid
                        db.execute("INSERT INTO presence(user_id) VALUES(?)",(uid,))
                except sqlite3.IntegrityError:
                    self.send_json(409,{"error":"Este e-mail já está cadastrado."}); return
                self.create_session(uid); return
            if path == "/api/login":
                email=str(data.get("email","")).strip().lower(); password=str(data.get("password",""))
                with connect() as db: row=db.execute("SELECT id,salt,password_hash FROM users WHERE email=?",(email,)).fetchone()
                if not row:
                    # Mantém custo semelhante para e-mails inexistentes.
                    hash_password(password, b"\x00"*16); self.send_json(401,{"error":"E-mail ou senha incorretos."}); return
                _,digest=hash_password(password,bytes.fromhex(row["salt"]))
                if not hmac.compare_digest(digest,row["password_hash"]): self.send_json(401,{"error":"E-mail ou senha incorretos."}); return
                self.create_session(row["id"]); return
            if path == "/api/logout":
                cookie=SimpleCookie(self.headers.get("Cookie",""));m=cookie.get("vl_session")
                if m:
                    with SESSIONS_LOCK: SESSIONS.pop(m.value,None)
                self.send_json(200,{"ok":True},{"Set-Cookie":"vl_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"}); return
            if path == "/api/mode":
                user=self.require_user(); mode=data.get("mode")
                if mode not in ("buyer","seller"): self.send_json(400,{"error":"Modo inválido."}); return
                with connect() as db: db.execute("UPDATE users SET mode=? WHERE id=?",(mode,user["id"]))
                self.send_json(200,{"user":{**dict(user),"mode":mode}}); return
            if path == "/api/presence":
                user=self.require_user()
                if user["mode"]!="seller": self.send_json(403,{"error":"Alterne para o modo vendedor."}); return
                point=data.get("point_id");selling=bool(data.get("selling"));phone=re.sub(r"\D","",str(data.get("whatsapp","")))
                if len(phone) not in range(10,16): self.send_json(400,{"error":"Informe o WhatsApp completo com código do país, entre 10 e 15 dígitos."}); return
                if not point: self.send_json(400,{"error":"Selecione o ponto de venda."}); return
                try: point=int(point)
                except (ValueError,TypeError): self.send_json(400,{"error":"Ponto inválido."}); return
                with connect() as db:
                    if not db.execute("SELECT 1 FROM points WHERE id=?",(point,)).fetchone(): self.send_json(400,{"error":"Ponto de venda não encontrado."}); return
                    db.execute("UPDATE users SET whatsapp=? WHERE id=?",(phone,user["id"]))
                    db.execute("INSERT INTO presence(user_id,point_id,selling,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET point_id=excluded.point_id,selling=excluded.selling,updated_at=CURRENT_TIMESTAMP",(user["id"],point,int(selling)))
                self.send_json(200,{"ok":True,"message":"Presença salva." if selling else "Ponto salvo. Você não aparece como disponível."}); return
            if path == "/api/products":
                user=self.require_user()
                if user["mode"]!="seller": self.send_json(403,{"error":"Alterne para o modo vendedor."}); return
                name=str(data.get("name","")).strip();description=str(data.get("description","")).strip()
                if not name or len(name)>100 or len(description)>240: self.send_json(400,{"error":"Informe um nome (até 100 caracteres) e descrição (até 240 caracteres)."}); return
                try: price=money_cents(data.get("price_cents"))
                except ValueError as e: self.send_json(400,{"error":str(e)}); return
                with connect() as db: cur=db.execute("INSERT INTO products(seller_id,name,description,price_cents) VALUES(?,?,?,?)",(user["id"],name,description,price))
                self.send_json(201,{"id":cur.lastrowid}); return
            self.send_json(404,{"error":"Rota não encontrada."})
        except PermissionError as e: self.send_json(401,{"error":str(e)})
        except (ValueError,json.JSONDecodeError) as e: self.send_json(400,{"error":str(e) or "Dados inválidos."})
        except Exception as e: print("POST error:",repr(e)); self.send_json(500,{"error":"Não foi possível concluir a solicitação."})

    def do_PATCH(self) -> None:
        self.change_product(delete=False)

    def do_DELETE(self) -> None:
        self.change_product(delete=True)

    def change_product(self, delete: bool) -> None:
        match=re.fullmatch(r"/api/products/(\d+)",urlparse(self.path).path)
        if not match: self.send_json(404,{"error":"Produto não encontrado."}); return
        try:
            user=self.require_user()
            if user["mode"]!="seller": self.send_json(403,{"error":"Alterne para o modo vendedor."}); return
            data=self.read_json()
            with connect() as db:
                row=db.execute("SELECT id FROM products WHERE id=? AND seller_id=?",(int(match.group(1)),user["id"])).fetchone()
                if not row: self.send_json(404,{"error":"Produto não encontrado na sua conta."}); return
                if delete: db.execute("DELETE FROM products WHERE id=?",(row["id"],))
                elif "available" in data: db.execute("UPDATE products SET available=? WHERE id=?",(int(bool(data["available"])),row["id"]))
                else: self.send_json(400,{"error":"Nenhuma alteração informada."}); return
            self.send_json(200,{"ok":True})
        except PermissionError as e: self.send_json(401,{"error":str(e)})
        except ValueError as e: self.send_json(400,{"error":str(e)})
        except Exception as e: print("Product error:",repr(e)); self.send_json(500,{"error":"Não foi possível atualizar o produto."})

    def create_session(self, uid: int) -> None:
        token=secrets.token_urlsafe(32)
        with SESSIONS_LOCK:
            now=time.time()
            for key,(_,expiry) in list(SESSIONS.items()):
                if expiry<now: SESSIONS.pop(key,None)
            SESSIONS[token]=(uid,now+SESSION_TTL)
        with connect() as db: user=dict(db.execute("SELECT id,name,email,mode,whatsapp FROM users WHERE id=?",(uid,)).fetchone())
        self.send_json(200,{"user":user},{"Set-Cookie":f"vl_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={SESSION_TTL}"})


def main() -> None:
    init_db()
    server=ThreadingHTTPServer((HOST,PORT),AppHandler)
    print(f"VôLanchar está disponível em http://{HOST}:{PORT}")
    print(f"Banco de dados: {DB_PATH}")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nAplicativo encerrado.")
    finally: server.server_close()

if __name__ == "__main__": main()
