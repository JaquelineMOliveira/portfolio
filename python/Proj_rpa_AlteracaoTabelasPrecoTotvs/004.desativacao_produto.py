"""
ATIVAR / BLOQUEAR ITENS EM TABELAS DE PREÇO - TOTVS PROTHEUS (WEB)
==================================================================
Fluxo:
  1. Você escolhe a planilha (colunas: Código | Tabela | Ativo  ->  Sim / Não)
  2. Abre manualmente a tabela no Protheus (modo Alterar)
  3. O script sugere a próxima tabela da planilha; você confirma qual está aberta
  4. Você clica numa célula da coluna Cod.Produto -> o script varre o grid UMA vez
  5. Gera/atualiza o arquivo de CONFERÊNCIA na mesma pasta da planilha
  6. Você confere e CONFIRMA manualmente no Protheus -> segue para a próxima tabela

O script NUNCA clica em Confirmar.

Segurança:
  - Só lê/escreve quando a célula atual tem EXATAMENTE 10 dígitos (Cod.Produto)
  - Se sair da coluna, se realinha sozinho (vai até a coluna Item e anda 1 para a direita)
  - Só digita depois de ler e reconhecer o valor da coluna Ativo (Sim/Nao)
  - Depois de digitar, lê de novo para conferir; se não bater, PARA tudo
  - Se a janela ativa mudar (você clicou em outro programa), PARA tudo
  - Mouse no CANTO SUPERIOR ESQUERDO da tela = parada de emergência

Instalação (uma vez):  pip install pyautogui pyperclip pandas openpyxl
"""

import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyautogui
import pyperclip
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================
PASTA_BASE = Path(r"Z:\Alterações de Tabela")   # a pasta do dia (AAAA.MM.DD) é aberta automaticamente se existir

COLUNAS_ATE_ATIVO = 8      # quantas colunas à direita do Cod.Produto fica o "Ativo" (só usado como referência)
MAX_PASSOS_LATERAIS = 14   # máximo de colunas que ele anda procurando o Ativo ou o Cod.Produto
TECLA_TOPO = 'home'        # tecla que leva ao topo da lista
MAX_LINHAS = 3000          # limite de segurança da varredura

# Tempos (segundos). Se o Protheus estiver lento e der erro de leitura, aumente um pouco.
PAUSA_TECLA = 0.25         # entre setas laterais (o grid rola de lado e precisa de tempo)
PAUSA_DESCER = 0.06        # depois de cada seta para baixo
PAUSA_APOS_DIGITAR = 0.5   # depois de digitar 1/2 no campo Ativo
ESPERAS_LEITURA = (0.05, 0.12, 0.25, 0.5)   # tentativas de leitura (cada uma espera mais)


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0        # o padrão (0,1s após CADA comando) era o maior motivo da lentidão

# Exibido S/N no grid, digitado 1/2
VALOR_PARA_CODIGO = {"SIM": "1", "S": "1", "1": "1",
                     "NAO": "2", "N": "2", "2": "2"}
CODIGO_PARA_TEXTO = {"1": "Sim", "2": "Não"}
ACAO = {"1": "ATIVAR", "2": "BLOQUEAR"}


class ProcessoParado(Exception):
    pass


# ==========================================================
# UTILITÁRIOS
# ==========================================================
def normalizar(txt) -> str:
    """'Não ' -> 'NAO'"""
    txt = "" if txt is None or (isinstance(txt, float) and pd.isna(txt)) else str(txt)
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.strip().upper()


def eh_codigo(txt: str) -> bool:
    return bool(re.fullmatch(r"\d{10}", txt or ""))


def contagem(seg: int, msg: str):
    print(msg)
    for i in range(seg, 0, -1):
        print(f"  {i}...", end=" ", flush=True)
        time.sleep(1)
    print()


def janela_ativa():
    try:
        return pyautogui.getActiveWindowTitle() or ""
    except Exception:
        return None          # sistema sem suporte: verificação desligada


def checar_janela(titulo_inicial):
    if titulo_inicial is None:
        return
    atual = janela_ativa()
    if atual is not None and atual != titulo_inicial:
        raise ProcessoParado(f"a janela ativa mudou para '{atual}'.")


# ==========================================================
# LEITURA / NAVEGAÇÃO NO GRID
# ==========================================================
def ler_celula(esperas=ESPERAS_LEITURA) -> str:
    """Copia a célula atual sem alterar nada. Tenta de novo, esperando mais, se vier vazio."""
    for espera in esperas:
        pyperclip.copy("")
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(espera)
        texto = pyperclip.paste().strip()
        if texto:
            return texto
    return ""


def mover(tecla: str, vezes: int, pausa: float = PAUSA_TECLA):
    for _ in range(vezes):
        pyautogui.press(tecla)
        time.sleep(pausa)


def realinhar(cod_esperado: str = None) -> str:
    """
    Volta para a coluna Cod.Produto da LINHA ATUAL lendo célula por célula.
    Anda para a ESQUERDA até ler 10 dígitos. Se a seta para a esquerda não muda nada
    e a célula tem 4 dígitos, está na primeira coluna (Item) -> anda 1 para a direita.
    Não depende de contar teclas, então não se perde se o Protheus engolir uma seta.
    """
    lido = ler_celula()
    for _ in range(MAX_PASSOS_LATERAIS + 3):
        if eh_codigo(lido):
            break
        pyautogui.press('left')
        time.sleep(PAUSA_TECLA)
        novo = ler_celula()
        if novo == lido and re.fullmatch(r"\d{4}", novo):   # parede da esquerda = coluna Item
            pyautogui.press('right')
            time.sleep(PAUSA_TECLA)
            novo = ler_celula()
        lido = novo

    if not eh_codigo(lido):
        raise ProcessoParado(f"não consegui voltar para a coluna Cod.Produto (lido: '{lido}').")
    if cod_esperado and lido != cod_esperado:
        raise ProcessoParado(f"cursor saiu da linha do produto {cod_esperado} (lido: '{lido}').")
    return lido


def voltar_para_codigo(cod: str, passos: int):
    """Volta rápido o número de passos conhecido e depois confirma/ajusta lendo."""
    mover('left', passos)
    time.sleep(0.2)
    return realinhar(cod)


def interpretar_ativo(texto: str):
    """'Sim' / 'Nao' / '1 - Sim' / '2 - Nao' -> '1' ou '2'. Qualquer outra coisa -> None."""
    t = normalizar(texto)
    m = re.fullmatch(r"([12])\s*-\s*(SIM|NAO)", t)
    if m:
        return m.group(1)
    return {"SIM": "1", "S": "1", "NAO": "2", "N": "2"}.get(t)


def ler_ativo(esperas=ESPERAS_LEITURA):
    """Retorna '1', '2' ou None se a célula atual não for o campo Ativo."""
    return interpretar_ativo(ler_celula(esperas))


def ir_para_ativo():
    """
    Sai do Cod.Produto andando UMA coluna por vez e lendo cada célula,
    até encontrar Sim/Nao. Retorna (valor '1'/'2' ou None, passos andados).
    """
    passos = 0
    for _ in range(MAX_PASSOS_LATERAIS):
        pyautogui.press('right')
        time.sleep(PAUSA_TECLA)
        passos += 1
        if passos < COLUNAS_ATE_ATIVO - 2:      # colunas iniciais: só anda, não precisa ler
            continue
        valor = ler_ativo(esperas=(0.08, 0.2, 0.4))
        if valor:
            return valor, passos
    return None, passos


def alterar_item(cod: str, desejado: str, titulo) -> dict:
    """Estando no Cod.Produto do item: acha o Ativo, digita se precisar, confere e volta."""
    antes, passos = ir_para_ativo()

    if antes is None:
        voltar_para_codigo(cod, passos)
        return {"verificacao": "Erro: coluna Ativo não encontrada", "antes": "", "depois": "",
                "parar": True}

    if antes == desejado:
        voltar_para_codigo(cod, passos)
        return {"verificacao": "Já estava assim", "antes": antes, "depois": antes}

    checar_janela(titulo)
    pyautogui.press(desejado)
    time.sleep(PAUSA_APOS_DIGITAR)

    # Conferência: o Protheus pode ter pulado para a direita depois de digitar
    depois = ler_ativo(esperas=(0.1, 0.25))
    for _ in range(3):                      # procura a célula Ativo à esquerda (até 3 colunas)
        if depois is not None:
            break
        pyautogui.press('left'); time.sleep(PAUSA_TECLA)
        depois = ler_ativo()

    voltar_para_codigo(cod, passos)

    if depois != desejado:
        return {"verificacao": f"ERRO: digitado {desejado}, conferência leu '{depois}'",
                "antes": antes, "depois": depois or "", "parar": True}
    return {"verificacao": "Alterado", "antes": antes, "depois": depois}


def ler_com_paciencia(anterior: str, esperas=(0.3, 0.6, 1.0, 1.5)) -> str:
    """Lê de novo, esperando cada vez mais, enquanto vier vazio ou igual ao anterior."""
    novo = ler_celula()
    for espera in esperas:
        if novo and novo != anterior:
            return novo
        time.sleep(espera)
        novo = ler_celula()
    return novo


def confirmar_fim(atual: str) -> bool:
    """
    Só aceita que a lista acabou depois de testar de novo:
    volta uma linha (tem que ler o código anterior), desce de novo e espera.
    Se mesmo assim não aparecer um código novo, é fim de verdade.
    """
    print("  (possível fim da lista, conferindo...)")
    time.sleep(1.5)
    lido = ler_celula()
    if eh_codigo(lido) and lido != atual:
        return False                        # era só lentidão: a linha carregou

    for _ in range(3):                      # linha em branco: sobe para a última linha válida
        if lido != "":
            break
        pyautogui.press('up'); time.sleep(0.8)
        lido = ler_celula()

    if lido != atual:                       # não está onde deveria: realinha e continua
        return False

    pyautogui.press('down'); time.sleep(2.0)
    lido = ler_celula()
    if lido == atual:
        return True
    if lido == "":
        for _ in range(3):                  # tira o cursor da linha em branco
            pyautogui.press('up'); time.sleep(0.8)
            if ler_celula() == atual:
                break
        return True
    return False


def descer(atual: str):
    """
    Desce uma linha. Retorna o novo código ou None se chegou ao fim da lista.
    Se a leitura vier igual ou vazia, primeiro ESPERA (o Protheus pode estar carregando
    o próximo bloco do grid) e só depois tenta de novo - assim não pula nem para antes da hora.
    """
    for _ in range(3):
        pyautogui.press('down')
        time.sleep(PAUSA_DESCER)
        novo = ler_com_paciencia(atual)
        if novo and novo != atual:
            break
    else:
        if confirmar_fim(atual):
            return None
        novo = ler_celula()

    if not eh_codigo(novo):                 # saiu da coluna ou leitura estranha -> realinha
        print(f"  (realinhando: lido '{novo}')")
        novo = realinhar()
    return novo


def varrer(itens: dict, pendentes: set, titulo, resultados: dict, avisar_repetidos: bool):
    """Uma varredura de cima para baixo. Remove de 'pendentes' o que encontrar."""
    pyautogui.press(TECLA_TOPO)
    time.sleep(1.0)
    atual = realinhar()
    linha = 1

    while True:
        checar_janela(titulo)

        if atual in pendentes:
            print(f"Linha {linha}: {atual} -> {ACAO[itens[atual]]}")
            r = alterar_item(atual, itens[atual], titulo)
            r["linha"] = linha
            resultados[atual] = r
            pendentes.discard(atual)
            print(f"   {r['verificacao']}")
            if r.get("parar"):
                raise ProcessoParado(r["verificacao"] + f" (produto {atual}). Verifique essa linha.")
            if not pendentes:
                print("  (todos os itens da tabela foram processados)")
                return
        elif avisar_repetidos and atual in resultados:
            print(f"  aviso: {atual} aparece mais de uma vez no grid (linha {linha})")

        if linha >= MAX_LINHAS:
            print("  (limite de linhas atingido)")
            return

        novo = descer(atual)
        if novo is None:
            print(f"  (fim da lista na linha {linha})")
            return
        atual = novo
        linha += 1


def processar_tabela(itens: dict, titulo, resultados: dict) -> set:
    """
    Varre o grid de cima para baixo. Se sobrar item não encontrado, faz uma
    2ª varredura só para conferir (garante que nenhum foi pulado).
    itens: {codigo: '1' ou '2'}. Retorna os códigos não encontrados.
    """
    pendentes = set(itens)
    varrer(itens, pendentes, titulo, resultados, avisar_repetidos=True)
    if pendentes:
        print(f"\n  2ª varredura para {len(pendentes)} item(ns) não encontrado(s)...")
        varrer(itens, pendentes, titulo, resultados, avisar_repetidos=False)
    return pendentes


# ==========================================================
# PLANILHA E CONFERÊNCIA
# ==========================================================
def escolher_planilha(root) -> Path:
    pasta_dia = PASTA_BASE / datetime.now().strftime("%Y.%m.%d")
    inicial = pasta_dia if pasta_dia.exists() else (PASTA_BASE if PASTA_BASE.exists() else Path.home())
    caminho = filedialog.askopenfilename(
        parent=root, title="Selecione a planilha de alterações", initialdir=str(inicial),
        filetypes=[("Excel", "*.xlsx *.xlsm *.xls")])
    return Path(caminho) if caminho else None


def carregar_planilha(caminho: Path) -> pd.DataFrame:
    df = pd.read_excel(caminho, dtype=str)
    colunas = {}
    for c in df.columns:
        n = normalizar(c)
        if n.startswith("COD"):
            colunas["cod"] = c
        elif n.startswith("TABELA"):
            colunas["tab"] = c
        elif n in ("ATIVO", "STATUS"):
            colunas["ativo"] = c
    faltando = {"cod", "tab", "ativo"} - set(colunas)
    if faltando:
        raise ValueError("A planilha precisa das colunas Código, Tabela e Ativo.")

    df["_cod"] = df[colunas["cod"]].fillna("").str.strip().str.replace(r"\.0$", "", regex=True)
    df["_tab"] = df[colunas["tab"]].apply(normalizar)
    df["_des"] = df[colunas["ativo"]].apply(lambda v: VALOR_PARA_CODIGO.get(normalizar(v)))

    df["Status antes"] = ""
    df["Status depois"] = ""
    df["Verificação"] = "Pendente (tabela não processada)"
    df["Linha no grid"] = ""
    df["Processado em"] = ""

    df = df.astype(object)
    df["_ok"] = True
    for idx, row in df.iterrows():
        erro = None
        if not eh_codigo(row["_cod"]):
            erro = "Erro na planilha: código não tem 10 dígitos"
        elif not row["_tab"]:
            erro = "Erro na planilha: tabela vazia"
        elif pd.isna(row["_des"]):
            erro = "Erro na planilha: Ativo deve ser Sim ou Não"
        if erro:
            df.at[idx, "Verificação"] = erro
            df.at[idx, "_ok"] = False

    # mesmo código + tabela com pedidos diferentes -> não mexe
    validos = df[df["_ok"]]
    conflitos = validos.groupby(["_tab", "_cod"])["_des"].nunique()
    for (tab, cod) in conflitos[conflitos > 1].index:
        m = (df["_tab"] == tab) & (df["_cod"] == cod)
        df.loc[m, "Verificação"] = "Erro na planilha: código repetido com Sim e Não"
        df.loc[m, "_ok"] = False
    return df


def registrar(df, tab, resultados, nao_encontrados, interrompido):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    for idx in df.index[(df["_tab"] == tab) & df["_ok"]]:
        cod = df.at[idx, "_cod"]
        if cod in resultados:
            r = resultados[cod]
            nova = r["verificacao"]
            # numa 2ª passada o item aparece como "Já estava assim": mantém o "Alterado" original
            if df.at[idx, "Verificação"] == "Alterado" and nova == "Já estava assim":
                continue
            df.at[idx, "Verificação"] = nova
            df.at[idx, "Status antes"] = CODIGO_PARA_TEXTO.get(r["antes"], r["antes"])
            df.at[idx, "Status depois"] = CODIGO_PARA_TEXTO.get(r["depois"], r["depois"])
            df.at[idx, "Linha no grid"] = str(r.get("linha", ""))
        elif df.at[idx, "Verificação"] == "Alterado":
            continue
        elif interrompido:
            df.at[idx, "Verificação"] = "Não processado (execução interrompida)"
        elif cod in nao_encontrados:
            df.at[idx, "Verificação"] = "Não encontrado"
        df.at[idx, "Processado em"] = agora


def salvar_conferencia(df: pd.DataFrame, caminho: Path):
    saida = df.drop(columns=[c for c in df.columns if c.startswith("_")])
    saida.to_excel(caminho, index=False)

    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill
    wb = load_workbook(caminho)
    ws = wb.active
    cores = {"Alterado": "C6EFCE", "Já estava assim": "E7E6E6",
             "Não encontrado": "FFEB9C", "Erro": "FFC7CE", "ERRO": "FFC7CE"}
    col_verif = list(saida.columns).index("Verificação") + 1
    for cel in ws[1]:
        cel.font = Font(bold=True)
    for linha in ws.iter_rows(min_row=2):
        valor = str(linha[col_verif - 1].value or "")
        for chave, cor in cores.items():
            if valor.startswith(chave):
                for cel in linha:
                    cel.fill = PatternFill("solid", fgColor=cor)
                break
    for col in ws.columns:
        largura = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(largura + 2, 60)
    ws.freeze_panes = "A2"
    wb.save(caminho)


# ==========================================================
# ESCOLHA DA TABELA (sem clicar em nada no Protheus)
# ==========================================================
def escolher_tabela(root, opcoes: list, resumo_por_tabela: dict):
    """
    Janela com a lista das tabelas pendentes, já sugerindo a próxima.
    O script NÃO clica no Protheus para descobrir a tabela: a tela rola e um clique
    em posição fixa pode cair dentro do grid.
    """
    from tkinter import ttk
    escolha = {"valor": None}

    win = tk.Toplevel(root)
    win.title("Qual tabela está aberta no Protheus?")
    win.attributes("-topmost", True)
    win.resizable(False, False)

    tk.Label(win, text="Abra a tabela no Protheus em modo ALTERAR e confirme aqui qual é:",
             font=("Segoe UI", 10)).pack(padx=16, pady=(14, 6))

    var = tk.StringVar(value=opcoes[0])
    rotulos = {t: f"{t}   ({resumo_por_tabela[t]})" for t in opcoes}
    combo = ttk.Combobox(win, state="readonly", width=40, font=("Segoe UI", 12, "bold"),
                         values=[rotulos[t] for t in opcoes])
    combo.current(0)
    combo.pack(padx=16, pady=6)

    def ok():
        escolha["valor"] = opcoes[combo.current()]
        win.destroy()

    botoes = tk.Frame(win)
    botoes.pack(pady=(6, 14))
    tk.Button(botoes, text="Iniciar", width=12, command=ok).pack(side="left", padx=6)
    tk.Button(botoes, text="Encerrar script", width=14, command=win.destroy).pack(side="left", padx=6)
    win.bind("<Return>", lambda e: ok())

    win.grab_set()
    win.focus_force()
    root.wait_window(win)
    return escolha["valor"]


# ==========================================================
# EXECUÇÃO
# ==========================================================
def main():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    planilha = escolher_planilha(root)
    if not planilha:
        print("Nenhuma planilha escolhida. Nada foi feito.")
        return

    try:
        df = carregar_planilha(planilha)
    except Exception as e:
        messagebox.showerror("Planilha", f"Não consegui ler a planilha:\n{e}", parent=root)
        return

    conferencia = planilha.with_name(f"{planilha.stem}_CONFERENCIA_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
    salvar_conferencia(df, conferencia)
    invalidos = int((~df["_ok"]).sum())
    print(f"Planilha: {planilha.name} | {len(df)} linhas | {invalidos} com erro")
    print(f"Conferência: {conferencia.name}\n")

    todas = sorted(df.loc[df["_ok"], "_tab"].unique())
    concluidas = set()

    while True:
        faltam = [t for t in todas if t not in concluidas]
        if not faltam:
            messagebox.showinfo("Concluído", "Todas as tabelas da planilha foram processadas.\n\n"
                                f"Conferência: {conferencia.name}", parent=root)
            break

        resumo_tab = {}
        for t in faltam:
            st = df[(df["_tab"] == t) & df["_ok"]].drop_duplicates("_cod")
            n = len(st); a = int((st["_des"] == "1").sum())
            resumo_tab[t] = f"{n} itens: {a} ativar, {n - a} bloquear"

        tab = escolher_tabela(root, faltam, resumo_tab)
        if not tab:
            break

        sel = df[(df["_tab"] == tab) & df["_ok"]]
        itens = dict(zip(sel["_cod"], sel["_des"]))
        n_ativar = sum(1 for v in itens.values() if v == "1")
        n_bloquear = len(itens) - n_ativar

        if not messagebox.askyesno(
                "Confirmar", f"Tabela: {tab}\n\nConfira se é ESSA a tabela aberta no Protheus.\n\n"
                             f"{len(itens)} item(ns): {n_ativar} ATIVAR, {n_bloquear} BLOQUEAR.\n\n"
                             "Depois de clicar SIM, você terá 5 segundos para clicar em uma "
                             "célula da coluna Cod.Produto.", parent=root):
            continue

        contagem(5, f"\n=== Tabela {tab} === Clique em uma célula da coluna Cod.Produto...")
        titulo = janela_ativa()
        resultados, nao_encontrados, interrompido = {}, set(), False
        inicio = time.time()

        try:
            nao_encontrados = processar_tabela(itens, titulo, resultados)
        except ProcessoParado as e:
            interrompido = True
            print(f"\n!!! PARADO: {e}")
        except pyautogui.FailSafeException:
            interrompido = True
            print("\n!!! PARADO pela parada de emergência (mouse no canto da tela).")

        registrar(df, tab, resultados, nao_encontrados, interrompido)
        salvar_conferencia(df, conferencia)

        vals = [r["verificacao"] for r in resultados.values()]
        resumo = (f"Alterados: {vals.count('Alterado')}\n"
                  f"Já estavam assim: {vals.count('Já estava assim')}\n"
                  f"Não encontrados: {len(nao_encontrados) if not interrompido else 0}\n"
                  f"Erros: {sum(1 for v in vals if v.upper().startswith('ERRO'))}\n"
                  f"Tempo: {time.time() - inicio:.0f}s")
        print(resumo.replace("\n", " | "))

        if interrompido:
            messagebox.showerror(
                f"Tabela {tab} - INTERROMPIDA",
                f"{resumo}\n\nNada mais foi digitado. Confira a tela.\n"
                "A tabela continua pendente: você pode rodá-la de novo (o que já foi alterado "
                "aparecerá como 'Já estava assim' e o registro de 'Alterado' é mantido).", parent=root)
        else:
            concluidas.add(tab)
            messagebox.showinfo(
                f"Tabela {tab} - concluída",
                f"{resumo}\n\nConfira o grid e o arquivo de conferência e CONFIRME manualmente "
                "no Protheus. Depois clique OK para seguir.", parent=root)

    print(f"\nArquivo de conferência: {conferencia}")
    root.destroy()


if __name__ == "__main__":
    main()
