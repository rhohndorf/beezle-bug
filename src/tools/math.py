from enum import Enum
from typing import Union

from pydantic import Field

from tools import Tool


class MathOperation(Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class Calculator(Tool):
    """
    Perform a math operation on two numbers.
    """

    number_one: Union[int, float] = Field(..., description="First number.")
    operation: MathOperation = Field(..., description="Math operation to perform.")
    number_two: Union[int, float] = Field(..., description="Second number.")

    def run(self, agent):
        if self.operation == MathOperation.ADD:
            result = self.number_one + self.number_two
        elif self.operation == MathOperation.SUBTRACT:
            result = self.number_one - self.number_two
        elif self.operation == MathOperation.MULTIPLY:
            result = self.number_one * self.number_two
        elif self.operation == MathOperation.DIVIDE:
            result = self.number_one / self.number_two
        else:
            raise ValueError("Unknown operation.")

        return f"{self.number_one} {self.operation} {self.number_two} = {result}"
