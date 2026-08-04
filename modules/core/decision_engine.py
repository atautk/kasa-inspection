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
        result,
        threshold=None
    ):

        ratio = result.get(
            "change_ratio",
            0
        )

        active_threshold = (
            self.change_threshold
            if threshold is None
            else threshold
        )

        if ratio >= active_threshold:

            return "FULL"

        return "EMPTY"