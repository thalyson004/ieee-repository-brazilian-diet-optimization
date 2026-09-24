# Correções de mapeamentos alimentares — 2026-09-24

Esta é uma trilha de auditoria separada da fila histórica `food-mapping-review-queue`: ela registra sete erros evidentes no mapa TBCA ativo e as correções apoiadas por correspondência de nome, estado/preparo e registro oficial da TBCA. O mapa ambiental não foi alterado. As referências abaixo sustentam a identidade do registro; não significam validação nutricional clínica nem revisão de todas as 170 equivalências não identitárias.

| Alimento de origem | Registro TBCA ativo | Código | Justificativa da correção | Fonte primária |
|---|---|---|---|---|
| Tomate, in natura | Tomate, cru, Brasil | BRC0035B | Mesmo alimento em estado cru; o registro anterior era pitaia. | [TBCA — tomate cru](https://www.tbca.net.br/base-dados/int_composicao_estatistica.php?n0REd3kv7e86D%2BViXWYUnQ%3D%3D=0qP6TPuuLlp52oyveljmug%3D%3D) |
| Pão francês, trigo, branco, de padaria (médias de diferentes amostras) | Pão francês de padaria, farinha refinada, médias de amostras | BRC0002A | O registro descreve pão francês de padaria e farinha refinada; o anterior era queijo prato. | [TBCA — pão francês](https://www.tbca.net.br/base-dados/int_composicao_estatistica.php?n0REd3kv7e86D%2BViXWYUnQ%3D%3D=%2Fs6Hd1%2FWTFwO5veBwRglNg%3D%3D) |
| Morango, in natura | Morango, in natura, Brasil, média de amostras | BRC0029C | Correspondência direta de alimento e estado cru; o anterior era amora-preta. | [TBCA — morango](https://www.tbca.net.br/base-dados/int_composicao_estatistica.php?n0REd3kv7e86D%2BViXWYUnQ%3D%3D=b7WfIT%2FR72TNSHwxAYkp5A%3D%3D) |
| Kiwi, in natura | Kiwi, in natura, Brasil | BRC0061C | Correspondência direta de alimento e estado cru; o anterior era pitaia. | [TBCA — kiwi](https://www.tbca.net.br/base-dados/int_composicao_estatistica.php?n0REd3kv7e86D%2BViXWYUnQ%3D%3D=K5WD7sv2VBQFAmPbA1F7Rg%3D%3D) |
| Pera, in natura | Pera com casca, in natura, média de variedades | BRC0030C | Correspondência por alimento e estado cru; a casca é explicitada pelo registro TBCA, não pelo nome de origem. | [TBCA — pera](https://www.tbca.net.br/base-dados/int_composicao_alimentos.php?n0REd3kv7e86D%2BViXWYUnQ%3D%3D=pWC8SadNj49tHN5%2BKJavzQ%3D%3D) |
| Almeirão, cru | Almeirão (chicória amarga), cru, Brasil | BRC0011B | Correspondência direta por nome botânico/comum e estado cru; o anterior era amendoim. | [TBCA — listagem de almeirão](https://www.tbca.net.br/base-dados/composicao_estatistica.php?atuald=2&pagina=12) |
| Caqui, in natura | Caqui com casca, in natura, Brasil | BRC0012C | Correspondência direta por alimento e estado cru; o registro explicita casca. | [TBCA — caqui](https://www.tbca.net.br/base-dados/int_composicao_estatistica.php?n0REd3kv7e86D%2BViXWYUnQ%3D%3D=WYKNZPNxh4q%2Fpr%2F1jtPujg%3D%3D) |

**Pendente, sem alteração:** `Cacau, in natura` permanece mapeado como estava. A denominação de origem não esclarece se representa polpa do fruto ou amêndoa/semente, portanto não há base suficiente para escolher um registro TBCA.

**Escopo da correção:** foram atualizados somente `maps/base/mapa-sustentavel-nome.json` e seu mapa de códigos derivado `maps/derived/mapa-sustentavel-tbca.json`. A auditoria submetida arquivada não foi reescrita, preservando o retrato histórico. O experimento de replicação anterior continua sendo diagnóstico do mapa anterior e não deve ser apresentado como a replicação corrigida.
