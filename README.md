# Conversor ET58 → formato INSITE de ET50

**App pública:** https://luctiv-conversor-et58-et50.streamlit.app/  
**Código:** https://github.com/LucasVuletin/luctiv-conversor-et58-et50

Aplicación Streamlit para cargar dos CSV: el INSITE de la etapa 50 como base de
estructura y el Treatment Data Publisher (TDP) de la etapa 58 como origen de
los valores. Genera un CSV INSITE de 51 canales con el encabezado y orden del
archivo base. La salida lleva la marca `SIMUL`.

## Ejecutar en local

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

En la página, cargar primero el CSV INSITE de ET50 y después el CSV TDP de ET58.
La app no necesita rutas locales a los datos: los archivos se suben en la sesión.
Descargar el CSV generado después de revisar el gráfico y los controles.

## Gráfico

Hay un solo gráfico para todas las señales. Permite alternar entre ET58 convertido
y ET50 base cuando el archivo base contiene muestras. Cada eje conserva la unidad
del canal INSITE:

| Señal | Canal | Eje |
| --- | --- | --- |
| Presión | `PRESION_PPAL` | psi |
| Caudal | `CAUDAL_SLURRY` | bpm |
| Arena en superficie y fondo | `CONC_SLURRY`, `CONC_FONDO` | lb/gal compartido |
| FR líquido | `FightR Conc` | gal/Mgal |
| FR sólido | `FightR LXD Conc` | lb/Mgal |

Cada escala se calcula por separado y empieza en cero cuando sus valores no son
negativos. La reducción visual de series largas preserva máximos y mínimos por
intervalo; el CSV descargable siempre incluye todos los registros.

**Advertencia de interpretación:** en la conversión de ET58, el canal de FR sólido
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

- El CSV base debe seguir el esquema INSITE de 51 canales, con 15 filas de
  preámbulo y los nombres/unidades esperados en todas las posiciones.
- El origen TDP debe contener los canales usados por el conversor. Las filas de
  eventos de tres campos se omiten.
- Se mantiene el orden, nombres y unidades del archivo base. El preámbulo
  conserva su estructura, pero actualiza pozo, fecha, identificador y zona
  horaria. Las muestras se desplazan desde UTC según el valor configurado
  (UTC-3 por defecto).
- Las fórmulas y factores estimados proceden de la homologación previa de
  ELG-137 ET58 contra un archivo ELG-136. Validar la salida con ingeniería antes
  de usarla para decisiones operativas o entregas a clientes.
- Los canales sin medición se escriben como cero. Cero no implica lectura de
  sensor. Los controles de integración asumen muestreo de un segundo.
