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
            "Arroz, polido, cozido, c/ óleo, cebola e alho, c/ sal": (
                "Arroz polido, cozido, c/ óleo de soja, cebola e alho, c/ sal, Brasil", "BRC0209A"
            ),
            "Biscoito, arroz": ("Biscoito, farinha de arroz (dado importado)", "BRC0836A"),
            "Macarrão, trigo, cozido, drenado, s/ óleo, c/ sal": (
                "Macarrão, farinha de trigo refinada, cozido, drenado, s/ óleo, c/ sal, Brasil",
                "BRC0834A",
            ),
            "Pão, sírio, branco": ("Pão, sírio, farinha de trigo refinada (dado importado)", "BRC0575A"),
            "Soja, tofu": ("Tofu, soja, s/ sal, Brasil", "BRC0056T"),
            "Queijo, muçarela, light": (
                "Queijo, muçarela (mussarela, muzarela, mozarela), light, Brasil", "BRC0074N"
            ),
            "Soja, extrato, bebida, natural (média de diferentes amostras)": (
                "Soja, extrato, bebida, natural, Brasil", "BRC0043T"
            ),
            "Leite, vaca, integral, fluído": (
                "Leite, vaca, integral, fluído, pasteurizado, Brasil (média de diferentes amostras)",
                "BRC0043G",
            ),
            "Iogurte, frutas, diet": ("Iogurte, frutas, dietético (dado importado)", "BRC0073N"),
            "Coco, água": ("Coco, água, industrializada, Brasil", "BRC0174C"),
            "Couve, crua": ("Couve, manteiga, crua, Brasil", "BRC0023B"),
            "Coco, leite": ("Coco, leite, industrializado, Brasil", "BRC0175C"),
            "Queijo, prato": ("Queijo, prato, Brasil (média de diferentes amostras)", "BRC0064G"),
            "Queijo, muçarela (média de diferentes amostras)": (
                "Queijo, leite de vaca, muçarela (mussarela, muzarela, mozarela), Brasil (média de diferentes amostras)",
                "BRC0059G",
            ),
            "Biscoito, doce, maisena": (
                "Biscoito, doce, maisena (amido de milho), Brasil", "BRC0200A"
            ),
            "Risoto de legumes, c/ arroz polido, c/ sal": (
                "Risoto de legumes, c/ arroz polido, c/ sal, Brasil", "BRC0623A"
            ),
            "Avelã , crua, s/ sal": ("Avelã , crua, s/ sal (dado importado)", "BRC0013U"),
            "Manga, polpa, in natura": (
                "Manga, polpa,in natura, Brasil (média diferentes variedades)", "BRC0025C"
            ),
            "Canela, em pó": ("Canela, em pó (dado importado)", "BRC0778B"),
            "Cuscuz de milho, cozido, c/ sal": (
                "Farinha de milho, cuscuz, cozido no vapor, c/ sal, Brasil", "BRC0409A"
            ),
            "Coco, polpa, in natura": (
                "Coco, maduro, polpa,in natura, Brasil", "BRC0013C"
            ),
            "Repolho, cru": ("Repolho, branco, cru, Brasil", "BRC0033B"),
            "Mamão, polpa, in natura": (
                "Mamão, polpa,in natura, Brasil (média diferentes variedades)", "BRC0024C"
            ),
            "Torrada, trigo, integral": (
                "Torrada, integral, c/ farinha de trigo refinada, Brasil", "BRC0170A"
            ),
            "Pão, trigo, leite, industrializado (média de diferentes marcas)": (
                "Pão, de leite, c/ farinha de trigo refinada, industrializado (média de diferentes marcas), Brasil",
                "BRC0147A",
            ),
        }
        adjudication = json.loads(
            (ROOT / "archive/audits/adjudicated-food-map-sources.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(adjudication["source_food_names"]), set(expected))
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
