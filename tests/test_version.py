def test_version():
    from hrepr.version import version

    assert isinstance(version, str) and len(version.split(".")) == 3
