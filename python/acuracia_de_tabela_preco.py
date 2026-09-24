
"""
ETAPA 4 - Compara a planilha com o preço que está HOJE no Protheus.
Não altera nada: só lê o banco e gera o arquivo "relatorio_precos.csv" (abre no Excel).
Rode no terminal do VSCode:   python compara_precos.py
"""
import csv
import io
import os
import urllib.request
from decimal import Decimal

import pymssql
from dotenv import load_dotenv

load_dotenv()

# Colunas da planilha (A = 0, B = 1, C = 2)
COL_PRODUTO, COL_PRECO, COL_TABELA = 0, 1, 2


def br_para_decimal(txt):
    return Decimal(str(txt).strip().replace(".", "").replace(",", ".")).quantize(Decimal("0.01"))


def br(valor):
    return "" if valor is None else f"{valor:.2f}".replace(".", ",")


# ---------------------------------------------------------------- planilha
def ler_planilha():
    url = os.environ.get("SHEET_CSV_URL", "").strip()
    if url:
        texto = urllib.request.urlopen(url).read().decode("utf-8")
    else:
        with open(os.environ.get("SHEET_ARQUIVO", "precos.csv"), encoding="utf-8-sig") as f:
            texto = f.read()

    # aceita CSV separado por vírgula, ponto e vírgula ou TAB
    dialeto = csv.Sniffer().sniff(texto[:2000], delimiters=",;\t")
    novos, conflitos = {}, []
    for linha in csv.reader(io.StringIO(texto), dialeto):
        try:
            codigo = linha[COL_PRODUTO].split(" - ")[0].strip()
            preco = br_para_decimal(linha[COL_PRECO])
            tabela = linha[COL_TABELA].strip()
        except Exception:
            continue  # cabeçalho ou linha vazia
        chave = (tabela, codigo)
        if chave in novos and novos[chave] != preco:
            conflitos.append((tabela, codigo, novos[chave], preco))
        novos[chave] = preco

    if conflitos:
        print("ATENÇÃO - mesmo produto/tabela com preços diferentes na planilha:")
        for c in conflitos:
            print(f"   tabela {c[0]} produto {c[1]}: {br(c[2])} x {br(c[3])}")
        raise SystemExit("Corrija a planilha e rode de novo.")
    return novos


# ---------------------------------------------------------------- banco
def ler_banco(tabelas, produtos):
    emp = os.environ.get("EMPRESA", "010")
    conn = pymssql.connect(
        server=os.environ["DB_SERVER"], port=os.environ.get("DB_PORT", "2372"),
        user=os.environ["DB_USER"], password=os.environ["DB_PASS"],
        database=os.environ["DB_NAME"], login_timeout=15,
    )
    cur = conn.cursor()
    marcas_t = ",".join(["%s"] * len(tabelas))
    marcas_p = ",".join(["%s"] * len(produtos))
    cur.execute(
        f"""
        SELECT RTRIM(DA1_CODTAB), RTRIM(DA1_CODPRO), DA1_ITEM, DA1_PRCVEN, DA1_ATIVO
        FROM DA1{emp}
        WHERE D_E_L_E_T_ = ' '
          AND RTRIM(DA1_CODTAB) IN ({marcas_t})
          AND RTRIM(DA1_CODPRO) IN ({marcas_p})
        """,
        tuple(tabelas) + tuple(produtos),
    )
    atuais = {}
    for tab, prod, item, preco, ativo in cur.fetchall():
        atuais[(tab, prod)] = {"item": item, "preco": Decimal(str(preco)).quantize(Decimal("0.01")), "ativo": ativo}
    conn.close()
    return atuais


# ---------------------------------------------------------------- relatório
def main():
    novos = ler_planilha()
    tabelas = sorted({t for t, _ in novos})
    produtos = sorted({p for _, p in novos})
    print(f"Planilha: {len(novos)} itens únicos em {len(tabelas)} tabelas.")

    atuais = ler_banco(tabelas, produtos)

    cont = {"ALTERAR": 0, "JA_ESTA_CERTO": 0, "NAO_EXISTE_NA_TABELA": 0}
    with open("relatorio_precos.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["tabela", "produto", "item", "preco_atual", "preco_novo", "ativo", "situacao"])
        for (tab, prod), preco_novo in sorted(novos.items()):
            atual = atuais.get((tab, prod))
            if atual is None:
                situacao = "NAO_EXISTE_NA_TABELA"
                w.writerow([tab, prod, "", "", br(preco_novo), "", situacao])
            else:
                situacao = "JA_ESTA_CERTO" if atual["preco"] == preco_novo else "ALTERAR"
                w.writerow([tab, prod, atual["item"], br(atual["preco"]), br(preco_novo), atual["ativo"], situacao])
            cont[situacao] += 1

    print("\nResultado:")
    for k, v in cont.items():
        print(f"   {k}: {v}")
    print("\nArquivo gerado: relatorio_precos.csv")


if __name__ == "__main__":
    main()
