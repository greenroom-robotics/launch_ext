from launch import LaunchContext
from launch.actions import SetLaunchConfiguration
from launch.substitutions import LaunchConfiguration
from launch_ext.substitutions import JinjaTemplate


def test_render_with_vars(tmp_path):
    template = tmp_path / "greeting.j2"
    template.write_text("hello {{ name }}")

    lc = LaunchContext()
    sub = JinjaTemplate(str(template), {"name": "world"})
    assert sub.perform(lc) == "hello world"


def test_render_without_vars(tmp_path):
    template = tmp_path / "static.j2"
    template.write_text("no variables here")

    lc = LaunchContext()
    sub = JinjaTemplate(str(template))
    assert sub.perform(lc) == "no variables here"


def test_template_path_is_substituted(tmp_path):
    template = tmp_path / "path_sub.j2"
    template.write_text("value is {{ value }}")

    lc = LaunchContext()
    SetLaunchConfiguration("template_path", str(template)).visit(lc)

    sub = JinjaTemplate(LaunchConfiguration("template_path"), {"value": "42"})
    assert sub.perform(lc) == "value is 42"


def test_template_vars_are_substituted(tmp_path):
    template = tmp_path / "var_sub.j2"
    template.write_text("hello {{ name }}")

    lc = LaunchContext()
    SetLaunchConfiguration("who", "world").visit(lc)

    sub = JinjaTemplate(str(template), {"name": LaunchConfiguration("who")})
    assert sub.perform(lc) == "hello world"


def test_trailing_newline_is_kept(tmp_path):
    template = tmp_path / "trailing.j2"
    template.write_text("line\n")

    lc = LaunchContext()
    sub = JinjaTemplate(str(template))
    assert sub.perform(lc) == "line\n"


def test_jinja_control_flow(tmp_path):
    template = tmp_path / "loop.j2"
    template.write_text("{% if enabled == 'true' %}on{% else %}off{% endif %}")

    lc = LaunchContext()
    assert JinjaTemplate(str(template), {"enabled": "true"}).perform(lc) == "on"
    assert JinjaTemplate(str(template), {"enabled": "false"}).perform(lc) == "off"


def test_non_substitution_values_pass_through(tmp_path):
    template = tmp_path / "collection.j2"
    template.write_text("{% for i in items %}{{ i }},{% endfor %}")

    lc = LaunchContext()

    # A list and a tuple of non-substitution objects are passed straight to the
    # template instead of being normalized, so neither raises and the template
    # iterates the real collection.
    assert JinjaTemplate(str(template), {"items": [1, 2, 3]}).perform(lc) == "1,2,3,"
    assert JinjaTemplate(str(template), {"items": ("a", "b")}).perform(lc) == "a,b,"


def test_substitutions_resolved_within_structure(tmp_path):
    template = tmp_path / "hosts.j2"
    template.write_text("{% for h in hosts %}{{ h }},{% endfor %}")

    lc = LaunchContext()
    SetLaunchConfiguration("host_a", "alpha").visit(lc)
    SetLaunchConfiguration("host_b", "beta").visit(lc)

    # Substitutions inside a list are resolved while the list structure is kept,
    # so the template iterates the individual resolved values.
    sub = JinjaTemplate(
        str(template),
        {"hosts": [LaunchConfiguration("host_a"), LaunchConfiguration("host_b")]},
    )
    assert sub.perform(lc) == "alpha,beta,"


def test_describe(tmp_path):
    template = tmp_path / "describe.j2"
    template.write_text("hi")

    sub = JinjaTemplate(str(template), {"name": "world"})
    description = sub.describe()
    assert "JinjaTemplate(" in description
    assert "name" in description
