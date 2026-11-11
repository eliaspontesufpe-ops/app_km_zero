# VôLanchar

**O lanche pertim. O bucho chein.**

O **VôLanchar** é um aplicativo Android que aproxima quem vende e quem procura lanches no ambiente universitário. A plataforma facilita a divulgação de produtos, a localização de vendedores nos pontos de venda e a organização dos pedidos, com contato direto pelo WhatsApp.

Desenvolvido como projeto acadêmico por estudantes da **Universidade Federal Rural de Pernambuco (UFRPE)**, o aplicativo busca tornar mais simples a conexão entre vendedores e a comunidade universitária.

## Funcionalidades

### Para quem compra

- Criar uma conta e entrar com e-mail ou telefone e senha.
- Encontrar vendedores e consultar os pontos de venda cadastrados.
- Visualizar produtos, descrições e preços.
- Adicionar itens ao carrinho e consultar o valor total.
- Encaminhar o pedido ao vendedor pelo WhatsApp.

### Para quem vende

- Alternar para o perfil de vendedor.
- Informar o ponto de venda e o contato de WhatsApp.
- Indicar a disponibilidade com a opção **“Vendendo agora”**.
- Cadastrar produtos com nome, descrição, preço e foto opcional.
- Editar, pausar, reativar ou excluir produtos do cardápio.

### Gerenciamento de conta

- Atualizar informações do perfil.
- Solicitar recuperação de acesso por e-mail.

## Como funciona

1. **Encontre:** consulte os pontos de venda e os vendedores disponíveis.
2. **Escolha:** veja o cardápio e adicione produtos ao carrinho.
3. **Peça:** confira o pedido e encaminhe os detalhes ao vendedor pelo WhatsApp.

O VôLanchar **não realiza pagamentos dentro do aplicativo**. A combinação de pagamento e retirada é feita diretamente entre comprador e vendedor.

## Instalação

O VôLanchar está em desenvolvimento e dispõe de uma versão de testes para **Android (ARM64)**.

Para instalar o aplicativo:

1. Baixe o APK disponibilizado na área de [Releases deste repositório](https://github.com/eliaspontesufpe-ops/app_km_zero/releases), quando houver uma versão publicada.
2. Abra o arquivo no dispositivo Android.
3. Caso o Android solicite, permita a instalação de aplicativos dessa origem.
4. Abra o VôLanchar e conecte-se à internet para utilizar os recursos disponíveis.

> **Observação:** trata-se de uma versão de testes. Algumas funcionalidades podem apresentar limitações ou mudanças durante o desenvolvimento.

## Tecnologias utilizadas

| Componente | Tecnologia |
| --- | --- |
| Aplicativo Android | Python e Kivy |
| Compilação Android | Buildozer e python-for-android |
| API | Python e Flask |
| Hospedagem da API | Render |
| Banco de dados | TiDB Cloud (compatível com MySQL) |
| Comunicação | HTTPS |
| Contato para pedidos | WhatsApp |

O aplicativo se comunica pela internet com uma API Flask, responsável pelo processamento das operações e pelo acesso aos dados armazenados na nuvem.

## Estrutura do projeto

```text
app_km_zero/
├── app/                 # Código do aplicativo Android
├── backend/             # API e dependências do servidor
├── docs/                # Requisitos e documentação de testes
├── README.md            # Apresentação e instruções
├── LICENSE              # Licença do projeto
└── .gitignore           # Arquivos excluídos do versionamento
```

A estrutura e os arquivos disponíveis podem evoluir conforme o desenvolvimento.

## Documentação

A pasta [`docs/`](docs/) reúne os documentos técnicos do projeto, incluindo a especificação de requisitos e o plano de teste.

## Estado de desenvolvimento

O VôLanchar encontra-se em fase de **MVP (produto mínimo viável)**, na versão **0.5.0**. O aplicativo já contempla o fluxo principal de consulta a vendedores, escolha de produtos e encaminhamento de pedidos.

O acesso com Google ainda está em validação. A disponibilidade e o tempo de resposta do serviço podem variar, especialmente após períodos de inatividade da hospedagem.

## Desenvolvedores

Projeto desenvolvido por:

- Alceu Domingues Alves
- Elias Pontes Junior
- Jeniffer Cavalcanti de Oliveira
- Sérgio Ricardo Ferreira da Silva Filho
- Wilber Antonio Santos da Silva

**Universidade Federal Rural de Pernambuco (UFRPE)**

## Licença

O código está disponibilizado conforme os termos do arquivo [LICENSE](LICENSE). Consulte esse documento para conhecer as condições de uso, distribuição e atribuição de autoria.
