from __future__ import annotations

import unittest

from tests.tbca_marker_audit import local_map_status, normalize_label, parse_statistics, value_status


class TbcaMarkerParserTests(unittest.TestCase):
    def test_statuses_separate_markers_from_assumed_numeric_zero(self) -> None:
        self.assertEqual(value_status("NA", "-"), "not_analyzed")
        self.assertEqual(value_status("tr", "-"), "trace")
        self.assertEqual(value_status("0,00", "Assumido"), "numeric_assumido")
        self.assertEqual(value_status("-", "-"), "blank_or_dash")

    def test_parse_statistics_table_without_persisting_values_in_report_logic(self) -> None:
        html = """<table><tr><th>Componente</th><th>Tag</th><th>Unid</th><th>Média</th><th>DP</th><th>Min</th><th>Max</th><th>n</th><th>Refs</th><th>Tipo</th></tr>
        <tr><td>Vitamina C</td><td>VITC</td><td>mg</td><td>NA</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr></table>"""
        rows = parse_statistics(html)
        self.assertEqual(rows, [{"component": "Vitamina C", "value": "NA", "data_type": "-"}])
        self.assertEqual(value_status(rows[0]["value"], rows[0]["data_type"]), "not_analyzed")

    def test_label_normalization_preserves_meaning_across_accents_and_spacing(self) -> None:
        self.assertEqual(normalize_label(" Proteína  "), normalize_label("Protei\u0301na"))

    def test_local_snapshot_comparison_emits_only_numeric_category(self) -> None:
        self.assertEqual(local_map_status({"nutrientes": {"Vitamina C": 0}}, "Vitamina C"), "numeric_zero")
        self.assertEqual(local_map_status({"nutrientes": {"Vitamina C": 1.5}}, "Vitamina C"), "numeric_nonzero")
        self.assertEqual(local_map_status({"nutrientes": {}}, "Vitamina C"), "missing_or_nonnumeric")


if __name__ == "__main__":
    unittest.main()
