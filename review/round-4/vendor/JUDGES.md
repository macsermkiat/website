# Judges on vendor, round 4 pass 1

## Improve

Failed:
- Lebkuchen hearts read as gingerbread: three_lebkuchen_tag.jpg: the hanging hearts render near-black with little visible icing, so they read as burnt or dark chocolate rather than brown Lebkuchen

Fixes:
- Brighten the Lebkuchen heart material in the engine (albedo and roughness) so the hearts read as warm brown gingerbread with bright icing under the stall lighting, not near-black.
- Push the Maß beer toward a lighter, more saturated Helles gold (raise the top colour's value, or add a mild emissive lift) so it is not muddy amber.
- Raise the lite glass_pint alpha to about 0.2 so the emptied glasses read as glasses.
- Re-render prop_bier_counter_hero.jpg with the current material names and the preview-only beer_preview setup.
