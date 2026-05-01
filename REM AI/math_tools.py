import re
import sympy
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application

def solve_math(query: str):
    """
    Attempts to solve exact mathematical expressions using SymPy algebra engine.
    Detects math implicitly (regex) or via keywords (math:, solve:, calculate:).
    """
    query_clean = query.lower().strip()
    
    # 1. Detect Implicit Math (regex for equations or simple arithmetic)
    # This matches patterns like: 5+5, x^2=4, 89 * 5, etc.
    math_pattern = r'^[\d\s\+\-\*\/\^\(\)\.xXyYzZ\=]+$'
    is_implicit_math = re.match(math_pattern, query_clean) and any(op in query_clean for op in "+-*/^=")
    
    # 2. Trigger check
    trigger_keyword = None
    for kw in ["math:", "calculate:", "solve:"]:
        if kw in query_clean:
            trigger_keyword = kw
            break

    if is_implicit_math or trigger_keyword:
        try:
            # Extract the raw expression
            if trigger_keyword:
                expr_str = query_clean.split(trigger_keyword)[1].strip().replace("^", "**")
            else:
                expr_str = query_clean.replace("^", "**")
            
            # Basic sanity check to avoid empty strings
            if not expr_str:
                return None
        
            transformations = (standard_transformations + (implicit_multiplication_application,))
            x, y, z = sympy.symbols('x y z')
            
            # Equation solver
            if "=" in expr_str:
                left, right = expr_str.split("=")
                expr = parse_expr(f"({left})-({right})", transformations=transformations)
                ans = sympy.solve(expr)
                return f"Exact Output (SymPy Engine): Solutions are {ans}"
                
            # Calculus - Derivative
            if "derivative" in expr_str or "diff" in expr_str:
                clean_expr = expr_str.replace("derivative of", "").replace("derivative", "").replace("diff", "").strip()
                expr = parse_expr(clean_expr, transformations=transformations)
                return f"Exact Output (SymPy Engine): Derivative is {sympy.diff(expr, x)}"
                
            # Calculus - Integral
            if "integral" in expr_str or "integrate" in expr_str:
                clean_expr = expr_str.replace("integral of", "").replace("integral", "").replace("integrate", "").strip()
                expr = parse_expr(clean_expr, transformations=transformations)
                return f"Exact Output (SymPy Engine): Integral is {sympy.integrate(expr, x)} + C"
                
            # Standard Evaluation
            expr = parse_expr(expr_str, transformations=transformations)
            expanded = sympy.expand(expr)
            simplified = sympy.simplify(expr)
            evaluated = expr.evalf() if expr.is_number else sympy.factor(expr)
            
            return f"Exact Output (SymPy Engine):\n- Simplified: {simplified}\n- Expanded: {expanded}\n- Evaluated/Factored: {evaluated}"
            
        except Exception as e:
            return f"SymPy could not parse this perfectly: {e}"
            
    return None
