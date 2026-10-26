# Playable Archive — briefing de contexto para a equipe de tradução

Pesquisa e preparação técnica realizadas em 26/10/2026. Este briefing já
foi pesquisado e escrito como parte da engenharia do toolkit. Cabe à equipe de tradução
consultá-lo e confrontá-lo com os contextos. Este documento registra a pesquisa
anterior à tradução. A localização foi concluída em lotes de 250 e 226. As decisões atuais estão no
glossário, nas diretrizes e nas notas de revisão, que prevalecem sobre exemplos
terminológicos apresentados aqui como questões em aberto.

## Identidade e limites da pesquisa

Playable Archive é o jogo Steam AppID **5356470**, desenvolvido pela DarkStone
Digital e publicado pela DreadXP. A API oficial da Steam informa lançamento em
26/10/2026 [1]. O cadastro local identifica o build **26137575**, e os arquivos
informam Unity **6000.0.72f1**, Windows64. Esses dados descrevem a fonte examinada;
uma atualização deve ser novamente identificada pelo toolkit.

A apresentação oficial propõe um arquivo de origem anônima com registros de
eventos inexplicáveis. Sua premissa inclui um casal reformando uma casa,
um objeto misterioso, rituais, comunicação com mortos e múltiplas linhas
temporais. A duração anunciada é de 30–60 minutos, em uma sessão sem salvamento
[1–2]. Isso orienta a leitura do projeto como uma experiência de horror curta;
não autoriza inventar missões, classes ou sistemas de RPG.

As fontes locais contêm mais detalhes narrativos que a apresentação pública.
Elas incluem nomes, diálogos, descrições e documentos, mas sua presença no
arquivo não comprova que cada entrada seja alcançável na versão atual. Há
marcadores de demonstração e textos aparentemente provisórios. Não houve
execução do jogo nem conferência audiovisual nesta preparação.

## Premissa, lugar e estrutura temporal

As primeiras falas de `ScriptSet1` mostram a chegada a uma casa que o casal
conseguiu comprar: entusiasmo, sujeira, caixas, reparos e dificuldades com o
dinheiro. A reforma é o contexto concreto da descoberta, com paredes medidas,
compartimentos ocultos e ferramentas. A ameaça invade um ambiente doméstico
com problemas reconhecíveis, em vez de começar num cenário fantástico abstrato.

O texto oficial fala em New England. Os arquivos locais contêm `locationTitle`
com Rochester, NY e 21/07/2025; `vo_Lamar_IntroRecorder_0` identifica Rochester,
New York, caso CR25014 e 8 de agosto, enquanto `C_Binding_CommencementNote2`
associa 08/08/2025 a uma sexta-feira. Rochester não fica em New England. Registre
essa divergência entre a apresentação e os textos: não substitua locais ou
datas para harmonizar por conta própria. Etiquetas de fitas mencionam 13 de
julho e 8 de agosto; as relações temporais completas precisam de conferência
na partida [3: InGameUiText, ScriptSet1, CompendiumTwo, ObjectText].

Há pelo menos duas formas de apresentação no corpus: conversas domésticas
gravadas e uma investigação posterior. Distinguir o que alguém vive, grava,
recorda ou encontra num documento será importante para manter tempo verbal,
deixis e referentes. Os IDs que terminam em `_0`, `_1`, `_2` frequentemente
fragmentam uma mesma fala; a linha isolada pode não encerrar a oração.

## Personagens e registros de fala

**Daniel** aparece em falas ligadas à casa, ao registro em vídeo e a escolhas
de ferramentas/equipamentos. Seu humor é coloquial, com comentários sarcásticos,
hesitações e palavrões. `S5_threeDays` faz uma piada com pontos em lock picking e
two-handed: é uma referência ao vocabulário de jogos dentro da conversa, não
evidência de que Playable Archive possua essas árvores de habilidade.

**Jessica / Jess** participa da reforma e das conversas sobre trabalho, dinheiro
e organização. `S2_WeCanDoThis_*` mostra encorajamento; `S3_NotTheFocus` e
`S3_TalksAboutMoney` mostram conflito e irritação. A descrição `JessicaId` traz
Jessica Stewart e uma data de nascimento. Não extrapole profissão ou biografia.
`ScriptJessica` também contém falas sobre símbolos e perigo: a voz e o momento
narrativo precisam ser lidos em conjunto, sem tornar todas as falas solenemente
ocultistas [3: ObjectText/JessicaId; ScriptJessica].

**Lamar Robbins / Robins** tem identificação de detetive e narração investigativa.
O roteiro usa Robbins em `vo_Lamar_IntroRecorder_0`, mas o cartão `LamarSheet`
traz Robins. A inconsistência já existe na fonte; a equipe deve registrá-la como
dúvida, sem alterar IDs ou presumir uma grafia definitiva. O registro técnico
de observações convive com reações de medo e linguagem informal. Não uniformize
o tom de uma descrição pericial e de uma exclamação de pânico.

**Dresden / Alan** aparece nas interações policiais, associado a cansaço e a
um turno prolongado. As chamadas de Lamar sugerem uma relação entre as formas
de tratamento, mas a equivalência completa nome/sobrenome depende de contexto.
`M.E.` em `Intro_SixteenHours_2` pertence a esse ambiente de investigação;
pesquisar sua função na situação antes de decidir o termo brasileiro.

**Henry, Tiffany e Adam** aparecem principalmente na documentação pessoal.
O material muda de registro em relação às conversas do casal. Os rótulos
`Speaker_*` identificam Lamar, Jessica, Daniel, Dresden, Henry e uma voz.
São textos visíveis, não metadados a apagar. A palavra `Voice` não revela,
por si só, a identidade completa da entidade.

## Objetos, leitura e ações do jogador

`ObjectText` possui 42 descrições. Há ferramentas de reforma, telefone,
carregador, câmera e fitas mini DV, cadernos, chaves e peças de mecanismos.
A descrição e a fala sobre um objeto devem usar terminologia compatível:
uma mesma fita pode ser descrita no inventário, referida na legenda e rotulada
na interface. Não transforme `key` sempre no mesmo substantivo sem verificar
se é uma chave física, uma instrução de interface ou um símbolo ritual.

`InGameUiText` tem comandos de pegar, colocar, usar, ler, desenhar, equipar,
guardar e interagir; tutoriais de inventário e física; avisos de novas perguntas,
notas e conhecimentos; perguntas e respostas; e etiquetas de fitas. Essas
entradas devem ser curtas e facilmente reconhecíveis, mas o tamanho real da
caixa e a quebra de linha ainda não foram medidos em execução.

`MenuUiText` inclui retomada, opções, aplicação de configurações, cancelamento,
VSync e closed captioning. Há também a string literal `New Game` no assembly,
fora das tabelas. Portanto, traduzir todos os JSONL não equivale a comprovar
que todo menu esteja em português. As descrições podem estar ligadas a
TextMeshPro, imagens ou objetos distintos; o adaptador atual cobre as dez
tabelas TextAsset, sem editar cenas ou código [3–4].

## Símbolos e vocabulário oculto

Nos compêndios e diálogos aparecem `Threshold`, `binding`, `keys of binding`,
`commencement keys`, `pediment slate`, `tracings`, `markings`, `offerings`,
`intent` e `tithe`. Esses termos têm relações internas: o texto descreve
símbolos e procedimentos capazes de impor comandos ou estabelecer vínculos
com entidades. É necessário manter coerência entre a instrução escrita e a
fala que a explica, sem transformar palavras próximas em sinônimos automáticos.

`CompendiumTwo` menciona Rehoboam, Solomon e Abijam numa moldura de transmissão
de conhecimento, com um trecho apresentado como tradução de escrita hebraica
para latim. O registro documental pode ser arcaizante, mas a forma final em
PT-BR pertence às decisões da equipe de tradução. Não substitua a ficção por uma interpretação
religiosa própria nem alegue que esses documentos reproduzem uma fonte histórica.

Valefor, Barbatos, Bathin, Agares, Naberius e Dantalion aparecem tanto como nomes
de seção quanto em respostas de interface. Preserve os identificadores técnicos;
as escolhas sobre grafia visível devem ser documentadas. Várias descrições
dessas seções repetem um texto claramente esquemático (`This is information
about this demon...`). Isso deve ser tratado como uma peculiaridade da fonte,
sem completar a ficha com informações externas ou imaginar conteúdo ausente.

Não há base suficiente para descrever facções, mapas extensos ou uma hierarquia
completa de entidades. O compêndio, as cartas e as instruções oferecem um
conjunto de pistas, não uma enciclopédia verificada do universo.

## Spoilers dos documentos pessoais

**Esta seção revela acontecimentos descritos em `Letters`.** As cartas de
Henry passam por oração, luto, preocupação com a doença do filho, esgotamento
e revolta. Tiffany é descrita como esposa falecida; Adam, como filho doente.
As entradas posteriores aproximam o sofrimento de uma busca por respostas e
de propostas de sacrifício. A progressão emocional deve permanecer legível:
a mudança não é apenas uma troca súbita de vocabulário neutro por palavrões.

Há terminologia clínica, como insuficiência renal e `dialysate`, dentro de uma
voz pessoal. Ela pede precisão contextual sem transformar uma carta em laudo.
O uso de God/god, maiúsculas e repetições também é expressivo. As implicações
religiosas pertencem às personagens; devem ser localizadas com fidelidade,
sem comentar ou corrigir suas crenças.

`Misc` inclui poemas e escrita automática. Ritmo, imagens e ambiguidades
merecem revisão própria; não se deve inferir que rima seja uma condição técnica.
Uma sequência numérica presente no texto e os símbolos de formatação devem
ser avaliados como possíveis pistas, preservando dados de jogo.

## Restrições concretas e riscos para o PT-BR

- O parser do jogo faz `ReadLine`, `Split(';')` e `Trim`. Não aceita ponto e
  vírgula literal nem CSV com campos entre aspas. Use a formatação nativa
  `<br>` quando o contexto exigir quebra; não insira nova linha física.
- `%?` injeta um valor e `%+` possui reaproveitamento por ID na sessão.
  `NOTE_Safe1` e `JessicaNotes1` são os exemplos identificados. Não altere
  o marcador nem traduza o número/código que ele representa.
- Tags como `<b>`, `<i>`, `<size=70%>` e `<br>` são preservadas com
  multiplicidade. `CompBinding1Title` já contém `<b>` sem fechamento correto;
  o toolkit permite preservar a sequência original e registra a anomalia.
- Há erros/rascunhos de origem: `gen_flashlight` contém `delete`, `JessicaId`
  contém `/n` literal, há grafias e datas inconsistentes. Não remova entradas
  nem interprete `/n` automaticamente como quebra válida.
- O suporte a UTF-8 foi verificado na reconstrução. Isso não comprova que os
  atlas das fontes tenham todos os glifos. Yuri deve testar ç, ã, õ, é, ê, á,
  maiúsculas acentuadas, pontuação e expansão das linhas no jogo.
- Falas interrompidas, respiração e sons entre parênteses pertencem às legendas.
  Revise o contexto dos fragmentos, a função de closed captioning e as vozes.
  O toolkit valida estrutura, não concordância, tom ou sincronização audiovisual.

## Perguntas para a revisão contextual

Qual grafia de Robbins/Robins será adotada no texto visível? Quais entradas de
demonstração são usadas nesta edição? Como as pistas de calor, mão e vínculo
aparecem visualmente nos enigmas? A voz identificada no speaker muda de caráter
entre momentos? Os textos fixos de cena precisam de um segundo adaptador?
Há rótulos que dependem de imagens em vez de TextAsset? Registre evidências
novas sem preencher lacunas com suposições.

## Fontes e rastreabilidade

1. [API oficial da Steam — AppID 5356470](https://store.steampowered.com/api/appdetails?appids=5356470&l=english).
   Consulta em 26/10/2026; metadados selecionados em `../research/steam-metadata.json`.
2. [Página oficial do jogo na Steam](https://store.steampowered.com/app/5356470/Playable_Archive/).
   A página HTML não ficou acessível pelo leitor web nesta sessão; a descrição,
   imagem e dados foram verificados pela API oficial e pelo endereço da imagem.
3. Fonte local: `EN/Playable Archive_Data/resources.assets`. Tabelas e chaves
   estão no manifesto e em `translations/batch-0001.jsonl`. Os IDs usam
   `caminho#tabela/chave`; as referências acima podem ser localizadas por `key`.
4. Inspeção somente leitura de `Playable Archive_Data/Managed/Assembly-CSharp.dll`:
   `TextManager.BuildNewLanguage`, `ParseCsv`, `GetString`, `NoteBuilder` e
   `TextObjectUpdater`. O assembly não é redistribuído no repositório.

As afirmações sobre personagens e documentos provêm dos textos originais locais.
Yuri confirmou o teste da tradução completa e dos glifos no jogo em 26/10/2026.
