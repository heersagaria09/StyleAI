BODY_TYPES = ("Pear", "Apple", "Hourglass", "Rectangle", "Inverted Triangle")
SKIN_TONES = ("Fair", "Medium", "Wheatish", "Deep")
FACE_SHAPES = ("Round", "Oval", "Square", "Heart", "Diamond")
OCCASIONS = ("Casual", "College", "Office", "Wedding", "Party")
PREFERRED_STYLES = ("Western", "Traditional", "Indo-Western")
HAIR_LENGTHS = ("Short", "Medium", "Long")
HAIR_TEXTURES = ("Straight", "Wavy", "Curly", "Coily")

FEATURE_COLUMNS = (
    "body_type",
    "skin_tone",
    "face_shape",
    "occasion",
    "preferred_style",
    "hair_length",
    "hair_texture",
)

OUTFIT_FEATURES = ("body_type", "occasion", "preferred_style")
PALETTE_FEATURES = ("skin_tone", "preferred_style")
HAIRSTYLE_FEATURES = ("face_shape", "hair_length", "hair_texture")
EARRING_FEATURES = ("face_shape", "occasion", "preferred_style")
NECKLACE_FEATURES = ("face_shape", "occasion", "preferred_style")
ACCESSORY_FEATURES = ("face_shape", "occasion", "preferred_style")

TARGET_COLUMNS = (
    "outfit",
    "palette",
    "hairstyle",
    "earrings",
    "necklace",
    "accessories",
)

TARGET_FEATURES = {
    "outfit": OUTFIT_FEATURES,
    "palette": PALETTE_FEATURES,
    "hairstyle": HAIRSTYLE_FEATURES,
    "earrings": EARRING_FEATURES,
    "necklace": NECKLACE_FEATURES,
    "accessories": ACCESSORY_FEATURES,
}

_OUTFITS = {
    "Casual": "a relaxed top with straight-leg trousers",
    "College": "a comfortable layered outfit with practical footwear",
    "Office": "a tailored top with well-fitted trousers",
    "Wedding": "an occasion-ready outfit with refined accessories",
    "Party": "a statement outfit balanced with simple accessories",
}

_BODY_TIPS = {
    "Pear": (["Structured tops", "A-line skirts", "Straight-leg trousers"], ["Unbalanced proportions"]),
    "Apple": (["Open layers", "V-neck tops", "Straight-leg trousers"], ["Restrictive waistbands"]),
    "Hourglass": (["Wrap styles", "Defined-waist outfits", "Balanced necklines"], ["Hiding every waist detail"]),
    "Rectangle": (["Layered outfits", "Belts and waist definition", "Textured separates"], ["Overly boxy head-to-toe looks"]),
    "Inverted Triangle": (["V-neck tops", "Flowing skirts", "Wide-leg trousers"], ["Adding excess shoulder volume"]),
}

_PALETTES = {
    "Fair": {
        "Western": ["Teal", "Coral", "Navy Blue"],
        "Traditional": ["Emerald Green", "Burgundy", "Gold"],
        "Indo-Western": ["Royal Blue", "Terracotta", "Ivory"],
    },
    "Medium": {
        "Western": ["Emerald Green", "Royal Blue", "Burgundy"],
        "Traditional": ["Mustard", "Teal", "Magenta"],
        "Indo-Western": ["Terracotta", "Navy Blue", "Gold"],
    },
    "Wheatish": {
        "Western": ["Terracotta", "Olive Green", "Teal"],
        "Traditional": ["Burgundy", "Mustard", "Emerald Green"],
        "Indo-Western": ["Rust", "Royal Blue", "Ivory"],
    },
    "Deep": {
        "Western": ["Mustard", "Ivory", "Electric Blue"],
        "Traditional": ["Gold", "Magenta", "Emerald Green"],
        "Indo-Western": ["Coral", "Bright Yellow", "Royal Blue"],
    },
}

_AVOID_COLORS = {
    "Fair": ["Washed-out Beige"],
    "Medium": ["Muted Grey"],
    "Wheatish": ["Washed-out Beige"],
    "Deep": ["Ash Grey"],
}

_HAIRSTYLES = {
    "Oval": ("Layers, side-swept styles, or a sleek bob", ["Long layers", "Soft waves", "Side part"], []),
    "Round": ("Long layers or a side part to add visual length", ["Long layers", "Side part", "Volume at the crown"], ["Heavy blunt bangs"]),
    "Square": ("Soft waves or layered styles to soften angular lines", ["Soft waves", "Side-swept fringe", "Layered bob"], ["Very blunt jaw-length cuts"]),
    "Heart": ("Chin-length layers or side-swept fringe", ["Side-swept fringe", "Chin-length layers", "Soft waves"], ["Excess volume at the crown"]),
    "Diamond": ("Soft fringe or chin-length layers for balance", ["Soft fringe", "Chin-length layers", "Tucked-behind-ear styles"], ["Excess width at the cheekbones"]),
}

_EARRINGS = {
    "Oval": "Hoops, studs, or drop earrings",
    "Round": "Long drop or angular earrings",
    "Square": "Rounded hoops or soft drop earrings",
    "Heart": "Teardrop or chandelier earrings",
    "Diamond": "Studs or curved drop earrings",
}

_NECKLACES = {
    "Oval": "Most necklace lengths work; coordinate with the neckline",
    "Round": "A longer pendant can create a lengthening line",
    "Square": "A rounded or curved necklace softens angular necklines",
    "Heart": "A short, curved necklace balances a wider neckline",
    "Diamond": "A delicate, curved necklace complements angular features",
}

_OCCASION_ACCESSORIES = {
    "Casual": ["A coordinating crossbody bag", "Comfortable flats or sneakers"],
    "College": ["A practical tote bag", "Comfortable everyday shoes"],
    "Office": ["A structured work bag", "Simple, comfortable shoes"],
    "Wedding": ["A small occasion clutch", "Dress shoes suited to the venue"],
    "Party": ["A compact statement bag", "One complementary accessory"],
}

_STYLE_ACCESSORIES = {
    "Western": ["Minimal metal accents"],
    "Traditional": ["Coordinated traditional jewelry"],
    "Indo-Western": ["A mix of modern and traditional accents"],
}


def build_training_labels(profile):
    style = profile["preferred_style"]
    face_shape = profile["face_shape"]
    hairstyle, _, _ = _HAIRSTYLES[face_shape]
    return {
        "outfit": (
            f"{style} styling for {profile['occasion'].lower()}: "
            f"{_OUTFITS[profile['occasion']]}."
        ),
        "palette": "|".join(_PALETTES[profile["skin_tone"]][style]),
        "hairstyle": (
            f"{profile['hair_length']} {profile['hair_texture'].lower()} hair: "
            f"{hairstyle}."
        ),
        "earrings": _EARRINGS[face_shape],
        "necklace": _NECKLACES[face_shape],
        "accessories": "|".join(
            _OCCASION_ACCESSORIES[profile["occasion"]]
            + _STYLE_ACCESSORIES[style]
        ),
    }


def get_body_type_guide(body_type):
    return _BODY_TIPS[body_type]


def get_color_avoidance(skin_tone):
    return _AVOID_COLORS[skin_tone]


def get_hairstyle_guide(face_shape):
    return _HAIRSTYLES[face_shape]
