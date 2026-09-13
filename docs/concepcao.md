# Concepção do Projeto

## 1. Identidade da Startup

**Nome:** StarTech

A StarTech é a startup desenvolvida para o Trabalho Prático da disciplina GCC129 – Sistemas Distribuídos. Neste projeto, sua proposta está inserida no contexto da doação de sangue, com foco no apoio à mobilização e à fidelização de doadores e na aproximação entre doadores e serviços de hemoterapia.

## 2. Problema e Motivação

### 2.1 Contexto do problema

A disponibilidade de sangue e hemocomponentes depende da realização contínua de novas doações. Segundo o Ministério da Saúde, os hemocomponentes possuem diferentes prazos de validade e a demanda dos serviços de saúde é permanente, tornando necessárias novas doações ao longo de todo o ano. Em 2025, o Sistema Único de Saúde (SUS) registrou 3.264.138 coletas de sangue, correspondendo a uma taxa de 15,29 doações por mil habitantes [1].

Mesmo com esse volume de doações, podem ocorrer períodos de baixa disponibilidade. Em agosto de 2026, por exemplo, a Fundação Hemominas divulgou um alerta informando que seus estoques haviam atingido níveis críticos e que a redução poderia comprometer a manutenção regular do atendimento às demandas transfusionais dos hospitais de Minas Gerais [2]. O caso demonstra que a necessidade por doações não é constante em intensidade e pode variar ao longo do tempo.

Além da captação de novos doadores, a retenção de pessoas que já doaram também constitui um desafio relevante. Um estudo realizado no Brasil, com dados de mais de dois milhões de tentativas de doação ao longo de 26 anos, identificou que impedimentos temporários estavam associados a uma redução de 50% na probabilidade de retorno dos doadores em um contexto sem ações específicas de retenção [3].

A literatura também apresenta evidências de que estratégias de comunicação podem contribuir para promover novas doações. Uma revisão sistemática que analisou 29 estudos identificou os lembretes entre as intervenções com resultados positivos para o aumento da doação de sangue [4]. Outro estudo, realizado com doadores temporariamente impedidos de doar, verificou que o envio de uma mensagem informando a proximidade do término do período de impedimento aumentou a probabilidade de tentativa de retorno [5].

No Brasil já existem soluções digitais voltadas à doação de sangue. O Hemovida, disponibilizado pelo Ministério da Saúde por meio do Meu SUS Digital, permite localizar hemocentros, realizar agendamentos, acompanhar contribuições e convidar outras pessoas para doar [6]. Dessa forma, a proposta da StarTech não se limita à criação de mais uma ferramenta de localização ou agendamento.

O problema central considerado pelo projeto é, portanto:

> **A dificuldade de manter uma mobilização contínua de doadores de sangue e alinhá-la às necessidades variáveis dos serviços de hemoterapia no Brasil.**

### 2.2 Motivação

A proposta parte da necessidade de fortalecer a comunicação entre serviços de hemoterapia e doadores, permitindo que necessidades de doação e campanhas sejam divulgadas de forma mais direcionada e que os doadores sejam incentivados a manter uma participação recorrente.

A possibilidade de acompanhar necessidades, receber avisos e lembretes e visualizar oportunidades de doação pode contribuir para reduzir a distância entre o momento em que um serviço necessita mobilizar doadores e o momento em que essas pessoas tomam conhecimento dessa necessidade.

A proposta também considera a importância da fidelização. Em vez de concentrar a atuação apenas na captação de novos doadores, a plataforma busca manter o vínculo com pessoas que já participaram de doações ou demonstraram interesse em doar, favorecendo seu retorno ao longo do tempo.

Assim, o foco do projeto está na **mobilização e fidelização de doadores orientadas pelas necessidades comunicadas pelos serviços de hemoterapia**.

## 3. Impacto Social Esperado

O impacto social esperado da solução é contribuir para uma mobilização mais contínua e direcionada de doadores de sangue, facilitando a comunicação entre os serviços de hemoterapia e as pessoas dispostas a doar.

Ao permitir a divulgação de necessidades e campanhas e oferecer mecanismos de avisos, lembretes e acompanhamento, a plataforma poderá apoiar tanto a mobilização de doadores diante de necessidades específicas quanto o retorno de pessoas que já realizaram doações anteriormente.

A proposta não pressupõe que o sistema seja capaz de eliminar períodos de baixa disponibilidade ou garantir a estabilidade dos estoques de sangue. Esses resultados dependem de diversos fatores externos à aplicação. O papel da plataforma é atuar como um instrumento adicional de comunicação, mobilização e acompanhamento.

### 3.1 Beneficiários

Os principais beneficiários esperados são:

- **Doadores de sangue:** poderão acompanhar necessidades e campanhas, receber avisos sobre oportunidades de doação e lembretes relacionados ao retorno à doação;
- **Serviços de hemoterapia:** poderão utilizar um canal adicional para divulgar necessidades, promover campanhas e acompanhar a resposta dos doadores às ações de mobilização;
- **Pacientes que necessitam de sangue e hemocomponentes:** serão beneficiários indiretos, uma vez que dependem da disponibilidade desses recursos para diferentes tratamentos e procedimentos de saúde.

### 3.2 Avaliação do impacto

Em uma aplicação real, o impacto da solução poderia ser acompanhado por meio de indicadores relacionados à mobilização e ao retorno dos doadores, como:

- número de doadores alcançados por campanha;
- número ou proporção de doadores que demonstraram interesse após a divulgação de uma necessidade;
- proporção de campanhas ou avisos que resultaram em agendamentos;
- taxa de comparecimento aos agendamentos;
- taxa de retorno de doadores ao longo do tempo;
- tempo entre a divulgação de uma necessidade e as primeiras respostas dos doadores.

Esses indicadores permitiriam avaliar se a plataforma está contribuindo efetivamente para aproximar as necessidades comunicadas pelos serviços de hemoterapia da participação dos doadores.

## 4. Esboço da Solução

A solução proposta consiste em uma plataforma destinada a aproximar serviços de hemoterapia e doadores de sangue, com foco na divulgação de necessidades de doação, mobilização de pessoas e incentivo ao retorno dos doadores.

Os serviços de hemoterapia poderão registrar e divulgar necessidades de doação e campanhas. Essas informações serão disponibilizadas pela plataforma para que os doadores possam acompanhar situações relevantes e identificar oportunidades de participação.

Os doadores poderão visualizar essas necessidades e campanhas, receber avisos e lembretes e demonstrar interesse em participar. A plataforma também poderá oferecer suporte ao agendamento de doações quando esse recurso estiver disponível no contexto do serviço de hemoterapia.

O histórico de doações e de interações registrado na plataforma poderá ser utilizado para apoiar ações de fidelização e retorno. Por exemplo, o sistema poderá lembrar um doador sobre uma nova oportunidade de participação quando houver uma necessidade relevante e as informações disponíveis indicarem que pode ser apropriado considerar uma nova doação.

Esses avisos terão caráter exclusivamente informativo. A plataforma não determinará se uma pessoa está apta a doar sangue, uma vez que a aptidão depende dos critérios vigentes e da triagem realizada pelo serviço de hemoterapia.

A partir das interações realizadas pela plataforma, os serviços também poderão acompanhar informações relacionadas à mobilização, como interesse em campanhas, agendamentos, comparecimentos e retorno dos doadores. Essas informações poderão auxiliar na avaliação das estratégias utilizadas para mobilização e fidelização.

De forma geral, o fluxo proposto pode ser representado da seguinte maneira:

1. o serviço de hemoterapia identifica e registra uma necessidade de doação ou uma campanha;
2. a plataforma disponibiliza essa informação aos doadores;
3. os doadores podem visualizar a necessidade, receber avisos e demonstrar interesse ou realizar um agendamento;
4. o serviço de hemoterapia acompanha a resposta dos doadores à ação de mobilização;
5. posteriormente, a plataforma pode apoiar o retorno dos doadores por meio de lembretes e novas oportunidades de participação.

A proposta não busca realizar a gestão completa dos estoques de sangue nem substituir os sistemas já utilizados pelos serviços de hemoterapia. Seu foco está no apoio à comunicação, à mobilização e à fidelização dos doadores.

Nesta etapa de concepção ainda não são definidos aspectos relacionados à arquitetura do sistema, tecnologias utilizadas, bancos de dados, protocolos de comunicação ou formato específico dos clientes da aplicação. Essas decisões serão realizadas nas etapas posteriores do projeto.

## 5. Referências

[1] BRASIL. Ministério da Saúde. [**Com novas regras do Ministério da Saúde, pessoas com mais de 70 anos poderão continuar a doar sangue**](https://www.gov.br/saude/pt-br/assuntos/noticias-ms/2026/agosto/com-novas-regras-do-ministerio-da-saude-pessoas-com-mais-de-70-anos-poderao-continuar-a-doar-sangue/). Brasília: Ministério da Saúde, 12 ago. 2026. Acesso em: 13 set. 2026.

[2] FUNDAÇÃO HEMOMINAS. [**Hemominas faz alerta urgente diante de níveis críticos dos estoques de sangue**](https://www.hemominas.mg.gov.br/hemominas-faz-alerta-urgente-diante-de-niveis-criticos-dos-estoques-de-sangue). Belo Horizonte: Fundação Centro de Hematologia e Hemoterapia de Minas Gerais, 10 ago. 2026. Atualizado em: 25 ago. 2026. Acesso em: 13 set. 2026.

[3] FERREIRA, Claudio M.; VIEITES, Yan; GOLDSZMIDT, Rafael; ANDRADE, Eduardo B. [**The effect of temporary deferrals on donor return: A 26-year assessment in a setting without retention activities**](https://pubmed.ncbi.nlm.nih.gov/35855649/). *Transfusion*, v. 62, n. 8, p. 1583-1593, 2022. DOI: [10.1111/trf.17025](https://doi.org/10.1111/trf.17025).

[4] GODIN, Gaston; VÉZINA-IM, Lydi-Anne; BÉLANGER-GRAVEL, Ariane; AMIREAULT, Steve. [**Efficacy of interventions promoting blood donation: a systematic review**](https://pubmed.ncbi.nlm.nih.gov/22126711/). *Transfusion Medicine Reviews*, v. 26, n. 3, p. 224-237.e6, 2012. DOI: [10.1016/j.tmrv.2011.10.001](https://doi.org/10.1016/j.tmrv.2011.10.001).

[5] GEMELLI, Carley N.; THIJSEN, Amanda; VAN DYKE, Nina; KRUSE, Sarah P.; DAVISON, Tanya E. [**Notifying donors when their deferral is ending: An effective donor retention strategy**](https://pubmed.ncbi.nlm.nih.gov/34352927/). *Transfusion*, v. 61, n. 10, p. 2930-2940, 2021. DOI: [10.1111/trf.16613](https://doi.org/10.1111/trf.16613).

[6] BRASIL. Ministério da Saúde. [**Consultar o guia Hemovida para obter as regras para doação de sangue**](https://www.gov.br/pt-br/servicos/consultar-o-guia-hemovida-para-obter-as-regras-para-doacao-de-sangue). Portal de Serviços do Governo Federal. Última modificação: 11 fev. 2026. Acesso em: 13 set. 2026.
