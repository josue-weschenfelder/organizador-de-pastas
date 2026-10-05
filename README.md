# Organizador de Pastas

Pequeno utilitário para **Windows** que observa uma pasta e, sempre que você cria uma nova pasta dentro dela, abre uma janela pedindo o **nome do cliente** e o **número do atendimento/projeto**. Em seguida ele organiza tudo automaticamente:

```
Pasta observada\
└── Nome do Cliente\
    └── 12345\        <- a pasta que você criou é movida para cá
        └── Levantamento.txt
```

Feito em Python com tkinter. Fica na bandeja do sistema, ao lado do relógio.

## Como funciona

1. Na primeira execução, o programa pede para você escolher a pasta que será observada e salva a escolha em `config.json`.
2. A cada 2 segundos ele verifica a pasta. Pastas que já existiam são ignoradas.
3. Ao detectar uma pasta nova (por exemplo, "Nova pasta"), abre uma janela com dois campos: cliente e atendimento/projeto.
4. Ao confirmar, a pasta nova é movida para `Cliente\Atendimento`. Se a pasta do cliente já existir, apenas a subpasta é criada dentro dela.
5. Dentro da pasta do atendimento é criado o `Levantamento.txt` a partir de um modelo editável. Se o arquivo já existir, ele não é sobrescrito.

### Ícone na bandeja

Clique com o botão direito no ícone (uma pasta amarela, ou cinza quando pausado) para:

- **Pausar monitoramento**: enquanto pausado, nada dispara a janela. Pastas criadas durante a pausa são ignoradas ao retomar.
- **Abrir pasta observada** (também abre com duplo clique no ícone).
- **Editar modelo do Levantamento.txt**.
- **Iniciar com o Windows**: liga ou desliga a inicialização automática, sem precisar mexer na pasta `shell:startup`.
- **Sair**.

### Modelo do Levantamento.txt

Na primeira execução é criado o arquivo `modelo_levantamento.txt` ao lado do programa. Edite-o como quiser; os campos abaixo são substituídos automaticamente:

| Campo | Valor |
|---|---|
| `{cliente}` | Nome do cliente informado |
| `{atendimento}` | Número do atendimento/projeto informado |
| `{data}` | Data atual (ex.: 05/10/2026) |
| `{hora}` | Hora atual (ex.: 14:30) |

Exemplo:

```
Levantamento - {cliente}
Atendimento: {atendimento}
Aberto em {data} às {hora}

Descrição do problema:

Requisitos:
```

Para criar o arquivo vazio, deixe o modelo em branco. Para trocar o nome do arquivo gerado, altere a constante `ARQUIVO_LEVANTAMENTO` em `organizador_pastas.py`.

### Detalhes tratados

- Caracteres inválidos no Windows (`\ / : * ? " < > |`) são substituídos por `_`.
- Pastas de sistema, ocultas, ou que começam com `$` ou `.` (como `$RECYCLE.BIN`) são ignoradas e nunca disparam a janela.
- Só uma cópia do programa roda por vez. Se você abrir de novo, aparece um aviso.
- Se o atendimento já existir para aquele cliente, o erro é exibido e você pode corrigir.
- Se o Explorer ainda estiver com a pasta em modo de renomear, o programa tenta mover novamente algumas vezes.
- Se você cancelar a janela, a pasta permanece como estava.
- Se o nome digitado para o cliente for igual ao da pasta nova, o programa lida com o conflito automaticamente.

## Download

Baixe o `OrganizadorDePastas.exe` na aba [Releases](../../releases), coloque em uma pasta de sua preferência e execute. O Windows SmartScreen pode avisar que o arquivo não é reconhecido (ele não é assinado digitalmente): clique em **Mais informações** e depois em **Executar assim mesmo**. Se preferir, confira o código-fonte e compile você mesmo.

## Executando pelo código-fonte

Requisitos: Windows 10 ou 11 e [Python 3.9+](https://www.python.org/downloads/) (com tkinter, que já vem no instalador padrão).

```bash
pip install -r requirements.txt
python organizador_pastas.py
```

Para rodar sem janela de terminal, use `pythonw organizador_pastas.py`.

Para trocar a pasta observada, apague o `config.json` e execute novamente. Há um exemplo do formato em [`config.example.json`](config.example.json).

Sem o `pystray` e o `Pillow` instalados o programa ainda funciona, mas sem o ícone na bandeja (e, portanto, sem o menu).

## Iniciar junto com o Windows

Clique com o botão direito no ícone da bandeja e marque **Iniciar com o Windows**. O programa registra a si mesmo para iniciar no seu login (sem exigir administrador). Se você mover o `.exe` para outra pasta, o caminho é atualizado na próxima vez que ele for aberto.

> Um serviço do Windows não consegue exibir janelas na sua área de trabalho, por isso o programa roda como um aplicativo em segundo plano iniciado no login.

## Gerar um executável (.exe)

Execute o `build.bat` ou, manualmente:

```bash
pip install -r requirements-dev.txt
pyinstaller --onefile --noconsole --name OrganizadorDePastas --hidden-import pystray._win32 organizador_pastas.py
```

O executável será criado em `dist\OrganizadorDePastas.exe`. O `config.json` e o `modelo_levantamento.txt` ficam ao lado dele.

### Releases automáticas

O repositório tem um workflow do GitHub Actions (`.github/workflows/release.yml`) que compila o `.exe` e o anexa a uma release sempre que uma tag de versão é enviada:

```bash
git tag v1.1.0
git push origin v1.1.0
```

Em poucos minutos a release aparece na aba **Releases** com o `OrganizadorDePastas.exe` e um arquivo `.sha256` para conferir a integridade do download.

### Solução de problemas

**`PermissionError: [WinError 5] Acesso negado` ao gerar o .exe**

O Windows está impedindo o PyInstaller de substituir o `.exe` anterior. Verifique:

- O programa pode estar rodando em segundo plano. Use **Sair** no ícone da bandeja ou finalize `OrganizadorDePastas.exe` no Gerenciador de Tarefas (o `build.bat` já tenta fazer isso).
- Se o projeto estiver dentro do OneDrive, o OneDrive ou o antivírus podem travar o arquivo. Mova o projeto para uma pasta fora dele (ex.: `C:\dev\organizador-de-pastas`) e tente novamente.
- Apague manualmente as pastas `dist` e `build` e rode o build outra vez.

**O ícone não aparece na bandeja**

O Windows pode esconder o ícone na seta "Mostrar ícones ocultos" ao lado do relógio. Arraste-o para a barra para fixá-lo. Se for rodar pelo código-fonte, confirme que executou `pip install -r requirements.txt`.

## Limitações

- A detecção é feita por verificação periódica (a cada 2 segundos), não por eventos do sistema de arquivos. É simples e confiável, mas há um pequeno atraso.
- Apenas pastas criadas diretamente na pasta observada são consideradas (subpastas não disparam a janela).
- Testado apenas no Windows.

## Contribuindo

Contribuições são bem-vindas! Abra uma *issue* para relatar problemas ou sugerir melhorias, ou envie um *pull request*.

Ideias para o futuro:

- Autocompletar o cliente com as pastas já existentes
- Subpastas padrão dentro do atendimento (ex.: `Documentos`, `Fotos`)
- Log em arquivo
- Testes automatizados
- Instalador

## Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).
