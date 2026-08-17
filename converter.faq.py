from __future__ import annotations

import argparse
import re
from pathlib import Path

import markdown


def normalizar_marcador(linha: str) -> str:
    """
    Normaliza os títulos estruturais da FAQ.

    Aceita:

        ### Item 1
        #### Pergunta
        #### Resposta

    e também:

        **### Item 1**
        **#### Pergunta**
        **#### Resposta**
    """

    linha = linha.strip()

    if (
        linha.startswith("**")
        and linha.endswith("**")
        and len(linha) >= 4
    ):
        linha = linha[2:-2].strip()

    return linha


def normalizar_markdown_escapado(texto: str) -> str:
    """
    Corrige Markdown que chegou com caracteres escapados.

    Exemplos:

        \\*\\*texto\\*\\*  ->  **texto**
        \\(               ->  (
        \\)               ->  )
        https\\://         ->  https://

    Também corrige casos como:

        **\\*\\*texto\\*\\***

    que podem virar:

        ****texto****

    transformando em:

        **texto**
    """

    texto = re.sub(
        r"\\([*()\[\]:])",
        r"\1",
        texto,
    )

    # ****texto**** -> **texto**
    texto = re.sub(
        r"\*{4}(.+?)\*{4}",
        r"**\1**",
        texto,
        flags=re.DOTALL,
    )

    return texto


def extrair_faq(
    markdown_completo: str,
) -> list[tuple[str, str, str]]:
    """
    Extrai FAQs no formato:

        ### Item 1

        #### Pergunta

        Minha pergunta?

        #### Resposta

        Minha resposta.

        ### Item 2
        ...

    Retorna:

        [
            (
                pergunta,
                numero,
                resposta_markdown,
            ),
            ...
        ]
    """

    linhas = markdown_completo.splitlines()

    itens: list[tuple[str, str, str]] = []

    numero_atual: str | None = None
    pergunta_linhas: list[str] = []
    resposta_linhas: list[str] = []

    secao: str | None = None

    def adicionar_item() -> None:
        """
        Adiciona o item atual à lista,
        caso tenha número, pergunta e resposta.
        """

        if numero_atual is None:
            return

        pergunta = " ".join(
            linha.strip()
            for linha in pergunta_linhas
            if linha.strip()
        ).strip()

        resposta = "\n".join(
            resposta_linhas
        ).strip()

        if pergunta and resposta:
            itens.append(
                (
                    pergunta,
                    numero_atual,
                    resposta,
                )
            )

    for linha in linhas:
        marcador = normalizar_marcador(linha)

        #
        # Detecta:
        #
        # ### Item 1
        # ### Item 2
        # ...
        #
        correspondencia_item = re.fullmatch(
            r"###\s+Item\s+(\d+)",
            marcador,
            flags=re.IGNORECASE,
        )

        if correspondencia_item:
            # Salva o item anterior
            adicionar_item()

            # Inicia o novo item
            numero_atual = correspondencia_item.group(1)

            pergunta_linhas = []
            resposta_linhas = []

            secao = None

            continue

        #
        # Detecta:
        #
        # #### Pergunta
        #
        if re.fullmatch(
            r"####\s+Pergunta",
            marcador,
            flags=re.IGNORECASE,
        ):
            secao = "pergunta"
            continue

        #
        # Detecta:
        #
        # #### Resposta
        #
        if re.fullmatch(
            r"####\s+Resposta",
            marcador,
            flags=re.IGNORECASE,
        ):
            secao = "resposta"
            continue

        #
        # Ignora separadores como:
        #
        # ---
        # **---**
        #
        if marcador in {
            "---",
            "***",
            "___",
        }:
            continue

        #
        # Ainda não encontramos nenhum Item.
        #
        if numero_atual is None:
            continue

        #
        # Armazena conteúdo da pergunta
        #
        if secao == "pergunta":
            pergunta_linhas.append(linha)

        #
        # Armazena conteúdo da resposta
        #
        elif secao == "resposta":
            resposta_linhas.append(linha)

    #
    # Adiciona o último item.
    #
    adicionar_item()

    return itens


def converter_underline(texto: str) -> str:
    """
    Converte:

        ++texto++

    para:

        <u>texto</u>
    """

    return re.sub(
        r"\+\+(.+?)\+\+",
        r"<u>\1</u>",
        texto,
        flags=re.DOTALL,
    )


def converter_espaco_duplo(texto: str) -> str:
    """
    Converte sequências de dois ou mais
    espaços em:

        <br><br>
    """

    return re.sub(
        r" {2,}",
        "<br><br>",
        texto,
    )


def remover_p_externo(html: str) -> str:
    """
    Remove as tags <p> externas geradas
    automaticamente pelo Markdown.

    Uma linha em branco no Markdown gera
    dois parágrafos:

        <p>Primeira linha</p>
        <p>Segunda linha</p>

    Aqui isso é transformado em:

        Primeira linha<br><br>Segunda linha
    """

    #
    # Transforma a separação entre
    # parágrafos em <br><br>.
    #
    html = re.sub(
        r"</p>\s*<p>",
        "<br><br>",
        html,
        flags=re.IGNORECASE,
    )

    #
    # Remove o <p> inicial.
    #
    html = re.sub(
        r"^\s*<p>",
        "",
        html,
        flags=re.IGNORECASE,
    )

    #
    # Remove o </p> final.
    #
    html = re.sub(
        r"</p>\s*$",
        "",
        html,
        flags=re.IGNORECASE,
    )

    return html.strip()


def markdown_para_html(
    texto_markdown: str,
) -> str:
    """
    Converte o conteúdo Markdown
    da resposta para HTML.

    Exemplo:

        Primeira linha

        Segunda linha

    vira:

        Primeira linha<br><br>Segunda linha
    """

    #
    # Corrige Markdown escapado.
    #
    texto_markdown = normalizar_markdown_escapado(
        texto_markdown
    )

    #
    # Mantém a regra existente:
    #
    # dois ou mais espaços
    # -> <br><br>
    #
    texto_markdown = converter_espaco_duplo(
        texto_markdown
    )

    #
    # ++texto++ -> <u>texto</u>
    #
    texto_markdown = converter_underline(
        texto_markdown
    )

    #
    # Converte Markdown para HTML.
    #
    html = markdown.markdown(
        texto_markdown,
        extensions=[
            "extra",
            "sane_lists",
        ],
        output_format="html5",
    )

    #
    # Converte separações entre
    # parágrafos para <br><br>.
    #
    html = remover_p_externo(
        html
    )

    return html


def converter_faq(
    arquivo_entrada: str | Path,
    arquivo_saida: str | Path,
) -> None:
    """
    Lê o arquivo Markdown,
    extrai as perguntas/respostas,
    converte as respostas para HTML
    e gera o TXT final.
    """

    entrada = Path(arquivo_entrada)
    saida = Path(arquivo_saida)

    if not entrada.exists():
        raise FileNotFoundError(
            f"Arquivo de entrada não encontrado: {entrada}"
        )

    conteudo_markdown = entrada.read_text(
        encoding="utf-8"
    )

    itens = extrair_faq(
        conteudo_markdown
    )

    if not itens:
        raise ValueError(
            "Nenhum bloco com Item, Pergunta "
            "e Resposta foi encontrado."
        )

    blocos: list[str] = []

    for (
        pergunta,
        numero,
        resposta_markdown,
    ) in itens:

        resposta_html = markdown_para_html(
            resposta_markdown
        )

        blocos.append(
            f"{numero}\n"
            f"{pergunta}\n"
            f"{resposta_html}"
        )

    conteudo_saida = (
        "\n\n".join(blocos)
        + "\n"
    )

    saida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    saida.write_text(
        conteudo_saida,
        encoding="utf-8",
    )

    print(
        f"{len(itens)} perguntas convertidas."
    )

    print(
        f"Arquivo gerado: {saida.resolve()}"
    )


def criar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Converte uma FAQ estruturada "
            "em Markdown para pergunta e "
            "resposta em HTML."
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