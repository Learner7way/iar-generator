"""Тесты XMLFormatter: форматирование XML в стиле IAR."""

import xml.etree.ElementTree as ET

from xml_formatter import XMLFormatter


class TestFormatCompact:
    def test_leaf_with_text_single_line(self):
        elem = XMLFormatter.create_element("name", text="value")
        assert XMLFormatter.format_compact(elem) == "<name>value</name>"

    def test_element_with_children_is_indented(self):
        root = ET.Element("configuration")
        child = ET.SubElement(root, "option")
        ET.SubElement(child, "state").text = "1"
        result = XMLFormatter.format_compact(root)
        assert "<configuration>" in result
        assert "</configuration>" in result
        assert "    <option>" in result
        assert "        <state>1</state>" in result

    def test_empty_element_self_closing(self):
        elem = ET.Element("option")
        assert XMLFormatter.format_compact(elem) == "<option/>"

    def test_attributes_included(self):
        elem = ET.Element("project", attrib={"version": "1.0"})
        result = XMLFormatter.format_compact(elem)
        assert (
            '<project version="1.0">' in result or '<project version="1.0"/>' in result
        )

    def test_none_returns_empty(self):
        assert XMLFormatter.format_compact(None) == ""


class TestFactories:
    def test_create_element_with_text_and_attrib(self):
        elem = XMLFormatter.create_element("option", text="x", attrib={"id": "1"})
        assert elem.tag == "option"
        assert elem.text == "x"
        assert elem.get("id") == "1"

    def test_create_file_element(self):
        file_elem = XMLFormatter.create_file_element(r"$PROJ_DIR$\..\src\uart.c")
        name = file_elem.find("name")
        assert file_elem.tag == "file"
        assert name is not None
        assert name.text == r"$PROJ_DIR$\..\src\uart.c"

    def test_create_group_element(self):
        group = XMLFormatter.create_group_element("Drivers")
        name = group.find("name")
        assert group.tag == "group"
        assert name.text == "Drivers"
