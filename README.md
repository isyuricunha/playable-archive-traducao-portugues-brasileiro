<div align="center">
<a href="https://store.steampowered.com/app/5356470/Playable_Archive/">
  <img src="https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/5356470/3e3dd7a994a836e1d4402e10821822658e4fba76/header.jpg" alt="Arte oficial de Playable Archive na Steam" width="650">
</a>

<h1>Playable Archive</h1>
<p><strong>🇧🇷 Tradução para Português Brasileiro</strong></p>
<p><em>Entre fitas e símbolos, nem toda descoberta deve atravessar o limiar.</em></p>
<p>
  <a href="https://store.steampowered.com/app/5356470/Playable_Archive/">🎮 Steam</a> ·
  <a href="https://github.com/isyuricunha/playable-archive-traducao-portugues-brasileiro/releases">📦 Releases</a> ·
  <a href="https://traducao.yuricunha.com/">🌐 Portal de traduções</a>
</p>
</div>

> **Tradução para PT-BR concluída, com textos e glifos testados em jogo.**
> O pacote de instalação é publicado automaticamente pelo GitHub Actions
> na [página de Releases](https://github.com/isyuricunha/playable-archive-traducao-portugues-brasileiro/releases).

## 🕯️ Sobre a tradução

Um arquivo anônimo, gravações domésticas e um objeto encontrado durante uma
reforma: Playable Archive transforma a curiosidade em parte do perigo. O projeto
leva ao português brasileiro os textos das tabelas de localização
identificadas no jogo, mantendo o ritmo das conversas, o peso dos documentos e
a clareza das instruções.

A base é o inglês original. A tradução abrange falas, legendas, interface,
interações, descrições de objetos, cartas e outros textos de leitura, sem
substituir a dublagem ou o áudio. Os textos e glifos foram validados em jogo.

## 📼 Um arquivo que não deveria ser aberto

Na apresentação oficial, um denunciante anônimo entrega material ligado a
acontecimentos inexplicáveis. Um casal encontra algo durante a reforma de uma
casa na região de New England; os registros envolvem rituais, contato com os
mortos e diferentes linhas temporais. A própria exposição aos símbolos faz parte
da ameaça descrita pela narrativa.

Nos textos do jogo, o cotidiano de Daniel e Jessica divide espaço com a
investigação de Lamar e Dresden, anotações pessoais e instruções sobre objetos
ocultos. As fitas e os documentos pedem atenção a pequenos detalhes: uma palavra
numa etiqueta pode reaparecer como pista, comando ou referência numa conversa.

O jogo foi desenvolvido pela **DarkStone Digital** e publicado pela **DreadXP**.
A [descrição oficial na Steam](https://store.steampowered.com/app/5356470/Playable_Archive/)
informa uma experiência de aproximadamente 30–60 minutos, sem sistema de
salvamento, para jogar em uma sessão. A tradução não altera esse funcionamento.

## 📦 Downloads e versões

Consulte a [página de Releases](https://github.com/isyuricunha/playable-archive-traducao-portugues-brasileiro/releases)
para baixar **PTBR.zip** da versão compatível com sua instalação. O pacote é
montado automaticamente pelo GitHub Actions a partir dos arquivos da tradução,
com histórico de alterações e instruções em cada Release.

**Importante:** os downloads “Source code” disponibilizados pelo GitHub não são
pacotes de instalação. Se ainda não houver uma Release com **PTBR.zip**, o
download da tradução não está disponível nessa página.

## 🛠️ Como instalar

O pacote completo foi testado em jogo, incluindo os caracteres acentuados.

1. Feche o jogo. Na Steam, abra **Gerenciar → Explorar arquivos locais**.
2. Faça uma cópia de segurança de `Playable Archive_Data/resources.assets` e
   `Playable Archive_Data/sharedassets0.assets` em uma pasta fora da instalação.
3. Baixe `PTBR.zip` de uma Release compatível com sua versão do jogo.
4. Extraia o conteúdo do ZIP na pasta que contém `Playable Archive.exe`,
   mantendo as subpastas e confirmando a substituição do arquivo correspondente.
5. Mantenha o idioma do jogo em **inglês**: o pacote substituirá os textos dessa
   coluna pelo PT-BR. Confira menus, legendas, documentos e caracteres acentuados.

O conteúdo do ZIP segue esta estrutura:

```text
Playable Archive_Data/
├── resources.assets
└── sharedassets0.assets
```

Na instalação, o resultado será:

```text
Playable Archive/
├── Playable Archive.exe
└── Playable Archive_Data/
    ├── resources.assets
    └── sharedassets0.assets
```

Não crie uma pasta `PTBR` dentro do jogo. Os demais arquivos da instalação são
necessários e devem continuar presentes; o pacote não é uma cópia completa do jogo.

### Remover ou restaurar

Com o jogo fechado, restaure seus backups de `resources.assets` e
`sharedassets0.assets`. A verificação de
integridade da Steam também pode restaurar os arquivos originais, mas pode
substituir outras modificações. Uma atualização do jogo pode sobrescrever a
tradução: confira a compatibilidade da nova Release antes de reinstalar.

## ⚙️ Compatibilidade e ajuda

O levantamento inicial usa a edição **Steam para Windows, build 26137575**, com
Unity 6000.0.72f1. A reconstrução dos dados foi verificada tecnicamente no Windows;
a tradução completa e os glifos foram testados em jogo. Não há comprovação de compatibilidade com mods ou outras
edições. A tradução não exige alteração de executáveis.

<details>
<summary>O texto continua em inglês</summary>

Confirme que instalou o `PTBR.zip` de uma Release, que o arquivo foi extraído na
pasta correta e que o idioma selecionado é inglês. Textos fora do escopo das
tabelas podem continuar em inglês. Relate a tela e a frase para avaliação.

</details>

<details>
<summary>Acentos ausentes, texto cortado ou erro ao iniciar</summary>

Restaure o backup antes de continuar. Informe a versão do jogo, a Release da
tradução e o trecho/tela afetado nas Issues. Se possível, inclua uma captura
recortada. A fonte do menu exibiu Ç e Õ corretamente no teste; o suporte das
outras fontes aos caracteres portugueses ainda precisa ser verificado no jogo.

</details>

<details>
<summary>O jogo foi atualizado</summary>

Não misture recursos de versões diferentes. Restaure os originais atualizados
e aguarde um pacote correspondente. O histórico de cada Release indicará a
origem utilizada e as mudanças nos textos e arquivos.

</details>

## 💬 Comunidade e contribuições

Use as [Issues do projeto](https://github.com/isyuricunha/playable-archive-traducao-portugues-brasileiro/issues)
para relatar problemas ou sugerir melhorias. Contribuições de texto precisam
seguir [CONTRIBUTING.md](CONTRIBUTING.md), incluindo autorização expressa e
registro dos créditos. Não presumimos consentimento de quem apenas comenta ou
abre um pedido de revisão.

## 🌐 Mais traduções e apoio

Conheça outros projetos no [Portal de Traduções](https://traducao.yuricunha.com/).
Se quiser apoiar voluntariamente o trabalho, a chave **Pix é
`pix@yuricunha.com`**. A contribuição é opcional e não compra acesso à tradução.

## 📜 Licença

O conteúdo original da tradução e da documentação sobre o qual os responsáveis
têm direitos segue a [CC BY-NC-SA 4.0](LICENSE)
([resumo oficial](https://creativecommons.org/licenses/by-nc-sa/4.0/)):
**BY**, dar os devidos créditos e indicar mudanças; **NC**, reutilização não
comercial; **SA**, compartilhar adaptações sob a mesma licença ou uma licença
compatível autorizada.

Existe uma [autorização adicional gratuita para integração oficial](GAME-DEVELOPER-PERMISSION.md),
inclusive em versões comerciais do jogo, com créditos à tradução. Ela cobre
somente direitos efetivamente detidos ou expressamente autorizados pelos
contribuidores. Não significa que a desenvolvedora ou editora tenha aceitado
ou incorporado o projeto.

O inglês original, executáveis, áudio, imagens, marcas e outros recursos
proprietários continuam pertencendo aos respectivos titulares. A licença deste
projeto não concede direitos sobre esses materiais nem transforma um arquivo
nativo que os contém em conteúdo integralmente Creative Commons. Permissões de
distribuição dos recursos do jogo são uma questão distinta. As condições de
contribuição estão em [CONTRIBUTING.md](CONTRIBUTING.md).

## 🤝 Créditos

- **Coordenação e manutenção:** [Yuri Cunha](https://github.com/isyuricunha).
- **Jogo original:** DarkStone Digital; publicação: DreadXP.
- **Fonte do menu:** Courier Prime, de Alan Dague-Greene e Courier Prime Project
  Authors, sob [SIL Open Font License 1.1](translation-work/vendor/courier-prime/OFL.txt).
- **Localização PT-BR:** tradução concluída e testada em jogo.
  Novos colaboradores serão creditados conforme as contribuições efetivamente
  realizadas e autorizadas.

Este é um projeto independente de tradução de fãs, sem vínculo oficial anunciado.

<div align="center">
<p><em>Uma fita de cada vez. Cada palavra no seu lugar.</em></p>
<a href="https://traducao.yuricunha.com/">Portal de Traduções • Yuri Cunha</a>
</div>
