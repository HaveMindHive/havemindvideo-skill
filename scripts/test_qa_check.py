#!/usr/bin/env python3
"""Minimal self-check for qa_check.py's pure logic (no ffmpeg/files needed)."""

from qa_check import aspect_matches, expected_dims


def test_aspect_matches():
    assert aspect_matches(1080, 1920, "9:16")
    assert aspect_matches(1088, 1904, "9:16")  # real-world kling output, close but not exact
    assert not aspect_matches(1920, 1080, "9:16")  # landscape when vertical expected
    assert aspect_matches(1920, 1080, "16:9")
    assert aspect_matches(500, 500, "unknown_ratio")  # unrecognized target never fails


def test_expected_dims():
    assert expected_dims("9:16") == (9, 16)
    assert expected_dims("nonsense") is None


if __name__ == "__main__":
    test_aspect_matches()
    test_expected_dims()
    print("ok")
