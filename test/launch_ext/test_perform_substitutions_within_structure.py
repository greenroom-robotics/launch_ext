from launch import LaunchContext
from launch.actions import SetLaunchConfiguration
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ext.utilities import perform_substitutions_within_structure


def _context():
    lc = LaunchContext()
    SetLaunchConfiguration("name", "world").visit(lc)
    SetLaunchConfiguration("port", "8080").visit(lc)
    return lc


def test_single_substitution():
    lc = _context()
    assert perform_substitutions_within_structure(lc, LaunchConfiguration("name")) == "world"


def test_list_is_not_merged():
    lc = _context()
    result = perform_substitutions_within_structure(lc, ["hello ", LaunchConfiguration("name")])
    # perform_substitutions would have merged these into "hello world";
    # here the list structure is preserved with each element resolved.
    assert result == ["hello ", "world"]


def test_tuple_structure_preserved():
    lc = _context()
    result = perform_substitutions_within_structure(
        lc, (LaunchConfiguration("name"), TextSubstitution(text="!"))
    )
    assert result == ("world", "!")
    assert isinstance(result, tuple)


def test_dict_keys_and_values_resolved():
    lc = _context()
    result = perform_substitutions_within_structure(
        lc, {LaunchConfiguration("name"): LaunchConfiguration("port")}
    )
    assert result == {"world": "8080"}


def test_nested_structure():
    lc = _context()
    structure = {
        "servers": [
            {"host": LaunchConfiguration("name"), "port": LaunchConfiguration("port")},
        ],
        "enabled": True,
        "retries": 3,
    }
    assert perform_substitutions_within_structure(lc, structure) == {
        "servers": [{"host": "world", "port": "8080"}],
        "enabled": True,
        "retries": 3,
    }


def test_non_substitution_leaves_pass_through():
    lc = _context()
    assert perform_substitutions_within_structure(lc, [1, 2.5, True, None]) == [1, 2.5, True, None]
