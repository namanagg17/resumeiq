from resumeiq.verify import quote_in, term_in, total_score, check_match

RESUME = "Skills: Python, C++, SQL, basic web development. Two academic projects using Python and SQL."
JD = "Required: Python, SQL, data structures, problem-solving skills, and experience developing web applications."


def test_quote_ignores_case_and_punctuation():
    assert quote_in("two academic projects using python and sql", RESUME)
    assert quote_in("Skills: Python, C++ ... SQL", RESUME)
    assert not quote_in("three academic projects", RESUME)


def test_term_keeps_cpp():
    assert term_in("C++", RESUME)
    assert not term_in("C++ programming", JD)
    assert not term_in("Java", RESUME)


def test_cpp_match_is_flagged():
    problems = check_match({"requirement": "C++"}, RESUME, JD)
    assert "job description does not ask for this" in problems


def test_real_match_passes():
    match = {"requirement": "Python", "resume_evidence": "Skills: Python", "jd_evidence": "Required: Python"}
    assert check_match(match, RESUME, JD) == []


def test_total_score_is_computed_and_clamped():
    assert total_score({"skills": 30, "projects": 25, "problem_solving": 10}) == 65
    assert total_score({"skills": 55, "projects": 25, "problem_solving": 10}) == 75
    assert total_score({"skills": 30}) is None
