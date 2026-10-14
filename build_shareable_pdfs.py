import os
import subprocess
import markdown

WORKSPACE = r"D:\new folder"

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EDGE_PATH   = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BROWSER     = CHROME_PATH if os.path.exists(CHROME_PATH) else EDGE_PATH

CSS_STYLE = """
@page {
    size: A4;
    margin: 18mm 15mm 18mm 15mm;
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.55;
    color: #1e293b;
    background-color: #ffffff;
    padding: 0;
    margin: 0;
}
h1, h2, h3, h4, h5, h6 {
    color: #0f172a;
    font-weight: 700;
    page-break-after: avoid;
    margin-top: 1.2em;
    margin-bottom: 0.4em;
}
h1 {
    font-size: 19pt;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 6px;
    margin-top: 0;
    color: #1e3a8a;
}
h2 {
    font-size: 13.5pt;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
    color: #1e40af;
    margin-top: 1.4em;
}
h3 {
    font-size: 11.5pt;
    color: #334155;
    margin-top: 1.1em;
}
h4 {
    font-size: 10.5pt;
    color: #475569;
}
p {
    margin-top: 0.4em;
    margin-bottom: 0.7em;
}
a {
    color: #2563eb;
    text-decoration: none;
}
code {
    font-family: "Consolas", "Cascadia Code", "Courier New", monospace;
    font-size: 8.5pt;
    background-color: #f1f5f9;
    padding: 2px 4px;
    border-radius: 4px;
    color: #0f172a;
    border: 1px solid #e2e8f0;
}
pre {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 10px 14px;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 0.8em 0;
}
pre code {
    background-color: transparent;
    padding: 0;
    border: none;
    font-size: 8pt;
    line-height: 1.4;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #cbd5e1;
    padding: 5px 8px;
    text-align: left;
    vertical-align: top;
}
th {
    background-color: #f1f5f9;
    font-weight: 600;
    color: #0f172a;
}
tr:nth-child(even) {
    background-color: #f8fafc;
}
blockquote {
    border-left: 4px solid #3b82f6;
    margin: 0.8em 0;
    padding: 6px 14px;
    background-color: #eff6ff;
    color: #1e3a8a;
    border-radius: 0 6px 6px 0;
    page-break-inside: avoid;
}
blockquote p {
    margin: 0.3em 0;
}
ul, ol {
    margin-top: 0.4em;
    margin-bottom: 0.7em;
    padding-left: 20px;
}
li {
    margin-bottom: 0.25em;
}
hr {
    border: 0;
    height: 1px;
    background: #cbd5e1;
    margin: 1.5em 0;
}
.header-badge {
    display: inline-block;
    background-color: #dbeafe;
    color: #1e40af;
    font-size: 8pt;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 12px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
"""

def md_to_pdf(input_md_path, output_pdf_path, title="Project Document"):
    with open(input_md_path, 'r', encoding='utf-8', errors='ignore') as f:
        md_text = f.read()

    html_body = markdown.markdown(
        md_text,
        extensions=['extra', 'toc', 'sane_lists', 'admonition']
    )

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>{CSS_STYLE}</style>
</head>
<body>
{html_body}
</body>
</html>
"""

    temp_html_path = output_pdf_path.replace('.pdf', '_temp.html')
    with open(temp_html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

    cmd = [
        BROWSER,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output_pdf_path}",
        temp_html_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)

    print(f"Generated: {os.path.basename(output_pdf_path)} ({os.path.getsize(output_pdf_path):,} bytes)")

if __name__ == "__main__":
    docs = [
        (os.path.join(WORKSPACE, "IMPLEMENTATION_PLAN.md"), os.path.join(WORKSPACE, "IMPLEMENTATION_PLAN.pdf"), "Implementation Plan & Roadmap v4.8"),
        (os.path.join(WORKSPACE, "ARCHITECTURE.md"),         os.path.join(WORKSPACE, "ARCHITECTURE.pdf"),         "System Architecture & Engineering Specification v4.8"),
        (os.path.join(WORKSPACE, "CURSOR_BRIEF.md"),        os.path.join(WORKSPACE, "CURSOR_BRIEF.pdf"),        "Cursor AI Master Brief v4.8"),
        (os.path.join(WORKSPACE, "PROJECT_BRIEF.md"),       os.path.join(WORKSPACE, "PROJECT_BRIEF.pdf"),       "Project Specification Brief v4.8"),
    ]

    print("=" * 60)
    print("Compiling Shareable Team PDFs...")
    print("=" * 60)
    for src, dst, title in docs:
        if os.path.exists(src):
            md_to_pdf(src, dst, title)
        else:
            print(f"Error: {src} not found!")
    print("=" * 60)
    print("All 4 Core PDFs generated successfully!")
    print("=" * 60)
