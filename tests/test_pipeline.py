"""Pruebas del mapeo de canales y del gráfico combinado."""

import csv
import io
import unittest

from conversor import DIRECTOS, convertir_csv, leer_csv, nombre_descarga
from esquema import ESQUEMA_INSITE
from grafico import crear_grafico, _reducir_extremos


def _csv_bytes(filas):
    buffer = io.StringIO(newline="")
    csv.writer(buffer).writerows(filas)
    return buffer.getvalue().encode("utf-8")


def _archivos():
    base = [[] for _ in range(15)]
    base[0] = ["2", "3", "4", "12", "14", "16", "51"]
    base[13] = [nombre for nombre, _ in ESQUEMA_INSITE]
    base[14] = [unidad for _, unidad in ESQUEMA_INSITE]

    origen = [[] for _ in range(15)]
    origen[4] = ["ELG-137(h)"]
    origen[9] = ["job-58"]
    nombres = list(dict.fromkeys(["Time", *DIRECTOS.values(),
                                  "Stage At Blender", "Clean Density"]))
    nombres += [f"Extra {i}" for i in range(70 - len(nombres))]
    origen[13] = nombres
    origen[14] = ["(api)"] * 70
    valores = {
        "Treating Pressure": "7000", "Slurry Rate": "45",
        "Slurry Proppant Conc": "2.5", "BH Proppant Conc": "2.1",
        "FightR EC-3 Conc": "4", "FDP-S1278-17 Conc": "10",
        "Clean Rate": "40", "B1 Dirty Magnetic FM Rate": "5",
        "Clean Density": "8.3", "Job Slurry Vol": "420",
        "Stage At Blender": "58", "Job Proppant": "3",
    }
    for segundo in (0, 1, 2):
        fila = ["0"] * 70
        fila[0] = f"22-Nov-2026 12:00:{segundo:02d}"
        for nombre, valor in valores.items():
            fila[nombres.index(nombre)] = valor
        origen.append(fila)
    return _csv_bytes(origen), _csv_bytes(base)


class PipelineTest(unittest.TestCase):
    def test_conversion_y_cinco_escalas(self):
        origen, base = _archivos()
        contenido, filas, nombres = convertir_csv(origen, base)
        salida = leer_csv(contenido)
        self.assertEqual(len(filas), 3)
        self.assertEqual(salida[13], nombres)
        self.assertEqual(salida[14][39], "(lb/Mgal)")
        self.assertEqual([filas[0][i] for i in (2, 6, 31, 32, 37, 39)],
                         ["7000", "45", "2.5", "2.1", "4", "10"])
        grafico = crear_grafico(filas, "ET58")
        self.assertEqual(len(grafico.data), 6)
        self.assertEqual([traza.yaxis for traza in grafico.data],
                         ["y", "y2", "y3", "y3", "y4", "y5"])
        self.assertEqual(grafico.layout.yaxis.range[0], 0)
        self.assertEqual(grafico.layout.yaxis5.title.text,
                         "FR sólido proxy (lb/Mgal)")
        self.assertEqual(grafico.layout.xaxis.title.text,
                         "Tiempo transcurrido (min)")

    def test_slider_amplia_cada_eje_sin_cambiar_unidades(self):
        origen, base = _archivos()
        _, filas, _ = convertir_csv(origen, base)
        normal = crear_grafico(filas, "Convertido", escala=1.0)
        amplio = crear_grafico(filas, "Convertido", escala=2.0)
        for nombre in ("yaxis", "yaxis2", "yaxis3", "yaxis4", "yaxis5"):
            eje_normal = getattr(normal.layout, nombre)
            eje_amplio = getattr(amplio.layout, nombre)
            self.assertAlmostEqual(eje_amplio.range[1], eje_normal.range[1] * 2)
            self.assertEqual(eje_amplio.title.text, eje_normal.title.text)
        self.assertIn("psi", amplio.data[0].hovertemplate)

    def test_base_incompatible_se_rechaza(self):
        origen, base = _archivos()
        filas = leer_csv(base)
        filas[14][39] = "(gal/Mgal)"
        with self.assertRaisesRegex(ValueError, "esquema INSITE"):
            convertir_csv(origen, _csv_bytes(filas))

    def test_nombre_descarga_conserva_pozo_y_etapa(self):
        nombre = nombre_descarga("ELG-137(h)_58_202611211151.csv")
        self.assertEqual(nombre, "YPF.Nq.ELG-137(h)_ET58_FORMATO_YPF.csv")
        self.assertNotIn("SIMUL", nombre.upper())
        self.assertNotIn("ZIPPER", nombre.upper())

    def test_reduccion_conserva_pico(self):
        x = list(range(12000))
        y = [1.0] * len(x)
        y[5999] = 100.0
        xr, yr = _reducir_extremos(x, y)
        self.assertLessEqual(len(xr), 6002)
        self.assertEqual(yr[xr.index(5999)], 100.0)


if __name__ == "__main__":
    unittest.main()
