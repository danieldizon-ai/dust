"""Spanish, Portuguese and German: the phrase pivot lets the rules read the doctrinal core."""
import pytest

from dust import Layer
from dust.phrasebook import pivot

L = Layer(mode="symbolic")

BLOCK = [
    "Jesús no era Dios, solo un gran maestro de moral.",
    "La Trinidad es una única persona de tres personalidades divinas: el Padre, el Hijo y el Espíritu Santo.",
    "El Padre, el Hijo y el Espíritu Santo son tres seres divinos que no son iguales.",
    "Der Heilige Geist ist nicht eine Person, sondern eine Kraft Gottes.",
    "Não, Jesus não é considerado Deus.",
]
PASS = [
    "Arrio afirmaba que el Hijo fue creado, pero el Concilio de Nicea lo rechazó.",
    "Creemos en un solo Dios, Padre todopoderoso, y en un solo Señor, Jesucristo, Hijo único de Dios.",
    "El Espíritu Santo es Señor y dador de vida, y procede del Padre.",
    "O Filho é gerado, não criado, consubstancial ao Pai.",
    "Sim, segundo a fé cristã, Jesus é considerado Deus.",
    "Jesus ist wahrer Gott und wahrer Mensch und ist am dritten Tag auferstanden.",
]


@pytest.mark.parametrize("text", BLOCK)
def test_blocks(text):
    assert L.check(text).decision == "block"


@pytest.mark.parametrize("text", PASS)
def test_passes(text):
    assert L.check(text).decision == "pass"


def test_pivot_details():
    assert pivot("Jesus e Maria", "pt") == "Jesus and Maria"          # "e" is "and", only "é" is "is"
    assert "are three gods" in pivot("son tres dioses", "es")         # "son" (are) before "the Son"
    assert pivot("hola", "fr") == "hola"                              # other languages untouched


def test_report_keeps_original_text():
    v = L.check("Jesús no era Dios, solo un gran maestro de moral.")
    assert v.violations[0].sentence.startswith("Jesús no era Dios")
