---
title: Discurso de odio con pysentimiento
emoji: 🔎
colorFrom: green
colorTo: red
sdk: gradio
sdk_version: 5.49.1
python_version: "3.11"
app_file: app.py
pinned: false
---

# 🔎 Evaluación de discurso de odio

Aplicación web que hace lo mismo que el notebook `Pysentimiento_discurso_odio_BI`:

1. Carga un Excel (la primera fila es la cabecera) y toma los mensajes de una columna (por defecto, la 2ª).
2. Pide el número de **NIVELES**.
3. Analiza cada mensaje con `pysentimiento` (`create_analyzer(task="hate_speech", lang="es")`) y calcula
   `nivel = P(hateful) × NIVELES`.
4. Muestra el resultado directamente en la web: escala de color de verde a rojo, una caja coloreada con el nivel de cada mensaje,
   un resumen por tramos y, opcionalmente, otra columna del Excel para comparar (por ejemplo, `Final Scores`).
5. Permite descargar un Excel con los resultados (`nivel_odio`, `prob_hateful`, `prob_targeted` y `prob_aggressive`).

## Ficheros

| Fichero | Qué hace |
|---|---|
| `README.md` | Este texto. La cabecera entre `---` es la configuración del Space: no la borres. |
| `app.py` | La aplicación (Gradio + pysentimiento) |
| `requirements.txt` | Librerías que instala Hugging Face |
| `mensajes-BI.xlsx` | Excel de ejemplo (opcional) |

## Publicarlo en Hugging Face Spaces (gratis)

1. Crea una cuenta en <https://huggingface.co/join>.
2. Ve a <https://huggingface.co/new-space>.
   - **Space name**: por ejemplo, `discurso-odio`.
   - **Space SDK**: **Gradio**.
   - **Hardware**: *CPU basic · Free*.
   - **Visibility**: *Public* o *Private*, como prefieras.
   - Pulsa **Create Space**.
3. En el Space, ve a la pestaña **Files**, pulsa **+ Contribute → Upload files** y arrastra
   `app.py`, `requirements.txt` y `README.md`. Pulsa **Commit changes to main**. Si te pregunta, sustituye el `README.md` que crea por defecto.
4. Vuelve a la pestaña **App**. Verás *Building*: instala las librerías y descarga el modelo
   (la primera vez tarda unos 3–6 minutos). Cuando ponga *Running*, ya está lista.
5. La dirección será `https://huggingface.co/spaces/TU_USUARIO/discurso-odio`.

Notas:
- En el plan gratuito, el Space **se duerme tras 48 h sin visitas**. Al entrar de nuevo se despierta solo, pero tarda uno o dos minutos.
- El análisis de 70 mensajes tarda unos segundos en la CPU gratuita.
- Si el Space es público, cualquiera puede usar la app. Los ficheros que suben los usuarios no se publican.

## Probar en local

```bash
pip install -r requirements.txt gradio
python app.py   # abre http://127.0.0.1:7860
```
