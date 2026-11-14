Reciben `leyes-de-platon.md` y tres documentos en `contratos/`. El expediente corresponde a la ciudad ficticia de Calípolis y se analiza exclusivamente con sus normas. Todas las personas, cuentas y direcciones del material son sintéticas.

Suban `nivel-1/hallazgos.json`, en UTF-8. Debe ser una lista de objetos con exactamente cuatro campos: `contrato` (identificador que aparece en el documento), `clausula` (identificador C01 a C10), `articulo` (número entero del artículo que fundamenta la incompatibilidad) y `explicacion` (texto de entre 40 y 3.000 caracteres).

Incluyan una sola fila por cláusula que consideren incompatible con las normas. Si hay más de un fundamento, indiquen en `articulo` el principal y desarrollen los demás en la explicación. No incluyan cláusulas que consideren válidas ni repitan una cláusula con otra redacción. La lista puede ordenarse libremente; no agreguen otros campos ni texto fuera del JSON.
