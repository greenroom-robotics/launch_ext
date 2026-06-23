"""Tests for the FastDDSProfile substitution.

FastDDSProfile renders ``config/fastdds_profile.xml.j2`` from the installed
``launch_ext`` package share (resolved via FindPackageShare), so these tests
require the package to be available on the ament prefix path (as it is under
``colcon test``).

``ROS_DISTRO`` is pinned per-test so the template's distro-dependent branches
render deterministically, and ``127.0.0.1`` is used for hosts so ResolveHost
resolves to a stable value without real network lookups.
"""

import xml.etree.ElementTree as ET

import pytest

from launch import LaunchContext
from launch_ext.substitutions import FastDDSProfile
from launch_ext.discovery.discovery_config import IPEndPoint


LOCAL_SERVER = IPEndPoint(address="127.0.0.1", port=11811)


@pytest.fixture(autouse=True)
def _pin_ros_distro(monkeypatch):
    monkeypatch.setenv("ROS_DISTRO", "kilted")


def _render(**kwargs):
    kwargs.setdefault("local_discovery_server", LOCAL_SERVER)
    return FastDDSProfile(**kwargs).perform(LaunchContext())


def test_renders_well_formed_xml():
    xml = _render(discovery_protocol="CLIENT")
    # Parsing succeeds (raises on malformed XML) and gives the expected root.
    root = ET.fromstring(xml)
    assert root.tag.endswith("dds")


def test_client_protocol():
    xml = _render(discovery_protocol="CLIENT")
    assert "<discoveryProtocol>SUPER_CLIENT</discoveryProtocol>" in xml
    assert "<mutation_tries>1000</mutation_tries>" in xml
    # type propagation is explicitly disabled for clients
    assert "fastdds.type_propagation" in xml
    # the discovery server endpoint is rendered
    assert "<address>127.0.0.1</address>" in xml


def test_server_protocol():
    xml = _render(
        discovery_protocol="SERVER",
        external_discovery_servers=[IPEndPoint(address="127.0.0.1", port=12000)],
    )
    assert "<discoveryProtocol>SERVER</discoveryProtocol>" in xml
    assert "discovery_server_thread" in xml
    # the external discovery server endpoint is rendered into the servers list
    assert "<port>12000</port>" in xml
    assert "SUPER_CLIENT" not in xml


def test_simple_protocol_has_no_discovery_server_block():
    xml = _render(discovery_protocol="SIMPLE")
    assert "SUPER_CLIENT" not in xml
    assert "discovery_server_thread" not in xml
    # still valid XML
    assert ET.fromstring(xml).tag.endswith("dds")


def test_shm_large_segment_toggles_segment_size():
    with_segment = _render(discovery_protocol="SIMPLE", shm_large_segment=True)
    without_segment = _render(discovery_protocol="SIMPLE", shm_large_segment=False)
    assert "<segment_size>16384000</segment_size>" in with_segment
    assert "<segment_size>16384000</segment_size>" not in without_segment


def test_external_interfaces_are_resolved_and_rendered():
    xml = _render(discovery_protocol="CLIENT", external_interfaces=["127.0.0.1"])
    # ResolveHost("127.0.0.1") -> "127.0.0.1", which appears as an allowed interface.
    assert '<interface name="127.0.0.1"' in xml


def test_describe():
    description = FastDDSProfile(
        discovery_protocol="CLIENT", local_discovery_server=LOCAL_SERVER
    ).describe()
    assert description.startswith("FastDDSProfile(")
    assert "discovery_protocol" in description
