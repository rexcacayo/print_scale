# Print Scale 1.0.0

Complemento para Blender 4.2 a 5.x. Elige el **tamaño de impresión** y te dice, antes de imprimir, qué zonas dejan de salir con tu boquilla.

## Uso (pestaña Print Scale)

1. Selecciona el modelo: muestra su tamaño actual en mm.
2. Elige cómo escalar: **Alto**, **Lado mayor**, **Largo X**, **Fondo Y**, **Porcentaje**, **Escala 1:N** (modelismo, a partir del tamaño real) o **Que quepa** en tu impresora.
3. **Comprobar**: tamaño nuevo, si cabe en la impresora y qué parte del modelo queda:
   - **roja**: más fina que la boquilla → no se imprime;
   - **ámbar**: más fina que dos pasadas → sale frágil.
   Las zonas se marcan con puntos sobre el modelo (no lo modifican).
4. **Aplicar tamaño**: crea `<modelo>_<alto>mm` escalado desde el centro de la base; el original queda oculto. Colores conservados.

Si quedan zonas rojas: engrósalas con **Thicken** o elige un tamaño mayor.
