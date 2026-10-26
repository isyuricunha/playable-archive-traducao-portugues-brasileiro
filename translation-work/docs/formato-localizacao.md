# Formato nativo e contrato do adaptador

## Fonte verificada

Jogo: Playable Archive, Steam AppID 5356470, build 26137575. Unity 6000.0.72f1,
Windows64. Recurso gerenciado único:
`Playable Archive_Data/resources.assets` — **21.731.896 bytes**, SHA-256
`67096199754073b6a3e6007df745c737559ea9327efbb6872c2a15376bae5766`.
Esses valores são o snapshot inicial, não requisitos eternos para updates.

| TextAsset | Entradas |
| --- | ---: |
| CompendiumBase | 22 |
| CompendiumTwo | 23 |
| InGameUiText | 63 |
| Letters | 8 |
| MenuUiText | 12 |
| Misc | 5 |
| ObjectText | 42 |
| ScriptCC | 1 |
| ScriptJessica | 56 |
| ScriptSet1 | 244 |

O contêiner possui 2.879 objetos. Somente os dez TextAssets de localização são
interpretados para reconstrução; os demais payloads, IDs, hashes de tipo,
referências externas e metadados permanecem opacos. Não há criptografia ou
compressão envolvendo esse arquivo específico.

## SerializedFile

O cabeçalho Unity v22 usa campos de tamanho/offset de 64 bits e números big-endian
no header; a seção de metadados identificada usa little-endian. O adaptador
aceita somente v22, Unity 6000 e target19, valida contagens, limites, sobreposição
e unicidade de PathID. Lê tipos e sua tabela de objetos. Type trees presentes
podem ser saltados pelo tamanho especificado; o jogo examinado não requer
interpretar layouts de MonoBehaviour para ler TextAssets.

Cada TextAsset classe49 possui nome UTF-8 com comprimento int32 e alinhamento4,
seguido por comprimento int32 do script, bytes UTF-8 e padding4. O adaptador
recusa dados finais desconhecidos. Para alterar um script, calcula novamente
o comprimento em bytes e o padding, preserva nome/estrutura e reempacota a
seção de dados. Ajusta somente tamanho do arquivo e offsets/tamanhos da tabela
de objetos. Mantém alinhamento8 relativo aos objetos de origem, gaps opacos,
ordem e bytes de todos os payloads não modificados.

O no-op de todos os textos ingleses gera bytes **idênticos** ao original. Um
teste acentuado em memória foi reaberto com UnityPy 1.25.4 de desenvolvimento,
que confirmou a leitura dos TextAssets e a preservação dos 2.879 objetos, com
somente o objeto escolhido alterado. A versão do UnityPy instalada para
investigação não é dependência de execução nem é vendorizada no Git.

Referência de pesquisa do layout: implementação pública de
[SerializedFile no AssetStudio](https://github.com/Perfare/AssetStudio/blob/master/AssetStudio/SerializedFile.cs).
O código do adaptador foi escrito para este contrato restrito, sem copiar ou
redistribuir o programa de terceiros. Não é um parser universal de Unity.

## Carregamento e texto

Inspeção de IL em `Assembly-CSharp.dll`, somente leitura, mostrou:

- `TextManager.BuildNewLanguage`: carrega TextAssets em `Text/` e passa a
  escolha de idioma ao parser.
- `ParseCsv`: ignora cabeçalho; usa `ReadLine`, `Split(';')`, chave na coluna0
  e idioma pelo índice, seguido de `Trim`. Não há escape CSV nem fallback de
  idioma comprovado. Uma chave duplicada é ignorada depois da primeira no jogo;
  o toolkit recusa duplicações para não depender da ordem de carregamento.
- `GetString`: usa `%?` para injeção e `%+` com cache de sessão por ID.
- `TextObjectUpdater` e `NoteBuilder`: encaminham o valor para objetos de texto.

Cabeçalho reconhecido:

```text
KEY;English;French;Italian;German;Spanish;Chinese;Japanese
```

O arquivo inicial usa UTF-8 e LF. As seis colunas adicionais estão vazias nas
tabelas reconhecidas. Elas são mantidas e expostas em `original_languages`,
inclusive para detectar mudanças futuras de contexto. O build substitui somente
**English**, não adiciona uma coluna que o jogo desconheça. Aspas não escapam
um ponto e vírgula. Uma nova linha visível deve usar tags nativas como `<br>`.

## Identidade e registro

Cada registro tem ID `caminho#tabela/chave`, com componentes tabela/chave
percent-encoded, `source_file`, `table`, `key`, `row`, `path_id`, `EN`,
`original_languages`, `source_fingerprint` e `PTBR`. IDs não usam número de
linha como identidade. Hash semântico usa caminho/tabela/chave/EN/outros idiomas;
row e PathID são localizadores atualizáveis, não a identidade permanente.
Não se reutiliza tradução automaticamente entre chaves com texto igual.

O manifesto schema1 armazena mapeamento, hashes, geração, catálogo completo
de fonte e inventário de lotes. Os lotes mantêm sua atribuição durante updates;
o build usa a localização do snapshot atual, não a ordem dos lotes.
O histórico versionado guarda registros completos modificados/removidos.

## Validação e limites

Proteção de `%?`, `%+`, placeholders posicionais e tags por multiplicidade;
pareamento/nesting de rich text quando o original é válido. A anomalia nativa
`CompBinding1Title` exige preservar a sequência de tags exata, sem uma correção
automática oculta. Controles, semicolons e newlines físicas são recusados em PTBR.

O pacote atual cobre as tabelas. Não cobre strings literais como `New Game`
em código, campos de texto serializados em cenas, nem imagens com texto. Não
edita DLLs, fontes ou cenas. Adicionar esses formatos exigirá outra investigação
e um adaptador com identidade e reconstrução comprovadas. Não há teste visual
de glifos, layout, sincronização de legendas ou cobertura em runtime.
