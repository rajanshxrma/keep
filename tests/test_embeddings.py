"""Real tests for embeddings.py -- against the actual NLEmbedding model."""

from keep.search.embeddings import cosine_similarity, dimension, embed


def test_dimension_is_real_and_positive():
    assert dimension() > 0


def test_similar_sentences_score_higher_than_unrelated():
    cat1 = embed("the cat sat on the mat")
    cat2 = embed("a feline rested on the rug")
    unrelated = embed("quarterly earnings exceeded analyst expectations")

    sim_related = cosine_similarity(cat1, cat2)
    sim_unrelated = cosine_similarity(cat1, unrelated)

    assert sim_related > sim_unrelated


def test_identical_strings_score_near_one():
    v = embed("the same sentence")
    assert cosine_similarity(v, v) > 0.99
