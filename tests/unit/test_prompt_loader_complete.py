"""
Prompt Loader完整单元测试

测试PromptLoader的所有功能分支，提升覆盖率
"""

import pytest
import tempfile
from pathlib import Path
from jinja2 import TemplateNotFound

from src.services.prompt_loader import PromptLoader


@pytest.mark.unit
class TestPromptLoader:
    """PromptLoader单元测试"""

    @pytest.fixture
    def temp_prompts_dir(self):
        """创建临时prompts目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)

            # 创建示例模板文件
            basic_template = prompts_dir / "basic.txt"
            basic_template.write_text("Hello {{ name }}!")

            complex_template = prompts_dir / "complex.txt"
            complex_template.write_text(
                """Meeting Summary:
Title: {{ title }}
Date: {{ date }}

{% if participants %}
Participants:
{% for participant in participants %}
- {{ participant }}
{% endfor %}
{% endif %}

{% if topics %}
Topics:
{% for topic in topics %}
{{ loop.index }}. {{ topic }}
{% endfor %}
{% endif %}
"""
            )

            jinja_template = prompts_dir / "template.j2"
            jinja_template.write_text("Template: {{ content }}")

            yield prompts_dir

    @pytest.fixture
    def loader_with_temp_dir(self, temp_prompts_dir):
        """创建使用临时目录的PromptLoader"""
        return PromptLoader(prompts_dir=str(temp_prompts_dir))

    def test_init_with_custom_dir(self, temp_prompts_dir):
        """测试使用自定义目录初始化"""
        loader = PromptLoader(prompts_dir=str(temp_prompts_dir))

        assert loader.prompts_dir == temp_prompts_dir
        assert loader.prompts_dir.exists()

    def test_init_with_default_dir(self):
        """测试使用默认目录初始化"""
        loader = PromptLoader()

        # 应该使用项目根目录下的prompts文件夹
        assert loader.prompts_dir.name == "prompts"
        assert loader.prompts_dir.exists()

    def test_init_creates_directory_if_not_exists(self):
        """测试初始化时创建不存在的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_prompts_dir = Path(tmpdir) / "new_prompts"
            assert not new_prompts_dir.exists()

            loader = PromptLoader(prompts_dir=str(new_prompts_dir))

            # 目录应该被创建
            assert new_prompts_dir.exists()
            assert loader.prompts_dir == new_prompts_dir

    def test_load_template_success(self, loader_with_temp_dir):
        """测试成功加载模板"""
        template = loader_with_temp_dir.load_template("basic.txt")

        assert template is not None
        rendered = template.render(name="World")
        assert rendered == "Hello World!"

    def test_load_template_not_found(self, loader_with_temp_dir):
        """测试加载不存在的模板"""
        with pytest.raises(FileNotFoundError, match="Template not found"):
            loader_with_temp_dir.load_template("nonexistent.txt")

    def test_load_template_complex(self, loader_with_temp_dir):
        """测试加载复杂模板"""
        template = loader_with_temp_dir.load_template("complex.txt")

        rendered = template.render(
            title="Q4 Planning",
            date="2025-10-01",
            participants=["Alice", "Bob", "Charlie"],
            topics=["Budget Review", "Roadmap", "Hiring"],
        )

        assert "Title: Q4 Planning" in rendered
        assert "Date: 2025-10-01" in rendered
        assert "- Alice" in rendered
        assert "- Bob" in rendered
        assert "- Charlie" in rendered
        assert "1. Budget Review" in rendered
        assert "2. Roadmap" in rendered
        assert "3. Hiring" in rendered

    def test_render_template_success(self, loader_with_temp_dir):
        """测试成功渲染模板"""
        rendered = loader_with_temp_dir.render_template(
            "basic.txt", name="Alice"
        )

        assert rendered == "Hello Alice!"

    def test_render_template_with_multiple_variables(self, loader_with_temp_dir):
        """测试使用多个变量渲染模板"""
        rendered = loader_with_temp_dir.render_template(
            "complex.txt",
            title="Weekly Sync",
            date="2025-10-05",
            participants=["John"],
            topics=["Status Update"],
        )

        assert "Weekly Sync" in rendered
        assert "2025-10-05" in rendered
        assert "- John" in rendered
        assert "1. Status Update" in rendered

    def test_render_template_with_empty_optional_lists(self, loader_with_temp_dir):
        """测试渲染时可选列表为空"""
        rendered = loader_with_temp_dir.render_template(
            "complex.txt",
            title="Simple Meeting",
            date="2025-10-10",
            participants=[],
            topics=None,
        )

        # 应该只包含必需字段
        assert "Simple Meeting" in rendered
        assert "2025-10-10" in rendered
        # 空列表不应该渲染
        assert "Participants:" not in rendered
        assert "Topics:" not in rendered

    def test_render_template_not_found(self, loader_with_temp_dir):
        """测试渲染不存在的模板"""
        with pytest.raises(FileNotFoundError):
            loader_with_temp_dir.render_template("missing.txt", var="value")

    def test_render_template_error(self, loader_with_temp_dir, temp_prompts_dir):
        """测试渲染时的错误处理"""
        # 创建一个有语法错误的模板
        bad_template = temp_prompts_dir / "bad.txt"
        bad_template.write_text("{{ unclosed")

        with pytest.raises(Exception):
            loader_with_temp_dir.render_template("bad.txt")

    def test_list_templates_txt_files(self, loader_with_temp_dir):
        """测试列出.txt模板文件"""
        templates = loader_with_temp_dir.list_templates()

        assert "basic.txt" in templates
        assert "complex.txt" in templates

    def test_list_templates_j2_files(self, loader_with_temp_dir):
        """测试列出.j2模板文件"""
        templates = loader_with_temp_dir.list_templates()

        assert "template.j2" in templates

    def test_list_templates_sorted(self, loader_with_temp_dir):
        """测试列出的模板是排序的"""
        templates = loader_with_temp_dir.list_templates()

        # 验证列表是排序的
        assert templates == sorted(templates)

    def test_list_templates_empty_directory(self):
        """测试空目录中列出模板"""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir) / "empty"
            empty_dir.mkdir()

            loader = PromptLoader(prompts_dir=str(empty_dir))
            templates = loader.list_templates()

            assert templates == []

    def test_list_templates_ignores_other_files(self, temp_prompts_dir):
        """测试列出模板时忽略其他文件类型"""
        # 添加其他类型的文件
        (temp_prompts_dir / "readme.md").write_text("# README")
        (temp_prompts_dir / "config.json").write_text("{}")
        (temp_prompts_dir / "script.py").write_text("print('hello')")

        loader = PromptLoader(prompts_dir=str(temp_prompts_dir))
        templates = loader.list_templates()

        # 只应该包含.txt和.j2文件
        assert "readme.md" not in templates
        assert "config.json" not in templates
        assert "script.py" not in templates
        assert "basic.txt" in templates
        assert "template.j2" in templates

    def test_validate_template_valid(self, loader_with_temp_dir):
        """测试验证有效的模板"""
        result = loader_with_temp_dir.validate_template("basic.txt")

        assert result is True

    def test_validate_template_not_found(self, loader_with_temp_dir):
        """测试验证不存在的模板"""
        result = loader_with_temp_dir.validate_template("nonexistent.txt")

        assert result is False

    def test_validate_template_invalid_syntax(self, loader_with_temp_dir, temp_prompts_dir):
        """测试验证语法错误的模板"""
        # 创建语法错误的模板
        invalid_template = temp_prompts_dir / "invalid.txt"
        invalid_template.write_text("{{ unclosed_tag")

        result = loader_with_temp_dir.validate_template("invalid.txt")

        assert result is False

    def test_get_template_path(self, loader_with_temp_dir, temp_prompts_dir):
        """测试获取模板路径"""
        path = loader_with_temp_dir.get_template_path("basic.txt")

        assert path == temp_prompts_dir / "basic.txt"
        assert path.exists()

    def test_get_template_path_nonexistent(self, loader_with_temp_dir, temp_prompts_dir):
        """测试获取不存在模板的路径"""
        path = loader_with_temp_dir.get_template_path("nonexistent.txt")

        assert path == temp_prompts_dir / "nonexistent.txt"
        assert not path.exists()

    def test_jinja2_trim_and_lstrip_config(self, loader_with_temp_dir, temp_prompts_dir):
        """测试Jinja2环境的trim和lstrip配置"""
        # 创建带有空白符的模板
        whitespace_template = temp_prompts_dir / "whitespace.txt"
        whitespace_template.write_text(
            """
            {% if show %}
            Content here
            {% endif %}
            """
        )

        rendered = loader_with_temp_dir.render_template("whitespace.txt", show=True)

        # trim_blocks和lstrip_blocks应该移除多余的空白
        # 结果应该相对紧凑
        assert rendered.strip() != ""
        # 不应该有大量的前导/尾随空行
        lines = rendered.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]
        assert len(non_empty_lines) >= 1

    def test_jinja2_keep_trailing_newline(self, loader_with_temp_dir, temp_prompts_dir):
        """测试Jinja2环境保留末尾换行符"""
        newline_template = temp_prompts_dir / "newline.txt"
        newline_template.write_text("Content\n")

        rendered = loader_with_temp_dir.render_template("newline.txt")

        # 应该保留文件末尾的换行符
        assert rendered.endswith("\n")

    def test_render_template_with_complex_data_structure(self, loader_with_temp_dir, temp_prompts_dir):
        """测试使用复杂数据结构渲染"""
        nested_template = temp_prompts_dir / "nested.txt"
        nested_template.write_text(
            """
Project: {{ project.name }}
Status: {{ project.status }}

Team:
{% for member in project.team %}
- {{ member.name }} ({{ member.role }})
{% endfor %}
"""
        )

        rendered = loader_with_temp_dir.render_template(
            "nested.txt",
            project={
                "name": "AI Assistant",
                "status": "Active",
                "team": [
                    {"name": "Alice", "role": "Engineer"},
                    {"name": "Bob", "role": "Designer"},
                ],
            },
        )

        assert "Project: AI Assistant" in rendered
        assert "Status: Active" in rendered
        assert "- Alice (Engineer)" in rendered
        assert "- Bob (Designer)" in rendered

    def test_load_template_j2_extension(self, loader_with_temp_dir):
        """测试加载.j2扩展名的模板"""
        template = loader_with_temp_dir.load_template("template.j2")

        rendered = template.render(content="Test Content")
        assert rendered == "Template: Test Content"

    def test_multiple_loaders_independent(self):
        """测试多个加载器实例相互独立"""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                dir1 = Path(tmpdir1) / "prompts1"
                dir2 = Path(tmpdir2) / "prompts2"
                dir1.mkdir()
                dir2.mkdir()

                # 在不同目录创建不同的模板
                (dir1 / "template1.txt").write_text("Template 1")
                (dir2 / "template2.txt").write_text("Template 2")

                loader1 = PromptLoader(prompts_dir=str(dir1))
                loader2 = PromptLoader(prompts_dir=str(dir2))

                # 每个加载器应该只能访问自己目录的模板
                assert "template1.txt" in loader1.list_templates()
                assert "template2.txt" not in loader1.list_templates()

                assert "template2.txt" in loader2.list_templates()
                assert "template1.txt" not in loader2.list_templates()

    def test_render_with_filter_functions(self, loader_with_temp_dir, temp_prompts_dir):
        """测试使用Jinja2内置过滤器"""
        filter_template = temp_prompts_dir / "filter.txt"
        filter_template.write_text("{{ text | upper }}")

        rendered = loader_with_temp_dir.render_template(
            "filter.txt", text="hello world"
        )

        assert rendered == "HELLO WORLD"

    def test_render_with_default_values(self, loader_with_temp_dir, temp_prompts_dir):
        """测试使用默认值渲染"""
        default_template = temp_prompts_dir / "default.txt"
        default_template.write_text("Name: {{ name | default('Unknown') }}")

        # 不提供name变量
        rendered = loader_with_temp_dir.render_template("default.txt")
        assert rendered == "Name: Unknown"

        # 提供name变量
        rendered = loader_with_temp_dir.render_template("default.txt", name="Alice")
        assert rendered == "Name: Alice"

    def test_path_operations(self, temp_prompts_dir):
        """测试Path对象操作"""
        loader = PromptLoader(prompts_dir=str(temp_prompts_dir))

        # 验证prompts_dir是Path对象
        assert isinstance(loader.prompts_dir, Path)

        # 验证可以进行路径操作
        full_path = loader.prompts_dir / "test.txt"
        assert isinstance(full_path, Path)
        assert str(full_path).endswith("test.txt")
