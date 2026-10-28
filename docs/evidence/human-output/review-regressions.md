# Final review regressions before correction

These targeted regressions demonstrated both issues before the corresponding
source corrections. They are retained as failure evidence, not final results.

```text
test_interrupt_while_renderer_drains_after_producer_exit (__main__.PresentationTests.test_interrupt_while_renderer_drains_after_producer_exit) ... FAIL
test_node_report_uses_actual_terminal_width_without_columns (__main__.PresentationTests.test_node_report_uses_actual_terminal_width_without_columns) ... FAIL

======================================================================
FAIL: test_interrupt_while_renderer_drains_after_producer_exit (__main__.PresentationTests.test_interrupt_while_renderer_drains_after_producer_exit)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_presentation.py", line 224, in test_interrupt_while_renderer_drains_after_producer_exit
    self.assertEqual(proc.returncode,130,out+err)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 0 != 130 : b'formatter-wait\n'

======================================================================
FAIL: test_node_report_uses_actual_terminal_width_without_columns (__main__.PresentationTests.test_node_report_uses_actual_terminal_width_without_columns)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_presentation.py", line 247, in test_node_report_uses_actual_terminal_width_without_columns
    self.assertIn('  State\n    Stopped\n',plain)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: '  State\n    Stopped\n' not found in '\nManaged server\n  State                       Stopped\n  Instance                    /data/data/com.termux/files/usr/tmp/codex-termux-integration-lhlnos10/home space 雪/.local/share/codex-termux/servers/9c3321c7f31ef9885a3c9fcc0828c04e\n'

----------------------------------------------------------------------
Ran 2 tests in 2.085s

FAILED (failures=2)
```
