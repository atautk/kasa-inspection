class DecisionEngine:

    # -----------------------------------------
    # Varsayılan Eşikler
    # -----------------------------------------

    EMPTY_THRESHOLD = 3.0

    def __init__(self):

        self.change_threshold = self.EMPTY_THRESHOLD

    # -----------------------------------------
    # Eşik Güncelle
    # -----------------------------------------

    def set_threshold(
        self,
        value
    ):

        self.change_threshold = float(value)

    # -----------------------------------------
    # Karar Ver
    # -----------------------------------------

    def detect(
        self,
        result
    ):

        ratio = result.get(
            "change_ratio",
            0
        )

        if ratio >= self.change_threshold:

            return "FULL"

        return "EMPTY"