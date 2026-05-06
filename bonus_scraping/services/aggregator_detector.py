class AggregatorDetector:
    PATTERNS = (
        ("SoftSwiss", ("softswiss", "softswisscdn", "softswiss.net")),
        ("EveryMatrix", ("everymatrix", "casinoengine", "gamematrix")),
        ("Pragmatic Solutions", ("pragmaticplay", "pragmatic solutions")),
        ("BetConstruct", ("betconstruct", "springbuilder")),
        ("Slotegrator", ("slotegrator",)),
        ("SOFTSWISS", ("softswiss",)),
    )

    @classmethod
    def detect(cls, html, url=""):
        haystack = "%s %s" % (url or "", html or "")
        haystack = haystack.lower()
        for name, patterns in cls.PATTERNS:
            if any(pattern in haystack for pattern in patterns):
                return name
        return ""
