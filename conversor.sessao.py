from pathlib import Path
import re
import markdown


MARCADOR_TEXTO = re.compile(
    r"^\*\*Texto/Parágrafo:\*\*\s*$",
    flags=re.IGNORECASE,
)

MARCADOR_FIM = re.compile(
    r"^\*\*(Alt Text|Botões):\*\*",
    flags=re.IGNORECASE,
)

TITULO_SECAO = re.compile(
    r"^##\s+(.+?)\s*$"
)


def converter_underline(texto: str) -> str:
    """
    Converte:

    ++texto sublinhado++

    para:

    <u>texto sublinhado</u>
    """
    return re.sub(
        r"\+\+(.+?)\+\+",
        r"<u>\1</u>",
        texto,
        flags=re.DOTALL,
    )


def paragrafos_para_br(html: str) -> str:
    """
    Remove tags <p> e substitui a separação entre parágrafos
    por dois <br>.

    Listas, links, strong, em e outras tags são preservadas.
    """

    def substituir_paragrafo(match: re.Match) -> str:
        conteudo = match.group(1).strip()
        return f"{conteudo}\n"
    html = re.sub(
        r"<p>(.*?)</p>",
        substituir_paragrafo,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Remove os dois <br> adicionados ao final do último parágrafo.
    html = re.sub(
        r"(?:\s*<br\s*/?>\s*){2}\s*$",
        "",
        html,
        flags=re.IGNORECASE,
    )
    return html.strip()


def extrair_blocos_texto(markdown_completo: str) -> list[dict[str, str]]:
    """
    Extrai somente os conteúdos encontrados depois de:
        **Texto/Parágrafo:**
    A captura termina ao encontrar:
        **Alt Text:**
        **Botões:**
        ---
        outro título ##
    Retorna uma lista com o título da seção e o Markdown capturado.
    """

    blocos: list[dict[str, str]] = []
    titulo_atual = "Seção sem título"
    capturando = False
    linhas_bloco: list[str] = []
    def finalizar_bloco() -> None:
        nonlocal capturando, linhas_bloco
        texto_bloco = "\n".join(linhas_bloco).strip()
        if texto_bloco:
            blocos.append(
                {
                    "titulo": titulo_atual,
                    "markdown": texto_bloco,
                }
            )

        capturando = False
        linhas_bloco = []

    for linha in markdown_completo.splitlines():
        linha_limpa = linha.strip()

        titulo_encontrado = TITULO_SECAO.match(linha_limpa)

        if titulo_encontrado:
            if capturando:
                finalizar_bloco()

            titulo_atual = titulo_encontrado.group(1).strip()
            continue

        if MARCADOR_TEXTO.match(linha_limpa):
            if capturando:
                finalizar_bloco()

            capturando = True
            linhas_bloco = []
            continue

        if capturando and (
            MARCADOR_FIM.match(linha_limpa)
            or linha_limpa == "---"
        ):
            finalizar_bloco()
            continue

        if capturando:
            linhas_bloco.append(linha)

    # Caso o arquivo termine enquanto um bloco ainda está sendo capturado.
    if capturando:
        finalizar_bloco()

    return blocos


def converter_bloco_markdown(
    texto_markdown: str,
    remover_paragrafos: bool = True,) -> str:
    texto_markdown = converter_underline(texto_markdown)

    html = markdown.markdown(
        texto_markdown,
        extensions=[
            "extra",
            "sane_lists",
        ],
        output_format="html5",
    )
    if remover_paragrafos:
        html = paragrafos_para_br(html)
    return html.strip()

def formata_main_key(main_key: str) -> str:
    main_key = main_key.strip()
    main_key = re.sub(
        r"[^\w.-]+",
        "-",
        main_key,
        flags=re.UNICODE,
    )
    return main_key.strip("-._") or "sem-chave"


def markdown_para_html_elementor(
    arquivo_entrada: str,
    main_key: str,
    pasta_saida: str = "out-sessions",
    remover_paragrafos: bool = True,
    incluir_comentarios: bool = True,
) -> Path:
    caminho_entrada = Path(arquivo_entrada)

    if not caminho_entrada.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho_entrada}"
        )

    main_key_segura = formata_main_key(main_key)
    caminho_saida = (
        Path(pasta_saida)
        / f"saida-{main_key_segura}-elementor.html"
    )

    markdown_completo = caminho_entrada.read_text(
        encoding="utf-8"
    )

    blocos = extrair_blocos_texto(markdown_completo)

    if not blocos:
        raise ValueError(
            "Nenhum bloco '**Texto/Parágrafo:**' foi encontrado."
        )

    partes_html: list[str] = []

    for bloco in blocos:
        html_bloco = converter_bloco_markdown(
            bloco["markdown"],
            remover_paragrafos=remover_paragrafos,
        )

        if incluir_comentarios:
            titulo_seguro = bloco["titulo"].replace("--", "—")

            partes_html.append(
                f"<!-- Seção: {titulo_seguro} -->\n"
                f"{html_bloco}"
            )
        else:
            partes_html.append(html_bloco)

    html_final = "\n\n".join(partes_html)

    caminho_saida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_saida.write_text(
        html_final,
        encoding="utf-8",
    )

    print(
        f"Conversão concluída: {len(blocos)} blocos convertidos."
    )
    print(f"Arquivo gerado: {caminho_saida}")

    return caminho_saida

if __name__ == "__main__":
    markdown_para_html_elementor(
        arquivo_entrada="entrada.md",
        main_key="Link de Voz para 3CX",
        remover_paragrafos=True,
        incluir_comentarios=True,
    )