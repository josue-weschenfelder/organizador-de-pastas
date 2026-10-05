# Organizador de Pastas

Pequeno utilitário para **Windows** que observa uma pasta e, sempre que você cria uma nova pasta dentro dela, abre uma janela pedindo o **nome do cliente** e o **número do atendimento/projeto**. Em seguida ele organiza tudo automaticamente:

```
Pasta observada\
└── Nome do Cliente\
    └── 12345\        <- a pasta que você criou é movida para cá
        └── Levantamento.txt
```

Feito em Python, sem dependências externas (só a biblioteca padrão e o tkinter).

## Como funciona

1. Na primeira execução, o programa pede para você escolher a pasta que será observada e salva a escolha em `config.json`.
2. A cada 2 segundos ele verifica a pasta. Pastas que já existiam são ignoradas.
3. Ao detectar uma pasta nova (por exemplo, "Nova pasta"), abre uma janela com dois campos: cliente e atendimento/projeto.
4. Ao confirmar, a pasta nova é movida para `Cliente\Atendimento`. Se a pasta do cliente já existir, apenas a subpasta é criada dentro dela.
5. Dentro da pasta do atendimento é criado o arquivo `Levantamento.txt` com um cabeçalho (cliente, atendimento e data). Se o arquivo já existir, ele não é sobrescrito.

### Detalhes tratados

- Caracteres inválidos no Windows (`\ / : * ? " < > |`) são substituídos por `_`.
- Se o atendimento já existir para aquele cliente, o erro é exibido e você pode corrigir.
- Se o Explorer ainda estiver com a pasta em modo de renomear, o programa tenta mover novamente algumas vezes.
- Se você cancelar a janela, a pasta permanece como estava.
- Se o nome digitado para o cliente for igual ao da pasta nova, o programa lida com o conflito automaticamente.

### Personalizar o Levantamento.txt

O nome do arquivo está na constante `ARQUIVO_LEVANTAMENTO` e o conteúdo inicial na função `criar_levantamento`, ambos em `organizador_pastas.py`. Para criar o arquivo vazio, basta deixar `cabecalho = ""`.

## Requisitos

- Windows 10 ou 11
- [Python 3.9+](https://www.python.org/downloads/) (com tkinter, que já vem no instalador padrão)

## Uso

```bash
python organizador_pastas.py
```

Para rodar sem janela de terminal, use `pythonw`:

```bash
pythonw organizador_pastas.py
```

Para trocar a pasta observada, apague o `config.json` e execute novamente. Há um exemplo do formato em [`config.example.json`](config.example.json).

## Iniciar junto com o Windows

Um serviço do Windows não consegue exibir janelas na sua área de trabalho, por isso o programa roda como um aplicativo em segundo plano iniciado no login:

1. Pressione `Win + R`, digite `shell:startup` e pressione Enter.
2. Coloque nessa pasta um atalho para o `OrganizadorDePastas.exe` (veja abaixo como gerar) ou para `pythonw.exe organizador_pastas.py`.

## Gerar um executável (.exe)

Execute o `build.bat` ou, manualmente:

```bash
pip install -r requirements-dev.txt
pyinstaller --onefile --noconsole --name OrganizadorDePastas organizador_pastas.py
```

O executável será criado em `dist\OrganizadorDePastas.exe`. O `config.json` é salvo ao lado dele.

### Releases automáticas

O repositório tem um workflow do GitHub Actions (`.github/workflows/release.yml`) que compila o `.exe` e o anexa a uma release sempre que uma tag de versão é enviada:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Em poucos minutos a release aparece na aba **Releases** com o `OrganizadorDePastas.exe` e um arquivo `.sha256` para conferir a integridade do download.

### Solução de problemas

**`PermissionError: [WinError 5] Acesso negado` ao gerar o .exe**

O Windows está impedindo o PyInstaller de substituir o `.exe` anterior. Verifique:

- O programa pode estar rodando em segundo plano. Finalize `OrganizadorDePastas.exe` no Gerenciador de Tarefas (o `build.bat` já tenta fazer isso).
- Se o projeto estiver dentro do OneDrive, o OneDrive ou o antivírus podem travar o arquivo. Mova o projeto para uma pasta fora dele (ex.: `C:\dev\organizador-de-pastas`) e tente novamente.
- Apague manualmente as pastas `dist` e `build` e rode o build outra vez.

## Limitações

- A detecção é feita por verificação periódica (a cada 2 segundos), não por eventos do sistema de arquivos. É simples e confiável, mas há um pequeno atraso.
- Apenas pastas criadas diretamente na pasta observada são consideradas (subpastas não disparam a janela).
- Testado apenas no Windows.

## Contribuindo

Contribuições são bem-vindas! Abra uma *issue* para relatar problemas ou sugerir melhorias, ou envie um *pull request*.

Ideias para o futuro:

- Ícone na bandeja do sistema (pausar/sair)
- Modelo de conteúdo configurável para o `Levantamento.txt`
- Modelo de subpastas padrão (ex.: `Documentos`, `Fotos`)
- Intervalo de verificação configurável
- Instalador

## Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).
