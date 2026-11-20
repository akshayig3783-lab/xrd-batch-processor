"""X-ray tube wavelengths in Å (Kα1 lines)."""

WAVELENGTHS = {"Cu Kα1": 1.5406, "Co Kα1": 1.78897, "Mo Kα1": 0.70932}

SCHERRER_CAVEAT = (
    "Crystallite sizes use the Scherrer equation and are uncorrected for instrumental broadening "
    "and microstrain; treat them as lower-bound estimates."
)

# (Kα1, Kα2) pairs in Å, used to recognise Kα2 shoulders. Matched against the analysis wavelength
# within KA_MATCH_TOLERANCE, so the Kα-average wavelength (e.g. Cu 1.5418) also matches.
KA_DOUBLETS = {"Cu": (1.540562, 1.544390), "Co": (1.788965, 1.792850), "Mo": (0.709300, 0.713590)}
KA_MATCH_TOLERANCE = 0.01
