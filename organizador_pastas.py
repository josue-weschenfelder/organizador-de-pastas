"""
Organizador de pastas (Windows)

Observa uma pasta. Quando uma nova pasta é criada dentro dela, abre uma janela
pedindo o nome do cliente e o número do atendimento/projeto. Depois move a
pasta nova para:  <pasta observada>\\<Cliente>\\<Atendimento>

Dentro da pasta do atendimento também é criado o arquivo Levantamento.txt, a
partir do modelo em modelo_levantamento.txt (que pode ser editado).

O programa fica na bandeja do sistema (ícone perto do relógio), de onde é
possível pausar, abrir a pasta, editar o modelo, ativar a inicialização com o
Windows e sair.

Na primeira execução pergunta qual pasta observar e salva em config.json.
Para trocar a pasta depois, apague o config.json.
"""

import json
import os
import queue
import re
import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:  # sem as dependências o programa roda, só que sem ícone na bandeja
    pystray = None

try:
    import winreg  # só existe no Windows
except ImportError:
    winreg = None

NOME_APP = "Organizador de Pastas"
INTERVALO_MS = 2000  # de quanto em quanto tempo verifica a pasta
FILA_MS = 200  # de quanto em quanto tempo processa os cliques do menu da bandeja
ARQUIVO_LEVANTAMENTO = "Levantamento.txt"  # criado dentro da pasta do atendimento

BASE_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
MODELO_FILE = BASE_DIR / "modelo_levantamento.txt"
INVALIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Modelo usado na primeira execução. Campos: {cliente} {atendimento} {data} {hora}
MODELO_PADRAO = (
    "Cliente: {cliente}\n"
    "Atendimento: {atendimento}\n"
    "Data: {data}\n"
    + "-" * 40
    + "\n\n"
)

# Pastas que nunca devem disparar a janela (lixeira, pastas de sistema, ocultas...)
IGNORAR_NOMES = {"system volume information", "recycler", "msocache"}
ATRIBUTO_OCULTO_OU_SISTEMA = 0x2 | 0x4  # FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM

# Inicialização com o Windows (registro do usuário atual, não exige administrador)
CHAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOME_VALOR_RUN = "OrganizadorDePastas"

# Mantém o handle do mutex vivo enquanto o programa roda (instância única)
_mutex = None


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def limpar_nome(nome: str) -> str:
    """Remove caracteres proibidos no Windows e espaços/pontos nas pontas."""
    return INVALIDOS.sub("_", nome).strip(" .")


def instancia_unica() -> bool:
    """Retorna False se já houver outra cópia do programa rodando (Windows)."""
    global _mutex
    if os.name != "nt":
        return True
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    _mutex = kernel32.CreateMutexW(None, False, "Local\\OrganizadorDePastas_instancia_unica")
    return ctypes.get_last_error() != 183  # 183 = ERROR_ALREADY_EXISTS


def abrir_no_explorer(caminho: Path):
    try:
        os.startfile(caminho)  # type: ignore[attr-defined]  # só existe no Windows
    except (AttributeError, OSError) as erro:
        messagebox.showerror(NOME_APP, f"Não foi possível abrir:\n{caminho}\n\n{erro}")


# --------------------------------------------------------------------------- #
# Configuração e pasta observada
# --------------------------------------------------------------------------- #
def carregar_pasta_observada() -> Path:
    if CONFIG_FILE.exists():
        try:
            pasta = Path(json.loads(CONFIG_FILE.read_text(encoding="utf-8"))["pasta_observada"])
            if pasta.is_dir():
                return pasta
        except (OSError, KeyError, ValueError):
            pass
    escolhida = filedialog.askdirectory(title="Escolha a pasta que será observada")
    if not escolhida:
        sys.exit(0)
    CONFIG_FILE.write_text(
        json.dumps({"pasta_observada": escolhida}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return Path(escolhida)


def deve_ignorar(entrada: os.DirEntry) -> bool:
    nome = entrada.name
    if nome.startswith(("$", ".")) or nome.casefold() in IGNORAR_NOMES:
        return True
    try:
        atributos = getattr(entrada.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(atributos & ATRIBUTO_OCULTO_OU_SISTEMA)


def listar_pastas(raiz: Path) -> set[str]:
    try:
        return {e.name for e in os.scandir(raiz) if e.is_dir() and not deve_ignorar(e)}
    except OSError:
        return set()


# --------------------------------------------------------------------------- #
# Modelo do Levantamento.txt
# --------------------------------------------------------------------------- #
def garantir_modelo():
    """Cria o modelo padrão na primeira execução."""
    if not MODELO_FILE.exists():
        try:
            MODELO_FILE.write_text(MODELO_PADRAO, encoding="utf-8")
        except OSError:
            pass


def ler_modelo() -> str:
    try:
        return MODELO_FILE.read_text(encoding="utf-8-sig")
    except OSError:
        return MODELO_PADRAO


def renderizar_modelo(modelo: str, cliente: str, atendimento: str) -> str:
    agora = datetime.now()
    return (
        modelo.replace("{cliente}", cliente)
        .replace("{atendimento}", atendimento)
        .replace("{data}", f"{agora:%d/%m/%Y}")
        .replace("{hora}", f"{agora:%H:%M}")
    )


# --------------------------------------------------------------------------- #
# Inicialização com o Windows
# --------------------------------------------------------------------------- #
def comando_inicializacao() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interpretador = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{interpretador}" "{Path(__file__).resolve()}"'


def valor_autostart():
    """Comando registrado para iniciar com o Windows, ou None se não estiver ativo."""
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_RUN) as chave:
            return winreg.QueryValueEx(chave, NOME_VALOR_RUN)[0]
    except OSError:
        return None


def autostart_ativo() -> bool:
    return valor_autostart() is not None


def definir_autostart(ativar: bool):
    if winreg is None:
        raise RuntimeError("A inicialização com o Windows só está disponível no Windows.")
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_RUN, 0, winreg.KEY_SET_VALUE) as chave:
        if ativar:
            winreg.SetValueEx(chave, NOME_VALOR_RUN, 0, winreg.REG_SZ, comando_inicializacao())
        else:
            try:
                winreg.DeleteValue(chave, NOME_VALOR_RUN)
            except FileNotFoundError:
                pass


# --------------------------------------------------------------------------- #
# Ícone da bandeja
# --------------------------------------------------------------------------- #
def criar_imagem_icone(ativo: bool = True):
    """Desenha um ícone de pasta (amarelo = observando, cinza = pausado)."""
    frente, fundo = ((245, 190, 50, 255), (200, 140, 20, 255)) if ativo else (
        (160, 160, 160, 255),
        (115, 115, 115, 255),
    )
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 10, 28, 26), radius=4, fill=fundo)  # aba
    d.rounded_rectangle((4, 18, 60, 54), radius=6, fill=frente)  # corpo
    return img


# --------------------------------------------------------------------------- #
# Janela de entrada
# --------------------------------------------------------------------------- #
class DialogoCliente:
    """Janela que pede cliente e atendimento. Retorna (cliente, atendimento) ou None."""

    def __init__(self, root, nome_pasta, cliente="", atendimento=""):
        self.resultado = None
        self.win = tk.Toplevel(root)
        self.win.title("Nova pasta detectada")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)

        frm = ttk.Frame(self.win, padding=16)
        frm.grid()
        ttk.Label(frm, text=f"Pasta detectada: {nome_pasta}", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        ttk.Label(frm, text="Nome do cliente:").grid(row=1, column=0, sticky="w", pady=4)
        self.e_cliente = ttk.Entry(frm, width=36)
        self.e_cliente.grid(row=1, column=1, pady=4, padx=(8, 0))
        self.e_cliente.insert(0, cliente)

        ttk.Label(frm, text="Nº do atendimento/projeto:").grid(row=2, column=0, sticky="w", pady=4)
        self.e_atend = ttk.Entry(frm, width=36)
        self.e_atend.grid(row=2, column=1, pady=4, padx=(8, 0))
        self.e_atend.insert(0, atendimento)

        botoes = ttk.Frame(frm)
        botoes.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(botoes, text="Cancelar", command=self.cancelar).pack(side="right", padx=(8, 0))
        ttk.Button(botoes, text="Criar", command=self.confirmar).pack(side="right")

        self.win.bind("<Return>", lambda _e: self.confirmar())
        self.win.bind("<Escape>", lambda _e: self.cancelar())
        self.win.protocol("WM_DELETE_WINDOW", self.cancelar)

        self.win.update_idletasks()
        w, h = self.win.winfo_width(), self.win.winfo_height()
        x = (self.win.winfo_screenwidth() - w) // 2
        y = (self.win.winfo_screenheight() - h) // 3
        self.win.geometry(f"+{x}+{y}")
        self.win.lift()
        self.win.focus_force()
        (self.e_cliente if not cliente else self.e_atend).focus_set()
        self.win.grab_set()

    def confirmar(self):
        cliente = limpar_nome(self.e_cliente.get())
        atendimento = limpar_nome(self.e_atend.get())
        if not cliente or not atendimento:
            messagebox.showwarning("Campos obrigatórios", "Informe o cliente e o atendimento.", parent=self.win)
            return
        self.resultado = (cliente, atendimento)
        self.win.destroy()

    def cancelar(self):
        self.resultado = None
        self.win.destroy()

    def mostrar(self):
        self.win.wait_window()
        return self.resultado


# --------------------------------------------------------------------------- #
# Aplicação
# --------------------------------------------------------------------------- #
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        if not instancia_unica():
            messagebox.showinfo(
                NOME_APP,
                "O programa já está em execução.\nProcure o ícone na bandeja do sistema (perto do relógio).",
            )
            sys.exit(0)

        self.pasta = carregar_pasta_observada()
        garantir_modelo()
        self.conhecidas = listar_pastas(self.pasta)  # pastas que já existiam não disparam nada
        self.pausado = False
        self.ocupado = False  # True enquanto a janela de cliente está aberta
        self.fila: "queue.Queue[str]" = queue.Queue()  # cliques do menu (vêm de outra thread)
        self.icone = None

        self.sincronizar_autostart()
        self.iniciar_bandeja()

        self.root.after(INTERVALO_MS, self.verificar)
        self.root.after(FILA_MS, self.processar_fila)

    # ---- bandeja ---------------------------------------------------------- #
    def titulo_bandeja(self) -> str:
        estado = "pausado" if self.pausado else "observando"
        return f"{NOME_APP} - {estado}"

    def pedir(self, acao: str):
        """Cria o callback do menu. O clique roda em outra thread, então só enfileira."""
        return lambda _icone=None, _item=None: self.fila.put(acao)

    def iniciar_bandeja(self):
        if pystray is None:
            messagebox.showwarning(
                NOME_APP,
                "Os pacotes pystray e Pillow não foram encontrados.\n"
                "O programa vai rodar sem o ícone na bandeja.\n\n"
                "Para instalar:  pip install -r requirements.txt",
            )
            return
        menu = pystray.Menu(
            pystray.MenuItem(lambda _i: f"Observando: {self.pasta}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Pausar monitoramento", self.pedir("pausa"), checked=lambda _i: self.pausado),
            pystray.MenuItem("Abrir pasta observada", self.pedir("abrir_pasta"), default=True),
            pystray.MenuItem("Editar modelo do Levantamento.txt", self.pedir("abrir_modelo")),
            pystray.MenuItem("Iniciar com o Windows", self.pedir("autostart"), checked=lambda _i: autostart_ativo()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", self.pedir("sair")),
        )
        self.icone = pystray.Icon("organizador_pastas", criar_imagem_icone(True), self.titulo_bandeja(), menu)
        self.icone.run_detached()

    def processar_fila(self):
        if not self.ocupado:  # não mexe em nada enquanto a janela de cliente está aberta
            while True:
                try:
                    acao = self.fila.get_nowait()
                except queue.Empty:
                    break
                self.executar(acao)
        self.root.after(FILA_MS, self.processar_fila)

    def executar(self, acao: str):
        if acao == "pausa":
            self.pausado = not self.pausado
            if not self.pausado:
                # o que foi criado durante a pausa não dispara a janela
                self.conhecidas = listar_pastas(self.pasta)
            if self.icone is not None:
                self.icone.icon = criar_imagem_icone(not self.pausado)
                self.icone.title = self.titulo_bandeja()
        elif acao == "abrir_pasta":
            abrir_no_explorer(self.pasta)
        elif acao == "abrir_modelo":
            garantir_modelo()
            abrir_no_explorer(MODELO_FILE)
        elif acao == "autostart":
            try:
                definir_autostart(not autostart_ativo())
            except Exception as erro:
                messagebox.showerror(NOME_APP, f"Não foi possível alterar a inicialização:\n{erro}")
        elif acao == "sair":
            if self.icone is not None:
                self.icone.stop()
            self.root.quit()

    def sincronizar_autostart(self):
        """Se a inicialização está ativa mas o programa mudou de lugar, atualiza o caminho."""
        try:
            valor = valor_autostart()
            if valor is not None and valor != comando_inicializacao():
                definir_autostart(True)
        except Exception:
            pass

    # ---- monitoramento ---------------------------------------------------- #
    def verificar(self):
        if not self.pausado:
            novas = sorted(listar_pastas(self.pasta) - self.conhecidas)
            if novas:
                self.ocupado = True
                try:
                    for nome in novas:
                        self.tratar_nova_pasta(nome)
                finally:
                    self.ocupado = False
            # atualiza depois do tratamento para incluir a pasta do cliente recém-criada
            self.conhecidas = listar_pastas(self.pasta)
        self.root.after(INTERVALO_MS, self.verificar)

    def tratar_nova_pasta(self, nome):
        cliente, atendimento = "", ""
        while True:
            res = DialogoCliente(self.root, nome, cliente, atendimento).mostrar()
            if res is None:
                return  # cancelado: a pasta fica como está
            cliente, atendimento = res
            try:
                destino = self.mover(nome, cliente, atendimento)
            except Exception as erro:  # mostra o erro e deixa corrigir
                messagebox.showerror("Não foi possível criar", str(erro))
                continue
            try:
                self.criar_levantamento(destino, cliente, atendimento)
            except OSError as erro:
                messagebox.showwarning(
                    "Pasta criada, mas sem o arquivo",
                    f"A pasta foi organizada, porém não foi possível criar {ARQUIVO_LEVANTAMENTO}:\n{erro}",
                )
            return

    @staticmethod
    def criar_levantamento(destino: Path, cliente: str, atendimento: str):
        """Cria o Levantamento.txt a partir do modelo (não sobrescreve se já existir)."""
        arquivo = destino / ARQUIVO_LEVANTAMENTO
        if arquivo.exists():
            return
        conteudo = renderizar_modelo(ler_modelo(), cliente, atendimento)
        # utf-8-sig para o Bloco de Notas exibir acentos corretamente
        arquivo.write_text(conteudo, encoding="utf-8-sig")

    def mover(self, nome, cliente, atendimento) -> Path:
        origem = self.pasta / nome
        pasta_cliente = self.pasta / cliente
        destino = pasta_cliente / atendimento

        if destino.exists():
            raise FileExistsError(f"Já existe: {destino}")

        # Caso o nome digitado seja igual ao da pasta nova, renomeia antes para não conflitar
        temporaria = None
        if nome.casefold() == cliente.casefold():
            temporaria = self.pasta / f"{nome}.__tmp__"
            self.renomear(origem, temporaria)
            origem = temporaria

        try:
            pasta_cliente.mkdir(exist_ok=True)
            self.renomear(origem, destino)
            return destino
        except Exception:
            if temporaria is not None and temporaria.exists():
                self.renomear(temporaria, self.pasta / nome)
            raise

    @staticmethod
    def renomear(origem: Path, destino: Path, tentativas=5):
        """O Explorer pode estar com a pasta em uso (modo de renomear); tenta algumas vezes."""
        for i in range(tentativas):
            try:
                os.rename(origem, destino)
                return
            except PermissionError:
                if i == tentativas - 1:
                    raise PermissionError(
                        f"A pasta '{origem.name}' está em uso. Feche o Explorer nela e tente de novo."
                    )
                time.sleep(1)

    def rodar(self):
        self.root.mainloop()
        if self.icone is not None:
            self.icone.stop()


if __name__ == "__main__":
    App().rodar()
