from ukpm.watch import data_links

BASE = "https://www.gov.uk/government/statistics/x"


def test_data_links_keeps_allowlisted_data_files_only():
    html = (
        '<a href="https://assets.publishing.service.gov.uk/media/abc/Table.xlsx">t</a>'
        '<a href="/government/statistics/y">page</a>'
        '<a href="https://evil.example/a.xlsx">x</a>'
        '<a href="http://www.gov.uk/a.csv">insecure</a>'
    )
    assert data_links(html, BASE) == {
        "https://assets.publishing.service.gov.uk/media/abc/Table.xlsx"
    }


def test_data_links_handles_ons_file_uri():
    html = '<a href="/file?uri=/economy/x/current/data.xlsx&amp;v=1">d</a>'
    got = data_links(html, "https://www.ons.gov.uk/economy/x")
    assert got == {"https://www.ons.gov.uk/file?uri=/economy/x/current/data.xlsx&v=1"}


def test_data_links_survives_bad_href_and_query_strings():
    html = '<a href="https://[bad/x.xlsx">b</a><a href="https://assets.publishing.service.gov.uk/a/T.xlsx?x=1">t</a>'
    assert data_links(html, BASE) == {"https://assets.publishing.service.gov.uk/a/T.xlsx?x=1"}
