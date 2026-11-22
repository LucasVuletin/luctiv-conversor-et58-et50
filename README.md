# Conversor de variables WRST a variables para YPF

**App pública:** https://luctiv-conversor-et58-et50.streamlit.app/  
**Código:** https://github.com/LucasVuletin/luctiv-conversor-et58-et50

Aplicación Streamlit para cargar dos CSV: uno INSITE como base de la estructura
para YPF y uno WRST de Treatment Data Publisher (TDP) como origen de los valores.
Genera un CSV INSITE de 51 columnas físicas con el encabezado y orden del
archivo base. El nombre descargado conserva pozo y etapa, y termina en
`_FORMATO_YPF.csv`.

## Ejecutar en local

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

En la página, cargar primero el CSV INSITE base y después el CSV WRST/TDP.
La app no necesita rutas locales a los datos: los archivos se suben en la sesión.
Descargar el CSV generado después de revisar el gráfico y los controles.

## Gráfico

Hay un solo gráfico para todas las señales. Permite alternar entre el archivo
convertido y el base cuando éste contiene muestras. Cada eje conserva la unidad
del canal INSITE:

| Señal | Canal | Eje |
| --- | --- | --- |
| Presión | `PRESION_PPAL` | psi |
| Caudal | `CAUDAL_SLURRY` | bpm |
| Arena en superficie y fondo | `CONC_SLURRY`, `CONC_FONDO` | lb/gal compartido |
| FR líquido | `FightR Conc` | gal/Mgal |
| FR sólido | `FightR LXD Conc` | lb/Mgal |

Cada escala se calcula por separado y empieza en cero cuando sus valores no son
negativos. Un slider ajusta simultáneamente el rango vertical de los cinco ejes
del 100 % al 300 % sin mezclar unidades: bajarlo acerca y subirlo deja más espacio.
El eje horizontal muestra minutos transcurridos desde la primera muestra. La
reducción visual de series largas preserva máximos y mínimos por intervalo; el
CSV descargable siempre incluye todos los registros.

**Advertencia de interpretación:** en el archivo convertido, el canal de FR sólido
se rellena con `FDP-S1278-17 Conc` por compatibilidad de unidades. Es un proxy,
no una lectura directa de FightR LXD ni una equivalencia química.

## Publicar cambios

La app está desplegada desde la rama `main`, con `app.py` como punto de entrada.
Para actualizarla, subir los cambios al repositorio de GitHub; Streamlit
Community Cloud volverá a desplegar la rama.

No subir CSV operativos al repositorio público. Los usuarios cargan sus archivos
desde la interfaz. Si se publica un repositorio privado, revisar la configuración
de visibilidad de la app antes de compartir el enlace.

## Formato y límites

- El CSV base debe seguir el esquema INSITE de 51 columnas, con 15 filas de
  preámbulo y los nombres/unidades esperados en todas las posiciones.
- El TDP de referencia contiene 70 columnas físicas; el origen debe incluir
  los canales usados por el conversor. Las filas de eventos de tres campos se
  omiten.
- Se mantiene el orden, nombres y unidades del archivo base. El preámbulo
  conserva su estructura, pero actualiza pozo, fecha, identificador y zona
  horaria. Las muestras se desplazan desde UTC según el valor configurado
  (UTC-3 por defecto).
- Las fórmulas y factores estimados proceden de la homologación previa de
  ELG-137 ET58 contra un archivo ELG-136. Validar la salida con ingeniería antes
  de usarla para decisiones operativas o entregas a clientes.
- Los canales sin medición se escriben como cero. Cero no implica lectura de
  sensor. Los controles de integración asumen muestreo de un segundo.
