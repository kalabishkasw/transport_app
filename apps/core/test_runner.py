"""
кастомний test runner з кольоровим виводом і великим підсумком у кінці.

після стандартного django-виводу друкую великий блок:
- зелений "OK" якщо все пройшло
- червоний "FAILED" якщо щось впало

активую через settings.TEST_RUNNER = 'apps.core.test_runner.ColorfulDjangoRunner'

запуск тестів:
    python manage.py test apps.portal apps.orders -v 2
"""
import unittest

from colorama import Fore, Style, init as colorama_init
from django.test.runner import DiscoverRunner

# windows-термінал не підтримує ANSI escape коди за замовчуванням.
# colorama init() їх трансформує у Windows API виклики.
colorama_init()


GREEN = Fore.GREEN + Style.BRIGHT
RED = Fore.RED + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
CYAN = Fore.CYAN + Style.BRIGHT
RESET = Style.RESET_ALL




class ColorfulTextResult(unittest.TextTestResult):
    """розширюю стандартний TextTestResult щоб після кожного тесту
    виводити кольоровий маркер замість буденного 'ok' / 'FAIL'."""

    def addSuccess(self, test):
        # викликаю TestResult.addSuccess (не TextTestResult), щоб не двоїлося
        unittest.TestResult.addSuccess(self, test)
        if self.showAll:
            self.stream.writeln(f'{GREEN}[OK]{RESET}')
        elif self.dots:
            self.stream.write(f'{GREEN}.{RESET}')
            self.stream.flush()

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        if self.showAll:
            self.stream.writeln(f'{RED}[ERROR]{RESET}')
        elif self.dots:
            self.stream.write(f'{RED}E{RESET}')
            self.stream.flush()

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        if self.showAll:
            self.stream.writeln(f'{RED}[FAIL]{RESET}')
        elif self.dots:
            self.stream.write(f'{RED}F{RESET}')
            self.stream.flush()

    def addSkip(self, test, reason):
        unittest.TestResult.addSkip(self, test, reason)
        if self.showAll:
            self.stream.writeln(f'{YELLOW}[SKIP]{RESET} ({reason})')
        elif self.dots:
            self.stream.write(f'{YELLOW}s{RESET}')
            self.stream.flush()




# просто OK / FAILED, без рамки.
_OK_BANNER = '\nOK\n'
_FAIL_BANNER = '\nFAILED\n'




class ColorfulDjangoRunner(DiscoverRunner):
    """django runner з кольоровим виводом і великим підсумковим банером."""

    def get_resultclass(self):
        return ColorfulTextResult

    def run_tests(self, test_labels, **kwargs):
        failures = super().run_tests(test_labels, **kwargs)
        # друкую підсумок ПІСЛЯ всього стандартного виводу.
        # failures = кількість failures + errors (django.suite_result).
        # 0 означає все ок.
        if failures == 0:
            print(f'{GREEN}{_OK_BANNER}{RESET}')
        else:
            print(f'{RED}{_FAIL_BANNER}{RESET}')
            print(f'{RED}  {failures} тест(ів) провалилось.{RESET}')
        return failures
