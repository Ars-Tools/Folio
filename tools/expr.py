#!/usr/bin/env python3
from typing import Annotated
from pydantic_ai.tools import Tool
from pydantic import Field
from sympy import sympify, N, Symbol, Integer, Float, Rational

def _expr(
    expression: Annotated[str, Field(description="The mathematical expression to evaluate")]
) -> str:
    """
    Evaluate a mathematical expression.
    
    Supported functions include standard arithmetic, trigonometry (sin, cos, tan),
    combinatorics (factorial, binomial), number theory (gcd, lcm, isprime),
    calculus (integrate, diff, limit), and solvers (solve).
    """
    try:
        return str(sympify(expression))
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"

expr = Tool(_expr, name="math_expression", description="Evaluate mathematical expressions", takes_ctx=False, sequential=False)

if __name__ == "__main__":
    print(_expr("1 + 2 * (3 / 4) ** 2"))
    print(_expr("sqrt(16) + sin(0)")) 
    print(_expr("gcd(28, 42)"))
    print(_expr("expand((x + 1)**2)"))
    print(_expr("integrate(x**2, x)"))
    print(_expr("solve(x**2 - 4, x)"))
    print(_expr("limit(sin(x)/x, x, 0)"))
    print(_expr("diff(sin(x * y), y)"))
    print(_expr("isprime(257)"))
    # print(_expr("os.popen('/bin/pwd')")) # Raise
    # print(_expr("os.listdir(',')")) # Raise
    # print(_expr("import sys")) # Raise
