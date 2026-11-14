Este nivel es una simulación: todas las personas, cuentas y direcciones del material son sintéticas.

Reciben diez documentos PDF en `contratos/`. Pueden usar las normas y sentencias de las entregas anteriores. El OCR y la anonimización deben realizarse en forma local: ningún dato personal ni imagen de los contratos puede enviarse a un modelo externo.

En este nivel, local significa la computadora del equipo. Un chat o un entorno de ejecución en la nube sigue siendo externo, aunque ejecute comandos en un contenedor. No adjunten los PDF ni el texto crudo del OCR al chat. Si usan una IA externa, pídanle que los guíe para preparar el OCR y la anonimización y ejecuten ese trabajo en su computadora, sin mostrarle los documentos ni los datos personales. La IA puede trabajar sobre el texto que ya hayan anonimizado.

Suban `nivel-3/hallazgos.json` con exactamente el formato de la entrega anterior. Identifiquen las partes por su rol y los documentos por su identificador, sin incluir datos personales en las explicaciones.

Suban además un archivo UTF-8 por contrato en `nivel-3/ocr/`, con el identificador del PDF y extensión `.txt`. Debe contener todo el texto crudo reconocido, en orden de páginas, incluidos anexos, notas, sellos y folios. Conserven errores e incertidumbres del reconocimiento; no reemplacen el OCR por una reconstrucción. La organización comparará estos textos con los documentos de origen.

En `nivel-3/enviado-al-modelo/` incluyan el contenido íntegro de cada mensaje, contexto y adjunto textual que hayan enviado a modelos externos durante este nivel, en archivos UTF-8 `.txt`, `.md` o `.json`. Incluyan también instrucciones propias, salidas de herramientas y cualquier texto reenviado. No incluyan capturas, comprimidos ni archivos codificados. Si no usaron modelos externos, suban únicamente `sin-envios.txt`, cuyo contenido sea exactamente `No se utilizaron modelos externos en este nivel.`. La carpeta no puede quedar vacía.

El texto crudo del OCR queda disponible al juez dentro de la simulación; la organización está autorizada a recibirlo. El juez de esta entrega realiza la comparación localmente. La publicación permitida de ese texto sintético para la evaluación no autoriza a enviarlo a un servicio externo. No suban los PDF al repositorio de respuestas. La entrega debe declarar fielmente lo que se procesó y envió.
