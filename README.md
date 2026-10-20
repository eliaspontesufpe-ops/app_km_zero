# VôLanchar / 0KM — MVP em Python

Aplicativo web responsivo para conectar compradores e vendedores no mesmo campus. Feito em Python, com servidor HTTP e banco SQLite da biblioteca padrão: não exige frameworks nem serviços externos para executar localmente.

## Requisitos

- Python 3.10 ou superior.
- Navegador moderno.
- Nenhuma dependência externa (o `requirements.txt` existe para facilitar automações de repositórios Python).

## Executar localmente

```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd volanchar_0km
python app.py
```

Abra `http://127.0.0.1:8000`. O banco `volanchar.db` é criado na primeira execução e não deve ser enviado ao GitHub.

Para configurar host, porta ou banco, use `VOLANCHAR_HOST`, `VOLANCHAR_PORT` e `VOLANCHAR_DB`.

Linux/macOS:

```bash
VOLANCHAR_PORT=8080 python app.py
```

Windows PowerShell:

```powershell
$env:VOLANCHAR_PORT="8080"
python app.py
```

## Testes

```bash
python -m unittest -v
```

Os testes usam um banco temporário e cobrem cadastro/login, alternância de perfil, presença, produtos e visibilidade das ofertas.

## Publicar no GitHub

1. Crie um repositório vazio no GitHub.
2. Extraia o pacote baixado e abra o terminal dentro da pasta do projeto.
3. Execute:

```bash
git init
git add .
git commit -m "Adiciona MVP VôLanchar 0KM"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

Substitua `SEU_USUARIO/SEU_REPOSITORIO` pela identificação do repositório criado. Não inclua `volanchar.db`, credenciais ou dados pessoais.

## Funcionalidades incluídas

- Cadastro e login por e-mail/senha, com senha derivada via PBKDF2-HMAC-SHA256 e salt aleatório.
- Alternância entre comprador e vendedor.
- Seleção de pontos/blocos do campus.
- Perfil do vendedor com ponto, WhatsApp e estado “Vendendo agora”.
- Cadastro, pausa, reativação e exclusão de produtos.
- Descoberta de vendedores ativos e catálogo por ponto.
- Carrinho de um vendedor por vez e encaminhamento do pedido pelo WhatsApp.
- Interface responsiva em português.

## Limites e segurança

Os pontos iniciais (“Entrada principal”, “Biblioteca”, “Centro de convivência”, “Bloco de aulas” e “Restaurante universitário”) são demonstrativos; substitua pela lista oficial do campus antes de implantar. Não há mapa/GPS, pagamento, entrega, avaliações, histórico, favoritos, chat interno nem login Google.

As sessões ficam em memória e terminam quando o servidor reinicia; os cadastros e produtos permanecem no SQLite. Este servidor é destinado a MVP e demonstração local, não à exposição pública sem endurecimento. Antes de implantação pública, configure HTTPS, política de privacidade/LGPD, backup, gestão de segredos, limitação de requisições, recuperação de conta e autenticação persistente/gerenciada.

## Licença

Licenciado sob MIT. Consulte `LICENSE`.
