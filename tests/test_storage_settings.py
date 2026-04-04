import pytest

from config.settings import (
    build_media_url,
    build_s3_storage_options,
    ensure_trailing_slash,
)


def test_ensure_trailing_slash_preserves_existing_suffix():
    assert (
        ensure_trailing_slash("https://files.example.com/media/")
        == "https://files.example.com/media/"
    )


def test_ensure_trailing_slash_appends_missing_suffix():
    assert (
        ensure_trailing_slash("https://files.example.com/media")
        == "https://files.example.com/media/"
    )


@pytest.mark.parametrize(
    (
        "explicit_media_url",
        "custom_domain",
        "endpoint_url",
        "bucket_name",
        "use_ssl",
        "expected",
    ),
    [
        (
            "https://cdn.jawafdehi.org/uploads",
            None,
            None,
            None,
            True,
            "https://cdn.jawafdehi.org/uploads/",
        ),
        (
            None,
            "files.jawafdehi.org",
            None,
            None,
            True,
            "https://files.jawafdehi.org/",
        ),
        (
            None,
            "http://files.jawafdehi.test",
            None,
            None,
            False,
            "http://files.jawafdehi.test/",
        ),
        (
            None,
            None,
            "https://r2.example.com",
            "jawafdehi",
            True,
            "https://r2.example.com/jawafdehi/",
        ),
        (
            None,
            None,
            None,
            None,
            True,
            "/media/",
        ),
    ],
)
def test_build_media_url(
    explicit_media_url,
    custom_domain,
    endpoint_url,
    bucket_name,
    use_ssl,
    expected,
):
    assert (
        build_media_url(
            explicit_media_url=explicit_media_url,
            custom_domain=custom_domain,
            endpoint_url=endpoint_url,
            bucket_name=bucket_name,
            use_ssl=use_ssl,
        )
        == expected
    )


def test_build_s3_storage_options_includes_public_url_defaults():
    options = build_s3_storage_options(
        access_key="key",
        secret_key="secret",
        bucket_name="jawafdehi",
        region_name="auto",
        endpoint_url="https://r2.example.com",
        use_ssl=True,
        custom_domain="files.jawafdehi.org",
    )

    assert options == {
        "access_key": "key",
        "secret_key": "secret",
        "bucket_name": "jawafdehi",
        "region_name": "auto",
        "endpoint_url": "https://r2.example.com",
        "use_ssl": True,
        "querystring_auth": False,
        "custom_domain": "files.jawafdehi.org",
    }
