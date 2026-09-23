# Original LLM-generation provenance

The repository preserves the three prompt files and the 150 normalized weekly diets, but it does not preserve the raw API responses or request logs. Consequently, the exact API model identifier, access date, SDK/API, inference parameters, seed support, retry policy, failures, and regenerations cannot be reconstructed.

There is conflicting secondary evidence about the model name. Parent-project documentation contemporaneous with the initial dataset describes **Gemini 2.5 Flash**, whereas later availability-repository and manuscript text describes **Gemini 3-Flash**. Neither label is treated as verified without the original request logs.

`original-generation-metadata.json` records this evidence field by field. `../prompts/manifest.json` records SHA-256 hashes and shows that the published prompts are byte-identical across the three available repository copies. This proves preservation of the published files, but not that those exact bytes were sent in every original API request.

The base-diet audit operates only on the normalized JSON datasets. It must not be used to infer the number of invalid raw responses or regeneration attempts.
