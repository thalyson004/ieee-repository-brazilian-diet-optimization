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
            "Torrada, trigo, tradicional": (
                "Torrada, tradicional, c/ farinha de trigo refinada, industrializada, Brasil (media diferentes amostras)",
                "BRC0169A",
            ),
            "Bebida, chá, preto, infusão 5%, s/ açúcar": (
                "Bebida, chá, preto, infusão 5%, s/ açúcar, Brasil", "BRC0013H"
            ),
            "Goiaba, inteira, in natura": (
                "Goiaba, inteira,in natura, Brasil (média diferentes amostras)", "BRC0014C"
            ),
            "Pequi, polpa, maduro, cru": (
                "Pequi, polpa, maduro,in natura, Brasil (média diferentes amostras)", "BRC0173C"
            ),
            "Pimentão, cru": (
                "Pimentão, cru, Brasil (média de diferentes tipos)", "BRC0031B"
            ),
            "Macarrão, trigo, c/ vegetais, c/ sal": (
                "Macarrão, farinha de trigo refinada, c/ vegetais, c/ sal, Brasil", "BRC0596A"
            ),
            "Laranja, in natura": (
                "Laranja,in natura, Brasil (média diferentes variedades)", "BRC0017C"
            ),
            "Bebida, chá, mate, infusão 5%, s/ açúcar": (
                "Bebida, chá, mate, infusão 5%, s/ açúcar, Brasil", "BRC0011H"
            ),
            "Bebida, chá, infusão, s/ açúcar (média de várias ervas)": (
                "Bebida, chá, infusão, s/ açúcar (média de várias ervas), Brasil", "BRC0015H"
            ),
            "Brócolos, flor, cozido, drenado, s/ óleo, c/ sal": (
                "Brócolis, flor, cozido, drenado, s/ óleo, c/ sal", "BRC0150B"
            ),
            "Castanha do Brasil, crua": (
                "Castanha do Brasil, crua, Brasil", "BRC0003U"
            ),
            "Mamão, Papaia, polpa, in natura": (
                "Mamão, Papaia, polpa,in natura, Brasil", "BRC0044C"
            ),
            "Quinoa, grão, cozida, s/ óleo, s/ sal": (
                "Quinoa, grão, cozida, s/ óleo, s/ sal (dado importado)", "BRC0399A"
            ),
            "Aveia, crua (média de diferentes tipos)": (
                "Aveia, crua, Brasil (média de diferentes tipos)", "BRC0021A"
            ),
            "Alface, crua": ("Alface, crua, Brasil", "BRC0009B"),
            "Leite, vaca, desnatado, fluído (média de diferentes amostras)": (
                "Leite, vaca, desnatado, fluído (média de diferentes amostras), Brasil", "BRC0036G"
            ),
            "Melão, polpa, in natura": ("Melão, polpa,in natura, Brasil", "BRC0028C"),
            "Ovo, galinha, mexido, c/ margarina, c/ sal": (
                "Ovo, galinha, mexido, c/ margarina, c/ sal, Brasil", "BRC0027J"
            ),
            "Castanha de caju, crua, s/ sal": (
                "Castanha de caju, crua, s/ sal, Brasil", "BRC0012U"
            ),
            "Linhaça, semente": ("Linhaça, semente, Brasil", "BRC0006U"),
            "Chia, semente, seca": ("Chia, semente, seca (dado importado)", "BRC0402A"),
            "Abacate, polpa, in natura": ("Abacate, polpa,in natura, Brasil", "BRC0001C"),
            "Cenoura, s/ casca, crua": ("Cenoura, s/ casca, crua, Brasil", "BRC0020B"),
            "Pepino, c/ casca, cru": ("Pepino, c/ casca, cru, Brasil", "BRC0030B"),
            "Tangerina, Ponkã, in natura": ("Tangerina, Ponkã,in natura, Brasil", "BRC0032C"),
            "Pizza, muçarela, caseira": (
                "Pizza, queijo muçarela, artesanal, assada, Brasil", "BRC0225A"
            ),
            "Cereal matinal, milho": ("Cereal matinal, milho, Brasil", "BRC0100A"),
            "Amendoim, torrado, c/ sal": ("Amendoim, torrado, c/ sal, Brasil", "BRC0021T"),
            "Amendoim, grão, cru": ("Amendoim, grão, cru, Brasil", "BRC0020T"),
            "Amêndoa, torrada, c/ sal": ("Amêndoa, torrada, c/ sal, Brasil", "BRC0001U"),
            "Beterraba, s/ casca, crua": ("Beterraba, s/ casca, crua, Brasil", "BRC0015B"),
            "Acelga, crua": ("Acelga, crua, Brasil", "BRC0007B"),
            "Abacaxi, polpa, in natura": ("Abacaxi, polpa,in natura, Brasil", "BRC0002C"),
            "Queijo, coalho": ("Queijo, coalho, Brasil", "BRC0048G"),
            "Cream cheese (média de diferentes sabores)": (
                "Cream cheese, Brasil (média de diferentes sabores)", "BRC0006G"
            ),
            "Iogurte, integral (média de diferentes sabores)": (
                "Iogurte, integral (média de diferentes sabores), Brasil", "BRC0011G"
            ),
            "Queijo, requeijão (média de diferentes amostras)": (
                "Queijo, requeijão (média de diferentes amostras), Brasil", "BRC0066G"
            ),
            "Pinhão, cozido, s/ sal": ("Pinhão, cozido, s/ sal, Brasil", "BRC0007U"),
            "Repolho, roxo, cru": ("Repolho, roxo, cru, Brasil", "BRC0080B"),
            "Chuchu, s/ casca, cozido, drenado, s/ óleo, c/ sal": (
                "Chuchu, s/ casca, cozido, drenado, s/ óleo, c/ sal, Brasil", "BRC0154B"
            ),
            "Manteiga, c/ sal": ("Manteiga, c/ sal, Brasil", "BRC0007D"),
            "Queijo, ricota": ("Queijo, ricota, Brasil", "BRC0051G"),
            "Pistache, cru, s/ sal": ("Pistache, cru, s/ sal (dado importado)", "BRC0015U"),
            "Melancia, polpa, in natura": ("Melancia, polpa,in natura, Brasil", "BRC0027C"),
            "Uva, in natura": ("Uva,in natura, Brasil", "BRC0033C"),
            "Chicória, crua": ("Chicória, crua, Brasil", "BRC0071B"),
            "Espinafre, folha, cru": ("Espinafre, folha, cru, Brasil", "BRC0072B"),
            "Rúcula, crua": ("Rúcula, crua, Brasil", "BRC0081B"),
            "Soja, extrato, bebida (média de diferentes sabores)": (
                "Soja, extrato, bebida (média de diferentes sabores), Brasil", "BRC0042T"
            ),
            "Geleia, s/ açúcar (média de diferentes sabores)": (
                "Geleia, s/ açúcar, Brasil (média de diferentes sabores)", "BRC0058N"
            ),
            "Margarina, c/ óleo interesterificado (65% lipídeos), s/ sal": (
                "Margarina, c/ óleo interesterificado (65% lipídeos), s/ sal, Brasil", "BRC0013D"
            ),
            "Pão, de queijo, industrializado, assado": (
                "Pão, de queijo, industrializado, assado, Brasil", "BRC0123B"
            ),
            "Queijo, ricota, light": ("Queijo, ricota, light, Brasil", "BRC0075N"),
            "Biscoito, salgado, cream cracker": (
                "Biscoito, salgado, cream cracker, Brasil", "BRC0201A"
            ),
            "Uva, passa, preta": ("Uva, passa, preta, Brasil", "BRC0169C"),
            "Abóbora, moranga, s/ casca, s/ semente, assada, s/ óleo, c/ sal": (
                "Abóbora, moranga, s/ casca, s/ semente, assada, s/ óleo, c/ sal, Brasil", "BRC0355B"
            ),
            "Cebolinha, verde, crua": ("Cebolinha, verde, crua, Brasil", "BRC0019B"),
            "Soja, extrato, solúvel, em pó": ("Soja, extrato, solúvel, em pó, Brasil", "BRC0048T"),
            "Biscoito, doce, simples (média de diferentes tipos)": (
                "Biscoito, doce, simples (média de diferentes tipos), Brasil", "BRC0027A"
            ),
            "Milho, verde, grão, cozido, drenado, c/ sal": (
                "Milho, verde, grão, cozido, drenado, c/ sal, Brasil", "BRC0177A"
            ),
            "Abobrinha, italiana, c/ casca, crua": (
                "Abobrinha, italiana, c/ casca, crua, Brasil", "BRC0006B"
            ),
            "Azeitona, verde, conserva, drenada": (
                "Azeitona, verde, conserva, drenada, Brasil", "BRC0121B"
            ),
            "Rabanete, c/ casca, cru": ("Rabanete, c/ casca, cru, Brasil", "BRC0079B"),
            "Pêssego, in natura": ("Pêssego,in natura, Brasil", "BRC0031C"),
            "Mandioca, farinha, crua": ("Mandioca, farinha, crua, Brasil", "BRC0087B"),
            "Carne, boi, seca, cozida, s/ óleo": (
                "Carne, boi, seca, cozida, s/ óleo, Brasil", "BRC0085F"
            ),
            "Peixe, água salgada, atum, sólido, conserva, light": (
                "Peixe, água salgada, atum, sólido, conserva, light, Brasil", "BRC0053N"
            ),
            "Queijo, pasteurizado (média de diferentes amostras)": (
                "Queijo, pasteurizado (média de diferentes amostras), Brasil", "BRC0062G"
            ),
            "Leite, vaca, desnatado, em pó": (
                "Leite, vaca, desnatado, em pó, Brasil", "BRC0038G"
            ),
            "Nabo, c/ casca, cru": ("Nabo, c/ casca, cru, Brasil", "BRC0077B"),
            "Palmito, conversa, drenado (média de variedades - Pupunha e Juçara)": (
                "Palmito, conversa, drenado (média de variedades - Pupunha e Juçara), Brasil", "BRC0078B"
            ),
            "Peixe, água salgada, sardinha, filé, conserva, em óleo": (
                "Peixe, água salgada, sardinha, filé, conserva, em óleo, Brasil", "BRC0073E"
            ),
            "Bebida, café, infusão 8% - médio, s/ açúcar": (
                "Bebida, café, infusão 8% - médio, s/ açúcar, Brasil", "BRC0062H"
            ),
            "Trigo para quibe, cozido, s/ sal": (
                "Trigo para quibe (kibe), cozido, s/ óleo, s/ sal (dado importado)", "BRC0405A"
            ),
            "Carne, boi, acém moída, cozida, c/ óleo, cebola e alho, c/ sal": (
                "Carne, bovina, moída (acém), cozida, c/ óleo de soja, cebola e alho, c/ sal, Brasil", "BRC0354F"
            ),
            "Carne, boi, acém, moída, refogada (c/ óleo, cebola e alho), c/ sal": (
                "Carne, bovina, moída (acém), refogada (c/ óleo de soja, cebola e alho), c/ sal, Brasil", "BRC0245F"
            ),
            "Peixe, água doce, filé, grelhado/assado, s/ óleo, s/ sal (média de 7 espécies)": (
                "Peixe, água doce, filé, grelhado/assado, s/ óleo, s/ sal (média de 7 espécies), Brasil", "BRC0105E"
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
