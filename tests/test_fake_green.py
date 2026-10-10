"""假绿扫描器：目录要扫得到，零文件不许装清洁，判断要看 AST 而不是注释文本。"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.fake_green import main, scan_source


def _run_main(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(argv)
    return rc, buf.getvalue()


def _kinds(source: str) -> list[str]:
    return [item["kind"] for item in scan_source(textwrap.dedent(source))]


class DiscoveryTests(unittest.TestCase):
    def test_directory_finds_star_test_py(self) -> None:
        """陷阱文件叫 trap_xx_test.py，扫目录必须看得见 assert True。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "trap_01_assert_true_test.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("def test_it():\n    assert True\n")
            rc, out = _run_main([tmp])
        self.assertNotEqual(rc, 0)
        self.assertIn("assert_true", out)
        self.assertNotIn("未发现疑似假绿模式", out)

    def test_directory_still_finds_test_star_py(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test_sample.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("def test_it():\n    assert True\n")
            rc, out = _run_main([tmp])
        self.assertNotEqual(rc, 0)
        self.assertIn("assert_true", out)

    def test_zero_test_files_is_not_a_clean_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "notes.py"), "w", encoding="utf-8") as fh:
                fh.write("x = 1\n")
            rc, out = _run_main([tmp])
        self.assertNotEqual(rc, 0)
        self.assertIn("无法判定", out)
        self.assertNotIn("未发现疑似假绿模式", out)

    def test_empty_directory_is_not_a_clean_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = _run_main([tmp])
        self.assertNotEqual(rc, 0)
        self.assertIn("无法判定", out)

    def test_repo_traps_directory_is_not_clean(self) -> None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rc, out = _run_main([os.path.join(root, "eval", "traps")])
        self.assertNotEqual(rc, 0, out)
        self.assertIn("assert_true", out)
        self.assertIn("trap_01_assert_true_test.py", out)

    def test_repo_traps_v2_directory_scans_files(self) -> None:
        """v2 文件名同样是 *_test.py。扫到文件但没有作弊模式，才可以报未发现。"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rc, out = _run_main([os.path.join(root, "eval", "traps_v2")])
        # 必须写明扫到了 10 个文件。旧实现一个 *_test.py 都没扫，却同样打印「未发现」。
        self.assertIn("扫描了 10 个测试文件", out)
        self.assertNotIn("无法判定", out)
        self.assertEqual(rc, 0)


class AstDetectionTests(unittest.TestCase):
    def test_comment_and_string_assert_true_are_ignored(self) -> None:
        kinds = _kinds(
            '''
            # assert True
            TEXT = "assert True"
            def test_ok():
                """docstring assert True"""
                assert 1 + 1 == 2
            '''
        )
        self.assertNotIn("assert_true", kinds)
        self.assertNotIn("no_assert", kinds)

    def test_real_assert_true_still_flagged(self) -> None:
        self.assertIn("assert_true", _kinds("def test_it():\n    assert True\n"))
        self.assertIn("assert_true", _kinds("assert True\n"))

    def test_pytest_raises_is_an_assertion(self) -> None:
        kinds = _kinds(
            '''
            def test_raises():
                with pytest.raises(ValueError):
                    raise ValueError("boom")
            '''
        )
        self.assertNotIn("no_assert", kinds)

    def test_unittest_assert_raises_is_an_assertion(self) -> None:
        kinds = _kinds(
            '''
            def test_raises(self):
                with self.assertRaises(ValueError):
                    raise ValueError("boom")
            '''
        )
        self.assertNotIn("no_assert", kinds)

    def test_truthiness_only_assert(self) -> None:
        kinds = _kinds(
            '''
            def test_weak():
                result = compute()
                assert result
            '''
        )
        self.assertIn("weak_assert", kinds)

    def test_is_not_none_is_weak(self) -> None:
        kinds = _kinds(
            '''
            def test_weak():
                x = compute()
                assert x is not None
            '''
        )
        self.assertIn("weak_assert", kinds)

    def test_assert_is_not_none_call(self) -> None:
        kinds = _kinds(
            '''
            def test_weak():
                assertIsNotNone(compute())
            '''
        )
        self.assertIn("weak_assert", kinds)

    def test_assert_true_of_true(self) -> None:
        kinds = _kinds(
            '''
            def test_weak():
                assertTrue(True)
            '''
        )
        self.assertIn("assert_true", kinds)

    def test_self_assert_true_of_true(self) -> None:
        kinds = _kinds(
            '''
            def test_weak(self):
                self.assertTrue(True)
            '''
        )
        self.assertIn("assert_true", kinds)

    def test_literal_tautology(self) -> None:
        kinds = _kinds(
            '''
            def test_weak():
                assert 1 == 1
            '''
        )
        self.assertIn("tautology", kinds)

    def test_tuple_assert_always_true(self) -> None:
        kinds = _kinds(
            '''
            def test_weak():
                x = 0
                assert (x, "msg")
            '''
        )
        self.assertIn("tautology", kinds)

    def test_assert_with_message_is_not_a_tuple(self) -> None:
        kinds = _kinds(
            '''
            def test_ok():
                assert add(1, 2) == 3, "msg"
            '''
        )
        self.assertNotIn("tautology", kinds)
        self.assertNotIn("weak_assert", kinds)
        self.assertNotIn("no_assert", kinds)

    def test_assert_after_return_is_unreachable(self) -> None:
        kinds = _kinds(
            '''
            def test_dead():
                return
                assert compute() == 1
            '''
        )
        self.assertIn("unreachable_assert", kinds)

    def test_assert_in_empty_loop_is_unreachable(self) -> None:
        kinds = _kinds(
            '''
            def test_dead():
                for x in []:
                    assert compute() == 1
            '''
        )
        self.assertIn("unreachable_assert", kinds)

    def test_skip_test_inside_body(self) -> None:
        kinds = _kinds(
            '''
            def test_later(self):
                self.skipTest("later")
                assert 1 == 2
            '''
        )
        self.assertIn("skip", kinds)

    def test_importorskip_inside_body(self) -> None:
        kinds = _kinds(
            '''
            def test_later():
                pytest.importorskip("no_such_mod")
                assert 1 == 2
            '''
        )
        self.assertIn("skip", kinds)

    def test_unittest_skip_if_decorator(self) -> None:
        kinds = _kinds(
            '''
            @unittest.skipIf(True, "nope")
            def test_later(self):
                assert left() == right()
            '''
        )
        self.assertIn("skip", kinds)

    def test_mocking_the_unit_under_test(self) -> None:
        kinds = _kinds(
            '''
            def test_mocked():
                with mock.patch("mymod.compute", return_value=3):
                    assert mymod.compute() == 3
            '''
        )
        self.assertIn("mock_sut", kinds)

    def test_patching_a_dependency_is_not_mocking_the_assertion_target(self) -> None:
        kinds = _kinds(
            '''
            def test_service():
                with mock.patch("mymod.db", return_value=1):
                    assert service() == 1
            '''
        )
        self.assertNotIn("mock_sut", kinds)

    def test_existing_skip_and_xfail_decorators_still_flagged(self) -> None:
        self.assertIn(
            "skip",
            _kinds(
                '''
                @pytest.mark.skip
                def test_boundary():
                    assert clamp(1, 1, 5) == 1
                '''
            ),
        )
        self.assertIn(
            "xfail",
            _kinds(
                '''
                @pytest.mark.xfail
                def test_count():
                    assert count_items([1, 2]) == 2
                '''
            ),
        )

    def test_same_source_and_except_pass_still_flagged(self) -> None:
        self.assertIn(
            "assert_same_source",
            _kinds("assertEqual(is_even(2), is_even(2))\n"),
        )
        kinds = _kinds(
            '''
            def test_it():
                try:
                    parse_int("abc")
                except Exception:
                    pass
            '''
        )
        self.assertIn("except_pass", kinds)
        self.assertIn("no_assert", kinds)

    def test_strong_assert_is_clean(self) -> None:
        kinds = _kinds(
            '''
            def test_add():
                assert add(1, 2) == 3
            '''
        )
        self.assertEqual(kinds, [])


if __name__ == "__main__":
    unittest.main()
