from pathlib import Path
import re
import markdown


def converter_underline(texto: str) -> str:
    return re.sub(r"\+\+(.*?)\+\+", r"<u>\1</u>", texto)


def remover_tags_p(html: str) -> str:
    # Troca o fim de cada parágrafo por 2 <br>
    html = re.sub(r"</p>\s*<p>", "<br><br>", html)
    # Remove o <p> inicial e o </p> final restantes
    html = re.sub(r"^\s*<p>", "", html)
    html = re.sub(r"</p>\s*$", "", html)

    return html.strip()


def markdown_para_html_elementor(
    arquivo_entrada: str,
    arquivo_saida: str,
    remover_paragrafos: bool = True
) -> None:
    caminho_entrada = Path(arquivo_entrada)
    caminho_saida = Path(arquivo_saida)

    if not caminho_entrada.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo_entrada}")

    texto = caminho_entrada.read_text(encoding="utf-8")

    texto = converter_underline(texto)

    html = markdown.markdown(
        texto,
        extensions=[
            "extra",
            "sane_lists",
            "nl2br",
        ],
        output_format="html5"
    )

    if remover_paragrafos:
        html = remover_tags_p(html)

    caminho_saida.write_text(html, encoding="utf-8")

    print(f"Arquivo convertido com sucesso: {arquivo_saida}")


if __name__ == "__main__":
    markdown_para_html_elementor(
        arquivo_entrada="entrada.md",
        arquivo_saida="saida-elementor.html",
        remover_paragrafos=True
    )