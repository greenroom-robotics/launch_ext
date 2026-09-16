"""Tests for the restored (pre-2.0) FastDDS profile substitution.

``FastDDSProfileSubstitution`` (in ``launch_ext/actions/configure_fastdds.py``)
renders ``config/fastdds_profile.xml.j2`` from the installed ``launch_ext``
package share (resolved via ``FindPackageShare``, then loaded through a
Jinja2 ``Environment`` rooted at that directory), so these tests require the
package to be available on the ament prefix path (as it is under
``colcon test``).

``ROS_DISTRO`` is pinned per-test so the template's distro-dependent branches
render deterministically.

Both the legacy and ng FastDDS templates use jinja2's default ``Undefined``,
so cross-wiring them (the legacy renderer loading the ng template, or vice
versa) renders empty/missing values instead of raising. The assertions below
target content that only the *legacy* template produces -- the
``super_client_profile`` name shared by every protocol, the literal
(untranslated) ``discoveryProtocol`` value, and the hardcoded discovery
server port -- so that cross-wiring fails this test.
"""

import xml.etree.ElementTree as ET

import pytest

from launch import LaunchContext
from launch_ext.actions.configure_fastdds import FastDDSProfileSubstitution


@pytest.fixture(autouse=True)
def _pin_ros_distro(monkeypatch):
    monkeypatch.setenv("ROS_DISTRO", "kilted")


def _render(**kwargs):
    kwargs.setdefault("discovery_server_ip", "10.0.0.5")
    kwargs.setdefault("allowed_interfaces", [])
    return FastDDSProfileSubstitution(**kwargs).perform(LaunchContext())


def test_renders_well_formed_xml():
    xml = _render(discovery_protocol="SIMPLE")
    # Parsing succeeds (raises on malformed XML) and gives the expected root.
    root = ET.fromstring(xml)
    assert root.tag.endswith("dds")


def test_client_protocol_renders_discovery_server_ip():
    xml = _render(discovery_protocol="CLIENT")
    # unlike the ng template, the legacy template echoes discovery_protocol
    # literally rather than translating CLIENT -> SUPER_CLIENT.
    assert "<discoveryProtocol>CLIENT</discoveryProtocol>" in xml
    assert "<mutation_tries>1000</mutation_tries>" in xml
    assert "fastdds.type_propagation" in xml
    # the legacy template renders discovery_server_ip directly at a
    # hardcoded port; the ng template has no discovery_server_ip variable.
    assert "<address>10.0.0.5</address>" in xml
    assert "<port>11811</port>" in xml
    # only the legacy template names its (single) participant profile this
    assert 'profile_name="super_client_profile"' in xml
    # the ng template's hardcoded CLIENT metatraffic port must not appear
    assert "27400" not in xml


def test_super_client_protocol_is_not_translated():
    xml = _render(discovery_protocol="SUPER_CLIENT")
    assert "<discoveryProtocol>SUPER_CLIENT</discoveryProtocol>" in xml
    assert "<address>10.0.0.5</address>" in xml


def test_server_protocol_uses_interfaces_not_discovery_server_ip():
    # the legacy SERVER branch ignores discovery_server_ip and falls back to
    # 0.0.0.0 when no interfaces are given.
    xml = _render(discovery_protocol="SERVER")
    assert "<discoveryProtocol>SERVER</discoveryProtocol>" in xml
    assert "<address>0.0.0.0</address>" in xml
    assert "<port>11811</port>" in xml
    assert "SUPER_CLIENT" not in xml
    assert "10.0.0.5" not in xml


def test_server_protocol_with_interfaces():
    xml = _render(discovery_protocol="SERVER", allowed_interfaces=["127.0.0.1"])
    assert "<address>127.0.0.1</address>" in xml


def test_simple_protocol_has_no_discovery_server_block():
    xml = _render(discovery_protocol="SIMPLE")
    assert "SUPER_CLIENT" not in xml
    assert "<discoveryProtocol>SERVER</discoveryProtocol>" not in xml
    # still valid XML
    assert ET.fromstring(xml).tag.endswith("dds")


def test_allowed_interfaces_are_resolved_and_rendered():
    xml = _render(discovery_protocol="CLIENT", allowed_interfaces=["127.0.0.1"])
    # ResolveHost("127.0.0.1") -> "127.0.0.1", which appears as an allowed
    # interface in the kilted allowlist form.
    assert '<interface name="127.0.0.1"' in xml


def test_non_kilted_uses_remote_server_and_interface_whitelist(monkeypatch):
    monkeypatch.setenv("ROS_DISTRO", "iron")
    xml = _render(discovery_protocol="CLIENT", allowed_interfaces=["127.0.0.1"])
    assert 'RemoteServer prefix="44.53.00.5f.45.50.52.4f.53.49.4d.41"' in xml
    assert "<interfaceWhiteList>" in xml
    assert "<address>127.0.0.1</address>" in xml


def test_describe():
    description = FastDDSProfileSubstitution(
        discovery_protocol="CLIENT",
        discovery_server_ip="10.0.0.5",
        allowed_interfaces=[],
    ).describe()
    assert description.startswith("FastDDSProfile(")
    assert "CLIENT" in description
