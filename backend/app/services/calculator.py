import ast
import operator
from decimal import Decimal

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}


def safe_calculate(expression: str) -> str:
    """Evaluate arithmetic only; names, calls, attributes and containers are rejected."""
    if len(expression) > 200:
        raise ValueError("Expression too long")
    tree = ast.parse(expression, mode="eval")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Decimal(str(node.value))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](visit(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 20:
                raise ValueError("Exponent too large")
            return OPS[type(node.op)](left, right)
        raise ValueError("Only numeric arithmetic expressions are allowed")

    result = visit(tree)
    return format(result, "f")
