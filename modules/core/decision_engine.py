class DecisionEngine:

    def __init__(self):

        # İlk test eşiği
        self.change_threshold = 3.0

    def detect(self, result):

        if result["change_ratio"] >= self.change_threshold:
            return "FULL"

        return "EMPTY"