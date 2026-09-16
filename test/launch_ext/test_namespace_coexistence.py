"""Both middleware generations must import side by side and stay distinct."""

import inspect

from launch_ext.actions import ConfigureFastDDS as LegacyConfigureFastDDS
from launch_ext.discovery import configure_middleware as legacy_configure_middleware
from launch_ext.ng.actions import ConfigureFastDDS as NgConfigureFastDDS
from launch_ext.ng.discovery import configure_middleware as ng_configure_middleware


def test_configure_middleware_functions_are_distinct():
    assert legacy_configure_middleware is not ng_configure_middleware


def test_configure_fastdds_classes_are_distinct():
    assert LegacyConfigureFastDDS is not NgConfigureFastDDS


def test_legacy_configure_middleware_keeps_its_1_27_signature():
    params = inspect.signature(legacy_configure_middleware).parameters

    assert list(params) == ["discovery", "with_server", "then"]


def test_ng_configure_middleware_keeps_its_2_x_signature():
    params = inspect.signature(ng_configure_middleware).parameters

    assert list(params) == ["middleware_config", "inherit", "then"]


def test_legacy_configure_fastdds_keeps_its_1_27_signature():
    params = inspect.signature(LegacyConfigureFastDDS.__init__).parameters

    assert "with_discovery_server" in params
    assert "discovery_protocol" not in params


def test_ng_configure_fastdds_keeps_its_2_x_signature():
    params = inspect.signature(NgConfigureFastDDS.__init__).parameters

    assert "discovery_protocol" in params
    assert "with_discovery_server" not in params
