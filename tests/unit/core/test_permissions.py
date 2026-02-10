from app.utils.acl import has_all_permissions, has_any_permission, has_permission


def test_has_permission():
    assert has_permission(["a", "b"], "a")
    assert not has_permission(["a"], "b")


def test_has_any_permission():
    assert has_any_permission(["read"], ["write", "read"])
    assert not has_any_permission(["read"], ["write", "delete"])


def test_has_all_permissions():
    assert has_all_permissions(["read", "write"], ["read"])
    assert not has_all_permissions(["read"], ["read", "write"])
