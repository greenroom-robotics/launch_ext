from pathlib import Path

from launch import LaunchContext
from launch.substitutions import LaunchConfiguration
from launch_ext.substitutions import YAMLToFile
from launch.actions import SetLaunchConfiguration


def test_file_contents():
    lc = LaunchContext()
    SetLaunchConfiguration("test_sub", "world").visit(lc)

    config = {
        "asdf": "moo",
        "hello": LaunchConfiguration("test_sub"),
        "baz": {"asdf": "moo", "foo": "bar"},
        "list": ["asdf", "moo", "foo", "bar"],
    }

    sub = YAMLToFile(config)
    p = sub.perform(lc)
    print(p)
    assert Path(p).read_text() == """asdf: moo
baz:
  asdf: moo
  foo: bar
hello: world
list:
- asdf
- moo
- foo
- bar
"""
    # This doesn't work well at all
    # assert sub.describe() == "YAMLToFile(config={'asdf': 'moo', 'hello': LaunchConfiguration('test_sub'), 'baz': {'asdf': 'moo', 'foo': 'bar'}, 'list': ['asdf', 'moo', 'foo', 'bar']})"
