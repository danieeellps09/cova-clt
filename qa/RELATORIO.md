# Auditoria técnica - A Corrida da Aposentadoria

Data: 17/10/2026.

Arquivo auditado: `A Corrida da Aposentadoria .html`. O arquivo existente tem um espaço antes de `.html`; o caminho sem esse espaço não existe. O nome foi preservado.

## Resultado

Nenhum bloqueador técnico conhecido permaneceu nos cenários testados em Google Chrome headless. Visual, cores, cenas, interfaces, custos e fórmulas de balanceamento foram preservados. A pausa da aba oculta agora é explícita e consistente.

## Bugs corrigidos

| Prioridade | Problema encontrado | Correção |
| --- | --- | --- |
| P2 | Enter/espaço sobre um card portrait podia executar TRABALHAR em vez de comprar. O botão de trabalho não tinha ativação nativa por teclado. | Botões HTML recebem seu comportamento nativo; o atalho global só atua fora deles. |
| P2 | O botão portrait aceitava o botão direito e ponteiros secundários. | Somente botão principal e ponteiro primário contam como trabalho. |
| P2 | O mudo ficava em coordenadas da janela, sobrepondo o PIB quando o canvas era reduzido ou centralizado. | Posição e tamanho acompanham a escala e a origem do canvas em landscape. |
| P2 | Compras e chamadas repetidas de finalização podiam alterar o estado após o encerramento; compras diretas também atravessavam popups. | Guardas nas quatro compras e finalização idempotente. |
| P2 | Eventos, recuperação e timeout da Janela usavam relógios independentes; eventos continuavam penalizando o jogador com a aba oculta. | Um relógio ativo pausa ao ocultar a aba. Eventos mantêm 12 segundos ativos, Janela 5 segundos ativos e recuperação 2 pontos por segundo ativo. Não há rajada de eventos ao voltar. |
| P2 | Efeitos que não eram cliques podiam acumular agendamentos de áudio no futuro. | Fila limitada a no máximo 50 ms; fontes são rastreadas, encerradas ao silenciar e desconectadas ao terminar. Clique e picareta continuam como efeito composto com intervalo interno de 30 ms. |
| P2 | Vitória com progresso inválido gerava idade e meses `NaN`, fora do contrato de 1 a 12 meses. | Sanitização de progresso antes do cálculo. A derrota já protegia idade e meta, e essa proteção foi confirmada. |
| P2 | O início da animação do atestado dependia da chegada do primeiro quadro e usava um teste de valor falso para o timestamp zero. | O timestamp é registrado ao finalizar a partida, sem depender da renderização. |
| P3 | Falha ao iniciar ou retomar áudio podia interromper a interação ou gerar warnings repetidos. | Degradação para mudo, mantendo a partida, com diagnóstico no título acessível do botão. |
| P3 | Rotação das partículas de evento dependia do FPS; não havia prazo máximo de remoção dessas partículas. | Movimento proporcional a `dt` e remoção defensiva após 15 segundos ativos. |
| P3 | Estado de impacto inalcançável, contador chamado FPS que contava quadros acumulados, idade inicial abandonada e CSS sobrescrito. | Remoção do código comprovadamente morto, sem mudança visual. |

## Lógica confirmada

- Meta: `0.3 + Math.log(E.pib + 1) * 0.05`, somente quando não está travada.
- Hora Extra: custa 50 meses, velocidade 1.2, burnout adicional 1.5 por clique; desgaste passivo continua 0.01.
- Curso: custa 30 meses; só altera a aparência por 3 segundos.
- Empreender: desconta 10 meses e exibe popup.
- Negociação: custa 40 meses, multiplica a meta por 1.15 e bloqueia nova compra.
- Fator: `Math.floor(meses * 0.75)`; Intimação: menos 8, com piso zero; Janela: trava a meta por 5 segundos.
- Vitória: meses aproveitados sempre entre 1 e 12, inclusive entradas inválidas testadas.
- Marcas: limite de 15, prazo de 1.5 segundo e fade final; limpeza confirmada nos dois layouts.
- Partículas: limite de 200, com remoção por idade ou saída da tela.
- Um AudioContext por página, iniciado apenas por interação, retomada se suspenso, preferência `aposentadoria_mudo` persistida e início silencioso após recarga.
- Nenhum `console.log`/`console.warn`, URL de recurso externo, importação, imagem ou biblioteca externa no HTML.

### Zero e valores inválidos

Zero meses não é condição de derrota nas regras existentes. O teste confirmou que o Fator pode levar o progresso de 1 a 0 sem encerrar ou quebrar o jogo. Para testar a apresentação de derrota com zero e `NaN`, foi preparado um estado defensivo de burnout e chamada a finalização. Ambos mostram 65 anos. Não foi inventada uma nova regra de derrota.

### Limites matemáticos e aleatoriedade

A meta não tem teto e só deixa de crescer durante a Janela ou após o encerramento. Seu incremento marginal atinge 1 mês por clique perto de `exp(14)-1`, aproximadamente 1.2 milhão de PIB. Isso não bloqueia as partidas curtas testadas, mas não existe garantia matemática de vitória em qualquer sequência de eventos ou número de cliques.

Os eventos podem alongar muito uma partida: uma sequência portrait não terminou em 1.600 cliques, e uma tentativa com compras não terminou em 700. Essas execuções não produziram erro técnico; revelam variância do balanceamento aprovado. Não foram adicionados teto, proteção contra azar, perda automática por zero ou mudanças nos eventos.

## QA executado

Partidas automatizadas com relógio acelerado, entradas pelos controles e eventos ativos. Diferentes sementes foram usadas quando a sequência aleatória não permitia concluir dentro do limite do teste.

| Fluxo | 900x600 | 400x900 |
| --- | --- | --- |
| Vitória normal | 291 cliques | 229 cliques |
| Derrota por burnout | 118 cliques | 118 cliques |
| Vitória com quatro upgrades | 466 cliques | 388 cliques |
| Zero/NaN na derrota | 65 anos | 65 anos |
| Reinício após o atestado | Passou | Passou |
| Hitboxes de trabalho, quatro cards e mudo | Passou | Passou |

Também foram exercitadas rotações 900x400, 400x900, 1600x900 e 900x600; sem distorção da proporção 3:2 e com mudo alinhado ao canvas. Teclado, toque e rejeição de clique secundário passaram.

Carga: dez minutos de tempo simulado e 60.000 cliques, reiniciando o estado ao terminar rodadas. Máximos: 200 partículas e 15 marcas; após repouso simulado, ambas as listas ficaram vazias. Isso valida limites e descarte, mas não equivale a dez minutos reais de medição contínua de heap.

Desempenho: 60.2 FPS em amostra separada de 3 segundos de renderização portrait, em repouso, no Chrome headless. Esse número não é média das partidas aceleradas nem medição em aparelho físico.

Nenhum erro ou warning de console nas etapas concluídas. A suíte precisou aguardar a navegação de reinício e executar os quadros da animação final; saltar o relógio diretamente ao último instante não produz uma captura válida dessa animação.

## Melhorias futuras não implementadas

1. Validação manual em Safari/iOS e Android físico, incluindo áudio audível, safe areas e retomada de aba. O headless confirma funcionamento da API, não qualidade sonora.
2. Sessão real de 10 minutos com perfil contínuo de heap/GPU e bateria em dispositivo móvel.
3. Decisão de produto sobre limite de duração e sequências de eventos muito desfavoráveis. Exige aprovação de balanceamento.
4. Definir o nome/rota de entrada na hospedagem; o HTML atual contém espaço antes da extensão.

## Artefatos

- `qa/auditoria.py`: suíte reproduzível; depende de Playwright apenas no ambiente de testes.
- `qa/resultado.json`: resultados da execução final das verificações comuns e cenários portrait.
- `qa/prints/`: evidências dos dois layouts, vitórias, burnout e estados defensivos zero/NaN.

O jogo distribuído continua sendo um único HTML autocontido. Nenhum arquivo de QA é dependência do jogo.

Conclusão: o jogo está estável e pronto para produção no escopo técnico validado em Chrome. Não há bloqueadores técnicos conhecidos nesse escopo; a aprovação não substitui a validação física de Safari/iOS/Android nem garante conclusão rápida para toda sequência de eventos.
