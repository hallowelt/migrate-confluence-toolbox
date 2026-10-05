#!/usr/bin/env python3
"""
Minimal self-check for bin/minimize-confluence-export.py. No frameworks,
no fixtures beyond the repo's existing multi-space test XML.

Run: python3 bin/test_minimize_confluence_export.py
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "bin" / "minimize-confluence-export.py"
FIXTURE = REPO_ROOT / "delme_entities.xml"


def run(input_dir: Path, output_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(TOOL), str(input_dir), str(output_dir)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"tool failed: {result.stdout}\n{result.stderr}"


def run_with_flags(input_dir: Path, output_dir: Path, *flags: str) -> None:
    result = subprocess.run(
        [sys.executable, str(TOOL), *flags, str(input_dir), str(output_dir)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"tool failed: {result.stdout}\n{result.stderr}"


def test_filters_foreign_space() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        shutil.copy(FIXTURE, input_dir / "entities.xml")
        (input_dir / "exportDescriptor.properties").write_text("spaceKey=HR\n")
        (input_dir / "attachments").mkdir()
        (input_dir / "attachments" / "dummy.bin").write_text("x")

        output_dir = tmp_path / "minimized"
        run(input_dir, output_dir)

        out_xml = (output_dir / "entities.xml").read_text()
        assert "HR" in out_xml
        assert "OTHER" not in out_xml
        assert not (output_dir / "attachments").exists(), "attachments folder must be ignored"
        assert (output_dir / "exportDescriptor.properties").exists()


def test_no_properties_file_copies_unchanged() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        shutil.copy(FIXTURE, input_dir / "entities.xml")

        output_dir = tmp_path / "minimized"
        run(input_dir, output_dir)

        original = (input_dir / "entities.xml").read_bytes()
        copied = (output_dir / "entities.xml").read_bytes()
        assert original == copied, "without a spaceKey, the file must pass through unchanged"


def test_collateral_damage_is_reported() -> None:
    """
    Attachment 300 belongs to the kept space (HR, space id 1) but its
    containerContent stays pointed at page 200, which belongs to the
    dropped space (OTHER, space id 2) -- the KB article's actual root
    cause (stale SPACEID after a page move). The tool must warn instead of
    silently producing an incomplete kept space.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        corrupted = FIXTURE.read_text().replace(
            '<property name="containerContent" class="Page" package="com.atlassian.confluence.pages">\n'
            '\t\t\t<id name="id">100</id>\n\t\t</property>\n\t</object>\n'
            '\t<object class="Attachment" package="com.atlassian.confluence.pages">\n'
            '\t\t<id name="id">400</id>',
            '<property name="containerContent" class="Page" package="com.atlassian.confluence.pages">\n'
            '\t\t\t<id name="id">200</id>\n\t\t</property>\n\t</object>\n'
            '\t<object class="Attachment" package="com.atlassian.confluence.pages">\n'
            '\t\t<id name="id">400</id>',
        )
        (input_dir / "entities.xml").write_text(corrupted)
        (input_dir / "exportDescriptor.properties").write_text("spaceKey=HR\n")

        output_dir = tmp_path / "minimized"
        result = subprocess.run(
            [sys.executable, str(TOOL), str(input_dir), str(output_dir)],
            capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        assert "cross-space reference corruption" in result.stdout, result.stdout
        assert "Attachment (ID:300)" in result.stdout, result.stdout


def test_filters_foreign_historical_version_and_its_body() -> None:
    """
    A historical Page version carries no "space" property of its own (only
    an "originalVersionId" back-reference to the live page it's a version
    of) -- self-contained fixture, doesn't depend on FIXTURE.
    """
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<hibernate-generic>
<object class="Space" package="com.atlassian.confluence.spaces">
<id name="id">1</id>
<property name="key"><![CDATA[KEEP]]></property>
</object>
<object class="Space" package="com.atlassian.confluence.spaces">
<id name="id">2</id>
<property name="key"><![CDATA[OTHER]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">100</id>
<property name="title"><![CDATA[Keep Home]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">1</id>
</property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">101</id>
<property name="title"><![CDATA[Keep Home]]></property>
<property name="originalVersionId">100</property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">150</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">101</id>
</property>
<property name="body"><![CDATA[keep historical body]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">200</id>
<property name="title"><![CDATA[Foreign Home]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">2</id>
</property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">201</id>
<property name="title"><![CDATA[Foreign Home]]></property>
<property name="originalVersionId">200</property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">300</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">201</id>
</property>
<property name="body"><![CDATA[foreign historical body]]></property>
</object>
</hibernate-generic>
"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "entities.xml").write_text(xml)
        (input_dir / "exportDescriptor.properties").write_text("spaceKey=KEEP\n")

        output_dir = tmp_path / "minimized"
        run(input_dir, output_dir)

        out_xml = (output_dir / "entities.xml").read_text()
        assert "Keep Home" in out_xml
        assert "keep historical body" in out_xml, "kept space's historical version's body must survive"
        assert "Foreign Home" not in out_xml, "foreign live page must be dropped"
        assert "foreign historical body" not in out_xml, \
            "foreign historical version's body must be dropped, not just its live page"


def test_filters_foreign_historical_version_via_ref_style_original_version() -> None:
    """
    Some Confluence exports carry the historical-version back-reference as a
    ref-style "originalVersion" property (class="Page" + nested <id>) instead
    of (or in addition to) the scalar "originalVersionId" used by
    test_filters_foreign_historical_version_and_its_body. Missing this form
    means every historical Page silently falls back to "unresolvable ->
    keep", in every space -- this was an actual production bug, not just a
    hypothetical.
    """
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<hibernate-generic>
<object class="Space" package="com.atlassian.confluence.spaces">
<id name="id">1</id>
<property name="key"><![CDATA[KEEP]]></property>
</object>
<object class="Space" package="com.atlassian.confluence.spaces">
<id name="id">2</id>
<property name="key"><![CDATA[OTHER]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">100</id>
<property name="title"><![CDATA[Keep Home]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">1</id>
</property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">101</id>
<property name="title"><![CDATA[Keep Home]]></property>
<property name="originalVersion" class="Page" package="com.atlassian.confluence.pages"><id name="id">100</id>
</property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">150</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">101</id>
</property>
<property name="body"><![CDATA[keep historical body via ref]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">200</id>
<property name="title"><![CDATA[Foreign Home]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">2</id>
</property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">201</id>
<property name="title"><![CDATA[Foreign Home]]></property>
<property name="originalVersion" class="Page" package="com.atlassian.confluence.pages"><id name="id">200</id>
</property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">300</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">201</id>
</property>
<property name="body"><![CDATA[foreign historical body via ref]]></property>
</object>
</hibernate-generic>
"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "entities.xml").write_text(xml)
        (input_dir / "exportDescriptor.properties").write_text("spaceKey=KEEP\n")

        output_dir = tmp_path / "minimized"
        run(input_dir, output_dir)

        out_xml = (output_dir / "entities.xml").read_text()
        assert "Keep Home" in out_xml
        assert "keep historical body via ref" in out_xml, "kept space's historical version's body must survive"
        assert "Foreign Home" not in out_xml, "foreign live page must be dropped"
        assert "foreign historical body via ref" not in out_xml, \
            "foreign historical version's body must be dropped, not just its live page"


def test_filters_foreign_custom_content_and_its_body() -> None:
    """
    CustomContentEntityObject (whiteboards, drawio diagrams, plugin-backed
    generic content, ...) carries a real "space" property just like Page,
    but is easy to overlook as "just metadata". If this class isn't
    recognized, every row of it -- and its BodyContent, which can be large
    -- is kept unconditionally regardless of space, in every space in the
    export. Self-contained fixture, doesn't depend on FIXTURE.
    """
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<hibernate-generic>
<object class="Space" package="com.atlassian.confluence.spaces">
<id name="id">1</id>
<property name="key"><![CDATA[KEEP]]></property>
</object>
<object class="Space" package="com.atlassian.confluence.spaces">
<id name="id">2</id>
<property name="key"><![CDATA[OTHER]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">100</id>
<property name="title"><![CDATA[Keep Home]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">1</id>
</property>
</object>
<object class="CustomContentEntityObject" package="com.atlassian.confluence.content">
<id name="id">900</id>
<property name="title"><![CDATA[Foreign Whiteboard]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">2</id>
</property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">901</id>
<property name="content" class="CustomContentEntityObject" package="com.atlassian.confluence.content"><id name="id">900</id>
</property>
<property name="body"><![CDATA[HUGE FOREIGN WHITEBOARD PAYLOAD]]></property>
</object>
</hibernate-generic>
"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "entities.xml").write_text(xml)
        (input_dir / "exportDescriptor.properties").write_text("spaceKey=KEEP\n")

        output_dir = tmp_path / "minimized"
        run(input_dir, output_dir)

        out_xml = (output_dir / "entities.xml").read_text()
        assert "Keep Home" in out_xml
        assert "Foreign Whiteboard" not in out_xml, "foreign CustomContentEntityObject must be dropped"
        assert "HUGE FOREIGN WHITEBOARD PAYLOAD" not in out_xml, \
            "foreign CustomContentEntityObject's body must be dropped, not kept as unresolvable"


def _status_flags_fixture() -> str:
    """
    One space (KEEP), one page of each kind: a current page with a
    historical (superseded) version, a deleted page, and a draft page --
    each with its own body, and the deleted/draft pages also carrying a
    comment / label / content property, to check that excluding a page by
    status cascades to everything owned by it instead of leaving it dangling.
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<hibernate-generic>
<object class="Space" package="com.atlassian.confluence.spaces">
<id name="id">1</id>
<property name="key"><![CDATA[KEEP]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">100</id>
<property name="title"><![CDATA[Current Page]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">1</id>
</property>
<property name="contentStatus"><![CDATA[current]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">101</id>
<property name="title"><![CDATA[Current Page]]></property>
<property name="originalVersion" class="Page" package="com.atlassian.confluence.pages"><id name="id">100</id>
</property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">150</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">101</id>
</property>
<property name="body"><![CDATA[historical version body]]></property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">160</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">100</id>
</property>
<property name="body"><![CDATA[current version body]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">200</id>
<property name="title"><![CDATA[Deleted Page]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">1</id>
</property>
<property name="contentStatus"><![CDATA[deleted]]></property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">250</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">200</id>
</property>
<property name="body"><![CDATA[deleted page body]]></property>
</object>
<object class="Comment" package="com.atlassian.confluence.pages">
<id name="id">260</id>
<property name="containerContent" class="Page" package="com.atlassian.confluence.pages"><id name="id">200</id>
</property>
<property name="body"><![CDATA[comment on deleted page]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">300</id>
<property name="title"><![CDATA[Draft Page]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">1</id>
</property>
<property name="contentStatus"><![CDATA[draft]]></property>
<collection name="labellings" class="java.util.Collection"><element class="Labelling" package="com.atlassian.confluence.labels"><id name="id">360</id>
</element>
</collection>
<collection name="contentProperties" class="java.util.Collection"><element class="ContentProperty" package="com.atlassian.confluence.content"><id name="id">370</id>
</element>
</collection>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">350</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">300</id>
</property>
<property name="body"><![CDATA[draft page body]]></property>
</object>
<object class="Labelling" package="com.atlassian.confluence.labels">
<id name="id">360</id>
<property name="labelText"><![CDATA[draft page label]]></property>
</object>
<object class="ContentProperty" package="com.atlassian.confluence.content">
<id name="id">370</id>
<property name="stringValue"><![CDATA[draft page content property]]></property>
</object>
</hibernate-generic>
"""


def test_no_history_flag_drops_superseded_versions_and_their_body() -> None:
    xml = _status_flags_fixture()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "entities.xml").write_text(xml)
        (input_dir / "exportDescriptor.properties").write_text("spaceKey=KEEP\n")

        output_dir = tmp_path / "minimized"
        run_with_flags(input_dir, output_dir, "--no-history")

        out_xml = (output_dir / "entities.xml").read_text()
        assert "current version body" in out_xml, "current page body must survive"
        assert "historical version body" not in out_xml, "historical version's body must be dropped"
        # Unrelated flags weren't requested: deleted/draft pages untouched.
        assert "deleted page body" in out_xml
        assert "draft page body" in out_xml


def test_no_deleted_flag_cascades_to_body_and_comments() -> None:
    xml = _status_flags_fixture()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "entities.xml").write_text(xml)
        (input_dir / "exportDescriptor.properties").write_text("spaceKey=KEEP\n")

        output_dir = tmp_path / "minimized"
        run_with_flags(input_dir, output_dir, "--no-deleted")

        out_xml = (output_dir / "entities.xml").read_text()
        assert "Deleted Page" not in out_xml
        assert "deleted page body" not in out_xml, "deleted page's own body must be dropped, not orphaned"
        assert "comment on deleted page" not in out_xml, "comment on a deleted page must be dropped too"
        # Unrelated flags weren't requested: history/draft untouched.
        assert "historical version body" in out_xml
        assert "draft page body" in out_xml


def test_no_draft_flag_cascades_to_body_labels_and_content_properties() -> None:
    xml = _status_flags_fixture()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "entities.xml").write_text(xml)
        (input_dir / "exportDescriptor.properties").write_text("spaceKey=KEEP\n")

        output_dir = tmp_path / "minimized"
        run_with_flags(input_dir, output_dir, "--no-draft")

        out_xml = (output_dir / "entities.xml").read_text()
        assert "Draft Page" not in out_xml
        assert "draft page body" not in out_xml, "draft page's own body must be dropped, not orphaned"
        assert "draft page label" not in out_xml, "label owned by a draft page must be dropped too"
        assert "draft page content property" not in out_xml, \
            "content property owned (via collection) by a draft page must be dropped too"
        # Unrelated flags weren't requested: history/deleted untouched.
        assert "historical version body" in out_xml
        assert "deleted page body" in out_xml


def test_all_three_flags_combined() -> None:
    xml = _status_flags_fixture()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "entities.xml").write_text(xml)
        (input_dir / "exportDescriptor.properties").write_text("spaceKey=KEEP\n")

        output_dir = tmp_path / "minimized"
        run_with_flags(input_dir, output_dir, "--no-history", "--no-deleted", "--no-draft")

        out_xml = (output_dir / "entities.xml").read_text()
        assert "current version body" in out_xml, "the one remaining live current page must survive"
        assert "historical version body" not in out_xml
        assert "deleted page body" not in out_xml
        assert "comment on deleted page" not in out_xml
        assert "draft page body" not in out_xml
        assert "draft page label" not in out_xml
        assert "draft page content property" not in out_xml


if __name__ == "__main__":
    test_filters_foreign_custom_content_and_its_body()
    test_filters_foreign_historical_version_and_its_body()
    test_filters_foreign_historical_version_via_ref_style_original_version()
    test_filters_foreign_space()
    test_no_properties_file_copies_unchanged()
    test_collateral_damage_is_reported()
    test_no_history_flag_drops_superseded_versions_and_their_body()
    test_no_deleted_flag_cascades_to_body_and_comments()
    test_no_draft_flag_cascades_to_body_labels_and_content_properties()
    test_all_three_flags_combined()
    print("OK")
