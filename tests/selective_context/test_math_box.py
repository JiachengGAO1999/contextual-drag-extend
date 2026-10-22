from selective_context.tasks import extract_math_box

def test_nested_radical_and_fraction():
    assert extract_math_box(r'\boxed{\dfrac{\sqrt{3}}{3}}') == r'\dfrac{\sqrt{3}}{3}'

def test_literal_set_braces():
    assert extract_math_box(r'\boxed{\{1,\frac{2}{3}\}}') == r'\{1,\frac{2}{3}\}'

def test_last_incomplete_box_cannot_reuse_earlier_answer():
    assert extract_math_box(r'\boxed{2} then \boxed{\frac{1}{') is None

def test_preserves_last_box_policy():
    assert extract_math_box(r'\boxed{-2} and \boxed{1}') == '1'
