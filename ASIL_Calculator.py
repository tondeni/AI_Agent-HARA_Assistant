# asil_calculator.py
# ASIL Calculation logic based on ISO 26262-3:2018 Table 7

class ASILCalculator:
    """
    Calculates ASIL based on Severity (S), Exposure (E), and Controllability (C)
    according to ISO 26262-3:2018 Table 7.
    """
    
    # ASIL Matrix: [S][E][C] -> ASIL
    # S: 0-3, E: 0-3, C: 0-3
    # ASIL: QM, A, B, C, D
    ASIL_MATRIX = [
        # S0 -> QM
        [
            [["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"]], # E0
            [["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"]], # E1
            [["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"]], # E2
            [["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"], ["QM", "QM", "QM", "QM"]]  # E3
        ],
        # S1
        [
            [["QM", "QM", "QM", "QM"], ["QM", "A", "A", "A"], ["QM", "A", "A", "A"], ["QM", "A", "A", "A"]], # E0
            [["QM", "QM", "QM", "QM"], ["QM", "A", "A", "A"], ["QM", "A", "B", "B"], ["QM", "A", "B", "B"]], # E1
            [["QM", "QM", "QM", "QM"], ["QM", "A", "B", "B"], ["QM", "B", "B", "C"], ["QM", "B", "C", "C"]], # E2
            [["QM", "QM", "QM", "QM"], ["QM", "A", "B", "C"], ["QM", "B", "C", "C"], ["QM", "C", "C", "D"]]  # E3
        ],
        # S2
        [
            [["QM", "QM", "QM", "QM"], ["QM", "A", "B", "B"], ["QM", "B", "B", "C"], ["QM", "B", "C", "C"]], # E0
            [["QM", "QM", "QM", "QM"], ["QM", "A", "B", "C"], ["QM", "B", "C", "C"], ["QM", "C", "C", "D"]], # E1
            [["QM", "QM", "QM", "QM"], ["QM", "B", "C", "C"], ["QM", "C", "C", "D"], ["QM", "C", "D", "D"]], # E2
            [["QM", "QM", "QM", "QM"], ["QM", "B", "C", "D"], ["QM", "C", "D", "D"], ["QM", "D", "D", "D"]]  # E3
        ],
        # S3
        [
            [["QM", "QM", "QM", "QM"], ["QM", "B", "C", "C"], ["QM", "C", "C", "D"], ["QM", "C", "D", "D"]], # E0
            [["QM", "QM", "QM", "QM"], ["QM", "B", "C", "D"], ["QM", "C", "D", "D"], ["QM", "D", "D", "D"]], # E1
            [["QM", "QM", "QM", "QM"], ["QM", "C", "D", "D"], ["QM", "D", "D", "D"], ["QM", "D", "D", "D"]], # E2
            [["QM", "QM", "QM", "QM"], ["QM", "C", "D", "D"], ["QM", "D", "D", "D"], ["QM", "D", "D", "D"]]  # E3
        ]
    ]

    @staticmethod
    def calculate_asil(s, e, c):
        """
        Calculate ASIL based on S, E, C values.
        
        Args:
            s (int): Severity (0-3)
            e (int): Exposure (0-3)
            c (int): Controllability (0-3)
            
        Returns:
            str: ASIL level (QM, A, B, C, D) or "Invalid" if inputs are out of range
        """
        if not (0 <= s <= 3 and 0 <= e <= 3 and 0 <= c <= 3):
            return "Invalid"
        
        return ASILCalculator.ASIL_MATRIX[s][e][c]
