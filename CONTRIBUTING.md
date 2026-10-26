# Como contribuir

O projeto é mantido por [Yuri Cunha](https://github.com/isyuricunha).
Relatos de problemas podem ser enviados nas Issues. Informe a versão do jogo,
a versão da tradução e o contexto da frase. Não envie executáveis, saves ou
arquivos inteiros do jogo em uma contribuição de revisão.

## Textos originais e consentimento

Você continua sendo titular da sua contribuição. Para incorporarmos texto
original protegido por direitos autorais, precisamos de autorização expressa:

> Autorizo, de forma não exclusiva e gratuita, o mantenedor a usar, editar,
> adaptar e redistribuir as minhas contribuições originais deste PR sob
> CC BY-NC-SA 4.0 e a conceder à desenvolvedora/editora original do Playable
> Archive a permissão adicional de integração oficial, inclusive comercial,
> descrita em GAME-DEVELOPER-PERMISSION.md, com os devidos créditos, sem novas
> aprovações individuais ou pagamentos. Declaro ter os direitos necessários.

Essa autorização não transfere propriedade nem exige renúncia a direitos
morais inalienáveis. Não envie conteúdo de terceiros sem permissão compatível.
Uma sugestão simples ou relato de bug não é automaticamente tratado como autoria
de texto novo; quando houver dúvida sobre uma contribuição substancial, o
responsável pela revisão deve esclarecer a autorização antes de utilizá-la.

## Registro prático

1. Abra um PR, leia os documentos e marque pessoalmente a declaração do template.
2. Acrescente `translation-work/contributor-consents/PR-NUMERO.json`, com:

```json
{
  "identity": "SEU_LOGIN_GITHUB",
  "pull_request": "URL_REAL_DO_SEU_PR",
  "scope": "original contributions in this pull request",
  "permission": "CC-BY-NC-SA-4.0 + official-game-commercial-integration",
  "affirmative": true
}
```

3. O CI compara a identidade e a URL com o evento real do PR e verifica a
   declaração afirmativa. O registro acompanha as alterações no histórico Git.
4. O revisor confere autoria, escopo, autorização e créditos antes do merge.
   Não pode marcar a declaração nem criar consentimento em nome de outra pessoa.

Não use os valores ilustrativos acima literalmente. Se o PR mudar de escopo,
revise a autorização. Contribuições por outros meios devem vir acompanhadas
da mesma declaração com identidade, data e escopo, preservadas no histórico
e verificadas pelo mantenedor. Sem autorização registrada, o texto fica fora
do pacote e da permissão de integração oficial. Incompatibilidades de direitos
devem ser resolvidas antes do merge, sem presumir consentimento.

## Tradução e validação

Consulte o guia em `translation-work/README.md`. Os originais são imutáveis;
traduza somente `PTBR` nos JSONL. Prefira o comando `apply`, preserve marcadores
e valide antes de enviar. Nunca inclua mudanças de progresso em `PTBR/`: essa
pasta é reservada ao build completo. Contribuições documentais também devem
preservar fontes, créditos e a distinção entre fatos e interpretações.
