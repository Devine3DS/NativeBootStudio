"""Modern native animation only. Classic exports are no longer supported."""

from i18n import app_dir

MODERN = "modern"


def source(name="modern"):
    if name != "modern":
        raise ValueError("Die klassische Bootanimation wird nicht mehr unterstützt.")
    return app_dir() / "originals" / "modern" / "bootanim.xex"
