"""
Organizador de pastas (Windows)

Observa uma pasta. Quando uma nova pasta é criada dentro dela, abre uma janela
pedindo o nome do cliente e o número do atendimento/projeto. Depois move a
pasta nova para:  <pasta observada>\\<Cliente>\\<Atendimento>

Dentro da pasta do atendimento também é criado o arquivo Levantamento.txt.

Na primeira execução pergunta qual pasta observar e salva em config.json.
Para trocar a pasta depois, apague o config.json.
"""

import json
import os
import re
import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

INTERVALO_MS = 2000  # de quanto em quanto tempo verifica a pasta
ARQUIVO_LEVANTAMENTO = "Levantamento.txt"  # criado dentro da pasta do atendimento

BASE_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
INVALIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def limpar_nome(nome: str) -> str:
    """Remove caracteres proibidos no Windows e espaços/pontos nas pontas."""
    return INVALIDOS.sub("_", nome).strip(" .")


def carregar_pasta_observada(root: tk.Tk) -> Path:
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


def listar_pastas(raiz: Path) -> set[str]:
    try:
        return {e.name for e in os.scandir(raiz) if e.is_dir()}
    except OSError:
        return set()


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


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.pasta = carregar_pasta_observada(self.root)
        self.conhecidas = listar_pastas(self.pasta)  # pastas que já existiam não disparam nada
        self.root.after(INTERVALO_MS, self.verificar)

    def verificar(self):
        atuais = listar_pastas(self.pasta)
        for nome in sorted(atuais - self.conhecidas):
            self.tratar_nova_pasta(nome)
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
        """Cria o Levantamento.txt com um cabeçalho simples (não sobrescreve se já existir)."""
        arquivo = destino / ARQUIVO_LEVANTAMENTO
        if arquivo.exists():
            return
        cabecalho = (
            f"Cliente: {cliente}\n"
            f"Atendimento: {atendimento}\n"
            f"Data: {datetime.now():%d/%m/%Y}\n"
            f"{'-' * 40}\n\n"
        )
        # utf-8-sig para o Bloco de Notas exibir acentos corretamente
        arquivo.write_text(cabecalho, encoding="utf-8-sig")

    def mover(self, nome, cliente, atendimento):
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


if __name__ == "__main__":
    App().rodar()
