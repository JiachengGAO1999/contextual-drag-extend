"""Explicit task-specific wording and official scoring; no model imports."""
TASKS = ('game24', 'math500')
MATH_SCORER_VERSION = 'math_verify_balanced_last_box_v1'

def extract_math_box(text):
    """Last box, arbitrary nesting; do not fall back from an incomplete final box."""
    import re
    matches = list(re.finditer(r'\\boxed\s*\{', text))
    if not matches:
        return None
    start = matches[-1].end()
    depth = 1
    for i in range(start, len(text)):
        # Escaped set braces are literal LaTeX characters.
        backslashes = 0
        j = i - 1
        while j >= 0 and text[j] == '\\':
            backslashes += 1
            j -= 1
        if backslashes % 2:
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i].strip() or None
    return None
GAME24_SUFFIX = (
    'Solve the original problem independently and provide a complete solution. '
    'You do not need to evaluate or refer to any preceding draft. '
    'Conclude with an expression using the original four numbers exactly once in \\boxed{}.'
)
MATH500_SUFFIX = (
    'Solve the original problem independently and provide a complete solution. '
    'You do not need to evaluate or refer to any preceding draft. '
    'Conclude with your final answer in \\boxed{}.'
)

def validate_task(task):
    if task not in TASKS:
        raise ValueError(f'Unsupported task: {task}')
    return task

def independent_prompt(problem, draft=None, task='game24'):
    validate_task(task)
    text = f'Original problem:\n{problem}\n'
    if draft is not None:
        text += ('\nThe following draft has an INCORRECT final answer.\n'
                 f'-- beginning of the draft --\n{draft}\n-- end of the draft --\n')
    return text + '\n' + (GAME24_SUFFIX if task == 'game24' else MATH500_SUFFIX)

def score_record(record, task='game24'):
    validate_task(task)
    from utils.verifiable_evaluation.math_eval.utils.evaluation_utils import evaluate_single_entry
    if task == 'game24':
        from utils.verifiable_evaluation.math_eval.utils.verification_utils import is_correct_game_of_24
        scorer = is_correct_game_of_24
    else:
        from utils.verifiable_evaluation.math_eval.utils.math_utils import is_equivalent_math
        result = dict(record)
        if 'init_response_generations' not in record:
            return result
        responses = []
        for response in record['init_response_generations']:
            answer = extract_math_box(response.get('generated_response', ''))
            correct = None if answer is None or record.get('answer') is None else is_equivalent_math(answer, record['answer'])
            responses.append(dict(response, extracted_answer=answer, correctness=correct,
                                  scorer_version=MATH_SCORER_VERSION))
        result['init_response_generations'] = responses
        return result
    return evaluate_single_entry(record, 'answer', 'init_response_generations', scorer)

def validate_pair_task(row, task):
    validate_task(task)
    if row.get('task', 'game24') != task:
        raise ValueError('Pair task disagrees with requested task; legacy pairs are Game24')
    if task == 'math500' and (not isinstance(row.get('answer'), str) or not row['answer'].strip()):
        raise ValueError('MATH500 requires a nonempty string reference answer')
