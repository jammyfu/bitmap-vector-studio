from vector_studio.presets import PRESETS, get_preset, options_from_preset


def test_all_presets_validate():
    for options in PRESETS.values():
        assert options.validate() is options


def test_get_preset_normalizes_dash_to_underscore():
    assert get_preset("pixel-art") == get_preset("pixel_art")


def test_options_override():
    options = options_from_preset("poster", {"color_precision": 8, "filter_speckle": 2})
    assert options.color_precision == 8
    assert options.filter_speckle == 2
