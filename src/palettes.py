"""Coordinated native color presets, including the exported background."""

import copy
import colorsys
from native_extension import defaults, profile_preset, validate
from native_boot_color import preset as classic_effects

GROUPS = ("Alle", "Basis", "Hell", "Dunkel", "Pastell", "Zweifarbig")

# ID, label, group, primary, background, lettering accent, sphere material.
PALETTES = [
    ("original", "Xbox Original", "Basis", None, None, None, None),
    ("blue", "Blau · Standard", "Basis", None, None, None, None),
    ("cyan", "Cyan · Standard", "Basis", None, None, None, None),
    ("purple", "Violett · Standard", "Basis", None, None, None, None),
    ("ice", "Eisblau", "Hell", "#009DFF", "#F4FAFF", "#7894A8", "#414B56"),
    ("sapphire", "Saphir", "Hell", "#2855FF", "#F2F4FF", "#8E94B7", "#454759"),
    ("ocean", "Ozean", "Hell", "#00B6C9", "#F1FCFC", "#659B9E", "#354E51"),
    ("mint", "Mint", "Hell", "#00CB93", "#F2FFF9", "#679B86", "#3C534A"),
    ("lime", "Limette", "Hell", "#82CC00", "#FAFFF0", "#8D9C66", "#47553A"),
    ("lavender", "Lavendel", "Hell", "#9560FF", "#FBF7FF", "#9C85B1", "#4C425D"),
    ("rose", "Rose", "Hell", "#ED55A6", "#FFF5FA", "#AF819A", "#58414C"),
    ("coral", "Koralle", "Hell", "#F66D5E", "#FFF7F3", "#B0877D", "#594944"),
    ("sunrise", "Sonnenaufgang", "Hell", "#FF9C28", "#FFFAF0", "#AE966D", "#5A513D"),
    ("gold", "Gold", "Hell", "#E7AE35", "#FFFBF2", "#A39778", "#58513F"),
    ("black_blue", "Blau auf Schwarz", "Dunkel", "#168BFF", "#000000", "#CEE6FF", "#303B4F"),
    ("midnight", "Midnight Blue", "Dunkel", "#329EFF", "#080D1B", "#A8C5F3", "#30394D"),
    ("arctic", "Arctic Night", "Dunkel", "#63DFFF", "#06131C", "#A1CBD8", "#2C414B"),
    ("black_cyan", "Cyan auf Schwarz", "Dunkel", "#00F0E0", "#000000", "#B6F4EF", "#294543"),
    ("emerald", "Smaragd-Nacht", "Dunkel", "#20E8A0", "#051711", "#A3D9C4", "#294A3D"),
    ("forest", "Waldnacht", "Dunkel", "#A1DE59", "#0C1608", "#CDDBB9", "#3B4930"),
    ("purple_night", "Violette Nacht", "Dunkel", "#AA70FF", "#11091E", "#D9C5F5", "#40324F"),
    ("neon_pink", "Neon Pink", "Dunkel", "#FF40BA", "#19091A", "#FFD3EB", "#4D2F46"),
    ("crimson", "Crimson Black", "Dunkel", "#FF405B", "#000000", "#FFD0D7", "#4B2D34"),
    ("ember", "Glut", "Dunkel", "#FF782E", "#190C06", "#FFD2B2", "#4D372B"),
    ("bronze", "Bronze-Nacht", "Dunkel", "#DE9B55", "#170F09", "#DDC0A1", "#48382D"),
    ("black_gold", "Gold auf Schwarz", "Dunkel", "#FFD05A", "#000000", "#FFF0BF", "#49412E"),
    ("graphite", "Graphit", "Dunkel", "#B7C3D4", "#090B10", "#E6EBF2", "#39404A"),
    ("moonlight", "Mondlicht", "Dunkel", "#E1EDFF", "#101521", "#B6C7DE", "#3D4757"),
    ("ice_mist", "Eisnebel", "Pastell", "#79C8FF", "#ECF5FC", "#7C99B3", "#4C5D6D"),
    ("lilac_mist", "Fliedernebel", "Pastell", "#BB93F3", "#F3EDF9", "#9B85AF", "#594D66"),
    ("mint_mist", "Mintnebel", "Pastell", "#74D8B6", "#EDF9F4", "#759F8D", "#4C665B"),
    ("peach", "Pfirsich", "Pastell", "#F9AA82", "#FFF2E8", "#B48E7A", "#6D584C"),
    ("warm_gray", "Warmes Silber", "Pastell", "#B9AA96", "#F6F1EA", "#958775", "#60584D"),
    ("rose_quartz", "Rosenquarz", "Pastell", "#ECA1C3", "#FCF0F6", "#AC88A0", "#65515F"),
    ("sunset", "Sunset · Orange & Pink", "Zweifarbig", "#FF9A36", "#180C21", "#FF85C7", "#47324E"),
    (
        "aurora",
        "Aurora · Türkis & Violett",
        "Zweifarbig",
        "#39EDD0",
        "#080F20",
        "#BE9BFF",
        "#303A51",
    ),
    (
        "cyberpunk",
        "Cyberpunk · Cyan & Pink",
        "Zweifarbig",
        "#15DEFF",
        "#0E0819",
        "#FF67D1",
        "#39304C",
    ),
    ("royal", "Royal · Violett & Gold", "Zweifarbig", "#AD7BFF", "#130D22", "#FFD479", "#43354F"),
    ("volcano", "Vulkan · Rot & Orange", "Zweifarbig", "#FF4F43", "#140909", "#FFB36B", "#4C3030"),
    (
        "white_gold",
        "Champagner · Weiß & Gold",
        "Zweifarbig",
        "#D5BA77",
        "#F9F6ED",
        "#967231",
        "#61573E",
    ),
]
BY_ID = {row[0]: row for row in PALETTES}
BY_LABEL = {row[1]: row[0] for row in PALETTES}


def rgb(value):
    return [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]


def palette(name):
    try:
        _, _, group, primary, background, accent, material = BY_ID[name]
    except KeyError as exc:
        raise ValueError("Unbekanntes Farb-Preset.") from exc
    original = defaults()
    if group == "Basis":
        return profile_preset(name, classic_effects(name))
    p = copy.deepcopy(original)
    tint = rgb(primary)
    h, s, v = colorsys.rgb_to_hsv(*tint)
    for key in ("effects", "shader_colors"):
        p[key] = [
            list(
                colorsys.hsv_to_rgb(
                    h, colorsys.rgb_to_hsv(*c)[1] * s, colorsys.rgb_to_hsv(*c)[2] * v
                )
            )
            for c in original[key]
        ]
    p["texture_tint"] = tint
    p["ribbon_tint"] = list(tint)
    p["background_color"] = rgb(background)
    p["text_colors"] = [list(p["effects"][0]), rgb(accent), rgb(accent)]
    for m in p["materials"]:
        m["diffuse"] = rgb(material)
    return validate(p)


def apply(profile, name):
    p = validate(profile)
    theme = palette(name)
    for key in (
        "effects",
        "shader_colors",
        "materials",
        "texture_tint",
        "ribbon_tint",
        "background_color",
        "text_colors",
    ):
        p[key] = copy.deepcopy(theme[key])
    return validate(p)
