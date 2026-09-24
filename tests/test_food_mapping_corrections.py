"""Regression checks for the individually sourced TBCA mapping corrections."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FoodMappingCorrectionTests(unittest.TestCase):
    def test_corrected_names_and_codes_are_consistent(self) -> None:
        name_map = json.loads(
            (ROOT / "maps/base/mapa-sustentavel-nome.json").read_text(encoding="utf-8")
        )
        code_map = json.loads(
            (ROOT / "maps/derived/mapa-sustentavel-tbca.json").read_text(encoding="utf-8")
        )
        tbca_names = json.loads(
            (ROOT / "maps/base/mapa-nome-tbca.json").read_text(encoding="utf-8")
        )
        expected = {
            "Tomate, in natura": ("Tomate, cru, Brasil", "BRC0035B"),
            "Pão francês, trigo, branco, de padaria (médias de diferentes amostras)": (
                "Pão francês (cacetinho, de sal, média), de padaria, c/ farinha de trigo refinada, Brasil  (médias de diferentes amostras)",
                "BRC0002A",
            ),
            "Morango, in natura": ("Morango,in natura, Brasil (média diferentes amostras)", "BRC0029C"),
            "Kiwi, in natura": ("Kiwi (quiuí),in natura, Brasil", "BRC0061C"),
            "Pera, in natura": (
                "Pera, c/ casca,in natura, Brasil (média diferentes variedades)", "BRC0030C"
            ),
            "Almeirão, cru": ("Almeirão (chicória amarga), cru, Brasil", "BRC0011B"),
            "Caqui, in natura": ("Caqui,  c/ casca,in natura, Brasil", "BRC0012C"),
            "Banana, in natura": ("Banana,in natura(média diferentes variedades), Brasil", "BRC0006C"),
            "Pão, trigo, integral, forma (média de diferentes marcas)": (
                "Pão, integral, c/ farinha de trigo refinada, forma (média de diferentes marcas), Brasil",
                "BRC0155A",
            ),
            "Suco, laranja, s/ açúcar": (
                "Suco, laranja, s/ açúcar (média diferentes variedades)", "BRC0038C"
            ),
            "Bebida, café, infusão 10%, s/ açúcar": (
                "Bebida, café, infusão 10%, s/ açúcar, Brasil", "BRC0007H"
            ),
            "Azeite, oliva": ("Azeite, oliva, Brasil", "BRC0002D"),
            "Arroz, integral, cozido, c/ óleo, cebolha e alho, c/ sal": (
                "Arroz, integral, cozido, c/ óleo, cebola e alho, c/ sal, Brasil", "BRC0211A"
            ),
            "Maçã, c/ casca, in natura": (
                "Maçã, c/ casca,in natura, Brasil (média diferentes variedades)", "BRC0023C"
            ),
            "Feijão, carioca, cozido (50% grão e 50% caldo), c/ óleo, cebola e alho, c/ sal": (
                "Feijão carioca, cozido (50% grão e 50% caldo), c/ óleo de soja, cebola e alho, c/ sal, Brasil",
                "BRC0091T",
            ),
        }
        for source, (expected_name, expected_code) in expected.items():
            with self.subTest(source=source):
                self.assertEqual(name_map[source], expected_name)
                self.assertEqual(code_map[source], expected_code)
                self.assertEqual(tbca_names[expected_name], expected_code)

    def test_ambiguous_cacao_mapping_is_not_changed(self) -> None:
        name_map = json.loads(
            (ROOT / "maps/base/mapa-sustentavel-nome.json").read_text(encoding="utf-8")
        )
        code_map = json.loads(
            (ROOT / "maps/derived/mapa-sustentavel-tbca.json").read_text(encoding="utf-8")
        )
        self.assertEqual(name_map["Cacau, in natura"], "Pitaia,in natura")
        self.assertEqual(code_map["Cacau, in natura"], "BRC0225C")


if __name__ == "__main__":
    unittest.main()
