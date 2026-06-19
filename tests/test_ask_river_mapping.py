from core.recipes import ask_river_recipe_types


def test_ask_river_clean_duplicates_maps_to_duplicate_recipe():
    mapped = ask_river_recipe_types("clean up duplicates and rename the rest")
    assert mapped[:2] == ["clean_duplicates", "clean_names"]


def test_ask_river_sort_by_type_maps_to_composition_recipe():
    mapped = ask_river_recipe_types("sort this folder by type")
    assert mapped[:2] == ["sort_by_composition", "separate_mixed_folder"]
