# Print Scale 1.1.0

Complemento para Blender 4.2 a 5.x. Elige el **tamaño de impresión** y te dice, antes de imprimir, qué zonas dejan de salir con tu boquilla.


## Qué cambia en 1.1.0

- **Toda la figura**: si el modelo viene en varias piezas (un 3MF de colores, una figura con ojos y brazos aparte), al seleccionar una se escalan **todas juntas**, con el mismo factor y desde la base del conjunto, para que sigan encajando. También encuentra las copias reparadas con Mesh Doctor o Print Ready. Se puede desmarcar para escalar solo una pieza.
- Con varias piezas seleccionadas a mano, se escalan esas, juntas.
## Uso (pestaña Print Scale)

1. Selecciona el modelo: muestra su tamaño actual en mm.
2. Elige cómo escalar: **Alto**, **Lado mayor**, **Largo X**, **Fondo Y**, **Porcentaje**, **Escala 1:N** (modelismo, a partir del tamaño real) o **Que quepa** en tu impresora.
3. **Comprobar**: tamaño nuevo, si cabe en la impresora y qué parte del modelo queda:
   - **roja**: más fina que la boquilla → no se imprime;
   - **ámbar**: más fina que dos pasadas → sale frágil.
   Las zonas se marcan con puntos sobre el modelo (no lo modifican).
4. **Aplicar tamaño**: crea `<modelo>_<alto>mm` escalado desde el centro de la base; el original queda oculto. Colores conservados.

Si quedan zonas rojas: engrósalas con **Thicken** o elige un tamaño mayor.
