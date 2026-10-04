from __future__ import annotations

import subprocess
import math
import unittest
from unittest import mock

from useless_maybe import toast


class ToastLaunchTests(unittest.TestCase):
    def setUp(self) -> None:
        # Launcher tests emulate Windows even on CI hosts where subprocess
        # does not expose Windows-only process flags.
        flags = mock.patch.multiple(subprocess, DETACHED_PROCESS=0x00000008,
                                    CREATE_NO_WINDOW=0x08000000, create=True)
        flags.start()
        self.addCleanup(flags.stop)

    def test_non_windows_or_blank_message_does_not_launch(self) -> None:
        with mock.patch.object(toast.sys, "platform", "linux"), mock.patch.object(toast.subprocess, "Popen") as popen:
            self.assertFalse(toast.launch_toast("Nothing happened."))
            popen.assert_not_called()
        with mock.patch.object(toast.sys, "platform", "win32"), mock.patch.object(toast.subprocess, "Popen") as popen:
            self.assertFalse(toast.launch_toast("  "))
            popen.assert_not_called()

    def test_detached_launch_is_windowless_and_does_not_wait(self) -> None:
        with mock.patch.object(toast.sys, "platform", "win32"), \
             mock.patch.object(toast, "_python_without_console", return_value=toast.Path("C:/Python/pythonw.exe")), \
             mock.patch.object(toast.subprocess, "Popen") as popen:
            self.assertTrue(toast.launch_toast("Nothing happened.\nProbably."))
        argv, kwargs = popen.call_args
        self.assertEqual(toast.Path(argv[0][0]), toast.Path("C:/Python/pythonw.exe"))
        self.assertEqual(argv[0][1], "-I")
        self.assertEqual(argv[0][-2:], ["--message", "Nothing happened.\nProbably."])
        script = toast.Path(argv[0][2])
        self.assertEqual(script.name, "show_toast.py")
        self.assertEqual(script.parent.name, "scripts")
        self.assertEqual(kwargs["creationflags"], subprocess.DETACHED_PROCESS)
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
        self.assertTrue(kwargs["close_fds"])

    def test_launcher_failure_is_only_false(self) -> None:
        with mock.patch.object(toast.sys, "platform", "win32"), \
             mock.patch.object(toast, "_python_without_console", return_value=toast.Path("C:/Python/pythonw.exe")), \
             mock.patch.object(toast.subprocess, "Popen", side_effect=OSError("missing executable")):
            self.assertFalse(toast.launch_toast("Hello"))

    def test_no_pythonw_uses_create_no_window(self) -> None:
        with mock.patch.object(toast.sys, "platform", "win32"), \
             mock.patch.object(toast, "_python_without_console", return_value=toast.Path("C:/Python/python.exe")), \
             mock.patch.object(toast.subprocess, "Popen") as popen:
            self.assertTrue(toast.launch_toast("Hello"))
        self.assertEqual(popen.call_args.kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)

    def test_geometry_respects_signed_work_area_and_taskbar(self) -> None:
        area = toast.RECT(-1920, -200, 0, 840)
        self.assertEqual(toast._place(area), (-438, 684))
        tiny = toast.RECT(0, 0, 300, 120)
        self.assertEqual(toast._place(tiny), (0, 0))

    def test_bounded_message_keeps_current_multiline_content(self) -> None:
        text = "You found a tiny frog.\n\n  @..@\n (----)\n( >__< )\n^^ ~~ ^^"
        self.assertEqual(toast._bounded_message(text), text)
        self.assertEqual(len(toast._bounded_message("x" * 500)), toast.MAX_MESSAGE)
        self.assertTrue(toast._bounded_message("x" * 500).endswith("…"))

    def test_wrap_preserves_intentional_blank_lines(self) -> None:
        class Font:
            def measure(self, text: str) -> int:
                return len(text) * 10

        font = Font()
        self.assertEqual(toast._wrap_pixels("Hello world\n\nAgain", font.measure, 60),
                         ["Hello", "world", "", "Again"])
        self.assertEqual(toast._wrap_pixels("  @..@", font.measure, 60), ["  @..@"])
        self.assertEqual(toast._wrap_pixels("abcdefghijkl", font.measure, 60), ["abcdef", "ghijkl"])
        self.assertEqual(toast._wrap_pixels("没有空格的很长中文", font.measure, 60),
                         ["没有空格的很", "长中文"])

    def test_nonfinite_duration_is_rejected_before_native_loading(self) -> None:
        with mock.patch.object(toast.sys, "platform", "win32"):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(duration=value):
                    self.assertFalse(toast.show_toast("Hello", value))

    def test_overflow_is_ellipsized_within_last_fitting_row(self) -> None:
        measure = lambda value: len(value) * 10
        lines = toast._fit_lines("\n".join("x" for _ in range(20)), measure, 12, 267, 90)
        self.assertLessEqual(len(lines) * 12, 90)
        self.assertTrue(lines[-1].endswith("…"))
        self.assertTrue(all(len(line) * 10 <= 267 for line in lines))


if __name__ == "__main__":
    unittest.main()
