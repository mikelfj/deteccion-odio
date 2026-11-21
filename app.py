"""
Evaluación de discurso de odio con pysentimiento (Hugging Face Space con Gradio).

Basado en el notebook "Pysentimiento_discurso_odio_BI":
  nivel = probabilidad("hateful") * NIVELES
"""
import html
import tempfile

import gradio as gr
import pandas as pd
from pysentimiento import create_analyzer

# El modelo se carga una sola vez al arrancar el Space (tarda un poco la primera vez).
hate_speech_analyzer = create_analyzer(task="hate_speech", lang="es")

NINGUNA = "(ninguna)"

# Escala RdYlGn invertida de matplotlib (verde = poco odio, rojo = mucho odio).
RDYLGN_R = ["#006837", "#1a9850", "#66bd63", "#a6d96a", "#d9ef8b", "#ffffbf",
            "#fee08b", "#fdae61", "#f46d43", "#d73027", "#a50026"]


# ------------------------------------------------------------------ utilidades
def color_para(frac):
    """Color de la escala para un valor entre 0 y 1."""
    frac = min(max(frac, 0.0), 1.0)
    pos = frac * (len(RDYLGN_R) - 1)
    i = min(int(pos), len(RDYLGN_R) - 2)
    t = pos - i
    a, b = RDYLGN_R[i], RDYLGN_R[i + 1]
    rgb = [round(int(a[k:k + 2], 16) * (1 - t) + int(b[k:k + 2], 16) * t) for k in (1, 3, 5)]
    return "#{:02x}{:02x}{:02x}".format(*rgb), frac > 0.55 or frac < 0.1


def leer_tabla(ruta):
    if ruta.lower().endswith(".csv"):
        return pd.read_csv(ruta)
    return pd.read_excel(ruta)  # primera hoja, primera fila = cabecera


def limpiar(texto):
    # Igual que en el notebook: quita saltos de línea y espacios repetidos.
    return " ".join(str(texto).split())


# --------------------------------------------------------- al subir el fichero
def al_subir(fichero):
    if fichero is None:
        return gr.update(choices=[], value=None), gr.update(choices=[NINGUNA], value=NINGUNA), ""
    df = leer_tabla(fichero)
    cols = [str(c) for c in df.columns]
    # Por defecto, la 2ª columna (como en el notebook) o la que más texto tenga.
    if len(cols) >= 2:
        texto = cols[1]
    else:
        texto = cols[0]
    numericas = [c for c, orig in zip(cols, df.columns) if pd.api.types.is_numeric_dtype(df[orig])]
    ref = numericas[0] if numericas else NINGUNA
    info = f"✅ {len(df)} filas · columnas: {', '.join(cols)}"
    return (gr.update(choices=cols, value=texto),
            gr.update(choices=[NINGUNA] + cols, value=ref),
            info)


# ------------------------------------------------------------------- análisis
def analizar(fichero, niveles, col_texto, col_ref, orden, progress=gr.Progress()):
    if fichero is None:
        raise gr.Error("Primero sube un fichero Excel.")
    if not niveles or niveles < 1:
        raise gr.Error("NIVELES debe ser un número mayor o igual que 1.")
    niveles = int(niveles)

    df = leer_tabla(fichero)
    df.columns = [str(c) for c in df.columns]
    if col_texto not in df.columns:
        raise gr.Error("Elige la columna que contiene los mensajes.")

    df = df[df[col_texto].notna()].copy()
    df["_texto"] = df[col_texto].map(limpiar)
    df = df[df["_texto"] != ""]
    if df.empty:
        raise gr.Error("La columna elegida no tiene mensajes.")

    textos = df["_texto"].tolist()
    hateful, targeted, aggressive = [], [], []
    lote = 16
    for i in progress.tqdm(range(0, len(textos), lote), desc="Analizando mensajes"):
        for r in hate_speech_analyzer.predict(textos[i:i + lote]):
            hateful.append(r.probas["hateful"])
            targeted.append(r.probas.get("targeted", 0.0))
            aggressive.append(r.probas.get("aggressive", 0.0))

    df["nivel_odio"] = [p * niveles for p in hateful]
    df["prob_hateful"] = hateful
    df["prob_targeted"] = targeted
    df["prob_aggressive"] = aggressive

    # Excel descargable con los resultados
    salida = df.drop(columns=["_texto"])
    ruta = tempfile.NamedTemporaryFile(suffix="_odio.xlsx", delete=False).name
    salida.round(4).to_excel(ruta, index=False)

    vista = df.sort_values("nivel_odio", ascending=False) if orden.startswith("De más") else df
    ref = col_ref if col_ref and col_ref != NINGUNA and col_ref in df.columns else None
    return generar_html(vista, niveles, ref), ruta


# ------------------------------------------------------------------ vista HTML
def generar_html(df, niveles, col_ref):
    n = len(df)
    media = df["nivel_odio"].mean()
    altos = int((df["nivel_odio"] >= niveles / 2).sum())

    gradiente = ", ".join(RDYLGN_R)
    marcas = "".join(
        f'<span style="position:absolute;left:{k / niveles * 100}%;transform:translateX(-50%)">{k}</span>'
        for k in range(niveles + 1))

    # Reparto por tramos de nivel (0–1, 1–2, ...)
    tramos = ""
    for k in range(niveles):
        lo, hi = k, k + 1
        cnt = int(((df["nivel_odio"] >= lo) & ((df["nivel_odio"] < hi) | (hi == niveles))).sum())
        c, _ = color_para((k + 0.5) / niveles)
        ancho = cnt / n * 100 if n else 0
        tramos += (f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
                   f'<span style="width:52px;font-size:12px;color:#555">{lo}–{hi}</span>'
                   f'<div style="flex:1;background:#eee;border-radius:4px;height:14px">'
                   f'<div style="width:{ancho}%;background:{c};height:100%;border-radius:4px"></div></div>'
                   f'<span style="width:28px;font-size:12px;text-align:right">{cnt}</span></div>')

    filas = ""
    for i, (_, r) in enumerate(df.iterrows(), 1):
        nivel = r["nivel_odio"]
        c, blanco = color_para(nivel / niveles)
        ref = ""
        if col_ref is not None:
            v = r[col_ref]
            ref = (f'<div style="width:70px;text-align:center;font-size:13px;color:#555" '
                   f'title="{html.escape(col_ref)}">{html.escape(str(v)) if pd.notna(v) else "—"}</div>')
        filas += (
            f'<div style="display:flex;gap:14px;align-items:center;padding:10px 4px;border-bottom:1px solid #eee">'
            f'<div style="width:26px;color:#999;font-size:12px;text-align:right">{i}</div>'
            f'<div style="flex:1;font-size:14px;line-height:1.45">{html.escape(r["_texto"])}</div>'
            f'{ref}'
            f'<div title="P(hateful) = {r["prob_hateful"]:.3f}" style="width:64px;min-width:64px;height:38px;'
            f'background:{c};border:1px solid #999;border-radius:6px;display:grid;place-items:center;'
            f'font-weight:700;font-size:15px;color:{"#fff" if blanco else "#111"}">{nivel:.1f}</div>'
            f'</div>')

    cab_ref = (f'<div style="width:70px;text-align:center">{html.escape(col_ref)}</div>'
               if col_ref is not None else "")

    return f"""
<div style="background:#fff;color:#111;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
            padding:20px;border-radius:12px;border:1px solid #e5e7eb">
  <h2 style="margin:0 0 14px;text-align:center;color:#111">
    Evaluación de discurso de odio sobre {niveles} niveles</h2>

  <div style="max-width:560px;margin:0 auto 6px">
    <div style="height:16px;border-radius:4px;border:1px solid #ccc;
                background:linear-gradient(to right, {gradiente})"></div>
    <div style="position:relative;height:18px;font-size:12px;color:#444">{marcas}</div>
    <div style="text-align:center;font-size:12px;color:#555">Nivel de odio (0 – {niveles})</div>
  </div>

  <div style="display:flex;flex-wrap:wrap;gap:24px;margin:18px 0 8px;align-items:flex-start">
    <div style="display:flex;gap:12px">
      <div style="background:#f6f7f9;border-radius:10px;padding:10px 16px">
        <div style="font-size:22px;font-weight:700">{n}</div><div style="font-size:12px;color:#666">mensajes</div></div>
      <div style="background:#f6f7f9;border-radius:10px;padding:10px 16px">
        <div style="font-size:22px;font-weight:700">{media:.2f}</div><div style="font-size:12px;color:#666">nivel medio</div></div>
      <div style="background:#f6f7f9;border-radius:10px;padding:10px 16px">
        <div style="font-size:22px;font-weight:700">{altos}</div>
        <div style="font-size:12px;color:#666">con nivel ≥ {niveles / 2:g}</div></div>
    </div>
    <div style="flex:1;min-width:240px">
      <div style="font-size:12px;color:#666;margin-bottom:4px">Mensajes por tramo de nivel</div>
      {tramos}
    </div>
  </div>

  <div style="display:flex;gap:14px;padding:8px 4px;border-bottom:2px solid #ddd;font-size:12px;
              color:#666;font-weight:600;margin-top:10px">
    <div style="width:26px"></div><div style="flex:1">Mensaje</div>{cab_ref}
    <div style="width:64px;text-align:center">Nivel</div>
  </div>
  {filas}
</div>"""


# ------------------------------------------------------------------ interfaz
with gr.Blocks(title="Discurso de odio · pysentimiento") as demo:
    gr.Markdown(
        "# 🔎 Evaluación de discurso de odio\n"
        "Sube un Excel con los mensajes (la primera fila es la cabecera). Cada mensaje se analiza con "
        "[pysentimiento](https://github.com/pysentimiento/pysentimiento) (`task=\"hate_speech\"`, español) "
        "y su nivel se calcula como **P(hateful) × NIVELES**.")
    with gr.Row():
        with gr.Column(scale=2):
            fichero = gr.File(label="Fichero Excel (.xlsx, .xls o .csv)",
                              file_types=[".xlsx", ".xls", ".csv"], type="filepath")
            info = gr.Markdown()
        with gr.Column(scale=1):
            niveles = gr.Number(label="NIVELES (número de niveles de odio)", value=4,
                                precision=0, minimum=1)
            col_texto = gr.Dropdown(label="Columna con los mensajes", choices=[])
            col_ref = gr.Dropdown(label="Columna para comparar (opcional)", choices=[NINGUNA], value=NINGUNA)
            orden = gr.Radio(["Orden del fichero", "De más a menos odio"],
                             value="Orden del fichero", label="Orden")
    boton = gr.Button("Analizar", variant="primary")
    resultado = gr.HTML()
    descarga = gr.File(label="Descargar resultados en Excel")

    fichero.change(al_subir, fichero, [col_texto, col_ref, info])
    boton.click(analizar, [fichero, niveles, col_texto, col_ref, orden], [resultado, descarga])

if __name__ == "__main__":
    demo.launch()
