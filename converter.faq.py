from __future__ import annotations

import argparse
import re
from pathlib import Path

import markdown


def separar_linha_tabela(linha: str) -> list[str]:
    linha = linha.strip()

    if linha.startswith("|"):
        linha = linha[1:]

    if linha.endswith("|"):
        linha = linha[:-1]

    colunas = re.split(r"(?<!\\)\|", linha)

    return [
        coluna.replace(r"\|", "|").strip()
        for coluna in colunas
    ]


def eh_separador_tabela(colunas: list[str]) -> bool:
    return bool(colunas) and all(
        re.fullmatch(r":?-{3,}:?", coluna.strip()) is not None
        for coluna in colunas
    )


def extrair_faq(
    markdown_completo: str,
) -> list[tuple[str, str, str]]:
    linhas = markdown_completo.splitlines()
    itens: list[tuple[str, str, str]] = []

    indice_numero: int | None = None
    indice_pergunta: int | None = None
    indice_resposta: int | None = None

    esperando_separador = False
    dentro_tabela = False

    for linha in linhas:
        linha_limpa = linha.strip()

        if not linha_limpa.startswith("|"):
            if dentro_tabela and itens:
                break

            continue

        colunas = separar_linha_tabela(linha_limpa)

        if (
            indice_numero is None
            or indice_pergunta is None
            or indice_resposta is None
        ):
            cabecalhos = [
                re.sub(r"\s+", " ", coluna).strip().casefold()
                for coluna in colunas
            ]

            if all(
                cabecalho in cabecalhos
                for cabecalho in ("index", "pergunta", "resposta")
            ):
                indice_numero = cabecalhos.index("index")
                indice_pergunta = cabecalhos.index("pergunta")
                indice_resposta = cabecalhos.index("resposta")
                esperando_separador = True

            continue

        if esperando_separador:
            if not eh_separador_tabela(colunas):
                raise ValueError(
                    "A linha separadora da tabela Markdown é inválida."
                )

            esperando_separador = False
            dentro_tabela = True
            continue

        maior_indice = max(
            indice_numero,
            indice_pergunta,
            indice_resposta,
        )

        if len(colunas) <= maior_indice:
            continue

        numero = colunas[indice_numero].strip()
        pergunta = colunas[indice_pergunta].strip()
        resposta_markdown = colunas[indice_resposta].strip()

        if numero and pergunta and resposta_markdown:
            itens.append(
                (
                    pergunta,
                    numero,
                    resposta_markdown,
                )
            )

    return itens


def converter_underline(texto: str) -> str:
    return re.sub(
        r"\+\+(.+?)\+\+",
        r"<u>\1</u>",
        texto,
        flags=re.DOTALL,
    )


def converter_espaco_duplo(texto: str) -> str:
    """
    Converte sequências de dois ou mais espaços em <br><br>.
    """
    return re.sub(
        r" {2,}",
        "<br><br>",
        texto,
    )


def remover_p_externo(html: str) -> str:
    html = re.sub(
        r"</p>\s*<p>",
        "<br><br>",
        html,
        flags=re.IGNORECASE,
    )

    html = re.sub(
        r"^\s*<p>",
        "",
        html,
        flags=re.IGNORECASE,
    )

    html = re.sub(
        r"</p>\s*$",
        "",
        html,
        flags=re.IGNORECASE,
    )

    return html.strip()


def markdown_para_html(texto_markdown: str) -> str:
    texto_markdown = converter_espaco_duplo(texto_markdown)
    texto_markdown = converter_underline(texto_markdown)

    html = markdown.markdown(
        texto_markdown,
        extensions=[
            "extra",
            "sane_lists",
        ],
        output_format="html5",
    )

    return remover_p_externo(html)


def converter_faq(
    arquivo_entrada: str | Path,
    arquivo_saida: str | Path,
) -> None:
    entrada = Path(arquivo_entrada)
    saida = Path(arquivo_saida)

    if not entrada.exists():
        raise FileNotFoundError(
            f"Arquivo de entrada não encontrado: {entrada}"
        )

    conteudo_markdown = entrada.read_text(encoding="utf-8")
    itens = extrair_faq(conteudo_markdown)

    if not itens:
        raise ValueError(
            "Nenhuma tabela com as colunas Pergunta e Resposta foi encontrada."
        )

    blocos: list[str] = []

    for pergunta, numero, resposta_markdown in itens:
        resposta_html = markdown_para_html(resposta_markdown)

        blocos.append(
            f"{numero}\n"
            f"{pergunta}\n"
            f"{resposta_html}"
        )

    conteudo_saida = "\n\n".join(blocos) + "\n"

    saida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    saida.write_text(
        conteudo_saida,
        encoding="utf-8",
    )

    print(f"{len(itens)} perguntas convertidas.")
    print(f"Arquivo gerado: {saida.resolve()}")


def criar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Converte uma tabela FAQ em Markdown para "
            "pergunta e resposta em HTML."
        )
    )

    parser.add_argument(
        "entrada",
        nargs="?",
        default="faq.md",
        help="Arquivo Markdown de entrada.",
    )

    parser.add_argument(
        "saida",
        nargs="?",
        default="faq-convertida.txt",
        help="Arquivo TXT de saída.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    argumentos = criar_argumentos()

    converter_faq(
        arquivo_entrada=argumentos.entrada,
        arquivo_saida=argumentos.saida,
    )