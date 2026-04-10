import pytest

from seqtypo import models


def _db(name: str, description: str, href: str = "https://example.org/db"):
    return models.DatabaseModel(name=name, description=description, href=href)


def test_database_model_parses_category_and_subject():
    db = _db(
        name="pubmlst_neisseria_seqdef",
        description="REST API access to Neisseria sequence/profile definitions database",
    )

    assert db.category == models.DatabaseCategory.SEQDEF.value
    assert db.subject == "Neisseria"


def test_database_list_search_partial_and_regex():
    db_list = models.DatabaseList(
        [
            _db("a_seqdef", "REST API access to Salmonella seqdef database", "https://example.org/a"),
            _db("b_isolates", "REST API access to Neisseria isolates database", "https://example.org/b"),
        ]
    )

    partial = db_list.search("subject", pattern="Neiss", exact_match=False)
    regex = db_list.search("subject", pattern="^Sal", use_regex=True)

    assert len(partial) == 1
    assert partial[0].subject == "Neisseria"
    assert len(regex) == 1
    assert regex[0].subject == "Salmonella"


def test_database_list_get_urls_and_flatten_helpers():
    list_a = models.DatabaseList([_db("a_seqdef", "REST API access to A seqdef database", "https://example.org/a")])
    list_b = models.DatabaseList([_db("b_seqdef", "REST API access to B seqdef database", "https://example.org/b")])

    merged = models.DatabaseList.from_list_of_model_lists([list_a, list_b])

    assert len(merged) == 2
    assert [str(url) for url in merged.get_urls()] == ["https://example.org/a", "https://example.org/b"]


def test_sequence_query_result_maps_exact_matches():
    model = models.SequenceQueryResult(
        exact_matches={
            "abc": [{"allele_id": 11, "href": "https://example.org/11"}],
            "def": [{"allele_id": 22}],
        }
    )

    assert len(model.exact_matches) == 2
    assert model.exact_matches[0].allele_name in {"abc", "def"}


def test_rmlst_result_model_maps_taxonomy():
    result = models.rMLSTResultModel(
        exact_matches={"abc": [{"allele_id": 1}]},
        taxon_prediction=[
            {
                "taxon": "Bacteria",
                "taxonomy": "Life > Bacteria",
                "support": 100,
                "rank": "domain",
            }
        ],
    )

    assert result.taxon_prediction[0].taxonomy == ["Life", "Bacteria"]


def test_api_resource_collection_model_current_behavior():
    collection = models.ApiResourceCollectionModel(
        resources=[
            {
                "name": "PubMLST",
                "description": "Public datasets",
                "databases": [
                    {
                        "name": "x_seqdef",
                        "description": "REST API access to X seqdef database",
                        "href": "https://example.org/x",
                    }
                ],
            }
        ]
    )

    assert collection.resources is None


def test_api_endpoint_model_from_json_rejects_invalid_types():
    with pytest.raises(ValueError):
        models.SchemeModel.from_json(["invalid"])
