from app.services.search import _is_broad_list_query


def test_education_queries_expand_document_context():
    assert _is_broad_list_query("tell me his education details")
    assert _is_broad_list_query("What degree and college did the candidate attend?")
    assert _is_broad_list_query("List all academic qualifications")


def test_other_section_queries_expand_document_context():
    assert _is_broad_list_query("show work experience")
    assert _is_broad_list_query("which certifications are listed?")
    assert _is_broad_list_query("list all project details")


def test_specific_fact_queries_keep_normal_top_k():
    assert not _is_broad_list_query("What is the candidate's phone number?")
