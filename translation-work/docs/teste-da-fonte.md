# Teste da fonte do menu

O menu principal usa o TextMeshPro `courier_bold SDF`, apontando para o objeto
`Font` 133 em `Playable Archive_Data/sharedassets0.assets`. Ele usa atlas
dinâmico e contém os bytes da fonte de origem. Foi confirmado no jogo que a
fonte original apresenta `Ç` e `Õ` como outras letras; a investigação revelou
que o próprio arquivo de fonte tem mapeamentos para glifos incorretos.

O teste substitui somente os bytes desse objeto pela **Courier Prime Regular**,
similar à fonte original e com acentos portugueses. O jogo já inclui outra
versão de Courier Prime em seus recursos. Esta cópia vem do Google Fonts e
mantém a licença [SIL OFL 1.1](../vendor/courier-prime/OFL.txt) e os créditos
em [vendor/courier-prime/README.md](../vendor/courier-prime/README.md).

O adaptador experimental é reproduzível com Python padrão no Windows e no Linux.
Seu input deve ser o **original** do build Steam 26137575, SHA-256
`e0a57c03f72d20ebf4f763b466393a894bfe80ef31f547effc2a7a2444827ad7`:

```bash
python -B translation-work/font_patch.py --source "/caminho/sharedassets0.assets" --output "translation-work/.state/menu-test/font-test/Playable Archive_Data/sharedassets0.assets"
```

O comando apenas prepara uma cópia na área local ignorada pelo Git. Verifica o
hash do recurso e da fonte, o objeto nativo, a lista de caracteres PT-BR, a
reconstrução e a reabertura; recusa outros builds ou arquivos modificados.
Ele não instala no jogo e não altera o `PTBR/` de produção.

Para o teste autorizado por Yuri, foram preparados dois recursos: o menu em
`resources.assets`, com **VER ARQUIVO / OPÇÕES / SAIR**, e o recurso de fonte em
`sharedassets0.assets`. O conteúdo dos demais objetos foi preservado e a leitura
independente por UnityPy confirmou que somente o objeto de fonte foi alterado.
Em 26/10/2026, Yuri confirmou numa captura do jogo que **OPÇÕES** aparece com
Ç e Õ legíveis no menu. O teste inicial foi seguido pela validação completa em jogo por Yuri.
Historicamente, o teste do menu não validava outras telas nem todas as
letras acentuadas em runtime.
Backups locais ficam em `translation-work/.state/menu-test/`, fora do Git:
`resources.assets.original` e `sharedassets0.assets.original`. Também foi salvo
`resources.assets.before-font-test` para recuperar o teste anterior com AJUSTES.

Para voltar aos dois arquivos originais, feche o jogo e copie os backups para
`Playable Archive_Data`, removendo o sufixo `.original` dos nomes. Por exemplo,
no PowerShell, a partir da raiz deste repositório:

```powershell
Copy-Item -LiteralPath 'translation-work/.state/menu-test/resources.assets.original' -Destination 'G:/SteamLibrary/steamapps/common/Playable Archive/Playable Archive_Data/resources.assets' -Force
Copy-Item -LiteralPath 'translation-work/.state/menu-test/sharedassets0.assets.original' -Destination 'G:/SteamLibrary/steamapps/common/Playable Archive/Playable Archive_Data/sharedassets0.assets' -Force
```

Enquanto o teste estiver instalado, `update-sources` pode rejeitar a instalação
como modificada. Restaure os dois originais antes de usá-la como fonte inglesa.

Após essa confirmação, o `build` completo inclui automaticamente a fonte em
`PTBR/Playable Archive_Data/sharedassets0.assets`; a Release deve distribuir
o texto OFL como asset separado de `PTBR.zip`. A correção está vinculada ao
hash do build original informado acima: uma atualização incompatível exige
revisão, sem supor que o offset ou a fonte continuam iguais.

Após o teste inicial do menu, Yuri confirmou em 26/10/2026 que a tradução
completa e os glifos funcionam no jogo. As observações offline sobre outras
fontes foram anteriores a essa validação em runtime.
