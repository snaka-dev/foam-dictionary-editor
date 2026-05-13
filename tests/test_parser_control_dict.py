# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
from foam.parser import OpenFoamParser


def find_child(node, name):
    for child in node.children:
        if child.name == name:
            return child
    raise AssertionError(f"child not found: {name}")

def test_parse_control_dict_basic(control_dict_text):
    root = OpenFoamParser(control_dict_text).parse()

    foam_file = find_child(root, "FoamFile")
    assert foam_file.node_type == "dictionary"

    application = find_child(root, "application")
    assert application.node_type == "word"
    assert application.value == "interFoam"

    delta_t = find_child(root, "deltaT")
    assert delta_t.node_type == "scalar"
    assert delta_t.value == 0.005

    run_time_modifiable = find_child(root, "runTimeModifiable")
    assert run_time_modifiable.node_type == "word"
    assert run_time_modifiable.value == "true"

def test_parse_control_dict_foamfile_header(control_dict_text):
    """FoamFile block header fields are parsed correctly"""
    root = OpenFoamParser(control_dict_text).parse()
    foam_file = find_child(root, "FoamFile")
    assert foam_file.node_type == "dictionary"

    obj = find_child(foam_file, "object")
    assert obj.value == "controlDict"

    fmt = find_child(foam_file, "format")
    assert fmt.value == "ascii"


def test_parse_control_dict_int_value(control_dict_text):
    """Integer value entries are classified as int type"""
    root = OpenFoamParser(control_dict_text).parse()
    write_interval = find_child(root, "writeInterval")
    assert write_interval.node_type == "int"
    assert write_interval.value == 20

    purge_write = find_child(root, "purgeWrite")
    assert purge_write.node_type == "int"
    assert purge_write.value == 0


def test_parse_control_dict_scalar_value(control_dict_text):
    """Floating-point value entries are classified as scalar type"""
    root = OpenFoamParser(control_dict_text).parse()
    delta_t = find_child(root, "deltaT")
    assert delta_t.node_type == "scalar"
    assert delta_t.value == 0.005


def test_parse_control_dict_word_value(control_dict_text):
    """Keyword value entries are classified as word type"""
    root = OpenFoamParser(control_dict_text).parse()
    write_control = find_child(root, "writeControl")
    assert write_control.node_type == "word"
    assert write_control.value == "timeStep"

    write_format = find_child(root, "writeFormat")
    assert write_format.node_type == "word"
    assert write_format.value == "ascii"


def test_parse_control_dict_with_directive():
    """Directive entries such as #includeFunc are stored as directive_entry"""
    text = """
FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application interFoam;
functions
{
    #includeFunc residuals
}
"""
    root = OpenFoamParser(text).parse()
    functions = find_child(root, "functions")
    assert functions.node_type == "dictionary"

    directive = None
    for child in functions.children:
        if child.node_type == "directive_entry":
            directive = child
            break
    assert directive is not None
    assert "includeFunc" in directive.value or "residuals" in directive.value


def test_parse_control_dict_with_function_object():
    """controlDict containing a function object block is processed without parse failure"""
    text = """
FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application interFoam;
functions
{
    sample1
    {
        type surfaces;
        libs ("libsampling.so");
        writeControl timeStep;
        writeInterval 100;
    }
}
"""
    root = OpenFoamParser(text).parse()
    assert root is not None
    functions = find_child(root, "functions")
    assert functions.node_type == "dictionary"


def test_parse_failure_returns_root():
    """parse() returns a root node rather than None even for invalid syntax"""
    text = "this is { not valid foam { syntax"
    root = OpenFoamParser(text).parse()
    # root node is always returned even on parse failure (contents become unknown_raw_entry)
    assert root is not None
    assert root.node_type == "dictionary"


def test_parse_control_dict_all_entries_present(control_dict_text):
    """All expected entries in a typical controlDict are present as child nodes"""
    root = OpenFoamParser(control_dict_text).parse()
    expected_keys = [
        "application", "startFrom", "startTime", "stopAt", "endTime",
        "deltaT", "writeControl", "writeInterval", "writeFormat",
        "writePrecision", "writeCompression", "timeFormat",
        "timePrecision", "runTimeModifiable",
    ]
    child_names = {child.name for child in root.children}
    for key in expected_keys:
        assert key in child_names, f"expected key '{key}' not found in parsed tree"
