#!/usr/bin/env python3
"""
Minimal self-check for bin/report-confluence-export.py. Builds a tiny
synthetic entities.xml (no external fixture dependency) and asserts the
counts at each verbosity level.

Run: python3 bin/test_report_confluence_export.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "bin" / "report-confluence-export.py"

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hibernate-generic>
<object class="Space" package="com.atlassian.confluence.spaces">
<id name="id">1</id>
<property name="key"><![CDATA[DEMO]]></property>
<property name="name"><![CDATA[Demo Space]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">100</id>
<property name="title"><![CDATA[Home]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">1</id>
</property>
<property name="contentStatus"><![CDATA[current]]></property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">101</id>
<property name="title"><![CDATA[Home]]></property>
<property name="originalVersionId">100</property>
</object>
<object class="Page" package="com.atlassian.confluence.pages">
<id name="id">102</id>
<property name="title"><![CDATA[Draft Page]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">1</id>
</property>
<property name="contentStatus"><![CDATA[draft]]></property>
</object>
<object class="Attachment" package="com.atlassian.confluence.pages">
<id name="id">200</id>
<property name="title"><![CDATA[dummy.pdf]]></property>
<property name="space" class="Space" package="com.atlassian.confluence.spaces"><id name="id">1</id>
</property>
<property name="contentStatus"><![CDATA[current]]></property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">300</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">100</id>
</property>
<property name="body"><![CDATA[<ac:image><ri:attachment ri:filename="dummy.pdf" /></ac:image>]]></property>
</object>
<object class="BodyContent" package="com.atlassian.confluence.core">
<id name="id">301</id>
<property name="content" class="Page" package="com.atlassian.confluence.pages"><id name="id">101</id>
</property>
<property name="body"><![CDATA[old body text]]></property>
</object>
<object class="Comment" package="com.atlassian.confluence.pages">
<id name="id">400</id>
<property name="containerContent" class="Page" package="com.atlassian.confluence.pages"><id name="id">100</id>
</property>
</object>
<object class="Label" package="com.atlassian.confluence.labels">
<id name="id">500</id>
<property name="name"><![CDATA[demo]]></property>
</object>
<object class="ConfluenceUserImpl" package="com.atlassian.confluence.user">
<id name="key">u1</id>
</object>
</hibernate-generic>
"""


def run(args) -> str:
    result = subprocess.run(
        [sys.executable, str(TOOL)] + args, capture_output=True, text=True
    )
    assert result.returncode == 0, f"tool failed: {result.stdout}\n{result.stderr}"
    return result.stdout


def test_summary_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "entities.xml"
        xml_path.write_text(SAMPLE_XML)
        out = run([str(xml_path)])
        assert "Spaces" in out and "Count" in out  # summary table header
        assert "1 current, 1 historical versions" in out, out
        assert "in page/blog post content" in out, out


def test_per_space_breakdown_and_orphans() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "entities.xml"
        xml_path.write_text(SAMPLE_XML)
        out = run([str(xml_path), "-v"])
        assert "DEMO" in out and "2" in out  # DEMO row: 2 live pages, 1 attachment, 1 comment
        assert "no resolvable owning space" in out and "1 Page" in out, out


def test_content_status_and_size_breakdown() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "entities.xml"
        xml_path.write_text(SAMPLE_XML)
        out = run([str(xml_path), "-v"])
        assert "Content status" in out, out
        assert "Historical" in out, out
        assert "File size by top-level object class" in out, out
        assert "BodyContent" in out, out


def test_body_content_size_at_vv() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "entities.xml"
        xml_path.write_text(SAMPLE_XML)
        out = run([str(xml_path), "-vv"])
        assert "live Page, status=current" in out, out
        assert "historical Page version" in out, out


def test_titles_deduplicated_with_version_count() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "entities.xml"
        xml_path.write_text(SAMPLE_XML)
        out = run([str(xml_path), "-vv"])
        assert "Page titles (2 unique of 3 rows)" in out, out  # Home x2 (live+historical), Draft Page x1
        assert "Home (2 versions)" in out, out
        assert "Draft Page" in out and "Draft Page (" not in out, out  # single version: no count suffix
        assert "dummy.pdf" in out


if __name__ == "__main__":
    test_summary_counts()
    test_per_space_breakdown_and_orphans()
    test_content_status_and_size_breakdown()
    test_body_content_size_at_vv()
    test_titles_deduplicated_with_version_count()
    print("OK")
