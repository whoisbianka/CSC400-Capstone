"""Questionnaire definition, validation, and demo matching."""
from .search import search
from ..forms import validate_text

QUESTIONS = [
    ('interests', 'What subjects or activities do you enjoy most?'),
    ('strengths', 'What do you feel you are good at? Think about skills or strengths you enjoy using.'),
    ('work_style', 'What kind of work interests you: working with people, technology, ideas, or hands-on projects?'),
    ('goals', 'What matters most to you in a future career?'),
    ('curiosity', 'Are there any majors or careers you would like to explore? It is okay to be unsure.'),
]


def next_step(answers):
    return next((i for i, (key, _) in enumerate(QUESTIONS) if not answers.get(key)), None)


def results(answers, programs):
    return search(' '.join(answers[key] for key, _ in QUESTIONS), programs)
