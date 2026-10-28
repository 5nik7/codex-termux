#!/usr/bin/env python3
"""Human presentation and literal-output contracts in disposable roots only."""
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import subprocess
import termios
import time
import unittest

import test_wrapper as base
import test_runit as runit

ANSI = re.compile(r'\x1b\[[0-9;]*m')


class PresentationTests(unittest.TestCase):
    tearDown = base.WrapperTests.tearDown
    run_wrapper = base.WrapperTests.run_wrapper
    run_tty = base.WrapperTests.run_tty
    assert_ok = base.WrapperTests.assert_ok
    server = runit.RunitTests.server

    def setUp(self):
        runit.RunitTests.setUp(self)
        self.env['CODEX_TERMUX_OUTPUT'] = 'pretty'
        self.env['CODEX_TERMUX_COLOR'] = 'always'
        self.env['CODEX_TERMUX_BANNER'] = 'never'
        self.sv.write_text('#!'+base.BASH+'''\n
printf '%s' "${SV_OUTPUT-run: fixture (pid 321) 45s; log: down: fixture/log 2s\n}"
printf '%s' "${SV_STDERR-}" >&2
exit "${SV_EXIT:-0}"
''')

    def log(self, data):
        path = self.home / '.local/share/codex-remote/log/current'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_modes_precedence_and_narrow_reports(self):
        config = self.root / 'config'; config.write_text('output=raw\ncolor=always\n')
        env = {**self.env, 'CODEX_TERMUX_CONFIG': str(config), 'COLUMNS': '35'}
        result = self.run_wrapper('manage','config','show',env=env)
        self.assertIn('Effective wrapper configuration',result.stdout)
        self.assertIn('Output\x1b[0m\n    ',result.stdout)
        result = self.run_wrapper('--wrapper-output','raw','manage','config','show',env=env)
        self.assertNotIn('\x1b',result.stdout)
        self.assertIn('output=raw\n',result.stdout)
        env.pop('CODEX_TERMUX_OUTPUT')
        self.assertIn('output=raw\n',self.run_wrapper('manage','config','show',env=env).stdout)
        self.assertEqual(self.run_wrapper('--wrapper-output','invalid','manage','config','show').returncode,2)
        self.assertFalse(self.record.exists())
        mono=self.run_wrapper('--wrapper-color','never','manage','config','show')
        self.assertIn('Effective wrapper configuration',mono.stdout)
        self.assertNotIn('\x1b',mono.stdout)

    def test_service_fields_unknown_details_and_exit_codes(self):
        result = self.server('status')
        self.assert_ok(result)
        text = ANSI.sub('',result.stdout)
        for value in ['Service status','Running','321','45 seconds','log: down: fixture/log 2s','Enabled']:
            self.assertIn(value,text)
        self.assertIn('\x1b[1;32mRunning\x1b[0m',result.stdout)
        env = {**self.env,'SV_OUTPUT':'unrecognized service response 雪\n','SV_EXIT':'111','SV_STDERR':'native diagnostic\n'}
        result = self.server('status',env=env)
        self.assertEqual(result.returncode,111)
        self.assertIn('unrecognized service response 雪',result.stdout)
        self.assertIn('Failed (exit 111)',result.stdout)
        self.assertIn('native diagnostic',result.stderr)
        raw = self.run_wrapper('--wrapper-output','raw','manage','server','status',env=env)
        self.assertEqual((raw.stdout,raw.stderr,raw.returncode),('unrecognized service response 雪\n','native diagnostic\n',111))

    def test_auto_pipes_and_raw_override_preserve_service_bytes(self):
        env = {**self.env,'CODEX_TERMUX_OUTPUT':'auto','SV_OUTPUT':'down: service\n','SV_STDERR':'native'}
        result = self.server('status',env=env)
        self.assertEqual((result.stdout,result.stderr),('down: service\n','native'))
        self.assertEqual(self.server('is-enabled',env=env).stdout,'enabled\n')
        self.marker.touch()
        result = self.server('is-enabled')
        self.assertEqual(result.returncode,1)
        self.assertIn('\x1b[1;33mDisabled\x1b[0m',result.stdout)
        for args in [('--help',),('manage','server','help')]:
            out=self.run_wrapper('--wrapper-output','raw','--wrapper-banner','always',*args).stdout
            self.assertNotIn('\x1b',out)
            self.assertNotIn('< codex (termux) >',out)

    def test_pretty_service_and_logs_without_node(self):
        self.log(b'INFO hello\n')
        self.fake.unlink()
        (self.prefix/'bin/tail').symlink_to(shutil.which('tail'))
        (self.prefix/'bin/rm').symlink_to(shutil.which('rm'))
        env={**self.env,'PATH':str(self.prefix/'bin')}
        for action in ['start','stop','restart','status','enable','disable','is-enabled','logs']:
            result=self.server(action,env=env)
            self.assertIn(result.returncode,(0,1),(action,result.stderr))
            self.assertIn('\x1b',result.stdout,(action,result.stderr))
            self.assertNotIn('Node.js is required',result.stderr)

    def test_log_highlighting_and_literal_raw_bytes(self):
        text=('2026-10-28T12:34:56Z INFO hello 雪\n'
              '2026-10-28 12:34:57.001 WARN caution\n'
              '@400000006902e00000000000 ERROR failed\n'
              '  continuation mentioning ERROR\n\n'+('long '*2000)+'\n'
              'unknown \x1b]0;injected\x07 ending')
        self.log(text.encode())
        pretty=self.server('logs','-n','100')
        self.assert_ok(pretty)
        self.assertIn('\x1b[1;36mINFO\x1b[0m',pretty.stdout)
        self.assertIn('\x1b[1;33mWARN\x1b[0m',pretty.stdout)
        self.assertIn('\x1b[1;31mERROR\x1b[0m',pretty.stdout)
        body=ANSI.sub('',pretty.stdout)
        self.assertTrue(body.endswith(text.replace('\x1b','\\x1b').replace('\x07','\\x07')))
        self.assertNotIn('\x1b]',pretty.stdout)
        raw=self.run_wrapper('--wrapper-output','raw','manage','server','logs')
        self.assertEqual(raw.stdout,text)

    def test_pretty_follow_rotation_and_signal_cleanup(self):
        for sig,code in [(signal.SIGINT,130),(signal.SIGTERM,143)]:
            with self.subTest(signal=sig): self.follow_signal(sig,code)

    def test_colored_codex_logs_with_two_timestamps(self):
        text=('2026-10-28_21:13:09.25704 '
              '\x1b[2m2026-10-28T21:13:09.255877Z\x1b[0m '
              '\x1b[31mERROR\x1b[0m '
              '\x1b[2mcodex_core::tools::router\x1b[0m\x1b[2m:\x1b[0m '
              '\x1b[3merror\x1b[0m\x1b[2m=\x1b[0m'
              'write_stdin failed: Unknown process id 71146\n')
        self.log(text.encode())
        expected=ANSI.sub('',text)
        pretty=self.server('logs')
        self.assert_ok(pretty)
        self.assertTrue(ANSI.sub('',pretty.stdout).endswith(expected),pretty.stdout)
        self.assertIn('\x1b[2m2026-10-28_21:13:09.25704 \x1b[0m',pretty.stdout)
        self.assertIn('\x1b[2m2026-10-28T21:13:09.255877Z \x1b[0m',pretty.stdout)
        self.assertIn('\x1b[1;31mERROR\x1b[0m',pretty.stdout)
        self.assertNotIn('\\x1b[',pretty.stdout)
        mono=self.run_wrapper('--wrapper-color','never','manage','server','logs')
        self.assertTrue(mono.stdout.endswith(expected))
        self.assertNotIn('\x1b',mono.stdout)
        code,out=self.run_tty(['manage','server','logs'],{
            **self.env,'CODEX_TERMUX_OUTPUT':'auto','CODEX_TERMUX_COLOR':'auto','NO_COLOR':'1'})
        self.assertEqual(code,0,out)
        self.assertTrue(out.replace('\r\n','\n').endswith(expected),out)
        self.assertNotIn('\x1b',out)
        for mode in ['raw','auto']:
            raw=self.run_wrapper('--wrapper-output',mode,'manage','server','logs')
            self.assertEqual(raw.stdout,text)

    def test_log_sgr_normalization_preserves_other_text_and_controls(self):
        text=('\x1b[m\x1b[38;2;12;34;56mINFO\x1b[0m extended\n'
              'unknown \x1b[38:2::12:34:56mcolored\x1b[m 雪\n'
              '  continuation mentions ERROR and literal \\x1b[31m text\n'
              'INFO control \x1b[2J \x1b]0;title\x07 \x1b]8;;https://example.test\x1b\\link\x1b]8;;\x1b\\\n'
              'unterminated \x1b[31')
        self.log(text.encode())
        plain=re.sub(r'\x1b\[[0-9;:]*m','',text)
        expected=plain.replace('\x1b','\\x1b').replace('\x07','\\x07')
        pretty=self.server('logs')
        self.assert_ok(pretty)
        self.assertTrue(ANSI.sub('',pretty.stdout).endswith(expected),pretty.stdout)
        self.assertIn('\x1b[1;36mINFO\x1b[0m',pretty.stdout)
        self.assertNotIn('\x1b[2J',pretty.stdout)
        self.assertNotIn('\x1b]',pretty.stdout)
        self.assertNotIn('\x07',pretty.stdout)
        raw=self.run_wrapper('--wrapper-output','raw','manage','server','logs')
        self.assertEqual(raw.stdout,text)

    def follow_signal(self, sig, code):
        path=self.log(b'INFO initial\n')
        tail_pid=self.root/'tail.pid'
        tail=self.prefix/'bin/tail'
        tail.write_text('#!'+base.BASH+'\nprintf "%s" "$$" > "$TAIL_PID"\nexec '+shutil.which('tail')+' "$@"\n')
        tail.chmod(0o755)
        proc=subprocess.Popen([base.BASH,str(base.WRAPPER),'manage','server','logs','-f','-n','1'],
            env={**self.env,'TAIL_PID':str(tail_pid)},stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        output=b''
        def until(needle):
            nonlocal output
            deadline=time.monotonic()+12
            while needle not in output and time.monotonic()<deadline:
                if select.select([proc.stdout],[],[],.1)[0]: output+=os.read(proc.stdout.fileno(),65536)
            self.assertIn(needle,output)
        try:
            until(b'initial')
            path.rename(path.with_name('old')); path.write_text('WARN rotated\n')
            until(b'rotated')
            producer=int(tail_pid.read_text())
            proc.send_signal(sig)
            proc.communicate(timeout=5)
            self.assertEqual(proc.returncode,code)
            with self.assertRaises(ProcessLookupError): os.kill(producer,0)
            self.assertFalse(self.calls.exists())
        finally:
            if proc.poll() is None: os.killpg(proc.pid,signal.SIGKILL); proc.communicate()

    def test_machine_outputs_and_codex_streams_are_untouched(self):
        for args in [('manage','check','--json'),('manage','auth-check','--json'),('manage','config','example'),('completion','bash'),('completion','zsh'),('--wrapper-version',)]:
            pretty=self.run_wrapper(*args)
            raw=self.run_wrapper('--wrapper-output','raw',*args)
            self.assertEqual((pretty.returncode,pretty.stdout),(raw.returncode,raw.stdout),args)
            self.assertNotIn('\x1b',pretty.stdout)
        result=self.run_wrapper('run','--wrapper-output','literal','exec','fake prompt')
        self.assert_ok(result)
        self.assertEqual(json.loads(result.stdout)['args'],['--wrapper-output','literal','exec','fake prompt'])
        self.assertNotIn('\x1b',result.stdout)
        preview=self.run_wrapper('--wrapper-dry-run','run','exec','private prompt')
        self.assertNotIn('private prompt',preview.stdout+preview.stderr)
        self.assertIn('Forwarded argument count',preview.stdout)

    def test_tty_color_modes_and_independent_stderr(self):
        env={**self.env,'CODEX_TERMUX_OUTPUT':'auto','CODEX_TERMUX_COLOR':'auto'}
        for extra,colored,pretty in [({},True,True),({'NO_COLOR':'1'},False,True),({'TERM':'dumb'},False,False)]:
            status,out=self.run_tty(['manage','config','show'],{**env,**extra})
            self.assertEqual(status,0,out)
            self.assertEqual('\x1b[' in out,colored)
            self.assertEqual('Effective wrapper configuration' in out,pretty)
        # stderr stays a terminal while stdout is redirected: no ANSI leaks into stdout.
        capture=self.root/'stdout'
        pid,master=pty.fork()
        if pid==0:
            fd=os.open(capture,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600); os.dup2(fd,1); os.close(fd)
            os.execve(base.BASH,[base.BASH,str(base.WRAPPER),'manage','server','status'],{**env,'SV_STDERR':'diagnostic\n'})
        out=b''
        try:
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]:
                    try: chunk=os.read(master,65536)
                    except OSError: break
                    if not chunk: break
                    out+=chunk
            else: self.fail('independent-stream fixture did not finish')
            _,status=os.waitpid(pid,0)
            self.assertEqual(os.waitstatus_to_exitcode(status),0)
            self.assertIn(b'\x1b[',out)
            self.assertNotIn('\x1b',capture.read_text())
            self.assertTrue(capture.read_text().startswith('run: fixture'))
        finally:
            try: os.kill(pid,signal.SIGKILL)
            except ProcessLookupError: pass
            try: os.waitpid(pid,0)
            except ChildProcessError: pass
            os.close(master)

    def test_interrupt_while_renderer_drains_after_producer_exit(self):
        # A stalled formatter models a slow terminal after its producer is done.
        script='''source "$UI_SOURCE"
ui_output=pretty
ui_stream() { while :; do :; done; }
wait() {
  local rc=0
  if [[ $1 != "$ui_producer" ]]; then printf 'formatter-wait\\n'; fi
  builtin wait "$@" || rc=$?
  return "$rc"
}
ui_run_stream logs printf fixture
'''
        proc=subprocess.Popen([base.BASH,'-c',script],env={**self.env,'UI_SOURCE':str(base.ROOT/'src/ui.sh')},
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:
            self.assertTrue(select.select([proc.stdout],[],[],5)[0])
            self.assertEqual(proc.stdout.readline(),b'formatter-wait\n')
            proc.send_signal(signal.SIGINT)
            out,err=proc.communicate(timeout=5)
            self.assertEqual(proc.returncode,130,out+err)
        finally:
            if proc.poll() is None: os.killpg(proc.pid,signal.SIGKILL); proc.communicate()

    def test_node_report_uses_actual_terminal_width_without_columns(self):
        pid,master=pty.fork()
        if pid==0:
            termios.tcsetwinsize(1,(24,35))
            env={key:value for key,value in self.env.items() if key!='COLUMNS'}
            os.execve(base.BASH,[base.BASH,str(base.WRAPPER),'manage','server','status','--backend','managed'],env)
        out=b''
        try:
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]:
                    try: chunk=os.read(master,65536)
                    except OSError: break
                    if not chunk: break
                    out+=chunk
            else: self.fail('narrow Node report did not finish')
            _,status=os.waitpid(pid,0)
            self.assertEqual(os.waitstatus_to_exitcode(status),0,out)
            plain=ANSI.sub('',out.decode()).replace('\r\n','\n')
            self.assertIn('  State\n    Stopped\n',plain)
        finally:
            try: os.kill(pid,signal.SIGKILL)
            except ProcessLookupError: pass
            try: os.waitpid(pid,0)
            except ChildProcessError: pass
            os.close(master)

    def test_output_completion_values_and_boundaries(self):
        script='source "$COMPLETION"; COMP_WORDS=("$@"); COMP_CWORD=$((${#COMP_WORDS[@]}-1)); _codex_termux_complete; printf "%s\\n" "${COMPREPLY[@]}"'
        for args,expected in [(['--wrapper-output',''],{'auto','pretty','raw'}),
                              (['manage','self-update','--output',''],{'auto','pretty','raw'}),
                              (['run','--wrapper-output',''],set())]:
            result=subprocess.run([base.BASH,'--norc','-c',script,'fixture','codex-termux',*args],
                env={**self.env,'COMPLETION':str(base.ROOT/'completions/codex-termux.bash')},text=True,capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(set(filter(None,result.stdout.splitlines())),expected)


if __name__ == '__main__': unittest.main(verbosity=2)
