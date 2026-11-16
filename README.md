# VôLanchar

**O lanche pertim. O bucho chein.**

O **VôLanchar** é um aplicativo Android desenvolvido para aproximar vendedores de lanches e a comunidade universitária da Universidade Federal Rural de Pernambuco (UFRPE), campus Recife.

A plataforma facilita a divulgação de produtos, a localização de pontos fixos de venda, a consulta de cardápios e a organização de pedidos, permitindo que compradores e vendedores se comuniquem diretamente pelo WhatsApp.

Desenvolvido como projeto acadêmico por estudantes do curso de **Licenciatura em Computação da UFRPE**, na disciplina de Engenharia de Software, o aplicativo busca oferecer uma solução simples, acessível e prática para a comercialização de lanches no ambiente universitário.

## 1. Funcionalidades

### 1.1. Para quem compra

- Criar uma conta com nome, e-mail, telefone e senha.
- Entrar utilizando e-mail ou telefone e senha.
- Recuperar o acesso por meio de código enviado ao e-mail cadastrado.
- Alternar entre os perfis de comprador e vendedor na mesma conta.
- Consultar o mapa interativo do campus Recife da UFRPE.
- Visualizar os nove pontos fixos de venda disponíveis no aplicativo.
- Consultar vendedores, estabelecimentos e produtos cadastrados.
- Pesquisar e visualizar ofertas, descrições, preços e fotografias dos produtos.
- Adicionar produtos ao carrinho e alterar quantidades.
- Consultar o valor total antes de finalizar uma solicitação.
- Registrar pedidos e consultar seus detalhes e histórico.
- Encaminhar os pedidos diretamente ao vendedor pelo WhatsApp.
- Acessar e atualizar informações do perfil.

### 1.2. Para quem vende

- Utilizar a mesma conta para acessar o perfil de vendedor.
- Cadastrar e atualizar o nome do estabelecimento.
- Selecionar um dos pontos fixos de venda da UFRPE.
- Informar o WhatsApp para receber solicitações.
- Ativar ou desativar a disponibilidade por meio da opção **“Vendendo agora”**.
- Cadastrar produtos com nome, descrição, preço e fotografia opcional.
- Visualizar o próprio cardápio.
- Editar informações dos produtos cadastrados.
- Pausar e reativar produtos.
- Excluir produtos do cardápio.
- Consultar pedidos recebidos e seus detalhes.
- Gerenciar as informações da loja e do perfil.

### 1.3. Gerenciamento de conta

- Cadastro e autenticação de usuários.
- Recuperação de senha por e-mail.
- Atualização de informações pessoais.
- Alteração de senha.
- Gerenciamento de fotografia de perfil.
- Exclusão de conta, conforme as regras implementadas no sistema.
- Alternância entre os modos comprador e vendedor sem necessidade de criar outra conta.

### 1.4. Funcionalidades complementares

O aplicativo também contempla recursos de organização dos pedidos, acompanhamento de informações relacionadas às solicitações e avaliações associadas aos pedidos.

A integração com o Google está validada no dispositivo Android.

## 2. Mapa interativo da UFRPE

O VôLanchar disponibiliza um mapa interativo do campus Recife, desenvolvido com recursos do Kivy e integração com dados cartográficos.

O mapa apresenta nove pontos fixos de venda:

1. Biblioteca Central;
2. Biblioteca Setorial;
3. CEAGRI II / DC;
4. CEGEN;
5. CEGOE;
6. DEAGRI;
7. Departamento de Medicina Veterinária (DMV);
8. Reitoria;
9. Restaurante Universitário (RU).

Os usuários podem consultar os pontos, movimentar o mapa, utilizar os controles de zoom e acessar as ofertas relacionadas aos locais cadastrados.

**Importante:** o VôLanchar trabalha com pontos fixos de venda. O aplicativo não realiza rastreamento da localização pessoal dos usuários nem depende de GPS em tempo real.

## 3. Como funciona

### Para compradores

1. **Cadastre-se:** crie uma conta ou entre com suas credenciais.
2. **Escolha seu perfil:** selecione o modo comprador.
3. **Encontre:** consulte o mapa, os pontos fixos e os vendedores disponíveis.
4. **Explore:** visualize os produtos, preços, descrições e fotografias.
5. **Monte seu pedido:** adicione os produtos ao carrinho e confira o valor total.
6. **Solicite:** registre o pedido e encaminhe a mensagem ao vendedor pelo WhatsApp.
7. **Acompanhe:** consulte as informações dos pedidos registrados.

### Para vendedores

1. Entre no aplicativo e selecione o modo vendedor.
2. Configure o nome do estabelecimento e o WhatsApp.
3. Escolha um dos pontos fixos de venda.
4. Cadastre os produtos disponíveis no cardápio.
5. Ative a opção **“Vendendo agora”** para disponibilizar sua loja nas consultas.
6. Gerencie produtos e pedidos conforme a necessidade.

O VôLanchar **não realiza pagamentos dentro do aplicativo**. A negociação, a forma de pagamento, a confirmação da solicitação e a retirada dos produtos são combinadas diretamente entre comprador e vendedor.

## 4. Tecnologias utilizadas

| Componente | Tecnologia |
|---|---|
| Aplicativo Android | Python e Kivy |
| Interface gráfica | Kivy e componentes personalizados |
| Compilação Android | Buildozer e python-for-android |
| Ambiente de compilação | Ubuntu em WSL2 |
| API | Python e Flask |
| Servidor de aplicação | Gunicorn |
| Hospedagem do backend | Render |
| Banco de dados em nuvem | TiDB Cloud, compatível com MySQL |
| Banco de desenvolvimento | MySQL |
| Comunicação | API REST por HTTPS |
| Mapa interativo | Kivy Garden MapView e dados do OpenStreetMap |
| Integração cartográfica externa | Google Maps |
| Comunicação de pedidos | WhatsApp |
| Controle de versão | Git e GitHub |

### Arquitetura

O VôLanchar utiliza uma arquitetura cliente-servidor.

**Aplicativo Android → API Flask (Render) → Banco de dados (TiDB Cloud)**

O aplicativo apresenta a interface e envia requisições HTTP à API. O servidor processa as operações, realiza as validações necessárias e consulta ou atualiza os dados armazenados no banco.

A comunicação entre o aplicativo e a API ocorre por HTTPS.

## 5. Estrutura do projeto

```text
app_km_zero/
├── app/
│   ├── main.py
│   ├── api.py
│   ├── config.py
│   ├── auth_ui.py
│   ├── ui_theme.py
│   ├── campus_embedded_map.py
│   ├── campus_google_maps.py
│   ├── google_config.py
│   ├── google_maps_config.py
│   ├── buildozer.spec
│   ├── manifest_extra.xml
│   └── assets/
├── backend/
│   └── server.py
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

A estrutura acima representa os principais arquivos do projeto. Outros arquivos de dependências, testes e documentação podem estar disponíveis conforme a organização do repositório.

### Principais componentes

- **main.py:** implementação das telas e das funcionalidades do aplicativo.
- **api.py:** comunicação entre o aplicativo e o backend.
- **config.py:** configuração do endereço público da API.
- **auth_ui.py:** componentes da interface de autenticação.
- **ui_theme.py:** identidade visual e componentes reutilizáveis.
- **campus_embedded_map.py:** implementação do mapa interativo do campus.
- **campus_google_maps.py:** integração com o Google Maps.
- **google_config.py:** configurações relacionadas à autenticação Google.
- **buildozer.spec:** configurações para a compilação Android.
- **server.py:** implementação da API Flask.

## 6. Repositórios e hospedagem

O projeto utiliza repositórios GitHub com responsabilidades diferentes.

### Repositório do projeto completo

**app_km_zero**

https://github.com/eliaspontesufpe-ops/app_km_zero

Reúne o código do aplicativo Android, os arquivos do backend, a documentação e os demais recursos do projeto acadêmico.

### Repositório de implantação do backend

**volanchar-backend**

https://github.com/JenifferUFRPE/volanchar-backend

Utilizado para manter o código do servidor responsável pelo funcionamento da API publicada no Render.

Os repositórios são independentes. Atualizações realizadas no repositório do projeto completo não são automaticamente implantadas no Render.

### API pública

https://volanchar-api.onrender.com

A API é responsável pela autenticação, consulta aos pontos de venda, gerenciamento de estabelecimentos e produtos, registro de pedidos e demais operações relacionadas ao banco de dados.

A disponibilidade do serviço pode variar conforme as condições da hospedagem.

## 7. Instalação no Android

O VôLanchar possui uma versão de testes para dispositivos Android com arquitetura **ARM64 (arm64-v8a)**.

### Versão compilada

- **Aplicativo:** VôLanchar
- **Versão da APK testada:** 0.8.5
- **Tipo:** Debug
- **Arquitetura:** arm64-v8a
- **API mínima configurada:** Android API 24
- **API de compilação:** Android API 36

### Como instalar

1. Acesse a seção [Releases do repositório](https://github.com/eliaspontesufpe-ops/app_km_zero/releases), caso exista uma APK publicada.
2. Baixe a versão compatível com seu dispositivo.
3. Abra o arquivo APK no Android.
4. Autorize a instalação dessa origem, caso o sistema solicite.
5. Conclua a instalação e abra o VôLanchar.
6. Conecte-se à internet e utilize as funcionalidades disponíveis.

**Observação:** a APK de depuração é destinada a testes acadêmicos. Não se trata de uma versão de produção distribuída pela Google Play Store.

## 8. Testes e validação

O VôLanchar passou por atividades de desenvolvimento, compilação e testes internos, envolvendo a interface, a comunicação com o servidor e os principais fluxos funcionais.

Entre as verificações realizadas ou registradas no projeto estão:

- Cadastro e autenticação por senha.
- Alternância entre comprador e vendedor.
- Consulta aos pontos fixos de venda.
- Configuração de estabelecimento e disponibilidade.
- Cadastro e gerenciamento de produtos.
- Consulta de ofertas e utilização do carrinho.
- Registro de pedidos e encaminhamento pelo WhatsApp.
- Comunicação com a API hospedada no Render.
- Integração com o banco de dados TiDB Cloud.
- Compilação e instalação da APK em dispositivo Android físico.

A versão 0.8.5 também recebeu ajustes para o posicionamento da interface em relação às barras de sistema do Android.

A confirmação final desses ajustes, a autenticação Google e os demais testes específicos devem ser registrados com suas respectivas evidências no plano de teste.

Os documentos acadêmicos do projeto incluem o Documento de Requisitos e o Plano de Teste, atualizados para contemplar as funcionalidades atuais.

## 9. Regras de negócio

O funcionamento do VôLanchar considera as seguintes regras:

- Uma mesma conta pode ser utilizada nos modos comprador e vendedor.
- Cada conta possui, no máximo, uma configuração de vendedor.
- A disponibilidade da loja é controlada pela opção “Vendendo agora”.
- Produtos pausados não devem ser apresentados como disponíveis para compra.
- O carrinho não deve misturar produtos de vendedores diferentes em uma mesma solicitação.
- Os valores dos produtos devem ser registrados no momento da criação do pedido, preservando o histórico.
- O pedido deve ser registrado no sistema antes da tentativa de encaminhamento pelo WhatsApp.
- O envio efetivo da mensagem pelo WhatsApp depende da confirmação do usuário.
- Os pontos de venda são locais previamente cadastrados, sem rastreamento por GPS.

## 10. Segurança e privacidade

O projeto adota medidas de proteção relacionadas à autenticação, à comunicação e ao acesso aos dados.

Entre elas:

- Comunicação com a API por HTTPS.
- Autenticação por credenciais e utilização de tokens para acessar recursos privados.
- Validação de operações no servidor.
- Separação entre configurações do aplicativo e credenciais privadas do backend.
- Utilização de variáveis de ambiente para informações sensíveis da infraestrutura.

Senhas, tokens privados, credenciais do banco e arquivos `.env` não devem ser publicados no GitHub.

O aplicativo utiliza informações de cadastro e contato necessárias ao funcionamento dos serviços oferecidos.

## 11. Limitações e funcionalidades futuras

O VôLanchar está em evolução. Algumas funcionalidades ainda podem necessitar de aperfeiçoamentos ou validações adicionais.

Entre os recursos previstos ou considerados para versões futuras estão:

- Sistema de favoritos para vendedores.
- Notificações relacionadas aos pedidos.
- Chat interno entre compradores e vendedores.
- Dashboard com indicadores de vendas.
- Ampliação dos recursos de avaliações.
- Melhorias na experiência de navegação e acessibilidade.
- Aperfeiçoamentos da autenticação com Google.
- Ampliação dos testes de compatibilidade com diferentes dispositivos Android.

Não fazem parte do MVP atual o pagamento integrado, o rastreamento por GPS em tempo real e um serviço próprio de entregas.

## 12. Estado de desenvolvimento

**Versão de referência: 0.8.5 — MVP Android em testes.**

O VôLanchar possui os principais fluxos de comprador e vendedor implementados, integração com uma API pública e armazenamento de dados na nuvem.

O projeto passou por revisões de interface, banco de dados, funcionalidades e documentação. A APK foi compilada e instalada em um dispositivo Android físico.

O desenvolvimento encontra-se em etapa de consolidação, testes de regressão e validação das funcionalidades antes de uma possível distribuição mais ampla.

## 13. Desenvolvedores

Projeto desenvolvido por estudantes da Universidade Federal Rural de Pernambuco:

- Alceu Domingues Alves
- Elias Pontes Junior
- Jeniffer Cavalcanti de Oliveira
- Sérgio Ricardo Ferreira da Silva Filho
- Wilber Antonio Santos da Silva

**Universidade Federal Rural de Pernambuco (UFRPE)**  
**Curso de Licenciatura em Computação**  
**Disciplina: Engenharia de Software**  
**Docente: Prof.ª Suzana Candido de Barros Sampaio**  
**Recife — Pernambuco, 2026**

## 14. Licença

O código-fonte está disponibilizado conforme os termos do arquivo [LICENSE](https://github.com/eliaspontesufpe-ops/app_km_zero/blob/main/LICENSE).

Consulte o documento para conhecer as condições de uso, modificação, distribuição e atribuição de autoria.
