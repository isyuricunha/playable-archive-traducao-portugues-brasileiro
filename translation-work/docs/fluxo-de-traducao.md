# Fluxo da tradução manual

O briefing já foi pesquisado e escrito. A tradução inicial foi concluída em dois lotes de 250 e 226. Em trabalhos futuros,
leia o briefing e as decisões existentes antes de revisar termos. No servidor,
execute o preflight ARM64 antes de começar. O toolkit não traduz nem aprova termos.

1. `status` / `resume`: encontre a próxima entrada pendente e confira a geração.
2. Leia trechos relacionados pelo prefixo de chave, tabela e contexto do briefing.
3. Traduza e revise um grupo manejável. Neste projeto, os lotes armazenam até
   250 entradas, conforme solicitado por Yuri.
4. Prepare payload com ID, fingerprint e PTBR e aplique por `apply --payload`.
5. Rode `check`, revise rejeições e faça commits de progresso quando apropriado.
   O comando não cria PTBR nem publica uma Release.
6. Numa atualização, rode `update-sources` ou `sync`, veja `diff`, consulte
   `history/` e trabalhe nas entradas adicionadas/invalidadas. Não reescreva
   toda a tradução porque o hash de um arquivo mudou.
7. Ao concluir todas as entradas, revise consistência, termos, instruções e
   marcadores. Rode `check`, depois o `build` explícito e `verify-output`.
8. Encaminhe o resultado para o teste de Yuri no jogo. O sucesso técnico não
   comprova cobertura, glifos ou diagramação. Registre o que foi observado.
9. Somente o usuário ou alguém autorizado faz commit/push do build completo,
   com PTBR e build-manifest juntos. O Actions publica PTBR.zip versionado.
10. Após uma Release real, faça a reconciliação dos READMEs descrita no guia
    técnico, incluindo disponibilidade, contagem, créditos e limitações reais.

`PTBR=""` é pendente. Um nome ou palavra a manter em inglês deve ser
explicitamente escrito e revisado no campo PTBR; isso não é tarefa automática
do toolkit. Nunca edite EN, chave, localizadores ou fingerprints para aceitar
um payload. Nunca copie automaticamente texto entre contextos só porque o inglês
é igual. Em dúvida de sentido, registre a questão no glossário/diretrizes.

Se houver erro de checksum, formato, lock ou fonte incompleta, preserve os
arquivos e encaminhe o diagnóstico. Use `recover` apenas para uma transação
interrompida, e `rollback` para desfazer conscientemente a última operação.
O histórico Git preserva a evolução; journals locais têm retenção limitada.
