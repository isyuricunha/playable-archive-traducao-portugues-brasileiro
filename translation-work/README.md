# Playable Archive — guia técnico da tradução

<!-- release-state: unavailable -->

Estado atual: **tradução concluída e testada em jogo por Yuri**, incluindo os
glifos. São 476 entradas em dois lotes de 250 e 226, sem campos pendentes.
`PTBR/` e o build-manifest estão validados. O GitHub Actions gera o ZIP
automaticamente para publicação na página de Releases.

## Começo no Ubuntu Server 24.04 LTS ARM64

Após o clone/pull habitual, na raiz do repositório, execute **um preflight**:

```bash
python3 -B translation-work/toolkit.py doctor
```

Requer Python **3.10+** com biblioteca padrão; o Python 3.12 do Ubuntu 24.04 é
adequado ao contrato. Não há pip, Mono, .NET, DLL, pacote nativo, serviço externo
ou variável de busca de assemblies para configurar. O toolkit não instala nada.
O doctor verifica SO/arquitetura, runtime, hashes canônicos, a fonte aceita e
uma fixture Unity válida, inclusive reconstrução com caracteres acentuados, e
reconstrói em memória a fonte do menu usando o recurso original aceito.
Não altera traduções, fontes, relatórios, PTBR ou pacotes.

**Resultado ao vivo no Ubuntu ARM64: pendente.** Os testes de engenharia são
executados no Windows. O preflight local usa `doctor --local`, que não certifica
ARM64. Se o preflight do servidor falhar, a equipe deve parar antes da tradução e
encaminhar o erro exato para correção no Windows. Não regenerar hashes para
contornar uma falha nem instalar pacotes/usar SSH automaticamente.

Depois de passar:

1. Leia [o briefing pronto](docs/briefing-do-jogo.md),
   [o formato](docs/formato-localizacao.md) e [o fluxo](docs/fluxo-de-traducao.md).
2. Mantenha as decisões em [glossario-ptbr.md](docs/glossario-ptbr.md) e
   [diretrizes-de-traducao.md](docs/diretrizes-de-traducao.md).
3. Execute `status`, `diff` e `resume`; traduza o JSONL em grupos que consiga
   revisar, aplicando apenas `PTBR` pelo mecanismo abaixo.
4. Faça commits de progresso quando desejar, sem tocar em `PTBR/`. O toolkit
   nunca faz commit ou push. A versão textual atual já está traduzida; em
   atualizações, revise os itens que o sync adicionar ou invalidar.

## Organização e instalação nativa

```text
EN/Playable Archive_Data/resources.assets    original binário preservado
EN/Playable Archive_Data/sharedassets0.assets original da fonte do menu
translation-work/translations/             manifest.json e batch-0001.jsonl
translation-work/history/                  textos anteriores em atualizações
translation-work/reports/                  último diff e validação técnica
translation-work/.state/                   locks/backups locais ignorados
PTBR/Playable Archive_Data/resources.assets somente depois de build completo
PTBR/Playable Archive_Data/sharedassets0.assets fonte somente no build completo
translation-work/build-manifest.json       recibo versionado do build
```

O caminho relativo dentro de `PTBR/` é o caminho real abaixo da pasta do jogo.
O ZIP contém `Playable Archive_Data/resources.assets` e
`Playable Archive_Data/sharedassets0.assets`, sem pasta PTBR externa.
O jogo continua em inglês no seletor: a reconstrução substitui a coluna English.
A instalação é manual, com backup, conforme o README público. Nenhuma operação
da ferramenta escreve no diretório de instalação. Não execute a ferramenta
de dentro de uma instalação nem mova o repositório para ela.

O binário possui outros objetos e referências a recursos da instalação.
Eles são preservados; não é um pacote autônomo. A licença do projeto não concede
permissões sobre esses recursos proprietários. Revise os direitos aplicáveis
antes de distribuição pública. Nenhum recurso de mod é incluído.

A fonte do menu usa Courier Prime Regular, sob [SIL OFL 1.1](vendor/courier-prime/OFL.txt).
Yuri confirmou em jogo a tradução completa e os glifos. O build gera o
recurso de fonte junto aos textos. Detalhes e restauração: [teste-da-fonte.md](docs/teste-da-fonte.md).

## Comandos na raiz do repositório

Os caminhos do projeto são relativos ao próprio script: também funciona a partir
de outro diretório usando o caminho completo do script. Todos os comandos emitem
JSON; `--json` é aceito para automações. Saída 0 indica sucesso, 2 indica erro;
`apply --partial` retorna 1 quando há rejeições, preservando os itens aceitos.

```bash
python translation-work/toolkit.py status
python translation-work/toolkit.py resume
python translation-work/toolkit.py check
python translation-work/toolkit.py diff

# Autodetecção limitada a metadados Steam e caminho local já validado:
python translation-work/toolkit.py update-sources --dry-run
python translation-work/toolkit.py update-sources

# Quando o jogo não está detectável:
python translation-work/toolkit.py update-sources --game-root "G:/SteamLibrary/steamapps/common/Playable Archive" --dry-run
python translation-work/toolkit.py update-sources --game-root "G:/SteamLibrary/steamapps/common/Playable Archive"

# Alternativas para originais fornecidos pelo usuário:
python translation-work/toolkit.py sync
python translation-work/toolkit.py sync --source-file "/caminho/resources.assets" --dry-run
python translation-work/toolkit.py sync --source-root "/caminho/raiz-com-Playable-Archive_Data"

python translation-work/toolkit.py apply --payload "/caminho/aplicacao.json"
python translation-work/toolkit.py build
python translation-work/toolkit.py verify-output
python translation-work/toolkit.py package

python translation-work/toolkit.py gc --dry-run
python translation-work/toolkit.py gc
python translation-work/toolkit.py recover
python translation-work/toolkit.py rollback
```

`extract --source-file ...` é apenas para a criação inicial e recusa sobrescrever
um manifesto existente. O lote inicial pode ser configurado por `--batch-size`
(1–500). Atualizações respeitam o tamanho e as atribuições já aceitos.
`diff --source-file ...` compara um candidato sem aceitar mudanças;
`diff` sozinho apresenta o último relatório, com a geração aceita atual.

No servidor, não existe acesso ao jogo do Windows por mágica: se não houver uma
instalação local identificável, `update-sources` falha com o exemplo `--game-root`.
Yuri pode atualizar as fontes no Windows e entregar o EN aceito pelo Git.

### Proveniência e atualizações

`app.info`, estrutura nativa, AppID e metadados Steam identificam a instalação.
O primeiro snapshot foi confirmado pelo caminho fornecido por Yuri. Um arquivo
igual a um build PTBR conhecido é recusado como inglês. Se o mesmo build Steam
aparecer com bytes diferentes, a importação exige restaurar os originais pela
Steam. Um novo build pode ser aceito após validação estrutural e identidade;
isso **não é prova criptográfica de ausência de mods**. Arquivos fornecidos
explicitamente são registrados como originais fornecidos pelo usuário, sem
alegar autenticação pelo fabricante. Não use instalações modificadas como EN.

`sharedassets0.assets` também é uma dependência nativa do build e é preservado
em `EN/`. O adaptador de fonte aceita somente o hash original verificado do
build 26137575; um arquivo modificado ou atualização diferente bloqueia a
importação do diretório do jogo até revisão do adaptador. `--source-root` também
deve conter esse recurso original. `--source-file` usa a cópia aceita em EN;
a compatibilidade desse arquivo isolado com o build continua dependendo da
origem informada. A instalação de teste contém arquivos modificados, portanto
restaure os backups antes de usá-la com `update-sources`.

Não há varredura recursiva de discos: a descoberta consulta locais Steam
limitados e seus manifests. Zero ou múltiplas instalações válidas exigem caminho
explícito. Caminho externo validado fica apenas em `.state/local-install.json`.

`sync` e `update-sources` usam a mesma implementação. IDs são estáveis por
caminho/tabela/chave. Mudanças em EN ou outras colunas da mesma entrada invalidam
somente seu PTBR e preservam o anterior em `history/`. Mover uma linha preserva
a tradução e atualiza o localizador. Chave renomeada é remoção mais adição;
sem reuso aproximado. Uma tabela desaparecida é tratada como fonte incompleta e
bloqueia a atualização, até revisão explícita do adaptador. Um novo arquivo
nativo não é importado silenciosamente: o contrato de textos cobre apenas resources.assets;
novos TextAssets com o cabeçalho reconhecido nesse arquivo são descobertos.

O catálogo completo de originais aceitos fica no manifesto versionado, e as
entradas antigas afetadas ficam no histórico versionado. Portanto, substituir
EN manualmente não destrói a comparação. A falta de um snapshot aceito válido
deve ser corrigida pelo histórico Git; não é autorização para apagar progresso.

### Aplicar sem alterar os originais

O payload é um JSON (não é o lote JSONL inteiro):

```json
{
  "generation": "copiar generation do manifest.json",
  "expected_count": 1,
  "updates": [
    {
      "id": "copiar id exato da entrada",
      "source_fingerprint": "copiar source_fingerprint da entrada",
      "PTBR": "texto que a equipe de tradução traduziu e revisou"
    }
  ]
}
```

Somente esses campos de atualização são aceitos. Os valores de exemplo não são
um payload executável. `--replace` permite uma substituição intencional após
revisão; sem ele, uma tradução já preenchida não é sobrescrita. `--partial`
aceita os itens válidos e lista os rejeitados. IDs duplicados/desconhecidos e
geração incorreta invalidam o payload inteiro. Repetir itens idênticos é inócuo.

É possível editar diretamente só `PTBR` no JSONL; `check` detecta alterações em
campos imutáveis. Nesse caso, o editor é responsável pela gravação segura; use
`apply` para ter journal, aplicação parcial e proteção contra sobreposição.
Campo vazio continua pendente. Inglês deliberadamente mantido deve ser escrito
explicitamente em PTBR e revisto, sem preenchimento automático.

## Recuperação, espaço e retenção

Cada operação adquire um lock exclusivo. O journal é copy-on-write: faz backup
somente dos arquivos alterados e prepara novos bytes antes da promoção.
Um apply de uma linha não duplica o corpus nem regrava manifesto ou lotes
inalterados. O source-sync e o build podem precisar de um snapshot do binário
de aproximadamente 21 MB. SHA-256 e inventário verificam os membros do journal.

A promoção de vários arquivos é uma **transação recuperável**, não uma promessa
de atomicidade simultânea de múltiplos diretórios pelo sistema operacional.
Um journal pendente bloqueia novas operações; `recover` restaura os valores
anteriores. Se um editor mudou um membro depois da interrupção, a recuperação
recusa sobrescrever e preserva o material para inspeção. Staging interrompido
antes da promoção pode ser descartado depois de verificar o estado original.
`rollback` desfaz a última operação retida, guardando seu próprio journal.
É uma manutenção explícita; não é uma publicação normal de PTBR.

`recover --break-lock` somente remove lock cujo processo foi comprovadamente
encerrado. Um processo ativo continua bloqueando. Nunca apague `.state/` para
contornar uma falha antes de preservar os dados e entender o journal.

Os limites padrão em `config.json` são **10 transações completas, 512 MiB** e
**4 MiB de margem livre**, além do espaço estimado para a transação. O limite de
bytes inclui staging e rollback durante a operação; uma operação que não caiba
falha antes de mudar dados vivos e informa a necessidade. A configuração pode
ser ampliada conscientemente para um jogo/atualização maior.

O GC automático acontece depois de operações verificadas. `gc --dry-run` é
somente leitura e lista IDs, idade e bytes elegíveis. `gc` usa o mesmo lock,
valida recibos/caminhos e só remove snapshots completos mais antigos necessários
ao limite. O snapshot mais recente, journals pendentes, dados corrompidos e
caminhos simbólicos não são descartados. `status` informa contagem, proteção,
bytes, limites e espaço recuperável. `.state/` é recuperação local de curto
prazo; `history/`, manifesto e commits constituem o histórico durável. Não
atribua ao Git mudanças que ainda não foram commitadas.

## Integridade Windows → Git → Ubuntu ARM64

`.gitattributes` determina LF em código/JSON/documentação e `-text` em EN/PTBR
e binários. A cadeia é `engine-shapes.json` → `toolchain.json` →
`runtime-support.json`: toolchain contém hashes de arquivos em modo `git-lf` ou
`binary`, runtime contém o hash canônico de toolchain. Não há dependência cíclica.
EN usa SHA-256 dos bytes nativos. A fixture binária também usa hash bruto.

Uma mudança de CRLF para LF em metadados não quebra os recibos. Uma mudança
real em conteúdo ou no binário quebra. As ferramentas não recalculam recibos
automaticamente para esconder divergências. Após alteração revisada no código,
o desenvolvedor deve atualizar os recibos em ordem e executar os testes.

Verificado no Windows: parsing/reconstrução, no-op binário idêntico, preservação
de objetos não alterados, leitura independente por UnityPy de desenvolvimento,
Unicode em fixture/recurso em memória, transações, aplicação, Git LF, packaging
e mocks HTTP da publicação. Dependências de pesquisa em `.dev-deps/` são locais,
ignoradas e desnecessárias para usar o toolkit. **Não verificados:** execução
real ARM64 e execução real do Actions. A tradução completa e os glifos foram
testados no jogo por Yuri.

## Release automática

`.github/workflows/release.yml` roda em push de `PTBR/**` na branch main e
oferece `workflow_dispatch`. O cliente também verifica a branch padrão canônica,
o SHA exato, árvore rastreada limpa e cabeça atual da branch. Progresso em JSONL,
EN e READMEs não dispara publicação. O workflow não reconstrói o nativo.

`verify-output` compara fontes, JSONL, catálogo, completude, toolchain e hashes
dos arquivos PTBR com o build-manifest. Falha em ausência, staleness, arquivos
extras ou adulteração. Depois, `release.py` cria ZIP determinístico, consulta
Releases publicadas estáveis, verifica ancestralidade e compara bytes nativos.
Primeira publicação: **v1.0.0**; mudanças reais: incremento de patch. Aumento
major/minor exige decisão explícita, fora da automação atual. Tags existentes
nunca são movidas. Drafts, pré-releases e tags soltas não determinam a versão
estável anterior; conflitos são recusados.

A publicação inclui a licença da fonte como asset separado
`CourierPrime-OFL.txt`; o ZIP contém apenas os arquivos nativos. Usa draft
recuperável, upload com hash/size, publicação e nova
consulta para confirmar tag e asset. Retry de GET transitório é limitado;
erros de autenticação/permissão/404 não viram falsos sucessos. Um POST incerto
deve ser repetido pelo workflow para reconciliação do draft, sem criar nova tag
arbitrária. O grupo concurrency serializa os jobs; a cabeça é conferida antes
de publicar para bloquear candidatos antigos. Assets interrompidos divergentes
exigem inspeção do draft, sem substituição silenciosa.

O changelog compara IDs e EN/PTBR versionados e lista recursos nativos alterados,
origem e versão, sem inventar correções ou teste de gameplay. O ZIP permanece na
Release, não apenas num artifact transitório. Somente `contents: write` e o token
do próprio Actions são usados. **Nenhum push, Release ou workflow remoto foi
disparado na preparação.** Os testes executam o cliente HTTP real com transport
simulado, incluindo endpoints, upload, retomada e confirmação.

### Reconciliação dos READMEs após uma Release real

Depois da primeira publicação, ou quando quiser conferir novamente:

```bash
python -B translation-work/toolkit.py docs-status
```

É uma consulta somente leitura à API pública; `GITHUB_TOKEN` é opcional para
repositórios públicos e necessário caso o acesso seja restrito. Sem acesso à
API, o comando informa a falha em vez de inventar uma Release. A checagem usa
os marcadores explícitos `release-state`, sem tentar adivinhar o sentido de
prosa livre. Após publicação confirmada com PTBR.zip, o Actions também aponta
avisos não fatais para documentos marcados como indisponíveis.

O mantenedor deve confirmar tag/asset, contagem real e cobertura; atualizar os dois
READMEs, links de download, estado, versão e créditos; remover afirmações antigas
de indisponibilidade/zero traduções; e trocar o marcador para
`<!-- release-state: available -->`. Preserve as limitações de gameplay enquanto
não houver teste real. Depois da revisão, rode novamente `docs-status`.
O checker nunca edita arquivos ou abre commits/PRs, e um aviso documental nunca
desfaz uma publicação bem-sucedida. Commits só de README não geram outra versão.

## Licença e contribuições

Leia os documentos públicos [LICENSE](../LICENSE),
[GAME-DEVELOPER-PERMISSION.md](../GAME-DEVELOPER-PERMISSION.md) e
[CONTRIBUTING.md](../CONTRIBUTING.md). O arquivo LICENSE é o código jurídico
oficial completo CC BY-NC-SA 4.0, obtido da Creative Commons. O documento adicional
em inglês concede somente os direitos detidos para integração oficial comercial
com créditos. O template externo citado pelo prompt não veio no anexo; o texto
foi redigido com todas as seções e limitações exigidas, sem alegar verificação de
um modelo externo ausente. A Creative Commons não recomenda suas licenças para
software; não há aplicação de licença distinta inventada pelo toolkit nem
relicenciamento de dependências de terceiros.

O PR template parte desmarcado. O consent checker compara declaração, identidade,
PR e registro durável de escopo. O workflow executa o verificador da **base
confiável**, sem secrets nem execução do código do candidato. O mantenedor deve
exigir o check e revisar os direitos antes de merge; configurar proteção de
branch remota não foi parte desta execução. Nenhum consentimento foi fabricado.
Documentos de licença não entram em PTBR.zip.

## Testes

```bash
python -B -m unittest discover -s translation-work/tests -v
python -B translation-work/toolkit.py doctor --local
python -B translation-work/toolkit.py check
git diff --check
```

A regressão de armazenamento executa 500 applies consecutivos sobre uma fixture
de 1.001 registros em 101 lotes de dez, verifica cópias apenas do lote afetado,
mtimes preservados e limites de bytes/quantidade. O tamanho padrão de 500 por
lote é testado separadamente. Fixtures têm dados sintéticos; elas não preenchem
o PT-BR real nem geram um pacote parcial do jogo. Consulte o relatório de
engenharia para resultados medidos e os limites da verificação independente.
